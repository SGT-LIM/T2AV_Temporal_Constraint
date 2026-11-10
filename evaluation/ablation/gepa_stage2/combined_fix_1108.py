#!/usr/bin/env python3
"""Frozen combined gate recomputed with the corrected AVB scorer (11/08). No API / GPU calls; no rule changes; originals untouched.
Combined gate (frozen): A speech = original paper Whisper gate (inherited); A sound = P01/P02 FLAM rules; V = P01/P02-validated
contradicts / describes; AVB = P01/P02 rules (|off| >= 1.2 & conf >= .1278 for initial PASS; |off| <= 0.2 & conf >= .3221 for initial FAIL);
TC / TR no gate.
AVB: universe and all four baseline conditions from avb_skipfix_1108 (corrected scorer). Closed gate -> restored media-only label;
open -> exact-prompt cached stage-2 label (bidir payload, obs_judge_1028.build_call; reuse index of p12_calib_1108). Every AVB gap of the
new gate, the original gate and always shown is classified: no cached call / cached call without an entry for the event (restored events
are absent from the stage-2 anchor because run_two_stage.stage1_lookup applies the same SKIP_RE) / no stage-1 anchor.
A, V, TC / TR: unchanged (the AVB fix does not touch them) -> p12_combo_1108/combined_unit_results.csv.
  python gepa_stage2/combined_fix_1108.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import glob, hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "combined_fix_1108"
SYA = Path((_tp.DATA + "/tools/synchformer_action_1030"))
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA (old 220)", "P03-P09": "P03-P09"}


def sync_features():
    hd = pd.concat(pd.read_csv(f) for f in sorted((SYA / "holdout").glob("per_event_shard*.csv")))
    hd = hd[hd.status == "ok"].drop_duplicates(["item_id", "event_id"]).assign(dataset="P03-P09")
    hd = hd.rename(columns={"item_id": "item", "event_id": "event"}).assign(off=lambda t: t.offset.abs())[["dataset", "item", "event", "off", "prob"]]
    sg = pd.read_csv(RUNS / "flam_sync_audit_1106/events.csv")
    sg["dataset"] = sg.apply(lambda r: {"220": f"220 {'LTX' if r.model == 'LTX_2p3' else 'MOVA'}", "149": "149 LTX", "gen2k25": "2k_25 LTX"}[str(r.set)], axis=1)
    sg = sg[sg.lag.notna()].rename(columns={"item_id": "item", "event_id": "event"}).assign(off=lambda t: t.lag.abs(), prob=lambda t: t.conf)
    return pd.concat([hd, sg[["dataset", "item", "event", "off", "prob"]].drop_duplicates(["dataset", "item", "event"])]).set_index(["dataset", "item", "event"])


def main():
    import obs_judge_1028 as O, audit_1106 as AU, bidir_full_1107 as BF
    import gen2k25_stage2_1104  # noqa: F401
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(RUNS / "p12_calib_1108/frozen_p12_config.json"))["config"]
    pF, pP = cfg["AVB_FAIL"]["params"], cfg["AVB_PASS"]["params"]
    T = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False)
    piv = {c: T[T.cond == c].set_index(["dataset", "unit"]) for c in ("row1", "row2", "row4", "row5")}
    base = piv["row1"]; base = base[(base.status == "scored")].reset_index()
    S = pd.read_csv(RUNS / "gate_pilot_1106/split.csv")
    M = base[["dataset", "unit", "item", "event", "gt_y", "pred"]].rename(columns={"gt_y": "gt", "pred": "initial"}).merge(S[["dataset", "item", "portion"]], on=["dataset", "item"], how="left")
    for c, nm in (("row2", "one_call"), ("row4", "always_shown"), ("row5", "original_gate")):
        M[nm] = [piv[c].pred.get((d, u)) if piv[c].status.get((d, u)) == "scored" else "" for d, u in zip(M.dataset, M.unit)]
        M[nm + "_reason"] = [piv[c].reason.get((d, u)) if piv[c].status.get((d, u)) != "scored" else "" for d, u in zip(M.dataset, M.unit)]
    old_r1 = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False)
    old_r1 = set(map(tuple, old_r1[(old_r1.group == old_r1.dataset) & (old_r1.axis == "AVB") & (old_r1.cond == "row1") & (old_r1.status == "scored")][["dataset", "unit"]].values))
    M["restored_unit"] = [(d, u) not in old_r1 for d, u in zip(M.dataset, M.unit)]
    F = sync_features()
    M["off"] = [F.off.get((d, i, e)) for d, i, e in zip(M.dataset, M["item"], M.event)]; M["prob"] = [F.prob.get((d, i, e)) for d, i, e in zip(M.dataset, M["item"], M.event)]
    M["opened"] = [bool(pd.notna(o) and ((ini == "yes" and o >= pF[1] and p >= pF[3]) or (ini == "no" and o <= pP[1] and p >= pP[3]))) for ini, o, p in zip(M.initial, M.off, M.prob)]
    idx = json.load(open(RUNS / "p12_calib_1108/reuse_index.json"))
    for p in (RUNS / "p12_calib_1108/calls").glob("*.json"):
        r = json.load(open(p))
        if r.get("status") == "ok" and r.get("user_md5"):
            idx.setdefault(r["user_md5"], str(p))
    cache, lab, src = {}, [], []
    for x in M.to_dict("records"):
        if not x["opened"]:
            lab.append(x["initial"]); src.append("closed: restored media-only label" if x["restored_unit"] else "closed: media-only label"); continue
        k = (x["dataset"], x["item"])
        if k not in cache:
            text, s_ = BF.payload(x["dataset"], "AVB", x["item"], {x["event"]: "AVB"})
            cc = None if text is None else O.build_call(dict(set="CF", source=s_, uid=f"{s_}|{x['item']}|AVB", item_id=x["item"], axis="AVB", variant="pilot", gt={}, clip=x["item"], cond="gen_tool_text", obs={"text": text}))
            if text is None:
                cache[k] = ("missing payload", None, 0)
            elif cc is None:
                cache[k] = ("no stage-1 anchor (no AVB event of the item in the anchor)", None, 0)
            else:
                md5 = hashlib.md5(cc["user"].encode()).hexdigest(); f = idx.get(md5)
                rec = json.load(open(f)) if f else None
                if rec is not None and "anchor" not in rec:
                    rec["anchor"] = O.anchor_entries(s_, x["item"], "AVB")
                cache[k] = ("cached" if rec else "no cached call for the exact prompt", rec, len(cc["system"]) + len(cc["user"]))
        st, rec, _ = cache[k]
        if rec is None:
            lab.append(""); src.append(f"open: missing ({st})"); continue
        l, s2 = AU.s2_event(rec, "AVB", x["event"])
        if s2 == "ok" and l in ("yes", "no"):
            lab.append(l); src.append("open: cached stage-2 label")
        else:
            lab.append(""); src.append("open: missing (cached call has no entry for this event: absent from the stage-2 anchor)" if s2 == "no_stage2_entry" else f"open: missing ({s2})")
    M["combined"] = lab; M["combined_source"] = src; M["axis"] = "AVB"; M["group"] = M.dataset.map(GROUP)
    M.to_csv(OUT / "avb_combined_unit_results.csv", index=False)
    # other axes: unchanged combined results
    Oth = pd.read_csv(RUNS / "p12_combo_1108/combined_unit_results.csv", low_memory=False)
    Oth = Oth[Oth.axis != "AVB"][["dataset", "group", "unit", "item", "event", "axis", "portion", "gt", "initial", "one_call", "always_shown", "original_gate", "combined"]]
    ALL = pd.concat([Oth, M[Oth.columns.tolist() + ["restored_unit", "opened", "combined_source"]]], ignore_index=True)
    ALL.to_csv(OUT / "all_axes_combined_unit_results.csv", index=False)
    pipes = [("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("original_gate", "original paper gate"), ("combined", "combined gate")]
    rows, pc = [], []
    for kk in (("dataset", "axis"), ("group", "axis"), ("dataset", "portion", "axis")):
        for key, q in ALL.groupby(list(kk)):
            common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c, _ in pipes])]
            for col, nm in pipes:
                m = BF.metrics(common["gt"], common[col])
                rows.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), method=nm, eligible_row1=len(q), common_units=len(common),
                                 acc=m.get("acc"), macro_F1=m.get("macro_F1"), bal_acc=m.get("bal_acc"), FAIL_R=m.get("FAIL_R"), FA=m.get("FA"),
                                 FAIL_P=m.get("FAIL_P"), FAIL_F1=m.get("FAIL_F1"), PASS_P=m.get("PASS_P"), PASS_R=m.get("PASS_R"), PASS_F1=m.get("PASS_F1")))
            for ref, rn in pipes[:4]:
                o_, n_ = common[ref] == common["gt"], common["combined"] == common["gt"]
                pc.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), vs=rn, common_units=len(common), corrections=int((~o_ & n_).sum()), corruptions=int((o_ & ~n_).sum())))
    pd.DataFrame(rows).to_csv(OUT / "metrics_five_methods.csv", index=False); pd.DataFrame(pc).to_csv(OUT / "paired_changes.csv", index=False)
    # missing calls to complete AVB coverage
    b = json.load(open(RUNS / "bidir_full_1107/estimate_basis.json")); med_chars = float(np.median([v[2] for v in cache.values() if v[2]])) if cache else 15000
    need = []
    nm = M[M.combined == ""]
    for (d, i), g in nm.groupby(["dataset", "item"]):
        need.append(dict(method="combined gate", dataset=d, item=i, units=len(g), reason=g.combined_source.iloc[0].replace("open: missing ", "")))
    for col, mth in (("original_gate", "original paper gate"), ("always_shown", "always shown")):
        g0 = M[(M[col] == "") & M[col + "_reason"].fillna("").str.contains("stage-2")]
        for (d, i), g in g0.groupby(["dataset", "item"]):
            need.append(dict(method=mth, dataset=d, item=i, units=len(g), reason=g[col + "_reason"].iloc[0]))
    N = pd.DataFrame(need); N.to_csv(OUT / "missing_calls.csv", index=False)
    est = []
    for (mth, rs), g in (N.groupby(["method", "reason"]) if len(N) else []):
        n = len(g); ti, to = n * med_chars / b["chars_per_token"], n * b["output_tokens_median"]
        est.append(dict(method=mth, reason=rs, calls=n, units=int(g.units.sum()), est_input_tokens=int(ti), est_output_tokens=int(to), est_usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 2)))
    E = pd.DataFrame(est); E.to_csv(OUT / "missing_calls_estimate.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(M.combined_source.value_counts().to_string()); print(E.to_string(index=False)); print("total calls", int(E.calls.sum()) if len(E) else 0, "usd", round(E.est_usd_list.sum(), 2) if len(E) else 0)


if __name__ == "__main__":
    main()
