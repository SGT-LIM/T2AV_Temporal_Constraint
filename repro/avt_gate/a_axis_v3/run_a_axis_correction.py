#!/usr/bin/env python3
"""Corrected A-axis evaluation (contract v3, event-level gate; 2026-11-10). See A_AXIS_CONTRACT.md and a_event_gate.py.

Writes ONLY to $T2AV_OUT_DIR/a_axis_event_gate_v3_2026-11-10/ (an audit hook aborts any other write under the workspace, data or repo
roots). Historical runs, GT, eligibility, Stage-1 labels and tool outputs are read only.

  python run_a_axis_correction.py features        # per-event A features and openings at alpha .01/.05/.10 (no GT used)
  python run_a_axis_correction.py select_example  # freeze the walkthrough clip from composition + gate conditions only
  python run_a_axis_correction.py plan            # build every corrected A request; exact-request reuse or new call
  python run_a_axis_correction.py run [--workers 4]   # new reconsideration calls only (GEMINI_API_KEY in the environment)
  python run_a_axis_correction.py walkthrough     # real-example walkthrough + regression clip
  python run_a_axis_correction.py score           # labels, three views, tables, checks
"""
import sys
sys.dont_write_bytecode = True
import argparse, collections, hashlib, json, os, re, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
NAME = "a_axis_event_gate_v3_2026-11-10"
OUT = Path(os.environ["T2AV_OUT_DIR"]) / NAME
ALLOW = [str(OUT.resolve()) if OUT.exists() else str(OUT), "/dev/null"]
GUARD = [os.path.realpath(os.environ["T2AV_WORKSPACE"]), os.path.realpath(os.environ["T2AV_DATA"]), str(REPO)]


def _hook(ev, args):
    if ev == "open" and args and not isinstance(args[0], int) and len(args) > 1 and isinstance(args[1], str) and any(c in args[1] for c in "wax+"):
        p = os.path.realpath(os.fsdecode(args[0]))
        if any(p.startswith(os.path.realpath(a)) for a in ALLOW):
            return
        if any(p.startswith(g) for g in GUARD):
            raise PermissionError(f"write outside {OUT} blocked: {p}")
sys.addaudithook(_hook)

sys.path[:0] = [str(Path(__file__).resolve().parent), str(REPO / "evaluation/ablation/gepa_stage2"), str(REPO / "evaluation/ablation"), str(REPO / "repro/avt_gate/analysis")]
sys.path.append(str(REPO))
import numpy as np, pandas as pd                                                        # noqa: E402
import a_event_gate as AG                                                               # noqa: E402

ALPHAS = {"a01": 0.01, "a05": 0.05, "a10": 0.10}
CFGP = {t: REPO / f"repro/avt_gate/configs/sensitivity/{t}/frozen_config.json" for t in ALPHAS}
MAIN_CFG = REPO / "repro/avt_gate/configs/main/frozen_p12_config.json"
MODEL, THINKING, TEMP, SEED, MAXTRY = "gemini-3.6-flash", "high", 0.0, 42, 3
BILL = re.compile(r"spending cap|billing|exceeded its monthly", re.I)
SENS = Path(os.environ["T2AV_WORKSPACE"]) / "eval_results/analysis/sensitivity_2026-11-10"
SAN = Path(os.environ["T2AV_WORKSPACE"]) / "eval_results/analysis/sanjoy_two_baselines_2026-11-08"
CALLS, PROMPTS = OUT / "calls", OUT / "prompts"
_M = {}


def md5s(s):
    return hashlib.md5(s.encode() if isinstance(s, str) else s).hexdigest()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cfgs():
    return {t: json.load(open(p))["config"] for t, p in CFGP.items()}


def setup():
    if not _M:
        import alpha_sensitivity as AS
        M = AS.setup()
        _M.update(M); _M["AS"] = AS
    return _M


def universe():
    import alpha_sensitivity as AS
    return AS.universe()


# ------------------------------------------------------------------ features + openings (no GT)
def stage_features(a):
    OUT.mkdir(parents=True, exist_ok=True)
    M = setup(); FB, G, GPI = M["FB"], M["G"], M["GPI"]
    U = universe()
    A = U[U.axis == "A"].copy()
    IT = FB.items_all(); C = cfgs()
    rec_cache = {}

    def rec(ds, item):
        k = (ds, item)
        if k not in rec_cache:
            rec_cache[k] = G.evidence(FB.EVSRC[ds], item) if ds != "P03-P09" else None
        return rec_cache[k]
    rows = []
    for r in A.itertuples():
        kind = {"A speech": "speech", "A sound": "sounding"}.get(r.family, str(r.family))
        initial = r.initial if r.scored_row1 else ""
        x = dict(dataset=r.dataset, group=r.group, batch=r.batch, unit=r.unit, item=r.item, event=r.event, kind=kind, initial=initial,
                 scored_row1=bool(r.scored_row1), flam_max=r.flam_max, target_text="", heard_tokens="", transcript="", whisper_record=False,
                 flam_query="")
        if r.dataset != "P03-P09":
            e = IT[FB.PSET[r.dataset]][r.item]["events"][int(r.event.split("_")[1]) - 1]
            ev = rec(r.dataset, r.item)
            if kind == "speech":
                x["target_text"] = e.get("text", "")
                w = (ev or {}).get("whisper")
                h = AG.heard_tokens(w)
                x["whisper_record"] = h is not None
                x["heard_tokens"] = " ".join(sorted(h)) if h is not None else ""
                if w:
                    x["transcript"] = " ".join(s["text"].strip() for s in w["segments"] if s["no_speech_prob"] < 0.5)
            elif kind == "sounding" and ev:
                q1 = {z["event_id"]: z["queries"][0] for z in ev.get("events", []) if z.get("queries")}
                x["flam_query"] = q1.get(r.event, "")
        rows.append(x)
    F = pd.DataFrame(rows)
    for t, cfg in C.items():
        op, why, br, thr, opx, dr = [], [], [], [], [], []
        for x in F.itertuples():
            ev = dict(kind=x.kind, initial=x.initial, target_text=x.target_text, flam_max=None if pd.isna(x.flam_max) else float(x.flam_max), cfg=cfg,
                      heard=(set(x.heard_tokens.split()) if x.whisper_record else None))
            d = AG.decide(ev)
            op.append(bool(d["open"])); why.append(d["reason"]); br.append(d.get("branch", "")); thr.append(d.get("threshold")); opx.append(d.get("operator", ""))
            dr.append(d.get("direction", ""))
        F[f"open_{t}"], F[f"reason_{t}"], F[f"branch_{t}"], F[f"threshold_{t}"], F[f"operator_{t}"], F[f"direction_{t}"] = op, why, br, thr, opx, dr
    F["recognized"] = [bool(set(AG.norm(t)) & set(h.split())) if k == "speech" and w else False
                       for k, t, h, w in zip(F.kind, F.target_text, F.heard_tokens, F.whisper_record)]
    F.to_csv(OUT / "a_event_features_openings.csv", index=False, float_format="%.17g")
    s = F[F.scored_row1].groupby(["group", "kind", "initial"]).agg(units=("unit", "size"), **{f"open_{t}": (f"open_{t}", "sum") for t in ALPHAS})
    print(s.to_string())


# ------------------------------------------------------------------ example selection (composition + gate conditions only)
def stage_select_example(a):
    f = OUT / "selected_example.json"
    if f.exists():
        sys.exit(f"{f} exists (frozen); not changed")
    F = pd.read_csv(OUT / "a_event_features_openings.csv", keep_default_na=False, low_memory=False)
    F = F[F.scored_row1.astype(str) == "True"]
    cand = []
    for (ds, item), g in F[F.group.isin(["LTX", "MOVA"])].groupby(["dataset", "item"]):
        sp, so = g[g.kind == "speech"], g[g.kind == "sounding"]
        if not len(sp) or not len(so):
            continue
        o = g.open_a05.astype(str) == "True"
        if not o.any() or o.all():
            continue
        cov = {"speech open (initial FAIL, own word recognised)": bool(((g.kind == "speech") & o).any()),
               "speech closed (initial PASS)": bool(((g.kind == "speech") & (g.initial == "yes")).any()),
               "speech closed (initial FAIL, own word not recognised, another target recognised)":
                   bool(((g.kind == "speech") & (g.initial == "no") & ~o & (sp.recognized.astype(str) == "True").any()).any()),
               "sounding open": bool(((g.kind == "sounding") & o).any()), "sounding closed": bool(((g.kind == "sounding") & ~o).any())}
        cand.append(dict(dataset=ds, item=item, n_speech=len(sp), n_sounding=len(so), coverage=sum(cov.values()), branches=cov))
    C = pd.DataFrame(cand)
    C = C[C.branches.map(lambda b: b["speech open (initial FAIL, own word recognised)"])]          # the corrected Whisper path must be shown
    C = C.sort_values(["coverage", "dataset", "item"], ascending=[False, True, True])
    pick = C.iloc[0].to_dict()
    json.dump(dict(frozen_at=time.strftime("%Y-%m-%dT%H:%M:%S"), selected=dict(dataset=pick["dataset"], item=pick["item"]), branches=pick["branches"],
                   rule=("generated clip with >= 1 scored speech and >= 1 scored sounding A event, >= 1 open and >= 1 closed A gate under the "
                         "corrected alpha .05 rules, including an opened speech event; maximise the number of contract branches covered; ties by "
                         "(dataset, item) order. Inputs: event composition and gate decisions only (no GT, no Stage-2 label, no outcome)."),
                   candidates=len(C), top5=C.head(5)[["dataset", "item", "coverage"]].to_dict("records")), open(f, "w"), indent=1, default=str)
    print(json.load(open(f)))


# ------------------------------------------------------------------ requests
def build_request(ds, item, fam):
    M = setup(); BF, O = M["BF"], M["O"]
    text, s_ = BF.payload(ds, "A", item, fam)
    uid = f"{s_}|{item}|A"
    if text is None:
        return None, uid, "missing payload (no admitted evidence line)"
    cc = O.build_call(dict(set="PC", source=s_, uid=uid, item_id=item, axis="A", variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text}))
    return cc, uid, ("no stage-1 anchor" if cc is None else "")


def fingerprint(cc):
    return dict(user_md5=md5s(cc["user"]), system_md5=md5s(cc["system"]), schema_md5=md5s(json.dumps(cc["schema"], sort_keys=True)),
                settings=f"model={MODEL};thinking={THINKING};temperature={TEMP};seed={SEED};response_mime_type=application/json;media=none")


def reuse_index():
    """md5 -> ordered list of candidate handles, in the order final_benchmark_1108.reuse_index / alpha_sensitivity.reuse_idx scan them, then this run's
    calls. resolve() uses the first candidate that passes valid_record."""
    M = setup(); FB = M["FB"]
    RUNS = FB.RUNS; idx = collections.defaultdict(list)
    for k, v in json.load(open(RUNS / "p12_calib_1108/reuse_index.json")).items():
        idx[k].append(v)
    for d in ("p12_calib_1108/calls", "avb_anchorfix_1108/calls"):
        for p in (RUNS / d).glob("*.json"):
            r = json.load(open(p))
            if r.get("user_md5"):
                idx[r["user_md5"]].append(str(p))
    for p in (RUNS / "calls/gen_tool_text").glob("*.json"):
        try:
            r = json.load(open(p))
        except Exception:
            continue
        if r.get("user_md5"):
            idx[r["user_md5"]].append(str(p))
    for base in (RUNS / "final_cov_1108/calls", FB.CALLS, SENS / "calls", CALLS):
        for p in base.glob("*.json") if base.exists() else []:
            att = [x for x in json.load(open(p)).get("attempts", []) if x.get("complete")]
            if att:
                idx[att[-1]["user_md5"]].append(("attempts", str(p)))
    return idx


CODE_FILES = ["evaluation/ablation/new_eval.py", "evaluation/ablation/gepa_stage2/obs_judge_1028.py", "evaluation/ablation/gepa_stage2/run_two_stage.py",
              "evaluation/ablation/gepa_stage2/adapter.py"]
SYSTEM_MD5_STORED = "1ac460ed7a517e5d4db6505943ba97cc"      # system text of every stored single-axis reconsideration prompt, 11-06 .. 11-10


# Earliest point at which the system prompt / schema builder is verified identical to the current one: the verbatim snapshot of the
# untracked ablation code in refactor/pipeline-v4 commit 786d16e (2026-11-02 02:11:48 -0500). Rendering that snapshot's
# new_eval.build_system_prompt('none','none','none', single_axis=True) gives md5 1ac460ed... (= current), build_call uses the same
# system / schema expressions, and run_two_stage.py (SCHEMA) is byte-identical (md5 39cab118...). The July copy has no single_axis
# argument, so records written before the snapshot cannot be verified and are never reused.
VERIFIED_BUILDER_SINCE = "2026-11-02T02:11:48"


def code_cutoff():
    ws = Path(os.environ["T2AV_WORKSPACE"])
    m = {f: time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(ws / f))) for f in CODE_FILES}
    return VERIFIED_BUILDER_SINCE, m


def valid_record(rec, md5):
    """exact-request reuse: same user md5 (generation prompt, criteria, rules, Stage-1 judgments and evidence), same model settings, text
    only, and written by the current system-prompt / schema builder (record time after the builder's last modification)."""
    O = setup()["O"]
    if rec is None:
        return False, "no record"
    why = []
    cut, _ = code_cutoff()
    if not rec.get("time") or str(rec["time"]) < cut:
        why.append(f"written {rec.get('time')} before the earliest verified state of the system-prompt builder ({cut}); not verifiable")
    if rec.get("user_md5") != md5:
        why.append("user md5 differs")
    if rec.get("model", MODEL) != MODEL:
        why.append(f"model {rec.get('model')}")
    if rec.get("thinking", THINKING) != THINKING:
        why.append(f"thinking {rec.get('thinking')}")
    if rec.get("rules_md5") != O.OBS_RULES_MD5:
        why.append("OBS_RULES md5 differs")
    if rec.get("media") not in (None, "none"):
        why.append(f"media {rec.get('media')}")
    if rec.get("cond") not in (None, "gen_tool_text"):
        why.append(f"cond {rec.get('cond')}")
    if rec.get("status", "ok") != "ok":
        why.append("status not ok")
    return (not why), "; ".join(why)


def bad_md5():
    out = set()
    M = setup(); AS, FB = M["AS"], M["FB"]
    out |= AS.KNOWN_FAIL | FB.failed_md5()
    for base in (SENS / "calls", CALLS):
        for p in base.glob("*.json") if base.exists() else []:
            att = json.load(open(p))["attempts"]
            if len(att) >= MAXTRY and not any(x.get("complete") for x in att):
                out |= {x.get("user_md5") for x in att if x.get("user_md5")} | ({p.stem.split("__", 1)[1]} if "__" in p.stem else set())
    return out


def resolve(ds, item, opened, idx, bad):
    """-> dict with request, fingerprint, record, per-event labels, action."""
    M = setup(); FB, AU = M["FB"], M["AU"]
    cc, uid, why = build_request(ds, item, opened)
    if cc is None:
        return dict(cc=None, uid=uid, action=f"no request possible ({why})", rec=None, labels={}, fp={})
    fp = fingerprint(cc); md5 = fp["user_md5"]
    assert fp["system_md5"] == SYSTEM_MD5_STORED, "system prompt differs from the stored reconsideration prompts"
    rec, src, action = None, "", ""
    cands = []
    for h in dict.fromkeys(map(lambda v: tuple(v) if isinstance(v, list) else v, idx.get(md5, []))):
        r0 = FB.load_idx(list(h) if isinstance(h, tuple) else h)
        if r0 is not None:
            cands.append((str(r0.get("time", "")), h, r0))
    rejected = []
    for _, h, r0 in cands:              # first valid candidate in historical index order (the record the historical run used, if valid)
        ok, w = valid_record(r0, md5)
        if ok:
            rec = dict(r0); rec.setdefault("anchor", cc["anchor"]); src = str(h[1] if isinstance(h, tuple) else h); break
        rejected.append(w)
    if rec is None and rejected:
        action = f"cached record not reusable ({rejected[0]})"
    labels, miss = {}, []
    if rec is not None:
        for e in opened:
            l, st = AU.s2_event(rec, "A", e)
            labels[e] = l if st == "ok" and l in ("yes", "no") else None
            if labels[e] is None:
                miss.append(e)
        all_lab = {}
        for z in (rec.get("anchor") or []):
            eid = z.get("event_id")
            if eid:
                l, st = AU.s2_event(rec, "A", eid); all_lab[eid] = l if st == "ok" else f"({st})"
        if not miss:
            action = "this run (complete output)" if str(src).startswith(str(CALLS)) else "reuse (exact request, valid complete output)"
        else:
            action = f"valid record lacks labels for opened events {miss}"
    else:
        all_lab = {}
    if rec is None or miss:
        if md5 in bad:
            action = (action + "; " if action else "") + "unresolved earlier (max attempts without a complete output); not retried"
        elif not (CALLS / f"AE__{md5}.json").exists() or not any(x.get("complete") for x in json.load(open(CALLS / f"AE__{md5}.json"))["attempts"]):
            action = (action + " -> " if action else "") + "new call"
    return dict(cc=cc, uid=uid, fp=fp, rec=rec, src=src, labels=labels, all_labels=all_lab, action=action)


def opened_groups(F, t):
    o = F[F[f"open_{t}"].astype(str) == "True"]
    return {k: {e: ("A speech" if kd == "speech" else "A sound") for e, kd in zip(g.event, g.kind)} for k, g in o.groupby(["dataset", "item"])}


def stage_plan(a):
    F = pd.read_csv(OUT / "a_event_features_openings.csv", keep_default_na=False, low_memory=False)
    idx, bad = reuse_index(), bad_md5(); PROMPTS.mkdir(parents=True, exist_ok=True)
    rows = []
    for t in ALPHAS:
        for (ds, item), fam in sorted(opened_groups(F, t).items()):
            R = resolve(ds, item, fam, idx, bad)
            sp = sorted(e for e, f in fam.items() if f == "A speech"); so = sorted(e for e, f in fam.items() if f == "A sound")
            if R["cc"] is not None and R["action"].endswith("new call"):
                p = PROMPTS / f"AE__{R['fp']['user_md5']}.json"
                if not p.exists():
                    json.dump(dict(uid=R["uid"], item=item, axis="A", system=R["cc"]["system"], user=R["cc"]["user"], schema=R["cc"]["schema"], **R["fp"],
                                   anchor=R["cc"]["anchor"], need=sorted(fam)), open(p, "w"), indent=1)
            rows.append(dict(alpha=t, dataset=ds, item=item, opened_events=";".join(sorted(fam)), whisper_supports_events=";".join(sp),
                             flam_events=";".join(so), **(R["fp"] or {}), action=R["action"], reuse_source=R.get("src", ""),
                             prompt_chars=(len(R["cc"]["system"]) + len(R["cc"]["user"])) if R["cc"] else 0))
    P = pd.DataFrame(rows); P.to_csv(OUT / "call_plan.csv", index=False)
    new = P[P.action.str.endswith("new call")].drop_duplicates("user_md5")
    summ = dict(by_alpha_action=P.groupby(["alpha", "action"]).size().rename("n").reset_index().to_dict("records"),
                requests_total=len(P), unique_requests=int(P.user_md5.nunique()), unique_new_calls=len(new),
                with_speech_evidence=int((P.whisper_supports_events != "").sum()))
    us = [u for f in (SENS / "calls").glob("AS__*.json") for x in json.load(open(f))["attempts"] for u in [x.get("usage") or {}] if u.get("prompt_token_count")]
    per = [(u["prompt_token_count"] * 1.5 + ((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)) * 7.5) / 1e6 for u in us]
    if per:
        q = np.percentile(per, [25, 50, 75]); summ.update(est_usd_median=round(len(new) * q[1], 3), est_usd_iqr=[round(len(new) * q[0], 3), round(len(new) * q[2], 3)],
                                                           est_basis=f"{len(per)} sensitivity_2026-11-10 attempts (list price $1.50 / $7.50 per 1M)")
    json.dump(summ, open(OUT / "plan_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1))


def stage_run(a):
    M = setup(); O, FC = M["O"], M["FC"]
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    import threading
    P = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = P[P.action.str.endswith("new call")].drop_duplicates("user_md5")
    if a.only:
        todo = todo[todo.user_md5.isin(a.only.split(","))]
    CALLS.mkdir(exist_ok=True)
    if (OUT / "HOLD").exists():
        sys.exit("HOLD present; not running")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); stop = threading.Event(); n = collections.Counter(); t0 = time.time()

    def one(c):
        if stop.is_set():
            return "skipped (hold)"
        f = CALLS / f"AE__{c.user_md5}.json"
        att = json.load(open(f))["attempts"] if f.exists() else []
        if any(x.get("complete") for x in att) or len(att) >= MAXTRY:
            return "cached"
        p = json.load(open(PROMPTS / f"AE__{c.user_md5}.json"))
        assert md5s(p["user"]) == p["user_md5"] == c.user_md5
        while len(att) < MAXTRY and not stop.is_set():
            r = dict(uid=p["uid"], obs={})
            try:
                parsed, raw = O.call(client, MODEL, dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
                rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], anchor=p["anchor"])
                rec["complete"] = FC.complete(rec, "A", p["need"])
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                rec = dict(status="error", error=msg[:2000], complete=False, usage=r.get("_usage"), user_md5=p["user_md5"])
                if BILL.search(msg):
                    stop.set(); (OUT / "HOLD").write_text(f"HOLD {time.strftime('%Y-%m-%dT%H:%M:%S')}: billing / spending-cap error; no key rotation\n")
            rec.update(uid=p["uid"], model=MODEL, thinking=THINKING, temperature=TEMP, seed=SEED, rules_md5=O.OBS_RULES_MD5, system_md5=p["system_md5"],
                       schema_md5=p["schema_md5"], media=None, cond="gen_tool_text", attempt=len(att) + 1, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
            att.append(rec); json.dump(dict(key=f"AE__{c.user_md5}", uid=p["uid"], attempts=att), open(f, "w"), default=str)
            if rec.get("complete") or (rec["status"] == "error" and BILL.search(rec.get("error", ""))):
                break
        return "ok" if att and att[-1].get("complete") else ("hold" if stop.is_set() else "unresolved")
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 10 == 0 or i + 1 == len(todo):
                print(f"[a-axis-v3] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), hold=stop.is_set(), time=time.strftime("%Y-%m-%dT%H:%M:%S")),
              open(OUT / f"run_info_{time.strftime('%H%M%S')}.json", "w"), indent=1)
    print("[DONE]", dict(n))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["features", "select_example", "plan", "run", "walkthrough", "score"])
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--only", default="", help="run: restrict to these user md5s (comma separated)")
    a = ap.parse_args()
    if a.stage in ("walkthrough", "score"):
        import a_axis_score as S
        getattr(S, f"stage_{a.stage}")(a, sys.modules[__name__])
    else:
        globals()[f"stage_{a.stage}"](a)
