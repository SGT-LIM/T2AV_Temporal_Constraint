#!/usr/bin/env python3
"""Paper-table numerical handoff (2026-11-09). CPU only; reads existing predictions, writes only this directory.
Input predictions: eval_results/analysis/sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv (one row per GT-eligible unit; ten
methods; answer category per method). It was built from final_benchmark_1108/unit_results_final.csv (five existing methods, unchanged)
plus the five Sanjoy controls. The FLAM+Synchformer ablation is not read.
Positive class: FAIL (GT 'no'), as in every earlier report (comprehensive_report_1108.metrics: TP_FAIL / FN_FAIL / FP_FAIL / TN_FAIL).
Views:
  common10   units answered by all ten methods (identical unit IDs)
  answered   each method's own answered units
  fixed      all GT-eligible units (answered + unanswered). Established fixed-view quantities: correct / GT-eligible and coverage.
             Additional fixed-denominator recall-type metrics are NEW definitions (flagged): unanswered GT-PASS / GT-FAIL units count
             as not recovered (in the recall denominator, never in a numerator); precision-type metrics are not defined in this view
             because unanswered units have no prediction (left undefined, reason stated).
  python scripts/score_handoff.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import json, hashlib
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path((_tp.WORKSPACE))
SAN = ROOT / "eval_results/analysis/sanjoy_two_baselines_2026-11-08"
FB = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2/runs/obsval_1028/final_benchmark_1108"   # portable: via the linked runs/ dir
OUT = _tp.out_dir("paper_tables_handoff_2026-11-09")   # portable: $T2AV_OUT_DIR/<name>
METHODS = [("initial", "MLLM-only"), ("one_call", "one-call + tools"), ("always_shown", "always-shown"), ("original_gate", "original gate"),
           ("combined", "combined gate v2"), ("direct_orig", "direct-original"), ("direct_comb", "direct-combined-v2"),
           ("b1", "no-tool-all"), ("b2_orig", "no-tool-original"), ("b2_comb", "no-tool-combined-v2")]
COLS = [c for c, _ in METHODS]; NAME = dict(METHODS)
REASONS = ["model prerequisite skip", "model abstention / no usable label", "technical missing / failed output"]


def safe(n, d):
    return (n / d, "") if d else (np.nan, "denominator 0")


def answered_metrics(y, p):
    """established metrics on units with a prediction (FAIL positive)."""
    y, p = np.asarray(y), np.asarray(p)
    TP = int(((p == "no") & (y == "no")).sum()); FN = int(((p == "yes") & (y == "no")).sum())
    FP = int(((p == "no") & (y == "yes")).sum()); TN = int(((p == "yes") & (y == "yes")).sum())
    n = len(y); gtF, gtP = TP + FN, TN + FP; prF, prP = TP + FP, TN + FN
    m = {}
    def put(k, num, den, why_if0):
        v, w = safe(num, den); m[k] = (v, num, den, why_if0 if w else "")
    put("accuracy", TP + TN, n, "no answered units")
    put("FAIL_precision", TP, prF, "no FAIL predictions"); put("FAIL_recall", TP, gtF, "no GT-FAIL units")
    put("PASS_precision", TN, prP, "no PASS predictions"); put("PASS_recall", TN, gtP, "no GT-PASS units")
    put("false_alarm_rate", FP, gtP, "no GT-PASS units")
    for c in ("FAIL", "PASS"):
        pr, rc = m[f"{c}_precision"][0], m[f"{c}_recall"][0]
        if np.isnan(rc):
            m[f"{c}_F1"] = (np.nan, "", "", f"{c} recall undefined (no GT-{c} units)")
        elif np.isnan(pr):
            m[f"{c}_F1"] = (0.0, "", "", f"{c} precision undefined (no {c} predictions); F1 set to 0 as in comprehensive_report_1108.metrics")
        else:
            m[f"{c}_F1"] = ((2 * pr * rc / (pr + rc)) if (pr + rc) else 0.0, "2PR", "P+R", "")
    f1s = [m["FAIL_F1"][0], m["PASS_F1"][0]]
    m["macro_F1"] = (np.nan if any(np.isnan(f1s)) else sum(f1s) / 2, "FAIL_F1+PASS_F1", 2, "a class F1 is undefined" if any(np.isnan(f1s)) else "")
    rr = [m["FAIL_recall"][0], m["PASS_recall"][0]]
    m["balanced_accuracy"] = (np.nan if any(np.isnan(rr)) else sum(rr) / 2, "FAIL_recall+PASS_recall", 2, "a class recall is undefined" if any(np.isnan(rr)) else "")
    m["false_alarm_count"] = (FP, FP, "", "")
    cm = dict(positive_class="FAIL", TP=TP, FP=FP, TN=TN, FN=FN, GT_PASS=gtP, GT_FAIL=gtF, pred_PASS=prP, pred_FAIL=prF, N=n)
    return m, cm


def fixed_metrics(q, c):
    """fixed GT-eligible denominator. Unanswered units never get a label."""
    ok = q[c].isin(["yes", "no"]); y = q["gt"]; p = q[c]
    E, A = len(q), int(ok.sum()); gtF, gtP = int((y == "no").sum()), int((y == "yes").sum())
    TP = int((ok & (p == "no") & (y == "no")).sum()); TN = int((ok & (p == "yes") & (y == "yes")).sum())
    FP = int((ok & (p == "no") & (y == "yes")).sum()); FN = int((ok & (p == "yes") & (y == "no")).sum())
    m = {}
    est, new = "established (correct / GT-eligible, coverage; final_benchmark_1108 view 3)", "NEW definition (not previously specified)"
    def put(k, num, den, why, status):
        v, w = safe(num, den); m[k] = (v, num, den, why if w else "", status)
    put("accuracy", TP + TN, E, "no GT-eligible units", est + ": correct / GT-eligible")
    put("coverage", A, E, "no GT-eligible units", est)
    put("FAIL_recall", TP, gtF, "no GT-FAIL units", new + ": TP / all GT-FAIL eligible; unanswered GT-FAIL count as not recovered")
    put("PASS_recall", TN, gtP, "no GT-PASS units", new + ": TN / all GT-PASS eligible; unanswered GT-PASS count as not recovered")
    put("false_alarm_rate", FP, gtP, "no GT-PASS units", new + ": FP / all GT-PASS eligible (unanswered units are not false alarms)")
    rr = [m["FAIL_recall"][0], m["PASS_recall"][0]]
    m["balanced_accuracy"] = (np.nan if any(np.isnan(rr)) else sum(rr) / 2, "FAIL_recall+PASS_recall", 2, "a class recall is undefined" if any(np.isnan(rr)) else "",
                              new + ": mean of the fixed-denominator recalls")
    for k in ("FAIL_precision", "PASS_precision", "FAIL_F1", "PASS_F1", "macro_F1"):
        m[k] = (np.nan, "", "", "not defined in the fixed view: unanswered units have no prediction, so precision (and F1 / macro-F1, which need it) is only defined on answered units (see 'answered' view)", "not defined")
    m["false_alarm_count"] = (FP, FP, "", "", "established count (answered FAIL predictions on GT-PASS)")
    unans = {}
    for lab, nm in (("yes", "GT_PASS"), ("no", "GT_FAIL")):
        h = q[(~ok) & (y == lab)]
        unans[f"unanswered_{nm}"] = len(h)
        for r in REASONS:
            unans[f"unanswered_{nm}__{r}"] = int((h[c + "_cat"] == r).sum())
        unans[f"unanswered_{nm}__other"] = int((~h[c + "_cat"].isin(REASONS)).sum())
    cm = dict(positive_class="FAIL", TP=TP, FP=FP, TN=TN, FN=FN, GT_PASS=gtP, GT_FAIL=gtF, N=E, answered=A, **unans)
    return m, cm


def main():
    U = pd.read_csv(SAN / "results/unit_predictions.csv", low_memory=False)
    U["a_kind"] = U.a_kind.fillna("")
    T = U.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind
    T = pd.concat([T, TA], ignore_index=True)
    wide, long_, man, chk = [], [], [], []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        level = "video" if ax == "TCR" else "event"
        ans_all = np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in COLS]); c10 = q[ans_all]
        c5 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in COLS[:5]])]
        chk.append(dict(dataset=g, axis=ax, unit_level=level, gt_eligible=len(q), common10=len(c10), common5=len(c5),
                        identical_sets=set(c10.unit) == set(c5.unit), only_in_common5=len(set(c5.unit) - set(c10.unit))))
        man += [dict(dataset=g, axis=ax, subset=s, dataset_batch=d, unit=u) for s, h in (("common10", c10), ("common5", c5)) for d, u in zip(h.dataset, h.unit)]
        for c in COLS:
            base = dict(dataset=g, axis=ax, unit_level=level, method=NAME[c], method_col=c, gt_eligible=len(q))
            for view, h in (("common10", c10), ("answered", q[q[c].isin(["yes", "no"])])):
                m, cm = answered_metrics(h["gt"], h[c])
                cov = len(h) / len(q) if len(q) else np.nan
                row = dict(base, view=view, answered=len(h), coverage=cov, **{f"cm_{k}": v for k, v in cm.items()})
                for k, (v, num, den, why) in m.items():
                    row[k] = v; row[k + "_undefined_reason"] = why
                    long_.append(dict(base, view=view, metric=k, value=v, numerator=num, denominator=den, undefined_reason=why,
                                      definition_status="established (comprehensive_report_1108.metrics)"))
                long_.append(dict(base, view=view, metric="coverage", value=cov, numerator=len(h), denominator=len(q), undefined_reason="", definition_status="established"))
                wide.append(row)
            m, cm = fixed_metrics(q, c)
            row = dict(base, view="fixed", answered=cm["answered"], coverage=cm["answered"] / len(q) if len(q) else np.nan, **{f"cm_{k}": v for k, v in cm.items()})
            for k, (v, num, den, why, st) in m.items():
                row[k] = v; row[k + "_undefined_reason"] = why; row[k + "_definition"] = st
                long_.append(dict(base, view="fixed", metric=k, value=v, numerator=num, denominator=den, undefined_reason=why, definition_status=st))
            wide.append(row)
    (OUT / "tables").mkdir(parents=True, exist_ok=True); (OUT / "manifests").mkdir(exist_ok=True)
    W = pd.DataFrame(wide); W.to_csv(OUT / "tables/metrics_wide_all_views.csv", index=False, float_format="%.17g")
    for v in ("common10", "answered", "fixed"):
        W[W.view == v].to_csv(OUT / f"tables/metrics_{v}.csv", index=False, float_format="%.17g")
    pd.DataFrame(long_).to_csv(OUT / "tables/metrics_long_with_numerators.csv", index=False, float_format="%.17g")
    pd.DataFrame(man).to_csv(OUT / "manifests/common_subset_manifest.csv", index=False)
    pd.DataFrame(chk).to_csv(OUT / "tables/check_common5_vs_common10.csv", index=False)
    checks(U, W)


def checks(U, W):
    out = {}
    # (1) combined gate = calibration_v2; A speech inherits the original (Whisper) gate
    v2 = json.load(open(FB / "calibration_v2/frozen_p12_config.json"))["config"]
    out["calibration_v2_AVB_PASS_params"] = v2["AVB_PASS"]["params"]
    out["calibration_v2_A_SPEECH"] = {k: v["status"] for k, v in v2.items() if k.startswith("A_SPEECH")}
    F = pd.read_csv(FB / "unit_results_final.csv", low_memory=False)
    out["unit_results_final: combined == combined_v2 (all units)"] = bool((F.combined.fillna("") == F.combined_v2.fillna("")).all())
    sp = F[(F.axis == "A") & (F.family == "A speech") & F.scored_row1]
    out["A speech: combined == original_gate (units)"] = f"{int((sp.combined.fillna('') == sp.original_gate.fillna('')).sum())} / {len(sp)}"
    out["sanjoy consistency (direct-combined openings vs stored v2 openings)"] = json.load(open(SAN / "results/consistency_checks.json"))
    # (2) MOVA unified, restored batches
    out["MOVA batches (videos)"] = U[U.group == "MOVA"].groupby("dataset")["item"].nunique().to_dict()
    out["LTX batches (videos)"] = U[U.group == "LTX"].groupby("dataset")["item"].nunique().to_dict()
    ms = json.load(open(FB / "manifests/manifest_summary.json"))
    out["restored 220 manifest summary"] = {k: ms[k] for k in ("rows_v4", "rows_not_in_gepa_split", "mova_videos", "mova_duplicates", "ltx_videos", "ltx_duplicates")}
    # (3) identical IDs in common view: by construction (one boolean mask over all ten methods per dataset x axis)
    out["common10 identical unit IDs across methods"] = "by construction: one mask requiring an answer from all ten methods; manifest in manifests/common_subset_manifest.csv"
    # (4) five vs ten
    C = pd.read_csv(OUT / "tables/check_common5_vs_common10.csv")
    out["common5 vs common10 differences"] = C[~C.identical_sets].to_dict("records") or "none (identical in every dataset x axis)"
    # (5) reproduce published final_benchmark_1108 tables for the five methods
    rep = []
    mapn = {"media only": "MLLM-only", "one call plus tools": "one-call + tools", "always shown": "always-shown", "original paper gate": "original gate", "combined gate (v2 frozen)": "combined gate v2"}
    for fn, view in (("continuity_five_method_common_subset.csv", "common5 (published continuity)"), ("view2_identical_common_subset.csv", "published six-method common (incl. ablation)"),
                     ("view1_per_method_valid_responses.csv", "answered")):
        P = pd.read_csv(FB / "tables" / fn); P = P[P.method.isin(mapn)]
        for r in P.itertuples():
            mine = W[(W.dataset == r.group) & (W.axis == r.axis) & (W.method == mapn[r.method]) & (W.view == ("answered" if view == "answered" else "common10"))]
            if not len(mine):
                continue
            x = mine.iloc[0]
            same = int(x.answered) == int(r.N) and all((pd.isna(getattr(r, k)) and pd.isna(x[k])) or (not pd.isna(x[k]) and abs(getattr(r, k) - x[k]) < 1e-12)
                                                       for k in ("accuracy", "macro_F1", "balanced_accuracy", "FAIL_recall", "PASS_recall"))
            rep.append(dict(published_table=fn, compared_to=("answered" if view == "answered" else "common10"), dataset=r.group, axis=r.axis, method=mapn[r.method],
                            N_published=r.N, N_here=int(x.answered), acc_published=r.accuracy, acc_here=x.accuracy, identical=same))
    V3 = pd.read_csv(FB / "tables/view3_fixed_gt_eligible_universe.csv"); V3 = V3[V3.method.isin(mapn)]
    for r in V3.itertuples():
        x = W[(W.dataset == r.group) & (W.axis == r.axis) & (W.method == mapn[r.method]) & (W.view == "fixed")].iloc[0]
        rep.append(dict(published_table="view3_fixed_gt_eligible_universe.csv", compared_to="fixed", dataset=r.group, axis=r.axis, method=mapn[r.method],
                        N_published=r.gt_eligible, N_here=int(x.gt_eligible), acc_published=r.correct_over_total, acc_here=x.accuracy,
                        identical=int(r.gt_eligible) == int(x.gt_eligible) and int(r.answered) == int(x.answered) and abs(r.correct_over_total - x.accuracy) < 1e-12))
    R = pd.DataFrame(rep); R.to_csv(OUT / "tables/check_reproduce_final_benchmark_1108.csv", index=False, float_format="%.17g")
    out["reproduction vs final_benchmark_1108"] = R.groupby(["published_table", "compared_to"]).identical.agg(["sum", "size"]).reset_index().to_dict("records")
    out["input md5"] = {str(p): hashlib.md5(open(p, "rb").read()).hexdigest() for p in (SAN / "results/unit_predictions.csv", FB / "unit_results_final.csv",
                                                                                       FB / "calibration_v2/frozen_p12_config.json")}
    json.dump(out, open(OUT / "checks.json", "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
