#!/usr/bin/env python3
"""No API calls. GEPA round 2 (10/22-24, two-stage KEEP/REVISE, judge 3.1), test set.
For every stage-2 rule (per-axis seed / best, orchestrator seed / best):
  acc (HD-EPIC item-level, 220 event-level per model), and labels changed vs stage 1: right / wrong after change.
Reads the merged held-out csv(s) under gepa_stage2/runs/s0_s1test (falls back to any heldout_test_merged*.csv under runs/s0*).
  python gepa_stage2/round2_changes.py | tee gepa_stage2/runs/round2_changes.txt"""
import glob, sys
import pandas as pd

fs = sorted(glob.glob("gepa_stage2/runs/s0_s1test/heldout_test_merged*.csv")) or \
     sorted(glob.glob("gepa_stage2/runs/s0*/heldout_test_merged*.csv"))
if not fs:
    sys.exit("no heldout_test_merged*.csv found; run: ls gepa_stage2/runs/s0_s1test gepa_stage2/runs/ | head -50")
f = max(fs, key=lambda p: len(pd.read_csv(p, nrows=0).columns))
df = pd.read_csv(f, dtype=str).fillna("")
cols = [c for c in df.columns if c.startswith("pred_") and c not in ("pred_video_only", "pred_oneshot", "pred_seed_run")]
print(f"file: {f}\nall csvs: {fs}\nrule columns: {cols}\nrows: {len(df)}  sources: {df.source.value_counts().to_dict()}\n")

def item(g, col):
    t = g.groupby("uid")
    return pd.DataFrame({"gt": t["gt"].apply(lambda s: "no" if (s == "no").any() else "yes"),
                         "s1": t["stage1"].apply(lambda s: "no" if (s == "no").any() else ("yes" if (s == "yes").any() else "")),
                         "p": t[col].apply(lambda s: "no" if (s == "no").any() else ("yes" if (s == "yes").any() else ""))})

rows = []
for ax, ga in df.groupby("axis"):
    for src in ("hdepic", "ltx", "mova"):
        g = ga[ga.source == src]
        if not len(g): continue
        for c in ["stage1"] + cols:
            if src == "hdepic":
                t = item(g, c if c != "stage1" else "stage1")
                gt, s1, p = t["gt"], t["s1"], t["p"]
            else:
                gt, s1, p = g["gt"], g["stage1"], g[c]
            ok = p.isin(["yes", "no"]) & s1.isin(["yes", "no"])
            gt, s1, p = gt[ok], s1[ok], p[ok]
            ch = p != s1
            rows.append(dict(axis=ax, source=src, rule=c.replace("pred_", ""), n=len(p), n_fail=int((gt == "no").sum()),
                             acc=round((p == gt).mean(), 3), changed=int(ch.sum()),
                             right=int((ch & (p == gt)).sum()), wrong=int((ch & (p != gt)).sum())))
out = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(out.to_string(index=False))
out.to_csv("gepa_stage2/runs/round2_changes.csv", index=False)
print("\n-> gepa_stage2/runs/round2_changes.csv")
