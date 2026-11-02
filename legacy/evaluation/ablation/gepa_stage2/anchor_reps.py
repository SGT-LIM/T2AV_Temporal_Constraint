#!/usr/bin/env python3
"""No API calls. Media-only rep1/rep2/rep3 on the v3 test rows, all scored with one rule (rep_scoring.row_label).
  1. acc/prec/rec per source x axis per run (FAIL = positive)
  2. 3-way agreement: rows judged in all three reps, unanimous vs disagree; P(rep1 wrong | disagree), P(rep1 wrong | unanimous),
     share of rep1 errors that are in the disagree group. Pairwise flip rates rep1-rep2, rep2-rep3 (same day), rep1-rep3.
  3. 220 drift: same rule for 10/16, 10/27, 10/28 x2 media-only and 10/16, 10/27 one call.
Input runs/v3_test/anchor_reps_1028_rows.csv (from rep_scoring.py). Outputs runs/v3_test/anchor_reps_1028_{metrics,agree,drift220}.csv.
  python gepa_stage2/anchor_reps.py
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rep_scoring import metrics, OUT as ROWS

D = ROWS.parent
REPS = ["rep1", "rep2", "rep3"]
ORDER = ["hdepic", "hdfoot", "hdmove", "ltx", "mova"]


def fmt(m):
    return f"{m['acc']:.2f}/{m['prec']:.2f}/{m['rec']:.2f}" if m["n"] else "-"


def group_keys(r):
    """HD-EPIC: also split original vs variant rows (CLAUDE.md)."""
    yield (r.source, r.axis, "all")
    if r.source.startswith("hd"):
        yield (r.source, r.axis, "original" if r.variant == "original" else "variant")


def main():
    rows = pd.read_csv(ROWS, keep_default_na=False)
    rows["grp"] = [list(group_keys(r)) for r in rows.itertuples()]
    ex = rows.explode("grp")
    ex[["source", "axis", "part"]] = pd.DataFrame(ex.grp.tolist(), index=ex.index)
    ex["source"] = pd.Categorical(ex.source, ORDER, ordered=True)

    met, agr = [], []
    for (src, ax, part), g in ex.groupby(["source", "axis", "part"], observed=True):
        rec = dict(source=src, axis=ax, part=part)
        for c in REPS + (["d1027", "oc1016", "oc1027"] if src in ("ltx", "mova") else []):
            k = g[c].isin(["yes", "no"])
            m = metrics(g.y[k], g[c][k])
            rec[c] = fmt(m); rec[f"n_{c}"] = f"{m['n']}({m['n_fail']})"
        met.append(rec)
        # 3-way agreement on rows judged by all three reps
        k = g[REPS].isin(["yes", "no"]).all(axis=1)
        h = g[k]
        if not len(h):
            continue
        dis = h[REPS].nunique(axis=1) > 1
        wrong1 = h.rep1 != h.y
        fail = h.y == "no"
        pair = lambda a, b: (h[a] != h[b]).mean()
        agr.append(dict(source=src, axis=ax, part=part, n=len(h), n_fail=int(fail.sum()),
                        disagree=int(dis.sum()), disagree_rate=dis.mean(),
                        P_wrong_dis=wrong1[dis].mean() if dis.any() else np.nan,
                        P_wrong_una=wrong1[~dis].mean() if (~dis).any() else np.nan,
                        rep1_errors=int(wrong1.sum()), err_in_dis=int((wrong1 & dis).sum()),
                        share_err_in_dis=(wrong1 & dis).sum() / wrong1.sum() if wrong1.any() else np.nan,
                        una_wrong_FAIL=int((wrong1 & ~dis & fail).sum()), una_wrong_PASS=int((wrong1 & ~dis & ~fail).sum()),
                        flip_12=pair("rep1", "rep2"), flip_23=pair("rep2", "rep3"), flip_13=pair("rep1", "rep3"),
                        maj_acc=(h[REPS].eq("no").sum(axis=1).ge(2).map({True: "no", False: "yes"}) == h.y).mean(),
                        acc1=(~wrong1).mean()))
    met, agr = pd.DataFrame(met), pd.DataFrame(agr)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
    print("== acc/prec/rec (FAIL = positive), n(FAIL) per run; same rule for every run")
    print(met.to_string(index=False))
    print("\n== 3-way agreement (rows judged in rep1, rep2 and rep3)")
    print(agr.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    # 220 drift: per model, mean balanced acc over axes with >= 1 FAIL and >= 1 PASS (internal diagnostic only)
    runs = ["rep1", "d1027", "rep2", "rep3", "oc1016", "oc1027"]
    dr = []
    for src in ("ltx", "mova"):
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            g = rows[(rows.source == src) & (rows.axis == ax)]
            rec = dict(source=src, axis=ax)
            for c in runs:
                k = g[c].isin(["yes", "no"]); m = metrics(g.y[k], g[c][k])
                rec[c] = fmt(m) + f" n{m['n']}f{m['n_fail']}"
                rec[f"bal_{c}"] = np.nanmean([m["rec"], 1 - m["FAR"]]) if m["n_fail"] and m["n"] > m["n_fail"] else np.nan
            dr.append(rec)
    dr = pd.DataFrame(dr)
    print("\n== 220 drift, same rule (acc/prec/rec nN fFAIL); runs: rep1 = 10/16, d1027 = 10/27, rep2/rep3 = 10/28 media-only; oc = one call")
    print(dr[["source", "axis"] + runs].to_string(index=False))
    print("\nmean balanced acc over axes (per model; internal diagnostic):")
    for src in ("ltx", "mova"):
        g = dr[dr.source == src]
        print(f"  {src}: " + "  ".join(f"{c} {g[f'bal_{c}'].mean():.3f} ({g[f'bal_{c}'].notna().sum()} ax)" for c in runs))
    g = dr  # the 10/27 doc figure pooled ltx+mova axes; reproduce that pooling for the supersede note only
    print("  pooled-axis mean as in gepa_results_all §7 (avg of per-model axis values): " +
          "  ".join(f"{c} {g[f'bal_{c}'].mean():.3f}" for c in runs))

    for name, t in (("metrics", met), ("agree", agr), ("drift220", dr)):
        p = D / f"anchor_reps_1028_{name}.csv"
        if p.exists():
            sys.exit(f"exists, not overwriting: {p}")
        t.to_csv(p, index=False); print(f"-> {p}")


if __name__ == "__main__":
    main()
