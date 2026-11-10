#!/usr/bin/env python3
"""Full-dataset bidirectional gate (11/07): AVB evaluated; A and V coverage / reuse / call estimates only (no new A / V calls).
Writes only to runs/obsval_1028/bidir_full_1107/. Rules, payloads, prompt builder, model settings and calibration statuses are
imported unchanged from bidir_pilot_1106.py (RULES, family_of, branch_open, payload, calib_table; obs_judge_1028.build_call;
gemini-3.6-flash, thinking high, temperature 0, seed 42 via obs_judge_1028.call). No thresholds are retuned.
Units: every A / V / AVB event-level unit of units_all.csv (group == dataset) with row1 scored and GT-eligible (the stage-1
prerequisite), both split portions (portion recorded; the pilot rules were calibrated on the dev portion). No subsampling.
Baselines per condition with their own denominators: row1 media only, row2 one call plus tools, row4 always shown, row5 original gate.
Reuse: an existing call is reused only if status ok, the full user prompt md5 matches, OBS_RULES md5 matches, model gemini-3.6-flash
and thinking high (gen_tool_text cache and bidir_pilot_1106 calls).
The generated-video AVB PASS branch (zero offset on an anchor window) is kept and labelled EXPLORATORY: the Synchformer diagnostic
(sync_diag_round2_1106) found no FAIL / PASS separation for it.
  python gepa_stage2/bidir_full_1107.py plan              # no calls; all three axes
  python gepa_stage2/bidir_full_1107.py run --axis AVB    # new AVB calls only (A / V refused)
  python gepa_stage2/bidir_full_1107.py score --axis AVB
"""
import argparse, collections, hashlib, json, os, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import bidir_pilot_1106 as BP
OUT = HERE / "runs/obsval_1028/bidir_full_1107"
RUNS = HERE / "runs/obsval_1028"
DS, GROUP_OF, AXES, RULES = BP.DS, BP.GROUP_OF, BP.AXES, BP.RULES
COND = {"row1": "media only", "row2": "one call plus tools", "row4": "always shown", "row5": "original gate"}


def exploratory_flag(ds, axis, branch):
    if axis == "AVB" and branch == "PASS" and ds != "P03-P09":
        return "EXPLORATORY: generated-video zero-offset PASS (not verified evidence; Synchformer diagnostic AUC 0.43-0.52)"
    return ""


def payload(ds, ax, item, fam_by_event):
    """bidir_pilot_1106.payload unchanged, except 2k_25 AVB: the pilot function has no 2k_25 Synchformer source (no 2k_25 AVB unit
    opened in the pilot). Adapter: the original 2k_25 cache sync_obs_lines_gen2k25.json (gen2k25_stage2_1104.sync_lines), formatted
    exactly as gen_stage2_1030.avb_text ('Observation (tool output):' + lines)."""
    if ds == "2k_25 LTX" and ax == "AVB":
        import gen2k25_stage2_1104 as K
        t = K.sync_lines(item)
        return (None if t is None else "Observation (tool output):\n" + t), DS[ds][0]
    return BP.payload(ds, ax, item, fam_by_event)


def reuse_index():
    f = OUT / "reuse_index.json"
    if f.exists():
        return json.load(open(f))
    import obs_judge_1028 as O
    idx = {}
    for d in (RUNS / "calls/gen_tool_text", RUNS / "bidir_pilot_1106/calls"):
        for p in d.glob("*.json"):
            try:
                r = json.load(open(p))
            except Exception:
                continue
            if (r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5
                    and r.get("model", "") == "gemini-3.6-flash" and r.get("thinking", "") == "high"):
                idx.setdefault(r["user_md5"], str(p))
    json.dump(idx, open(f, "w")); return idx


def stage_plan(a):
    import obs_judge_1028 as O
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "manifest.csv").exists() and not a.replan:
        sys.exit("manifest.csv exists; use --replan to rebuild the plan files (calls are never touched)")
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False)
    U = U[(U.group == U.dataset) & U.dataset.isin(list(DS)) & U.axis.isin(AXES)]
    S = pd.read_csv(RUNS / "gate_pilot_1106/split.csv")
    piv = {c: U[U.cond == c].set_index(["dataset", "unit"]) for c in COND}
    b = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)].merge(S[["dataset", "item", "portion"]], on=["dataset", "item"], how="left")
    M = b.rename(columns={"gt_y": "gt", "pred": "initial"})[["axis", "dataset", "unit", "item", "event", "portion", "gt", "initial"]].copy()
    for c in ("row2", "row4", "row5"):
        p = piv[c]
        M[COND[c]] = [p.pred.get((d, u)) if p.status.get((d, u)) == "scored" else "" for d, u in zip(M.dataset, M.unit)]
    M = M.rename(columns={"one call plus tools": "one_call", "always shown": "always_shown", "original gate": "old_gated"})
    pil = set(zip(*[pd.read_csv(RUNS / "bidir_pilot_1106/manifest.csv")[c] for c in ("dataset", "unit")]))
    M["in_pilot"] = [(d, u) in pil for d, u in zip(M.dataset, M.unit)]
    M.to_csv(OUT / "manifest.csv", index=False)
    F = pd.read_csv(RUNS / "gate_redesign_round2/unit_features.csv", low_memory=False).drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"])
    cal = BP.calib_table(); cal.to_csv(OUT / "branch_calibration_frozen.csv", index=False)
    calst = {(r.axis_family, r.branch, r.group): r.status for r in cal.itertuples()}
    rows = []
    for m in M.itertuples():
        f = F.loc[(m.dataset, m.unit)] if (m.dataset, m.unit) in F.index else None
        fam = BP.family_of(m.axis, f); br = "FAIL" if m.initial == "yes" else "PASS"
        op = BP.branch_open(f, fam, br)
        rows.append(dict(axis=m.axis, dataset=m.dataset, unit=m.unit, item=m.item, event=m.event, portion=m.portion, group=GROUP_OF[m.dataset], family=fam, branch=br,
                         evidence_available=f is not None and fam is not None, opened=op, rule=RULES.get((fam, br), ("",))[0] if fam else "",
                         calibration_status=calst.get((fam, br, GROUP_OF[m.dataset]), "no evidence") if fam else "no evidence",
                         exploratory=exploratory_flag(m.dataset, m.axis, br)))
    P = pd.DataFrame(rows); P.to_csv(OUT / "plan_units.csv", index=False)
    idx = reuse_index(); calls = []; (OUT / "prompts").mkdir(exist_ok=True)
    for (ds, item, ax), g in P[P.opened].groupby(["dataset", "item", "axis"]):
        fam_by_event = {e: fm for e, fm in zip(g.event, g.family) if isinstance(e, str)}
        text, src = payload(ds, ax, item, fam_by_event)
        uid = f"{src}|{item}|{ax}"; key = uid.replace("/", "_")
        if text is None:
            calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="missing payload")); continue
        r = dict(set="BD1", source=src, uid=uid, item_id=item, axis=ax, variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text})
        cc = O.build_call(r)
        if cc is None:
            calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="no stage-1 anchor (no call possible)")); continue
        md5 = hashlib.md5(cc["user"].encode()).hexdigest()
        json.dump(dict(uid=uid, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5), open(OUT / "prompts" / f"{key}.json", "w"), indent=1)
        hit = idx.get(md5)
        calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, key=key, n_units=len(g), payload_source="2k_25 AVB adapter" if (ds == "2k_25 LTX" and ax == "AVB") else "bidir_pilot_1106.payload", branches="/".join(sorted(set(g.branch))),
                          exploratory="yes" if any(g.exploratory.astype(bool)) else "", user_md5=md5, prompt_chars=len(cc["system"]) + len(cc["user"]),
                          reuse_file=hit or "", action="reuse (exact prompt match)" if hit else "new call"))
    CP = pd.DataFrame(calls); CP.to_csv(OUT / "call_plan.csv", index=False)
    est = estimate(CP); est.to_csv(OUT / "call_estimate.csv", index=False)
    cov = P.groupby(["axis", "dataset", "family", "branch", "calibration_status", "exploratory"], dropna=False).agg(
        eligible=("unit", "size"), evidence=("evidence_available", "sum"), opened=("opened", "sum")).reset_index()
    cov["missing_evidence"] = cov.eligible - cov.evidence
    cov.to_csv(OUT / "gate_coverage.csv", index=False)
    frozen = dict(written=time.strftime("%Y-%m-%dT%H:%M:%S"), rules={f"{k[0]}|{k[1]}": v for k, v in RULES.items()}, model="gemini-3.6-flash", thinking="high",
                  temperature=0.0, seed=42, prompt="obs_judge_1028.build_call (OBS_RULES md5 %s)" % O.OBS_RULES_MD5, payload="bidir_pilot_1106.payload; 2k_25 AVB adapter (sync_obs_lines_gen2k25.json, same format as gen_stage2_1030.avb_text)",
                  calibration="bidir_pilot_1106.calib_table (round-2 development grid)", units="row1 scored, GT-eligible, group == dataset, both portions",
                  pilot_md5=hashlib.md5(open(HERE / "bidir_pilot_1106.py").read().encode()).hexdigest(),
                  full_md5=hashlib.md5(open(__file__).read().encode()).hexdigest(), reuse_requirements="status ok, user_md5, rules_md5, model, thinking")
    json.dump(frozen, open(OUT / "frozen_config.json", "w"), indent=1)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
    print(P.groupby(["axis", "dataset", "branch"]).agg(eligible=("unit", "size"), opened=("opened", "sum")).to_string())
    print(est.to_string(index=False))


def estimate(CP):
    """tokens per new call: input = prompt chars / chars-per-token (calibrated on bidir_pilot_1106 calls), output = pilot median."""
    ratios, outs, walls = [], [], []
    for f in (RUNS / "bidir_pilot_1106/calls").glob("*.json"):
        r = json.load(open(f)); u = r.get("usage") or {}
        p = RUNS / "bidir_pilot_1106/prompts" / (f.stem.split("__", 1)[1] + ".json")
        if u.get("prompt_token_count") and p.exists():
            pr = json.load(open(p)); ratios.append((len(pr["system"]) + len(pr["user"])) / u["prompt_token_count"])
            outs.append((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)); walls.append(r.get("wall_s") or 0)
    cpt, out_med, wall_med = float(np.median(ratios)), float(np.median(outs)), float(np.median(walls))
    rows = []
    for (ax, ds, act), g in CP.groupby(["axis", "dataset", "action"]):
        n = len(g); tin = float(g.prompt_chars.fillna(0).sum() / cpt) if act == "new call" else 0.0; tout = out_med * n if act == "new call" else 0.0
        rows.append(dict(axis=ax, dataset=ds, action=act, calls=n, units=int(g.n_units.sum()), est_input_tokens=int(tin), est_output_tokens=int(tout),
                         est_usd_list=round(tin / 1e6 * 1.5 + tout / 1e6 * 7.5, 2), est_wall_min_4workers=round(n * wall_med / 4 / 60, 1) if act == "new call" else 0.0))
    E = pd.DataFrame(rows)
    E.attrs = dict(chars_per_token=cpt, out_median=out_med, wall_median=wall_med)
    json.dump(dict(chars_per_token=round(cpt, 2), output_tokens_median=out_med, wall_s_median=wall_med, n_pilot_calls=len(ratios)), open(OUT / "estimate_basis.json", "w"), indent=1)
    return E


def stage_run(a):
    import obs_judge_1028 as O
    from google import genai
    if a.axis != "AVB":
        sys.exit("only AVB is approved for new calls")
    CP = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = CP[(CP.action == "new call") & (CP.axis == a.axis)]
    (OUT / "calls").mkdir(exist_ok=True)
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); t0 = time.time(); n = collections.Counter()

    def one(c):
        f = OUT / "calls" / f"BF1__{c.key}.json"
        if f.exists():
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.key}.json")); r = dict(uid=c.uid, obs={})
        try:
            parsed, raw = O.call(client, "gemini-3.6-flash", dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
            rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"],
                       anchor=O.anchor_entries(c.uid.split("|")[0], c.item, c.axis))
        except Exception as e:
            rec = dict(status="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        rec.update(uid=c.uid, model="gemini-3.6-flash", thinking="high", rules_md5=O.OBS_RULES_MD5, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(f, "w"), default=str); return rec["status"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 25 == 0 or i + 1 == len(todo):
                print(f"[full {a.axis}] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(axis=a.axis, calls=dict(n), wall_s=round(time.time() - t0, 1), workers=a.workers), open(OUT / f"run_info_{a.axis}.json", "w"), indent=1)


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p); o = dict(n=len(y), acc=round(float((y == p).mean()), 3) if len(y) else None)
    for lab, nm in (("no", "FAIL"), ("yes", "PASS")):
        tp = int(((p == lab) & (y == lab)).sum()); pp = int((p == lab).sum()); ap = int((y == lab).sum())
        pr, rc = (tp / pp if pp else None), (tp / ap if ap else None)
        o[f"{nm}_P"], o[f"{nm}_R"] = (round(pr, 3) if pr is not None else None), (round(rc, 3) if rc is not None else None)
        o[f"{nm}_F1"] = round(2 * pr * rc / (pr + rc), 3) if pr and rc else (0.0 if ap else None)
    o["macro_F1"] = round((o["FAIL_F1"] + o["PASS_F1"]) / 2, 3) if o["FAIL_F1"] is not None and o["PASS_F1"] is not None else None
    o["bal_acc"] = round((o["FAIL_R"] + o["PASS_R"]) / 2, 3) if o["FAIL_R"] is not None and o["PASS_R"] is not None else None
    gp = y == "yes"; o["FA"] = f"{int(((p == 'no') & gp).sum())}/{int(gp.sum())}"
    return o


def stage_score(a):
    import audit_1106 as AU, obs_judge_1028 as O
    M = pd.read_csv(OUT / "manifest.csv"); P = pd.read_csv(OUT / "plan_units.csv"); CP = pd.read_csv(OUT / "call_plan.csv").fillna("")
    M, P = M[M.axis == a.axis], P[P.axis == a.axis]
    X = P.merge(M[["dataset", "unit", "gt", "initial", "one_call", "always_shown", "old_gated", "in_pilot"]], on=["dataset", "unit"])
    cmap = {(r.dataset, r.item, r.axis): r for r in CP.itertuples()}; lab, src = [], []
    for x in X.itertuples():
        if not x.opened:
            lab.append(x.initial); src.append("closed: media-only label"); continue
        c = cmap.get((x.dataset, x.item, x.axis)); rec = None
        if c is not None and c.action in ("new call", "reuse (exact prompt match)"):
            f = Path(c.reuse_file) if c.action.startswith("reuse") else OUT / "calls" / f"BF1__{c.key}.json"
            rec = json.load(open(f)) if f.exists() else None
            if rec is not None and "anchor" not in rec:
                rec["anchor"] = O.anchor_entries(c.uid.split("|")[0], x.item, x.axis)
        rec = rec if rec and rec.get("status") == "ok" else None
        l, st = AU.s2_event(rec, x.axis, x.event if isinstance(x.event, str) else None)
        ok = st == "ok" and l in ("yes", "no")
        lab.append(l if ok else ""); src.append(("open: reused call" if c is not None and c.action.startswith("reuse") else "open: new call") if ok else f"open: missing ({st}; {getattr(c, 'action', 'no call')})")
    X["bidir"] = lab; X["label_source"] = src; X.to_csv(OUT / f"unit_results_{a.axis}.csv", index=False)
    pipes = (("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("old_gated", "original gate"), ("bidir", "bidirectional gate"))
    rows = []
    for keys, q in list(X.groupby(["dataset", "portion"])) + [((d, "all"), g) for d, g in X.groupby("dataset")]:
        for col, nm in pipes:
            h = q[q[col].isin(["yes", "no"])]
            rows.append(dict(dataset=keys[0], portion=keys[1], pipeline=nm, eligible=len(q), excluded=len(q) - len(h), **metrics(h["gt"], h[col])))
    pd.DataFrame(rows).to_csv(OUT / f"metrics_condition_specific_{a.axis}.csv", index=False)
    rows = []
    for keys, q in list(X.groupby(["dataset", "portion", "branch"])) + [((d, "all", b), g) for (d, b), g in X.groupby(["dataset", "branch"])]:
        for ref, nm in pipes[:4]:
            v = q[q.bidir.isin(["yes", "no"]) & q[ref].isin(["yes", "no"])]
            o_, n_ = v[ref] == v["gt"], v.bidir == v["gt"]; vo = v[v.opened]
            rows.append(dict(dataset=keys[0], portion=keys[1], branch=keys[2], vs=nm, common_units=len(v), opened_common=len(vo),
                             exploratory=exploratory_flag(keys[0], a.axis, keys[2]),
                             bidir_correct=int(n_.sum()), ref_correct=int(o_.sum()), bidir_right_ref_wrong=int((~o_ & n_).sum()), bidir_wrong_ref_right=int((o_ & ~n_).sum()),
                             of_which_opened_W_R=int(((vo[ref] != vo["gt"]) & (vo.bidir == vo["gt"])).sum()), of_which_opened_R_W=int(((vo[ref] == vo["gt"]) & (vo.bidir != vo["gt"])).sum())))
    pd.DataFrame(rows).to_csv(OUT / f"paired_common_units_{a.axis}.csv", index=False)
    usage = [json.load(open(f)).get("usage") or {} for f in (OUT / "calls").glob("BF1__*.json")]
    ti = sum(u.get("prompt_token_count") or 0 for u in usage); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in usage)
    json.dump(dict(new_calls=len(usage), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3)), open(OUT / f"cost_{a.axis}.json", "w"), indent=1)
    print(X.label_source.str.replace(r"\(.*", "", regex=True).value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["plan", "run", "score"]); ap.add_argument("--axis", default="AVB")
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--replan", action="store_true")
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
