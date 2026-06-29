"""
Open-vocabulary body-pose evidence extraction with MediaPipe Holistic.

This module deliberately avoids assigning action labels such as "wave",
"clap", "slap", "thumbs-up", or "nod".  It only reports low-level,
prompt-independent evidence that a prompt-conditioned evaluator can interpret:

  1. body-part tracks and vertical zone intervals
  2. body-part motion features, velocity peaks, oscillation rates, active spans
  3. spatial proximity intervals between wrists/feet and body targets
  4. generic hand landmark states: finger extended/curled, thumb direction,
     palm facing direction
  5. posture evidence: torso lean and arms-crossed intervals

Entry point:
    primitives = extract_primitives("video.mp4", sample_fps=8.0)

The returned object is JSON-serializable and suitable for deterministic text
formatting before being injected into an LLM evaluator prompt.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np


# ---------------------------------------------------------------------------
# MediaPipe landmark index maps
# ---------------------------------------------------------------------------
POSE: Dict[str, int] = {
    "nose": 0,
    "left_eye_inner": 1,
    "left_eye": 2,
    "left_eye_outer": 3,
    "right_eye_inner": 4,
    "right_eye": 5,
    "right_eye_outer": 6,
    "left_ear": 7,
    "right_ear": 8,
    "mouth_left": 9,
    "mouth_right": 10,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_pinky": 17,
    "right_pinky": 18,
    "left_index": 19,
    "right_index": 20,
    "left_thumb": 21,
    "right_thumb": 22,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}

HAND: Dict[str, int] = {
    "wrist": 0,
    "thumb_cmc": 1,
    "thumb_mcp": 2,
    "thumb_ip": 3,
    "thumb_tip": 4,
    "index_mcp": 5,
    "index_pip": 6,
    "index_dip": 7,
    "index_tip": 8,
    "middle_mcp": 9,
    "middle_pip": 10,
    "middle_dip": 11,
    "middle_tip": 12,
    "ring_mcp": 13,
    "ring_pip": 14,
    "ring_dip": 15,
    "ring_tip": 16,
    "pinky_mcp": 17,
    "pinky_pip": 18,
    "pinky_dip": 19,
    "pinky_tip": 20,
}

TRACKED_PARTS: Dict[str, int] = {
    "nose": POSE["nose"],
    "left_shoulder": POSE["left_shoulder"],
    "right_shoulder": POSE["right_shoulder"],
    "left_elbow": POSE["left_elbow"],
    "right_elbow": POSE["right_elbow"],
    "left_wrist": POSE["left_wrist"],
    "right_wrist": POSE["right_wrist"],
    "left_hip": POSE["left_hip"],
    "right_hip": POSE["right_hip"],
    "left_knee": POSE["left_knee"],
    "right_knee": POSE["right_knee"],
    "left_ankle": POSE["left_ankle"],
    "right_ankle": POSE["right_ankle"],
    "left_foot_index": POSE["left_foot_index"],
    "right_foot_index": POSE["right_foot_index"],
}

# Parts for which trajectory samples are most useful in the LLM prompt.
DEFAULT_TRAJECTORY_PARTS = {
    "nose",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_foot_index",
    "right_foot_index",
}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def _r(x: Any, ndigits: int = 4) -> float:
    return round(float(x), ndigits)


def _dist(a: Iterable[float], b: Iterable[float]) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=np.float32)[:2] - np.asarray(b, dtype=np.float32)[:2]))


def _cosine(v1: np.ndarray, v2: np.ndarray) -> float:
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


def _to_arr(lm_proto, with_vis: bool = False) -> np.ndarray:
    if with_vis:
        return np.array(
            [[p.x, p.y, p.z, p.visibility] for p in lm_proto.landmark],
            dtype=np.float32,
        )
    return np.array([[p.x, p.y, p.z] for p in lm_proto.landmark], dtype=np.float32)


def _finite_or_none(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    if np.isnan(x) or np.isinf(x):
        return None
    return float(x)


# ---------------------------------------------------------------------------
# MediaPipe runner
# ---------------------------------------------------------------------------
def _verify_laterality(
    pose: Optional[np.ndarray],
    left_hand: Optional[np.ndarray],
    right_hand: Optional[np.ndarray],
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Reduce common MediaPipe hand left/right swaps.

    MediaPipe occasionally assigns a detected hand to the wrong side when hands
    cross. We compare each detected hand wrist to the pose-estimated left/right
    wrists. If the left-hand landmarks are closer to the pose right wrist, swap.
    This is a heuristic, not a guarantee.
    """
    if pose is None or left_hand is None:
        return left_hand, right_hand

    pose_left_wrist = pose[POSE["left_wrist"], :2]
    pose_right_wrist = pose[POSE["right_wrist"], :2]
    left_hand_wrist = left_hand[HAND["wrist"], :2]

    left_hand_closer_to_right = _dist(left_hand_wrist, pose_right_wrist) < _dist(
        left_hand_wrist, pose_left_wrist
    )
    if left_hand_closer_to_right:
        return right_hand, left_hand
    return left_hand, right_hand


def _run_mediapipe(
    video_path: str,
    sample_fps: float,
    model_complexity: int = 1,
) -> Tuple[List[dict], dict]:
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

    holistic = mp.solutions.holistic.Holistic(
        static_image_mode=False,
        model_complexity=int(model_complexity),
        smooth_landmarks=True,
        refine_face_landmarks=True,
    )

    frames: List[dict] = []
    pose_detected = 0
    left_hand_detected = 0
    right_hand_detected = 0
    face_detected = 0

    try:
        idx = 0
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            if idx % step != 0:
                idx += 1
                continue

            t = idx / native_fps if native_fps > 0 else len(frames) / sample_fps
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            res = holistic.process(rgb)

            pose = _to_arr(res.pose_landmarks, with_vis=True) if res.pose_landmarks else None
            left_hand = _to_arr(res.left_hand_landmarks) if res.left_hand_landmarks else None
            right_hand = _to_arr(res.right_hand_landmarks) if res.right_hand_landmarks else None
            face = _to_arr(res.face_landmarks) if res.face_landmarks else None
            left_hand, right_hand = _verify_laterality(pose, left_hand, right_hand)

            if pose is not None:
                pose_detected += 1
            if left_hand is not None:
                left_hand_detected += 1
            if right_hand is not None:
                right_hand_detected += 1
            if face is not None:
                face_detected += 1

            frames.append(
                {
                    "t": float(t),
                    "pose": pose,
                    "left_hand_landmarks": left_hand,
                    "right_hand_landmarks": right_hand,
                    "face_landmarks": face,
                }
            )
            idx += 1
    finally:
        holistic.close()
        cap.release()

    n_sampled = len(frames)
    meta = {
        "native_fps": _r(native_fps, 3),
        "sample_fps": _r(sampled_fps, 3),
        "requested_sample_fps": _r(sample_fps, 3),
        "duration_sec": _r(duration, 3),
        "n_total_frames": n_total,
        "n_sampled_frames": n_sampled,
        "width": width,
        "height": height,
        "mediapipe_model_complexity": int(model_complexity),
        "pose_detected_frames": pose_detected,
        "left_hand_landmarks_detected_frames": left_hand_detected,
        "right_hand_landmarks_detected_frames": right_hand_detected,
        "face_landmarks_detected_frames": face_detected,
        "mediapipe_face_landmark_count": 478,
    }
    return frames, meta


# ---------------------------------------------------------------------------
# Per-frame evidence
# ---------------------------------------------------------------------------
def _reference_from_pose(pose: np.ndarray) -> dict:
    left_sh = pose[POSE["left_shoulder"], :2]
    right_sh = pose[POSE["right_shoulder"], :2]
    left_hip = pose[POSE["left_hip"], :2]
    right_hip = pose[POSE["right_hip"], :2]

    shoulder_y = float((left_sh[1] + right_sh[1]) / 2.0)
    hip_y = float((left_hip[1] + right_hip[1]) / 2.0)
    nose_y = float(pose[POSE["nose"], 1])
    shoulder_width = max(float(abs(left_sh[0] - right_sh[0])), 1e-3)
    torso_height = max(float(abs(hip_y - shoulder_y)), 1e-3)
    head_top = nose_y - 0.5 * max(shoulder_y - nose_y, 1e-3)

    return {
        "nose_y": nose_y,
        "shoulder_y": shoulder_y,
        "hip_y": hip_y,
        "chest_y": (shoulder_y + hip_y) / 2.0,
        "head_top_y": head_top,
        "shoulder_width": shoulder_width,
        "torso_height": torso_height,
    }


def _classify_vertical_zone(y: float, ref: dict) -> str:
    # MediaPipe image y increases downward.
    if y < ref["head_top_y"]:
        return "above_head"
    if y < ref["shoulder_y"]:
        return "above_shoulder"
    if y < ref["chest_y"]:
        return "chest"
    if y < ref["hip_y"]:
        return "hip"
    return "below_hip"


def _direction_label_2d(v: np.ndarray) -> str:
    x, y = float(v[0]), float(v[1])
    if abs(y) > abs(x):
        return "up" if y < 0 else "down"
    return "right" if x > 0 else "left"


def _palm_direction_label(normal_3d: np.ndarray) -> str:
    nx, ny, nz = float(normal_3d[0]), float(normal_3d[1]), float(normal_3d[2])
    abs_vals = {"x": abs(nx), "y": abs(ny), "z": abs(nz)}
    axis = max(abs_vals, key=abs_vals.get)
    if abs_vals[axis] < 1e-6:
        return "unknown"
    if axis == "z":
        # MediaPipe z is relative; sign is still useful only as a heuristic.
        return "toward_camera" if nz > 0 else "away_from_camera"
    if axis == "y":
        return "down" if ny > 0 else "up"
    return "right" if nx > 0 else "left"


def _hand_landmark_state(hand: Optional[np.ndarray]) -> Optional[dict]:
    """Generic hand evidence: finger flexion + thumb/palm directions.

    This does not label gestures. It reports primitive states only.
    """
    if hand is None:
        return None

    fingers: Dict[str, str] = {}
    for name, mcp_i, pip_i, tip_i in [
        ("index", HAND["index_mcp"], HAND["index_pip"], HAND["index_tip"]),
        ("middle", HAND["middle_mcp"], HAND["middle_pip"], HAND["middle_tip"]),
        ("ring", HAND["ring_mcp"], HAND["ring_pip"], HAND["ring_tip"]),
        ("pinky", HAND["pinky_mcp"], HAND["pinky_pip"], HAND["pinky_tip"]),
    ]:
        v1 = hand[pip_i, :2] - hand[mcp_i, :2]
        v2 = hand[tip_i, :2] - hand[pip_i, :2]
        fingers[name] = "extended" if _cosine(v1, v2) > 0.6 else "curled"

    thumb_v1 = hand[HAND["thumb_ip"], :2] - hand[HAND["thumb_mcp"], :2]
    thumb_v2 = hand[HAND["thumb_tip"], :2] - hand[HAND["thumb_ip"], :2]
    fingers["thumb"] = "extended" if _cosine(thumb_v1, thumb_v2) > 0.5 else "curled"

    thumb_vec = hand[HAND["thumb_tip"], :2] - hand[HAND["thumb_cmc"], :2]
    thumb_direction = _direction_label_2d(thumb_vec) if fingers["thumb"] == "extended" else None

    palm_a = hand[HAND["index_mcp"]] - hand[HAND["wrist"]]
    palm_b = hand[HAND["pinky_mcp"]] - hand[HAND["wrist"]]
    palm_normal = np.cross(palm_a, palm_b)

    return {
        "fingers": fingers,
        "thumb_direction": thumb_direction,
        "palm_facing": _palm_direction_label(palm_normal),
    }


def _body_part_positions(pose: np.ndarray) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for name, idx in TRACKED_PARTS.items():
        x, y, z, vis = pose[idx]
        out[name] = {
            "x": _r(x),
            "y": _r(y),
            "z": _r(z),
            "visibility": _r(vis),
        }
    return out


def _pt(d: dict) -> np.ndarray:
    return np.array([d["x"], d["y"]], dtype=np.float32)


def _midpoint(a: dict, b: dict) -> dict:
    return {
        "x": _r((a["x"] + b["x"]) / 2.0),
        "y": _r((a["y"] + b["y"]) / 2.0),
        "z": _r((a.get("z", 0.0) + b.get("z", 0.0)) / 2.0),
        "visibility": _r(min(a.get("visibility", 1.0), b.get("visibility", 1.0))),
    }


def _virtual_body_targets(body_parts: Dict[str, dict]) -> Dict[str, dict]:
    """Create named body targets for generic proximity evidence."""
    targets = dict(body_parts)
    targets["head"] = body_parts["nose"]
    targets["left_chest"] = _midpoint(body_parts["left_shoulder"], body_parts["left_hip"])
    targets["right_chest"] = _midpoint(body_parts["right_shoulder"], body_parts["right_hip"])
    targets["center_chest"] = _midpoint(targets["left_chest"], targets["right_chest"])
    targets["left_thigh"] = _midpoint(body_parts["left_hip"], body_parts["left_knee"])
    targets["right_thigh"] = _midpoint(body_parts["right_hip"], body_parts["right_knee"])
    targets["left_upper_arm"] = _midpoint(body_parts["left_shoulder"], body_parts["left_elbow"])
    targets["right_upper_arm"] = _midpoint(body_parts["right_shoulder"], body_parts["right_elbow"])
    targets["left_forearm"] = _midpoint(body_parts["left_elbow"], body_parts["left_wrist"])
    targets["right_forearm"] = _midpoint(body_parts["right_elbow"], body_parts["right_wrist"])
    return targets


def _default_proximity_pairs() -> List[Tuple[str, str]]:
    """Pairs that cover common but open-ended human actions without naming them."""
    pairs = []
    hand_sources = ["left_wrist", "right_wrist"]
    body_targets = [
        "head",
        "left_shoulder",
        "right_shoulder",
        "left_chest",
        "right_chest",
        "center_chest",
        "left_upper_arm",
        "right_upper_arm",
        "left_forearm",
        "right_forearm",
        "left_hip",
        "right_hip",
        "left_thigh",
        "right_thigh",
        "left_knee",
        "right_knee",
    ]
    for src in hand_sources:
        for tgt in body_targets:
            # Skip the trivial same-side wrist-to-forearm pair only if desired; it
            # can still be useful for crossed-arm/touching evidence, so keep it.
            pairs.append((src, tgt))

    pairs.extend(
        [
            ("left_wrist", "right_wrist"),
            ("left_wrist", "right_elbow"),
            ("right_wrist", "left_elbow"),
            ("left_ankle", "right_ankle"),
            ("left_foot_index", "right_foot_index"),
            ("left_wrist", "left_ankle"),
            ("right_wrist", "right_ankle"),
            ("left_wrist", "right_ankle"),
            ("right_wrist", "left_ankle"),
        ]
    )
    # Deduplicate while preserving order.
    out = []
    seen = set()
    for pair in pairs:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


PROXIMITY_PAIRS = _default_proximity_pairs()


def _proximity_distances(
    body_parts: Dict[str, dict],
    ref: dict,
    visibility_threshold: float,
) -> Dict[str, Optional[float]]:
    targets = _virtual_body_targets(body_parts)
    distances: Dict[str, Optional[float]] = {}

    for src, tgt in PROXIMITY_PAIRS:
        if src not in targets or tgt not in targets:
            continue
        src_obj = targets[src]
        tgt_obj = targets[tgt]
        if src_obj.get("visibility", 1.0) < visibility_threshold or tgt_obj.get("visibility", 1.0) < visibility_threshold:
            distances[f"{src}__{tgt}"] = None
            continue
        # Normalize by shoulder width so values are comparable across scale.
        raw = _dist(_pt(src_obj), _pt(tgt_obj))
        distances[f"{src}__{tgt}"] = float(raw / max(ref["shoulder_width"], 1e-3))
    return distances


def _posture_state(body_parts: Dict[str, dict], ref: dict) -> dict:
    shoulder_y = ref["shoulder_y"]
    hip_y = ref["hip_y"]
    torso_h = hip_y - shoulder_y

    if torso_h < 0.15:
        lean = "leaning_forward_or_compressed"
    elif torso_h > 0.35:
        lean = "upright_or_extended"
    else:
        lean = "neutral"

    left_wrist = body_parts["left_wrist"]
    right_wrist = body_parts["right_wrist"]
    left_shoulder = body_parts["left_shoulder"]
    right_shoulder = body_parts["right_shoulder"]

    arms_crossed = bool(
        left_wrist["x"] > right_shoulder["x"]
        and right_wrist["x"] < left_shoulder["x"]
        and left_wrist["y"] > shoulder_y
        and right_wrist["y"] > shoulder_y
    )

    return {"torso_vertical_state": lean, "arms_crossed": arms_crossed}


def _frame_state(
    frame: dict,
    visibility_threshold: float,
) -> Optional[dict]:
    pose = frame["pose"]
    if pose is None:
        return None

    ref = _reference_from_pose(pose)
    body_parts = _body_part_positions(pose)
    zones = {
        part: _classify_vertical_zone(info["y"], ref)
        for part, info in body_parts.items()
        if info.get("visibility", 1.0) >= visibility_threshold
    }

    hand_landmark_states = {
        "left": _hand_landmark_state(frame.get("left_hand_landmarks")),
        "right": _hand_landmark_state(frame.get("right_hand_landmarks")),
    }

    return {
        "t": float(frame["t"]),
        "ref": {k: _r(v) for k, v in ref.items()},
        "body_parts": body_parts,
        "zones": zones,
        "hand_landmark_states": hand_landmark_states,
        "proximity_distances": _proximity_distances(body_parts, ref, visibility_threshold),
        "posture": _posture_state(body_parts, ref),
    }


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
def _runs_to_intervals(
    times: List[float],
    values: List[Optional[str]],
    min_duration: float = 0.0,
) -> Dict[str, List[List[float]]]:
    out: Dict[str, List[List[float]]] = {}
    if not times:
        return out

    cur_v = values[0]
    cur_start = times[0]
    last_t = times[0]

    for t, v in zip(times[1:], values[1:]):
        if v != cur_v:
            if cur_v is not None and (last_t - cur_start) >= min_duration:
                out.setdefault(str(cur_v), []).append([round(cur_start, 2), round(last_t, 2)])
            cur_v = v
            cur_start = t
        last_t = t

    if cur_v is not None and (last_t - cur_start) >= min_duration:
        out.setdefault(str(cur_v), []).append([round(cur_start, 2), round(last_t, 2)])
    return out


def _flag_to_intervals(
    times: List[float],
    flags: List[Optional[bool]],
    min_duration: float = 0.0,
) -> List[List[float]]:
    out: List[List[float]] = []
    if not times:
        return out

    in_run = False
    start = None
    last_t = times[0]

    for t, f in zip(times, flags):
        if f is True and not in_run:
            in_run = True
            start = t
        elif f is not True and in_run:
            if start is not None and (last_t - start) >= min_duration:
                out.append([round(start, 2), round(last_t, 2)])
            in_run = False
        last_t = t

    if in_run and start is not None and (last_t - start) >= min_duration:
        out.append([round(start, 2), round(last_t, 2)])
    return out


def _downsample_indices(n: int, max_items: int) -> List[int]:
    if n <= 0:
        return []
    if n <= max_items:
        return list(range(n))
    return sorted(set(int(i) for i in np.linspace(0, n - 1, max_items).round()))


def _osc_freq_hz(series: np.ndarray, times: np.ndarray) -> Optional[float]:
    """Crude oscillation estimate via zero crossings after detrending."""
    if len(series) < 4 or len(times) < 4 or np.isnan(series).any():
        return None
    duration = float(times[-1] - times[0])
    if duration < 0.5:
        return None

    s = series.astype(np.float32) - float(np.mean(series))
    std = float(np.std(s))
    if std < 1e-3:
        return 0.0
    s = np.where(np.abs(s) < 0.2 * std, 0.0, s)
    signs = np.sign(s)
    zc = int(np.sum(np.diff(signs) != 0))
    return round(float(zc / 2.0 / duration), 2)


def _component_velocity_peaks(
    series: np.ndarray,
    times: np.ndarray,
    rel_threshold: float = 2.0,
    abs_threshold: float = 0.03,
) -> List[float]:
    if len(series) < 4 or np.isnan(series).any():
        return []
    v = np.abs(np.diff(series))
    if len(v) < 3:
        return []
    base = float(np.median(v))
    thresh = max(rel_threshold * max(base, 1e-4), abs_threshold)
    peaks: List[float] = []
    for i in range(1, len(v) - 1):
        if v[i] > thresh and v[i] >= v[i - 1] and v[i] >= v[i + 1]:
            peaks.append(round(float(times[i + 1]), 2))
    return sorted(set(peaks))


def _speed_series(xs: np.ndarray, ys: np.ndarray, times: np.ndarray) -> np.ndarray:
    if len(xs) < 2:
        return np.array([], dtype=np.float32)
    dt = np.diff(times)
    dt = np.where(dt < 1e-6, 1e-6, dt)
    dx = np.diff(xs)
    dy = np.diff(ys)
    return np.sqrt(dx * dx + dy * dy) / dt


def _active_intervals_from_speed(
    times: List[float],
    speed: np.ndarray,
    rel_threshold: float = 1.8,
    abs_threshold: float = 0.10,
) -> List[List[float]]:
    if len(times) < 2 or len(speed) == 0:
        return []
    base = float(np.median(speed)) if len(speed) else 0.0
    threshold = max(rel_threshold * max(base, 1e-4), abs_threshold)
    # speed[i] describes motion from times[i] to times[i+1]; mark endpoint frame.
    flags = [False] + [float(v) > threshold for v in speed]
    return _flag_to_intervals(times, flags)


def _dominant_axis(xs: np.ndarray, ys: np.ndarray) -> str:
    if len(xs) < 2:
        return "unknown"
    x_path = float(np.sum(np.abs(np.diff(xs))))
    y_path = float(np.sum(np.abs(np.diff(ys))))
    if max(x_path, y_path) < 1e-4:
        return "stationary"
    if x_path > 1.25 * y_path:
        return "x"
    if y_path > 1.25 * x_path:
        return "y"
    return "mixed"


def _series_for_part(valid: List[dict], part: str, coord: str) -> np.ndarray:
    return np.array([s["body_parts"][part][coord] for s in valid], dtype=np.float32)


def _build_track_quality(states: List[Optional[dict]], meta: dict) -> dict:
    n = int(meta.get("n_sampled_frames", len(states)) or len(states))
    if n <= 0:
        return {
            "pose_detected_ratio": 0.0,
            "left_hand_landmarks_detected_ratio": 0.0,
            "right_hand_landmarks_detected_ratio": 0.0,
        }

    return {
        "pose_detected_ratio": _r(meta.get("pose_detected_frames", 0) / n, 3),
        "left_hand_landmarks_detected_ratio": _r(meta.get("left_hand_landmarks_detected_frames", 0) / n, 3),
        "right_hand_landmarks_detected_ratio": _r(meta.get("right_hand_landmarks_detected_frames", 0) / n, 3),
        "valid_pose_frames": int(meta.get("pose_detected_frames", 0)),
        "sampled_frames": n,
    }


def _build_body_parts(
    valid: List[dict],
    max_trajectory_samples: int,
    trajectory_parts: Optional[set] = None,
) -> dict:
    trajectory_parts = trajectory_parts or DEFAULT_TRAJECTORY_PARTS
    times = [s["t"] for s in valid]
    idxs = _downsample_indices(len(valid), max_trajectory_samples)
    out: Dict[str, dict] = {}

    for part in TRACKED_PARTS:
        zones = _runs_to_intervals(times, [s["zones"].get(part) for s in valid])
        vis_values = [s["body_parts"][part].get("visibility", 0.0) for s in valid]
        info: Dict[str, Any] = {
            "visible_ratio": _r(sum(v >= 0.5 for v in vis_values) / max(len(vis_values), 1), 3),
            "zone_intervals": zones,
        }
        if part in trajectory_parts:
            samples = []
            for i in idxs:
                bp = valid[i]["body_parts"][part]
                samples.append(
                    {
                        "t": round(float(valid[i]["t"]), 2),
                        "x": bp["x"],
                        "y": bp["y"],
                        "z": bp["z"],
                        "visibility": bp["visibility"],
                    }
                )
            info["trajectory_samples"] = samples
        out[part] = info
    return out


def _build_motion(valid: List[dict]) -> dict:
    times = [s["t"] for s in valid]
    times_arr = np.array(times, dtype=np.float32)
    out: Dict[str, dict] = {}

    for part in TRACKED_PARTS:
        xs = _series_for_part(valid, part, "x")
        ys = _series_for_part(valid, part, "y")
        speed = _speed_series(xs, ys, times_arr)
        step_path = np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2) if len(xs) > 1 else np.array([])

        out[part] = {
            "active_intervals": _active_intervals_from_speed(times, speed),
            "x_velocity_peaks_sec": _component_velocity_peaks(xs, times_arr),
            "y_velocity_peaks_sec": _component_velocity_peaks(ys, times_arr),
            "x_osc_hz": _finite_or_none(_osc_freq_hz(xs, times_arr)),
            "y_osc_hz": _finite_or_none(_osc_freq_hz(ys, times_arr)),
            "total_path_length_norm": _r(float(np.sum(step_path)) if len(step_path) else 0.0),
            "net_displacement": {
                "dx": _r(float(xs[-1] - xs[0]) if len(xs) else 0.0),
                "dy": _r(float(ys[-1] - ys[0]) if len(ys) else 0.0),
            },
            "dominant_motion_axis": _dominant_axis(xs, ys),
        }
    return out


def _nested_get(d: Optional[dict], path: List[str]) -> Optional[Any]:
    obj: Any = d
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _build_hand_landmark_state_intervals(valid: List[dict]) -> dict:
    times = [s["t"] for s in valid]
    out: Dict[str, dict] = {}

    for side in ("left", "right"):
        side_out: Dict[str, dict] = {
            "finger_state_intervals": {},
            "thumb_direction_intervals": {},
            "palm_facing_intervals": {},
            "landmarks_detected_intervals": [],
        }

        detected_flags = [s["hand_landmark_states"].get(side) is not None for s in valid]
        side_out["landmarks_detected_intervals"] = _flag_to_intervals(times, detected_flags)

        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            for state_name in ("extended", "curled"):
                flags = []
                for s in valid:
                    hand_state = s["hand_landmark_states"].get(side)
                    value = _nested_get(hand_state, ["fingers", finger])
                    flags.append(value == state_name if value is not None else None)
                intervals = _flag_to_intervals(times, flags)
                if intervals:
                    side_out["finger_state_intervals"][f"{finger}_{state_name}"] = intervals

        for direction in ("up", "down", "left", "right"):
            flags = []
            for s in valid:
                hand_state = s["hand_landmark_states"].get(side)
                value = _nested_get(hand_state, ["thumb_direction"])
                flags.append(value == direction if value is not None else None)
            intervals = _flag_to_intervals(times, flags)
            if intervals:
                side_out["thumb_direction_intervals"][direction] = intervals

        for facing in ("toward_camera", "away_from_camera", "up", "down", "left", "right", "unknown"):
            flags = []
            for s in valid:
                hand_state = s["hand_landmark_states"].get(side)
                value = _nested_get(hand_state, ["palm_facing"])
                flags.append(value == facing if value is not None else None)
            intervals = _flag_to_intervals(times, flags)
            if intervals:
                side_out["palm_facing_intervals"][facing] = intervals

        out[side] = side_out
    return out


def _build_proximities(
    valid: List[dict],
    near_threshold_norm: float,
) -> dict:
    times = [s["t"] for s in valid]
    out: Dict[str, dict] = {}
    all_keys = sorted({k for s in valid for k in s["proximity_distances"].keys()})

    for key in all_keys:
        values = [s["proximity_distances"].get(key) for s in valid]
        finite_values = [(times[i], v) for i, v in enumerate(values) if v is not None]
        if not finite_values:
            continue

        min_t, min_d = min(finite_values, key=lambda tv: tv[1])
        flags = [v is not None and v <= near_threshold_norm for v in values]
        intervals = _flag_to_intervals(times, flags)

        # Keep intervals and also keep nearest distance for borderline cases.
        if intervals or min_d <= near_threshold_norm * 1.5:
            out[key] = {
                "near_intervals": intervals,
                "near_threshold_shoulder_width_units": _r(near_threshold_norm, 3),
                "min_distance_shoulder_width_units": _r(min_d, 3),
                "min_distance_time_sec": round(float(min_t), 2),
            }
    return out


def _build_posture(valid: List[dict]) -> dict:
    times = [s["t"] for s in valid]
    return {
        "torso_vertical_state_intervals": _runs_to_intervals(
            times, [s["posture"].get("torso_vertical_state") for s in valid]
        ),
        "arms_crossed_intervals": _flag_to_intervals(
            times, [s["posture"].get("arms_crossed") for s in valid]
        ),
    }


def _prune_empty(d: Any) -> Any:
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            v2 = _prune_empty(v)
            if v2 in (None, [], {}):
                continue
            out[k] = v2
        return out
    if isinstance(d, list):
        return [_prune_empty(v) for v in d if v not in (None, [], {})]
    return d


def _aggregate(
    states: List[Optional[dict]],
    meta: dict,
    max_trajectory_samples: int,
    near_threshold_norm: float,
) -> dict:
    valid = [s for s in states if s is not None]
    track_quality = _build_track_quality(states, meta)

    warnings: List[str] = []
    if not valid:
        warnings.append("No sampled frames had a detectable body pose.")
        return {
            "video_meta": meta,
            "coordinate_system": {
                "x": "normalized image coordinate; left=0, right=1",
                "y": "normalized image coordinate; top=0, bottom=1",
                "z": "MediaPipe relative depth; use cautiously",
                "distance_units": "2D distances normalized by shoulder width",
            },
            "track_quality": track_quality,
            "body_parts": {},
            "motion": {},
            "proximities": {},
            "hand_landmark_states": {},
            "posture": {},
            "warnings": warnings,
        }

    n_missing_pose = len(states) - len(valid)
    if n_missing_pose > 0:
        warnings.append(f"{n_missing_pose}/{len(states)} sampled frames had no detectable pose.")
    if track_quality.get("left_hand_landmarks_detected_ratio", 0.0) < 0.25:
        warnings.append("Left-hand landmarks were detected in fewer than 25% of sampled frames; hand-state evidence may be incomplete.")
    if track_quality.get("right_hand_landmarks_detected_ratio", 0.0) < 0.25:
        warnings.append("Right-hand landmarks were detected in fewer than 25% of sampled frames; hand-state evidence may be incomplete.")

    result = {
        "video_meta": meta,
        "coordinate_system": {
            "x": "normalized image coordinate; left=0, right=1",
            "y": "normalized image coordinate; top=0, bottom=1",
            "z": "MediaPipe relative depth; use cautiously",
            "distance_units": "2D distances normalized by shoulder width",
        },
        "track_quality": track_quality,
        "body_parts": _build_body_parts(valid, max_trajectory_samples=max_trajectory_samples),
        "motion": _build_motion(valid),
        "proximities": _build_proximities(valid, near_threshold_norm=near_threshold_norm),
        "hand_landmark_states": _build_hand_landmark_state_intervals(valid),
        "posture": _build_posture(valid),
        "warnings": warnings,
    }
    return _prune_empty(result)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def extract_primitives(
    video_path: str,
    sample_fps: float = 8.0,
    model_complexity: int = 1,
    visibility_threshold: float = 0.5,
    near_threshold_norm: float = 0.60,
    max_trajectory_samples: int = 12,
) -> dict:
    """Extract open-vocabulary body-pose evidence from a video.

    Parameters
    ----------
    video_path:
        Path to an mp4/mov/etc. video.
    sample_fps:
        Sampling rate for MediaPipe inference. 8 fps is usually a reasonable
        tradeoff for short generated videos.
    model_complexity:
        MediaPipe Holistic model complexity: 0, 1, or 2.
    visibility_threshold:
        Minimum pose landmark visibility used for zone/proximity evidence.
    near_threshold_norm:
        Proximity threshold in shoulder-width-normalized 2D distance units.
    max_trajectory_samples:
        Maximum coordinate samples per tracked part included in the output.

    Returns
    -------
    dict
        JSON-serializable evidence with keys: video_meta, coordinate_system,
        track_quality, body_parts, motion, proximities, hand_landmark_states,
        posture, warnings.
    """
    frames, meta = _run_mediapipe(
        video_path=video_path,
        sample_fps=sample_fps,
        model_complexity=model_complexity,
    )
    states = [_frame_state(frame, visibility_threshold=visibility_threshold) for frame in frames]
    return _aggregate(
        states=states,
        meta=meta,
        max_trajectory_samples=max_trajectory_samples,
        near_threshold_norm=near_threshold_norm,
    )


# ---------------------------------------------------------------------------
# Optional CLI for debugging one video
# ---------------------------------------------------------------------------
def _main() -> None:
    parser = argparse.ArgumentParser(description="Extract open-vocabulary MediaPipe body-pose evidence.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--sample-fps", type=float, default=8.0)
    parser.add_argument("--model-complexity", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--near-threshold-norm", type=float, default=0.60)
    parser.add_argument("--max-trajectory-samples", type=int, default=12)
    parser.add_argument("--output-json", type=Path, default=None)
    args = parser.parse_args()

    evidence = extract_primitives(
        str(args.video),
        sample_fps=args.sample_fps,
        model_complexity=args.model_complexity,
        near_threshold_norm=args.near_threshold_norm,
        max_trajectory_samples=args.max_trajectory_samples,
    )
    text = json.dumps(evidence, indent=2, ensure_ascii=False)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    _main()
