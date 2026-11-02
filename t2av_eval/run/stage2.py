"""Stage-2 conditions (row 4 two_stage_ungated, row 5 gated, framing b / c) on a media_only run, one dataset family per run.

Everything runs in one process with text-call threads (config/runs.yaml workers.stage2) and one key (--key-index), in a new
run dir that is also the stage-2 work dir: rows.jsonl, calls/<cond>/ (call cache), vcap_check, groups and score tables.
Stage 1 = the media_only run given with --stage1 (its <set>_shard<k>.csv files). --reuse-calls-from copies an earlier
stage-2 run's calls/ into the new dir first (the source is only read), so calls with an identical prompt are not repeated.
"""
import argparse, os, shutil, sys
from pathlib import Path

import yaml

from t2av_eval import paths as _P
from t2av_eval.judge import conditions as C
from t2av_eval.run import keys as _keys
from t2av_eval.run import rundir as _rd
from t2av_eval.run import stop as _stop

RUNS = yaml.safe_load(open(_P.CONFIG / "runs.yaml"))
GEN_SETS = {"row4": "G4", "row5": "G5", "frb": "FRb", "frc": "FRc"}


def _module(family):
    if family == "hdepic":
        from t2av_eval.judge.stage2 import hdepic as M
        return M, M.SETS
    from t2av_eval.judge.stage2 import generated as M
    return M, GEN_SETS


def stage1_csvs(stage1, set_name):
    fs = sorted(f for f in Path(stage1).glob(f"{set_name}_shard*.csv") if not f.name.endswith("_per_event.csv"))
    if not fs:
        raise FileNotFoundError(f"no {set_name}_shard*.csv in the stage-1 run {stage1}")
    return fs


def run_stage2(conditions, stage1, set_names, name, workers=None, key_index=0, calls_per_hour=None, avb_thresholds="preregistered",
               reuse_calls_from=None, dry_run=False):
    infos = [C.set_info(s) for s in set_names]
    fams = {i["family"] for i in infos}
    if len(fams) != 1:
        sys.exit(f"one dataset family per stage-2 run, got {sorted(fams)}")
    family = fams.pop()
    if any("stage2_source" not in i for i in infos):
        sys.exit(f"sets without stage-2 GT rows: {[i['name'] for i in infos if 'stage2_source' not in i]}")
    steps = C.stage2_steps(conditions)
    keys = _keys.gemini_keys()
    if not keys:
        sys.exit("no Gemini key: set GEMINI_API_KEY in the environment")
    kname, kval = keys[key_index]
    kid = _keys.key_id(kname, kval)
    cph = calls_per_hour or RUNS["pacing"]["calls_per_hour_per_key"]
    workers = workers or RUNS["workers"]["stage2"]
    csvs = {i["name"]: stage1_csvs(stage1, i["name"]) for i in infos}
    if dry_run:
        print(f"family {family}; steps {steps}; key {kid}; workers {workers}; stage 1 {stage1}")
        for s, fs in csvs.items():
            print(f"  {s}: {len(fs)} stage-1 csv")
        return None

    d = _rd.create(name)
    os.environ.update(GEMINI_API_KEY=kval, T2AV_KEY_ID=kid, T2AV_RUN_DIR=str(d), T2AV_SHARD="stage2", T2AV_CALLS_PER_HOUR=str(cph))
    for k in [k for k, _ in keys if k != "GEMINI_API_KEY"]:
        os.environ.pop(k, None)
    from t2av_eval.run import client as _client
    _client.install()
    _client.install_stop_hooks()
    M, SETS = _module(family)
    O = M.O
    O.OUT = d
    sources = set()
    for i in infos:
        src = i["stage2_source"]
        if str(O.PROMPTS[src]) != i["prompts"]:
            sys.exit(f"{i['name']}: stage-2 source {src} reads {O.PROMPTS[src]}, sets.yaml says {i['prompts']}")
        O.ANCHOR[src] = csvs[i["name"]]
        sources.add(src)
    all_rows = M.gt_rows
    M.gt_rows = lambda: [r for r in all_rows() if r["source"] in sources]
    for i in infos:
        if i.get("mute_anchor"):
            O.ANCHOR[i["stage2_source"]] = csvs[i["name"]]
    if family == "generated":
        M.AVB_MAIN = avb_thresholds
    if reuse_calls_from:
        shutil.copytree(Path(reuse_calls_from) / "calls", d / "calls")

    from t2av_eval.gate import preregistered as PR
    rule = PR.avb_rule()
    _rd.write_readme(
        d, purpose=f"stage 2 ({', '.join(C.ROW[s] for s in steps)})", condition=",".join(steps), model="gemini-3.6-flash", thinking="high",
        sets=set_names, prompts={f"prompts {i['name']}": i["prompts"] for i in infos},
        caches={"stage-1 run (row 1 anchor)": stage1, "call cache (calls/)": d / "calls",
                **({"call cache copied from": reuse_calls_from} if reuse_calls_from else {}),
                **{f"captions {i['name']}": i["captions"] for i in infos}},
        keys={"stage 2 (all text calls)": kid}, command=_rd.argv(),
        extra={"OBS_RULES md5": O.OBS_RULES_MD5, "pre-registered AVB rule": f"T {rule['T']} s, P {rule['P']} (written {rule['written']})",
               "T_flam": PR.t_flam(), "AVB thresholds (generated row 5)": avb_thresholds if family == "generated" else "pre-registered (HD-EPIC)",
               "pacing": f"{cph} calls / hour", "workers": workers, "stop rule": RUNS["stop"]["rule"]})
    ns = argparse.Namespace(axes="A,V,AVB", workers=workers, model="gemini-3.6-flash", cond=M.COND, dry_run=0, set=None)

    def calls(set_name):
        _rd.event(d, f"calls {set_name}")
        O.stage_run(argparse.Namespace(**{**vars(ns), "set": set_name}))
    ma = [i for i in infos if i.get("mute_anchor")]
    if ma and (len(ma) != len(infos) or "framing" in steps):
        sys.exit("mute_anchor sets run alone and have rows 4 / 5 only (A, FLAM lines)")
    try:
        if ma:                                                # mute_anchor A sets: HMA4 / HMA5 (P01/P02), HMB4 / HMB5 (P03-P09)
            for i in ma:
                src = i["stage2_source"]; sets = M.MA_SETS_BY[src]; nsi = argparse.Namespace(**{**vars(ns), "src": src})
                _rd.event(d, f"mute_anchor {i['name']} ({src})")
                M.stage_ma_rows(nsi); calls(sets["row4"])
                if "gated" in steps:
                    calls(sets["row5"])
                M.stage_ma_score(nsi)
            _rd.event(d, "end: stage 2 done; tables in this dir")
            return 0
        did_vcheck = False
        for step in steps:
            _rd.event(d, f"step {step}")
            if step == "two_stage_ungated":
                M.stage_rows4(ns); calls(SETS["row4"])
            if step in ("gated", "framing") and not did_vcheck:
                M.stage_vcheck(ns); did_vcheck = True
            if step == "gated":
                M.stage_rows5(ns); calls(SETS["row5"])
            if step == "framing":
                M.stage_framing(ns); calls(SETS["frb"]); calls(SETS["frc"])
        if hasattr(M, "stage_groups"):
            M.stage_groups(ns)
        M.stage_score(ns)
    except _stop.StopRun as e:
        _rd.event(d, f"STOP: {e}; rerun the remaining calls with --reuse-calls-from {d}")
        return 3
    _rd.event(d, "end: stage 2 done; tables in this dir")
    return 0
