#!/usr/bin/env python3
"""Alpha sensitivity of the empirical evidence-admission limit (2026-11-10), for AVT-Judge (combined gated two-stage) and Gate-only
(direct-combined decision). Writes only eval_results/analysis/sensitivity_2026-11-10/.
Selection: p12_calib_1108.select_family / stat_row / the stage_select logic, unchanged except ALPHA, on the corrected P01/P02 calibration
population (final_benchmark_1108/calibration_v2/p12_calibration_units.csv; 39 restored AVB judgments). MIN_N (20), candidate families,
objective (max admission of initially incorrect units) and tie-breaking unchanged. alpha = .05 must reproduce calibration_v2.
Fixed choices: FLAM (A sound) and Synchformer (AVB) thresholds reselected per alpha; caption predicates contradicts / describes active only
if they meet alpha with risk denominator >= 20; Whisper word-presence speech rule (original gate, inherited) unchanged; TC / TR closed;
branches without a useful feasible rule stay closed (media-only label).
Evaluation: same openings for both variants. Gate-only = admitted direction (opened initial PASS -> FAIL, opened initial FAIL -> PASS; A speech
= direct-original speech mapping of sanjoy_two_baselines). AVT-Judge = unchanged text-only reconsideration call (final_benchmark_1108.comb_call:
bidirectional payload + obs_judge_1028.build_call; gemini-3.6-flash, thinking high, temperature 0, seed 42); A speech = original-gate label.
  python scripts/alpha_sensitivity.py calib | reproduce | plan | run | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, copy, glob, hashlib, json, os, re, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path((_tp.WORKSPACE))
GS = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2"   # portable: code dir of this checkout
sys.path.insert(0, str(GS)); sys.path.insert(0, str(GS.parent))
FBD = GS / "runs/obsval_1028/final_benchmark_1108"
SAN = ROOT / "eval_results/analysis/sanjoy_two_baselines_2026-11-08"
OUT = _tp.out_dir("sensitivity_2026-11-10")   # portable: $T2AV_OUT_DIR/<name>
CALLS, PROMPTS = OUT / "calls", OUT / "prompts"
ALPHAS = {"a01": 0.01, "a05": 0.05, "a10": 0.10}
MODEL, MAXTRY = "gemini-3.6-flash", 3
BILL = re.compile(r"spending cap|billing|exceeded its monthly", re.I)
KNOWN_FAIL = {"183efa72e2d529d31e6f4566f969926d"}      # old-MOVA slap V prompt: never retried
_M = {}


def cfg_path(tag):
    return OUT / "configs" / tag / "frozen_config.json"


# ------------------------------------------------------------------ calibration (P01/P02 only)
def select_one(alpha):
    import p12_calib_1108 as P12
    P12.ALPHA = alpha
    U = pd.read_csv(FBD / "calibration_v2/p12_calibration_units.csv", low_memory=False)
    out, allsets = {}, []
    for fam, ax, init in (("A_FAIL", "A sound", "yes"), ("A_PASS", "A sound", "no"), ("AVB_FAIL", "AVB", "yes"), ("AVB_PASS", "AVB", "no")):
        q, risk = P12.fam_rows(U, ax, init)
        S, sel = P12.select_family(q, risk, fam); out[fam] = sel; allsets.append(S.assign(family=fam))
    for fam, init, verdict in (("V_FAIL", "yes", "contradicts"), ("V_PASS", "no", "describes")):
        q, risk = P12.fam_rows(U, "V", init); s = P12.stat_row(f"verdict {verdict}", q.vcap == verdict, risk)
        s["status"] = (f"INSUFFICIENT SUPPORT (risk denominator {s['n_risk']}, initially incorrect {s['n_use']})" if s["n_risk"] < P12.MIN_N or s["n_use"] == 0
                       else ("MEETS CRITERION" if s["risk_rate"] <= alpha else f"FAILS CRITERION ({s['k_risk']}/{s['n_risk']} = {s['risk_rate']})"))
        out[fam] = s
    for fam in ("A_SPEECH_FAIL (Whisper absence)", "A_SPEECH_PASS (word heard, p >= .5)"):
        out[fam] = dict(status="UNSUPPORTED: no P01/P02 speech events (HD-EPIC has no speech); branch falls back to media only", n_risk=0, n_use=0)
    cfg = {}
    for fam, s in out.items():
        use = s["status"].startswith(("USABLE", "MEETS"))
        cfg[fam] = dict(active=use, params=s.get("params"), status=s["status"], fallback=None if use else "media-only label")
    P12.ALPHA = 0.05
    return cfg, out, pd.concat(allsets)


def compliance(sel, sets, alpha):
    """integer / unrounded check of every selected or active rule, and of the rounded-rate feasibility filter."""
    rows = []
    for fam, s in sel.items():
        if "k_risk" not in s or s.get("n_risk") in (None, 0):
            continue
        k, n = int(s["k_risk"]), int(s["n_risk"])
        rows.append(dict(family=fam, status=s["status"], params=str(s.get("params")), k_risk=k, n_risk=n, exact_rate=k / n, stored_rounded_rate=s.get("risk_rate"),
                         exact_le_alpha=k <= alpha * n + 1e-12, rounded_le_alpha=(s.get("risk_rate") or 0) <= alpha,
                         discrepancy=(k <= alpha * n + 1e-12) != ((s.get("risk_rate") or 0) <= alpha)))
    S = sets.copy()
    S["exact_feasible"] = [int(k) <= alpha * int(n) + 1e-12 if n else False for k, n in zip(S.k_risk, S.n_risk)]
    S["rounded_feasible"] = S.risk_rate <= alpha
    disc = S[S.exact_feasible != S.rounded_feasible]
    return pd.DataFrame(rows), disc


def stage_calib(a):
    for tag, alpha in ALPHAS.items():
        d = cfg_path(tag).parent; d.mkdir(parents=True, exist_ok=True)
        if cfg_path(tag).exists():
            print(tag, "frozen config exists; kept"); continue
        cfg, sel, sets = select_one(alpha)
        C, disc = compliance(sel, sets, alpha)
        sets.to_csv(d / "enumerated_admission_sets.csv", index=False); C.to_csv(d / "constraint_compliance.csv", index=False)
        disc.to_csv(d / "rounding_discrepancies_in_candidate_sets.csv", index=False)
        json.dump(dict(written=time.strftime("%Y-%m-%dT%H:%M:%S"), alpha=alpha, calibration="HD-EPIC P01/P02 only (corrected population, calibration_v2 units)",
                       config=cfg, selection=sel, p12_script_md5=hashlib.md5(open(GS / "p12_calib_1108.py", "rb").read()).hexdigest(),
                       units_md5=hashlib.md5(open(FBD / "calibration_v2/p12_calibration_units.csv", "rb").read()).hexdigest(),
                       this_script_md5=hashlib.md5(open(__file__, "rb").read()).hexdigest(), evaluation_rows_read=False,
                       fixed_choices=dict(whisper_speech="original-gate word-presence rule, unchanged (not calibrated on P01/P02)", tc_tr="closed",
                                          caption="fixed predicates contradicts / describes, active only if they meet alpha with n_risk >= 20",
                                          no_feasible_rule="branch closed (media-only label)")),
                  open(cfg_path(tag), "w"), indent=1, default=str)
        print(tag, {k: (v["active"], v["params"]) for k, v in cfg.items()}, "| rounding discrepancies in candidate sets:", len(disc))


# ------------------------------------------------------------------ shared
def setup():
    if not _M:
        import final_benchmark_1108 as FB
        M = FB.setup(); _M.update(M); _M["FB"] = FB
    return _M


def universe():
    U = pd.read_csv(FBD / "unit_results_final.csv", low_memory=False)
    S = pd.read_csv(SAN / "results/unit_predictions.csv", low_memory=False).set_index(["dataset", "unit"])
    U["direct_comb_ref"] = [S.direct_comb.get((d, u)) for d, u in zip(U.dataset, U.unit)]
    U["direct_orig_ref"] = [S.direct_orig.get((d, u)) for d, u in zip(U.dataset, U.unit)]
    U["a_kind"] = U.a_kind.fillna("")
    return U


def openings(U, cfg):
    import p12_calib_1108 as P12
    res = [P12.open_rule(cfg, r) if r.scored_row1 else (False, "", "no media-only label") for r in U.itertuples()]
    return [x[0] for x in res], [x[1] for x in res]


def bad_md5():
    out = set(KNOWN_FAIL)
    for base in (FBD / "calls", GS / "runs/obsval_1028/final_cov_1108/calls", CALLS):
        for p in base.glob("*.json") if base.exists() else []:
            att = json.load(open(p))["attempts"]
            if len(att) >= MAXTRY and not any(x.get("complete") for x in att):
                m = p.stem.split("__", 1)[1] if p.stem.startswith(("NB__", "FC__", "AS__")) else None
                if m:
                    out.add(m)
                out |= {x.get("user_md5") for x in att if x.get("user_md5")}
    return out


def reuse_idx():
    M = setup(); idx = M["FB"].reuse_index()
    for p in CALLS.glob("AS__*.json") if CALLS.exists() else []:
        att = [x for x in json.load(open(p))["attempts"] if x.get("complete")]
        if att:
            idx.setdefault(att[-1]["user_md5"], ("attempts", str(p)))
    return idx


def judge_labels(U, cfg, op, idx):
    """AVT-Judge labels for one alpha, same openings op; mirrors final_benchmark_1108.comb_labels."""
    M = setup(); AU, FB = M["AU"], M["FB"]
    cache, lab, src, req = {}, [], [], []
    opened = U[np.array(op)]
    groups = {k: sorted(set(g.event)) for k, g in opened.groupby(["dataset", "item", "axis"])}
    for x, o in zip(U.to_dict("records"), op):
        if not x["scored_row1"]:
            lab.append(""); src.append("no media-only label"); req.append(""); continue
        if x["family"] == "A speech":
            lab.append(x["original_gate"] if isinstance(x["original_gate"], str) else ""); src.append("A speech: original gate (Whisper word presence; unchanged)"); req.append(""); continue
        if not o:
            lab.append(x["initial"]); src.append("closed: media-only label"); req.append(""); continue
        k = (x["dataset"], x["item"], x["axis"])
        if k not in cache:
            cc, uid, why = FB.comb_call(k[0], k[1], k[2], groups[k]); rec, md5 = None, ""
            if cc is not None:
                md5 = hashlib.md5(cc["user"].encode()).hexdigest(); h = idx.get(md5)
                rec = FB.load_idx(h) if h else None
                if rec is not None:
                    rec = dict(rec); rec.setdefault("anchor", cc["anchor"])
            cache[k] = (rec, md5, cc, why)
        rec, md5, cc, why = cache[k]
        l, st = AU.s2_event(rec, x["axis"], x["event"])
        ok = st == "ok" and l in ("yes", "no")
        lab.append(l if ok else ""); src.append("open: stage-2 label" if ok else f"open: missing ({st}{'; ' + why if why else ''})"); req.append(md5)
    return lab, src, req, cache


def gate_only_labels(U, op):
    out = []
    for x, o in zip(U.to_dict("records"), op):
        if not x["scored_row1"]:
            out.append("")
        elif x["family"] == "A speech":
            out.append(x["direct_orig_ref"])                     # Whisper word-presence direct mapping, unchanged across alpha
        elif o:
            out.append("no" if x["initial"] == "yes" else "yes")
        else:
            out.append(x["initial"])
    return out


# ------------------------------------------------------------------ reproduce alpha = .05
def stage_reproduce(a):
    U = universe()
    v2 = json.load(open(FBD / "calibration_v2/frozen_p12_config.json")); new = json.load(open(cfg_path("a05")))
    rep = {}
    rep["config_identical_to_calibration_v2"] = {fam: (v2["config"][fam]["params"] == new["config"][fam]["params"] and v2["config"][fam]["status"] == new["config"][fam]["status"]
                                                        and v2["config"][fam]["active"] == new["config"][fam]["active"]) for fam in v2["config"]}
    rep["selection_counts_identical"] = {fam: all(str(v2["selection"][fam].get(k)) == str(new["selection"][fam].get(k)) for k in ("opened", "k_risk", "n_risk", "k_use", "n_use"))
                                         for fam in v2["selection"] if "diagnostic" not in fam}
    op, _ = openings(U, new["config"])
    ns = U.scored_row1 & (U.family != "A speech")
    stored = U.comb_opened_v2.astype(bool)
    rep["openings_mismatch_non_speech"] = int((np.array(op)[ns.values] != stored[ns].values).sum())
    idx = reuse_idx()
    lab, src, req, _ = judge_labels(U, new["config"], op, idx)
    rep["AVT-Judge labels identical to stored combined (all GT-eligible units)"] = f"{int((pd.Series(lab).fillna('').values == U.combined.fillna('').values).sum())} / {len(U)}"
    g = gate_only_labels(U, op)
    rep["Gate-only labels identical to stored direct_comb"] = f"{int((pd.Series(g).fillna('').values == U.direct_comb_ref.fillna('').values).sum())} / {len(U)}"
    json.dump(rep, open(OUT / "reproduction_alpha05.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))


# ------------------------------------------------------------------ plan / run
def stage_plan(a):
    U = universe(); idx = reuse_idx(); bad = bad_md5(); PROMPTS.mkdir(exist_ok=True)
    rows = []
    b = json.load(open(GS / "runs/obsval_1028/bidir_full_1107/estimate_basis.json"))
    for tag in ("a01", "a10", "a05"):
        cfg = json.load(open(cfg_path(tag)))["config"]; op, bk = openings(U, cfg)
        lab, src, req, cache = judge_labels(U, cfg, op, idx)
        for (ds, item, ax), (rec, md5, cc, why) in cache.items():
            if rec is not None:
                act = "reuse (identical complete request)"
            elif cc is None:
                act = f"no call possible ({why})"
            elif md5 in bad:
                act = "unresolved earlier (repeatedly failing prompt); not retried"
            else:
                act = "new call"
                if not (PROMPTS / f"AS__{md5}.json").exists():
                    json.dump(dict(uid=f"{ds}|{item}|{ax}", item=item, axis=ax, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5,
                                   anchor=cc["anchor"], need=sorted(set(U[(U.dataset == ds) & (U["item"] == item) & (U.axis == ax) & np.array(op)].event))),
                              open(PROMPTS / f"AS__{md5}.json", "w"))
            rows.append(dict(alpha=tag, dataset=ds, item=item, axis=ax, user_md5=md5, prompt_chars=(len(cc["system"]) + len(cc["user"])) if cc else 0, action=act))
    P = pd.DataFrame(rows); P.to_csv(OUT / "call_plan.csv", index=False)
    new = P[P.action == "new call"].drop_duplicates("user_md5")
    us = [u for f in glob.glob(str(FBD / "calls/NB__*.json")) for x in json.load(open(f))["attempts"] for u in [x.get("usage") or {}] if u.get("prompt_token_count")]
    per = [(u["prompt_token_count"] * 1.5 + ((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)) * 7.5) / 1e6 for u in us]
    q = np.percentile(per, [25, 50, 75]) if per else [np.nan] * 3
    summ = dict(by_alpha=P.groupby(["alpha", "action"]).size().rename("n").reset_index().to_dict("records"), unique_new_calls=len(new),
                est_usd_median=round(len(new) * q[1], 2), est_usd_iqr=[round(len(new) * q[0], 2), round(len(new) * q[2], 2)], basis=f"{len(per)} final_benchmark_1108 stage-2 records")
    json.dump(summ, open(OUT / "plan_summary.json", "w"), indent=1, default=str)
    print(json.dumps(summ, indent=1, default=str))


def stage_run(a):
    M = setup(); O, FC = M["O"], M["FC"]
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    import threading
    P = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = P[P.action == "new call"].drop_duplicates("user_md5")
    CALLS.mkdir(exist_ok=True)
    if (OUT / "HOLD").exists():
        sys.exit("HOLD present")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); stop = threading.Event(); n = collections.Counter(); t0 = time.time()

    def one(c):
        if stop.is_set():
            return "skipped (hold)"
        f = CALLS / f"AS__{c.user_md5}.json"
        att = json.load(open(f))["attempts"] if f.exists() else []
        if any(x.get("complete") for x in att) or len(att) >= MAXTRY:
            return "cached"
        p = json.load(open(PROMPTS / f"AS__{c.user_md5}.json"))
        while len(att) < MAXTRY and not stop.is_set():
            r = dict(uid=p["uid"], obs={})
            try:
                parsed, raw = O.call(client, MODEL, dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
                rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], anchor=p["anchor"])
                rec["complete"] = FC.complete(rec, p["axis"], p["need"])
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                rec = dict(status="error", error=msg[:2000], complete=False, usage=r.get("_usage"), user_md5=p["user_md5"])
                if BILL.search(msg):
                    stop.set(); (OUT / "HOLD").write_text(f"HOLD {time.strftime('%Y-%m-%dT%H:%M:%S')}: billing / spending-cap error; no key rotation\n")
            rec.update(uid=p["uid"], model=MODEL, thinking="high", rules_md5=O.OBS_RULES_MD5, attempt=len(att) + 1, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
            att.append(rec); json.dump(dict(key=f"AS__{c.user_md5}", uid=p["uid"], attempts=att), open(f, "w"), default=str)
            if rec.get("complete") or (rec["status"] == "error" and BILL.search(rec.get("error", ""))):
                break
        return "ok" if att and att[-1].get("complete") else ("hold" if stop.is_set() else "unresolved")
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 25 == 0 or i + 1 == len(todo):
                print(f"[alpha-sens] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), hold=stop.is_set(), time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(OUT / f"run_info_{time.strftime('%H%M%S')}.json", "w"), indent=1)
    print("[DONE]", dict(n))


# ------------------------------------------------------------------ score
def metrics(y, p):
    import comprehensive_report_1108 as CR
    return CR.metrics(y, p)


def stage_score(a):
    U = universe(); idx = reuse_idx()
    cat_init = U.initial_cat
    labs, branch_rows = {}, []
    S6 = pd.read_csv(FBD / "subset_manifests.csv"); S6 = S6[S6.subset == "six-method common"]
    for tag in ("a01", "a05", "a10"):
        cfg = json.load(open(cfg_path(tag)))["config"]; op, bk = openings(U, cfg)
        lab, src, req, _ = judge_labels(U, cfg, op, idx)
        U[f"open_{tag}"] = op; U[f"branch_{tag}"] = bk
        U[f"judge_{tag}"] = lab; U[f"judge_{tag}_source"] = src; U[f"judge_{tag}_request_md5"] = req
        U[f"gate_{tag}"] = gate_only_labels(U, op)
        for c in (f"judge_{tag}", f"gate_{tag}"):
            U[c + "_cat"] = ["answered" if v in ("yes", "no") else (ic if ic != "answered" else "technical missing / failed output") for v, ic in zip(U[c], cat_init)]
    U["initial_cat2"] = U.initial_cat
    keep = ["dataset", "batch", "group", "axis", "a_kind", "unit", "item", "event", "gt", "initial", "original_gate", "combined", "direct_comb_ref", "family", "flam_max", "vcap",
            "off", "prob", "scored_row1", "initial_cat"] + [c for c in U.columns if c.startswith(("open_a", "branch_a", "judge_a", "gate_a"))]
    (OUT / "results").mkdir(exist_ok=True)
    U[keep].to_csv(OUT / "results/unit_labels_openings.csv", index=False)
    T = U.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind; T = pd.concat([T, TA], ignore_index=True)
    fixed_ids = set(zip(S6.group, S6.axis_view, S6.dataset, S6.unit))
    T["in_fixed_common"] = [(g, a, d, u) in fixed_ids for g, a, d, u in zip(T.group, T.axis_view, T.dataset, T.unit)]
    T[T.in_fixed_common][["group", "axis_view", "dataset", "unit"]].to_csv(OUT / "results/fixed_common_subset_ids.csv", index=False)
    meth = [("initial", "MLLM-only", "-")] + [(f"{v}_{t}", f"{nm}", t) for t in ("a01", "a05", "a10") for v, nm in (("judge", "AVT-Judge"), ("gate", "Gate-only"))]
    rows, pc, br = [], [], []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        fc = q[q.in_fixed_common]
        for c, nm, t in meth:
            b = dict(dataset=g, axis=ax, method=nm, alpha={"a01": 0.01, "a05": 0.05, "a10": 0.10}.get(t, np.nan))
            ans_fc = fc[fc[c].isin(["yes", "no"])]
            rows.append(dict(b, view="primary: fixed six-method common subset", fixed_subset_size=len(fc), missing_in_fixed_subset=len(fc) - len(ans_fc), **metrics(ans_fc["gt"], ans_fc[c])))
            val = q[q[c].isin(["yes", "no"])]
            rows.append(dict(b, view="per-method answered", coverage=len(val) / len(q) if len(q) else np.nan, **metrics(val["gt"], val[c])))
            cat = q[c + "_cat"] if c != "initial" else q.initial_cat; ok = q[c].isin(["yes", "no"])
            rows.append(dict(b, view="fixed GT-eligible denominator", gt_eligible=len(q), N=int(ok.sum()), correct=int((ok & (q[c] == q["gt"])).sum()),
                             accuracy=(ok & (q[c] == q["gt"])).sum() / len(q) if len(q) else np.nan, coverage=ok.mean() if len(q) else np.nan,
                             model_prerequisite_skip=int((cat == "model prerequisite skip").sum()), technical_missing_failed=int((cat == "technical missing / failed output").sum())))
            if c != "initial":
                h = fc[fc[c].isin(["yes", "no"]) & fc.initial.isin(["yes", "no"])]
                ini, fin, y = h.initial, h[c], h["gt"]
                pc.append(dict(b, subset="fixed common", units=len(h), corrections=int(((ini != y) & (fin == y)).sum()), corruptions=int(((ini == y) & (fin != y)).sum()),
                               net=int(((ini != y) & (fin == y)).sum() - ((ini == y) & (fin != y)).sum()), revised=int((ini != fin).sum()),
                               PASS_to_FAIL=int(((ini == "yes") & (fin == "no")).sum()), FAIL_to_PASS=int(((ini == "no") & (fin == "yes")).sum())))
        if ax in ("A sounding", "V", "AVB", "A speech"):
            s = q[q.scored_row1]
            for t in ("a01", "a05", "a10"):
                for bname, h in s.groupby(f"branch_{t}"):
                    if not bname:
                        continue
                    o = h[h[f"open_{t}"].astype(bool)]
                    br.append(dict(dataset=g, axis=ax, alpha=t, branch=bname, test_units=len(h), test_opened=len(o), test_admission_rate=len(o) / len(h) if len(h) else np.nan,
                                   opened_initially_correct=int((o.initial == o["gt"]).sum()), opened_initially_wrong=int((o.initial != o["gt"]).sum())))
    R = pd.DataFrame(rows); P = pd.DataFrame(pc); B = pd.DataFrame(br)
    (OUT / "tables").mkdir(exist_ok=True)
    R.to_csv(OUT / "tables/metrics_all_views.csv", index=False, float_format="%.17g"); P.to_csv(OUT / "tables/corrections_corruptions.csv", index=False)
    B.to_csv(OUT / "tables/test_admission_by_branch.csv", index=False)
    calib_table(); summary(R, P); perturbation(U); cost(); latex(R)


def calib_table():
    rows = []
    for tag in ("a01", "a05", "a10"):
        c = json.load(open(cfg_path(tag)))
        for fam, s in c["selection"].items():
            if "diagnostic" in fam:
                continue
            rows.append(dict(alpha=c["alpha"], branch=fam, active=c["config"][fam]["active"], status=s.get("status"), rule=str(c["config"][fam]["params"]),
                             calib_opened=s.get("opened"), correct_admitted=s.get("k_risk"), correct_support=s.get("n_risk"),
                             correct_admission_rate_exact=(int(s["k_risk"]) / int(s["n_risk"])) if s.get("n_risk") not in (None, 0, "0") and s.get("k_risk") is not None else np.nan,
                             incorrect_admitted=s.get("k_use"), incorrect_support=s.get("n_use"),
                             incorrect_admission_rate_exact=(int(s["k_use"]) / int(s["n_use"])) if s.get("n_use") not in (None, 0, "0") and s.get("k_use") is not None else np.nan))
    C = pd.DataFrame(rows); C.to_csv(OUT / "tables/calibration_branches.csv", index=False, float_format="%.17g")
    for tag in ("a01", "a05", "a10"):
        cc = pd.read_csv(cfg_path(tag).parent / "constraint_compliance.csv"); cc.insert(0, "alpha", tag)
        cc.to_csv(OUT / f"tables/constraint_compliance_{tag}.csv", index=False, float_format="%.17g")


def summary(R, P):
    K = ["accuracy", "macro_F1", "balanced_accuracy", "FAIL_recall", "FAIL_precision", "PASS_recall", "FA_count"]
    p = R[(R.view == "primary: fixed six-method common subset") & R.method.isin(["AVT-Judge", "Gate-only"])]
    rows = []
    for (g, ax, m), q in p.groupby(["dataset", "axis", "method"]):
        ref = q[q.alpha == 0.05].iloc[0]
        for r in q.itertuples():
            d = dict(dataset=g, axis=ax, method=m, alpha=r.alpha, N=r.N, missing_in_fixed_subset=r.missing_in_fixed_subset)
            same = True
            for k in K:
                v, v0 = getattr(r, k), ref[k]
                d[k] = v; d[k + "_delta_vs_05"] = (v - v0) if not (pd.isna(v) or pd.isna(v0)) else np.nan
                same &= (pd.isna(v) and pd.isna(v0)) or (not pd.isna(v) and not pd.isna(v0) and abs(v - v0) < 1e-15)
            d["unchanged_vs_05"] = bool(same) if r.alpha != 0.05 else "reference"
            rows.append(d)
    pd.DataFrame(rows).to_csv(OUT / "tables/summary_alpha_with_deltas.csv", index=False, float_format="%.17g")


def perturbation(U):
    A = pd.read_csv(FBD / "units_all_conditions.csv", low_memory=False)
    var = A[A.cond == "row1"].drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"]).variant
    p = U[(U.group == "P03-P09") & U.scored_row1].copy()
    p["variant"] = [var.get((d, u)) for d, u in zip(p.dataset, p.unit)]
    import section6_1106 as S6
    p["k"] = [S6.kind(type("R", (), dict(axis=r.axis, variant=r.variant, item=r.item, y=r.gt))()) for r in p.itertuples()]
    rows = []
    for k in S6.ORDER:
        q = p[p.k == k]
        for c, nm in [("initial", "MLLM-only")] + [(f"{v}_{t}", f"{nm2} alpha={a}") for t, a in (("a01", .01), ("a05", .05), ("a10", .10)) for v, nm2 in (("judge", "AVT-Judge"), ("gate", "Gate-only"))]:
            h = q[q[c].isin(["yes", "no"])]
            rows.append(dict(row_type=k, method=nm, N=len(h), predicted_FAIL=int((h[c] == "no").sum()), predicted_FAIL_share=(h[c] == "no").mean() if len(h) else np.nan))
    pd.DataFrame(rows).to_csv(OUT / "tables/perturbation_breakdown_P03_P09.csv", index=False, float_format="%.17g")


def cost():
    us, n = [], 0
    for f in CALLS.glob("*.json") if CALLS.exists() else []:
        n += 1; us += [x.get("usage") or {} for x in json.load(open(f))["attempts"]]
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    unres = [json.load(open(f))["uid"] for f in CALLS.glob("*.json") if not any(x.get("complete") for x in json.load(open(f))["attempts"])] if CALLS.exists() else []
    json.dump(dict(AVT_Judge_new_requests=n, attempts=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3),
                   unresolved=unres, Gate_only_new_calls=0), open(OUT / "results/cost_new_calls.json", "w"), indent=1)


def latex(R):
    p = R[R.view == "primary: fixed six-method common subset"]
    lines = [r"% Alpha sensitivity (fixed six-method common subset); bal. acc. / FAIL recall. Observed calibration admission rates, not test guarantees.",
             r"\begin{tabular}{ll" + "c" * 7 + "}", r"\toprule",
             r"Dataset & Axis & MLLM-only & Judge 1\% & Judge 5\% & Judge 10\% & Gate 1\% & Gate 5\% & Gate 10\% \\", r"\midrule"]
    for g in ("P03-P09", "LTX", "MOVA"):
        for ax in ("A", "V", "AVB", "TCC", "TCR"):
            q = p[(p.dataset == g) & (p.axis == ax)]
            if not len(q):
                continue
            def cell(m, a):
                r = q[(q.method == m) & ((q.alpha == a) if a else q.alpha.isna())]
                if not len(r):
                    return "--"
                r = r.iloc[0]
                return ("--" if pd.isna(r.balanced_accuracy) else f"{r.balanced_accuracy:.3f}") + " / " + ("--" if pd.isna(r.FAIL_recall) else f"{r.FAIL_recall:.3f}")
            lines.append(f"{g} & {ax.replace('TCC', 'TC').replace('TCR', 'TR')} & {cell('MLLM-only', None)} & " + " & ".join(cell(m, a) for m in ("AVT-Judge", "Gate-only") for a in (0.01, 0.05, 0.10)) + r" \\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"; lines.append(r"\end{tabular}")
    (OUT / "tables/sensitivity_alpha_table.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["calib", "reproduce", "plan", "run", "score"]); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
