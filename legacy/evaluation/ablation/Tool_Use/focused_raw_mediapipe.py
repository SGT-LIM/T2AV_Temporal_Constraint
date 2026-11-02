"""
Agentic focused raw MediaPipe Holistic formatter.

This module implements an open-action, prompt-conditioned focused_raw baseline:

  1. Extract the same raw MediaPipe pose+hand landmarks as the raw baseline.
     - pose_landmarks: 33 MediaPipe pose landmarks
     - left_hand_landmarks: 21 MediaPipe hand landmarks
     - right_hand_landmarks: 21 MediaPipe hand landmarks
     - face landmarks are intentionally excluded, same as raw_mediapipe.py

  2. Ask a Gemini focus planner to read the original prompt, target events, and
     temporal constraint, then "shop" from the fixed MediaPipe landmark catalog.
     The planner selects landmark NAMES only. It does not see the video and it
     does not judge correctness.

  3. Python validates the planner output against the POSE/HAND whitelist, adds
     minimal symmetric/context safeguards, and filters the raw landmarks.

  4. The final Gemini evaluator receives the video/audio, original prompt, rubric,
     and this prompt-focused raw landmark subset.

Important: this module does NOT compute action labels, motion summaries,
proximity intervals, hand-state interpretations, or correctness judgments.
It only filters raw landmarks by planner-selected landmark names.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from google.genai import types
except Exception:  # pragma: no cover - permits local formatting tests without google-genai
    types = None

try:
    from .raw_mediapipe import extract_raw_mediapipe
    from .body_primitives import POSE, HAND
except ImportError:  # pragma: no cover
    from raw_mediapipe import extract_raw_mediapipe
    from body_primitives import POSE, HAND


ALLOWED_POSE_LANDMARKS: List[str] = list(POSE.keys())
ALLOWED_HAND_LANDMARKS: List[str] = list(HAND.keys())

# Non-action-specific context that helps Gemini reason about scale, body side,
# upper/lower body orientation, and left/right mistakes. These are safeguards,
# not action-specific classifiers.
MINIMAL_CONTEXT_POSE = [
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
]

UPPER_LIMB_CONTEXT = {
    "left": ["left_shoulder", "left_elbow", "left_wrist"],
    "right": ["right_shoulder", "right_elbow", "right_wrist"],
}

LOWER_LIMB_CONTEXT = {
    "left": ["left_hip", "left_knee", "left_ankle", "left_heel", "left_foot_index"],
    "right": ["right_hip", "right_knee", "right_ankle", "right_heel", "right_foot_index"],
}

# Small hand fallback if the planner indicates a hand is relevant but gives too
# few hand landmarks. Full hand landmarks are preferred when fingers/thumb/palm
# may matter, but this fallback keeps prompts shorter than always dumping all.
BASIC_HAND_LANDMARKS = [
    "wrist",
    "thumb_tip",
    "index_tip",
    "middle_tip",
    "ring_tip",
    "pinky_tip",
]


FOCUS_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "focus_summary": {"type": "string"},
        "selected_pose_landmarks": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_POSE_LANDMARKS},
        },
        "selected_left_hand_landmarks": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_HAND_LANDMARKS},
        },
        "selected_right_hand_landmarks": {
            "type": "array",
            "items": {"type": "string", "enum": ALLOWED_HAND_LANDMARKS},
        },
        "selection_reason": {"type": "string"},
        "contrastive_reason": {"type": "string"},
        "temporal_reason": {"type": "string"},
    },
    "required": [
        "focus_summary",
        "selected_pose_landmarks",
        "selected_left_hand_landmarks",
        "selected_right_hand_landmarks",
        "selection_reason",
        "contrastive_reason",
        "temporal_reason",
    ],
}


FOCUS_PLANNER_SYSTEM_PROMPT = """You are a MediaPipe landmark focus planner.

Your job is to select a subset of MediaPipe landmark NAMES that would be useful
for evaluating the visual action and temporal constraint in an original
text-to-audio-video generation prompt.

You are NOT evaluating the generated video.
You are NOT deciding whether the action occurred.
You are NOT assigning action labels.
You are NOT computing motion, proximity, or correctness.
You are only choosing which raw MediaPipe landmark coordinates should be exposed
to a later multimodal evaluator.

Rules:
- Choose only from the allowed pose and hand landmark catalogs provided by the user.
- Select landmarks useful for checking the requested visual action(s).
- If the prompt specifies a left/right side, include the target side and the opposite side as contrastive evidence.
- If hands, fingers, thumb, palm, grasping, pointing, touching, holding, clapping, waving, or gestures may matter, include enough hand landmarks to inspect the hand shape and the opposite hand when relevant.
- If contact with a body part may matter, include landmarks for the acting limb and the target body region.
- If whole-body movement, walking, jumping, squatting, kicking, or foot actions may matter, include a broader skeleton subset around hips, knees, ankles, heels, and foot indices.
- Preserve temporal reasoning: the selected landmarks will be included for ALL sampled frames.
- If uncertain, choose a broader but still relevant subset rather than a too-narrow subset.
- Do not include any correctness judgment in the plan.

Return only the requested JSON object.
"""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return str(obj)


def _describe_behavior(kind: str, label: str) -> str:
    label = _clean_text(label).replace("_", " ")
    if kind == "speech":
        return f'says "{label}"'
    if kind == "silent_action":
        return f'performs the silent visual action "{label}"'
    if kind == "sounding_action":
        return f'performs the sounding action "{label}" with corresponding visible motion and sound'
    return label


def _describe_event(event: dict) -> str:
    return f'Event {event.get("index", "?")}: {_describe_behavior(_clean_text(event.get("kind")), _clean_text(event.get("label")))}'


def _target_event_lines(item_meta: dict) -> str:
    events = item_meta.get("events", []) or []
    if not events:
        return "- See the original generation prompt."
    return "\n".join(f"- {_describe_event(e)}" for e in events if isinstance(e, dict))


def _allowed_catalog_text() -> str:
    return (
        "Allowed pose landmarks (MediaPipe Pose, 33 names):\n"
        + ", ".join(ALLOWED_POSE_LANDMARKS)
        + "\n\nAllowed hand landmarks (MediaPipe Hands, 21 names, available separately for left and right hands):\n"
        + ", ".join(ALLOWED_HAND_LANDMARKS)
    )


def build_focus_planner_user_prompt(item_meta: dict) -> str:
    """Build the text-only prompt for the Gemini focus-planner call."""
    return f"""Task: Select prompt-relevant MediaPipe raw landmark names for focused_raw evidence.

You will receive the original generation prompt, target events, and temporal constraint.
Select which MediaPipe landmark coordinates should be included for all sampled frames.
Do not judge whether the video satisfies the prompt.

{_allowed_catalog_text()}

Original generation prompt:
{_clean_text(item_meta.get("generated_prompt"))}

Item metadata:
- item_id: {_clean_text(item_meta.get("item_id"))}
- modality_combination: {_clean_text(item_meta.get("modality_combination"))}
- content: {_json_dumps(item_meta.get("content", {}) or {})}
- temporal_constraint: {_json_dumps(item_meta.get("temporal_constraint", {}) or {})}
- scene_hint: {_clean_text(item_meta.get("scene_hint"))}
- camera_hint: {_clean_text(item_meta.get("camera_hint"))}

Target events inferred from content:
{_target_event_lines(item_meta)}

Selection requirements:
- Choose pose landmarks by name from the allowed pose catalog.
- Choose left/right hand landmarks by name from the allowed hand catalog.
- For side-specific actions, include contrastive evidence from the opposite side.
- For hand-shape gestures, include enough landmarks to inspect fingers/thumb/palm configuration.
- For body-contact actions, include both the acting limb and target body region.
- Keep the plan compact but sufficient for visual and temporal judgment.
- The downstream code will keep these selected landmarks for every sampled frame.

Return only JSON matching the schema.
"""


def _parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def _dedupe_preserve(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items or []:
        x = _clean_text(x)
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _sanitize_landmarks(items: Iterable[str], allowed: Iterable[str]) -> List[str]:
    allowed_set = set(allowed)
    return _dedupe_preserve([x for x in (items or []) if _clean_text(x) in allowed_set])


def _side_counterpart_pose(name: str) -> Optional[str]:
    if name.startswith("left_"):
        other = "right_" + name[len("left_") :]
        return other if other in POSE else None
    if name.startswith("right_"):
        other = "left_" + name[len("right_") :]
        return other if other in POSE else None
    return None


def normalize_focus_plan(plan_obj: dict) -> dict:
    """Whitelist and lightly safeguard a planner JSON object.

    This function does not add action-specific labels or compute correctness. It
    only validates the planner's selected MediaPipe names and adds generic
    context/contrastive landmarks so focused_raw is robust.
    """
    if not isinstance(plan_obj, dict):
        plan_obj = {}

    pose = _sanitize_landmarks(plan_obj.get("selected_pose_landmarks", []), ALLOWED_POSE_LANDMARKS)
    left_hand = _sanitize_landmarks(plan_obj.get("selected_left_hand_landmarks", []), ALLOWED_HAND_LANDMARKS)
    right_hand = _sanitize_landmarks(plan_obj.get("selected_right_hand_landmarks", []), ALLOWED_HAND_LANDMARKS)

    # Always preserve coarse body context. This helps scale/orientation and is
    # not action-specific.
    pose = _dedupe_preserve(list(MINIMAL_CONTEXT_POSE) + pose)

    # If one side of a paired pose landmark is selected, include the opposite
    # side counterpart to catch wrong-side performance.
    pose_with_contrast = list(pose)
    for name in pose:
        other = _side_counterpart_pose(name)
        if other:
            pose_with_contrast.append(other)
    pose = _dedupe_preserve(pose_with_contrast)

    # If any hand landmarks are selected on one side, include at least a compact
    # opposite-hand set. This is essential for right/left hand mistakes.
    if right_hand and not left_hand:
        left_hand = list(BASIC_HAND_LANDMARKS)
    if left_hand and not right_hand:
        right_hand = list(BASIC_HAND_LANDMARKS)

    # If any hand is selected, include arm context for both sides.
    if left_hand or right_hand:
        pose = _dedupe_preserve(
            pose
            + UPPER_LIMB_CONTEXT["left"]
            + UPPER_LIMB_CONTEXT["right"]
        )

    # If the planner selected almost nothing, use a broad but compact skeleton
    # and fingertip-level hand fallback so evaluation can continue.
    planner_too_empty = len(pose) <= len(MINIMAL_CONTEXT_POSE) and not left_hand and not right_hand
    planner_error = _clean_text(plan_obj.get("planner_error"))
    if planner_too_empty:
        pose = _dedupe_preserve(
            MINIMAL_CONTEXT_POSE
            + UPPER_LIMB_CONTEXT["left"]
            + UPPER_LIMB_CONTEXT["right"]
            + LOWER_LIMB_CONTEXT["left"]
            + LOWER_LIMB_CONTEXT["right"]
        )
        left_hand = list(BASIC_HAND_LANDMARKS)
        right_hand = list(BASIC_HAND_LANDMARKS)

    return {
        "focus_summary": _clean_text(plan_obj.get("focus_summary")) or "Prompt-conditioned landmark subset selected from MediaPipe pose/hand catalogs.",
        "selected_pose_landmarks": _sanitize_landmarks(pose, ALLOWED_POSE_LANDMARKS),
        "selected_left_hand_landmarks": _sanitize_landmarks(left_hand, ALLOWED_HAND_LANDMARKS),
        "selected_right_hand_landmarks": _sanitize_landmarks(right_hand, ALLOWED_HAND_LANDMARKS),
        "selection_reason": _clean_text(plan_obj.get("selection_reason")),
        "contrastive_reason": _clean_text(plan_obj.get("contrastive_reason")) or "Symmetric/contrastive landmarks may be included to detect wrong-side performance.",
        "temporal_reason": _clean_text(plan_obj.get("temporal_reason")) or "Selected landmarks are preserved across all sampled frames for temporal reasoning.",
        "planner_error": planner_error,
        "planner_too_empty_fallback_used": planner_too_empty,
    }


def fallback_focus_plan(reason: str = "") -> dict:
    """Conservative fallback if the Gemini planner call fails."""
    return normalize_focus_plan(
        {
            "focus_summary": "Fallback focused_raw selection using broad skeleton and compact hand landmarks.",
            "selected_pose_landmarks": MINIMAL_CONTEXT_POSE
            + UPPER_LIMB_CONTEXT["left"]
            + UPPER_LIMB_CONTEXT["right"]
            + LOWER_LIMB_CONTEXT["left"]
            + LOWER_LIMB_CONTEXT["right"],
            "selected_left_hand_landmarks": BASIC_HAND_LANDMARKS,
            "selected_right_hand_landmarks": BASIC_HAND_LANDMARKS,
            "selection_reason": "Fallback was used because the focus planner was unavailable or returned invalid output.",
            "contrastive_reason": "Both sides are included to preserve wrong-side evidence.",
            "temporal_reason": "All selected landmarks are kept for every sampled frame.",
            "planner_error": reason,
        }
    )


def call_gemini_focus_planner(
    client: Any,
    planner_model_name: str,
    item_meta: dict,
    thinking_level: Optional[str] = "low",
) -> Tuple[dict, str]:
    """Call Gemini to choose landmark names from the fixed MediaPipe catalog.

    Returns (normalized_plan, raw_planner_output).
    """
    if client is None:
        raise RuntimeError("Gemini focus planner requires a genai.Client instance.")
    if types is None:
        raise RuntimeError("google.genai.types is unavailable; cannot configure the focus planner call.")

    config_kwargs = {
        "response_mime_type": "application/json",
        "response_json_schema": FOCUS_PLAN_SCHEMA,
        "system_instruction": FOCUS_PLANNER_SYSTEM_PROMPT,
    }
    if thinking_level and str(thinking_level).lower() != "none":
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    response = client.models.generate_content(
        model=planner_model_name,
        contents=[build_focus_planner_user_prompt(item_meta)],
        config=types.GenerateContentConfig(**config_kwargs),
    )
    raw_text = response.text or ""
    plan_obj = _parse_json_object(raw_text)
    return normalize_focus_plan(plan_obj), raw_text


def _select_dict(d: Optional[dict], names: List[str]) -> Optional[dict]:
    if d is None:
        return None
    out = {name: d[name] for name in names if name in d}
    return out if out else None


def filter_raw_mediapipe_by_focus_plan(raw: dict, plan: dict) -> dict:
    """Filter a raw MediaPipe JSON dict using a normalized focus plan."""
    pose_names = plan.get("selected_pose_landmarks", []) or []
    left_hand_names = plan.get("selected_left_hand_landmarks", []) or []
    right_hand_names = plan.get("selected_right_hand_landmarks", []) or []

    frames = []
    for frame in raw.get("sampled_frames", []) or []:
        frames.append(
            {
                "sample_index": frame.get("sample_index"),
                "t": frame.get("t"),
                "pose_landmarks": _select_dict(frame.get("pose_landmarks"), pose_names),
                "left_hand_landmarks": _select_dict(frame.get("left_hand_landmarks"), left_hand_names),
                "right_hand_landmarks": _select_dict(frame.get("right_hand_landmarks"), right_hand_names),
            }
        )

    return {
        "evidence_type": "agentic_focused_raw_mediapipe_holistic_landmarks",
        "coordinate_system": raw.get("coordinate_system", {}),
        "video_meta": raw.get("video_meta", {}),
        "raw_frame_count_before_truncation": raw.get("raw_frame_count_before_truncation"),
        "raw_frame_count_included": raw.get("raw_frame_count_included"),
        "focused_frame_count_included": len(frames),
        "max_frames": raw.get("max_frames"),
        "focus_plan": plan,
        "sampled_frames": frames,
        "note": (
            "This is agentic focused_raw MediaPipe evidence. A Gemini focus planner selected "
            "landmark names from the fixed MediaPipe pose/hand catalogs using only the original "
            "prompt, target events, and temporal constraint. Python then filtered the raw landmarks. "
            "This section contains raw coordinates only for the selected landmarks; it does not "
            "compute action labels, motion summaries, proximity intervals, or correctness judgments."
        ),
    }


def _truncate_json_string(obj: dict, max_chars: int) -> str:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [TRUNCATED focused_raw JSON due to max_chars limit]"


def format_focused_raw_mediapipe_as_section(focused_raw: dict, max_detail_chars: int = 50000) -> str:
    meta = focused_raw.get("video_meta", {}) or {}
    plan = focused_raw.get("focus_plan", {}) or {}
    sample_fps = float(meta.get("sample_fps", 0.0) or 0.0)
    duration = float(meta.get("duration_sec", 0.0) or 0.0)
    n_included = focused_raw.get("focused_frame_count_included", 0)
    n_total = focused_raw.get("raw_frame_count_before_truncation", 0)

    detail = _truncate_json_string(focused_raw, max_chars=max_detail_chars)

    return (
        f"Agentic focused raw MediaPipe Holistic output "
        f"(Gemini-planned landmark subset; sampled at {sample_fps:.1f} fps over {duration:.2f}s; "
        f"included {n_included}/{n_total} sampled frames):\n\n"
        f"Focus planner summary: {plan.get('focus_summary', '')}\n"
        f"Selected pose landmarks: {plan.get('selected_pose_landmarks', [])}\n"
        f"Selected left-hand landmarks: {plan.get('selected_left_hand_landmarks', [])}\n"
        f"Selected right-hand landmarks: {plan.get('selected_right_hand_landmarks', [])}\n"
        f"Selection reason: {plan.get('selection_reason', '')}\n"
        f"Contrastive reason: {plan.get('contrastive_reason', '')}\n"
        f"Temporal reason: {plan.get('temporal_reason', '')}\n"
        f"Planner error/fallback note: {plan.get('planner_error', '')}\n\n"
        f"Important note: This section is a prompt-conditioned subset of raw MediaPipe landmarks. "
        f"The first Gemini call selected landmark names only from the fixed MediaPipe catalog; "
        f"Python filtered the raw coordinates accordingly. This section contains no action labels, "
        f"no interval summaries, no proximity computations, and no natural-language motion interpretation. "
        f"Use it only as auxiliary low-level evidence for Visual Event Correctness and Temporal Constraint Satisfaction. "
        f"The video/audio and original prompt remain primary.\n\n"
        f"Focused raw JSON:\n{detail}\n"
    )


def extract_focused_raw_mediapipe(
    video_path: str,
    item_meta: dict,
    planner_client: Any,
    planner_model_name: str,
    planner_thinking_level: Optional[str] = "low",
    sample_fps: float = 8.0,
    model_complexity: int = 1,
    max_frames: int = 40,
    allow_planner_fallback: bool = True,
) -> dict:
    """Extract raw MediaPipe landmarks and filter them with a Gemini focus plan."""
    raw = extract_raw_mediapipe(
        video_path,
        sample_fps=sample_fps,
        model_complexity=model_complexity,
        max_frames=max_frames,
    )

    raw_planner_output = ""
    try:
        plan, raw_planner_output = call_gemini_focus_planner(
            client=planner_client,
            planner_model_name=planner_model_name,
            item_meta=item_meta,
            thinking_level=planner_thinking_level,
        )
    except Exception as exc:
        if not allow_planner_fallback:
            raise
        plan = fallback_focus_plan(f"{type(exc).__name__}: {exc}")

    focused = filter_raw_mediapipe_by_focus_plan(raw, plan)
    focused["raw_focus_planner_output"] = raw_planner_output
    return focused


# Optional CLI for debugging focused filtering with a saved planner JSON.
def _main() -> None:
    parser = argparse.ArgumentParser(description="Filter raw MediaPipe landmarks with a saved focus plan JSON.")
    parser.add_argument("raw_json", type=Path, help="Path to a JSON file produced by raw_mediapipe.py")
    parser.add_argument("focus_plan_json", type=Path, help="Path to a Gemini focus-plan JSON")
    parser.add_argument("--max-detail-chars", type=int, default=50000)
    args = parser.parse_args()

    raw = json.loads(args.raw_json.read_text(encoding="utf-8"))
    plan_obj = json.loads(args.focus_plan_json.read_text(encoding="utf-8"))
    plan = normalize_focus_plan(plan_obj)
    focused = filter_raw_mediapipe_by_focus_plan(raw, plan)
    print(format_focused_raw_mediapipe_as_section(focused, max_detail_chars=args.max_detail_chars))


if __name__ == "__main__":
    _main()
