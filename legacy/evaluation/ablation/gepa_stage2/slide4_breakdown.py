#!/usr/bin/env python3
"""No API calls. HD-EPIC test (hdepic + hdfoot + hdmove), 4 conditions, plain acc (FAIL = positive), two levels:
  (1) per axis (A = hdepic A + footstep pooled), (2) per axis x item type (variant).
video only = stage-1 label in heldout_v3.csv; two-stage = tag 'seed'; GEPA = tags b0 b1 b2 (mean and range);
one call = multi-agent run with tools in the same call (gated rows have no label and are dropped, n printed).
  python gepa_stage2/slide4_breakdown.py | tee gepa_stage2/runs/v3_test/slide4_breakdown.txt"""
import glob, sys
import numpy as np
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
HELD = "gepa_stage2/runs/v3_test/heldout_v3.csv"
ONE = {"hdepic": f"{E}/results/hdepic_medium_multi_tools_wf_hop5_g36", "hdfoot": f"{E}/results/hdepic_footstep48_tools_wf_hop5_g36"}
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
lab = lambda x: (lambda s: "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else ""))(str(x).strip().lower())

def load_run(d):
    fs = sorted(glob.glob(f"{d}/shard?.csv")) or sorted(glob.glob(f"{d}/all.csv")) or sorted(glob.glob(f"{d}/*.csv"))
    if not fs: sys.exit(f"no csv in {d}")
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")

h = pd.read_csv(HELD, dtype=str).fillna("")
h = h[h.source.isin(["hdepic", "hdfoot", "hdmove"])].copy()
h["item_id"] = h.uid.str.split("|").str[1]
tags = list(dict.fromkeys(h.tag))
base = h[h.tag == tags[0]][["uid", "source", "item_id", "axis", "variant", "y", "stage1"]].rename(columns={"stage1": "video"})
for t in tags:
    p = h[h.tag == t].set_index("uid").pred
    base["two" if t == tags[0] else t] = base.uid.map(p)
runs = {s: load_run(d) for s, d in ONE.items()}
PARENTS = {"AVB": ("A", "V"), "TCR": ("A", "V", "AVB"), "TCC": ("A", "V")}
def one_label(s, i, a):
    if s not in runs or i not in runs[s].index: return ""
    r = runs[s].loc[i]
    if a in PARENTS and any(lab(r[COL[p]]) == "no" for p in PARENTS[a]): return ""   # gated in the one-call run
    return lab(r[COL[a]])
base["one"] = [one_label(s, i, a) for s, i, a in zip(base.source, base.item_id, base.axis)]
gtags = [t for t in tags[1:]]
print("tags:", tags, "| rows:", len(base), "| one-call labels found:", int(base.one.isin(["yes", "no"]).sum()))

def acc(g, c):
    k = g[c].isin(["yes", "no"])
    return (g[c][k] == g.y[k]).mean() if k.sum() else np.nan, int(k.sum())

def line(name, g):
    out = [f"{name:28s} n {len(g):4d} FAIL {int((g.y == 'no').sum()):4d}"]
    for c in ["video", "one", "two"]:
        a, n = acc(g, c); out.append(f"{c} {a:.2f}" + (f" ({n})" if n != len(g) else ""))
    gs = [acc(g, t)[0] for t in gtags]
    out.append(f"GEPA {np.nanmean(gs):.2f} [{np.nanmin(gs):.2f}-{np.nanmax(gs):.2f}]")
    return "  ".join(out)

print("\n== (1) per axis")
for ax in ("A", "V", "AVB", "TCR", "TCC"):
    print(line(ax, base[base.axis == ax]))
print("\n== (2) per axis x source x item type")
for (ax, src, var), g in base.groupby(["axis", "source", "variant"], sort=False):
    print(line(f"{ax} {src} {var}", g))
