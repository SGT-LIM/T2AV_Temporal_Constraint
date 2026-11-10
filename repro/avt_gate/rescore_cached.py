#!/usr/bin/env python3
"""Re-run the evidence gate and the evaluation from cached outputs (no API / GPU call; writes only to --out/<tag>).

For one frozen gate configuration it recomputes, from the cached Stage-1 labels, tool features and Stage-2 call records:
  * gate openings (p12_calib_1108.open_rule, bidirectional: initial PASS -> FAIL-evidence branch, initial FAIL -> PASS-evidence branch)
  * AVT-Judge labels  = cached text-only reconsideration outputs for the opened (dataset, item, axis) requests, matched by the exact
                        user-prompt md5 (final_benchmark_1108.comb_call); A speech = original-gate label (Whisper word presence)
  * Gate-only labels  = admitted direction (opened initial PASS -> FAIL, opened initial FAIL -> PASS); A speech = direct-original
                        Whisper mapping (sanjoy_controls.direct_labels); closed -> initial label
  * metrics in three views (fixed six-method common subset; per-method answered; fixed GT-eligible denominator) with the established
    metric code (score_handoff.answered_metrics / fixed_metrics = comprehensive_report_1108.metrics definitions)
and compares every label with the stored result of the original run. Missing cached outputs stay missing (never filled); this script
never makes a model call.

  python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/main/frozen_p12_config.json --tag main_alpha05 --out $T2AV_OUT_DIR
  python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/sensitivity/a01/frozen_config.json --tag sens_alpha01 --out $T2AV_OUT_DIR \
         --stored-labels $T2AV_WORKSPACE/eval_results/analysis/sensitivity_2026-11-10/results/unit_labels_openings.csv --stored-tag a01
"""
import argparse, glob, hashlib, json, os, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "evaluation/ablation/gepa_stage2"), str(REPO / "evaluation/ablation"), str(REPO / "repro/avt_gate/analysis")]
sys.path.append(str(REPO))                       # t2av_paths.py


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_info():
    def run(*a):
        try:
            return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    return dict(commit=run("rev-parse", "HEAD"), branch=run("rev-parse", "--abbrev-ref", "HEAD"), dirty=bool(run("status", "--porcelain", "--untracked-files=no")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="frozen gate configuration json (configs/main or configs/sensitivity/<a>)")
    ap.add_argument("--tag", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--stored-labels", default="", help="optional stored unit labels to compare with (sensitivity runs)")
    ap.add_argument("--stored-tag", default="", help="a01 / a05 / a10 column suffix in --stored-labels")
    ap.add_argument("--extra-calls", nargs="*", default=None, help="extra directories of AS__/NB__ call records (default: historical sensitivity calls)")
    a = ap.parse_args()
    out = Path(a.out) / a.tag
    if out.exists():
        sys.exit(f"{out} exists; choose a new --tag (results are never overwritten)")
    out.mkdir(parents=True)
    os.environ.setdefault("T2AV_OUT_DIR", str(Path(a.out) / "_analysis_scratch"))
    import numpy as np, pandas as pd
    import t2av_paths as tp
    import alpha_sensitivity as AS, sanjoy_controls as SC, score_handoff as SH
    t0 = time.time()
    cfg_all = json.load(open(a.config)); cfg = cfg_all["config"]
    U = AS.universe()                                   # stored Stage-1 / baseline labels + cached tool features (final_benchmark_1108)
    stored_do = U.direct_orig_ref.copy()                # stored sanjoy_two_baselines direct-original labels (comparison only)
    do, dor, dc, dcr = SC.direct_labels(U.assign(event_key=U.event))
    U["direct_orig_ref"] = do                           # Whisper word-presence direct mapping, recomputed (used for A speech in Gate-only)
    op, bk = AS.openings(U, cfg)
    idx = AS.reuse_idx()
    extra = a.extra_calls if a.extra_calls is not None else [str(Path(tp.WORKSPACE) / "eval_results/analysis/sensitivity_2026-11-10/calls")]
    n_extra = 0
    for d in extra:
        for p in glob.glob(str(Path(d) / "AS__*.json")):
            att = [x for x in json.load(open(p))["attempts"] if x.get("complete")]
            if att:
                idx.setdefault(att[-1]["user_md5"], ("attempts", p)); n_extra += 1
    lab, src, req, cache = AS.judge_labels(U, cfg, op, idx)
    U["open"], U["branch"], U["avt_judge"], U["avt_judge_source"], U["request_md5"] = op, bk, lab, src, req
    U["gate_only"] = AS.gate_only_labels(U, op)
    for c in ("avt_judge", "gate_only"):
        U[c + "_cat"] = ["answered" if v in ("yes", "no") else (ic if ic != "answered" else "technical missing / failed output") for v, ic in zip(U[c], U.initial_cat)]
    keep = ["dataset", "batch", "group", "axis", "a_kind", "unit", "item", "event", "gt", "initial", "initial_cat", "family", "flam_max", "vcap", "off", "prob",
            "open", "branch", "avt_judge", "avt_judge_cat", "avt_judge_source", "request_md5", "gate_only", "gate_only_cat"]
    U[keep].to_csv(out / "unit_labels.csv", index=False)
    # ---- comparisons with the stored run
    S = pd.read_csv(AS.SAN / "results/unit_predictions.csv", low_memory=False).set_index(["dataset", "unit"])
    chk = dict(direct_original_mapping_recomputed_vs_stored_sanjoy=f"{int((pd.Series(do).fillna('').values == stored_do.fillna('').values).sum())} / {len(U)}")
    if a.stored_labels:
        St = pd.read_csv(a.stored_labels, low_memory=False).set_index(["dataset", "unit"]); t = a.stored_tag
        for mine, theirs in (("open", f"open_{t}"), ("avt_judge", f"judge_{t}"), ("gate_only", f"gate_{t}")):
            ref = [St[theirs].get(k) for k in zip(U.dataset, U.unit)]
            same = sum((str(x) if not (isinstance(x, float) and np.isnan(x)) else "") == (str(y) if not (isinstance(y, float) and np.isnan(y)) else "") for x, y in zip(U[mine], ref))
            chk[f"{mine}_vs_stored_{theirs}"] = f"{same} / {len(U)}"
    else:
        F = pd.read_csv(AS.FBD / "unit_results_final.csv", low_memory=False)
        chk["avt_judge_vs_stored_combined_final_benchmark_1108"] = f"{int((U.avt_judge.fillna('').values == F.combined.fillna('').values).sum())} / {len(U)}"
        chk["gate_only_vs_stored_direct_comb_sanjoy"] = f"{int(sum(x == (S.direct_comb.get(k) if isinstance(S.direct_comb.get(k), str) else '') for x, k in zip(U.gate_only.fillna(''), zip(U.dataset, U.unit))))} / {len(U)}"
        ns = U.scored_row1 & (U.family != "A speech")
        chk["openings_vs_stored_comb_opened_v2 (non-speech)"] = f"{int((np.array(op)[ns.values] == U.comb_opened_v2.astype(bool)[ns].values).sum())} / {int(ns.sum())}"
    miss = U[U.avt_judge_source.str.startswith("open: missing")]
    chk["avt_judge_opened_units_without_cached_output"] = len(miss)
    chk["avt_judge_missing_requests"] = sorted({f"{d}|{i}|{x}" for d, i, x in zip(miss.dataset, miss["item"], miss.axis)})
    # ---- metrics, three views
    T = U.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind; T = pd.concat([T, TA], ignore_index=True)
    S6 = pd.read_csv(AS.FBD / "subset_manifests.csv"); S6 = S6[S6.subset == "six-method common"]
    ids = set(zip(S6.group, S6.axis_view, S6.dataset, S6.unit))
    T["in_common"] = [(g, x, d, u) in ids for g, x, d, u in zip(T.group, T.axis_view, T.dataset, T.unit)]
    rows = []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        fc = q[q.in_common]
        for col, name in (("initial", "MLLM-only"), ("avt_judge", "AVT-Judge"), ("gate_only", "Gate-only")):
            for view, h in (("common_fixed_six_method", fc[fc[col].isin(["yes", "no"])]), ("answered", q[q[col].isin(["yes", "no"])])):
                m, cm = SH.answered_metrics(h["gt"], h[col])
                r = dict(dataset=g, axis=ax, method=name, view=view, answered=len(h), gt_eligible=len(q), missing_in_common=(len(fc) - len(h)) if view.startswith("common") else "",
                         **{f"cm_{k}": v for k, v in cm.items()})
                r.update({k: v[0] for k, v in m.items()}); r.update({k + "_undefined_reason": v[3] for k, v in m.items()}); rows.append(r)
            qq = q.assign(**{col + "_cat": q[col + "_cat"] if col != "initial" else q.initial_cat})
            m, cm = SH.fixed_metrics(qq, col)
            r = dict(dataset=g, axis=ax, method=name, view="fixed_gt_eligible", answered=cm["answered"], gt_eligible=len(q), **{f"cm_{k}": v for k, v in cm.items()})
            r.update({k: v[0] for k, v in m.items()}); r.update({k + "_definition": v[4] for k, v in m.items()}); rows.append(r)
    pd.DataFrame(rows).to_csv(out / "metrics_three_views.csv", index=False, float_format="%.17g")
    json.dump(chk, open(out / "checks.json", "w"), indent=1)
    import obs_judge_1028 as O
    man = dict(created=time.strftime("%Y-%m-%dT%H:%M:%S"), command=" ".join([sys.executable] + sys.argv), git=git_info(), tag=a.tag,
               config=dict(path=os.path.relpath(a.config, REPO) if str(a.config).startswith(str(REPO)) else a.config, sha256=hashlib.sha256(open(a.config, "rb").read()).hexdigest(),
                           alpha=cfg_all.get("alpha", "0.05 (calibration_v2)"), branches={k: [v["active"], v["params"]] for k, v in cfg.items()}),
               stage2_model=dict(model="gemini-3.6-flash", thinking="high", temperature=0.0, seed=42, response="application/json + run_two_stage.SCHEMA[axis]",
                                 obs_rules_md5=O.OBS_RULES_MD5, media="none (text only)", calls_made=0),
               data=dict(unit_results_final_md5=md5(AS.FBD / "unit_results_final.csv"), calibration_units_md5=md5(AS.FBD / "calibration_v2/p12_calibration_units.csv"),
                         subset_manifest_md5=md5(AS.FBD / "subset_manifests.csv"), sanjoy_unit_predictions_md5=md5(AS.SAN / "results/unit_predictions.csv"),
                         cached_call_records_indexed=len(idx), extra_call_records=n_extra, units=len(U)),
               env={k: ("set" if os.environ.get(k) else "unset") for k in ("T2AV_WORKSPACE", "T2AV_DATA", "T2AV_HF_CACHE", "T2AV_EXT_TMP", "T2AV_OUT_DIR", "GEMINI_API_KEY")},
               wall_s=round(time.time() - t0, 1))
    json.dump(man, open(out / "run_manifest.json", "w"), indent=1, default=str)
    print(json.dumps(chk, indent=1)[:3000])


if __name__ == "__main__":
    main()
