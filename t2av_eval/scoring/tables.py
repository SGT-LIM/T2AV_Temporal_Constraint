"""Tables of the main table, from one wide frame per family: columns group, axis, part, uid, y and one column per condition
(row1, row2, row3, row4, row5, row5_rule, FRb, FRc), values "yes" / "no" / "" (no label: dropped from that condition).

FAIL ("no") is the positive class. Groups are never pooled: every HD-EPIC group (P01P02, P03P09, P01P02-hdfoot, ...) and every
generated set and model (220-LTX, 220-MOVA, 149-LTX) is its own group; a group mixing generation models is refused.
FA = false-alarm rate on PASS rows (y = yes; on HD-EPIC these are the originals).
No-result bound: config/noise_bounds.yaml (same-day flip rate, 10/28 rep2 vs rep3); |delta acc| <= bound is no result.
"""
import numpy as np
import pandas as pd
import yaml

from t2av_eval import paths as _P
from t2av_eval.scoring import lookup as RS

BOUNDS = yaml.safe_load(open(_P.CONFIG / "noise_bounds.yaml"))
CONDS = ["row1", "row2", "row3", "row4", "row5", "row5_rule", "FRb", "FRc"]


def bound(group, axis):
    src = BOUNDS["group_source"].get(group)
    return BOUNDS.get(src, {}).get(axis) if src else None


def _check(W):
    if "model" in W and (W.groupby("group").model.nunique() > 1).any():
        raise ValueError("a group mixes generation models; LTX and MOVA are never pooled")


def _m(y, p):
    m = RS.metrics(y, p)
    yes = np.asarray(y) == "yes"
    m["FA"] = float((np.asarray(p)[yes] == "no").mean()) if yes.any() else np.nan
    return m


def metrics_table(W, conds=None):
    _check(W)
    conds = [c for c in (conds or CONDS) if c in W]
    out = []
    for (g, ax), t in W.groupby(["group", "axis"], sort=True):
        for c in conds:
            h = t[t[c].isin(["yes", "no"])]
            if not len(h):
                continue
            m = _m(h.y, h[c])
            o, v = h[h.part == "original"], h[h.part == "variant"]
            out.append(dict(group=g, axis=ax, cond=c, n=m["n"], n_fail=m["n_fail"], acc=m["acc"], prec=m["prec"], rec=m["rec"], FA=m["FA"],
                            acc_orig=(o[c] == o.y).mean() if len(o) else np.nan, acc_var=(v[c] == v.y).mean() if len(v) else np.nan))
    return pd.DataFrame(out)


def compare_table(W, base="row1", conds=None):
    """per group / axis / condition vs base, on rows labelled in both: delta acc, bound, verdict, fixed / broken"""
    _check(W)
    conds = [c for c in (conds or CONDS) if c in W and c != base]
    out = []
    for (g, ax), t in W.groupby(["group", "axis"], sort=True):
        for c in conds:
            h = t[t[base].isin(["yes", "no"]) & t[c].isin(["yes", "no"])]
            if not len(h):
                continue
            rb, rc = h[base] == h.y, h[c] == h.y
            d = float(rc.mean() - rb.mean())
            b = bound(g, ax)
            out.append(dict(group=g, axis=ax, cond=c, base=base, n=len(h), acc_base=float(rb.mean()), acc=float(rc.mean()), delta=d,
                            bound=b, verdict="no bound" if b is None else ("no result" if abs(d) <= b + 1e-9 else "beyond bound"),
                            fixed=int((~rb & rc).sum()), broken=int((rb & ~rc).sum()),
                            broken_pass=int((rb & ~rc & (h.y == "yes")).sum()), n_pass=int((h.y == "yes").sum())))
    return pd.DataFrame(out)


def operating_points(W, conds=None, axis="AVB"):
    """recall on FAIL rows (shifted) vs false-alarm rate on PASS rows (originals), per group"""
    _check(W)
    conds = [c for c in (conds or CONDS) if c in W]
    out = []
    for g, t in W[W.axis == axis].groupby("group", sort=True):
        for c in conds:
            h = t[t[c].isin(["yes", "no"])]
            if not len(h):
                continue
            f, p = h[h.y == "no"], h[h.y == "yes"]
            out.append(dict(group=g, cond=c, recall_fail=(f[c] == "no").mean() if len(f) else np.nan, n_fail=len(f),
                            FA_pass=(p[c] == "no").mean() if len(p) else np.nan, n_fa=int((p[c] == "no").sum()), n_pass=len(p),
                            acc=(h[c] == h.y).mean()))
    return pd.DataFrame(out)


def wide_from_long(D, cond_col="row", pred_col="pred"):
    """hd_rows_scored / gen_rows_scored (one row per run and GT row) -> wide"""
    keys = [k for k in ("group", "axis", "part", "uid", "y", "model") if k in D]
    return D.pivot_table(index=keys, columns=cond_col, values=pred_col, aggfunc="first").reset_index().rename_axis(None, axis=1).fillna("")
