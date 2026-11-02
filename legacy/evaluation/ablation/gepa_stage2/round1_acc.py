#!/usr/bin/env python3
"""No API calls. GEPA round 1 (10/21, one-pass judge, 3.1): plain acc, seed vs best, per run, from the merged test csvs.
HD-EPIC: item-level acc over all test items of that axis (broken variants + originals + eval_only), item = 'no' if any event 'no'.
220: event-level acc per model (same as eval_rules). Also prints n and n FAIL so the class balance is visible.
  python gepa_stage2/round1_acc.py | tee gepa_stage2/runs/round1_acc.txt"""
import glob, os
import numpy as np
import pandas as pd

def item(df, col):
    g = df.groupby("uid")
    return pd.DataFrame({"gt": g["gt"].apply(lambda s: "no" if (s == "no").any() else "yes"),
                         "pred": g[col].apply(lambda s: "no" if (s == "no").any() else "yes")})

def boot(a, b, n=5000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    idx = np.random.default_rng(0).integers(0, len(a), (n, len(a)))
    d = (b[idx] - a[idx]).mean(1)
    return f"[{np.percentile(d, 2.5):+.2f},{np.percentile(d, 97.5):+.2f}]"

print(f"{'run':12s} {'scope':7s} {'n':>5s} {'FAIL':>5s}  {'seed':>5s} {'best':>5s}  {'diff':>6s} CI")
for mode in ("video", "tools"):
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        fs = glob.glob(f"gepa_stage2/runs/s1{mode}_{ax}/heldout_test_merged_{mode}_{ax}.csv")
        if not fs:
            print(f"{mode} {ax}: merged csv not found"); continue
        df = pd.read_csv(fs[0], dtype=str).fillna("")
        df = df[(df.pred_seed.isin(["yes", "no"])) & (df.pred_best.isin(["yes", "no"]))]
        for scope in ("hdepic", "ltx", "mova"):
            g = df[df.source == scope]
            if not len(g): continue
            if scope == "hdepic":
                s, b = item(g, "pred_seed"), item(g, "pred_best")
                ok_s, ok_b, y = (s["pred"] == s["gt"]), (b["pred"] == b["gt"]), s["gt"]
            else:
                ok_s, ok_b, y = (g["pred_seed"] == g["gt"]), (g["pred_best"] == g["gt"]), g["gt"]
            print(f"{mode + ' ' + ax:12s} {scope:7s} {len(y):5d} {(y == 'no').sum():5d}  {ok_s.mean():5.2f} {ok_b.mean():5.2f}  "
                  f"{ok_b.mean() - ok_s.mean():+6.2f} {boot(ok_s, ok_b)}")
