#!/usr/bin/env python3
"""Merge clip-level AVoCaDO captions (av + mute passes) and expand to HD-EPIC item keys.

Item key = what run_agentic_eval sees: '<item_id>/<item_id>_v1_raw.mp4' (relpath under outputs-dir).
Mapping item -> clip comes from hdepic_medium_gt.csv (clip_path column). Output format matches the
existing external caption JSONs: {relpath: {"caption": str, ...}}.

  python expand_hdepic_captions.py
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[3] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[0])  # legacy path roots, see legacy/README.md
import json, os
import pandas as pd

CODE = _LEGACY_CODE
GT = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_gt.csv"
SRC = [f"{CODE}/captions/avocado_fps2_plain_v3_hdepic_av.json", f"{CODE}/captions/avocado_fps2_plain_v3_hdepic_mute.json"]
OUT = f"{CODE}/captions/avocado_fps2_plain_v3_hdepic_items.json"

clips = {}
for f in SRC:
    d = json.load(open(f))
    for k, v in d.items():
        clips[os.path.basename(k)] = v          # key by clip filename
    print(f"{os.path.basename(f)}: {len(d)} captions")
print("unique clip captions:", len(clips))

g = pd.read_csv(GT)
out, missing = {}, []
for r in g.itertuples():
    clip = os.path.basename(r.clip_path)
    if clip not in clips:
        missing.append((r.item_id, clip)); continue
    key = f"{r.item_id}/{r.item_id}_v1_raw.mp4"
    out[key] = dict(clips[clip], source_clip=clip)
json.dump(out, open(OUT, "w"), indent=1)
print(f"items with caption: {len(out)} / {len(g)}  -> {OUT}")
if missing:
    print(f"MISSING {len(missing)} (first 10):"); [print("  ", m) for m in missing[:10]]
# sanity
k = next(iter(out)); print("\nexample key:", k); print(out[k]["caption"][:300])
mute = [k for k in out if k.split("/")[0].endswith("_mute")]
print(f"\nmute items: {len(mute)}; example:", out[mute[0]]["caption"][:200] if mute else "-")
