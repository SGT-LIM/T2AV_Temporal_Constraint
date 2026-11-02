#!/usr/bin/env python3
"""No API calls. 220 test items (ltx + mova), four conditions judged on the SAME day (10/27 video-only and one-call reruns,
10/26-27 two-stage seed and GEPA from the v3 test cache). Old 10/16 columns are printed too, as a drift reference.
Metrics FAIL = positive: acc / prec / rec / FAR, balanced acc. Gated rows (label not yes/no) are dropped per condition.
  python gepa_stage2/compare_220_1027.py"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import glob, re, sys
import numpy as np
import pandas as pd

R = (_LEGACY_ROOT + "/eval_results/multi_agent")
HELD = "gepa_stage2/runs/v3_test/heldout_v3.csv"
OUT = "gepa_stage2/runs/v3_test/compare_220_1027.csv"
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
MODEL = {"ltx": "LTX_2p3", "mova": "MOVA"}
NEW = {"video only (10/27)": f"{R}/baseline_min3_g36_1027", "one call (10/27)": f"{R}/tools_min3_g36_1027"}
OLD = {"one call (10/16)": f"{R}/tools_wf_avocado_min3_g36/rep1"}

def lab(x):
    s = str(x).strip().lower()
    return "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else "")

def find_csv(d, model):
    """one result csv per model: must have item_id and all five axis columns; if several, the one with most rows."""
    fs = sorted(glob.glob(f"{d}/**/{model}*.csv", recursive=True))
    if not fs: sys.exit(f"no csv for {model} under {d}")
    best = None
    for f in fs:
        try: df = pd.read_csv(f, engine="python")
        except Exception: continue
        if "item_id" not in df.columns or not all(c in df.columns for c in COL.values()): continue
        if best is None or len(df) > len(best[1]): best = (f, df)
    if best is None: sys.exit(f"no csv with item_id + axis columns for {model} under {d}: {fs}")
    print(f"  {model:8s} <- {best[0]} ({len(best[1])} rows)")
    df = best[1].drop_duplicates("item_id", keep="last").set_index("item_id")
    nz = {ax: int(df[c].map(lab).isin(['yes', 'no']).sum()) for ax, c in COL.items()}
    print(f"           yes/no labels per axis: {nz}")
    return df

def metrics(y, p):
    y, p = np.asarray(y) == "no", np.asarray(p) == "no"
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    f = lambda a, b: a / b if b else np.nan
    rec, far = f(tp, tp + fn), f(fp, fp + tn)
    return dict(n=int(len(y)), n_fail=int(y.sum()), acc=f(tp + tn, len(y)), prec=f(tp, tp + fp), rec=rec, FAR=far,
                bal=np.nanmean([rec, 1 - far]))

h = pd.read_csv(HELD)
h = h[h.source.isin(MODEL)].copy()
h["item_id"] = h.uid.str.split("|").str[1]
tags = [t for t in h.tag.unique()]
print("tags in heldout:", tags)
seed = h[h.tag == tags[0]][["uid", "source", "item_id", "axis", "y", "stage1"]].rename(columns={"stage1": "video only (10/16)"})
for t in tags:
    p = h[h.tag == t].set_index("uid").pred
    seed[("two-stage seed" if t == tags[0] else f"GEPA {t}")] = seed.uid.map(p)

runs = {}
for tag, d in {**NEW, **OLD}.items():
    for src, m in MODEL.items():
        runs[(tag, src)] = find_csv(d, m)
PARENTS = {"AVB": ("A", "V"), "TCR": ("A", "V", "AVB"), "TCC": ("A", "V")}
for tag in list(NEW) + list(OLD):
    vals = []
    for _, r in seed.iterrows():
        df = runs[(tag, r.source)]
        if r.item_id not in df.index: vals.append("MISSING"); continue
        v = lab(df.loc[r.item_id, COL[r.axis]])
        # one call judges all axes in one answer, so gate dependent axes by its own parent verdicts
        # (the multi-agent runs do this inside the pipeline: child axis is "not evaluated" when a parent fails)
        if "one call" in tag and r.axis in PARENTS and any(lab(df.loc[r.item_id, COL[p]]) == "no" for p in PARENTS[r.axis]):
            v = ""
        vals.append(v)
    seed[tag] = vals
    miss = sum(v == "MISSING" for v in vals)
    if miss: print(f"[warn] {tag}: {miss} rows have no item in the run csv")

conds = [c for c in seed.columns if c not in ("uid", "source", "item_id", "axis", "y")]
order = ["video only (10/27)", "one call (10/27)", "two-stage seed"] + [c for c in conds if c.startswith("GEPA")] + ["video only (10/16)", "one call (10/16)"]
conds = [c for c in order if c in conds]
rows = []
for scope in ["ltx", "mova", "ltx+mova"]:
    g0 = seed if scope == "ltx+mova" else seed[seed.source == scope]
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        g = g0[g0.axis == ax]
        if not len(g): continue
        rec = dict(scope=scope, axis=ax)
        for c in conds:
            k = g[c].isin(["yes", "no"])
            m = metrics(g.y[k], g[c][k])
            rec[c] = f"{m['acc']:.2f}/{m['prec']:.2f}/{m['rec']:.2f}/{m['FAR']:.2f} (n{m['n']},f{m['n_fail']})"
        rows.append(rec)
tab = pd.DataFrame(rows)
print("\ncells: acc/prec/rec/FAR (n rows, n FAIL); FAIL = positive; gated rows dropped per condition")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
print(tab.to_string(index=False))

print("\n== balanced acc per axis, ltx+mova pooled")
bal = []
for ax in ("A", "V", "AVB", "TCR", "TCC"):
    g = seed[seed.axis == ax]; rec = dict(axis=ax)
    for c in conds:
        k = g[c].isin(["yes", "no"]); rec[c] = round(metrics(g.y[k], g[c][k])["bal"], 2) if k.sum() else np.nan
    bal.append(rec)
bal = pd.DataFrame(bal); print(bal.to_string(index=False))
print("mean over axes: " + "  ".join(f"{c} {bal[c].mean():.3f}" for c in conds))
tab.to_csv(OUT, index=False); print(f"\n-> {OUT}")
