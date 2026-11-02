"""t2av-eval: one command line for the main table and the final recipe. `t2av-eval <command> -h` for each.

  check                                   keys (ids only), roots, prompts / captions / caches of every set, recipe artifacts
  judge media_only|all_tools|routing      rows 1 / 2 / 3: --sets ... --name ...
  judge two_stage_ungated|gated|framing   rows 4 / 5 / framing: --stage1 RUN --sets ... --name ...
  controller choose                       text-only controller (gemini | openai) on a JSONL of stage-1 texts
  score                                   tables: metrics, comparison with the no-result bound, fixed / broken, AVB operating points
  data | evidence | gate | screen NAME    pass-through to the moved module's own command line (evidence / screen: qrsh only)
"""
import argparse, json, os, runpy, sys
from pathlib import Path

PASS = {
    "data": {"hdepic-items": "t2av_eval.data.build_items", "gt-v3": "t2av_eval.data.gt_v3", "mute-class": "t2av_eval.data.mute_class",
             "mute-anchor": "t2av_eval.data.mute_anchor", "mute-anchor-reselect": "t2av_eval.data.mute_anchor_reselect",
             "gen149": "t2av_eval.data.generated149", "gen220-gt": "t2av_eval.data.generated_gt"},
    "evidence": {"records": "t2av_eval.evidence.gen_evidence", "synchformer-action": "t2av_eval.evidence.synchformer_action",
                 "synchformer-gen": "t2av_eval.evidence.synchformer_gen", "panel": "t2av_eval.evidence.panel"},
    "gate": {"calibrate": "t2av_eval.gate.reliability", "derive-avb-rule": "t2av_eval.gate.avb_rule_derive",
             "holdout": "t2av_eval.gate.avb_rule_holdout", "drift-check": "t2av_eval.gate.drift_check",
             "v-caption-diag": "t2av_eval.gate.v_caption_diag"},
    "screen": {"clap": "t2av_eval.screening.clap", "imagebind": "t2av_eval.screening.imagebind", "qwen3s": "t2av_eval.screening.qwen3s",
               "vqascore": "t2av_eval.screening.vqascore", "qwen-ts": "t2av_eval.screening.qwen_ts"},
}
QRSH_ONLY = ("evidence", "screen")


def _sets(s):
    return [x for x in s.split(",") if x]


def cmd_check(a):
    from t2av_eval import paths as P
    from t2av_eval.judge import conditions as C
    from t2av_eval.gate import preregistered as PR
    from t2av_eval.run import keys as K
    ok = True
    ks = K.gemini_keys()
    print("Gemini keys:", ", ".join(K.key_id(n, v) for n, v in ks) or "NONE (set GEMINI_API_KEY)")
    ok &= bool(ks)
    print(f"roots: DATA {P.DATA}\n       INPUTS {P.INPUTS}\n       WORK {P.WORK}\n       cache-key root {P.CACHE_KEY_DATA_ROOT}")
    for s in C.config()["sets"]:
        i = C.set_info(s)
        miss = [k for k in ("prompts", "videos", "captions", "sync") if i.get(k) and not Path(i[k]).exists()]
        print(f"set {s:11s} {i['family']:9s} {'ok' if not miss else 'missing: ' + ', '.join(miss)}")
    try:
        r = PR.avb_rule(); print(f"AVB rule: T {r['T']} P {r['P']} written {r['written']}; T_flam {PR.t_flam()}")
    except Exception as e:
        ok = False; print("recipe artifacts:", e)
    if a.files and ks:
        from google import genai
        from t2av_eval.run import files as F
        for n, v in ks:
            u = F.used_gb(genai.Client(api_key=v)); print(f"Gemini Files {K.key_id(n, v)}: {u:.2f} GB used")
    return 0 if ok else 1


def cmd_judge(a):
    from t2av_eval.judge import conditions as C
    conds = a.condition.split(",")
    bad = [c for c in conds if c not in C.MEDIA + C.STAGE2]
    if bad or (len(conds) > 1 and set(conds) & set(C.MEDIA)):
        sys.exit(f"condition: one of {', '.join(C.MEDIA)}, or a comma list of {', '.join(C.STAGE2)}")
    if a.condition in C.MEDIA:
        from t2av_eval.run import launch as L
        return L.run_media(a.condition, _sets(a.sets), a.name, n_keys=a.keys, calls_per_hour=a.calls_per_hour, shards=a.shards,
                           items_from=a.items_from, dry_run=a.dry_run) or 0
    if not a.stage1:
        sys.exit(f"{a.condition} needs --stage1 (a media_only run dir)")
    from t2av_eval.run import stage2 as S2
    if not Path(a.stage1).is_dir():
        sys.exit(f"--stage1 {a.stage1}: not a run dir")
    return S2.run_stage2(conds, a.stage1, _sets(a.sets), a.name, workers=a.workers, key_index=a.key_index,
                         calls_per_hour=a.calls_per_hour, avb_thresholds=a.avb_thresholds, reuse_calls_from=a.reuse_calls_from,
                         dry_run=a.dry_run) or 0


def cmd_controller(a):
    import yaml
    from t2av_eval.gate import controller as CT
    from t2av_eval.run import rundir as RD
    tpl = yaml.safe_load(open(a.prompt))                      # {system: ..., user: "... {text} ..."}
    items = [json.loads(l) for l in open(a.inputs) if l.strip()]
    if a.backend == "gemini":
        from t2av_eval.run import client as CL
        CL.install()
    d = RD.create(a.name)
    os.environ.update(T2AV_RUN_DIR=str(d), T2AV_SHARD="controller", T2AV_CALLS_PER_HOUR=str(a.calls_per_hour))
    ctl = CT.make(a.backend)
    RD.write_readme(d, purpose="controller choices (pipeline v4 stage 3)", condition=f"controller:{a.backend}", model=ctl.cfg["model"],
                    thinking=ctl.cfg.get("thinking") or ctl.cfg.get("reasoning_effort"), sets=[Path(a.inputs).name],
                    prompts={"controller prompt": a.prompt, "inputs": a.inputs}, caches={}, keys={"controller": getattr(ctl, "key_id", ctl.cfg["key_env"])},
                    command=RD.argv(), extra=ctl.describe())
    from t2av_eval.run import stop as ST
    try:
        with open(d / "choices.jsonl", "w") as f:
            for it in items:
                parsed, raw = ctl.choose(tpl["system"], tpl["user"].format(text=it["text"]))
                f.write(json.dumps(dict(id=it["id"], choice=parsed, raw=raw)) + "\n")
    except ST.StopRun as e:
        RD.event(d, f"STOP: {e}")
        return 3
    RD.event(d, f"end: {len(items)} choices")
    return 0


def cmd_score(a):
    from t2av_eval.run import rundir as RD
    from t2av_eval.scoring import runs as SR
    from t2av_eval.scoring import tables as T
    parts = []
    if a.media:
        runs = dict(x.split("=", 1) for x in a.media.split(","))
        D = SR.score_media(runs, _sets(a.sets))
        parts.append(T.wide_from_long(D))
    if a.stage2:
        parts.append(SR.stage2_wide(a.stage2))
    if not parts:
        sys.exit("give --media row1=RUN[,row2=RUN,...] and / or --stage2 RUN")
    W = parts[0] if len(parts) == 1 else parts[1]                 # stage 2 carries row1 itself; media rows used alone otherwise
    d = RD.create(a.name)
    W.to_csv(d / "rows_wide.csv", index=False)
    for nm, t in (("metrics", T.metrics_table(W)), ("compare_vs_row1", T.compare_table(W)), ("avb_operating_points", T.operating_points(W))):
        t.to_csv(d / f"{nm}.csv", index=False)
        print(f"\n## {nm}\n" + t.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    if len(parts) == 2:
        M = parts[0]; M.to_csv(d / "media_rows_wide.csv", index=False)
        for nm, t in (("media_metrics", T.metrics_table(M)), ("media_compare_vs_row1", T.compare_table(M))):
            t.to_csv(d / f"{nm}.csv", index=False)
    (d / "README.md").write_text(f"# {d.name}\n\n- scoring only, no calls\n- media runs: {a.media or '-'}\n- stage-2 run: {a.stage2 or '-'}\n"
                                 f"- command: {' '.join(RD.argv())}\n")
    return 0


def cmd_pass(group, a, rest):
    mod = PASS[group][a.name]
    if group in QRSH_ONLY and not os.environ.get("JOB_ID") and not a.login_ok:
        sys.exit(f"{group} {a.name} runs GPU / heavy CPU work: start it inside qrsh (or pass --login-ok for a report-only stage)")
    sys.argv = [mod] + rest
    runpy.run_module(mod, run_name="__main__")
    return 0


def parser():
    from t2av_eval.judge import conditions as C
    ap = argparse.ArgumentParser(prog="t2av-eval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("check"); p.add_argument("--files", action="store_true", help="also list Gemini Files storage per key")
    p = sp.add_parser("judge", help="run one condition (a table row)")
    p.add_argument("condition", help=f"{' | '.join(C.MEDIA)}, or a comma list of {', '.join(C.STAGE2)}")
    p.add_argument("--sets", required=True, help="comma list of config/sets.yaml names")
    p.add_argument("--name", required=True, help="run dir name; the date is appended")
    p.add_argument("--stage1", help="stage-2 conditions: the media_only run dir")
    p.add_argument("--keys", type=int, help="media: use the first N Gemini keys (default all)")
    p.add_argument("--key-index", type=int, default=0, help="stage 2: which key (0 = GEMINI_API_KEY)")
    p.add_argument("--calls-per-hour", type=int, help="per key (default config/runs.yaml)")
    p.add_argument("--shards", type=int, help="media: shards per set (default config/sets.yaml)")
    p.add_argument("--workers", type=int, help="stage 2: text-call threads")
    p.add_argument("--items-from", help="media: rerun the items of this earlier run that have an error row or no row")
    p.add_argument("--reuse-calls-from", help="stage 2: copy this earlier stage-2 run's call cache first")
    p.add_argument("--avb-thresholds", choices=["preregistered", "batch"], default="preregistered",
                   help="generated row 5 AVB rule: preregistered (recipe_v4) or batch (reproduces the 10/30 outputs only)")
    p.add_argument("--dry-run", action="store_true")
    p = sp.add_parser("controller", help="text-only controller (pipeline v4 stage 3)")
    p.add_argument("action", choices=["choose"]); p.add_argument("--backend", choices=["gemini", "openai"], required=True)
    p.add_argument("--prompt", required=True, help="YAML with system and user (user contains {text})")
    p.add_argument("--inputs", required=True, help="JSONL of {id, text}"); p.add_argument("--name", required=True)
    p.add_argument("--calls-per-hour", type=int, default=2000)
    p = sp.add_parser("score", help="tables from run dirs, no calls")
    p.add_argument("--sets", default="", help="sets of the media runs"); p.add_argument("--media", help="row1=RUN,row2=RUN,row3=RUN")
    p.add_argument("--stage2", help="stage-2 run dir"); p.add_argument("--name", required=True)
    for g, mods in PASS.items():
        p = sp.add_parser(g, help=f"pass-through: {', '.join(mods)}")
        p.add_argument("name", choices=list(mods)); p.add_argument("--login-ok", action="store_true", help=argparse.SUPPRESS)
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in PASS:
        cut = argv.index("--") if "--" in argv else len(argv)
        a = parser().parse_args(argv[:cut])
        return cmd_pass(argv[0], a, argv[cut + 1:])
    a = parser().parse_args(argv)
    return {"check": cmd_check, "judge": cmd_judge, "controller": cmd_controller, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
