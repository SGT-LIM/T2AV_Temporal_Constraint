#!/usr/bin/env python3
"""HD-EPIC P03-P09 HOLDOUT build, post-clip steps (10/28). No API calls. Nothing under P01/P02 paths is written.

Pipeline (same rules as P01/P02; every output under T2AV_data/real_av_holdout_p3p9_1028/):
  1. real_av_pilot/build_items.py hdepic --participants P03..P09 --out items_hdepic_p3p9.json  (clean-pair anchors, all variants)
  2. drop windows whose 25 s clip runs past the end of the downloaded video (as drop_short_windows.py did for P01/P02)
     -> items_hdepic_p3p9_v1.json, dropped_windows_past_video_end.json
  3. real_av_pilot/make_clips.py items_hdepic_p3p9_v1.json --videos real_av/hdepic/videos_P03_P09 --out clips/ (ffmpeg -threads 2 shim)
  4. this script:
     - per-anchor loudness: for every clean-pair anchor (build_items.find_anchors) inside a window, dB = RMS of the 0.2 s after the
       sound onset (turn-off tap: the 0.2 s before the sound end) / median 50 ms frame RMS of the original clip, 16 kHz mono.
       This re-implementation of the 10/08 computation reads about 4 dB LOW against the stored P01/P02 values (median, n=157).
       NOT applied as a filter; stored per anchor (anchors_db.csv) and per window (window_db.csv: db_min, db_max, n_anchor;
       tier like P01/P02: clear >= 20, ambiguous 5-20, low < 5) and as item fields anchor_db_min / anchor_db_max.
     - footstep flag: fail_absent_sound items whose claim class is 'footstep' (the hdfoot construction).
     - holdout=true, split='holdout' on every item; no stage-1 selection.
     - to_eval_format.py -> eval/<item_id>/<item_id>_v1_raw.mp4, prompts_hdepic_p3p9.json, gt_hdepic_p3p9.csv

  python gepa_stage2/holdout_p3p9_1028.py
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import json, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_mute_anchor as MA

D = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
PARTS = [f"P0{i}" for i in range(3, 10)]


def main():
    items = json.load(open(D / "items_hdepic_p3p9_v1_with_clips.json"))
    B = MA.bi()
    s, n = B.load_hdepic(PARTS)
    anc = B.find_anchors(s, n)
    anc = anc[anc.vc.isin(MA.ACLASS)]
    wins = {}
    for it in items:
        wins.setdefault((it["video_id"], tuple(it["clip"])), it)
    rows = []
    for (vid, (lo, hi)), it in wins.items():
        orig = next(x["clip_path"] for x in items if x["video_id"] == vid and tuple(x["clip"]) == (lo, hi) and x["variant"] == "original")
        g = anc[(anc.video_id == vid) & (anc.a_st >= lo) & (anc.a_en <= hi) & (anc.s_st >= lo) & (anc.s_en <= hi + 5)]
        if not len(g):
            continue
        y = MA.audio16(orig)
        for r in g.itertuples():
            s0, s1 = r.s_st - lo, min(r.s_en, hi) - lo
            rows.append(dict(video_id=vid, lo=lo, hi=hi, nid=r.nid, aclass=MA.ACLASS[r.vc], verb=r.verb, noun=r.noun, a0=round(r.a_st - lo, 3),
                             s0=round(s0, 3), s1=round(s1, 3), db=round(float(MA.db_reimpl(y, s0, s1, r.vc == 8)), 2), db_source="reimpl (reads ~4 dB low)"))
        print(f"[db] {vid} {lo:.2f}: {len(g)} anchors", flush=True)
    a = pd.DataFrame(rows)
    a.to_csv(D / "anchors_db.csv", index=False)
    w = a.groupby(["video_id", "lo", "hi"]).db.agg(db_min="min", db_max="max", n_anchor="size").reset_index()
    w["tier"] = np.where(w.db_min >= 20, "clear", np.where(w.db_min >= 5, "ambiguous", "low"))
    w.to_csv(D / "window_db.csv", index=False)
    wd = {(r.video_id, round(r.lo, 3), round(r.hi, 3)): r for r in w.itertuples()}
    for it in items:
        r = wd.get((it["video_id"], round(it["clip"][0], 3), round(it["clip"][1], 3)))
        it["anchor_db_min"] = None if r is None else float(r.db_min)
        it["anchor_db_max"] = None if r is None else float(r.db_max)
        it["anchor_db_tier"] = None if r is None else r.tier
        it["anchor_db_note"] = "re-implemented RMS, reads ~4 dB low vs the 10/08 P01/P02 values; not used as a filter"
        it["footstep_claim"] = bool(it["variant"] == "fail_absent_sound" and (it.get("a_fail_claim") or {}).get("sound") == "footstep")
        it["holdout"] = True
        it["split"] = "holdout"
    out = D / "items_hdepic_p3p9_v1_with_clips_holdout.json"
    json.dump(items, open(out, "w"), indent=1)
    subprocess.run([sys.executable, str(PILOT / "to_eval_format.py"), str(out), "--outputs-dir", str(D / "eval"),
                    "--prompt-json", str(D / "prompts_hdepic_p3p9.json"), "--gt-csv", str(D / "gt_hdepic_p3p9.csv")], check=True, cwd=str(PILOT))
    df = pd.DataFrame(items)
    df["participant"] = df.video_id.str[:3]
    print(df.groupby(["participant", "variant"]).size().unstack(fill_value=0).to_string())
    print("footstep-claim items:", int(df.footstep_claim.sum()))
    print("windows by tier:", w.tier.value_counts().to_dict())


if __name__ == "__main__":
    main()
