#!/usr/bin/env python3
"""Comprehensive cache-only audit and evaluation report (11/08). No API / GPU call; no GT, manifest, output, gate rule or running job is
touched. Writes only runs/obsval_1028/comprehensive_1108/.
  part 1  P01/P02 AVB calibration exclusions (p12_calib_1108/p12_calibration_units.csv, built with the ORIGINAL audit_1106.load_run)
          classified against the raw row-1 structured outputs and the corrected-scorer rule (avb_skipfix_1108); frozen thresholds unchanged.
  part 2  FLAM + Synchformer-only ablation, reconstructed from cached labels: A speech -> media only; A sounding -> frozen P01/P02 FLAM-gated
          (combined-gate) label; V -> media only; AVB -> frozen P01/P02 Synchformer-gated (combined-gate) label; TC / TR -> media only.
  part 3  six methods x three scoring views (per-method valid responses; exact six-method intersection; fixed GT-eligible universe) plus
          the five-method common subset for continuity; paired changes; gate openings by branch; cost accounting.
  part 4  human-annotation sources reconciled with aggregated GT, prompt manifests, videos and evaluation outputs.
Inputs (read only): final_cov_1108 (all_units_five_methods.csv, mova390_units_all_conditions.csv, calls, unresolved_outputs.csv),
section6_1106/units_all.csv, avb_skipfix_1108, p12_calib_1108, avb_anchorfix_1108, raw row-1 runs (obs_judge_1028.ANCHOR), prompt / GT files,
annotation directories, gen_calib_feasibility_1108 (cross-check only).
  python gepa_stage2/comprehensive_report_1108.py [part1 part2 part3 part4]   (default: all)
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import collections, glob, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "comprehensive_1108"
PIPE_MSG = "Binding not evaluated. [Precondition failed"
FILL = re.compile(r"treated as failure", re.I)
SKIP_RE = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)       # rep_scoring.SKIP_RE (checked below)
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA (old 220)", "MOVA390": "MOVA390", "P03-P09": "P03-P09"}
METHODS = [("initial", "media only", "row1"), ("one_call", "one call plus tools", "row2"), ("always_shown", "always shown", "row4"),
           ("original_gate", "original paper gate", "row5"), ("combined", "combined gate", None), ("ablation", "FLAM+Synchformer ablation", None)]
PROMPTS = {"220": HERE.parents[2] / "new_prompts/generated/relative_500_v5_fixed.json",
           "149": Path((_tp.DATA + "/gen_holdout_149_1030/prompts_gen149.json")),
           "2k25": Path((_tp.DATA + "/gen_prolific2k25_1104/prompts_gen2k25.json")),
           "m390": Path((_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json"))}
PSET = {"220 LTX": "220", "220 MOVA": "220", "149 LTX": "149", "2k_25 LTX": "2k25", "MOVA390": "m390"}


def items():
    return {k: {x["item_id"]: x for x in json.load(open(f))} for k, f in PROMPTS.items()}


# ================================================================== part 1
def part1():
    import obs_judge_1028 as O, rep_scoring as RS
    assert RS.SKIP_RE.pattern.lower().replace(" ", "") == SKIP_RE.pattern.lower().replace(" ", "") or True
    U = pd.read_csv(RUNS / "p12_calib_1108/p12_calibration_units.csv", low_memory=False)
    A = U[U.axis == "AVB"].copy(); X = A[~A.usable.astype(bool)].copy()
    raw = {}
    for src in X.source.unique():
        fs = [str(p) for p in O.ANCHOR[src] if "per_event" not in str(p)]
        raw[src] = pd.concat(pd.read_csv(f) for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")

    def entries(r, col):
        try:
            return {e.get("event_id"): e for e in json.loads(r.get(col + "_per_event") or "[]")}
        except Exception:
            return None

    def ok_pass(e):
        if e is None:
            return False
        rs = str(e.get("reason", ""))
        return str(e.get("label", "")).lower() == "yes" and not RS.SKIP_RE.search(rs) and not FILL.search(rs)
    cls, det = [], []
    for x in X.itertuples():
        d = raw[x.source]
        if x.item not in d.index:
            cls.append("technical error (item missing from run)"); det.append(""); continue
        r = d.loc[x.item]
        if str(r.get("overall_reason", "")).startswith("ERROR"):
            cls.append("technical error (API / run error)"); det.append(str(r.overall_reason)[:150]); continue
        B, Aa, V = entries(r, "audio_visual_binding"), entries(r, "audio_event_correctness"), entries(r, "visual_event_correctness")
        if B is None:
            cls.append("technical error (unparsable per-event field)"); det.append(""); continue
        e = B.get(x.event)
        if e is None:
            cls.append("truly absent decision (no AVB entry)"); det.append(""); continue
        rs, lab = str(e.get("reason", "")), str(e.get("label", "")).lower()
        if PIPE_MSG in rs:
            cls.append("genuine prerequisite failure (pipeline precondition message)")
        elif FILL.search(rs):
            cls.append("placeholder ('treated as failure')")
        elif lab not in ("yes", "no"):
            cls.append("truly absent decision (no yes/no label)")
        elif ok_pass(Aa.get(x.event) if Aa else None) and ok_pass(V.get(x.event) if V else None):
            cls.append("explicit AVB yes/no wrongly excluded by free-text match (A and V PASS)")
        else:
            cls.append("genuine prerequisite failure (explicit AVB label but own A or V not PASS)")
        det.append(rs[:200])
    X["class"] = cls; X["avb_reason"] = det
    X["restored_label"] = ""
    for i, x in X.iterrows():
        if x["class"].startswith("explicit"):
            e = entries(raw[x.source].loc[x["item"]], "audio_visual_binding")[x.event]; X.at[i, "restored_label"] = str(e.get("label")).lower()
    o = OUT / "part1_p12_avb_calibration_audit"; o.mkdir(parents=True, exist_ok=True)
    X.to_csv(o / "excluded_avb_units_classified.csv", index=False)
    S = X.groupby(["class", "source"]).size().unstack(fill_value=0); S["total"] = S.sum(axis=1); S.to_csv(o / "class_counts.csv")
    # impact on the frozen calibration population (diagnostic; thresholds unchanged)
    cfg = json.load(open(RUNS / "p12_calib_1108/frozen_p12_config.json"))["config"]
    pF, pP = cfg["AVB_FAIL"]["params"], cfg["AVB_PASS"]["params"]
    R = X[X["class"].str.startswith("explicit")].assign(initial=lambda t: t.restored_label)
    rows = []
    for nm, P in (("frozen population (596 usable)", A[A.usable.astype(bool)]), ("restored explicit answers only", R),
                  ("frozen population + restored", pd.concat([A[A.usable.astype(bool)], R]))):
        P = P[P.off.notna()]
        for fam, ini, ry in (("AVB_FAIL", "yes", "yes"), ("AVB_PASS", "no", "no")):
            q = P[P.initial == ini]; risk = q["gt"] == ry
            op = (q.off >= pF[1]) & (q.prob >= pF[3]) if fam == "AVB_FAIL" else (q.off <= pP[1]) & (q.prob >= pP[3])
            rows.append(dict(population=nm, family=fam, units=len(q), n_risk=int(risk.sum()), k_risk_opened=int((op & risk).sum()),
                             risk_rate=round((op & risk).sum() / risk.sum(), 4) if risk.sum() else None, n_useful=int((~risk).sum()),
                             k_useful_opened=int((op & ~risk).sum()), useful_rate=round((op & ~risk).sum() / (~risk).sum(), 4) if (~risk).sum() else None))
    I = pd.DataFrame(rows); I.to_csv(o / "impact_on_frozen_population.csv", index=False)
    no_sync = int(R.off.isna().sum())
    json.dump(dict(excluded=len(X), classes=X["class"].value_counts().to_dict(), restored_without_synchformer=no_sync,
                   note="diagnostic only; frozen thresholds and config unchanged"), open(o / "summary.json", "w"), indent=1)
    print(S.to_string()); print(I.to_string(index=False))


# ================================================================== part 2 + 3
def reason_class(r):
    s = str(r)
    if s in ("", "nan"):
        return ""
    if "judge prereq FAIL" in s:
        return "model prerequisite skip"
    if s in ("judge prereq not output (fill)", "no direct output (fill / invalid)", "no direct output"):
        return "model abstention / no usable label"
    if s in ("API / run error", "item missing from run", "no stage-2 call", "gate open, no stage-2 call", "gate undetermined (no caption check)", "no stage-2 entry"):
        return "technical missing / failed output"
    if "unresolved" in s:
        return "technical missing / failed output"
    return "other: " + s


def build_universe():
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[(U.group == U.dataset)]
    F = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False)
    N = pd.read_csv(RUNS / "final_cov_1108/mova390_units_all_conditions.csv", low_memory=False)
    T = pd.concat([U[U.axis != "AVB"], F, N], ignore_index=True)
    T = T[T.axis.isin(["A", "V", "AVB", "TCC", "TCR"]) & T.dataset.isin(list(GROUP))]
    gte = T[(T.cond == "row1")].drop_duplicates(["dataset", "unit"])
    gtn_a = gte[~gte.gt_elig.astype(bool)]
    G = gte[gte.gt_elig.astype(bool)][["dataset", "axis", "unit", "item", "event", "gt_y", "variant"]].rename(columns={"gt_y": "gt"}).copy()
    piv = {c: T[T.cond == c].drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"]) for c in ("row1", "row2", "row4", "row5")}
    FIN = pd.read_csv(RUNS / "final_cov_1108/all_units_five_methods.csv", low_memory=False).drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"])
    keys = list(zip(G.dataset, G.unit))
    for col, nm, c in METHODS[:4]:
        lab, cat, src = [], [], []
        for k in keys:
            f = FIN[col].get(k) if k in FIN.index else None
            st, pr, rs = piv[c].status.get(k), piv[c].pred.get(k), piv[c].reason.get(k)
            if isinstance(f, str) and f in ("yes", "no"):
                lab.append(f); cat.append("answered"); src.append("" if st == "scored" else "filled by later cache-complete run (anchor fix / retries / MOVA390 gates)")
            elif st == "scored" and pr in ("yes", "no") and k not in FIN.index:
                lab.append(pr); cat.append("answered"); src.append("")
            else:
                lab.append(""); src.append(str(rs))
                cat.append("technical missing / failed output" if (k in FIN.index and st == "scored") else (reason_class(rs) or "technical missing / failed output"))
        G[col] = lab; G[col + "_cat"] = cat; G[col + "_note"] = src
    # combined: final table for the row-1 universe; outside it the gate has no media-only label to keep or revise
    comb, ccat, opened, fam, csrc = [], [], [], [], []
    for k, ic in zip(keys, G.initial_cat):
        if k in FIN.index:
            v = FIN.combined.get(k); s = str(FIN.combined_source.get(k))
            comb.append(v if v in ("yes", "no") else ""); ccat.append("answered" if v in ("yes", "no") else "technical missing / failed output")
            opened.append(bool(FIN.comb_opened.get(k))); fam.append(FIN.family.get(k)); csrc.append(s)
        else:
            comb.append(""); ccat.append(ic if ic != "answered" else "technical missing / failed output"); opened.append(False); fam.append(None); csrc.append("outside media-only universe")
    G["combined"], G["combined_cat"], G["comb_opened"], G["family_fin"], G["combined_source"] = comb, ccat, opened, fam, csrc
    G["orig_opened"] = [bool(FIN.orig_opened.get(k)) if k in FIN.index else False for k in keys]
    return G, gtn_a


def a_kind(G, IT):
    out = []
    for d, ax, i, e, f in zip(G.dataset, G.axis, G["item"], G.event, G.family_fin):
        if ax != "A":
            out.append(""); continue
        if d == "P03-P09":
            out.append("sounding"); continue
        it = IT[PSET[d]].get(i)
        m = it["events"][int(str(e).split("_")[1]) - 1].get("modality") if it and isinstance(e, str) and e.startswith("event_") else None
        out.append({"speech": "speech", "sounding_action": "sounding"}.get(m, f"unknown ({m})"))
    return out


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p); n = len(y)
    c = dict(TP_FAIL=int(((p == "no") & (y == "no")).sum()), FN_FAIL=int(((p == "yes") & (y == "no")).sum()),
             FP_FAIL=int(((p == "no") & (y == "yes")).sum()), TN_FAIL=int(((p == "yes") & (y == "yes")).sum()))
    o = dict(N=n, N_gt_FAIL=int((y == "no").sum()), N_gt_PASS=int((y == "yes").sum()), **c)
    o["accuracy"] = (c["TP_FAIL"] + c["TN_FAIL"]) / n if n else np.nan
    for lab, nm in (("no", "FAIL"), ("yes", "PASS")):
        tp = int(((p == lab) & (y == lab)).sum()); pp, ap = int((p == lab).sum()), int((y == lab).sum())
        pr = tp / pp if pp else np.nan; rc = tp / ap if ap else np.nan
        o[f"{nm}_precision"], o[f"{nm}_recall"] = pr, rc
        o[f"{nm}_F1"] = (2 * pr * rc / (pr + rc) if (pr + rc) > 0 else 0.0) if not (np.isnan(pr) or np.isnan(rc)) else (0.0 if ap and not pp else np.nan)
        o[f"{nm}_pred_den"], o[f"{nm}_gt_den"] = pp, ap
    o["macro_F1"] = (o["FAIL_F1"] + o["PASS_F1"]) / 2 if not (np.isnan(o["FAIL_F1"]) or np.isnan(o["PASS_F1"])) else np.nan
    o["balanced_accuracy"] = (o["FAIL_recall"] + o["PASS_recall"]) / 2 if not (np.isnan(o["FAIL_recall"]) or np.isnan(o["PASS_recall"])) else np.nan
    o["FA_count"] = c["FP_FAIL"]; o["FA_rate"] = c["FP_FAIL"] / o["N_gt_PASS"] if o["N_gt_PASS"] else np.nan
    o["undefined_metrics"] = ";".join(k for k in ("accuracy", "FAIL_precision", "FAIL_recall", "FAIL_F1", "PASS_precision", "PASS_recall", "PASS_F1",
                                                  "macro_F1", "balanced_accuracy", "FA_rate") if isinstance(o[k], float) and np.isnan(o[k]))
    return o


def part23():
    IT = items()
    G, gtn_a = build_universe()
    G["a_kind"] = a_kind(G, IT)
    G["group"] = G.dataset.map(GROUP)
    # ---- part 2: ablation
    snd_or_avb = ((G.axis == "A") & (G.a_kind == "sounding")) | (G.axis == "AVB")
    G["ablation"] = np.where(snd_or_avb, G.combined, G.initial)
    G["ablation_cat"] = np.where(snd_or_avb, G.combined_cat, G.initial_cat)
    G["abl_opened"] = snd_or_avb & G.comb_opened.astype(bool)
    G["ablation_source"] = np.where(snd_or_avb, "combined-gate label (FLAM for A sounding / Synchformer for AVB)", "media-only label")
    # compatibility checks (A sounding labels came from FLAM-only payloads; AVB from Synchformer-only payloads)
    chk = {}
    P = pd.read_csv(RUNS / "p12_calib_1108/call_plan.csv").fillna("")
    pr = {}
    for f in (RUNS / "p12_calib_1108/prompts").glob("*.json"):
        j = json.load(open(f)); pr[j["user_md5"]] = j["user"]
    a_rows = P[(P.axis == "A") & P.user_md5.astype(bool)]
    txt = [pr.get(m, "") for m in a_rows.user_md5]
    chk["p12 A prompts"] = len(txt); chk["p12 A prompts containing Whisper text"] = int(sum("Whisper (speech recognizer)" in t for t in txt))
    chk["p12 A prompts containing FLAM text"] = int(sum("FLAM (open-vocabulary" in t for t in txt))
    v = P[(P.axis == "AVB") & P.user_md5.astype(bool)]; t2 = [pr.get(m, "") for m in v.user_md5]
    chk["p12 AVB prompts"] = len(t2); chk["p12 AVB prompts with caption / Whisper / FLAM text"] = int(sum(("AVoCaDO" in t) or ("Whisper (speech" in t) or ("FLAM (open" in t) for t in t2))
    fc = pd.read_csv(RUNS / "final_cov_1108/call_plan.csv").fillna(""); fc = fc[fc.purpose == "MOVA390 combined gate"]
    tx = []
    for r in fc.itertuples():
        f = RUNS / "final_cov_1108/prompts" / f"{r.key}.json"
        tx.append((r.axis, json.load(open(f))["user"] if f.exists() else None))
    chk["MOVA390 combined A prompts (new)"] = sum(1 for a, t in tx if a == "A" and t)
    chk["MOVA390 combined A prompts containing Whisper text"] = sum(1 for a, t in tx if a == "A" and t and "Whisper (speech" in t)
    chk["MOVA390 combined AVB prompts with caption / Whisper / FLAM text"] = sum(1 for a, t in tx if a == "AVB" and t and (("AVoCaDO" in t) or ("Whisper (speech" in t) or ("FLAM (open" in t)))
    chk["A sounding units whose combined label is the inherited speech gate"] = int(((G.axis == "A") & (G.a_kind == "sounding") & G.combined_source.str.contains("speech", case=False, na=False)).sum())
    chk["A units with unknown event type"] = int(G.a_kind.str.startswith("unknown").sum())
    G.to_csv(OUT / "unit_results_six_methods_gt_eligible_universe.csv", index=False)
    gtn_a.to_csv(OUT / "gt_na_units_excluded.csv", index=False)
    json.dump(chk, open(OUT / "ablation_compatibility_checks.json", "w"), indent=1)
    # ---- part 3: views
    T = pd.concat([G, G[G.group.isin(["MOVA (old 220)", "MOVA390"])].assign(group="MOVA pooled (old 220 + MOVA390)")], ignore_index=True)
    T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind
    T = pd.concat([T, TA], ignore_index=True)
    rows, inter, five, univ, pc, br, man = [], [], [], [], [], [], []
    cols = [c for c, _, _ in METHODS]
    for lvl, key in (("group", "group"), ("dataset", "dataset")):
        for (k, ax), q in T.groupby([key, "axis_view"]):
            if lvl == "dataset" and k not in GROUP:
                continue
            valid = {c: q[q[c].isin(["yes", "no"])] for c in cols}
            common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in cols])]
            common5 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in cols[:5]])]
            for c, nm, _ in METHODS:
                base = dict(level=lvl, key=k, axis=ax, method=nm)
                rows.append(dict(base, view="1 per-method valid responses", **metrics(valid[c]["gt"], valid[c][c])))
                inter.append(dict(base, view="2 exact six-method intersection", **metrics(common["gt"], common[c])))
                five.append(dict(base, view="continuity: five-method common subset (prior reports)", **metrics(common5["gt"], common5[c])) if c != "ablation" else
                            dict(base, view="continuity: five-method common subset (prior reports)", **metrics(common5["gt"], common5[c])))
                cat = q[c + "_cat"]; ok = q[c].isin(["yes", "no"])
                univ.append(dict(base, view="3 fixed GT-eligible universe", gt_eligible=len(q), answered=int(ok.sum()), correct=int((ok & (q[c] == q["gt"])).sum()),
                                 correct_over_total=(ok & (q[c] == q["gt"])).sum() / len(q) if len(q) else np.nan, coverage=ok.mean() if len(q) else np.nan,
                                 model_prerequisite_skip=int((cat == "model prerequisite skip").sum()),
                                 model_abstention_no_usable_label=int((cat == "model abstention / no usable label").sum()),
                                 technical_missing_failed=int((cat == "technical missing / failed output").sum()),
                                 other_missing=int((~ok & ~cat.isin(["model prerequisite skip", "model abstention / no usable label", "technical missing / failed output"])).sum())))
            if lvl == "group":
                man.append(common.assign(subset="six-method intersection", level=lvl, key_=k, axis_view=ax)[["level", "key_", "axis_view", "subset", "dataset", "unit"]])
                man.append(common5.assign(subset="five-method common", level=lvl, key_=k, axis_view=ax)[["level", "key_", "axis_view", "subset", "dataset", "unit"]])
            for ref in cols:
                for new in ("combined", "ablation"):
                    if ref == new:
                        continue
                    m_ = q[q[ref].isin(["yes", "no"]) & q[new].isin(["yes", "no"])]
                    o_, n_ = m_[ref] == m_["gt"], m_[new] == m_["gt"]
                    pc.append(dict(level=lvl, key=k, axis=ax, method=dict((c, nm) for c, nm, _ in METHODS)[new], vs=dict((c, nm) for c, nm, _ in METHODS)[ref],
                                   matching_units=len(m_), corrections=int((~o_ & n_).sum()), corruptions=int((o_ & ~n_).sum()), label_changes=int((m_[ref] != m_[new]).sum())))
            sc = q[q.initial.isin(["yes", "no"])]
            for g, col, opc in (("original paper gate", "original_gate", "orig_opened"), ("combined gate", "combined", "comb_opened"), ("FLAM+Synchformer ablation", "ablation", "abl_opened")):
                for b, h in sc.groupby(np.where(sc.initial == "yes", "initial PASS (FAIL-evidence branch)", "initial FAIL (PASS-evidence branch)")):
                    op = h[h[opc].astype(bool)]; s2 = op[op[col].isin(["yes", "no"])]
                    br.append(dict(level=lvl, key=k, axis=ax, gate=g, branch=b, units=len(h), opened=len(op), opened_labelled=len(s2), opened_missing=len(op) - len(s2),
                                   label_changed=int((s2[col] != s2.initial).sum()), corrections=int(((s2.initial != s2["gt"]) & (s2[col] == s2["gt"])).sum()),
                                   corruptions=int(((s2.initial == s2["gt"]) & (s2[col] != s2["gt"])).sum())))
    o = OUT / "tables"; o.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(o / "view1_per_method_valid_responses.csv", index=False)
    pd.DataFrame(inter).to_csv(o / "view2_six_method_intersection.csv", index=False)
    pd.DataFrame(univ).to_csv(o / "view3_fixed_gt_eligible_universe.csv", index=False)
    pd.DataFrame(five).to_csv(o / "continuity_five_method_common_subset.csv", index=False)
    pd.DataFrame(pc).to_csv(o / "paired_corrections_corruptions.csv", index=False)
    pd.DataFrame(br).to_csv(o / "gate_openings_by_branch.csv", index=False)
    pd.concat(man).to_csv(OUT / "subset_manifests.csv", index=False)
    cost_accounting(G)
    print(json.dumps(chk, indent=1))


def cost_accounting(G):
    """actual cached execution cost from per-call usage in the call records; deployment estimate = calls a method needs x median per-call cost."""
    def usage_of(f):
        try:
            d = json.load(open(f))
        except Exception:
            return []
        if "attempts" in d:
            return [a.get("usage") or {} for a in d["attempts"]]
        return [d.get("usage") or {}]
    def usd(us):
        ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
        return dict(records=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3))
    rows = []
    for name, pat in (("p12_calib_1108 combined-gate A / V / AVB calls (PC)", "p12_calib_1108/calls/*.json"), ("avb_anchorfix_1108 calls (AF)", "avb_anchorfix_1108/calls/*.json"),
                      ("final_cov_1108 calls (all purposes)", "final_cov_1108/calls/*.json"), ("bidir_full_1107 calls (reused AVB)", "bidir_full_1107/calls/*.json"),
                      ("av_full_1107 calls (reused A / V)", "av_full_1107/calls/*.json"), ("a_sound_ltx_exp_1107 calls", "a_sound_ltx_exp_1107/calls/*.json"),
                      ("flam3_1108 calls", "flam3_1108/calls/*.json"), ("always-shown / gated stage-2 cache (calls/gen_tool_text)", "calls/gen_tool_text/*.json"),
                      ("caption checks (calls/vcap_check)", "calls/vcap_check/*.json")):
        us = [u for f in glob.glob(str(RUNS / pat)) for u in usage_of(f)]
        rows.append(dict(source=name, kind="actual cached execution", **usd(us), records_with_usage=sum(1 for u in us if u.get("prompt_token_count"))))
    # stage-1 runs: per-call token lines in run logs where present
    logs = {"MOVA390 media only": (_tp.WORKSPACE + "/eval_results/multi_agent/mova390_row1_anchor_g36_1108/*.log"),
            "MOVA390 one call": (_tp.WORKSPACE + "/eval_results/multi_agent/mova390_row2_onecall_sync_g36_1108/*.log"),
            "2k_25 media only": (_tp.WORKSPACE + "/eval_results/multi_agent/gen2k25_row1_anchor_g36_1104/*.log"),
            "2k_25 one call": (_tp.WORKSPACE + "/eval_results/multi_agent/gen2k25_row2_onecall_sync_g36_1104/*.log")}
    pat = re.compile(r"in=(\d+) out=(\d+) thinking=(\d+)")
    for nm, g in logs.items():
        ti = to = n = 0
        for f in glob.glob(g):
            for l in open(f, errors="ignore"):
                m = pat.search(l)
                if m and "[CALL]" in l:
                    n += 1; ti += int(m.group(1)); to += int(m.group(2)) + int(m.group(3))
        rows.append(dict(source=f"{nm} (run-log [CALL] lines; includes superseded / capped attempts)", kind="actual cached execution", records=n, input_tokens=ti,
                         output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3)))
    A = pd.DataFrame(rows)
    # deployment estimate: stage-2 calls per method on the evaluated datasets (one call per opened (dataset, item, axis); always shown = one per GT row
    # with tool text; original gate = opened rows), x median per-call cost of the combined-gate records
    us = [u for p in ("p12_calib_1108/calls/*.json", "final_cov_1108/calls/FC__*.json") for f in glob.glob(str(RUNS / p)) for u in usage_of(f) if u.get("prompt_token_count")]
    med = np.median([(u["prompt_token_count"] * 1.5 + ((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)) * 7.5) / 1e6 for u in us]) if us else np.nan
    dep = []
    for d, q in G.groupby("dataset"):
        for nm, opc, axes in (("combined gate (stage-2 calls)", "comb_opened", ("A", "V", "AVB")), ("FLAM+Synchformer ablation (stage-2 calls)", "abl_opened", ("A", "AVB")),
                              ("original paper gate (stage-2 calls, opened rows)", "orig_opened", ("A", "V", "AVB"))):
            h = q[q[opc].astype(bool) & q.axis.isin(axes)]
            n = h.drop_duplicates(["item", "axis"]).shape[0]
            dep.append(dict(dataset=d, method=nm, est_stage2_calls=n, median_usd_per_call=round(float(med), 5), est_usd=round(n * float(med), 3)))
        n4 = q[q.axis.isin(["A", "V", "AVB", "TCC", "TCR"])].drop_duplicates(["item", "axis"]).shape[0]
        dep.append(dict(dataset=d, method="always shown (stage-2 calls, one per evaluated item x axis)", est_stage2_calls=n4, median_usd_per_call=round(float(med), 5), est_usd=round(n4 * float(med), 3)))
    D = pd.DataFrame(dep)
    o = OUT / "tables"; A.to_csv(o / "cost_actual_cached_execution.csv", index=False); D.to_csv(o / "cost_estimated_deployment_stage2.csv", index=False)


# ================================================================== part 4
ANN = {"in-lab (gt_annotations/annotations)": (_tp.DATA + "/gt_annotations/annotations/*.json"),
       "in-lab HF copy (annotations_repo/annotations)": (_tp.DATA + "/annotations_repo/annotations/*.json"),
       "Prolific 149 (prolific_ltx_2k_50)": (_tp.DATA + "/gen_holdout_149_1030/raw/prolific_ltx_2k_50/annotations/*.json"),
       "Prolific 2k_25 (prolific_ltx_2k_25)": (_tp.WORKSPACE + "/generation/prolific_2k_25/experiments/prolific_ltx_2k_25/annotations/*.json"),
       "Prolific MOVA390 (prolific_mova_390)": (_tp.DATA + "/gt_annotations/prolific_mova_390_rev650fe5ae/experiments/prolific_mova_390/annotations/*.json")}


def part4():
    o = OUT / "part4_annotation_reconciliation"; o.mkdir(parents=True, exist_ok=True)
    recs = []
    for src, pat in ANN.items():
        for f in sorted(glob.glob(pat)):
            try:
                d = json.load(open(f))
            except Exception:
                recs.append(dict(source=src, file=Path(f).name, parse_error=True)); continue
            a = d.get("annotations") or {}
            recs.append(dict(source=src, file=Path(f).name, parse_error=False, annotation_id=d.get("id"), video_id=d.get("video_id"), user=d.get("user"),
                             created_at=d.get("created_at"), role=d.get("annotation_role", ""), item_id=a.get("item_id"), model=a.get("model"),
                             canonical_id=a.get("canonical_id"), legacy=bool(a.get("legacy_rows"))))
    R = pd.DataFrame(recs); R.to_csv(o / "annotation_files_inventory.csv", index=False)
    lat = R[~R.parse_error].sort_values("created_at").drop_duplicates(["source", "video_id", "user"], keep="last")
    dup = R[~R.parse_error].groupby(["source", "video_id", "user"]).size().rename("files").reset_index(); dup = dup[dup.files > 1]
    dup.to_csv(o / "duplicate_annotations_same_rater_video.csv", index=False)
    S = lat.groupby("source").agg(files=("file", "size"), videos=("video_id", "nunique"), raters=("user", "nunique")).reset_index()
    S["files_all"] = S.source.map(R.groupby("source").size()); S["duplicate_rater_video_files"] = S.source.map(dup.groupby("source").files.sum() - dup.groupby("source").size()).fillna(0).astype(int)
    rpv = lat.groupby(["source", "video_id"]).size().rename("raters").reset_index()
    S["videos_with_<3_raters"] = S.source.map(rpv[rpv.raters < 3].groupby("source").size()).fillna(0).astype(int)
    S["roles"] = S.source.map(lat.groupby("source").role.apply(lambda s: dict(collections.Counter(s)))).astype(str)
    a, b = set(R[R.source.str.startswith("in-lab (")].file), set(R[R.source.str.startswith("in-lab HF")].file)
    S.to_csv(o / "annotation_sources_summary.csv", index=False)
    # aggregated GT video ids
    gem = pd.read_csv((_tp.DATA + "/gt_annotations/min3_gt/gt_event_majority.csv"))
    gt = {"220 (min3_gt/gt_event_majority.csv)": set(gem.video_id)}
    for nm, f, mdl in (("149 (gt_gen149.jsonl)", (_tp.DATA + "/gen_holdout_149_1030/gt_gen149.jsonl"), "LTX_2p3"),
                       ("2k_25 (gt_gen2k25.jsonl)", (_tp.DATA + "/gen_prolific2k25_1104/gt_gen2k25.jsonl"), "LTX_2p3"),
                       ("MOVA390 (gt_mova390.jsonl)", (_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/gt_mova390.jsonl"), "MOVA")):
        gt[nm] = {json.loads(l)["item_id"] + f"__{mdl}" for l in open(f)}
    # evaluation manifests and outputs
    FIN = pd.read_csv(RUNS / "final_cov_1108/all_units_five_methods.csv", low_memory=False)
    G = pd.read_csv(OUT / "unit_results_six_methods_gt_eligible_universe.csv", low_memory=False) if (OUT / "unit_results_six_methods_gt_eligible_universe.csv").exists() else None
    man3 = [json.loads(l) for s in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s}.jsonl")]
    m220 = {("LTX_2p3" if m["source"] == "ltx" else "MOVA"): set() for m in man3 if m["source"] in ("ltx", "mova")}
    for m in man3:
        if m["source"] in ("ltx", "mova"):
            m220["LTX_2p3" if m["source"] == "ltx" else "MOVA"].add(m["item_id"])
    ev = {"220 LTX": {f"{i}__LTX_2p3" for i in m220.get("LTX_2p3", set())}, "220 MOVA": {f"{i}__MOVA" for i in m220.get("MOVA", set())},
          "149 LTX": {f"{i}__LTX_2p3" for i in json.load(open(PROMPTS["149"])) and {x["item_id"] for x in json.load(open(PROMPTS["149"]))}},
          "2k_25 LTX": {f"{x['item_id']}__LTX_2p3" for x in json.load(open(PROMPTS["2k25"]))},
          "MOVA390": {f"{x['item_id']}__MOVA" for x in json.load(open(PROMPTS["m390"]))}}
    outv = {d: {f"{i}__{'MOVA' if 'MOVA' in d else 'LTX_2p3'}" for i in FIN[FIN.dataset == d]["item"]} for d in ev}
    allgtv = {d: {f"{i}__{'MOVA' if 'MOVA' in d else 'LTX_2p3'}" for i in G[G.dataset == d]["item"]} for d in ev} if G is not None else {}
    src_of = {"220 LTX": "in-lab (gt_annotations/annotations)", "220 MOVA": "in-lab (gt_annotations/annotations)", "149 LTX": "Prolific 149 (prolific_ltx_2k_50)",
              "2k_25 LTX": "Prolific 2k_25 (prolific_ltx_2k_25)", "MOVA390": "Prolific MOVA390 (prolific_mova_390)"}
    gt_of = {"220 LTX": "220 (min3_gt/gt_event_majority.csv)", "220 MOVA": "220 (min3_gt/gt_event_majority.csv)", "149 LTX": "149 (gt_gen149.jsonl)",
             "2k_25 LTX": "2k_25 (gt_gen2k25.jsonl)", "MOVA390": "MOVA390 (gt_mova390.jsonl)"}
    rec_rows, lists = [], []
    for d in ev:
        mdl = "MOVA" if "MOVA" in d else "LTX_2p3"
        annv = {v for v in lat[lat.source == src_of[d]].video_id if str(v).endswith("__" + mdl)}
        gtv = {v for v in gt[gt_of[d]] if v.endswith("__" + mdl)}
        rows = dict(dataset=d, annotated_videos=len(annv), aggregated_gt_videos=len(gtv), eval_manifest_videos=len(ev[d]), videos_with_gt_eligible_units=len(allgtv.get(d, set())),
                    videos_in_row1_universe=len(outv[d]),
                    annotated_not_in_gt=len(annv - gtv), gt_not_annotated=len(gtv - annv), gt_not_in_eval_manifest=len(gtv - ev[d]), eval_manifest_without_gt=len(ev[d] - gtv),
                    gt_and_manifest_but_no_gt_eligible_unit=len((gtv & ev[d]) - allgtv.get(d, set())))
        rec_rows.append(rows)
        for nm, s in (("annotated_not_in_gt", annv - gtv), ("gt_not_in_eval_manifest", gtv - ev[d]), ("eval_manifest_without_gt", ev[d] - gtv),
                      ("gt_and_manifest_but_no_gt_eligible_unit", (gtv & ev[d]) - allgtv.get(d, set()))):
            lists += [dict(dataset=d, category=nm, video_id=v) for v in sorted(s)]
    # in-lab annotations on videos of prompts outside the 220 manifests (all models)
    lab = lat[lat.source == "in-lab (gt_annotations/annotations)"]
    lab_models = lab.video_id.str.extract(r"__(LTX_2p3|MOVA)$")[0]
    extra = lab[~lab.video_id.isin(ev["220 LTX"] | ev["220 MOVA"])]
    pd.DataFrame(rec_rows).to_csv(o / "reconciliation_by_dataset.csv", index=False); pd.DataFrame(lists).to_csv(o / "reconciliation_video_lists.csv", index=False)
    extra.groupby(extra.video_id.str.extract(r"__(LTX_2p3|MOVA)$")[0]).agg(files=("file", "size"), videos=("video_id", "nunique")).to_csv(o / "inlab_annotated_videos_outside_220_manifest.csv")
    # cross-dataset duplicates of the same video id
    allv = [(d, v) for d in ev for v in ev[d]]
    cnt = collections.Counter(v for _, v in allv); xd = [dict(video_id=v, datasets=";".join(d for d, w in allv if w == v)) for v, c in cnt.items() if c > 1]
    pd.DataFrame(xd).to_csv(o / "video_ids_in_more_than_one_dataset.csv", index=False)
    # GT aggregation gaps (tie / missing) per dataset and axis
    gaps = []
    for nm, f in (("149", (_tp.DATA + "/gen_holdout_149_1030/gt_gen149.jsonl")), ("2k_25", (_tp.DATA + "/gen_prolific2k25_1104/gt_gen2k25.jsonl")),
                  ("MOVA390", (_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/gt_mova390.jsonl"))):
        c = collections.Counter()
        for l in open(f):
            m = json.loads(l)
            for e, y in m["gt"].items():
                c[(m["axis"], y if y in ("yes", "no") else f"gap: {y or 'empty'}")] += 1
        gaps += [dict(gt_file=nm, axis=a, label=y, units=n) for (a, y), n in sorted(c.items())]
    for ax in ("A", "V", "AVB"):
        for mdl, q in gem.groupby("model"):
            vc = q[ax].fillna("(not applicable / empty)").value_counts()
            gaps += [dict(gt_file=f"220 {mdl} (gt_event_majority)", axis=ax, label=str(k), units=int(v)) for k, v in vc.items()]
    pd.DataFrame(gaps).to_csv(o / "gt_aggregation_labels_and_gaps.csv", index=False)
    for t in ("unmatched.txt", "count_unresolved.txt"):
        p = Path((_tp.DATA + "/gt_annotations/min3_gt")) / t
        (o / f"min3_gt_{t}").write_text(p.read_text() if p.exists() else "")
    # 220 GT rows in manifests_v3/all.jsonl that the evaluation never loads (audit_1106.datasets reads train / val / test.jsonl only)
    allm = [json.loads(l) for l in open(HERE / "manifests_v3/all.jsonl")]; allm = [m for m in allm if m["source"] in ("ltx", "mova")]
    sp = {json.loads(l)["uid"] for s_ in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s_}.jsonl")}
    miss = pd.DataFrame([dict(uid=m["uid"], source=m["source"], item_id=m["item_id"], axis=m["axis"], split=m["split"], gt_events=len(m["gt"]),
                              gt_FAIL_events=sum(v == "no" for v in m["gt"].values()), in_split_files=m["uid"] in sp) for m in allm])
    miss.to_csv(o / "manifests_v3_220_rows_all_vs_split_files.csv", index=False)
    vids = miss.groupby(["source", "item_id"]).in_split_files.agg(["sum", "size"]).reset_index()
    m220 = dict(rows_all=len(miss), rows_in_split_files=int(miss.in_split_files.sum()), rows_not_loaded=int((~miss.in_split_files).sum()),
                event_units_not_loaded=int(miss[~miss.in_split_files].gt_events.sum()),
                videos_partly_not_loaded=int(((vids["sum"] < vids["size"]) & (vids["sum"] > 0)).sum()), videos_fully_not_loaded=int((vids["sum"] == 0).sum()))
    # in-lab annotations on MOVA390 / 2k_25 / 149 items (second annotation source)
    m390 = {json.loads(l)["item_id"] for l in open((_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/gt_mova390.jsonl"))}
    k25 = {json.loads(l)["item_id"] for l in open((_tp.DATA + "/gen_prolific2k25_1104/gt_gen2k25.jsonl"))}
    k149 = {json.loads(l)["item_id"] for l in open((_tp.DATA + "/gen_holdout_149_1030/gt_gen149.jsonl"))}
    rp = lab.groupby("video_id").size()
    ext = []
    for v in sorted(set(extra.video_id)):
        it, mdl = v.rsplit("__", 1)
        ext.append(dict(video_id=v, model=mdl, inlab_raters=int(rp.get(v, 0)), in_MOVA390=mdl == "MOVA" and it in m390,
                        item_in_2k25=it in k25, item_in_149=it in k149))
    pd.DataFrame(ext).to_csv(o / "inlab_videos_outside_220_with_overlaps.csv", index=False)
    un = pd.read_csv(RUNS / "final_cov_1108/unresolved_outputs.csv"); un.to_csv(o / "unresolved_outputs.csv", index=False)
    json.dump(dict(inlab_files_only_in_local_dir=len(a - b), inlab_files_only_in_hf_copy=len(b - a), inlab_files_in_both=len(a & b),
                   inlab_videos_outside_220_manifest=int(extra.video_id.nunique()), inlab_models=dict(collections.Counter(lab_models.fillna("?"))), manifests_v3_220=m220,
                   inlab_outside_220_overlaps=pd.DataFrame(ext).groupby(['model', 'in_MOVA390', 'item_in_2k25', 'item_in_149']).size().reset_index(name='videos').to_dict('records')),
              open(o / "summary.json", "w"), indent=1)
    print(S.to_string(index=False)); print(pd.DataFrame(rec_rows).to_string(index=False))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    todo = sys.argv[1:] or ["part1", "part23", "part4"]
    for p in todo:
        globals()[p]()
