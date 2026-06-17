#!/usr/bin/env python3
"""
Gemini axis-level evaluator for T2AV temporal-constraint videos.

This version removes hard-coded action rubrics. Instead, it uses the original
generation prompt as the reference specification and asks Gemini to evaluate the
video along prompt-conditioned axes:

1. Audio Event Correctness
2. Visual Event Correctness
3. Audio-Visual Binding
4. Temporal Constraint Satisfaction
5. Constraint Compliance / Prompt Compliance

The main temporal success score intentionally excludes Constraint Compliance:

overall_temporal_success =
    audio_event_correctness
    AND visual_event_correctness
    AND audio_visual_binding
    AND temporal_constraint_satisfaction
"""

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google import genai
from google.genai import types


SUPPORTED_MODALITIES = [
    "Action (silent)",
    "Action (sounding)",
    "Speech",
    "Speech + Action (silent)",
    "Speech + Action (sounding)",
    "Action (silent) + Action (sounding)",
    "Speech + Action (silent) + Action (sounding)",
]

AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_constraint_satisfaction",
    "constraint_compliance",
]

CSV_FIELDNAMES = [
    "video_relpath",
    "video_file",
    "item_id",
    "variant_index",
    "label_name",
    "label_type",
    "modality_combination",
    "event_summary",
    "temporal_type",
    "audio_event_correctness",
    "audio_event_correctness_reason",
    "audio_event_correctness_evidence",
    "visual_event_correctness",
    "visual_event_correctness_reason",
    "visual_event_correctness_evidence",
    "audio_visual_binding",
    "audio_visual_binding_reason",
    "audio_visual_binding_evidence",
    "temporal_constraint_satisfaction",
    "temporal_constraint_satisfaction_reason",
    "temporal_constraint_satisfaction_evidence",
    "constraint_compliance",
    "constraint_compliance_reason",
    "constraint_compliance_evidence",
    "overall_temporal_success",
    "overall_reason",
    "observed_behavior_summary",
    "model",
    "media_fps",
    "thinking_level",
    "uploaded_file_name",
    "uploaded_file_uri",
    "user_prompt",
    "raw_output",
]

SYSTEM_PROMPT = """You are a strict multimodal evaluator for text-to-audio-video generation.

Your job:
- Inspect the video and audio carefully.
- Evaluate whether the generated video satisfies the original generation prompt.
- Use the provided axis definitions exactly.
- Be conservative: unclear, weak, ambiguous, incomplete, mismatched, or approximate evidence should be judged as failure for the relevant axis.
- Do not reward a video merely because it is plausible; it must satisfy the prompt-specific requirements.
- Separate event correctness, audio-visual binding, temporal constraint satisfaction, and constraint compliance.

Important distinction:
- Audio Event Correctness asks whether required speech/sound events are present and correct in audio.
- Visual Event Correctness asks whether required visual events/actions are present and correct in video.
- Audio-Visual Binding asks whether corresponding audio and visual events are correctly linked/aligned.
- Temporal Constraint Satisfaction asks whether the specified temporal relation among the target events is satisfied.
- Constraint Compliance asks whether non-core prompt constraints are satisfied, such as scene, camera, people count, no text/subtitles, no background music, no extra sounds/actions/speech, and post-event stillness.

The main overall_temporal_success score must be computed ONLY from:
audio_event_correctness AND visual_event_correctness AND audio_visual_binding AND temporal_constraint_satisfaction.
Do NOT include constraint_compliance in overall_temporal_success.

Return only the requested JSON object.
"""

AXIS_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["yes", "no"]},
        "reason": {"type": "string"},
        "evidence": {"type": "string"},
    },
    "required": ["label", "reason", "evidence"],
}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "audio_event_correctness": AXIS_RESULT_SCHEMA,
        "visual_event_correctness": AXIS_RESULT_SCHEMA,
        "audio_visual_binding": AXIS_RESULT_SCHEMA,
        "temporal_constraint_satisfaction": AXIS_RESULT_SCHEMA,
        "constraint_compliance": AXIS_RESULT_SCHEMA,
        "overall_temporal_success": {"type": "string", "enum": ["yes", "no"]},
        "overall_reason": {"type": "string"},
        "observed_behavior_summary": {"type": "string"},
    },
    "required": [
        "audio_event_correctness",
        "visual_event_correctness",
        "audio_visual_binding",
        "temporal_constraint_satisfaction",
        "constraint_compliance",
        "overall_temporal_success",
        "overall_reason",
        "observed_behavior_summary",
    ],
}


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def humanize_token(token: str) -> str:
    return clean_text(token).replace("_", " ")


def quote_label(label: str) -> str:
    return f'"{humanize_token(label)}"'


def load_prompt_items(json_path: Path) -> List[dict]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("--prompt-json must contain a list of item dictionaries.")
    return data


def load_json_if_exists(path: Optional[Path]) -> dict:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Overrides file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_variant_index(filename: str) -> Optional[int]:
    m = re.search(r"_v(\d+)(?:_raw)?\.mp4$", filename)
    return int(m.group(1)) if m else None


def infer_item_id_from_path(video_path: Path) -> str:
    return video_path.parent.name


def already_done(csv_path: Path, relpath: str) -> bool:
    if not csv_path.exists():
        return False
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            done_value = clean_text(row.get("overall_temporal_success") or row.get("result")).lower()
            if row.get("video_relpath", "").strip() == relpath and done_value in {"yes", "no"}:
                return True
    return False


# def find_video_files(outputs_dir: Path, include_raw: bool) -> List[Path]:
#     if not outputs_dir.exists():
#         raise FileNotFoundError(f"Outputs dir does not exist: {outputs_dir}")
#     files = []
#     for p in sorted(outputs_dir.rglob("*.mp4")):
#         if not include_raw and p.name.endswith("_raw.mp4"):
#             continue
#         files.append(p)
#     return files

def find_video_files(outputs_dir: Path) -> List[Path]:
    if not outputs_dir.exists():
        raise FileNotFoundError(f"Outputs dir does not exist: {outputs_dir}")
    return sorted(
        p for p in outputs_dir.rglob("*.mp4")
    )


def describe_behavior(kind: str, label: str) -> str:
    label = clean_text(label)
    if kind == "speech":
        return f"says {quote_label(label)}"
    if kind == "silent_action":
        return f"performs the silent visual action {quote_label(label)}"
    if kind == "sounding_action":
        return f"performs the sounding action {quote_label(label)} with corresponding visible motion and sound"
    return humanize_token(label)


def describe_event(event: dict) -> str:
    return f'Event {event["index"]}: {describe_behavior(event["kind"], event["label"])}'


def event_kind_from_key(key: str, modality: str) -> str:
    k = key.lower()
    if "speech" in k or "utterance" in k:
        return "speech"
    if "sounding" in k:
        return "sounding_action"
    if "silent" in k:
        return "silent_action"
    if "action" in k:
        if modality == "Action (sounding)":
            return "sounding_action"
        return "silent_action"
    return "unknown"


def dedupe_preserve(entries: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    out = []
    seen = set()
    for kind, label in entries:
        label = clean_text(label)
        if not label:
            continue
        key = (kind, label)
        if key not in seen:
            seen.add(key)
            out.append((kind, label))
    return out


def event_order_for_modality(modality: str, content: dict) -> List[Tuple[str, str]]:
    """
    Returns a canonical list of (kind, label) for target events.
    The ordering is used to resolve order constraints.
    """
    entries: List[Tuple[str, str]] = []

    if modality == "Speech":
        for key in ["speech", "utterance", "speech_1", "utterance_1", "speech_2", "utterance_2", "speech_3", "utterance_3"]:
            value = clean_text(content.get(key))
            if value:
                entries.append(("speech", value))
        return dedupe_preserve(entries)

    if modality == "Action (silent)":
        for key in ["action", "action_1", "action_2", "action_3", "silent_action", "action_silent"]:
            value = clean_text(content.get(key))
            if value:
                entries.append(("silent_action", value))
        return dedupe_preserve(entries)

    if modality == "Action (sounding)":
        for key in ["action", "action_1", "action_2", "action_3", "sounding_action", "action_sounding"]:
            value = clean_text(content.get(key))
            if value:
                entries.append(("sounding_action", value))
        return dedupe_preserve(entries)

    if modality == "Speech + Action (silent)":
        speech_value = first_value(content, ["speech", "utterance", "speech_1", "utterance_1"])
        silent_value = first_value(content, ["silent_action", "action_silent", "action", "action_1"])
        if speech_value:
            entries.append(("speech", speech_value))
        if silent_value:
            entries.append(("silent_action", silent_value))
        return dedupe_preserve(entries)

    if modality == "Speech + Action (sounding)":
        speech_value = first_value(content, ["speech", "utterance", "speech_1", "utterance_1"])
        sounding_value = first_value(content, ["sounding_action", "action_sounding", "action", "action_1"])
        if speech_value:
            entries.append(("speech", speech_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    if modality == "Action (silent) + Action (sounding)":
        silent_value = first_value(content, ["silent_action", "action_silent", "action_1"])
        sounding_value = first_value(content, ["sounding_action", "action_sounding", "action_2"])
        if not silent_value and not sounding_value:
            # fallback for older prompt JSONs with only generic action keys
            silent_value = first_value(content, ["action"])
        if silent_value:
            entries.append(("silent_action", silent_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    if modality == "Speech + Action (silent) + Action (sounding)":
        speech_value = first_value(content, ["speech", "utterance", "speech_1", "utterance_1"])
        silent_value = first_value(content, ["silent_action", "action_silent", "action_1"])
        sounding_value = first_value(content, ["sounding_action", "action_sounding", "action_2"])
        if speech_value:
            entries.append(("speech", speech_value))
        if silent_value:
            entries.append(("silent_action", silent_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    # Generic fallback.
    for key in [
        "speech", "utterance", "speech_1", "utterance_1", "speech_2", "utterance_2",
        "silent_action", "action_silent", "sounding_action", "action_sounding",
        "action", "action_1", "action_2", "action_3",
    ]:
        value = clean_text(content.get(key))
        if value:
            entries.append((event_kind_from_key(key, modality), value))
    return dedupe_preserve(entries)


def first_value(content: dict, keys: List[str]) -> str:
    for key in keys:
        value = clean_text(content.get(key))
        if value:
            return value
    return ""


def build_event_list(content: dict, modality: str) -> List[dict]:
    ordered = event_order_for_modality(modality, content)
    return [
        {"index": i + 1, "kind": kind, "label": label}
        for i, (kind, label) in enumerate(ordered)
    ]


def resolve_sequence(sequence_value, events: List[dict]) -> List[str]:
    if not sequence_value:
        return []
    if isinstance(sequence_value, str):
        sequence = [x.strip() for x in sequence_value.split(",") if x.strip()]
    else:
        sequence = list(sequence_value)

    resolved = []
    for token in sequence:
        if isinstance(token, int) or (isinstance(token, str) and token.isdigit()):
            idx = int(token)
            event = next((e for e in events if e["index"] == idx), None)
            resolved.append(describe_event(event) if event else f"Event {idx}")
            continue

        text = clean_text(token)
        if not text:
            continue

        # token may be key-like
        key_to_idx = {
            "speech": 1, "utterance": 1, "speech_1": 1, "utterance_1": 1,
            "action": 1, "action_1": 1,
            "speech_2": 2, "utterance_2": 2, "action_2": 2,
            "speech_3": 3, "utterance_3": 3, "action_3": 3,
        }
        matched = None
        if text in key_to_idx:
            idx = key_to_idx[text]
            matched = next((e for e in events if e["index"] == idx), None)

        resolved.append(describe_event(matched) if matched is not None else humanize_token(text))
    return resolved


def infer_label_name(events: List[dict], temporal_constraint: dict) -> str:
    if events:
        return " | ".join(describe_event(e) for e in events)
    sequence = resolve_sequence((temporal_constraint or {}).get("value", {}).get("sequence"), [])
    if sequence:
        return " -> ".join(sequence)
    return "(see prompt)"


def label_type_from_modality(modality: str) -> str:
    mapping = {
        "Speech": "speech",
        "Action (silent)": "silent_action",
        "Action (sounding)": "sounding_action",
        "Speech + Action (silent)": "speech_plus_silent_action",
        "Speech + Action (sounding)": "speech_plus_sounding_action",
        "Action (silent) + Action (sounding)": "silent_plus_sounding_action",
        "Speech + Action (silent) + Action (sounding)": "speech_plus_silent_plus_sounding_action",
    }
    return mapping.get(modality, "unknown")


def events_of_kind(events: List[dict], kind: str) -> List[dict]:
    return [e for e in events if e["kind"] == kind]


def build_audio_axis_criteria(events: List[dict]) -> str:
    lines = []
    for event in events_of_kind(events, "speech"):
        lines.append(f'- The speech event {quote_label(event["label"])} must be clearly audible and intelligible.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- The sound corresponding to the sounding action {quote_label(event["label"])} must be clearly audible and appropriate for the prompt.')
    if not lines:
        lines.append("- There is no explicit speech or sound event to evaluate for this axis; mark yes unless the original prompt requires audio that is missing.")
    return "\n".join(lines)


def build_visual_axis_criteria(events: List[dict]) -> str:
    lines = []
    for event in events_of_kind(events, "silent_action"):
        lines.append(f'- The visual silent action {quote_label(event["label"])} must be clearly visible and correctly performed according to the original generation prompt.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- The visible motion for the sounding action {quote_label(event["label"])} must be clearly visible and correctly performed according to the original generation prompt.')
    if not lines:
        lines.append("- There is no explicit visual action to evaluate for this axis; mark yes unless the original prompt requires a visual action that is missing.")
    return "\n".join(lines)


def build_av_binding_axis_criteria(events: List[dict]) -> str:
    lines = []
    for event in events_of_kind(events, "speech"):
        lines.append(f'- If the speaker is visible, the visible speaking/lip motion should be temporally aligned with the spoken event {quote_label(event["label"])}. If the face/mouth is not visible but the prompt does not require it, judge this based on the available evidence and the prompt.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- The visible action {quote_label(event["label"])} must be temporally aligned with its corresponding sound; the sound should occur at the moment implied by the visible action.')
    if not lines:
        lines.append("- There is no explicit audio-visual binding requirement to evaluate for this axis; mark yes unless the original prompt implies a required audio-visual link that is violated.")
    return "\n".join(lines)


def describe_temporal_value(value) -> str:
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def build_temporal_axis_criteria(events: List[dict], temporal_constraint: dict) -> str:
    if not temporal_constraint:
        return "- No explicit temporal constraint is provided; mark yes if the required target events are not temporally contradictory."

    t_type = clean_text(temporal_constraint.get("type")) or "unspecified"
    t_value = temporal_constraint.get("value", {}) or {}
    event_desc = ", ".join(describe_event(e) for e in events) if events else "the required target events"

    if t_type == "synchronization":
        mode = clean_text(t_value.get("mode"))
        desc = clean_text(t_value.get("description")) or clean_text(t_value.get("relation"))
        count = t_value.get("count")
        lines = [
            f"- Temporal constraint type: synchronization.",
            f"- Check whether the required target events are synchronized: {event_desc}.",
            "- The target events must occur simultaneously or with tight temporal alignment as specified by the original generation prompt.",
        ]
        if mode:
            lines.append(f"- Synchronization mode: {humanize_token(mode)}.")
            if mode == "simultaneous_once":
                lines.append("- The required synchronized target event should occur as a single synchronized co-occurrence.")
        if count is not None:
            lines.append(f"- The synchronized target co-occurrence should occur exactly {count} time(s).")
        if desc:
            lines.append(f"- Additional temporal guidance: {desc}")
        lines.append("- If the required events are sequential instead of simultaneous, offset, disconnected, missing, or unclear, mark this axis as no.")
        return "\n".join(lines)

    if t_type == "order":
        resolved = resolve_sequence(t_value.get("sequence"), events)
        sequence_desc = " -> ".join(resolved) if resolved else "the order specified in the original prompt"
        return f"""- Temporal constraint type: order.
- Required order: {sequence_desc}.
- Each required event must appear clearly in that exact order.
- If the order is reversed, mixed, overlapping when it should be sequential, missing, or unclear, mark this axis as no."""

    if t_type == "count":
        count = t_value.get("count")
        return f"""- Temporal constraint type: count.
- The target behavior must occur exactly {count} time(s).
- Count only clear and completed target event occurrences.
- If the number of target occurrences is different or unclear, mark this axis as no."""

    if t_type == "sync_count":
        count = t_value.get("count", t_value.get("sync_count"))
        if count is None:
            count = t_value.get("value")
        return f"""- Temporal constraint type: synchronized count.
- The required target events must occur in synchronized alignment exactly {count} time(s): {event_desc}.
- Count only clear synchronized co-occurrences where all required events happen together.
- If they synchronize fewer or more than {count} times, or if the count is unclear, mark this axis as no."""

    if t_type == "rhythm":
        pattern = humanize_token(t_value.get("pattern"))
        return f"""- Temporal constraint type: rhythm.
- The target behavior should repeat with the required rhythm: {pattern}.
- If the rhythm is irregular, missing, or unclear, mark this axis as no."""

    if t_type == "relative_spacing":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Temporal constraint type: relative spacing.
- Apply this spacing requirement: {description}
- If the event spacing is missing, inconsistent, or unclear, mark this axis as no."""

    if t_type == "absolute_timing":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Temporal constraint type: absolute timing.
- Apply this exact timing requirement: {description}
- If the event onsets, pauses, or durations clearly violate the timing requirement, mark this axis as no."""

    if t_type == "start_stop":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Temporal constraint type: start/stop.
- Apply this start/stop rule: {description}
- If any required behavior starts too early, ends too late, ignores the trigger, or is unclear, mark this axis as no."""

    return f"""- Temporal constraint type: {humanize_token(t_type)}.
- Raw temporal constraint value: {describe_temporal_value(t_value)}
- Apply the temporal rule strictly according to the original generation prompt.
- If the rule is not clearly satisfied, mark this axis as no."""


def build_constraint_compliance_criteria(item_meta: dict) -> str:
    scene_hint = clean_text(item_meta.get("scene_hint"))
    camera_hint = clean_text(item_meta.get("camera_hint"))

    lines = [
        "- Evaluate non-core prompt constraints separately from the main temporal score.",
        "- Check scene, setting, camera, shot type, people count, subtitles/on-screen text, background music, extra sounds, extra speech, extra gestures/actions, and post-event stillness according to the original generation prompt.",
        "- If the original prompt says the person should become still after the target event, then any additional speech, gesture, slap, or salient action after the target event should make this axis no.",
        "- If the original prompt says no other people, no subtitles, no on-screen text, no background music, or no extra sounds, enforce those constraints here.",
    ]
    if scene_hint:
        lines.append(f"- Scene hint to enforce when visible: {scene_hint}.")
    if camera_hint:
        lines.append(f"- Camera/shot hint to enforce when visible: {camera_hint}.")
    lines.append("- Do not use this axis when computing overall_temporal_success.")
    return "\n".join(lines)


def build_axis_criteria(item_meta: dict) -> str:
    events = item_meta["events"]
    temporal_constraint = item_meta.get("temporal_constraint", {}) or {}

    return f"""Axis-specific criteria:

1. Audio Event Correctness
{build_audio_axis_criteria(events)}

2. Visual Event Correctness
{build_visual_axis_criteria(events)}

3. Audio-Visual Binding
{build_av_binding_axis_criteria(events)}

4. Temporal Constraint Satisfaction
{build_temporal_axis_criteria(events, temporal_constraint)}

5. Constraint Compliance / Prompt Compliance
{build_constraint_compliance_criteria(item_meta)}
"""


def make_user_text(item_meta: dict) -> str:
    modality = item_meta["modality_combination"]
    generated_prompt = item_meta["generated_prompt"]
    events = item_meta["events"]
    temporal_constraint = item_meta.get("temporal_constraint", {}) or {}
    content = item_meta.get("content", {}) or {}

    event_lines = "\n".join(f"- {describe_event(e)}" for e in events) if events else "- See the original generation prompt."

    return f"""Task: Evaluate this generated video using the redefined axis-level T2AV temporal metric.

Original generation prompt:
{generated_prompt}

Item metadata:
- item_id: {item_meta.get("item_id", "")}
- modality_combination: {modality}
- content: {json.dumps(content, ensure_ascii=False)}
- temporal_constraint: {json.dumps(temporal_constraint, ensure_ascii=False)}
- scene_hint: {item_meta.get("scene_hint", "")}
- camera_hint: {item_meta.get("camera_hint", "")}

Target events inferred from content:
{event_lines}

{build_axis_criteria(item_meta)}

Decision rules:
- For each axis, output label "yes" only if that axis is clearly satisfied.
- If evidence is missing, ambiguous, weak, mismatched, or contradicted, output "no" for the relevant axis.
- Constraint Compliance is reported separately as prompt compliance / quality control.
- overall_temporal_success must be:
  audio_event_correctness AND visual_event_correctness AND audio_visual_binding AND temporal_constraint_satisfaction.
- Do not include constraint_compliance in overall_temporal_success.
- Keep reasons concise but specific.
- Return the JSON object only.
"""


def apply_item_overrides(item: dict, overrides: dict) -> dict:
    item_id = clean_text(item.get("item_id"))
    if not item_id:
        return item
    override = overrides.get(item_id)
    if not override:
        return item

    merged = dict(item)
    for key, value in override.items():
        if key == "content":
            merged["content"] = {**(item.get("content", {}) or {}), **(value or {})}
        elif key == "temporal_constraint":
            merged["temporal_constraint"] = {**(item.get("temporal_constraint", {}) or {}), **(value or {})}
        else:
            merged[key] = value
    return merged


def build_item_meta_map(
    items: List[dict],
    modality_filter: Optional[str] = None,
    item_overrides: Optional[dict] = None,
) -> Dict[str, dict]:
    out = {}
    item_overrides = item_overrides or {}

    for raw_item in items:
        item = apply_item_overrides(raw_item, item_overrides)

        item_id = clean_text(item.get("item_id"))
        modality = clean_text(item.get("modality_combination"))
        content = item.get("content", {}) or {}
        temporal_constraint = item.get("temporal_constraint", {}) or {}

        if not item_id:
            continue

        if modality_filter is not None and modality != modality_filter:
            continue

        events = build_event_list(content, modality)
        out[item_id] = {
            "item_id": item_id,
            "label": infer_label_name(events, temporal_constraint),
            "events": events,
            "modality_combination": modality,
            "generated_prompt": clean_text(item.get("generated_prompt")),
            "content": content,
            "temporal_constraint": temporal_constraint,
            "scene_hint": clean_text(item.get("scene_hint")),
            "camera_hint": clean_text(item.get("camera_hint")),
        }

    return out


def wait_until_active(client: genai.Client, uploaded_file, poll_seconds: float, timeout_seconds: float):
    start = time.time()
    current = uploaded_file
    while True:
        state = getattr(current, "state", None)
        state_name = getattr(state, "name", None) if state is not None else None

        if state_name == "ACTIVE":
            return current
        if state_name == "FAILED":
            raise RuntimeError(f"Gemini file processing failed for {getattr(current, 'name', 'unknown file')}")
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for file to become ACTIVE: {getattr(current, 'name', 'unknown file')}")

        time.sleep(poll_seconds)
        current = client.files.get(name=current.name)


def normalize_axis(obj: dict, axis_name: str) -> dict:
    if not isinstance(obj, dict):
        raise ValueError(f"Axis {axis_name!r} must be an object.")
    label = clean_text(obj.get("label")).lower()
    if label not in {"yes", "no"}:
        raise ValueError(f"Unexpected label value for {axis_name}: {label!r}")
    return {
        "label": label,
        "reason": clean_text(obj.get("reason")),
        "evidence": clean_text(obj.get("evidence")),
    }


def normalize_result(obj: dict) -> dict:
    result = {}
    for axis in AXIS_KEYS:
        result[axis] = normalize_axis(obj.get(axis), axis)

    # Force the main temporal score to follow our definition.
    axis_labels = [result[axis]["label"] for axis in [
        "audio_event_correctness",
        "visual_event_correctness",
        "audio_visual_binding",
        "temporal_constraint_satisfaction",
    ]]
    computed_overall = "yes" if all(label == "yes" for label in axis_labels) else "no"

    model_overall = clean_text(obj.get("overall_temporal_success")).lower()
    if model_overall not in {"yes", "no"}:
        model_overall = computed_overall

    result["overall_temporal_success"] = computed_overall
    result["overall_reason"] = clean_text(obj.get("overall_reason"))
    if model_overall != computed_overall:
        result["overall_reason"] = (
            result["overall_reason"] +
            f" [Post-processed: model overall was {model_overall!r}, but the required AND rule gives {computed_overall!r}.]"
        ).strip()
    result["observed_behavior_summary"] = clean_text(obj.get("observed_behavior_summary"))
    return result


def evaluate_video(
    client: genai.Client,
    model_name: str,
    video_path: Path,
    item_meta: dict,
    media_fps: Optional[float],
    thinking_level: Optional[str],
    timeout_seconds: float,
) -> dict:
    uploaded = client.files.upload(file=str(video_path))
    uploaded = wait_until_active(client, uploaded, poll_seconds=5.0, timeout_seconds=timeout_seconds)

    user_text = make_user_text(item_meta)

    config_kwargs = {
        "response_mime_type": "application/json",
        "response_json_schema": RESULT_SCHEMA,
        "system_instruction": SYSTEM_PROMPT,
    }

    if thinking_level is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    if media_fps is not None:
        contents = [
            types.Part(
                file_data=types.FileData(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
                video_metadata=types.VideoMetadata(fps=media_fps),
            ),
            user_text,
        ]
    else:
        contents = [uploaded, user_text]

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    raw_text = response.text or ""
    parsed = json.loads(raw_text)
    result = normalize_result(parsed)
    result["raw_output"] = raw_text
    result["uploaded_file_name"] = getattr(uploaded, "name", "")
    result["uploaded_file_uri"] = getattr(uploaded, "uri", "")
    result["user_prompt"] = user_text
    return result


def ensure_csv_header(csv_path: Path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()


def append_row(csv_path: Path, row: dict):
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(row)


def build_success_row_base(
    relpath: str,
    video_path: Path,
    outputs_dir: Path,
    item_id: str,
    variant_index: Optional[int],
    item_meta: dict,
    args,
) -> dict:
    return {
        "video_relpath": relpath,
        "video_file": video_path.name,
        "item_id": item_id,
        "variant_index": variant_index,
        "label_name": item_meta["label"],
        "label_type": label_type_from_modality(item_meta["modality_combination"]),
        "modality_combination": item_meta["modality_combination"],
        "event_summary": " | ".join(describe_event(e) for e in item_meta["events"]),
        "temporal_type": clean_text(item_meta.get("temporal_constraint", {}).get("type")),
        "model": args.model,
        "media_fps": args.media_fps,
        "thinking_level": args.thinking_level,
    }


def add_result_to_row(row: dict, result: dict) -> dict:
    for axis in AXIS_KEYS:
        row[axis] = result[axis]["label"]
        row[f"{axis}_reason"] = result[axis]["reason"]
        row[f"{axis}_evidence"] = result[axis]["evidence"]

    row["overall_temporal_success"] = result["overall_temporal_success"]
    row["overall_reason"] = result["overall_reason"]
    row["observed_behavior_summary"] = result["observed_behavior_summary"]
    row["uploaded_file_name"] = result["uploaded_file_name"]
    row["uploaded_file_uri"] = result["uploaded_file_uri"]
    row["user_prompt"] = result["user_prompt"]
    row["raw_output"] = result["raw_output"]
    return row


def add_error_to_row(row: dict, error: Exception, item_meta: dict) -> dict:
    for axis in AXIS_KEYS:
        row[axis] = ""
        row[f"{axis}_reason"] = ""
        row[f"{axis}_evidence"] = ""
    row["overall_temporal_success"] = ""
    row["overall_reason"] = f"ERROR: {error}"
    row["observed_behavior_summary"] = ""
    row["uploaded_file_name"] = ""
    row["uploaded_file_uri"] = ""
    row["user_prompt"] = make_user_text(item_meta)
    row["raw_output"] = ""
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-json", type=Path, required=True)
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--model", type=str, default="gemini-3.1-pro-preview")
    parser.add_argument("--output-csv", type=Path, default=Path("./eval_outputs/new-axis_temporal_eval.csv"))
    parser.add_argument("--media-fps", type=float, default=8.0)
    parser.add_argument("--thinking-level", type=str, default="high", choices=["low", "high"])
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--item-overrides-json",
        type=Path,
        default=None,
        help="Optional JSON mapping item_id -> override dict.",
    )
    parser.add_argument(
        "--modality-filter",
        type=str,
        default=None,
        choices=SUPPORTED_MODALITIES,
        help="Evaluate only items with this modality_combination.",
    )
    parser.add_argument(
        "--variant-indices",
        type=int,
        nargs="*",
        default=None,
        help="Only evaluate videos whose parsed variant index is in this list. Example: --variant-indices 2 3",
    )
    args = parser.parse_args()

    allowed_variants = set(args.variant_indices) if args.variant_indices is not None else None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")

    item_overrides = load_json_if_exists(args.item_overrides_json)
    item_meta_map = build_item_meta_map(
        load_prompt_items(args.prompt_json),
        modality_filter=args.modality_filter,
        item_overrides=item_overrides,
    )
    if not item_meta_map:
        raise ValueError("No valid item metadata found from prompt JSON.")

    video_files = find_video_files(args.outputs_dir)
    if not video_files:
        raise FileNotFoundError(f"No mp4 files found under {args.outputs_dir}")

    ensure_csv_header(args.output_csv)
    client = genai.Client(api_key=api_key)

    print(f"Found {len(video_files)} candidate videos.")
    print(f"Loaded {len(item_meta_map)} item metadata entries.")

    for video_path in video_files:
        relpath = str(video_path.relative_to(args.outputs_dir))
        item_id = infer_item_id_from_path(video_path)
        variant_index = parse_variant_index(video_path.name)

        if allowed_variants is not None:
            if variant_index is None:
                print(f"Skipping {relpath}: could not parse variant index")
                continue
            if variant_index not in allowed_variants:
                print(f"Skipping {relpath}: variant {variant_index} not in requested set {sorted(allowed_variants)}")
                continue

        if not args.overwrite and already_done(args.output_csv, relpath):
            print(f"Skipping {relpath}: already evaluated")
            continue

        if item_id not in item_meta_map:
            print(f"Skipping {relpath}: parent folder item_id not found in prompt JSON -> {item_id}")
            continue

        item_meta = item_meta_map[item_id]
        row = build_success_row_base(
            relpath=relpath,
            video_path=video_path,
            outputs_dir=args.outputs_dir,
            item_id=item_id,
            variant_index=variant_index,
            item_meta=item_meta,
            args=args,
        )

        try:
            result = evaluate_video(
                client=client,
                model_name=args.model,
                video_path=video_path,
                item_meta=item_meta,
                media_fps=args.media_fps,
                thinking_level=args.thinking_level,
                timeout_seconds=args.timeout_seconds,
            )
            row = add_result_to_row(row, result)
            append_row(args.output_csv, row)
            print(
                f"[OK] {relpath} -> overall_temporal_success={result['overall_temporal_success']} "
                f"(A={result['audio_event_correctness']['label']}, "
                f"V={result['visual_event_correctness']['label']}, "
                f"AVB={result['audio_visual_binding']['label']}, "
                f"TC={result['temporal_constraint_satisfaction']['label']}, "
                f"CC={result['constraint_compliance']['label']})"
            )
        except Exception as e:
            row = add_error_to_row(row, e, item_meta)
            append_row(args.output_csv, row)
            print(f"[ERROR] {relpath} -> {e}")


if __name__ == "__main__":
    main()
