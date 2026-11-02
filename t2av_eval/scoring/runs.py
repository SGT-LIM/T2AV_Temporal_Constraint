"""Score CLI runs into the wide frame of scoring.tables, with the stage1_lookup rule (scoring.lookup.row_label) and the GT rows
of the moved scorers (hdepic_rows.gt_all: HD-EPIC A / V / AVB / TCR / TCC; generated_rows.gt: 220 manifests_v3, 149 majority).

media runs: {"row1": run dir, "row2": ...}; each dir holds <set>_shard<k>.csv (t2av_eval.run.launch).
stage-2 run: the dir of t2av_eval.run.stage2 (hd_stage2_rows_1101.csv or gen_stage2_rows_1030.csv).
"""
from pathlib import Path

import pandas as pd

from t2av_eval.judge import conditions as C
from t2av_eval.scoring import lookup as RS

GEN = {"ltx220": ("220", "LTX_2p3", "220-LTX"), "mova220": ("220", "MOVA", "220-MOVA"), "gen149": ("149", "LTX_2p3", "149-LTX")}
GEN_GROUP = {("220", "LTX_2p3"): "220-LTX", ("220", "MOVA"): "220-MOVA", ("149", "LTX_2p3"): "149-LTX"}


def _load(run, set_name):
    fs = [str(f) for f in sorted(Path(run).glob(f"{set_name}_shard*.csv")) if not f.name.endswith("_per_event.csv")]
    return RS.load(fs) if fs else None


def score_media(runs, set_names):
    fams = {C.set_info(s)["family"] for s in set_names}
    if len(fams) != 1:
        raise ValueError(f"one family per table, got {sorted(fams)}")
    out = []
    if fams == {"hdepic"}:
        from t2av_eval.scoring import hdepic_rows as HR
        G = [g for g in HR.gt_all() if g["set"] in set_names]
        for row, d in runs.items():
            dfs = {s: _load(d, s) for s in set_names}
            for g in G:
                df = dfs.get(g["set"])
                if df is None:
                    continue
                out.append(dict(row=row, group=HR.H.GROUP.get(g["source"], "P01P02"), axis=g["axis"],
                                part="original" if g["variant"] == "original" else "variant", uid=f"{g['set']}|{g['item_id']}|{g['axis']}",
                                y="no" if "no" in g["gt"].values() else "yes", pred=RS.row_label(df, g["item_id"], g["axis"], g["gt"])))
    else:
        from t2av_eval.scoring import generated_rows as GR
        G = GR.gt()
        for row, d in runs.items():
            for s in set_names:
                gs, gm, grp = GEN[s]
                df = _load(d, s)
                if df is None:
                    continue
                for g in G:
                    if (g["set"], g["model"]) == (gs, gm):
                        out.append(dict(row=row, group=grp, model=gm, axis=g["axis"], part="-", uid=f"{gs}|{gm}|{g['item_id']}|{g['axis']}",
                                        y="no" if "no" in g["gt"].values() else "yes", pred=RS.row_label(df, g["item_id"], g["axis"], g["gt"])))
    return pd.DataFrame(out)


MA_GROUP = {"": "P01P02-ma", "_hm_ma39": "P03P09-ma"}


def stage2_wide(stage2_dir):
    d = Path(stage2_dir)
    ma = sorted(d.glob("hd_ma_rows*_1101.csv"))
    if ma:                                                    # mute_anchor A sets (variant: mute_anchor / sham / original)
        parts = []
        for f in ma:
            W = pd.read_csv(f, dtype=str).fillna("")
            W["group"] = MA_GROUP[f.name[len("hd_ma_rows"):-len("_1101.csv")]]
            W["axis"], W["part"] = "A", W.variant
            parts.append(W)
        return pd.concat(parts, ignore_index=True)
    if (d / "hd_stage2_rows_1101.csv").exists():
        W = pd.read_csv(d / "hd_stage2_rows_1101.csv", dtype=str).fillna("")
        W["part"] = (W.variant == "original").map({True: "original", False: "variant"})
        return W
    W = pd.read_csv(d / "gen_stage2_rows_1030.csv", dtype=str).fillna("")
    W["group"] = [GEN_GROUP[(s, m)] for s, m in zip(W.set, W.model)]
    W["part"] = "-"
    if "row5_rule_batch" in W:                        # column name of the 10/30 code; thresholds per generated.AVB_MAIN
        W["row5_rule"] = W["row5_rule_batch"]
    return W
