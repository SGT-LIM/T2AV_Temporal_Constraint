#!/usr/bin/env python3
"""hdepic_medium_gt.csv (video-level axis GT + broken_event_idx) -> per-event V GT CSV.

Rule: every target event is V PASS except, for the V-breaking variants
(fail_hand_swap, fail_noun_swap), the event at broken_event_idx, which is FAIL.
Event ids are taken from new_eval.build_scoring_events(item_meta) so they match
what the judge returns; broken_event_idx indexes item_meta["events"] in order.

Videos are located by walking every --outputs-dir (the 6 shard dirs are fine)
and mapping infer_item_id_from_path(video) -> item_id. Each row records its own
outputs_dir so manifest.py can handle sharded layouts.

Run from evaluation/ablation with PYTHONPATH set:
    python gepa_caption_guide/make_gt_hdepic.py \
        --gt /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_gt.csv \
        --prompt-json /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_prompts.json \
        --outputs-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_shard{0..5} \
        --out gepa_caption_guide/gt/hdepic_v_events.csv
"""
import argparse
import csv
import re
from pathlib import Path

import new_eval as NE

V_FAIL_VARIANTS = {"fail_hand_swap", "fail_noun_swap"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--outputs-dir", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    items = NE.load_prompt_items(a.prompt_json)
    meta_map = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)

    video_of = {}
    for root in a.outputs_dir:
        for p in NE.find_video_files(root):
            video_of[NE.infer_item_id_from_path(p)] = (str(root), str(p.relative_to(root)))
    print(f"videos indexed: {len(video_of)}")

    rows, n_fail, missing_video, missing_meta, bad_idx = [], 0, 0, 0, 0
    for r in csv.DictReader(a.gt.open(encoding="utf-8")):
        iid = r["item_id"]
        meta = meta_map.get(iid)
        if meta is None:
            missing_meta += 1
            continue
        loc = video_of.get(iid)
        if loc is None:
            missing_video += 1
            continue
        events = NE.build_scoring_events(meta)
        broken = None
        if r["variant"] in V_FAIL_VARIANTS:
            try:
                broken = int(r["broken_event_idx"])
            except ValueError:
                bad_idx += 1
        if r["variant"] in V_FAIL_VARIANTS and r["visual_event_correctness"] != "FAIL":
            print(f"  [WARN] {iid}: V-breaking variant but V={r['visual_event_correctness']}")
        m = re.match(r"hdepic_(P\d+)", iid)
        participant = m.group(1) if m else ""
        clip = re.sub(r"^hdepic_", "", iid).rsplit("_", 1)[0]   # P01-20240202-110250_0001710
        for k, se in enumerate(events):
            lab = "FAIL" if (broken is not None and k == broken) else "PASS"
            n_fail += lab == "FAIL"
            rows.append({"video_relpath": loc[1], "outputs_dir": loc[0], "event_id": se["event_id"],
                         "v_gt": lab, "participant": participant, "clip": clip, "variant": r["variant"], "item_id": iid})
        if broken is not None and broken >= len(events):
            bad_idx += 1

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    vids = len({r["video_relpath"] for r in rows})
    print(f"wrote {len(rows)} events / {vids} videos, FAIL events={n_fail} -> {a.out}")
    print(f"skipped: no meta={missing_meta}, no video={missing_video}, bad broken_idx={bad_idx}")
    print("participants:", sorted({r['participant'] for r in rows}), "clips:", len({r['clip'] for r in rows}))


if __name__ == "__main__":
    main()
