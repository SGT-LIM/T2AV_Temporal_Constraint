#!/usr/bin/env python3
"""Generated-set threshold recalibration check (11/01). No judge calls. Writes docs/gen_recalibration_1101.md.

Calibration (per seed, 20 seeds): a random 20% of the GT rows of the 220 and 149 (stratified by batch: 220-LTX, 220-MOVA, 149),
pooled over batches because 20% of one model gives about 11 PASS rows per axis. Same derivations as the real-video thresholds:
  T_sync = 95th percentile of |offset| (strongest binding-event Synchformer reading, anchor-time window, 10/30) over human-PASS
           AVB rows, on the 0.2 s grid;  P_sync = 5th percentile of p over human-FAIL AVB rows with |offset| > T (none -> the rule
           cannot fire);  T_flam = 5th percentile of the first-query FLAM max score over the sounding GT events of human-PASS A rows.
Evaluation on the other 80%, per batch, from existing calls only (gen_stage2_rows_1030.csv: row 1 = 10/30 media-only anchor,
row 4 = the G4 call with the tool text):
  AVB code rule   FAIL if the rule fires, else row 1;   AVB gated judge   row 4 if the rule fires, else row 1
  A gate          row 4 if any GT sounding event has FLAM max < T_flam, else row 1. Approximation: the real row 5 shows only the
                  admitted FLAM lines (a new call when that text differs); here the row 4 call (all lines) stands in.
Both threshold sets: recalibrated (per seed) and real-video (1.8 s / .25 / .2705). Reported: median and range over seeds.
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import gen_stage2_1030 as G
import rep_scoring as RS

SYNC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_gen_1030")
DOC = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/docs/gen_recalibration_1101.md")
REAL = dict(T=1.8, P=0.25, F=0.2705)
SEEDS = range(20)


def main():
    D = pd.read_csv(HERE / "runs/obsval_1028/gen_stage2_rows_1030.csv").fillna("")
    D = D[D.axis.isin(["A", "AVB"])].copy()
    D["batch"] = D["set"].astype(str) + "-" + D["model"]
    D["item_id"] = D.uid.str.split("|").str[1]
    pe = pd.concat(pd.read_csv(f) for s in ("220", "149") for f in sorted((SYNC / s).glob("per_event_shard*.csv")))
    pe["batch"] = pe["set"].astype(str) + "-" + pe["model"]
    ok = pe[pe.status == "ok"].assign(a=lambda t: t.offset.abs())
    best = ok.sort_values(["a", "prob"], ascending=False).drop_duplicates(["batch", "item_id"]).set_index(["batch", "item_id"])
    D["absoff"] = [best.a.get((b, i), np.nan) for b, i in zip(D.batch, D.item_id)]
    D["prob"] = [best.prob.get((b, i), np.nan) for b, i in zip(D.batch, D.item_id)]
    rows = {r["uid"]: r for r in G.gt_rows()}
    fmin = []
    for u, ax in zip(D.uid, D.axis):
        if ax != "A":
            fmin.append(np.nan); continue
        r = rows[u]
        _, fl, _ = G.a_parts(r["source"], r["item_id"])
        s = [v[1] for e, v in fl.items() if e in r["gt"]]
        fmin.append(min(s) if s else np.nan)
    D["flam_min"] = fmin
    res, ths = [], []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        cal = np.zeros(len(D), bool)
        for b, idx in D.groupby("batch").groups.items():
            idx = np.array(list(idx)); pos = D.index.get_indexer(idx)
            cal[rng.choice(pos, size=int(round(0.2 * len(pos))), replace=False)] = True
        C, E = D[cal], D[~cal]
        av = C[C.axis == "AVB"].dropna(subset=["absoff"])
        T = round(round(float(np.quantile(av[av.y == "yes"].absoff, 0.95)) / 0.2) * 0.2, 2)
        sel = av[(av.y == "no") & (av.absoff > T + 1e-9)]
        P = round(float(np.quantile(sel.prob, 0.05)), 2) if len(sel) else np.nan
        a = C[(C.axis == "A") & (C.y == "yes")].flam_min.dropna()
        F = round(float(np.quantile(a, 0.05)), 4) if len(a) else np.nan
        ths.append(dict(seed=seed, T=T, P=P, F=F, n_pass_avb=int((av.y == "yes").sum()), n_fail_above_T=len(sel), n_pass_a=len(a)))
        for name, th in (("recalibrated", dict(T=T, P=P, F=F)), ("real-video", REAL)):
            for (b, ax), g in E.groupby(["batch", "axis"]):
                g = g[g.row1.isin(["yes", "no"])]
                if ax == "AVB":
                    fire = (g.absoff >= th["T"] - 1e-9) & (g.prob >= th["P"] - 1e-9) if not np.isnan(th["P"]) else pd.Series(False, index=g.index)
                    conds = {"code rule": np.where(fire, "no", g.row1), "gated judge": np.where(fire, g.row4.where(g.row4 != "", g.row1), g.row1)}
                else:
                    fire = g.flam_min < th["F"]
                    conds = {"A gate": np.where(fire, g.row4.where(g.row4 != "", g.row1), g.row1)}
                for cn, pred in conds.items():
                    m = RS.metrics(g.y, pred)
                    res.append(dict(seed=seed, thresholds=name, batch=b, axis=ax, cond=cn, n=m["n"], n_fail=m["n_fail"], open=int(fire.sum()),
                                    acc=m["acc"], prec=m["prec"], rec=m["rec"]))
                m = RS.metrics(g.y, g.row1)
                res.append(dict(seed=seed, thresholds="-", batch=b, axis=ax, cond="row 1", n=m["n"], n_fail=m["n_fail"], open=0, acc=m["acc"], prec=m["prec"], rec=m["rec"]))
    TH, R = pd.DataFrame(ths), pd.DataFrame(res)
    TH.to_csv(HERE / "runs/obsval_1028/gen_recalib_thresholds_1101.csv", index=False)
    R.to_csv(HERE / "runs/obsval_1028/gen_recalib_results_1101.csv", index=False)
    q = lambda s: f"{np.nanmedian(s):.2f} [{np.nanmin(s):.2f}, {np.nanmax(s):.2f}]" if s.notna().any() else "–"
    L = ["# Generated-set threshold recalibration check (2026-11-01, no judge calls)", "",
         "Script `evaluation/ablation/gepa_stage2/gen_recalib_1101.py`; per-seed tables in `runs/obsval_1028/gen_recalib_*_1101.csv`.", "",
         "Design:",
         "- Calibration: 20 random 20% splits of the 220 + 149 GT rows, stratified by batch and pooled over batches.",
         "- Derivations as for the real-video thresholds: T = 95th percentile of PASS |offset| on the 0.2 s grid; P = 5th percentile of p among FAIL rows above T; T_flam = 5th percentile of PASS first-query FLAM max.",
         "- Evaluation: the other 80%, per batch, assembled from the existing 10/30 row 1 and row 4 (G4) calls.",
         "- The A gate uses the row 4 call (all FLAM lines) where the gate opens. This is an approximation of row 5, which shows only the admitted lines.", "",
         "## Thresholds (median [min, max] over 20 seeds)", "",
         "| threshold | recalibrated on generated PASS rows | real-video (P01/P02) |", "|---|---|---|",
         f"| Synchformer T (s) | {q(TH['T'])} | 1.8 |", f"| Synchformer P | {q(TH['P'])} (undefined in {int(TH['P'].isna().sum())} of 20 seeds: no FAIL row above T) | .25 |",
         f"| FLAM audibility T_flam | {q(TH['F'])} | .2705 |", "",
         f"Calibration rows per seed: AVB PASS {int(TH.n_pass_avb.median())}, FAIL rows above T median {int(TH.n_fail_above_T.median())}; A PASS {int(TH.n_pass_a.median())}.", "",
         "## Gated results on the 80% (median over seeds; acc / precision / recall, gate open count)", "",
         "| batch | axis | condition | row 1 | recalibrated | real-video |", "|---|---|---|---|---|---|"]
    for (b, ax, cn), g in R[R.cond != "row 1"].groupby(["batch", "axis", "cond"]):
        r1 = R[(R.cond == "row 1") & (R.batch == b) & (R.axis == ax)]
        f = lambda x: f"{x.acc.median():.2f} / {x.prec.median():.2f} / {x.rec.median():.2f}"
        rc, rv = g[g.thresholds == "recalibrated"], g[g.thresholds == "real-video"]
        L.append(f"| {b} | {ax} | {cn} | {f(r1)} (n {int(r1.n.median())}, FAIL {int(r1.n_fail.median())}) | {f(rc)}, open {int(rc.open.median())} | {f(rv)}, open {int(rv.open.median())} |")
    DOC.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
