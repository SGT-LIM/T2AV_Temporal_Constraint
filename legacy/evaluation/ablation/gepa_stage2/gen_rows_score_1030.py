#!/usr/bin/env python3
"""Score the full-video rows of the generated block (rows 1, 2, 2b, 3), 10/30. No calls.
stage1_lookup rule (rep_scoring.row_label), per set / model / axis; 220 GT = manifests_v3 ltx / mova, 149 GT = gt_gen149 (majority).
TCR on the 149 is printed with its Fleiss kappa (.03) and is not interpreted.
  python gepa_stage2/gen_rows_score_1030.py   -> runs/obsval_1028/gen_rows_table_1030.csv
"""
import json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rep_scoring as RS

R = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent")
G149 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030")
RUNS = {"row1": "gen_row1_anchor_g36_1030", "row2": "gen_row2_onecall_sync_g36_1030", "row2b": "gen_row2b_onecall_neutral_g36_1030",
        "row3": "gen_row3_routing_g36_1030"}
PREFIX = {("220", "LTX_2p3"): "LTX_2p3", ("220", "MOVA"): "MOVA", ("149", "LTX_2p3"): "gen149"}


def gt():
    out = []
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s}.jsonl")]
    out += [dict(set="220", model={"ltx": "LTX_2p3", "mova": "MOVA"}[m["source"]], item_id=m["item_id"], axis=m["axis"], gt=m["gt"])
            for m in man if m["source"] in ("ltx", "mova")]
    out += [dict(set="149", model="LTX_2p3", item_id=m["item_id"], axis=m["axis"], gt=m["gt"])
            for m in map(json.loads, open(G149 / "gt_gen149.jsonl"))]
    return out


def main():
    G = gt()
    kappa = json.load(open(G149 / "kappa.json"))
    rows = []
    for row, d in RUNS.items():
        for (s, m), pre in PREFIX.items():
            fs = sorted((R / d).glob(f"{pre}_shard*.csv"))
            fs = [f for f in fs if not f.name.endswith("_per_event.csv")]
            if not fs:
                continue
            df = RS.load([str(f) for f in fs])
            for g in G:
                if g["set"] == s and g["model"] == m:
                    rows.append(dict(row=row, set=s, model=m, axis=g["axis"], uid=f"{s}|{m}|{g['item_id']}|{g['axis']}",
                                     y="no" if "no" in g["gt"].values() else "yes", pred=RS.row_label(df, g["item_id"], g["axis"], g["gt"])))
    D = pd.DataFrame(rows)
    D.to_csv(HERE / "runs/obsval_1028/gen_rows_scored_1030.csv", index=False)
    tab = []
    for (s, m, ax, row), g in D.groupby(["set", "model", "axis", "row"]):
        h = g[g.pred.isin(["yes", "no"])]
        mt = RS.metrics(h.y, h.pred) if len(h) else dict(n=0, n_fail=0, acc=None, prec=None, rec=None)
        tab.append(dict(set=s, model=m, axis=ax, row=row, n_gt=len(g), n=mt["n"], n_fail=mt["n_fail"], acc=mt["acc"], prec=mt["prec"],
                        rec=mt["rec"], kappa=kappa.get(ax, {}).get("kappa") if s == "149" else None))
    T = pd.DataFrame(tab)
    T.to_csv(HERE / "runs/obsval_1028/gen_rows_table_1030.csv", index=False)
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
