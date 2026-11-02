#!/usr/bin/env python3
"""HD-EPIC main table: score the full-video rows (row 1 media-only, row 2 one call + Synchformer) on all five axes, 11/01. No calls.
GT rows: A / V / AVB from hd_stage2_1101.gt_rows (P01/P02 v3 test, P03-P09 v3 rules); TCR: P01/P02 v3-test hdepic TCR rows, P03-P09
order_swap + originals with neighbouring events >= 1.0 s (item level); TCC: P01/P02 v3-test hdmove rows, P03-P09 count_off +
originals (item level). stage1_lookup rule (rep_scoring.row_label).
  python gepa_stage2/hd_rows_score_1101.py   -> runs/obsval_1028/hd_rows_table_1101.csv
"""
from t2av_eval import paths as _P
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
pass  # (legacy sys.path insert removed); pass  # (legacy sys.path insert removed)
from t2av_eval.scoring import lookup as RS
from t2av_eval.judge.stage2 import hdepic as H
from t2av_eval.gate import reliability as SC

R = Path((str(_P.DATA) + "/real_av/eval/results"))
RUNS = {"row1": "hdepic_main_row1_anchor_g36_1101", "row2": "hdepic_main_row2_onecall_sync_g36_1101"}
NSH = {"hdepic_p12": 3, "hdfoot_p12": 1, "hdmove_p12": 2, "p3p9": 24}
SRC2SET = {"hm_hdepic": "hdepic_p12", "hm_hdfoot": "hdfoot_p12", "hm_hdmove": "hdmove_p12", "hm_p3p9": "p3p9"}


# 11/01 (user): count_off items whose counted event is a stir / mix / whisk action are dropped from TCC scoring (a continuous stirring
# action has no agreed count). Found by rebuild_plan_1101.py; no movement-set item has a stir event.
TCC_STIR_DROP = {"hdepic_P02-20240210-122334_0018259_TCC", "hdepic_P04-20240414-165333_0009393_TCC",
                 "hdepic_P04-20240415-181212_0087085_TCC", "hdepic_P05-20240425-173353_0039436_TCC"}


def gt_all():
    rows = [dict(r, set=SRC2SET.get(r["source"], r["source"])) for r in H.gt_rows()]
    man = [json.loads(l) for l in open(_P.INPUTS / "evaluation/ablation/gepa_stage2/manifests_v3/test.jsonl")]
    rows += [dict(source="hm_hdepic", set="hdepic_p12", item_id=m["item_id"], axis="TCR", gt=m["gt"], variant=m["variant"])
             for m in man if m["source"] == "hdepic" and m["axis"] == "TCR"]
    rows += [dict(source="hm_hdmove", set="hdmove_p12", item_id=m["item_id"], axis="TCC", gt=m["gt"], variant=m["variant"])
             for m in man if m["source"] == "hdmove" and m["axis"] == "TCC"]
    for r in SC.rows("p3p9"):
        if r["axis"] in ("TCR", "TCC") and not (r["axis"] == "TCC" and r["item_id"] in TCC_STIR_DROP):
            v = "original" if r["item_id"].endswith("_pass") else "variant"
            rows.append(dict(source="hm_p3p9", set="p3p9", item_id=r["item_id"], axis=r["axis"], gt={"__item__": r["y"]}, variant=v))
    return rows


def main():
    G = gt_all()
    out = []
    for row, d in RUNS.items():
        dfs = {s: RS.load([str(R / d / f"{s}_shard{k}.csv") for k in range(n) if (R / d / f"{s}_shard{k}.csv").exists()])
               for s, n in NSH.items() if any((R / d / f"{s}_shard{k}.csv").exists() for k in range(n))}
        for g in G:
            if g["set"] not in dfs:
                continue
            out.append(dict(row=row, group=H.GROUP.get(g["source"], "P01P02"), axis=g["axis"],
                            part="original" if g["variant"] == "original" else "variant",
                            uid=f"{g['set']}|{g['item_id']}|{g['axis']}", y="no" if "no" in g["gt"].values() else "yes",
                            pred=RS.row_label(dfs[g["set"]], g["item_id"], g["axis"], g["gt"])))
    D = pd.DataFrame(out)
    D.to_csv(_P.WORK / "obsval_1028/hd_rows_scored_1101.csv", index=False)
    tab = []
    for (grp, ax, row), g in D.groupby(["group", "axis", "row"]):
        h = g[g.pred.isin(["yes", "no"])]
        m = RS.metrics(h.y, h.pred)
        o = h[h.part == "original"]; v = h[h.part == "variant"]
        tab.append(dict(group=grp, axis=ax, row=row, n=m["n"], n_fail=m["n_fail"], acc=round(m["acc"], 3), prec=round(m["prec"], 3),
                        rec=round(m["rec"], 3), FA_orig=round(float((o.pred == "no").mean()), 3) if len(o) else None,
                        acc_orig=round(float((o.pred == o.y).mean()), 3) if len(o) else None,
                        acc_var=round(float((v.pred == v.y).mean()), 3) if len(v) else None))
    T = pd.DataFrame(tab)
    T.to_csv(_P.WORK / "obsval_1028/hd_rows_table_1101.csv", index=False)
    pd.set_option("display.width", 200)
    print(T.to_string(index=False))


if __name__ == "__main__":
    main()
