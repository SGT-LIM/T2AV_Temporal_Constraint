#!/usr/bin/env python3
"""Final benchmark with corrected scope (11/08). Writes only runs/obsval_1028/final_benchmark_1108/; historical manifests, GT, caches,
configs and results are read only.
Scope corrections
  220 LTX / 220 MOVA: GT rows rebuilt from the established min-3 aggregation (gt_annotations/min3_gt/gt_event_majority.csv; >= 3
    annotators, strict majority, ties excluded) for every event of the 110 x 2 annotated videos, instead of the obsolete GEPA
    train / val / test subset files. TCR / TC rows unchanged (all.jsonl == split files for these axes). Eligibility = audit_1106 rules.
  2k_25: the two annotated items without GT re-aggregated with the unchanged prolific2k25_adapter_1104.majority rule.
  MOVA = old 220 MOVA + MOVA390 as ONE dataset (batch kept in unit files only); deduplicated by file md5 (none duplicated).
  In-lab annotations of MOVA390 videos are NOT merged with the Prolific GT; the annotator-count rule is not relaxed.
Calibration: p12_calib_1108 selection algorithm (select_family / stage_select, unchanged objectives, families, tie-breaking) rerun on the
  corrected P01/P02 population (39 explicit AVB answers restored, part 1 of comprehensive_report_1108); old config kept as v1.
Calls: gemini-3.6-flash, thinking high, temperature 0, seed 42, OBS_RULES unchanged, prompt builders unchanged (G4 / G5 / GA4 / caption
  check / bidirectional payload); exact prompt-md5 reuse of complete outputs; up to 3 attempts; billing-cap error -> HOLD.
  python gepa_stage2/final_benchmark_1108.py manifests | calib | plan | run | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, copy, glob, hashlib, json, os, re, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "final_benchmark_1108"; CALLS = OUT / "calls"; MAN = OUT / "manifests"
MODEL, MAXTRY = "gemini-3.6-flash", 3
BILL = re.compile(r"spending cap|billing|exceeded its monthly", re.I)
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA", "MOVA390": "MOVA", "P03-P09": "P03-P09"}
GEM = Path((_tp.DATA + "/gt_annotations/min3_gt/gt_event_majority.csv"))
REL500 = HERE.parents[2] / "new_prompts/generated/relative_500_v5_fixed.json"
SRC220 = {"220 LTX": ("g220ltx", "LTX_2p3", "ltx"), "220 MOVA": ("g220mova", "MOVA", "mova")}
S2 = {"P03-P09": ("HA4", "hm_p3p9"), "220 LTX": ("GA4", "g220ltx"), "220 MOVA": ("GA4", "g220mova"), "149 LTX": ("GA4", "g149"), "2k_25 LTX": ("K4", "g2k25")}
S2AV = {"P03-P09": ("HG4", "hm_p3p9"), "220 LTX": ("G4", "g220ltx"), "220 MOVA": ("G4", "g220mova"), "149 LTX": ("G4", "g149"), "2k_25 LTX": ("K4", "g2k25")}
CFG = {"v1": RUNS / "p12_calib_1108/frozen_p12_config.json", "v2": OUT / "calibration_v2/frozen_p12_config.json"}
_M = {}


# ------------------------------------------------------------------ 220 rows from the min-3 aggregation
def gem_rows():
    rel = {x["item_id"]: x for x in json.load(open(REL500))}
    gem = pd.read_csv(GEM)
    rows, ties = {}, []
    for r in gem.itertuples():
        mdl = r.model; iid = r.video_id.replace(f"__{mdl}", ""); it = rel.get(iid)
        if it is None:
            continue
        idx = {e["id"]: f"event_{k + 1}" for k, e in enumerate(it["events"])}; eid = idx.get(r.prompt_event)
        if not eid:
            continue
        ds = "220 LTX" if mdl == "LTX_2p3" else "220 MOVA"
        for ax in ("A", "V", "AVB"):
            v = str(getattr(r, ax)).upper()
            if v in ("PASS", "FAIL"):
                rows.setdefault((ds, iid, ax), {})[eid] = "yes" if v == "PASS" else "no"
            elif v == "TIE":
                ties.append(dict(dataset=ds, item=iid, axis=ax, event=eid, n_annot=r.n_annot))
    allm = [json.loads(l) for l in open(HERE / "manifests_v3/all.jsonl")]
    tcr = [m for m in allm if m["source"] in ("ltx", "mova") and m["axis"] in ("TCR", "TCC")]
    out = {"220 LTX": [], "220 MOVA": []}
    for (ds, iid, ax), gt in sorted(rows.items()):
        src = SRC220[ds][0]
        out[ds].append(dict(source=src, item_id=iid, axis=ax, gt=gt, uid=f"{src}|{iid}|{ax}", variant=SRC220[ds][1]))
    for m in tcr:
        ds = "220 LTX" if m["source"] == "ltx" else "220 MOVA"; src = SRC220[ds][0]
        out[ds].append(dict(source=src, item_id=m["item_id"], axis=m["axis"], gt=m["gt"], uid=f"{src}|{m['item_id']}|{m['axis']}", variant=SRC220[ds][1]))
    return out, pd.DataFrame(ties)


# ------------------------------------------------------------------ setup (in-process patches; no file edited)
def new_rec(key):
    f = CALLS / f"{key.replace('/', '_')}.json"
    if not f.exists():
        return None
    good = [a for a in json.load(open(f))["attempts"] if a.get("status") == "ok" and a.get("complete")]
    return good[-1] if good else None


def setup():
    if _M:
        return _M
    import final_cov_1108 as FC
    M = FC.setup(); AU, O, G, S6, BF, GPI = (M[k] for k in ("AU", "O", "G", "S6", "BF", "GPI"))
    R220, _ = gem_rows()
    orig_gt_rows = G.gt_rows

    def gt_rows():
        keep = [r for r in orig_gt_rows() if r["source"] not in ("g220ltx", "g220mova")]
        new = [dict(r) for ds in R220 for r in R220[ds] if r["axis"] in ("A", "V", "AVB")]
        return new + keep
    G.gt_rows = gt_rows
    orig_ds = AU.datasets

    def datasets():
        D = orig_ds()
        for ds in R220:
            D[ds]["rows"] = [dict(item_id=r["item_id"], axis=r["axis"], gt=r["gt"], source=SRC220[ds][2]) for r in R220[ds] if r["axis"] in ("AVB", "TCR")]
        return D
    AU.datasets = datasets
    prev_v = G.vcheck

    def vcheck(uid):
        old = prev_v(uid); nb = new_rec(f"VC__{uid}")
        nbv = {e["event_id"]: e["verdict"] for e in (nb.get("parsed") or {}).get("per_event", [])} if nb else None
        if old is None and nbv is None:
            return None
        return {**(nbv or {}), **(old or {})}                         # existing verdicts kept; new check only adds missing events
    G.vcheck = vcheck; GPI.vcap = vcheck
    # stage-2 records: anchor-fix fills of the existing sets (per-event fallback, as avb_anchorfix_1108 scored them) + this run's records
    af = pd.read_csv(RUNS / "avb_anchorfix_1108/call_plan.csv").fillna("")
    afmap = {}
    for r in af.itertuples():
        if r.method in ("always shown", "original paper gate") and r.user_md5:
            st = (S2 if r.method == "always shown" else S2AV)[r.dataset][0]
            afmap[f"{st}__{r.uid}"] = RUNS / "avb_anchorfix_1108/calls" / f"AF__{r.user_md5}.json"
    sub = json.load(open(OUT / "substitutions.json")) if (OUT / "substitutions.json").exists() else {}
    prev_s2 = AU.stage2_rec

    def stage2_rec(set_name, uid):
        rec = prev_s2(set_name, uid); k = f"{set_name}__{uid}"
        if k in afmap and afmap[k].exists():
            x = json.load(open(afmap[k])); rec = FC.merge(rec, x if x.get("status") == "ok" else None)
        if k in sub:
            rec = FC.merge(rec, new_rec(sub[k]))
        return rec
    AU.stage2_rec = stage2_rec
    M.update(FC=FC, R220=R220, SUB=sub)
    _M.update(M)
    return _M


# ------------------------------------------------------------------ stage: manifests
def stage_manifests(a):
    MAN.mkdir(parents=True, exist_ok=True)
    R220, ties = gem_rows()
    for ds, rr in R220.items():
        with open(MAN / f"gt_rows_{ds.replace(' ', '_')}_v4.jsonl", "w") as f:
            for r in rr:
                f.write(json.dumps(r) + "\n")
    ties.to_csv(MAN / "gt_220_tie_events_excluded.csv", index=False)
    allm = [json.loads(l) for l in open(HERE / "manifests_v3/all.jsonl")]; allm = {m["uid"]: m for m in allm if m["source"] in ("ltx", "mova")}
    sp = {json.loads(l)["uid"] for s in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s}.jsonl")}
    cmp_ = []
    for ds, rr in R220.items():
        for r in rr:
            u = f"{SRC220[ds][2]}|{r['item_id']}|{r['axis']}"; m = allm.get(u)
            cmp_.append(dict(dataset=ds, uid=r["uid"], axis=r["axis"], events_v4=len(r["gt"]), in_all_jsonl=m is not None, in_gepa_split_files=u in sp,
                             events_all_jsonl=len(m["gt"]) if m else 0, same_gt_as_all_jsonl=bool(m and m["gt"] == r["gt"])))
    C = pd.DataFrame(cmp_); C.to_csv(MAN / "v4_vs_historical_220_rows.csv", index=False)
    # 2k_25 aggregation gaps: unchanged majority rule on the two annotated items without GT
    import prolific2k25_adapter_1104 as P, gen149_adapter_1030 as A149
    by = P.load(); rec = []
    for iid in ("fist_pose_x2__count", "peace_sign_left_x2__count_2"):
        last = {}
        for d in sorted(by.get(iid, []), key=lambda d: d.get("created_at", "")):
            last[d["user"]] = d
        anns = [d["annotations"] for d in last.values()]; a0 = anns[0]
        for e in a0["events"]:
            for ax in ("a", "v", "avb"):
                if e["axes"].get(ax):
                    ls = [l for l in (A149.lab(x["responses"]["events"].get(e["id"], {}).get(ax)) for x in anns) if l]
                    rec.append(dict(item=iid, axis=ax.upper(), event=e["id"], labels=";".join(ls), n=len(ls), majority=P.majority(ls) or "none (tie / too few)"))
        exp = a0["temporal_constraint"].get("expectedCounts") or {}
        for e, n in exp.items():
            ls = []
            for x in anns:
                try:
                    ls.append("yes" if int(str(x["responses"]["events"][e]["tcCount"]["value"]).strip()) == int(n) else "no")
                except (KeyError, ValueError, TypeError):
                    pass
            rec.append(dict(item=iid, axis="TCC", event=e, labels=";".join(ls), n=len(ls), majority=P.majority(ls) or "none (tie / too few)"))
        rt = a0["temporal_constraint"]["relationType"]
        if rt in P.RELATED:
            ls = [l for l in (A149.lab(x["responses"]["video"].get("tcRel")) for x in anns) if l]
            rec.append(dict(item=iid, axis="TCR", event="__item__", labels=";".join(ls), n=len(ls), majority=P.majority(ls) or "none (tie / too few)"))
    pd.DataFrame(rec).to_csv(MAN / "gt_2k25_gap_reaggregation.csv", index=False)
    # unified MOVA manifest with batch provenance and video identity
    H = pd.read_csv(MAN / "video_hashes.csv")
    mv = H[H.dataset.isin(["220 MOVA", "MOVA390"])].assign(batch=lambda t: t.dataset.map({"220 MOVA": "old 220 batch", "MOVA390": "prolific_mova_390"}),
                                                          dataset_final="MOVA")
    mv["duplicate_of_earlier_md5"] = mv.duplicated("md5")
    mv.to_csv(MAN / "mova_unified_videos.csv", index=False)
    lt = H[H.dataset.isin(["220 LTX", "149 LTX", "2k_25 LTX"])].assign(dataset_final="LTX", duplicate_of_earlier_md5=lambda t: t.duplicated("md5"))
    lt.to_csv(MAN / "ltx_videos.csv", index=False)
    S = dict(rows_v4={ds: len(rr) for ds, rr in R220.items()}, rows_not_in_gepa_split=int((~C.in_gepa_split_files).sum()), rows_not_in_all_jsonl=int((~C.in_all_jsonl).sum()),
             rows_gt_differs_from_all_jsonl=int((C.in_all_jsonl & ~C.same_gt_as_all_jsonl).sum()), tie_events_220=len(ties),
             mova_videos=len(mv), mova_duplicates=int(mv.duplicate_of_earlier_md5.sum()), ltx_videos=len(lt), ltx_duplicates=int(lt.duplicate_of_earlier_md5.sum()),
             gt_2k25_gaps_recovered_rows=int((pd.DataFrame(rec).majority.str.startswith("none") == False).sum()),
             historical_files_untouched=["manifests_v3/*.jsonl", "min3_gt/*", "gt_gen*.jsonl", "gt_mova390.jsonl"])
    json.dump(S, open(MAN / "manifest_summary.json", "w"), indent=1)
    print(json.dumps(S, indent=1)); print(pd.DataFrame(rec).to_string(index=False))


# ------------------------------------------------------------------ stage: calibration v2 (unchanged algorithm, corrected population)
def stage_calib(a):
    import p12_calib_1108 as P12
    d = OUT / "calibration_v2"; d.mkdir(parents=True, exist_ok=True)
    if (d / "frozen_p12_config.json").exists():
        sys.exit("v2 config exists; not overwritten")
    U = pd.read_csv(RUNS / "p12_calib_1108/p12_calibration_units.csv", low_memory=False)
    X = pd.read_csv(RUNS / "comprehensive_1108/part1_p12_avb_calibration_audit/excluded_avb_units_classified.csv", low_memory=False)
    R = X[X["class"].str.startswith("explicit")]
    key = {(r.source, r.item, r.event): r.restored_label for r in R.itertuples()}
    n = 0
    for i, r in U.iterrows():
        k = (r.source, r["item"], r.event)
        if r.axis == "AVB" and k in key and not bool(r.usable):
            U.at[i, "initial"] = key[k]; U.at[i, "missing"] = np.nan if pd.isna(r.off) is False else "no Synchformer record"; U.at[i, "usable"] = pd.notna(r.off); n += 1
    U.to_csv(d / "p12_calibration_units.csv", index=False)
    P12.OUT = d
    P12.stage_select(a)
    v1, v2 = json.load(open(CFG["v1"])), json.load(open(d / "frozen_p12_config.json"))
    rows = []
    for fam in v1["config"]:
        s1, s2 = v1["selection"].get(fam, {}), v2["selection"].get(fam, {})
        rows.append(dict(family=fam, v1_params=str(v1["config"][fam]["params"]), v2_params=str(v2["config"][fam]["params"]), v1_status=v1["config"][fam]["status"],
                         v2_status=v2["config"][fam]["status"], **{f"v1_{k}": s1.get(k) for k in ("opened", "k_risk", "n_risk", "risk_rate", "k_use", "n_use", "use_rate")},
                         **{f"v2_{k}": s2.get(k) for k in ("opened", "k_risk", "n_risk", "risk_rate", "k_use", "n_use", "use_rate")}))
    pd.DataFrame(rows).to_csv(d / "v1_vs_v2_selection.csv", index=False)
    json.dump(dict(restored_units=n, v1=str(CFG["v1"]), v2=str(d / "frozen_p12_config.json"), algorithm="p12_calib_1108.stage_select (unchanged)",
                   p12_script_md5=hashlib.md5(open(HERE / "p12_calib_1108.py").read().encode()).hexdigest(), evaluation_rows_read=False), open(d / "provenance.json", "w"), indent=1)
    print(pd.DataFrame(rows).to_string(index=False))


# ------------------------------------------------------------------ units (all datasets, four baseline conditions)
def units_all():
    M = setup(); AU, S6, FC = M["AU"], M["S6"], M["FC"]
    D = AU.datasets()
    U = pd.DataFrame(S6.av_events(D) + S6.ma_events() + S6.avb_events(D))
    rows = []
    for name, ds in D.items():
        for u in AU.units(name, ds):
            if u["axis"] not in ("TCR", "TCC"):
                continue
            el = AU.gt_eligible(ds, u); y = AU.gt_label(ds, u) if el else ""
            ev = u["uid"].split("|")[2] if u["axis"] == "TCC" else "video"
            for c in S6.CONDS:
                lu = AU.label_unit(ds, u, c) if el else dict(status="excluded", reason="GT prerequisite not met / not applicable")
                rows.append(dict(dataset=name, axis=u["axis"], unit=u["uid"], item=u["item"], event=ev, cond=c, gt_elig=el, gt_y=y, status=lu["status"],
                                 reason=lu.get("reason", ""), pred=lu.get("pred", ""), gate_open=False if c == "row5" else None))
    U = pd.concat([U, pd.DataFrame(rows)], ignore_index=True)
    ds390, gt390, ok390 = FC.mova390_ds(); keep = S6.av_rows
    N = FC.mova390_units(ds390, gt390); S6.av_rows = keep
    U = pd.concat([U, N], ignore_index=True)
    return U[U.dataset.isin(list(GROUP))].drop_duplicates(["dataset", "unit", "cond"])


def items_all():
    out = {}
    for k, f in (("220", REL500), ("149", (_tp.DATA + "/gen_holdout_149_1030/prompts_gen149.json")),
                 ("2k25", (_tp.DATA + "/gen_prolific2k25_1104/prompts_gen2k25.json")),
                 ("m390", (_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json"))):
        out[k] = {x["item_id"]: x for x in json.load(open(f))}
    return out


PSET = {"220 LTX": "220", "220 MOVA": "220", "149 LTX": "149", "2k_25 LTX": "2k25", "MOVA390": "m390"}
EVSRC = {"220 LTX": "g220ltx", "220 MOVA": "g220mova", "149 LTX": "g149", "2k_25 LTX": "g2k25", "MOVA390": "m390", "P03-P09": "hm_p3p9"}


def universe(U):
    """row-1-scored, GT-eligible units with the baseline labels and the frozen-config features."""
    import combined_fix_1108 as CF
    M = setup(); G, GPI = M["G"], M["GPI"]
    piv = {c: U[U.cond == c].set_index(["dataset", "unit"]) for c in ("row1", "row2", "row4", "row5")}
    gte = U[(U.cond == "row1") & U.gt_elig.astype(bool)].copy()
    B = gte.rename(columns={"gt_y": "gt"})[["dataset", "axis", "unit", "item", "event", "gt"]].copy()
    k = list(zip(B.dataset, B.unit))
    for c, nm in (("row1", "initial"), ("row2", "one_call"), ("row4", "always_shown"), ("row5", "original_gate")):
        B[nm] = [piv[c].pred.get(x) if piv[c].status.get(x) == "scored" else "" for x in k]
        B[nm + "_reason"] = [piv[c].reason.get(x) if piv[c].status.get(x) != "scored" else "" for x in k]
    B["orig_opened"] = [bool(piv["row5"].gate_open.get(x) == True) for x in k]
    IT = items_all(); SY = CF.sync_features()
    pe = pd.concat(pd.read_csv(f) for f in sorted(Path((_tp.DATA + "/tools/synchformer_gen_1030/mova390")).glob("per_event_shard*.csv")))
    pe = pe[pe.status == "ok"].drop_duplicates(["item_id", "event_id"]).set_index(["item_id", "event_id"])
    fam, fl, vc, off, prob = [], [], [], [], []
    for r in B.itertuples():
        f = x = y = o = p = None
        if r.axis == "A":
            if r.dataset == "P03-P09":
                f = "A sound"; fp = GPI.EV / "ma39" / f"ma39__{r.item}.json"
                fe = GPI.flam_evidence(json.load(open(fp)), r.event) if fp.exists() else None; x = fe["max_score"] if fe else None
            else:
                e = IT[PSET[r.dataset]][r.item]["events"][int(r.event.split("_")[1]) - 1]
                f = {"speech": "A speech", "sounding_action": "A sound"}.get(e["modality"])
                rec = G.evidence(EVSRC[r.dataset], r.item)
                fe = GPI.flam_evidence(rec, r.event) if (rec and f == "A sound") else None; x = fe["max_score"] if fe else None
        elif r.axis == "V":
            f = "V"; v = G.vcheck(f"{EVSRC[r.dataset]}|{r.item}|V"); y = v.get(r.event) if v else None
        elif r.axis == "AVB":
            f = "AVB"
            if r.dataset == "MOVA390":
                if (r.item, r.event) in pe.index:
                    o, p = abs(float(pe.offset.get((r.item, r.event)))), float(pe.prob.get((r.item, r.event)))
            elif (r.dataset, r.item, r.event) in SY.index:
                o, p = float(SY.off.get((r.dataset, r.item, r.event))), float(SY.prob.get((r.dataset, r.item, r.event)))
        fam.append(f); fl.append(x); vc.append(y); off.append(o); prob.append(p)
    B["family"], B["flam_max"], B["vcap"], B["off"], B["prob"] = fam, fl, vc, off, prob
    B["scored_row1"] = B.initial.isin(["yes", "no"])
    return B


def reuse_index():
    M = setup(); O = M["O"]
    idx = dict(json.load(open(RUNS / "p12_calib_1108/reuse_index.json")))
    def ok(r):
        return r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5 and r.get("model", MODEL) == MODEL and r.get("thinking", "high") == "high"
    for d in ("p12_calib_1108/calls", "avb_anchorfix_1108/calls"):
        for p in (RUNS / d).glob("*.json"):
            r = json.load(open(p))
            if ok(r):
                idx.setdefault(r["user_md5"], str(p))
    for p in glob.glob(str(RUNS / "calls/gen_tool_text/*.json")):
        try:
            r = json.load(open(p))
        except Exception:
            continue
        if ok(r):
            idx.setdefault(r["user_md5"], p)
    for base in (RUNS / "final_cov_1108/calls", CALLS):
        for p in base.glob("FC__*.json") if base.exists() else []:
            att = [x for x in json.load(open(p))["attempts"] if x.get("complete")]
            if att:
                idx.setdefault(att[-1]["user_md5"], ("attempts", str(p)))
        for p in base.glob("NB__*.json") if base.exists() else []:
            att = [x for x in json.load(open(p))["attempts"] if x.get("complete")]
            if att:
                idx.setdefault(att[-1]["user_md5"], ("attempts", str(p)))
    return idx


def load_idx(v):
    if isinstance(v, (list, tuple)):
        att = [x for x in json.load(open(v[1]))["attempts"] if x.get("complete")]
        return att[-1] if att else None
    r = json.load(open(v)); return r if r.get("status") == "ok" else None


def failed_md5():
    """prompts already tried MAXTRY times without a complete output (final_cov_1108 or this run): unresolved, not re-planned."""
    out = set()
    for base in (RUNS / "final_cov_1108/calls", CALLS):
        for p in base.glob("*.json") if base.exists() else []:
            d = json.load(open(p)); att = d["attempts"]
            if len(att) >= MAXTRY and not any(x.get("complete") for x in att):
                out.add(att[-1].get("user_md5") or "")
    return out


def opened(B, cfg):
    import p12_calib_1108 as P12
    res = [P12.open_rule(cfg, r) if r.scored_row1 else (False, "", "no media-only label") for r in B.itertuples()]
    return [x[0] for x in res], [x[1] for x in res], [x[2] for x in res]


def comb_call(dsn, item, ax, events):
    M = setup(); BF, O = M["BF"], M["O"]
    text, s_ = BF.payload(dsn, ax, item, {e: ("A sound" if ax == "A" else ax) for e in events})
    uid = f"{s_}|{item}|{ax}"
    if text is None:
        return None, uid, "missing payload"
    cc = O.build_call(dict(set="PC", source=s_, uid=uid, item_id=item, axis=ax, variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text}))
    return cc, uid, ("no stage-1 anchor" if cc is None else "")


# ------------------------------------------------------------------ stage: plan
def stage_plan(a):
    M = setup(); AU, O, G, S6, FC = (M[k] for k in ("AU", "O", "G", "S6", "FC"))
    import allfour_1105 as AF4
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "prompts").mkdir(exist_ok=True)
    idx, bad = reuse_index(), failed_md5(); plan = []
    IT = items_all()

    def add(purpose, ds, item, axis, uid, cc, need, sub_key="", kind="stage2"):
        md5 = hashlib.md5(cc["user"].encode()).hexdigest()
        key = f"VC__{uid}" if kind == "vcheck" else f"NB__{md5}"
        if md5 in bad:
            plan.append(dict(purpose=purpose, dataset=ds, item=item, axis=axis, uid=uid, user_md5=md5, key=key, sub_key=sub_key, action="unresolved earlier (3 failed attempts); not re-run")); return
        hit = idx.get(md5) if kind == "stage2" else None; reuse = False
        if hit:
            rec = load_idx(hit)
            if rec is not None:
                rec = dict(rec); rec.setdefault("anchor", cc.get("anchor", [])); reuse = FC.complete(rec, axis, need)
        if not reuse:
            json.dump(dict(uid=uid, item=item, axis=axis, kind=kind, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5, anchor=cc.get("anchor", []),
                           need=need), open(OUT / "prompts" / f"{key.replace('/', '_')}.json", "w"))
        plan.append(dict(purpose=purpose, dataset=ds, item=item, axis=axis, uid=uid, user_md5=md5, key=key, sub_key=sub_key, prompt_chars=len(cc["system"]) + len(cc["user"]),
                         reuse_file=str(hit[1] if isinstance(hit, tuple) else hit) if reuse else "", action="reuse (exact complete output)" if reuse else "new call"))
    R220 = M["R220"]
    # (1) caption checks for 220 V rows lacking a verdict for any GT event
    for ds, rr in R220.items():
        for r in rr:
            if r["axis"] != "V":
                continue
            v = G.vcheck(r["uid"]) or {}
            if all(e in v for e in r["gt"]):
                continue
            c = G.caption(r["source"], r["item_id"])
            if c is None:
                plan.append(dict(purpose="220 caption check", dataset=ds, item=r["item_id"], axis="V", uid=r["uid"], action="no caption")); continue
            evs = IT["220"][r["item_id"]]["events"]; ids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(evs)}
            lines = [f"- {ids[e['id']]}: {e['definition']}" for e in evs if ids[e["id"]] in r["gt"]]
            user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() + "\n\nTarget visual events:\n" + "\n".join(lines) +
                    "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
                    "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
                    "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
                    "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
            add("220 caption check", ds, r["item_id"], "V", r["uid"], dict(system=G.VCHK_SYSTEM, user=user, schema=G.VCHK_SCHEMA), None, kind="vcheck")
    # (2) 220 stage-2 rows without an ok record: G4 (A, V; AVB when the pre-registered rule fires), G5 (A gated text), GA4 (AVB, TCR, TCC)
    D = AU.datasets()
    for ds, rr in R220.items():
        src = SRC220[ds][0]
        for r in rr:
            iid, ax, uid = r["item_id"], r["axis"], r["uid"]
            need_sets = []
            if ax in ("A", "V"):
                need_sets.append(("G4", {"A": G.a_text, "V": G.v_text}[ax](src, iid)))
            if ax == "A":
                g5, g4 = G.a_text(src, iid, gated=True), G.a_text(src, iid)
                if g5 and g5 != g4:
                    need_sets.append(("G5", g5))
            if ax == "AVB" and D[ds]["fires"](iid):
                need_sets.append(("G4", G.avb_text(src, iid)))
            if ax in ("AVB", "TCR", "TCC"):
                b, how = AF4.block(src, iid)
                if b:
                    b, _ = AF4.v_style(b); need_sets.append(("GA4", "Observation (tool output):\n" + b))
            for st, text in need_sets:
                old = AU.stage2_rec(st, uid)
                if old is not None or not text:
                    continue
                row = dict(set=st, source=src, uid=uid, item_id=iid, axis=ax, variant=SRC220[ds][1], gt=r["gt"], clip=iid, cond="gen_tool_text", obs={"text": text})
                cc = O.build_call(row)
                if cc is None:
                    plan.append(dict(purpose=f"220 {st}", dataset=ds, item=iid, axis=ax, uid=uid, action="no stage-1 anchor")); continue
                add(f"220 {st} (restored row)", ds, iid, ax, uid, cc, [e["event_id"] for e in cc["anchor"]] if ax != "TCR" else None, sub_key=f"{st}__{uid}")
    # (3) combined gate (v2 config) and v1 reproduction: every opened (dataset, item, axis)
    U = units_all(); B = universe(U)
    for ver in ("v1", "v2"):
        if not CFG[ver].exists():
            continue
        cfg = json.load(open(CFG[ver]))["config"]
        B["op"], _, _ = opened(B, cfg)
        for (dsn, item, ax), g in B[B.op].groupby(["dataset", "item", "axis"]):
            cc, uid, why = comb_call(dsn, item, ax, sorted(set(g.event)))
            if cc is None:
                plan.append(dict(purpose=f"combined {ver}", dataset=dsn, item=item, axis=ax, uid=uid, action=why)); continue
            add(f"combined {ver}", dsn, item, ax, uid, cc, sorted(set(g.event)))
    P = pd.DataFrame(plan).drop_duplicates(["purpose", "dataset", "item", "axis", "key"])
    P.to_csv(OUT / f"call_plan_{time.strftime('%H%M%S')}.csv", index=False); P.to_csv(OUT / "call_plan.csv", index=False)
    old = json.load(open(OUT / "substitutions.json")) if (OUT / "substitutions.json").exists() else {}
    old.update({r.sub_key: r.key for r in P.itertuples() if isinstance(r.sub_key, str) and r.sub_key and r.action == "new call"})
    json.dump(old, open(OUT / "substitutions.json", "w"), indent=1)
    b = json.load(open(RUNS / "bidir_full_1107/estimate_basis.json"))
    new = P[P.action == "new call"].drop_duplicates("key"); new = new[[not (CALLS / f"{k.replace('/', '_')}.json").exists() for k in new.key]]
    est = dict(unique_new_calls_to_make=len(new), est_usd_list=round(new.prompt_chars.sum() / b["chars_per_token"] / 1e6 * 1.5 + b["output_tokens_median"] * len(new) / 1e6 * 7.5, 2))
    json.dump(est, open(OUT / "estimate.json", "w"), indent=1)
    pd.set_option("display.width", 250); print(P.groupby(["purpose", "action"]).size().to_string()); print(est)


# ------------------------------------------------------------------ stage: run (same runner rules as final_cov_1108)
def stage_run(a):
    M = setup(); O, FC = M["O"], M["FC"]
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    import threading
    P = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = P[P.action == "new call"].drop_duplicates("key")
    CALLS.mkdir(exist_ok=True)
    if (OUT / "HOLD").exists():
        sys.exit("HOLD file present; not running")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); stop = threading.Event(); n = collections.Counter(); t0 = time.time()

    def one(c):
        if stop.is_set():
            return "skipped (hold)"
        f = CALLS / f"{c.key.replace('/', '_')}.json"
        att = json.load(open(f))["attempts"] if f.exists() else []
        if any(x.get("complete") for x in att) or len(att) >= MAXTRY:
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.key.replace('/', '_')}.json"))
        while len(att) < MAXTRY and not stop.is_set():
            r = dict(uid=c.uid, obs={})
            try:
                parsed, raw = O.call(client, MODEL, dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
                rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], anchor=p["anchor"])
                if p["kind"] == "vcheck":
                    got = {e.get("event_id"): e.get("verdict") for e in (parsed or {}).get("per_event", [])}
                    want = [l.split(":")[0][2:] for l in p["user"].split("Target visual events:\n")[1].split("\n\n")[0].split("\n")]
                    rec["complete"] = all(got.get(w) in ("describes", "contradicts", "not_mentioned") for w in want)
                else:
                    rec["complete"] = FC.complete(rec, p["axis"], [e or None for e in p["need"]] if p["need"] else None)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                rec = dict(status="error", error=msg[:2000], complete=False, usage=r.get("_usage"))
                if BILL.search(msg):
                    stop.set(); (OUT / "HOLD").write_text(f"HOLD {time.strftime('%Y-%m-%dT%H:%M:%S')}: billing / spending-cap error on {c.uid}; no key rotation\n")
            rec.update(uid=c.uid, model=MODEL, thinking="high", rules_md5=O.OBS_RULES_MD5, attempt=len(att) + 1, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
            att.append(rec); json.dump(dict(key=c.key, uid=c.uid, attempts=att), open(f, "w"), default=str)
            if rec.get("complete") or (rec["status"] == "error" and BILL.search(rec.get("error", ""))):
                break
        return "ok" if att and att[-1].get("complete") else ("hold" if stop.is_set() else "unresolved")
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 25 == 0 or i + 1 == len(todo):
                print(f"[final_benchmark] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), hold=stop.is_set(), time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(OUT / f"run_info_{time.strftime('%H%M%S')}.json", "w"), indent=1)
    print("[DONE]", dict(n), "HOLD" if stop.is_set() else "")


# ------------------------------------------------------------------ stage: score
def comb_labels(B, cfg, idx):
    M = setup(); AU = M["AU"]
    op, bk, fb = opened(B, cfg); B = B.copy(); B["comb_opened_raw"] = op
    cache, lab, src = {}, [], []
    for x, o in zip(B.to_dict("records"), op):
        if not x["scored_row1"]:
            lab.append(""); src.append("no media-only label"); continue
        if x["family"] == "A speech":
            lab.append(x["original_gate"]); src.append("A speech: original paper gate (inherited)"); continue
        if not o:
            lab.append(x["initial"]); src.append("closed: media-only label"); continue
        k = (x["dataset"], x["item"], x["axis"])
        if k not in cache:
            evs = sorted(set(B[(B.dataset == k[0]) & (B["item"] == k[1]) & (B.axis == k[2]) & np.array(op)].event))
            cc, uid, why = comb_call(k[0], k[1], k[2], evs)
            rec = None
            if cc is not None:
                md5 = hashlib.md5(cc["user"].encode()).hexdigest(); h = idx.get(md5)
                rec = load_idx(h) if h else None
                if rec is not None:
                    rec = dict(rec); rec.setdefault("anchor", cc["anchor"])
            cache[k] = rec
        l, st = AU.s2_event(cache[k], x["axis"], x["event"])
        ok = st == "ok" and l in ("yes", "no")
        lab.append(l if ok else ""); src.append("open: stage-2 label" if ok else f"open: unresolved ({st})")
    return lab, src, op


def stage_score(a):
    import comprehensive_report_1108 as CR
    M = setup()
    U = units_all(); U.to_csv(OUT / "units_all_conditions.csv", index=False)
    B = universe(U); idx = reuse_index()
    for ver in ("v1", "v2"):
        cfg = json.load(open(CFG[ver]))["config"]
        lab, src, op = comb_labels(B, cfg, idx)
        B[f"combined_{ver}"], B[f"combined_{ver}_source"], B[f"comb_opened_{ver}"] = lab, src, op
        B[f"comb_opened_{ver}"] = [bool(o) or (f == "A speech" and oo) for o, f, oo in zip(op, B.family, B.orig_opened)]
    B["combined"], B["comb_opened"] = B.combined_v2, B.comb_opened_v2
    snd_or_avb = ((B.axis == "A") & (B.family == "A sound")) | (B.axis == "AVB")
    B["ablation"] = np.where(snd_or_avb, B.combined, B.initial); B["abl_opened"] = snd_or_avb & B.comb_opened.astype(bool)
    # previous final labels (old universe) for a reproduction check of v1
    PREV = pd.read_csv(RUNS / "final_cov_1108/all_units_five_methods.csv", low_memory=False).set_index(["dataset", "unit"])
    rep = []
    for (d, ax), q in B.groupby(["dataset", "axis"]):
        k = [x for x in zip(q.dataset, q.unit) if x in PREV.index]
        if not k:
            continue
        old = PREV.loc[k]; new = q.set_index(["dataset", "unit"]).loc[k]
        for c_new, c_old in (("initial", "initial"), ("one_call", "one_call"), ("always_shown", "always_shown"), ("original_gate", "original_gate"), ("combined_v1", "combined")):
            rep.append(dict(dataset=d, axis=ax, method=c_new, units=len(k), identical=int((old[c_old].fillna("").values == new[c_new].fillna("").values).sum())))
    pd.DataFrame(rep).to_csv(OUT / "reproduction_check_vs_previous.csv", index=False)
    # fixed GT-eligible universe with answer categories
    gte = U[(U.cond == "row1") & U.gt_elig.astype(bool)].set_index(["dataset", "unit"])
    G_ = B.copy(); G_["group"] = G_.dataset.map(GROUP); G_["batch"] = G_.dataset
    for col, c in (("initial", "row1"), ("one_call", "row2"), ("always_shown", "row4"), ("original_gate", "row5")):
        G_[col + "_cat"] = ["answered" if v in ("yes", "no") else (CR.reason_class(r) or "technical missing / failed output") for v, r in zip(G_[col], G_[col + "_reason"])]
    for col in ("combined", "ablation"):
        G_[col + "_cat"] = ["answered" if v in ("yes", "no") else (ic if ic != "answered" else "technical missing / failed output") for v, ic in zip(G_[col], G_.initial_cat)]
    IT = items_all()
    G_["a_kind"] = ["" if ax != "A" else ("sounding" if f == "A sound" else "speech" if f == "A speech" else str(f)) for ax, f in zip(G_.axis, G_.family)]
    G_.to_csv(OUT / "unit_results_final.csv", index=False)
    run_views(G_, CR)
    cost(G_)
    print(pd.read_csv(OUT / "reproduction_check_vs_previous.csv").groupby("method")[["units", "identical"]].sum())


def run_views(G_, CR):
    T = G_.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind
    T = pd.concat([T, TA], ignore_index=True)
    meth = [("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("original_gate", "original paper gate"),
            ("combined", "combined gate (v2 frozen)"), ("ablation", "FLAM+Synchformer ablation (v2 frozen)")]
    cols = [c for c, _ in meth]; nm = dict(meth)
    v1, v2, v3, five, pc, br, man = [], [], [], [], [], [], []
    for (k, ax), q in T.groupby(["group", "axis_view"]):
        common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in cols])]
        common5 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in cols[:5]])]
        man += [dict(group=k, axis_view=ax, subset=s, dataset=d, unit=u) for s, h in (("six-method common", common), ("five-method common", common5)) for d, u in zip(h.dataset, h.unit)]
        for c in cols:
            b = dict(group=k, axis=ax, method=nm[c]); val = q[q[c].isin(["yes", "no"])]
            v1.append(dict(b, view="1 per-method valid responses", **CR.metrics(val["gt"], val[c])))
            v2.append(dict(b, view="2 identical six-method common subset", **CR.metrics(common["gt"], common[c])))
            five.append(dict(b, view="continuity: five-method common subset", **CR.metrics(common5["gt"], common5[c])))
            cat = q[c + "_cat"]; ok = q[c].isin(["yes", "no"])
            v3.append(dict(b, view="3 fixed GT-eligible universe", gt_eligible=len(q), answered=int(ok.sum()), correct=int((ok & (q[c] == q["gt"])).sum()),
                           correct_over_total=(ok & (q[c] == q["gt"])).sum() / len(q) if len(q) else np.nan, coverage=ok.mean() if len(q) else np.nan,
                           model_prerequisite_skip=int((cat == "model prerequisite skip").sum()), model_abstention_no_usable_label=int((cat == "model abstention / no usable label").sum()),
                           technical_missing_failed=int((cat == "technical missing / failed output").sum()), other=int((~ok & ~cat.isin(["model prerequisite skip", "model abstention / no usable label", "technical missing / failed output"])).sum())))
        for new in ("combined", "ablation"):
            for ref in cols:
                if ref == new:
                    continue
                m_ = q[q[ref].isin(["yes", "no"]) & q[new].isin(["yes", "no"])]; o_, n_ = m_[ref] == m_["gt"], m_[new] == m_["gt"]
                pc.append(dict(group=k, axis=ax, method=nm[new], vs=nm[ref], matching_units=len(m_), corrections=int((~o_ & n_).sum()), corruptions=int((o_ & ~n_).sum())))
        sc = q[q.initial.isin(["yes", "no"])]
        for g, col, opc in (("original paper gate", "original_gate", "orig_opened"), ("combined gate (v2)", "combined", "comb_opened"),
                            ("combined gate (v1, historical)", "combined_v1", "comb_opened_v1"), ("ablation (v2)", "ablation", "abl_opened")):
            for bname, h in sc.groupby(np.where(sc.initial == "yes", "initial PASS (FAIL-evidence branch)", "initial FAIL (PASS-evidence branch)")):
                op = h[h[opc].astype(bool)]; s2 = op[op[col].isin(["yes", "no"])]
                br.append(dict(group=k, axis=ax, gate=g, branch=bname, units=len(h), opened=len(op), opened_unresolved=len(op) - len(s2), label_changed=int((s2[col] != s2.initial).sum()),
                               corrections=int(((s2.initial != s2["gt"]) & (s2[col] == s2["gt"])).sum()), corruptions=int(((s2.initial == s2["gt"]) & (s2[col] != s2["gt"])).sum())))
    o = OUT / "tables"; o.mkdir(exist_ok=True)
    for nm_, rows in (("view1_per_method_valid_responses", v1), ("view2_identical_common_subset", v2), ("view3_fixed_gt_eligible_universe", v3),
                      ("continuity_five_method_common_subset", five), ("paired_corrections_corruptions", pc), ("gate_openings_by_branch", br)):
        pd.DataFrame(rows).to_csv(o / f"{nm_}.csv", index=False)
    pd.DataFrame(man).to_csv(OUT / "subset_manifests.csv", index=False)


def cost(G_):
    us = []
    for f in CALLS.glob("*.json"):
        us += [x.get("usage") or {} for x in json.load(open(f))["attempts"]]
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    unres = [dict(key=json.load(open(f))["key"], uid=json.load(open(f))["uid"], attempts=len(json.load(open(f))["attempts"])) for f in CALLS.glob("*.json")
             if not any(x.get("complete") for x in json.load(open(f))["attempts"])]
    json.dump(dict(this_run_prompts=len(list(CALLS.glob("*.json"))), attempts=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3),
                   unresolved_this_run=unres), open(OUT / "cost_this_run.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["manifests", "calib", "plan", "run", "score"]); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
