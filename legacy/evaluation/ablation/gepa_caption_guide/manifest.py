#!/usr/bin/env python3
"""Build train/val/test manifests (JSONL) for the GEPA caption-guide experiment.

One manifest row = one video (the unit of a judge call); GT and feedback are
per event inside the row.

Input per source: a per-event V-axis GT CSV with at least
    video_relpath, event_id, v_gt            (PASS/FAIL; TIE rows dropped)
optional columns
    rationale                                 human rationale text (any column named rationale/gt_reason)
    caption_ok                                1/0/blank: does the caption mention this GT event correctly
                                              (from hdepic_caption_recall.py or caption_accuracy.py; blank = unknown)

Sources config (JSON):
{
  "hdepic": {"prompt_json": "...", "outputs_dir": "...", "caption_json": "...", "gt_csv": "...", "group_col": "participant"},
  "mova":   {"prompt_json": "...", "outputs_dir": "...", "caption_json": "...", "gt_csv": "..."}
}
group_col (optional) is a GT CSV column used for grouped splitting (HD-EPIC participant),
so held-out videos come from unseen participants.

Split: --train 0.6 --val 0.15 --test 0.25 (per source, grouped when group_col given),
stratified on caption_ok mean per video when available. The "cross" test bucket
(HD-EPIC good-caption videos + generated bad-caption videos) is tagged in the test
manifest as bucket=cross so eval_guide.py can report it separately.

    python manifest.py --sources sources.json --out-dir manifests --seed 0
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


def load_gt(gt_csv: Path):
    rows = list(csv.DictReader(gt_csv.open(encoding="utf-8")))
    per_video = defaultdict(lambda: {"gt": {}, "rationale": {}, "caption_ok": {}, "group": "", "outputs_dir": ""})
    rat_col = next((c for c in ("rationale", "gt_reason", "human_rationale") if rows and c in rows[0]), None)
    for r in rows:
        lab = (r.get("v_gt") or r.get("V_gt") or "").strip().upper()
        if lab not in ("PASS", "FAIL"):
            continue
        v = per_video[r["video_relpath"]]
        eid = r["event_id"]
        v["gt"][eid] = lab
        if r.get("outputs_dir"):
            v["outputs_dir"] = r["outputs_dir"]
        if rat_col and r.get(rat_col):
            v["rationale"][eid] = r[rat_col]
        co = (r.get("caption_ok") or "").strip()
        v["caption_ok"][eid] = None if co == "" else bool(int(float(co)))
    return per_video, rows


def caption_ok_mean(v):
    vals = [x for x in v["caption_ok"].values() if x is not None]
    return None if not vals else sum(vals) / len(vals)


def split_source(name, cfg, per_video, rows, fr, rng):
    group_col = cfg.get("group_col")
    group_of = {}
    if group_col:
        for r in rows:
            group_of[r["video_relpath"]] = r.get(group_col, "")
    units = defaultdict(list)  # group -> relpaths
    for rp in per_video:
        units[group_of.get(rp, rp)].append(rp)
    keys = list(units)
    # stratify groups by caption_ok mean (unknown -> own stratum)
    def stratum(k):
        has_fail = any("FAIL" in per_video[rp]["gt"].values() for rp in units[k])
        ms = [caption_ok_mean(per_video[rp]) for rp in units[k]]
        ms = [m for m in ms if m is not None]
        if not ms:
            return f"unk|{int(has_fail)}"
        m = sum(ms) / len(ms)
        return ("hi" if m >= 0.7 else "lo" if m < 0.4 else "mid") + f"|{int(has_fail)}"
    by_s = defaultdict(list)
    for k in keys:
        by_s[stratum(k)].append(k)
    out = {"train": [], "val": [], "test": []}
    for s, ks in by_s.items():
        rng.shuffle(ks)
        n = len(ks)
        n_tr = int(round(n * fr[0])); n_va = int(round(n * fr[1]))
        out["train"] += ks[:n_tr]; out["val"] += ks[n_tr:n_tr + n_va]; out["test"] += ks[n_tr + n_va:]
    res = {k: [] for k in out}
    for split, ks in out.items():
        for k in ks:
            for rp in units[k]:
                v = per_video[rp]
                m = caption_ok_mean(v)
                bucket = ""
                if split == "test" and m is not None:
                    if name == "hdepic" and m >= 0.7:
                        bucket = "cross"
                    if name != "hdepic" and m < 0.5:
                        bucket = "cross"
                res[split].append({
                    "source": name, "relpath": rp,
                    "prompt_json": cfg["prompt_json"], "outputs_dir": v["outputs_dir"] or cfg["outputs_dir"],
                    "caption_json": cfg["caption_json"],
                    "gt": v["gt"], "rationale": v["rationale"], "caption_ok": v["caption_ok"],
                    "group": group_of.get(rp, ""), "bucket": bucket,
                })
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--train", type=float, default=0.6)
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    sources = json.loads(a.sources.read_text())
    a.out_dir.mkdir(parents=True, exist_ok=True)
    agg = {"train": [], "val": [], "test": []}
    for name, cfg in sources.items():
        per_video, rows = load_gt(Path(cfg["gt_csv"]))
        res = split_source(name, cfg, per_video, rows, (a.train, a.val), rng)
        for k in agg:
            agg[k] += res[k]
        print(f"{name}: videos={len(per_video)} train={len(res['train'])} val={len(res['val'])} test={len(res['test'])} "
              f"cross={sum(1 for r in res['test'] if r['bucket'] == 'cross')}")
    for k, rows in agg.items():
        rng.shuffle(rows)
        with (a.out_dir / f"{k}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", a.out_dir)


if __name__ == "__main__":
    main()
