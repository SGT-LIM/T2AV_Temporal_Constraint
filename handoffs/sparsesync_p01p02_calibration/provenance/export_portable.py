#!/usr/bin/env python3
"""Writes the portable handoff files of this folder from the internal handoff (T2AV_data/tools/sparsesync_handoff_1106, built by
sparsesync_handoff_1106.py) and the Hugging Face checksum match (provenance/hf_match_internal.csv). Runs only on the BU SCC copy of the
data; the outputs carry no absolute path. Video paths are relative to a configurable video root that mirrors the Hugging Face
dataset layout videos/<item_id>/<item_id>_v1_raw.mp4.
  python provenance/export_portable.py
"""
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
SRC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/sparsesync_handoff_1106")
HF = dict(repo="dghadiya/T2AV_TemporalConstraint_HDEPIC", repo_type="dataset", revision="bc8e844b5e2b0f1bb77ac9c5f0c2f97e7c193e8b")


def strongest(m):
    """per-item reading used by gate_b110_v2_1030.py: per event the occurrence with the lowest p(offset 0) (ties: larger |offset|),
    then the event with the largest |offset| (ties: higher probability)."""
    best = None
    for e in m["binding_events"]:
        if e["status"] != "ok" or not e["occurrences"]:
            continue
        o = min(e["occurrences"], key=lambda o: (o["synchformer_p_offset0"], -abs(o["synchformer_offset_s"])))
        k = (abs(o["synchformer_offset_s"]), o["synchformer_prob"])
        if best is None or k > best[0]:
            best = (k, e["event_id"], o)
    return best


def main():
    rule = json.load(open(SRC.parent / "synchformer_action_1030/PREREGISTERED_RULE.json"))
    T, P = rule["T"], rule["P"]
    hf = pd.read_csv(HERE / "provenance/hf_match_internal.csv").set_index("item_id")
    man, mem, occ = [], [], []
    for m in map(json.loads, open(SRC / "manifest_p01p02_calibration.jsonl")):
        h = hf.loc[m["item_id"]]
        rel = f"videos/{m['item_id']}/{m['item_id']}_v1_raw.mp4"
        assert h.hf_path == rel and h.status == "sha256 match"
        p = {k: v for k, v in m.items() if k not in ("video_path", "video_file")}
        p.update(video_relpath=rel, video_sha256=h.local_sha256, video_size_bytes=int(h.local_size), hf_dataset=HF,
                 hf_identity="sha256 of the local clip equals the LFS sha256 of hf_dataset/video_relpath at the pinned revision")
        man.append(p)
        b = strongest(m)
        off, prob, ev = (b[0][0], b[0][1], b[1]) if b else (None, None, None)
        orig = m["variant"] == "original"
        mem.append(dict(item_id=m["item_id"], participant=m["participant"], variant=m["variant"], audio_shift_s=m["audio_shift_s"],
                        gt_avb_row=m["gt_avb_row"], in_calibration=m["in_calibration"], media_only_anchor_verdict=m["media_only_anchor_verdict"],
                        reading_event_id=ev, reading_abs_offset_s=off, reading_prob=prob,
                        used_for_T=bool(m["in_calibration"] and orig),
                        used_for_P=bool(m["in_calibration"] and not orig and off is not None and off > T + 1e-9),
                        fires_at_rule=bool(off is not None and off >= T - 1e-9 and prob >= P - 1e-9)))
        for e in m["binding_events"]:
            for k, o in enumerate(e["occurrences"]):
                occ.append(dict(item_id=m["item_id"], variant=m["variant"], audio_shift_s=m["audio_shift_s"], in_calibration=m["in_calibration"],
                                video_relpath=rel, event_id=e["event_id"], label=e["label"], gt_avb=e["gt_avb"], occurrence=k,
                                action_start_s=o["action_span_s"][0], action_end_s=o["action_span_s"][1],
                                input_start_s=o["input_window_s"][0], input_end_s=o["input_window_s"][1],
                                synchformer_offset_s=o["synchformer_offset_s"], synchformer_prob=o["synchformer_prob"],
                                synchformer_p_offset0=o["synchformer_p_offset0"]))
    with open(HERE / "manifest.jsonl", "w") as f:
        for p in man:
            f.write(json.dumps(p) + "\n")
    pd.DataFrame(mem).to_csv(HERE / "calibration_membership.csv", index=False)
    pd.DataFrame(occ).to_csv(HERE / "event_windows.csv", index=False)
    hf.reset_index()[["item_id", "variant", "audio_shift_s", "in_calibration", "hf_path", "hf_size", "hf_sha256", "local_sha256", "status"]] \
        .rename(columns={"hf_path": "video_relpath"}).to_csv(HERE / "hf_mapping.csv", index=False)
    chk = json.load(open(SRC / "checks.json"))
    chk.pop("missing_files", None)
    chk["source_md5"] = {Path(k).name: v for k, v in chk["source_md5"].items()}
    chk["hf_dataset"] = HF
    json.dump(chk, open(HERE / "provenance/checks.json", "w"), indent=1)
    M = pd.DataFrame(mem)
    print(len(man), "items;", int(M.used_for_T.sum()), "used for T;", int(M.used_for_P.sum()), "used for P;", len(occ), "occurrences")


if __name__ == "__main__":
    main()
