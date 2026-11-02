#!/usr/bin/env python3
"""Frame-level FLAM peak times for the set-B sound spans (10/30). GPU, env t2av_eval. No Gemini calls.

The Synchformer pass (sync_1030.py) located each event's sound with FLAM (our Tool_Use/flam_audio, hop_sec=5, threshold 0.98,
the clone's _queries_for_label queries) but stored only each detection's [start, end] (0.31 s frames). This re-runs the identical,
deterministic FLAM call per clip and records, for every detection, the time and score of its per-frame score peak, matched to the
stored spans. Output: T2AV_data/tools/synchformer_1030/flam_peaks.json  {item_id: {label: [{span, peak_time, peak_score}, ...]}}
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import importlib.util, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
CLONE = Path("/projectnb/ivc-ml/youngsun/tmp/t2av_multiagent")
SYNC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_1030")
sys.path.insert(0, str(HERE))
from sync_1030 import FLAM_KW


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    OUR = load("our_flam_audio", ABL / "Tool_Use" / "flam_audio.py")
    THEIR = load("their_flam_audio_q", CLONE / "Tool_Use" / "flam_audio.py")     # only for _queries_for_label (same queries as the pass)
    out = {}
    recs = sorted((SYNC / "records").glob("*.json"))
    for k, f in enumerate(recs):
        rec = json.load(open(f))
        if "events" not in rec:
            continue
        iid = f.stem
        sound = [e for e in rec["events"] if e["kind"] == "sounding_action"]
        queries = []
        for e in sound:
            queries += [q for q in THEIR._queries_for_label("sounding_action", e["label"]) if q not in queries]
        ev = OUR.extract_flam_evidence(rec["video_path"], queries=queries, **FLAM_KW)
        byq = {q["query"]: q for q in ev["queries"]}
        n = len(byq[queries[0]]["frame_scores"]) if queries else 0
        dt = ev["model_duration"] / n if n else 0
        out[iid] = {}
        for e in sound:
            for q in THEIR._queries_for_label("sounding_action", e["label"]):          # the first query with detections = the pass's span source
                if byq.get(q, {}).get("detections"):
                    det = [dict(span=[round(d["start"], 3), round(d["end"], 3)], query=q,       # FLAM's own per-frame peak of the detection
                                peak_time=round(float(d["peak_time"]), 3), peak_score=round(float(d.get("peak_score", d.get("score", float("nan")))), 4))
                           for d in byq[q]["detections"]]
                    out[iid][e["label"]] = det
                    break
            else:
                out[iid][e["label"]] = []
        print(f"[peaks] {k + 1}/{len(recs)} {iid}", flush=True)
    json.dump(out, open(SYNC / "flam_peaks.json", "w"), indent=1)


if __name__ == "__main__":
    main()
