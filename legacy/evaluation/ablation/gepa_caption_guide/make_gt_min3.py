#!/usr/bin/env python3
"""gt_event_majority.csv (220 set) -> per-source V-axis event GT CSVs for manifest.py.

    python make_gt_min3.py --majority /projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/min3_gt/gt_event_majority.csv \
        --outputs-root /projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3 --out-dir gt

Writes gt/mova_v_events.csv and gt/ltx_v_events.csv with columns
    video_relpath, event_id, v_gt, model
event_id is the judge's id ("event_N"), mapped from the GT event_key through the
prompt json: new_eval.build_scoring_events gives each event its source_id (the raw
event id, e.g. "sounding_action_2") next to its event_id. Rows whose key cannot be
mapped are reported and dropped. Requires --prompt-json and PYTHONPATH to new_eval.
video_relpath is resolved by locating video_file under <outputs-root>/<model>/.
caption_ok is left out here; add it with add_caption_ok.py once the caption-accuracy
per-event output is mapped (optional).
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import new_eval as NE

MODEL_DIR = {"MOVA": "MOVA", "LTX_2p3": "LTX_2p3"}
OUT_NAME = {"MOVA": "mova", "LTX_2p3": "ltx"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--majority", type=Path, required=True)
    ap.add_argument("--outputs-root", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("gt"))
    ap.add_argument("--prompt-json", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    meta_map = NE.build_item_meta_map(NE.load_prompt_items(a.prompt_json), modality_filter=None,
                                      item_overrides=None, relative_only=False)
    keymap_cache = {}

    def key_to_id(model, rel):
        """{event_key -> event_id} for one video, via source_id / aliases / kind-order fallback."""
        if rel in keymap_cache:
            return keymap_cache[rel]
        vp = a.outputs_root / MODEL_DIR[model] / rel
        meta = meta_map.get(NE.infer_item_id_from_path(vp))
        m = {}
        if meta:
            counts = defaultdict(int)
            for se in NE.build_scoring_events(meta):
                if se.get("source_id"):
                    m[se["source_id"]] = se["event_id"]
                for al in se.get("aliases") or []:
                    m.setdefault(al, se["event_id"])
                base = {"speech": "speech", "silent": "silent_action", "sounding": "sounding_action"}.get(se["kind"], se["kind"])
                counts[base] += 1
                m.setdefault(base if counts[base] == 1 else f"{base}_{counts[base]}", se["event_id"])
        keymap_cache[rel] = m
        return m

    index = {}
    for model, sub in MODEL_DIR.items():
        root = a.outputs_root / sub
        for p in root.rglob("*.mp4"):
            index[(model, p.name)] = str(p.relative_to(root))

    rows_by_model = {m: [] for m in MODEL_DIR}
    missing, tie, unmapped = 0, 0, []
    for r in csv.DictReader(a.majority.open(encoding="utf-8")):
        m = r["model"]
        if m not in rows_by_model:
            continue
        lab = (r.get("V") or "").strip().upper()
        if lab not in ("PASS", "FAIL"):
            tie += 1
            continue
        rel = index.get((m, r["video_file"]))
        if rel is None:
            missing += 1
            continue
        eid = key_to_id(m, rel).get(r["event_key"])
        if eid is None:
            unmapped.append((m, r["video_file"], r["event_key"]))
            continue
        rows_by_model[m].append({"video_relpath": rel, "event_id": eid, "event_key": r["event_key"], "v_gt": lab, "model": m})

    for m, rows in rows_by_model.items():
        out = a.out_dir / f"{OUT_NAME[m]}_v_events.csv"
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["video_relpath", "event_id", "event_key", "v_gt", "model"])
            w.writeheader(); w.writerows(rows)
        vids = len({r["video_relpath"] for r in rows})
        print(f"{m}: {len(rows)} events / {vids} videos -> {out}")
    print(f"skipped: non-PASS/FAIL={tie}, video not found={missing}, unmapped event_key={len(unmapped)}")
    for u in unmapped[:10]:
        print("  unmapped:", u)


if __name__ == "__main__":
    main()
