"""
Raw MediaPipe Holistic output formatter for a vanilla tool-augmented baseline.

This module intentionally does almost no interpretation. It runs MediaPipe
Holistic on sampled video frames and returns per-frame landmark coordinates.
Use this as a baseline for:

    MLLM + Raw Tool Output

Compared with the structured evidence pipeline, this raw baseline does NOT
create zone intervals, motion features, proximity intervals, or natural-language
observations. It simply serializes sampled pose/hand landmarks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from .body_primitives import _run_mediapipe, POSE, HAND
except ImportError:  # pragma: no cover
    from body_primitives import _run_mediapipe, POSE, HAND


def _r(x: Any, ndigits: int = 4) -> float:
    return round(float(x), ndigits)


def _landmark_dict(arr: Optional[np.ndarray], names: Dict[str, int], with_visibility: bool) -> Optional[dict]:
    if arr is None:
        return None
    out = {}
    for name, idx in names.items():
        if idx >= len(arr):
            continue
        point = arr[idx]
        item = {"x": _r(point[0]), "y": _r(point[1]), "z": _r(point[2])}
        if with_visibility and len(point) > 3:
            item["visibility"] = _r(point[3])
        out[name] = item
    return out


def _truncate_frames(frames: List[dict], max_frames: int) -> List[dict]:
    """Evenly sample frames if a cap is requested. max_frames <= 0 means no cap."""
    if max_frames is None or max_frames <= 0 or len(frames) <= max_frames:
        return frames
    idxs = np.linspace(0, len(frames) - 1, max_frames).round().astype(int)
    # np.linspace can duplicate indices for very small arrays; preserve order.
    seen = set()
    selected = []
    for i in idxs:
        ii = int(i)
        if ii in seen:
            continue
        seen.add(ii)
        selected.append(frames[ii])
    return selected


def extract_raw_mediapipe(
    video_path: str,
    sample_fps: float = 8.0,
    model_complexity: int = 1,
    max_frames: int = 40,
) -> dict:
    """Return raw sampled MediaPipe Holistic landmarks.

    Output is JSON-serializable and intentionally minimally processed:
      - sampled_frames[*].pose_landmarks: named 33-pose landmarks, x/y/z/visibility
      - sampled_frames[*].left_hand_landmarks: named 21-hand landmarks, x/y/z
      - sampled_frames[*].right_hand_landmarks: named 21-hand landmarks, x/y/z

    Laterality uses the same wrist-distance heuristic as body_primitives.py,
    because it is part of getting MediaPipe's raw output into a usable left/right
    coordinate frame rather than an action interpretation.
    """
    frames, meta = _run_mediapipe(video_path, sample_fps=sample_fps, model_complexity=model_complexity)
    raw_frames = []
    for i, frame in enumerate(frames):
        raw_frames.append(
            {
                "sample_index": i,
                "t": _r(frame["t"], 3),
                "pose_landmarks": _landmark_dict(frame.get("pose"), POSE, with_visibility=True),
                "left_hand_landmarks": _landmark_dict(frame.get("left_hand_landmarks"), HAND, with_visibility=False),
                "right_hand_landmarks": _landmark_dict(frame.get("right_hand_landmarks"), HAND, with_visibility=False),
            }
        )

    selected = _truncate_frames(raw_frames, max_frames=max_frames)
    return {
        "evidence_type": "raw_mediapipe_holistic_landmarks",
        "coordinate_system": {
            "x": "normalized image coordinate; left=0, right=1",
            "y": "normalized image coordinate; top=0, bottom=1",
            "z": "MediaPipe relative depth; scale is model-dependent",
            "visibility": "MediaPipe pose visibility when available; hand landmarks do not include visibility",
        },
        "video_meta": meta,
        "raw_frame_count_before_truncation": len(raw_frames),
        "raw_frame_count_included": len(selected),
        "max_frames": max_frames,
        "sampled_frames": selected,
        "note": (
            "This is a raw MediaPipe baseline. It does not compute zones, motion summaries, "
            "proximities, intervals, or action labels. The evaluator must interpret these raw "
            "landmarks together with the video/audio and original prompt."
        ),
    }


def _truncate_json_string(obj: dict, max_chars: int) -> str:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [TRUNCATED raw MediaPipe JSON due to max_chars limit]"


def format_raw_mediapipe_as_section(raw: dict, max_detail_chars: int = 50000) -> str:
    meta = raw.get("video_meta", {})
    sample_fps = meta.get("sample_fps", 0.0)
    duration = meta.get("duration_sec", 0.0)
    n_included = raw.get("raw_frame_count_included", 0)
    n_total = raw.get("raw_frame_count_before_truncation", 0)
    detail = _truncate_json_string(raw, max_chars=max_detail_chars)
    return (
        f"Raw MediaPipe Holistic output (vanilla tool baseline; sampled at "
        f"{sample_fps:.1f} fps over {duration:.2f}s; included {n_included}/{n_total} sampled frames):\n\n"
        f"Important note: This section is raw landmark output only. It contains no action labels, "
        f"no interval summaries, no proximity computations, and no natural-language motion interpretation. "
        f"Use it only as auxiliary low-level evidence for Visual Event Correctness and Temporal Constraint Satisfaction. "
        f"The video/audio and original prompt remain primary.\n\n"
        f"Raw JSON:\n{detail}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump raw sampled MediaPipe Holistic landmarks as JSON.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--sample-fps", type=float, default=8.0)
    parser.add_argument("--model-complexity", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--max-frames", type=int, default=40, help="Evenly cap included sampled frames. <=0 means no cap.")
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()

    raw = extract_raw_mediapipe(
        str(args.video),
        sample_fps=args.sample_fps,
        model_complexity=args.model_complexity,
        max_frames=args.max_frames,
    )
    text = json.dumps(raw, indent=2, ensure_ascii=False)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
