#!/usr/bin/env python3
"""
Raw MMPose COCO-WholeBody output formatter for T2AV visual evidence.

This mirrors raw_mediapipe.py, but uses MMPose whole-body inference.
It intentionally performs almost no action interpretation: it serializes
sampled per-frame keypoints so a downstream Gemini/VLM evaluator can inspect
body, feet, face/lip/mouth, and hands.

Recommended model family:
  - RTMW / RTMPose whole-body checkpoints from MMPose
  - COCO-WholeBody format: 133 keypoints per person

COCO-WholeBody 133 layout used here:
  - body:      17 keypoints  indices 0..16
  - foot:       6 keypoints  indices 17..22
  - face:      68 keypoints  indices 23..90
  - left hand: 21 keypoints  indices 91..111
  - right hand:21 keypoints  indices 112..132

Mouth/lip landmarks:
  COCO-WholeBody face landmarks follow the common 68-point face layout.
  The mouth/lip subset is face_48..face_67, i.e. wholebody indices 71..90.

Example:
  python Tool_Use/raw_mmpose.py video.mp4 \
    --pose2d rtmpose-x_8xb64-270e_coco-wholebody-384x288 \
    --det-model rtmdet-m \
    --sample-fps 8 \
    --output-json out.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from mmpose.apis import MMPoseInferencer
except Exception:  # pragma: no cover
    MMPoseInferencer = None


BODY_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]

FOOT_NAMES = [
    "left_big_toe", "left_small_toe", "left_heel",
    "right_big_toe", "right_small_toe", "right_heel",
]

HAND_NAMES = [
    "wrist", "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]

# Standard 68-point face landmark regions. Useful for speech/lip motion.
FACE_68_REGIONS = {
    "jaw": list(range(0, 17)),
    "right_eyebrow": list(range(17, 22)),
    "left_eyebrow": list(range(22, 27)),
    "nose_bridge": list(range(27, 31)),
    "nose_lower": list(range(31, 36)),
    "right_eye": list(range(36, 42)),
    "left_eye": list(range(42, 48)),
    "outer_mouth": list(range(48, 60)),
    "inner_mouth": list(range(60, 68)),
    "mouth_all": list(range(48, 68)),
}

# WholeBody absolute index ranges.
BODY_SLICE = slice(0, 17)
FOOT_SLICE = slice(17, 23)
FACE_SLICE = slice(23, 91)
LEFT_HAND_SLICE = slice(91, 112)
RIGHT_HAND_SLICE = slice(112, 133)
MOUTH_WHOLEBODY_INDICES = list(range(23 + 48, 23 + 68))  # 71..90


def _r(x: Any, ndigits: int = 4) -> float:
    try:
        val = float(x)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return round(val, ndigits)
    except Exception:
        return 0.0


def _bbox_area(pred: dict) -> float:
    bbox = pred.get("bbox") or pred.get("bbox_xyxy") or None
    if bbox is None:
        return 0.0
    arr = np.asarray(bbox, dtype=np.float32).reshape(-1)
    if arr.size < 4:
        return 0.0
    x1, y1, x2, y2 = arr[:4]
    return max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))


def _select_person(predictions: Any) -> Optional[dict]:
    """Select one person instance, preferring the largest bbox.

    MMPoseInferencer returns a generator whose per-image item usually contains
    {'predictions': [[instance, ...]], 'visualization': ...}. This helper is
    defensive against small version differences.
    """
    if predictions is None:
        return None
    if isinstance(predictions, dict):
        predictions = predictions.get("predictions", predictions)
    if isinstance(predictions, list) and len(predictions) == 1 and isinstance(predictions[0], list):
        predictions = predictions[0]
    if not isinstance(predictions, list) or not predictions:
        return None
    instances = [p for p in predictions if isinstance(p, dict)]
    if not instances:
        return None
    return max(instances, key=_bbox_area)


def _point_dict(xy: np.ndarray, score: Optional[float], width: int, height: int) -> dict:
    x_px, y_px = float(xy[0]), float(xy[1])
    return {
        "x": _r(x_px / max(width, 1)),
        "y": _r(y_px / max(height, 1)),
        "x_px": _r(x_px, 2),
        "y_px": _r(y_px, 2),
        "score": _r(score if score is not None else 0.0),
    }


def _named_points(
    keypoints: np.ndarray,
    scores: Optional[np.ndarray],
    names: List[str],
    offset: int,
    width: int,
    height: int,
    score_threshold: float,
) -> Optional[dict]:
    out: Dict[str, dict] = {}
    for i, name in enumerate(names):
        idx = offset + i
        if idx >= len(keypoints):
            continue
        score = float(scores[idx]) if scores is not None and idx < len(scores) else None
        if score is not None and score < score_threshold:
            continue
        out[name] = _point_dict(keypoints[idx], score, width, height)
    return out or None


def _face_points(
    keypoints: np.ndarray,
    scores: Optional[np.ndarray],
    width: int,
    height: int,
    score_threshold: float,
    include_all_face: bool,
) -> Tuple[Optional[dict], Optional[dict]]:
    face_all: Dict[str, dict] = {}
    mouth: Dict[str, dict] = {}
    for face_i in range(68):
        idx = 23 + face_i
        if idx >= len(keypoints):
            continue
        score = float(scores[idx]) if scores is not None and idx < len(scores) else None
        if score is not None and score < score_threshold:
            continue
        item = _point_dict(keypoints[idx], score, width, height)
        if include_all_face:
            face_all[f"face_{face_i}"] = item
        if face_i in FACE_68_REGIONS["mouth_all"]:
            mouth[f"face_{face_i}"] = item
    return (face_all or None), (mouth or None)


def _truncate_frames(frames: List[dict], max_frames: int) -> List[dict]:
    if max_frames is None or max_frames <= 0 or len(frames) <= max_frames:
        return frames
    idxs = np.linspace(0, len(frames) - 1, max_frames).round().astype(int)
    seen = set()
    selected = []
    for i in idxs:
        ii = int(i)
        if ii in seen:
            continue
        seen.add(ii)
        selected.append(frames[ii])
    return selected


def _make_inferencer(pose2d: str, det_model: Optional[str], det_weights: Optional[str], device: str):
    if MMPoseInferencer is None:
        raise ImportError("mmpose is not installed. Install mmpose/mmengine/mmcv and retry.")
    kwargs = {"pose2d": pose2d, "device": device}
    if det_model:
        kwargs["det_model"] = det_model
    if det_weights:
        kwargs["det_weights"] = det_weights
    return MMPoseInferencer(**kwargs)


def extract_raw_mmpose(
    video_path: str,
    sample_fps: float = 8.0,
    pose2d: str = "rtmpose-x_8xb64-270e_coco-wholebody-384x288",
    det_model: Optional[str] = "rtmdet-m",
    det_weights: Optional[str] = None,
    device: str = "cuda:0",
    max_frames: int = 40,
    score_threshold: float = 0.2,
    include_all_face: bool = False,
    save_overlay_dir: Optional[str] = None,
) -> dict:
    """Return raw sampled MMPose WholeBody landmarks.

    Output is JSON-serializable and minimally processed:
      - sampled_frames[*].body_keypoints: named 17 COCO body points
      - sampled_frames[*].foot_keypoints: named 6 foot points
      - sampled_frames[*].mouth_keypoints: face_48..face_67 for lip/mouth motion
      - sampled_frames[*].face_keypoints: optional full face_0..face_67
      - sampled_frames[*].left_hand_keypoints: named 21 hand points
      - sampled_frames[*].right_hand_keypoints: named 21 hand points
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(video_path)

    native_fps = float(cap.get(cv2.CAP_PROP_FPS) or sample_fps or 8.0)
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = float(n_total / native_fps) if native_fps > 0 else 0.0

    if sample_fps <= 0:
        sample_fps = native_fps if native_fps > 0 else 8.0
    step = max(1, int(round(native_fps / sample_fps)))
    sampled_fps = native_fps / step if step > 0 else native_fps

    overlay_path = Path(save_overlay_dir) if save_overlay_dir else None
    if overlay_path:
        overlay_path.mkdir(parents=True, exist_ok=True)

    inferencer = _make_inferencer(pose2d=pose2d, det_model=det_model, det_weights=det_weights, device=device)

    raw_frames: List[dict] = []
    detected = 0
    idx = 0
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            if idx % step != 0:
                idx += 1
                continue

            t = idx / native_fps if native_fps > 0 else len(raw_frames) / sample_fps

            # MMPoseInferencer accepts ndarray frames. return_vis helps quick manual checks.
            result_iter = inferencer(frame_bgr, return_vis=bool(overlay_path), show=False)
            result = next(result_iter)
            pred = _select_person(result.get("predictions") if isinstance(result, dict) else result)

            frame_item = {"sample_index": len(raw_frames), "source_frame_index": idx, "t": _r(t, 3)}

            if pred is not None:
                keypoints = np.asarray(pred.get("keypoints", []), dtype=np.float32)
                scores_raw = pred.get("keypoint_scores", pred.get("keypoint_score", None))
                scores = np.asarray(scores_raw, dtype=np.float32).reshape(-1) if scores_raw is not None else None

                if keypoints.ndim == 2 and keypoints.shape[0] >= 133:
                    detected += 1
                    frame_item.update(
                        {
                            "bbox": pred.get("bbox") or pred.get("bbox_xyxy"),
                            "bbox_score": pred.get("bbox_score", pred.get("score")),
                            "body_keypoints": _named_points(keypoints, scores, BODY_NAMES, 0, width, height, score_threshold),
                            "foot_keypoints": _named_points(keypoints, scores, FOOT_NAMES, 17, width, height, score_threshold),
                            "left_hand_keypoints": _named_points(keypoints, scores, HAND_NAMES, 91, width, height, score_threshold),
                            "right_hand_keypoints": _named_points(keypoints, scores, HAND_NAMES, 112, width, height, score_threshold),
                        }
                    )
                    face_all, mouth = _face_points(keypoints, scores, width, height, score_threshold, include_all_face)
                    if include_all_face:
                        frame_item["face_keypoints"] = face_all
                    frame_item["mouth_keypoints"] = mouth
                else:
                    frame_item["mmpose_warning"] = f"No 133-keypoint wholebody prediction. keypoints_shape={list(keypoints.shape)}"
            else:
                frame_item["mmpose_warning"] = "No person prediction selected."

            if overlay_path and isinstance(result, dict) and result.get("visualization"):
                vis = result["visualization"][0]
                out_file = overlay_path / f"frame_{len(raw_frames):04d}_t{t:.3f}.jpg"
                cv2.imwrite(str(out_file), vis)

            raw_frames.append(frame_item)
            idx += 1
    finally:
        cap.release()

    selected = _truncate_frames(raw_frames, max_frames=max_frames)
    return {
        "evidence_type": "raw_mmpose_coco_wholebody_133_keypoints",
        "keypoint_layout": {
            "name": "COCO-WholeBody-133",
            "total_keypoints_per_person": 133,
            "body": "17 keypoints, indices 0..16",
            "foot": "6 keypoints, indices 17..22",
            "face": "68 keypoints, indices 23..90",
            "mouth_lip_subset": "face_48..face_67, wholebody indices 71..90",
            "left_hand": "21 keypoints, indices 91..111",
            "right_hand": "21 keypoints, indices 112..132",
        },
        "coordinate_system": {
            "x": "normalized image coordinate; left=0, right=1; x_px is absolute pixel x",
            "y": "normalized image coordinate; top=0, bottom=1; y_px is absolute pixel y",
            "score": "MMPose keypoint confidence score; low-score points are omitted by score_threshold",
        },
        "video_meta": {
            "native_fps": _r(native_fps, 3),
            "sample_fps": _r(sampled_fps, 3),
            "requested_sample_fps": _r(sample_fps, 3),
            "duration_sec": _r(duration, 3),
            "n_total_frames": n_total,
            "n_sampled_frames": len(raw_frames),
            "width": width,
            "height": height,
            "pose2d": pose2d,
            "det_model": det_model,
            "device": device,
            "score_threshold": score_threshold,
            "person_detected_frames": detected,
        },
        "raw_frame_count_before_truncation": len(raw_frames),
        "raw_frame_count_included": len(selected),
        "max_frames": max_frames,
        "sampled_frames": selected,
        "note": (
            "This is raw MMPose WholeBody output. It contains no action labels, no interval summaries, "
            "no proximity computations, and no correctness judgment. Use it as auxiliary visual evidence. "
            "Speech visual evidence should use mouth_keypoints / face keypoints together with direct video inspection."
        ),
    }


def _truncate_json_string(obj: dict, max_chars: int) -> str:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [TRUNCATED raw MMPose JSON due to max_chars limit]"


def format_raw_mmpose_as_section(raw: dict, max_detail_chars: int = 50000) -> str:
    meta = raw.get("video_meta", {}) or {}
    sample_fps = float(meta.get("sample_fps", 0.0) or 0.0)
    duration = float(meta.get("duration_sec", 0.0) or 0.0)
    n_included = raw.get("raw_frame_count_included", 0)
    n_total = raw.get("raw_frame_count_before_truncation", 0)
    detail = _truncate_json_string(raw, max_chars=max_detail_chars)
    return (
        f"Raw MMPose COCO-WholeBody output (vanilla tool baseline; sampled at "
        f"{sample_fps:.1f} fps over {duration:.2f}s; included {n_included}/{n_total} sampled frames):\n\n"
        f"Important note: This section is raw whole-body landmark output only. It contains no action labels, "
        f"no interval summaries, no proximity computations, and no natural-language motion interpretation. "
        f"Use it only as auxiliary low-level evidence for Visual Event Correctness and Temporal Constraint Satisfaction. "
        f"For speech events, inspect mouth_keypoints / face landmarks for visible lip/mouth motion. "
        f"The video/audio and original prompt remain primary.\n\n"
        f"Raw JSON:\n{detail}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump raw sampled MMPose COCO-WholeBody landmarks as JSON.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--sample-fps", type=float, default=8.0)
    parser.add_argument("--pose2d", type=str, default="rtmpose-x_8xb64-270e_coco-wholebody-384x288")
    parser.add_argument("--det-model", type=str, default="rtmdet-m")
    parser.add_argument("--det-weights", type=str, default=None)
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--max-frames", type=int, default=40, help="Evenly cap included sampled frames. <=0 means no cap.")
    parser.add_argument("--score-threshold", type=float, default=0.2)
    parser.add_argument("--include-all-face", action="store_true", help="Include all 68 face landmarks, not only mouth_keypoints.")
    parser.add_argument("--save-overlay-dir", type=Path, default=None, help="Optional directory for per-sampled-frame MMPose visualizations.")
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--print-section", action="store_true", help="Print LLM-ready text section instead of raw JSON.")
    parser.add_argument("--max-detail-chars", type=int, default=50000)
    args = parser.parse_args()

    raw = extract_raw_mmpose(
        str(args.video),
        sample_fps=args.sample_fps,
        pose2d=args.pose2d,
        det_model=args.det_model,
        det_weights=args.det_weights,
        device=args.device,
        max_frames=args.max_frames,
        score_threshold=args.score_threshold,
        include_all_face=args.include_all_face,
        save_overlay_dir=str(args.save_overlay_dir) if args.save_overlay_dir else None,
    )

    if args.print_section:
        text = format_raw_mmpose_as_section(raw, max_detail_chars=args.max_detail_chars)
    else:
        text = json.dumps(raw, indent=2, ensure_ascii=False)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
