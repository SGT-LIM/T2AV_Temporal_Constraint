#!/usr/bin/env python3
# Replaced by t2av_eval/data/mute_anchor_reselect.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""One loudness path for both groups (user 11/01, option a). No judge calls.
Every mute_anchor anchor (P01/P02 10/28 set, 78; P03-P09 candidates from the holdout anchor table) gets its dB from
make_mute_anchor.db_reimpl on the ORIGINAL clip audio (16 kHz mono; RMS of the 0.2 s after the sound onset, or the 0.2 s before
the sound end for turn-off tap, over the median 50 ms frame RMS of the clip). Kept: dB >= 20.
P01/P02: the existing 11/01 rows 1 / 4 / 5 (runs/obsval_1028/hd_ma_rows_1101.csv) are re-scored on the surviving anchors' rows
(mute_anchor + its sham + its original). P03-P09: the selection is compared with the 40 anchors built by build_p3p9.
  python gepa_stage2/mute_anchor_reselect_1101.py
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import make_mute_anchor as MA
import rep_scoring as RS

M12 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/hdepic_mute_anchor_1028")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
OUT = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028"


def main():
    cache = {}

    def dbv(clip, s0, s1, tap):
        if clip not in cache:
            cache.clear(); cache[clip] = MA.audio16(clip)
        return round(float(MA.db_reimpl(cache[clip], s0, s1, tap)), 2)

    # ---- P01/P02
    man = pd.DataFrame([json.loads(l) for l in open(M12 / "manifest.jsonl")])
    mu = man[man.variant == "mute_anchor"].copy()
    mu["db_reimpl"] = [dbv(o, s[0], s[1], a == "turn-off tap") for o, s, a in zip(mu.orig_video, mu.sound, mu.aclass)]
    mu["keep"] = mu.db_reimpl >= MA.DB_MIN
    mu[["item_id", "clip", "nid", "aclass", "split", "db", "db_source", "db_reimpl", "keep"]].to_csv(OUT / "ma_p12_reselect_1101.csv", index=False)
    print(f"P01/P02: {int(mu.keep.sum())} of {len(mu)} anchors keep dB >= 20 under the re-implementation "
          f"(stored-value median {mu.db.median():.1f} dB, re-implementation median {mu.db_reimpl.median():.1f} dB, "
          f"median difference {(mu.db_reimpl - mu.db).median():+.1f} dB)")
    print(mu.groupby("aclass").keep.agg(["size", "sum"]).to_string())
    keep = set(zip(mu[mu.keep]["clip"], mu[mu.keep].nid))
    man["keep"] = [(c, n) in keep for c, n in zip(man["clip"], man.nid)]
    rows = pd.read_csv(OUT / "hd_ma_rows_1101.csv").fillna("")
    rows["item_id"] = rows.uid.str.split("|").str[1]
    rows = rows.merge(man[["item_id", "keep"]], on="item_id")
    tab = []
    for sub, g0 in (("all 78 (stored-value selection)", rows), ("re-implementation >= 20 dB", rows[rows.keep])):
        for c in ("row1", "row4", "row5"):
            h = g0[g0[c].isin(["yes", "no"])]
            m = RS.metrics(h.y, h[c])
            tab.append(dict(subset=sub, cond=c, n=m["n"], n_fail=m["n_fail"], acc=round(m["acc"], 3), prec=round(m["prec"], 3), rec=round(m["rec"], 3),
                            FA_orig=round(float((h[h.variant == "original"][c] == "no").mean()), 3),
                            FA_sham=round(float((h[h.variant == "sham"][c] == "no").mean()), 3)))
    T = pd.DataFrame(tab); T.to_csv(OUT / "ma_p12_reselect_table_1101.csv", index=False)
    print(T.to_string(index=False))

    # ---- P03-P09
    d = pd.read_csv(HO / "anchors_db.csv")
    d = d[d.aclass.isin(MA.ACLASS.values())].copy()
    clipp = {}
    for x in json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json")):
        if x["variant"] == "original":
            clipp[f"{x['video_id']}_{int(round(x['clip'][0] * 100)):07d}"] = x["clip_path"]
    d["key"] = [f"{v}_{int(round(lo * 100)):07d}" for v, lo in zip(d.video_id, d.lo)]
    d = d[d.key.isin(clipp)].copy()
    d["db_reimpl"] = [dbv(clipp[k], s0, s1, a == "turn-off tap") for k, s0, s1, a in zip(d.key, d.s0, d.s1, d.aclass)]
    built = pd.DataFrame([json.loads(l) for l in open(HO / "mute_anchor_1101/manifest.jsonl")])
    bk = set(zip(built[built.variant == "mute_anchor"]["clip"], built[built.variant == "mute_anchor"].nid))
    d["built"] = [(k, n) in bk for k, n in zip(d.key, d.nid)]
    d.to_csv(OUT / "ma_p3p9_reselect_1101.csv", index=False)
    print(f"P03-P09: stored-table vs recomputed dB: max |diff| {float((d.db - d.db_reimpl).abs().max()):.2f} dB over {len(d)} anchors; "
          f">= 20 dB: table {int((d.db >= 20).sum())}, recomputed {int((d.db_reimpl >= 20).sum())}")


if __name__ == "__main__":
    main()
