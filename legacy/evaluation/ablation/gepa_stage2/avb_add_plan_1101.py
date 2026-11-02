#!/usr/bin/env python3
"""AVB additions for the 11/02 run (user scope 11/01, final). No calls, no item files outside runs/ written.

Keep every existing window (P01/P02 194, P03-P09 383). Add windows built by build_items --anchor-mode eligible (classes open / close,
cut / chop, stir / mix / whisk; no collision class; no loudness filter, as for the existing windows) that do not overlap any existing
window of the same video, and that do not run past the video end. AVB items of an added window: shift early / late (where the builder
finds a clean shift) + the original (only when the window has a shift). The >= 20 dB subset = added windows whose AVB anchor(s) pass
make_mute_anchor.db_reimpl >= 20 on the 25 s builder window (eligible_pairs_1101.csv), reported as its own table line.
  python gepa_stage2/avb_add_plan_1101.py   -> runs/obsval_1028/avb_add_items_1101.json, avb_add_plan_1101.json
"""
import importlib.util, json, subprocess, sys
from collections import Counter
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
V12 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/videos")
OUT = HERE / "runs/obsval_1028"
GROUPS = {"P01P02": ["P01", "P02"], "P03P09": [f"P0{k}" for k in range(3, 10)]}
CALLS_PER_ITEM = 5.26          # full-video pipeline, HD-EPIC (10/30 holdout logs)


def main():
    spec = importlib.util.spec_from_file_location("build_items", PILOT / "build_items.py")
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    B.ANCHOR_MODE = "eligible"
    pairs = pd.read_csv(OUT / "eligible_pairs_1101.csv")
    passing = set(zip(pairs.video_id, pairs.nid, pairs["sound"])) & set(zip(pairs[pairs.db >= 20].video_id, pairs[pairs.db >= 20].nid, pairs[pairs.db >= 20]["sound"]))
    old = {"P01P02": json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json")), "P03P09": json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))}
    hodur = json.load(open(HO / "video_durations.json")) if (HO / "video_durations.json").exists() else {}
    plan, added_items = {}, []
    for grp, parts in GROUPS.items():
        s, n = B.load_hdepic(parts)
        anc = B.find_anchors_eligible(s, n)
        new = B.build_windows(s, n, anc)
        ow = {}
        for x in old[grp]:
            if x["variant"] == "original":
                ow.setdefault(x["video_id"], []).append(tuple(x["clip"]))
        durs = {}
        keep = []
        for x in new:
            v, (lo, hi) = x["video_id"], x["clip"]
            if any(lo < b and hi > a for a, b in ow.get(v, [])):
                continue
            if v not in durs:
                durs[v] = float(hodur[v]) if v in hodur else float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(V12 / f"{v}.mp4")], capture_output=True, text=True).stdout.strip() or 0)
            if hi > durs[v]:
                continue
            keep.append(x)
        win = {}
        for x in keep:
            win.setdefault((x["video_id"], tuple(x["clip"])), {})[x["variant"]] = x
        avb, sub20 = [], []
        for (v, clip), vs in win.items():
            sh = [vs[k] for k in ("fail_audio_shift_early", "fail_audio_shift_late") if k in vs]
            if not sh:
                continue
            o = vs["original"]
            items = sh + [o]
            avb += items
            ga = anc[(anc.video_id == v) & (anc.a_st >= clip[0]) & (anc.a_en <= clip[1])]
            ok = len(ga) and all((v, r.nid, r.sound) in passing for r in ga.itertuples())
            if ok:
                sub20 += items
        cls = Counter(e["sound"] for x in avb if x["variant"] == "original" for e in x["events"] if e["kind"] == "sounding")
        old_avb = [x for x in old[grp] if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")]
        plan[grp] = dict(existing_windows=len({(x["video_id"], tuple(x["clip"])) for x in old[grp] if x["variant"] == "original"}),
                         existing_avb_shift_items=len(old_avb), added_windows=len({(x["video_id"], tuple(x["clip"])) for x in avb}),
                         added_avb_items=len(avb), added_by_variant=dict(Counter(x["variant"] for x in avb)),
                         added_sounding_classes=dict(cls), subset_20db_items=len(sub20),
                         subset_20db_windows=len({(x["video_id"], tuple(x["clip"])) for x in sub20}),
                         calls_row1=round(len(avb) * CALLS_PER_ITEM), calls_row2=round(len(avb) * CALLS_PER_ITEM),
                         calls_row4_max=len(avb), unique_new_clips=len({(x["video_id"], tuple(x["clip"]), x["variant"]) for x in avb}))
        for x in avb:
            added_items.append(dict(x, group=grp, subset_20db=x in sub20))
    json.dump(added_items, open(OUT / "avb_add_items_1101.json", "w"))
    json.dump(plan, open(OUT / "avb_add_plan_1101.json", "w"), indent=1)
    print(json.dumps(plan, indent=1))


if __name__ == "__main__":
    main()
