#!/usr/bin/env python3
"""11/02: inputs for row 2 of the AVB additions, after the GPU jobs. No calls.
captions_p12.json / captions_p3p9.json (keys <item>/<item>_v1_raw.mp4, from hdepic_avbadd_1102/gpu/captions_*.json) and
sync_sections_avbadd.json (Synchformer action-window lines, keyed by the resolved video path, same text as hdepic_main_sync_sections_1101).
  python gepa_stage2/avbadd_prep_row2_1102.py
"""
import json, os
from pathlib import Path
import pandas as pd

A = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_avbadd_1102")
S = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030/avbadd")
for g, parts in (("p12", ["p12"]), ("p3p9", ["p3p9a", "p3p9b"])):
    out = {}
    for p in parts:
        out.update(json.load(open(A / "gpu" / f"captions_{p}.json")))
    ids = os.listdir(A / g / "eval")
    miss = [i for i in ids if f"{i}/{i}_v1_raw.mp4" not in out]
    json.dump(out, open(A / f"captions_{g}.json", "w"), indent=1)
    print(g, "captions", len(out), "missing", len(miss))
pe = pd.concat(pd.read_csv(f) for f in sorted(S.glob("per_event_shard*.csv")))
sec = {}
for g in ("p12", "p3p9"):
    for i in os.listdir(A / g / "eval"):
        x = pe[pe.item_id == i]
        if not len(x):
            continue
        multi = len(x) > 1
        lines = [(f"'{r.label}': " if multi else "") + ("Synchformer, window around the action: no reading" if r.status != "ok" or pd.isna(r.offset) else
                 f"Synchformer, window around the action: most likely offset {float(r.offset):+.1f} s (positive = audio later than video), "
                 f"probability {float(r.prob):.2f}; probability of zero offset {float(r.p_offset0):.2f}") for r in x.itertuples()]
        sec[str((A / g / "eval" / i / f"{i}_v1_raw.mp4").resolve())] = ("Synchformer audio-visual synchronization (raw offset estimate):\n"
            "- Synchformer estimates the offset between the audio track and the video in a short window around each binding event's visible "
            "action. Offsets are on a 0.2 s grid; probabilities are the model's own, not correctness labels.\n" + "\n".join(f"- {l}" for l in lines))
json.dump(sec, open(A / "sync_sections_avbadd.json", "w"), indent=1)
print("sync sections", len(sec))
