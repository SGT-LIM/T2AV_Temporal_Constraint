#!/usr/bin/env python3
# Replaced by t2av_eval/gate/avb_rule_derive.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Data-defined AVB admission rule from the P01/P02 B rows (Synchformer ACTION-WINDOW mode), 10/30. No judge calls.

Row reading: each B row (anchor_1030 verdict present, 95 rows) is represented by the binding-event reading with the largest
|offset| (ties: higher probability); the rule fires on a row if that reading has |offset| >= T and probability >= P
(equivalent to "any event qualifies" for T, and conservative for P).
  T = 95th percentile of |offset| over the ORIGINAL rows, rounded to the tool's offset grid (0.2 s)
  P = 5th percentile of probability over SHIFTED rows (early + late) whose |offset| > T, rounded to 0.01
Rule applied in code to the anchor_1030 verdicts: FAIL if it fires, else keep the anchor verdict.
Writes the rule to PREREGISTERED_RULE.json (before any holdout result exists), the curve to b110/roc_T.csv, and the gate file:
GATE_OK if the rule breaks at most 5% of the B originals (round(0.05 * n_originals): 3 of 51), else GATE_STOP.
The same 5% criterion is pre-registered for the holdout originals.
  python gepa_stage2/gate_b110_v2_1030.py
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
T_DIR = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030")
GRID = 0.2


def rows_with_readings():
    pe = pd.concat(pd.read_csv(f) for f in sorted((T_DIR / "b110").glob("per_event_shard*.csv")))
    assert pe.item_id.nunique() == 110, f"only {pe.item_id.nunique()} items"
    pe.to_csv(T_DIR / "b110" / "per_event.csv", index=False)
    ok = pe[pe.status == "ok"].copy()
    ok["absoff"] = ok.offset.abs()
    best = ok.sort_values(["absoff", "prob"], ascending=False).drop_duplicates("item_id").set_index("item_id")
    sc = pd.read_csv(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028/scores_rows.csv")
    a = sc[(sc["set"] == "B30") & (sc.cond == "anchor") & sc.pred.isin(["yes", "no"])][["uid", "variant", "y", "pred"]].copy()
    a["item_id"] = a.uid.str.split("|").str[1]
    a = a.join(best[["offset", "absoff", "prob"]], on="item_id")
    return pe, a


def apply(a, T, P):
    fire = (a.absoff >= T - 1e-9) & (a.prob >= P - 1e-9)
    new = np.where(fire, "no", a.pred)
    ra, rb = a.pred.values == a.y.values, new == a.y.values
    o = a.variant.values == "original"
    return dict(T=round(T, 2), P=P, fired=int(fire.sum()), fixed=int((~ra & rb).sum()), broken_orig=int((ra & ~rb & o).sum()),
                broken=int((ra & ~rb).sum()), orig_FA=round(float((new[o] == "no").mean()), 3))


def main():
    pe, a = rows_with_readings()
    orig, shf = a[a.variant == "original"], a[a.variant != "original"]
    print(f"rows {len(a)}: originals {len(orig)} (no reading {int(orig.absoff.isna().sum())}), shifted {len(shf)} "
          f"(no reading {int(shf.absoff.isna().sum())}); anchor wrong on shifted: {int((shf.pred != shf.y).sum())}")
    qs = [0.5, 0.9, 0.95, 1.0]
    qt = pd.DataFrame({"quantile": qs, "orig_|offset|": [orig.absoff.quantile(q) for q in qs], "orig_p": [orig.prob.quantile(q) for q in qs]})
    print("\noriginals' |offset| and p quantiles:\n" + qt.round(3).to_string(index=False))
    T_raw = float(orig.absoff.quantile(0.95))
    T = round(round(T_raw / GRID) * GRID, 2)
    sel = shf[shf.absoff > T + 1e-9]
    P_raw = float(sel.prob.quantile(0.05)) if len(sel) else float("nan")
    P = round(P_raw, 2)
    print(f"\nT: 95th pct of original |offset| = {T_raw:.3f} -> {T:.1f} s (0.2 s grid)")
    print(f"P: 5th pct of probability over {len(sel)} shifted rows with |offset| > {T:.1f} = {P_raw:.4f} -> {P:.2f}")
    curve = pd.DataFrame([apply(a, t, P) for t in np.round(np.arange(0.0, 2.01, GRID), 2)])
    curve.to_csv(T_DIR / "b110" / "roc_T.csv", index=False)
    print(f"\nfixed vs broken originals as T varies (P = {P:.2f}):\n" + curve.to_string(index=False))
    op = apply(a, T, P)
    print(f"\noperating point: {op}")
    n_orig = int(len(orig))
    allowed = int(round(0.05 * n_orig))
    rule = dict(rule="AVB -> FAIL if the strongest binding-event Synchformer reading (action-window mode, window_if_alone_multi) has "
                     "|offset| >= T and probability >= P; otherwise keep the media-only anchor verdict",
                T=T, P=P, T_raw=T_raw, P_raw=P_raw, derived_on="P01/P02 v3-test B rows (anchor_1030), action-window Synchformer",
                derivation="T = 95th pct of |offset| on originals (0.2 s grid); P = 5th pct of p among shifted rows with |offset| > T (0.01)",
                b_operating_point=op, b_broken_originals=op["broken_orig"], b_n_originals=n_orig,
                b_gate=f"broken originals <= round(0.05 * n_originals) = {allowed} of {n_orig}",
                holdout_criterion="pass if broken holdout originals <= round(0.05 * n_holdout_originals) "
                                  "(originals with an anchor verdict), with the rule applied in code to the same-day holdout anchor",
                written=time.strftime("%Y-%m-%dT%H:%M:%S"), holdout_results_seen=False)
    json.dump(rule, open(T_DIR / "PREREGISTERED_RULE.json", "w"), indent=1)
    ok = op["broken_orig"] <= allowed
    print(f"B gate: broken originals {op['broken_orig']} vs allowed {allowed} of {n_orig} (5%)")
    (T_DIR / ("GATE_OK" if ok else "GATE_STOP")).write_text(json.dumps(op) + "\n")
    print(f"\nGATE: {'OK' if ok else 'STOP'} -> {T_DIR / ('GATE_OK' if ok else 'GATE_STOP')}")


if __name__ == "__main__":
    main()
