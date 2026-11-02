#!/usr/bin/env python3
"""Event inventory of the HD-EPIC main table (11/01), per axis and participant. No calls. Writes docs/event_inventory_1101.md.
Items: P01/P02 = all 194 hdepic windows (items_hdepic_medium_with_clips_v2.json; option ii, 11/01) and the v3-test movement set
(hdepic_move_prompts.json, TCC); P03-P09 = every holdout window (items_hdepic_p3p9_v1_with_clips_holdout.json).
  A    target sound classes of the sounding events in the windows (the clean-pair anchor classes; positives on originals) and
       the claimed absent class of each fail_absent_sound item (parsed from fail_reason; negatives)
  AVB  sound classes of the sounding events in windows that have a shift variant
  V    verbs and nouns of every prompt event (silent + sounding) in the windows
  TCR  verbs / nouns of the events in windows whose order swap passes the 1.0 s gap rule
  TCC  verbs / nouns of the counted events (P01/P02: movement set; P03-P09: count_off windows)
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import filters

PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/items_hdepic_medium_with_clips_v2.json")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/items_hdepic_p3p9_v1_with_clips_holdout.json")
MOVE = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_move_prompts.json")
OUT = Path((_LEGACY_ROOT + "/docs/event_inventory_1101.md"))
W = lambda i: re.search(r"(P\d+-\d+-\d+_\d+)", i).group(1)


def main():
    man = [json.loads(l) for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "manifests_v3/test.jsonl")]
    # 11/01 option (ii): P01/P02 = all 194 windows (the table now uses every P01/P02 window under the P03-P09 rules)
    items = json.load(open(PILOT)) + json.load(open(HO))
    inv = defaultdict(Counter)          # (axis, kind, participant) -> Counter(type)
    byw = defaultdict(dict)
    for x in items:
        byw[(x["video_id"], tuple(x["clip"]))][x["variant"]] = x
    for (vid, _), vs in byw.items():
        p = vid[:3]
        o = vs.get("original")
        if not o:
            continue
        for e in o["events"]:
            nm = f"{e['verb']} {e['noun']}"
            inv[("V", "verb", p)][e["verb"]] += 1
            inv[("V", "noun", p)][e["noun"]] += 1
            if e["kind"] == "sounding":
                inv[("A", "target sound (positive)", p)][e["sound"]] += 1
                if "fail_audio_shift_early" in vs or "fail_audio_shift_late" in vs:
                    inv[("AVB", "sound class", p)][e["sound"]] += 1
            if "fail_order_swap" in vs and filters.min_gap(o["sequence"]) >= 1.0:
                inv[("TCR", "action", p)][nm] += 1
            if p != "P01" and p != "P02" and "fail_count_off" in vs:
                inv[("TCC", "action", p)][nm] += 1
        a = vs.get("fail_absent_sound")
        if a:
            m = re.search(r"claims (.+?) \(", a.get("fail_reason", ""))
            if m:
                inv[("A", "claimed absent sound (negative)", p)][m.group(1)] += 1
    test_mv = {m["item_id"] for m in man if m["source"] == "hdmove"}
    for x in json.load(open(MOVE)):
        if x["item_id"] in test_mv and x["item_id"].endswith("_pass"):
            p = W(x["item_id"])[:3]
            for e in x["events"]:
                inv[("TCC", "action", p)][e.get("action", "?")] += 1
    parts = sorted({k[2] for k in inv})
    L = ["# Event inventory of the HD-EPIC main table (2026-11-01, no calls)", "",
         "Script `evaluation/ablation/gepa_stage2/event_inventory_1101.py`. Items:",
         "- P01/P02: all 194 hdepic windows (option ii, 11/01), plus the v3-test movement set (TCC).",
         "- P03–P09: all 383 holdout windows.",
         "", "Counts are prompt events of the original item of each window (or claimed absent classes for A negatives).",
         "Distinct types are per participant.", ""]
    for ax, kind in [("A", "target sound (positive)"), ("A", "claimed absent sound (negative)"), ("AVB", "sound class"),
                     ("V", "verb"), ("V", "noun"), ("TCR", "action"), ("TCC", "action")]:
        allc = Counter()
        for p in parts:
            allc += inv[(ax, kind, p)]
        L += [f"## {ax}: {kind}", "", f"All participants: {len(allc)} distinct types, {sum(allc.values())} events.", "",
              "| participant | events | distinct types | types not seen in P01/P02 | top types (count) |", "|---|---|---|---|---|"]
        p12 = set(inv[(ax, kind, "P01")]) | set(inv[(ax, kind, "P02")])
        for p in parts:
            c = inv[(ax, kind, p)]
            if not c:
                continue
            new = len(set(c) - p12) if p not in ("P01", "P02") else "–"
            L.append(f"| {p} | {sum(c.values())} | {len(c)} | {new} | " + ", ".join(f"{t} ({n})" for t, n in c.most_common(8)) + " |")
        L += ["", f"All types ({len(allc)}): " + ", ".join(f"{t} ({n})" for t, n in allc.most_common()), ""]
    old = OUT.read_text() if OUT.exists() else ""
    k = min([i for i in (old.find("\n## Sound classes co-occurring"), old.find("\n## Per-class table")) if i >= 0], default=-1)
    keep = old[k:] if k >= 0 else ""                 # sections appended by sound_class_inventory / eligible_class_table stay
    OUT.write_text("\n".join(L) + "\n" + keep)
    print(f"-> {OUT}")
    for ax, kind in [("A", "target sound (positive)"), ("A", "claimed absent sound (negative)"), ("AVB", "sound class"), ("V", "verb"), ("V", "noun"), ("TCR", "action"), ("TCC", "action")]:
        print(ax, kind, {p: len(inv[(ax, kind, p)]) for p in parts if inv[(ax, kind, p)]})


if __name__ == "__main__":
    main()
