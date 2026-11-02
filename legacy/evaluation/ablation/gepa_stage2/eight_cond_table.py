#!/usr/bin/env python3
"""All 8 conditions on the same test (1,088 rows): acc / precision / recall with FAIL ("no") as the positive class.
Item level (an item is FAIL if any judged event is "no"), per source x axis; HD-EPIC also per variant (recall of FAIL
on broken variants, false-alarm rate on originals), 220 per model.
Run from evaluation/ablation:  python gepa_stage2/eight_cond_table.py > gepa_stage2/runs/eight_cond_table.txt
Conditions: 1 s1v_seed  2 s1v_gepa  (stage 1, video only)      3 s1t_seed  4 s1t_gepa  (stage 1 + tools, one call)
            5 s2_seed   6 s2_gepa   (stage 2, axis-wise)       7 orch_seed 8 orch_gepa (stage 2, orchestrator)"""
import json, sys
from pathlib import Path
import pandas as pd

R = Path("gepa_stage2/runs")
AXES = ["A", "V", "AVB", "TCR", "TCC"]
COND = {}
for ax in AXES:
    COND[("s1v_seed", ax)] = R / f"s1video_{ax}/heldout_test_seed.csv"
    COND[("s1v_gepa", ax)] = R / f"s1video_{ax}/heldout_test_best.csv"
    COND[("s1t_seed", ax)] = R / f"s1tools_{ax}/heldout_test_seed.csv"
    COND[("s1t_gepa", ax)] = R / f"s1tools_{ax}/heldout_test_best.csv"
for tag, f in (("s2_seed", "heldout_test_seed"), ("s2_gepa", "heldout_test_best")):
    for ax in AXES: COND[(tag, ax)] = R / f"s0_s1test/{f}.csv"
for tag, f in (("orch_seed", "heldout_test_orch_seed"), ("orch_gepa", "heldout_test_orch_best")):
    for ax in AXES: COND[(tag, ax)] = R / f"orch_s1test/{f}.csv"
ORDER = ["s1v_seed", "s1v_gepa", "s1t_seed", "s1t_gepa", "s2_seed", "s2_gepa", "orch_seed", "orch_gepa"]

def item_table(csv, ax):
    df = pd.read_csv(csv); df = df[df.axis == ax]
    g = df.groupby("uid")
    t = g[["source", "axis", "variant", "eval_only"]].first()
    t["pred"] = g["pred"].apply(lambda s: "no" if (s == "no").any() else ("yes" if (s == "yes").any() else ""))
    t["gt"] = g["gt"].apply(lambda s: "no" if (s == "no").any() else "yes")
    return t

tabs = {}
for (tag, ax), p in COND.items():
    if p.exists():
        tabs[(tag, ax)] = item_table(p, ax)

def prf(t):
    """FAIL = positive. acc over all; precision = P(gt no | pred no); recall = P(pred no | gt no); far = P(pred no | gt yes)."""
    y, p = (t["gt"] == "no"), (t.pred == "no")
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    n = len(t)
    acc = (tp + tn) / n if n else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    far = fp / (fp + tn) if (fp + tn) else float("nan")
    return acc, prec, rec, far, n, int(y.sum())

def fmt(v): return "  -  " if pd.isna(v) else f"{v:.2f}"

print("== item-level, FAIL = positive class.  acc | prec | rec | FAR(false alarm rate)   [n items, n FAIL]")
for src in ("hdepic", "ltx", "mova"):
    print(f"\n#### {src}")
    for ax in AXES:
        print(f"-- {ax}")
        for tag in ORDER:
            t = tabs.get((tag, ax))
            if t is None: continue
            t = t[t.source == src]
            if not len(t): continue
            acc, prec, rec, far, n, nf = prf(t)
            print(f"   {tag:10s} acc {fmt(acc)}  prec {fmt(prec)}  rec {fmt(rec)}  FAR {fmt(far)}   [{n}, {nf}]")

print("\n\n== HD-EPIC per variant: fraction judged FAIL (broken variant -> recall; original / eval_only -> false alarm)")
hd_rows = []
for ax in AXES:
    for tag in ORDER:
        t = tabs.get((tag, ax))
        if t is None: continue
        t = t[t.source == "hdepic"]
        for (var, eo), g in t.groupby(["variant", "eval_only"]):
            hd_rows.append(dict(axis=ax, variant=var + (" (eval_only)" if eo else ""), cond=tag, n=len(g), fail=(g.pred == "no").mean()))
hd = pd.DataFrame(hd_rows)
if len(hd):
    piv = hd.pivot_table(index=["axis", "variant", "n"], columns="cond", values="fail").reindex(columns=[c for c in ORDER if c in hd.cond.unique()])
    pd.set_option("display.width", 250)
    print(piv.round(2).to_string())

print("\n\n== 220 per model x axis: acc | prec | rec | FAR  (FAIL positive; AVB/TC only parent-PASS items)")
for src in ("ltx", "mova"):
    for ax in AXES:
        line = []
        for tag in ORDER:
            t = tabs.get((tag, ax))
            if t is None: continue
            t = t[t.source == src]
            if not len(t): continue
            acc, prec, rec, far, n, nf = prf(t)
            line.append(f"{tag} {fmt(acc)}/{fmt(prec)}/{fmt(rec)}/{fmt(far)}")
        if line:
            n, nf = len(t), int((t["gt"] == "no").sum())
            print(f"{src:5s} {ax:4s} [{n} items, {nf} FAIL]  " + "  ".join(line))
