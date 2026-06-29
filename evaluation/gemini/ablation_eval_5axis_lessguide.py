#!/usr/bin/env python3
"""
Open-vocabulary, tool-augmented Gemini evaluator for T2AV temporal-constraint videos.

This script evaluates generated text-to-audio-video outputs with a strict 5-axis
rubric:

  1. audio_event_correctness
  2. visual_event_correctness
  3. audio_visual_binding
  4. temporal_constraint_satisfaction
  5. constraint_compliance

The main temporal success score intentionally excludes constraint_compliance:

    overall_temporal_success =
        audio_event_correctness
        AND visual_event_correctness
        AND audio_visual_binding
        AND temporal_constraint_satisfaction

Optional MediaPipe integration:
  - none: Gemini-only baseline.
  - raw: full raw MediaPipe pose+hand landmark dump, excluding face landmarks.
  - focused_raw: Gemini-planned, prompt-conditioned subset of the same raw pose+hand landmarks.
    A first Gemini call selects landmark names from the fixed MediaPipe catalog;
    Python filters the raw landmarks; the final Gemini call evaluates the video.
    The evidence contains no action labels, motion summaries, proximity intervals,
    or correctness labels.
  - Use --no-mediapipe-hint for Gemini-only ablation.

Expected video layout:
    outputs_dir/
      item_id/
        item_id_v1_raw.mp4
        item_id_v2_raw.mp4
        ...

The parent directory name of each mp4 is used as item_id.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google import genai
from google.genai import types

try:
    from Tool_Use.raw_mediapipe import extract_raw_mediapipe, format_raw_mediapipe_as_section
    from Tool_Use.focused_raw_mediapipe import (
        extract_focused_raw_mediapipe,
        format_focused_raw_mediapipe_as_section,
    )
except Exception:  # pragma: no cover - useful when running Gemini-only
    extract_raw_mediapipe = None
    format_raw_mediapipe_as_section = None
    extract_focused_raw_mediapipe = None
    format_focused_raw_mediapipe_as_section = None

try:
    from Tool_Use.audio_evidence import build_audio_evidence_section
except Exception:  # pragma: no cover - useful when running without audio tools
    build_audio_evidence_section = None


SUPPORTED_MODALITIES = [
    "Action (silent)",
    "Action (sounding)",
    "Speech",
    "Speech + Action (silent)",
    "Speech + Action (sounding)",
    "Action (silent) + Action (sounding)",
    "Speech + Action (silent) + Action (sounding)",
    # Compact metadata aliases used by the refined_prompt_ver2 outputs.
    "Action (Si)",
    "Action (So)",
    "Speech + Action (Si)",
    "Speech + Action (So)",
    "Action (Si) + Action (So)",
    "Speech + Action (Si) + Action (So)",
]

# Axes the model is asked to return directly (each has label/reason/evidence).
# Temporal Constraint is now split into two sub-axes: relation and count.
MODEL_AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_relation_satisfaction",
    "temporal_count_satisfaction",
    "constraint_compliance",
]

# Sub-axes that compose Temporal Constraint Satisfaction.
TC_SUBAXIS_KEYS = [
    "temporal_relation_satisfaction",
    "temporal_count_satisfaction",
]

# Combined Temporal Constraint Satisfaction is derived (relation AND count).
DERIVED_TC_KEY = "temporal_constraint_satisfaction"

# All axes that receive label/reason/evidence columns in the CSV
# (model-returned axes plus the derived combined TC axis).
ALL_AXIS_KEYS = MODEL_AXIS_KEYS + [DERIVED_TC_KEY]

# Backward-compatible alias used by older call sites.
AXIS_KEYS = ALL_AXIS_KEYS

# Axes ANDed into overall_temporal_success (uses the derived combined TC).
CORE_AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_constraint_satisfaction",
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
    "audio_event_correctness_per_event",
    "visual_event_correctness",
    "visual_event_correctness_reason",
    "visual_event_correctness_evidence",
    "visual_event_correctness_per_event",
    "audio_visual_binding",
    "audio_visual_binding_reason",
    "audio_visual_binding_evidence",
    "audio_visual_binding_per_event",
    "temporal_relation_satisfaction",
    "temporal_relation_satisfaction_reason",
    "temporal_relation_satisfaction_evidence",
    "temporal_count_satisfaction",
    "temporal_count_satisfaction_reason",
    "temporal_count_satisfaction_evidence",
    "temporal_count_satisfaction_per_event",
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
    "pose_evidence_mode",
    "mediapipe_hint_used",
    "mediapipe_fps",
    "mediapipe_error",
    "mediapipe_summary",
    "audio_evidence_mode",
    "audio_evidence_used",
    "audio_evidence_error",
    "audio_evidence_summary",
    "uploaded_file_name",
    "uploaded_file_uri",
    "user_prompt",
    "raw_output",
]

# ---------------------------------------------------------------------------
# System prompt, split into a tool-independent CORE and tool-specific guides.
# Tool guides are injected only when the corresponding evidence mode is active
# (see build_system_prompt), so a Gemini-only run carries no tool instructions.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_CORE_HEAD = """You are a strict multimodal evaluator for text-to-audio-video generation.

Your job:
- Inspect the video and audio carefully.
- Evaluate whether the generated video satisfies the original generation prompt.
- Use the provided axis definitions exactly.
- Be conservative: unclear, weak, ambiguous, incomplete, mismatched, or approximate evidence should be judged as failure for the relevant axis.
- Do not reward a video merely because it is plausible; it must satisfy the prompt-specific requirements.
- Evaluate audio correctness, visual correctness, audio-visual binding, temporal constraint satisfaction (relation and count), and constraint compliance, following the strict hierarchical dependency defined below.

Definition of "event":
- An event is a prompt-specified unit that may include audio, visual motion, or both.
- A speech event (e.g., saying "help") includes the spoken audio AND the corresponding visible mouth/lip movement.
- A silent action event (e.g., a right-hand thumbs-up) includes ONLY the visible action.
- A sounding action event (e.g., slapping the thigh) includes BOTH the slap sound AND the visible slapping motion.
- Audio Event Correctness and Visual Event Correctness are judged on the audio/visual components of each event. Audio-Visual Binding is judged WITHIN a single event (whether that event's audio and visual components are correctly bound). Temporal Constraint Satisfaction is judged BETWEEN events (their ordering, synchronization, spacing, count, etc.).

Axis definitions:
- Audio Event Correctness asks whether the required speech/sound component of each event is present and correct in the audio.
- Visual Event Correctness asks whether the required visual component of each event (action/pose/contact, or visible speaking mouth/lip motion for speech) is present and correct in the video. For speech it judges visible speaking behavior (face/mouth visible if required, plausible mouth/lip motion), NOT whether the spoken word/content is correct; correctness of the spoken word belongs to Audio Event Correctness.
- Audio-Visual Binding asks whether, WITHIN the same event, the audio and visual components are correctly bound (temporally and causally aligned).
- Temporal Constraint Satisfaction asks whether the specified temporal relation BETWEEN events is satisfied. It is split into two sub-axes:
  - Temporal Relation: the type-specific relation between events (synchronization / order / relative spacing / absolute timing / rhythm / start-stop).
  - Temporal Count: whether each required event/bundle occurs the required number of times (default EXACTLY ONCE), with no extra or spurious occurrences.
- Constraint Compliance asks whether non-core prompt constraints are satisfied, such as scene, camera, people count, no text/subtitles, no background music, no extra sounds/actions/speech, and post-event stillness.

Hierarchical evaluation dependency (CRITICAL - the axes are NOT orthogonal; a failure cascades downward):
- Step 1: Judge Audio Event Correctness and Visual Event Correctness on their own merits.
- Step 2: Evaluate Audio-Visual Binding ONLY when BOTH the required audio AND the required visual component of the event are correct. AVB judges whether they are correctly bound, ASSUMING both are present, correct, and synchronized. If either the required audio OR the required visual component is incorrect or missing, you MUST mark Audio-Visual Binding as "no" (binding is not evaluable, so it fails).
- Step 3: Evaluate Temporal Constraint Satisfaction (BOTH the Temporal Relation and Temporal Count sub-axes) ONLY when Audio Event Correctness, Visual Event Correctness, AND Audio-Visual Binding are all "yes" for the relevant events. If any preceding component fails, you MUST mark BOTH Temporal Relation and Temporal Count as "no".
- Concretely: a missing/incorrect audio or visual component forces Audio-Visual Binding to "no", which in turn forces both Temporal Relation and Temporal Count to "no".

Temporal Count sub-axis (applies to ALL temporal types, not only synchronization):
- By default, each required event/bundle must occur EXACTLY ONCE. More than the required number, or extra/spurious occurrences of a target action/sound/speech beyond the specified structure, makes Temporal Count "no".
- If the prompt explicitly specifies a repetition count N (e.g., a count or synchronized-count constraint), the required number is N instead of once.
- Even for order, synchronization, spacing, or absolute-timing prompts, still verify the count: each required event should appear the required number of times (default once) with no extra repetitions, unless the prompt explicitly allows repetition.

Temporal Relation sub-axis:
- This is the type-specific relation between events as specified by the prompt: synchronization (simultaneous or tightly aligned), order (exact sequence), relative spacing, absolute timing, rhythm, or start/stop.
- For a synchronization-"once" prompt, Temporal Relation judges simultaneity/tight alignment while Temporal Count separately judges that the synchronized bundle occurs exactly once.

The main overall_temporal_success score must be computed ONLY from:
audio_event_correctness AND visual_event_correctness AND audio_visual_binding AND temporal_relation_satisfaction AND temporal_count_satisfaction.
Do NOT include constraint_compliance in overall_temporal_success."""

TOOL_GENERAL_GUIDE = """Tool evidence interpretation guide:

General rule:
- Tool outputs are auxiliary evidence, not ground-truth labels.
- The video and audio themselves remain primary. If tool evidence conflicts with clear video/audio evidence, defer to the video/audio.
- Do not mark an axis as "yes" only because a tool section contains a plausible-looking value. Use tool evidence together with the original prompt and direct audiovisual inspection.
- If tool evidence is missing, sparse, low-confidence, contradictory, temporally too coarse, or inconsistent with the prompt, be conservative."""

MEDIAPIPE_GUIDE = """MediaPipe:
- MediaPipe evidence consists of sampled body/hand landmarks from the video.
- Raw MediaPipe output contains pose and hand coordinates only; it does not contain action labels, motion summaries, proximity computations, or correctness judgments.
- Focused raw MediaPipe output is only a prompt-conditioned subset of raw landmarks. The focus planner selected landmark names, not whether the action occurred.
- MediaPipe x/y coordinates are normalized image coordinates: x increases from image-left to image-right, and y increases from image-top to image-bottom.
- MediaPipe z is relative depth and model-dependent; use it cautiously.
- Pose landmarks may include visibility; hand landmarks do not include visibility.
- Left/right refers to MediaPipe-estimated body side, not the viewer's side. Laterality may be unreliable when hands cross, tracking is poor, or generated video anatomy is distorted.
- For side-specific prompts, compare both target-side and opposite-side landmarks, and be conservative if laterality is ambiguous.
- Use MediaPipe only for Visual Event Correctness and Temporal Constraint Satisfaction, especially visible action presence, rough timing, hand/body position, hand shape, side-specific evidence, and visible speaking/mouth/face evidence when available.
- A landmark pattern is not by itself proof of an action or speech motion. The visual event must also be supported by the video and must match the original prompt."""

WHISPER_GUIDE = """Whisper ASR:
- Whisper is an automatic speech-recognition tool. It transcribes speech-like audio into text with segment-level and word-level timestamps.
- Segment start/end times are approximate speech-region times.
- Word timestamps give approximate start/end times for individual words and are the most useful Whisper evidence for speech timing.
- no_speech_prob is Whisper's estimate that a segment contains no speech. Lower values mean stronger evidence of speech; higher values mean the segment may be non-speech or unreliable.
- has_speech is a heuristic flag based on whether any segment has no_speech_prob < 0.5. It is not a correctness label.
- avg_logprob is the average log probability of the transcription tokens. Less negative values generally indicate more confident transcription; very low values should be treated cautiously.
- language_probability indicates confidence in the detected language. Low language probability makes the transcription less reliable.
- Whisper can mis-transcribe or hallucinate speech in degraded generated audio, so do not treat a transcript as definitive if the audio itself suggests otherwise.
- Use Whisper only for Audio Event Correctness of speech, speech timing for Temporal Constraint Satisfaction, and speech-related Audio-Visual Binding when visible speaking/lip motion is relevant.
- Do not use Whisper to verify non-speech sound events such as clapping, slapping, knocking, footsteps, or object sounds.
- Do not use Whisper to judge whether mouth/lip motion visually occurred; that belongs to direct video inspection and visual evidence."""

CLAP_GUIDE = """CLAP:
- CLAP is an audio-text similarity model, not a calibrated sound classifier.
- CLAP compares the audio embedding with text-query embeddings and reports cosine similarities.
- cos_sim is a raw cosine similarity between the audio and a text query. Higher generally means closer match, but absolute thresholds are unreliable.
- softmax_pos is computed only among positive sound queries, excluding negative anchors. It is not the probability that the sound is truly present.
- Negative anchors such as silence, background noise, and white noise are comparison references. A target sound query is more useful when it is clearly stronger than these anchors and temporally plausible.
- Sliding-window similarities are approximate timing evidence over audio chunks. A high score means the queried sound may occur somewhere in that window, not exactly at the window center.
- If the window is long, temporal localization is coarse. Do not infer exact event onset from a broad window alone.
- Use CLAP only for non-speech sound-event presence, rough sound-event timing, and sound-to-visible-action binding.
- Do not use CLAP to verify speech content; use Whisper for speech content.
- Do not treat a high CLAP cosine similarity as proof of correctness on its own. Compare it against negative anchors, competing positive queries, the original prompt, and what can be heard in the audio."""

TOOL_HANDLING_GUIDE = """Tool-section handling:
- If the user message contains a "Raw MediaPipe Holistic output" section, treat it as a vanilla raw-tool baseline: raw sampled landmarks only.
- If the user message contains a "Focused raw MediaPipe Holistic output" or "Agentic focused raw MediaPipe Holistic output" section, treat it as a prompt-conditioned subset of raw sampled landmarks selected by a focus planner.
- In both MediaPipe cases, the evidence contains no action labels, no motion interpretation, no proximity computation, and no correctness judgment.
- If the user message contains a "Whisper ASR transcription" section, treat it as raw speech-recognition evidence over the audio track: segment timestamps, transcript text, no_speech_prob, avg_logprob, language confidence, and word timestamps. It is not a correctness label.
- If the user message contains a "CLAP open-vocabulary sound-event evidence" section, treat it as raw text-audio similarity evidence: global cosine similarities and optionally sliding-window cosine similarities between audio chunks and text queries. It is not a correctness label or calibrated probability.
- Use MediaPipe only as visual evidence. It may help judge visible action presence, body/hand position, hand shape, laterality, visible action timing, and visible speaking/mouth/face motion. Do not use MediaPipe to judge speech content or non-speech sound presence.
- Use Whisper and CLAP only as audio evidence. Whisper may help judge speech content and speech timing. CLAP may help judge non-speech sound presence and rough sound timing. Do not use Whisper or CLAP to judge whether a visual action or mouth/lip motion occurred.
- For Audio-Visual Binding and Temporal Constraint Satisfaction, you may compare visual timing from the video/MediaPipe with audio timing from Whisper/CLAP. The tools should still remain within their own modality: MediaPipe/video for visual evidence, Whisper/CLAP/audio for audio evidence.
- The video and audio remain primary evidence. If tool evidence disagrees with what you can clearly see or hear, defer to the video/audio.

Axis-specific tool usage:
- For Audio Event Correctness, use direct audio inspection, Whisper for required speech, and CLAP for required non-speech sound events.
- For Visual Event Correctness, use direct video inspection and MediaPipe evidence for visible body/hand actions, object/contact actions, pose correctness, side-specific visual details, and visible speaking/mouth/lip motion.
- For Audio-Visual Binding, use direct audiovisual inspection, Whisper word timestamps for speech timing, CLAP sound-event windows for non-speech timing, and MediaPipe/video evidence for visible action or mouth/lip timing.
- For Temporal Constraint Satisfaction, compare the required event order, count, synchronization, spacing, or absolute timing against direct video/audio evidence and any relevant tool timestamps or windows.
- For Constraint Compliance, check extra speech, extra sounds, extra actions, subtitles/text, background music, people count, scene/camera constraints, and post-event stillness. Tool evidence can help detect extra speech/sounds/actions, but the final judgment should still rely on the video/audio and original prompt."""

SYSTEM_PROMPT_CORE_TAIL = """Temporal reasoning:
- Treat exact timestamps in the prompt strictly, but allow for the practical uncertainty of generated video and frame-level observation (and any tool timestamps/windows when provided).
- Do not claim exact timing from coarse evidence. Use phrases such as "near", "around", or "within the window" when the evidence is approximate.
- If a required event is missing, ambiguous, too early, too late, reversed, repeated incorrectly, or temporally disconnected from its paired audio/visual event, mark the relevant axis as "no".
- For synchronization, required events must occur together or with tight temporal alignment according to the prompt. Sequential or loosely related events should not be counted as synchronized.
- For absolute timing, required events should occur at the specified times in the specified order. If timing evidence is too uncertain to verify the requirement, be conservative.
- For fixed target-event structures such as absolute schedules, relative orders, synchronization, or single synchronized bundles, the target sequence is exclusive unless the prompt explicitly allows repetitions. If any required target event occurs again after the scheduled final event, or if the video contains an extra occurrence of a target action/sound/speech beyond the specified structure, mark Temporal Constraint Satisfaction as "no". Score this repetition error under Temporal Constraint (specifically Temporal Count); do NOT additionally count the same repetition error as an extra action under Constraint Compliance.
- If a required target event is absent or only partially present in one modality, mark Temporal Constraint Satisfaction as "no" when that missing component prevents the scheduled/order/sync structure from being completed.

Laterality and perspective:
- If the prompt specifies the person's left/right body side, judge body-side laterality, not viewer-left/viewer-right.
- For side-specific actions, check whether the target body side performed the action and whether the opposite side did not substitute for it.
- If the video perspective, MediaPipe landmarks, or generated anatomy make left/right ambiguous, do not give credit for a side-specific requirement unless the target side is clearly supported.

Speech-specific examples (apply the hierarchical dependency: AVB requires BOTH audio and visual to be correct):
- If the word "help" is clearly heard but the mouth/face is not visible when required, or the mouth is visible but shows no speaking motion, then Audio Event Correctness can be "yes", Visual Event Correctness should be "no", and because the visual component fails, Audio-Visual Binding must be "no".
- If speech-like audio is present and visible mouth/lip motion is synchronized, but the word is not "help", then Audio Event Correctness should be "no" and Visual Event Correctness can be "yes"; because the audio component is incorrect, Audio-Visual Binding must be "no" even though the lip motion looks synchronized.
- If the mouth/lips visibly move as if speaking but no speech audio is heard, then Audio Event Correctness should be "no", Visual Event Correctness can be "yes", and because the audio component is missing, Audio-Visual Binding must be "no".
- If the spoken word is correct AND visible mouth/lip motion is correct but their timing is offset, then Audio Event Correctness can be "yes", Visual Event Correctness can be "yes", and Audio-Visual Binding should be "no" (both components are correct, so binding is evaluable, and the misalignment fails it).

Sounding-action examples (apply the hierarchical dependency: AVB requires BOTH sound and action to be correct):
- If a required non-speech sound such as a slap is heard but there is no visible candidate action at the sound time, then Audio Event Correctness can be "yes", Visual Event Correctness should be "no", and because the visual component fails, Audio-Visual Binding must be "no".
- If a required non-speech sound is heard and a visible candidate action occurs at the same time, but the action uses the wrong hand, wrong side, wrong target body part, wrong contact location, or imperfect form, then Audio Event Correctness can be "yes", Visual Event Correctness should be "no", and because the visual component is incorrect, Audio-Visual Binding must be "no".
- If a visible candidate action occurs but the corresponding sound is absent, then Visual Event Correctness depends on whether the visible action itself is correct, Audio Event Correctness should be "no", and because the audio component is missing, Audio-Visual Binding must be "no".
- If both the sound and the action are correct but they are temporally offset or disconnected, then Audio Event Correctness can be "yes", Visual Event Correctness can be "yes", and Audio-Visual Binding should be "no" (binding is evaluable but fails).

Output rules (PER-EVENT for three axes, PER-EVENT counts for one, OVERALL for the rest):
- Return only the requested JSON object.
- audio_event_correctness, visual_event_correctness, and audio_visual_binding are scored PER EVENT. Each of these axes is an object with a "per_event" array. Each array entry corresponds to one target event_id and contains: event_id, label ("yes"/"no"), reason, evidence.
  - audio_event_correctness: include one entry for EACH event that has an audio component (speech events and sounding-action events). Do NOT include silent-action events (they have no audio).
  - visual_event_correctness: include one entry for EACH target event (speech = visible speaking mouth/lip motion; silent or sounding action = the visible action).
  - audio_visual_binding: include one entry for EACH event that has BOTH an audio and a visual component (speech events and sounding-action events). Do NOT include silent-action events.
- temporal_count_satisfaction is also PER EVENT. It is an object with a "per_event" array. Each entry contains: event_id, observed_count (integer = the number of clear, completed occurrences of THAT event you actually observe), reason, evidence. Report the raw count; the harness compares it to the required count.
- temporal_relation_satisfaction and constraint_compliance are SINGLE OVERALL judgments (one object each with label, reason, evidence). temporal_relation describes the BETWEEN-event timing relation (synchronization / order / spacing / absolute timing / rhythm / start-stop).
- Do NOT output a combined temporal_constraint_satisfaction object; it is derived downstream as temporal_relation_satisfaction AND temporal_count_satisfaction.
- For a per-event label to be "yes", that event must clearly satisfy the axis AND its hierarchical preconditions must hold for that event (binding for an event requires that same event's audio and visual to be correct).
- When you mark an entry "no" because a precondition failed, say so explicitly in its reason (e.g., 'audio component for this event is incorrect, so binding is not evaluable').
- Use the exact event_id strings provided in the user message. Provide an entry for every applicable event_id; do not invent extra ids.
- Keep reasons concise but specific. In evidence fields, cite concrete observations such as visible event timing, heard audio timing, Whisper word timestamps, CLAP windows, or MediaPipe landmark timestamps when useful.
- overall_temporal_success must be computed as the AND, over the relevant events, of audio_event_correctness, visual_event_correctness, audio_visual_binding, temporal_relation_satisfaction, and temporal_count_satisfaction. Do not include constraint_compliance in overall_temporal_success."""

def build_system_prompt(pose_evidence_mode: str = "none", audio_evidence_mode: str = "none") -> str:
    """Assemble the system prompt for the active evidence modes.

    The tool-interpretation guides (MediaPipe / Whisper / CLAP) are included only
    when the corresponding tool is active. With both modes set to "none" the
    returned prompt contains the core evaluation rules only -- no instructions for
    tools that are not present in the user message. Ordering matches the original
    prompt when all tools are enabled.
    """
    use_pose = pose_evidence_mode not in (None, "", "none")
    use_whisper = audio_evidence_mode in ("whisper", "both")
    use_clap = audio_evidence_mode in ("clap", "both")
    any_tool = use_pose or use_whisper or use_clap

    parts = [SYSTEM_PROMPT_CORE_HEAD]
    if any_tool:
        parts.append(TOOL_GENERAL_GUIDE)
        if use_pose:
            parts.append(MEDIAPIPE_GUIDE)
        if use_whisper:
            parts.append(WHISPER_GUIDE)
        if use_clap:
            parts.append(CLAP_GUIDE)
        parts.append(TOOL_HANDLING_GUIDE)
    parts.append(SYSTEM_PROMPT_CORE_TAIL)
    return "\n\n".join(parts)


# Backward-compatible full prompt (all tool guides included).
SYSTEM_PROMPT = build_system_prompt("raw", "both")

# Item-independent global rules, taken verbatim from the human-evaluation
# guideline. Injected once into the user message so the model and human raters
# apply the same definitions. Item-specific criteria are still generated
# per-item by the build_*_criteria functions below.
GUIDELINE_DEFINITIONS = """Shared evaluation notes:
- Judge each axis according to the original generation prompt and the axis-specific criteria below, using your own best judgment of the audio and the video.
- For temporal relations (synchronization, order, relative spacing, absolute timing, rhythm, start/stop) and for occurrence counts, decide whether the requirement stated in the prompt is satisfied based on what you observe.
"""

# Scalar axis result (used for the OVERALL axes: temporal_relation, constraint_compliance).
AXIS_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["yes", "no"]},
        "reason": {"type": "string"},
        "evidence": {"type": "string"},
    },
    "required": ["label", "reason", "evidence"],
}

# One per-event yes/no judgment (for audio/visual/binding axes).
PER_EVENT_AXIS_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "label": {"type": "string", "enum": ["yes", "no"]},
        "reason": {"type": "string"},
        "evidence": {"type": "string"},
    },
    "required": ["event_id", "label", "reason", "evidence"],
}

# One per-event count judgment (observed integer count; harness compares to required).
PER_EVENT_COUNT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "observed_count": {"type": "integer"},
        "reason": {"type": "string"},
        "evidence": {"type": "string"},
    },
    "required": ["event_id", "observed_count", "reason", "evidence"],
}

PER_EVENT_AXIS_SCHEMA = {
    "type": "object",
    "properties": {
        "per_event": {"type": "array", "items": PER_EVENT_AXIS_ITEM_SCHEMA},
    },
    "required": ["per_event"],
}

PER_EVENT_COUNT_SCHEMA = {
    "type": "object",
    "properties": {
        "per_event": {"type": "array", "items": PER_EVENT_COUNT_ITEM_SCHEMA},
    },
    "required": ["per_event"],
}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        # Per-event axes.
        "audio_event_correctness": PER_EVENT_AXIS_SCHEMA,
        "visual_event_correctness": PER_EVENT_AXIS_SCHEMA,
        "audio_visual_binding": PER_EVENT_AXIS_SCHEMA,
        "temporal_count_satisfaction": PER_EVENT_COUNT_SCHEMA,
        # Overall (between-event / global) axes.
        "temporal_relation_satisfaction": AXIS_RESULT_SCHEMA,
        "constraint_compliance": AXIS_RESULT_SCHEMA,
        "overall_temporal_success": {"type": "string", "enum": ["yes", "no"]},
        "overall_reason": {"type": "string"},
        "observed_behavior_summary": {"type": "string"},
    },
    "required": [
        "audio_event_correctness",
        "visual_event_correctness",
        "audio_visual_binding",
        "temporal_relation_satisfaction",
        "temporal_count_satisfaction",
        "constraint_compliance",
        "overall_temporal_success",
        "overall_reason",
        "observed_behavior_summary",
    ],
}

# Per-event axes that emit a "per_event" array (used for JSON columns / long CSV).
PER_EVENT_AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_count_satisfaction",
]


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------
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


def find_video_files(outputs_dir: Path) -> List[Path]:
    if not outputs_dir.exists():
        raise FileNotFoundError(f"Outputs dir does not exist: {outputs_dir}")
    return sorted(p for p in outputs_dir.rglob("*.mp4") if p.is_file())


# ---------------------------------------------------------------------------
# Prompt item / event interpretation
# ---------------------------------------------------------------------------
def canonical_event_kind(value: str, modality: str = "") -> str:
    """Map old-schema and compact-schema event/modality tokens to evaluator kinds."""
    token = clean_text(value).lower()
    modality_norm = normalize_modality(modality) if modality else ""

    if token in {"speech", "sp", "sp_action", "utterance"} or "speech" in token or "utterance" in token:
        return "speech"
    if token in {"si", "si_action", "silent", "silent_action", "action_silent"} or "silent" in token:
        return "silent_action"
    if token in {"so", "so_action", "sounding", "sounding_action", "action_sounding"} or "sounding" in token:
        return "sounding_action"
    if token in {"action", "action_1", "action_2", "action_3"}:
        if modality_norm == "Action (sounding)":
            return "sounding_action"
        return "silent_action"
    return "unknown"


def normalize_modality(modality: str) -> str:
    """Canonicalize compact modality strings only for evaluator logic."""
    m = clean_text(modality)
    replacements = {
        "Action (Si)": "Action (silent)",
        "Action (So)": "Action (sounding)",
        "Speech + Action (Si)": "Speech + Action (silent)",
        "Speech + Action (So)": "Speech + Action (sounding)",
        "Action (Si) + Action (So)": "Action (silent) + Action (sounding)",
        "Speech + Action (Si) + Action (So)": "Speech + Action (silent) + Action (sounding)",
    }
    return replacements.get(m, m)


def label_from_event(event: dict, kind: str) -> str:
    if kind == "speech":
        return clean_text(event.get("text") or event.get("utterance") or event.get("label") or event.get("id"))
    if kind in {"silent_action", "sounding_action"}:
        return clean_text(event.get("action") or event.get("label") or event.get("id"))
    return clean_text(event.get("label") or event.get("action") or event.get("text") or event.get("id"))


def label_from_content_value(value, kind: str = "unknown") -> str:
    """Extract a human label from either old string content or new dict content."""
    if isinstance(value, dict):
        if kind == "speech":
            return clean_text(value.get("text") or value.get("utterance") or value.get("label") or value.get("id"))
        if kind in {"silent_action", "sounding_action"}:
            return clean_text(value.get("action") or value.get("label") or value.get("id"))
        return clean_text(value.get("action") or value.get("text") or value.get("label") or value.get("id"))
    return clean_text(value)


def event_aliases(kind: str, source_id: str = "") -> List[str]:
    aliases = set()
    sid = clean_text(source_id)
    if sid:
        aliases.add(sid)
    if kind == "speech":
        aliases.update(["speech", "Sp", "sp", "Sp_action", "sp_action", "utterance"])
    elif kind == "silent_action":
        aliases.update(["silent_action", "silent", "Si", "si", "Si_action", "si_action", "action_silent"])
    elif kind == "sounding_action":
        aliases.update(["sounding_action", "sounding", "So", "so", "So_action", "so_action", "action_sounding"])
    return sorted(a for a in aliases if a)


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
    return canonical_event_kind(key, modality)


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


def first_value(content: dict, keys: List[str], kind: str = "unknown") -> str:
    for key in keys:
        if key not in content:
            continue
        value = label_from_content_value(content.get(key), kind=kind)
        if value:
            return value
    return ""


def event_order_for_modality(modality: str, content: dict) -> List[Tuple[str, str]]:
    """Return a canonical list of (kind, label) for old, new, or compact content schemas."""
    entries: List[Tuple[str, str]] = []
    modality_norm = normalize_modality(modality)

    if not isinstance(content, dict):
        return []

    if modality_norm == "Speech":
        for key in ["speech", "Sp", "Sp_action", "utterance", "speech_1", "utterance_1", "speech_2", "utterance_2", "speech_3", "utterance_3"]:
            value = first_value(content, [key], "speech")
            if value:
                entries.append(("speech", value))
        return dedupe_preserve(entries)

    if modality_norm == "Action (silent)":
        for key in ["silent_action", "Si_action", "Si", "action_silent", "action", "action_1", "action_2", "action_3"]:
            value = first_value(content, [key], "silent_action")
            if value:
                entries.append(("silent_action", value))
        return dedupe_preserve(entries)

    if modality_norm == "Action (sounding)":
        for key in ["sounding_action", "So_action", "So", "action_sounding", "action", "action_1", "action_2", "action_3"]:
            value = first_value(content, [key], "sounding_action")
            if value:
                entries.append(("sounding_action", value))
        return dedupe_preserve(entries)

    if modality_norm == "Speech + Action (silent)":
        speech_value = first_value(content, ["speech", "Sp", "Sp_action", "utterance", "speech_1", "utterance_1"], "speech")
        silent_value = first_value(content, ["silent_action", "Si_action", "Si", "action_silent", "action", "action_1"], "silent_action")
        if speech_value:
            entries.append(("speech", speech_value))
        if silent_value:
            entries.append(("silent_action", silent_value))
        return dedupe_preserve(entries)

    if modality_norm == "Speech + Action (sounding)":
        speech_value = first_value(content, ["speech", "Sp", "Sp_action", "utterance", "speech_1", "utterance_1"], "speech")
        sounding_value = first_value(content, ["sounding_action", "So_action", "So", "action_sounding", "action", "action_1"], "sounding_action")
        if speech_value:
            entries.append(("speech", speech_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    if modality_norm == "Action (silent) + Action (sounding)":
        silent_value = first_value(content, ["silent_action", "Si_action", "Si", "action_silent", "action_1"], "silent_action")
        sounding_value = first_value(content, ["sounding_action", "So_action", "So", "action_sounding", "action_2"], "sounding_action")
        if not silent_value and not sounding_value:
            silent_value = first_value(content, ["action"], "silent_action")
        if silent_value:
            entries.append(("silent_action", silent_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    if modality_norm == "Speech + Action (silent) + Action (sounding)":
        speech_value = first_value(content, ["speech", "Sp", "Sp_action", "utterance", "speech_1", "utterance_1"], "speech")
        silent_value = first_value(content, ["silent_action", "Si_action", "Si", "action_silent", "action_1"], "silent_action")
        sounding_value = first_value(content, ["sounding_action", "So_action", "So", "action_sounding", "action_2"], "sounding_action")
        if speech_value:
            entries.append(("speech", speech_value))
        if silent_value:
            entries.append(("silent_action", silent_value))
        if sounding_value:
            entries.append(("sounding_action", sounding_value))
        return dedupe_preserve(entries)

    # Generic fallback for old, new, compact, or open-ended prompt JSONs.
    for key, value in content.items():
        kind = canonical_event_kind(key, modality_norm)
        label = label_from_content_value(value, kind=kind)
        if label:
            entries.append((kind, label))
    return dedupe_preserve(entries)


def build_event_list(content: dict, modality: str, raw_events: Optional[List[dict]] = None) -> List[dict]:
    """Build evaluator event objects. Prefer explicit item["events"] when available."""
    built: List[dict] = []

    if isinstance(raw_events, list) and raw_events:
        for i, event in enumerate(raw_events):
            if not isinstance(event, dict):
                continue
            source_id = clean_text(event.get("id") or event.get("event_id") or event.get("modality"))
            kind = canonical_event_kind(event.get("modality") or source_id, modality)
            label = label_from_event(event, kind)
            if not label:
                continue
            built.append({
                "index": i + 1,
                "kind": kind,
                "label": label,
                "source_id": source_id,
                "aliases": event_aliases(kind, source_id),
                "definition": clean_text(event.get("definition")),
                "count": event.get("count"),
            })
        if built:
            return built

    ordered = event_order_for_modality(modality, content)
    for i, (kind, label) in enumerate(ordered):
        built.append({
            "index": i + 1,
            "kind": kind,
            "label": label,
            "source_id": "",
            "aliases": event_aliases(kind),
            "definition": "",
            "count": None,
        })
    return built


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

        matched = next((e for e in events if text in set(e.get("aliases", []))), None)
        if matched is None:
            canonical = canonical_event_kind(text)
            matched = next((e for e in events if e.get("kind") == canonical), None)

        resolved.append(describe_event(matched) if matched is not None else humanize_token(text))
    return resolved


def infer_label_name(events: List[dict], temporal_constraint: dict) -> str:
    if events:
        return " | ".join(describe_event(e) for e in events)
    value = (temporal_constraint or {}).get("value", {}) or {}
    sequence = resolve_sequence(value.get("sequence") or value.get("events"), [])
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
    return mapping.get(normalize_modality(modality), "unknown")


def events_of_kind(events: List[dict], kind: str) -> List[dict]:
    return [e for e in events if e["kind"] == kind]


def build_audio_axis_criteria(events: List[dict]) -> str:
    lines = []
    for event in events_of_kind(events, "speech"):
        lines.append(f'- The speech event {quote_label(event["label"])} must be clearly audible and intelligible.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- The sound corresponding to the sounding action {quote_label(event["label"])} must be clearly audible and appropriate for the prompt.')
    if not lines:
        lines.append("- There is no explicit speech or sound event to evaluate for this axis; mark yes unless the original prompt requires audio that is missing or wrong.")
    return "\n".join(lines)


def build_visual_axis_criteria(events: List[dict]) -> str:
    lines = []
    for event in events_of_kind(events, "speech"):
        lines.append(f'- For the speech event {quote_label(event["label"])}: the speaker\'s mouth/lips must be visible (when required by the prompt) and show plausible speaking motion. Judge ONLY the visible speaking behavior here, NOT whether the spoken word is correct (that belongs to Audio Event Correctness).')
    for event in events_of_kind(events, "silent_action"):
        lines.append(f'- The visual silent action {quote_label(event["label"])} must be clearly visible and correctly performed according to the original generation prompt.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- The visible motion for the sounding action {quote_label(event["label"])} must be clearly visible and correctly performed according to the original generation prompt.')
    if not lines:
        lines.append("- There is no explicit visual action to evaluate for this axis; mark yes unless the original prompt requires a visual action that is missing or wrong.")
    return "\n".join(lines)


def build_av_binding_axis_criteria(events: List[dict]) -> str:
    lines = [
        "- Audio-Visual Binding is evaluated WITHIN each event: whether that event's audio component and visual component are correctly bound (temporally and causally aligned), assuming both are present and correct.",
        "- Precondition (hierarchical): evaluate this axis only when the event's required audio (Audio Event Correctness) AND required visual component (Visual Event Correctness) are both correct. If either is incorrect or missing, mark this axis no.",
    ]
    for event in events_of_kind(events, "speech"):
        lines.append(f'- For the speech event {quote_label(event["label"])}: given correct spoken audio and correct visible mouth/lip motion, check that the audible speech is temporally aligned with that visible mouth/lip motion. If the spoken word is wrong or the visible speaking motion is wrong/absent, mark this axis no.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- For the sounding action {quote_label(event["label"])}: given a correct sound and a correctly performed visible motion, check that the sound occurs at the moment implied by the visible action. If either the sound or the visible action is wrong or missing, mark this axis no.')
    if not events_of_kind(events, "speech") and not events_of_kind(events, "sounding_action"):
        lines.append("- There is no explicit audio-visual binding requirement to evaluate for this axis (e.g., a silent-only action). Mark yes unless the prompt implies a required audio-visual link that is violated, subject to the precondition above.")
    return "\n".join(lines)


def describe_temporal_value(value) -> str:
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def temporal_relation_and_timing(temporal_constraint: dict) -> Tuple[str, str, dict]:
    """Return (relation, timing, value) for old and new temporal schemas."""
    if not temporal_constraint:
        return "", "", {}

    value = temporal_constraint.get("value", {}) or {}
    relation = clean_text(temporal_constraint.get("relation_type"))
    timing = clean_text(temporal_constraint.get("timing_type"))

    old_type = clean_text(temporal_constraint.get("type"))
    if not relation:
        if old_type == "absolute_timing":
            timing = timing or "absolute"
            relation = clean_text(value.get("base_relation")) or "absolute_timing"
            if relation == "count":
                relation = "sync_count"
        elif old_type == "count":
            relation = "sync_count" if clean_text(value.get("mode")) == "synchronized_repetition" else "count"
        else:
            relation = old_type

    if not timing:
        if old_type == "absolute_timing":
            timing = "absolute"
        elif old_type or relation:
            timing = "relative"

    return relation, timing, value


def temporal_type_label(temporal_constraint: dict) -> str:
    relation, timing, _ = temporal_relation_and_timing(temporal_constraint)
    if timing and relation:
        return f"{timing}_{relation}"
    return relation or timing or ""


def describe_scheduled_events(schedule, events: List[dict]) -> List[str]:
    lines = []
    if not isinstance(schedule, list):
        return lines
    for step in schedule:
        if not isinstance(step, dict):
            continue
        time_sec = step.get("time_sec")
        resolved = resolve_sequence(step.get("events"), events)
        event_text = " + ".join(resolved) if resolved else "the specified event(s)"
        if time_sec is not None:
            lines.append(f"around {time_sec} seconds: {event_text}")
        else:
            lines.append(event_text)
    return lines


def required_event_count(events: List[dict], temporal_constraint: dict) -> Optional[int]:
    """Required number of occurrences of the target event/bundle.

    Returns an explicit integer when the prompt specifies a count
    (count / sync_count / repetition schedule), otherwise None to mean the
    default of exactly once.
    """
    if not temporal_constraint:
        return None
    relation, _timing, t_value = temporal_relation_and_timing(temporal_constraint)
    if relation in {"sync_count", "count"}:
        count = t_value.get("count")
        if count is None:
            scheduled = describe_scheduled_events(t_value.get("schedule"), events)
            if scheduled:
                count = len(scheduled)
        if isinstance(count, int):
            return count
    return None


# ---------------------------------------------------------------------------
# Per-event scoring scaffolding
# ---------------------------------------------------------------------------
def event_axis_applicability(kind: str) -> Tuple[bool, bool, bool]:
    """Return (has_audio, has_visual, has_binding) for an event kind."""
    has_audio = kind in {"speech", "sounding_action"}
    has_binding = kind in {"speech", "sounding_action"}
    has_visual = True  # every target event has a visual component
    return has_audio, has_visual, has_binding


def build_scoring_events(item_meta: dict) -> List[dict]:
    """Attach per-event ids, axis applicability, and required occurrence counts.

    The event list is already parsed into item_meta["events"]; this just decorates
    each event with the metadata the per-event evaluator needs. The required count
    is taken from an explicit per-event "count" if present, else the prompt-level
    count (count / sync_count), else the default of exactly once.
    """
    events = item_meta.get("events", []) or []
    temporal_constraint = item_meta.get("temporal_constraint", {}) or {}
    global_required = required_event_count(events, temporal_constraint)

    scoring: List[dict] = []
    for e in events:
        kind = e.get("kind", "unknown")
        has_audio, has_visual, has_binding = event_axis_applicability(kind)

        ev_count = e.get("count")
        if isinstance(ev_count, bool):
            ev_count = None
        if isinstance(ev_count, int):
            required = ev_count
        elif global_required is not None:
            required = global_required
        else:
            required = 1

        scoring.append({
            "event_id": f"event_{e['index']}",
            "index": e["index"],
            "kind": kind,
            "label": clean_text(e.get("label")),
            "has_audio": has_audio,
            "has_visual": has_visual,
            "has_binding": has_binding,
            "required_count": required,
        })
    return scoring


def _applicable_axes_for_event(se: dict) -> List[str]:
    axes = ["visual_event_correctness", "temporal_count_satisfaction"]
    if se["has_audio"]:
        axes.append("audio_event_correctness")
    if se["has_binding"]:
        axes.append("audio_visual_binding")
    return sorted(set(axes))


def build_per_event_instructions(item_meta: dict) -> str:
    """Human-readable per-event target list injected into the user message."""
    scoring = build_scoring_events(item_meta)
    if not scoring:
        return ("Per-event scoring: no discrete target events were parsed for this item. "
                "Return empty per_event arrays for the per-event axes and fall back to the "
                "original generation prompt for the overall axes.")

    lines = [
        "Per-event scoring targets (CRITICAL):",
        "Use these EXACT event_id strings in the per_event arrays of audio_event_correctness, "
        "visual_event_correctness, audio_visual_binding, and temporal_count_satisfaction.",
    ]
    for se in scoring:
        kind_h = humanize_token(se["kind"])
        axes = ", ".join(_applicable_axes_for_event(se))
        lines.append(f'- {se["event_id"]} ({kind_h}): {quote_label(se["label"])}  ->  score in: {axes}.')

    req_bits = ", ".join(f'{se["event_id"]}={se["required_count"]}' for se in scoring)
    lines.extend([
        "",
        f"Required occurrence count per event (default exactly once): {req_bits}.",
        "For temporal_count_satisfaction, report observed_count as the integer number of clear, "
        "completed occurrences you actually see/hear for that event_id. Do NOT pre-judge pass/fail; "
        "the harness compares observed_count against the required count above.",
        "audio_event_correctness and audio_visual_binding apply ONLY to events with an audio "
        "component (speech, sounding action). Silent actions are scored for visual and count only.",
        "temporal_relation_satisfaction and constraint_compliance stay SINGLE overall judgments "
        "(not per event). temporal_relation is the between-event timing relation "
        "(synchronization / order / spacing / absolute timing / rhythm / start-stop).",
    ])
    return "\n".join(lines)


def build_temporal_relation_criteria(events: List[dict], temporal_constraint: dict) -> str:
    """Type-specific relation BETWEEN events (no counting; counting is its own sub-axis)."""
    if not temporal_constraint:
        return "- No explicit temporal relation is provided; mark yes if the required target events are not temporally contradictory."

    relation, timing, t_value = temporal_relation_and_timing(temporal_constraint)
    event_desc = ", ".join(describe_event(e) for e in events) if events else "the required target events"
    relation_text = humanize_token(relation or "unspecified")
    timing_text = humanize_token(timing) if timing else "unspecified"

    if relation == "synchronization":
        scheduled = describe_scheduled_events(t_value.get("schedule"), events)
        sync_events = resolve_sequence(t_value.get("events"), events)
        target_desc = " + ".join(sync_events) if sync_events else event_desc
        lines = [
            f"- Relation type: {timing_text} synchronization.",
            f"- Check whether the required target events are synchronized: {target_desc}.",
            "- The target events should be synchronized (occur together / tightly aligned) as required by the prompt.",
        ]
        if scheduled:
            lines.append("- Required absolute synchronized schedule: " + "; ".join(scheduled) + ".")
        mode = clean_text(t_value.get("mode"))
        if mode:
            lines.append(f"- Synchronization mode: {humanize_token(mode)} (judge only the simultaneity here; the number of synchronized co-occurrences is judged by the Temporal Count sub-axis).")
        lines.append("- If the required events are sequential instead of simultaneous, offset, disconnected, missing, or unclear, mark this sub-axis as no.")
        return "\n".join(lines)

    if relation == "order":
        scheduled = describe_scheduled_events(t_value.get("schedule"), events)
        resolved = resolve_sequence(t_value.get("sequence"), events)
        lines = [f"- Relation type: {timing_text} order."]
        if scheduled:
            lines.append("- Required absolute schedule/order: " + " -> ".join(scheduled) + ".")
        elif resolved:
            lines.append("- Required order: " + " -> ".join(resolved) + ".")
        else:
            lines.append("- Required order: the order specified in the original prompt.")
        lines.extend([
            "- The events should occur in the required order according to the prompt.",
            "- If the events begin simultaneously, the order is reversed/mixed, the order cannot be clearly distinguished, or a required event is missing, mark this sub-axis as no.",
        ])
        return "\n".join(lines)

    if relation == "sync_count":
        sync_events = resolve_sequence(t_value.get("events"), events)
        target_desc = " + ".join(sync_events) if sync_events else event_desc
        return "\n".join([
            f"- Relation type: {timing_text} synchronized repetition.",
            f"- Each occurrence of the target bundle must be synchronized (simultaneous/tightly aligned): {target_desc}.",
            "- Judge only synchronization quality here; the number of repetitions is judged by the Temporal Count sub-axis.",
            "- If any occurrence of the bundle is not synchronized when required, or the alignment is unclear, mark this sub-axis as no.",
        ])

    if relation == "count":
        return "\n".join([
            "- Relation type: count only.",
            "- This prompt specifies only how many times the target event occurs; there is no additional ordering or synchronization relation between events.",
            "- Mark this sub-axis yes unless the target occurrences are temporally contradictory or impossible to order; the number of occurrences itself is judged by the Temporal Count sub-axis.",
        ])

    if relation == "rhythm":
        pattern = humanize_token(t_value.get("pattern"))
        return f"""- Relation type: rhythm.
- The target behavior should repeat with the required rhythm: {pattern}.
- If the rhythm is irregular, missing, or unclear, mark this sub-axis as no."""

    if relation == "relative_spacing":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Relation type: relative spacing.
- Apply this spacing requirement: {description}
- If the event spacing is missing, inconsistent, or unclear, mark this sub-axis as no."""

    if relation == "absolute_timing":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Relation type: absolute timing.
- Apply this timing requirement: {description}
- An event satisfies timing when it occurs at about the required timestamp.
- If the event onsets, pauses, or durations fall outside that tolerance or otherwise clearly violate the requirement, mark this sub-axis as no."""

    if relation == "start_stop":
        description = clean_text(t_value.get("description")) or describe_temporal_value(t_value)
        return f"""- Relation type: start/stop.
- Apply this start/stop rule: {description}
- If any required behavior starts too early, ends too late, ignores the trigger, or is unclear, mark this sub-axis as no."""

    return f"""- Relation type: {timing_text} {relation_text}.
- Raw temporal constraint value: {describe_temporal_value(t_value)}
- Apply the temporal rule strictly according to the original generation prompt.
- If the rule is not clearly satisfied, mark this sub-axis as no."""


def build_temporal_count_criteria(events: List[dict], temporal_constraint: dict) -> str:
    """Counting / repetition sub-axis. Applies to ALL temporal types (default exactly once)."""
    relation, _timing, _t_value = temporal_relation_and_timing(temporal_constraint)
    required = required_event_count(events, temporal_constraint)
    count_text = "exactly once" if required is None else f"exactly {required} time(s)"
    bundle = "synchronized bundle" if relation in {"synchronization", "sync_count"} else "target event"

    lines = [
        "- This sub-axis checks the number of occurrences (counting / repetition), independent of the relation type.",
        f"- The required {bundle} should occur {count_text}. Count only clear, completed occurrences.",
        "- A continuously held pose counts as ONE occurrence; releasing and forming it again creates another. Each distinct utterance, sound, contact, or action repetition counts separately.",
        "- Any extra or spurious occurrence of a target action/sound/speech beyond the specified structure makes this sub-axis no.",
        "- This applies to every temporal type: even for order, synchronization, spacing, absolute-timing, rhythm, or start/stop prompts, verify each required event occurs the required number of times (default exactly once) with no extra repetitions, unless the prompt explicitly allows repetition.",
        "- A count/repetition error is scored ONLY here, not double-counted as an extra action under Constraint Compliance.",
        "- If the number of occurrences differs from the requirement, or the count is unclear, mark this sub-axis as no.",
    ]
    return "\n".join(lines)


def build_constraint_compliance_criteria(item_meta: dict) -> str:
    scene_hint = clean_text(item_meta.get("scene_hint"))
    camera_hint = clean_text(item_meta.get("camera_hint"))

    lines = [
        "- Evaluate non-core prompt constraints separately from the main temporal score.",
        "- Check scene, setting, camera, shot type, people count, subtitles/on-screen text, background music, extra sounds, extra speech, extra gestures/actions, and post-event stillness according to the original generation prompt.",
        "- Allowed natural motion that must NOT fail this axis: blinking, breathing, minor posture adjustment, necessary preparation, and natural reset motion.",
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

    return f"""Axis-specific criteria (evaluate in this hierarchical order; a failure cascades downward):

1. Audio Event Correctness
{build_audio_axis_criteria(events)}

2. Visual Event Correctness
{build_visual_axis_criteria(events)}

3. Audio-Visual Binding (WITHIN each event)
{build_av_binding_axis_criteria(events)}

4. Temporal Relation Satisfaction (BETWEEN events)
{build_temporal_relation_criteria(events, temporal_constraint)}
- Precondition: evaluate this sub-axis only when Audio Event Correctness, Visual Event Correctness, and Audio-Visual Binding are all satisfied; otherwise mark it no.

5. Temporal Count Satisfaction (number of occurrences)
{build_temporal_count_criteria(events, temporal_constraint)}
- Precondition: evaluate this sub-axis only when Audio Event Correctness, Visual Event Correctness, and Audio-Visual Binding are all satisfied; otherwise mark it no.

6. Constraint Compliance / Prompt Compliance
{build_constraint_compliance_criteria(item_meta)}
"""


def make_user_text(item_meta: dict, body_pose_section: str = "", audio_evidence_section: str = "") -> str:
    modality = item_meta["modality_combination"]
    generated_prompt = item_meta["generated_prompt"]
    events = item_meta["events"]
    temporal_constraint = item_meta.get("temporal_constraint", {}) or {}
    content = item_meta.get("content", {}) or {}

    event_lines = "\n".join(f"- {describe_event(e)}" for e in events) if events else "- See the original generation prompt."
    body_block = (body_pose_section.strip() + "\n\n") if body_pose_section else ""
    audio_block = (audio_evidence_section.strip() + "\n\n") if audio_evidence_section else ""

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

{build_per_event_instructions(item_meta)}

{GUIDELINE_DEFINITIONS}
{body_block}{audio_block}{build_axis_criteria(item_meta)}

Decision rules:
- audio_event_correctness, visual_event_correctness, and audio_visual_binding are PER-EVENT: return one entry per applicable event_id (see the per-event targets above), each with label "yes"/"no", reason, evidence.
- temporal_count_satisfaction is PER-EVENT: return one entry per event_id with an integer observed_count (the raw number of clear, completed occurrences). The harness compares it to the required count.
- temporal_relation_satisfaction and constraint_compliance are SINGLE overall judgments.
- For a per-event entry, output label "yes" only if that event clearly satisfies the axis.
- If evidence is missing, ambiguous, weak, mismatched, or contradicted for an event, output "no" for that event's entry.
- Apply the hierarchical dependency PER EVENT: an event's Audio-Visual Binding is "no" if that same event's required audio or visual component is incorrect/missing. The harness derives overall temporal success from the per-event labels and counts.
- Do NOT output a combined temporal_constraint_satisfaction; it is derived as relation AND count.
- The generic body-pose evidence, if present, is not an action classifier. It is only low-level auxiliary evidence.
- Constraint Compliance is reported separately as prompt compliance / quality control and is NOT part of overall_temporal_success.
- Keep reasons concise but specific.
- Return the JSON object only.
"""


# ---------------------------------------------------------------------------
# Metadata map construction
# ---------------------------------------------------------------------------
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
    relative_only: bool = False,
) -> Dict[str, dict]:
    out = {}
    item_overrides = item_overrides or {}
    normalized_filter = normalize_modality(modality_filter) if modality_filter is not None else None

    for raw_item in items:
        item = apply_item_overrides(raw_item, item_overrides)
        temporal_constraint = item.get("temporal_constraint", {}) or {}
        timing_type = clean_text(temporal_constraint.get("timing_type")).lower()

        if relative_only and timing_type == "absolute":
            continue

        item_id = clean_text(item.get("item_id"))
        modality = clean_text(item.get("modality_combination"))
        normalized_modality = normalize_modality(modality)
        content = item.get("content", {}) or {}
        temporal_constraint = item.get("temporal_constraint", {}) or {}
        raw_events = item.get("events")

        if not item_id:
            continue
        if normalized_filter is not None and normalized_modality != normalized_filter:
            continue

        events = build_event_list(content, modality, raw_events=raw_events)
        out[item_id] = {
            "item_id": item_id,
            "original_item_id": item_id,
            "label": infer_label_name(events, temporal_constraint),
            "events": events,
            "raw_events": raw_events if isinstance(raw_events, list) else [],
            "modality_combination": modality,
            "normalized_modality_combination": normalized_modality,
            "generated_prompt": clean_text(item.get("generated_prompt") or item.get("prompt")),
            "content": content,
            "temporal_constraint": temporal_constraint,
            "scene_hint": clean_text(item.get("scene_hint")),
            "camera_hint": clean_text(item.get("camera_hint")),
        }

        compact_id = compact_item_id(item_id)
        if compact_id != item_id:
            alias_meta = dict(out[item_id])
            alias_meta["item_id"] = compact_id
            alias_meta["original_item_id"] = item_id
            out[compact_id] = alias_meta
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
    """Tolerant scalar-axis normalizer (used for relation + constraint_compliance).

    On a missing/invalid object, fail closed to "no" with a note rather than
    raising, so a single malformed field does not discard the whole evaluation.
    """
    if not isinstance(obj, dict):
        return {
            "label": "no",
            "reason": f"Model did not return a valid object for {axis_name}; treated as failure.",
            "evidence": "",
        }
    label = clean_text(obj.get("label")).lower()
    if label not in {"yes", "no"}:
        return {
            "label": "no",
            "reason": (clean_text(obj.get("reason"))
                       + f" [Post-processed: invalid label for {axis_name}, treated as no.]").strip(),
            "evidence": clean_text(obj.get("evidence")),
        }
    return {
        "label": label,
        "reason": clean_text(obj.get("reason")),
        "evidence": clean_text(obj.get("evidence")),
    }


def _per_event_entries(raw_axis) -> List[dict]:
    """Return the model's per_event entries as a list. Accepts an object with a
    'per_event' list, a bare list, or (legacy) a scalar axis object."""
    if isinstance(raw_axis, dict):
        entries = raw_axis.get("per_event") or raw_axis.get("events") or []
    elif isinstance(raw_axis, list):
        entries = raw_axis
    else:
        entries = []
    return [e for e in entries if isinstance(e, dict)]


def _norm_key(s: str) -> str:
    return re.sub(r"[\s_]+", " ", clean_text(s)).strip().lower()


def _find_entry(entries: List[dict], se: dict) -> Optional[dict]:
    """Match a model entry to an expected event by event_id, then by label, then
    by event index. Models often key per_event by the human label (e.g.
    'slapping the thigh') or a bare index instead of the canonical 'event_N'."""
    eid = se["event_id"]
    target_label = _norm_key(se["label"])
    target_idx = str(se["index"])
    by_id = {}
    by_label = {}
    by_idx = {}
    for e in entries:
        raw_id = clean_text(e.get("event_id") or e.get("id"))
        nid = _norm_key(raw_id)
        if nid:
            by_id.setdefault(nid, e)
            by_label.setdefault(nid, e)  # raw_id might itself be the label
        digits = re.findall(r"\d+", raw_id)
        if digits:
            by_idx.setdefault(digits[-1], e)
        ev_lbl = _norm_key(e.get("event_label") or e.get("label_name") or "")
        if ev_lbl:
            by_label.setdefault(ev_lbl, e)
    if _norm_key(eid) in by_id:
        return by_id[_norm_key(eid)]
    if target_label and target_label in by_label:
        return by_label[target_label]
    if target_idx in by_idx and len(by_idx) == sum(1 for _ in entries if re.findall(r"\d+", clean_text(_.get("event_id") or _.get("id")))):
        return by_idx[target_idx]
    return None


def _to_int_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+", value)
        if m:
            return int(m.group(0))
    return None


def normalize_label_per_event(raw_axis, expected_events: List[dict], axis_name: str) -> List[dict]:
    """Align yes/no per-event entries to the expected event list."""
    entries = _per_event_entries(raw_axis)
    # Legacy fallback: a single scalar axis object -> apply to all expected events.
    legacy_scalar = None
    if isinstance(raw_axis, dict) and "per_event" not in raw_axis and "events" not in raw_axis and "label" in raw_axis:
        legacy_scalar = clean_text(raw_axis.get("label")).lower()

    out = []
    for se in expected_events:
        eid = se["event_id"]
        got = _find_entry(entries, se)
        if got is None and legacy_scalar in {"yes", "no"}:
            out.append({
                "event_id": eid, "event_kind": se["kind"], "event_label": se["label"],
                "label": legacy_scalar,
                "reason": f"Applied from a single (non per-event) {axis_name} judgment.",
                "evidence": clean_text(raw_axis.get("evidence")),
            })
            continue
        if got is None:
            out.append({
                "event_id": eid, "event_kind": se["kind"], "event_label": se["label"],
                "label": "no",
                "reason": f"Model returned no {axis_name} entry for {eid}; treated as failure.",
                "evidence": "",
            })
            continue
        label = clean_text(got.get("label")).lower()
        if label not in {"yes", "no"}:
            label = "no"
        out.append({
            "event_id": eid, "event_kind": se["kind"], "event_label": se["label"],
            "label": label,
            "reason": clean_text(got.get("reason")),
            "evidence": clean_text(got.get("evidence")),
        })
    return out


def normalize_count_per_event(raw_axis, expected_events: List[dict]) -> List[dict]:
    """Align observed counts to the expected event list and compare to required."""
    entries = _per_event_entries(raw_axis)
    out = []
    for se in expected_events:
        eid = se["event_id"]
        required = se["required_count"]
        got = _find_entry(entries, se)
        observed = _to_int_or_none(got.get("observed_count")) if isinstance(got, dict) else None
        count_correct = (observed is not None and observed == required)
        if got is None:
            reason = f"Model returned no count entry for {eid}; treated as failure."
            evidence = ""
        else:
            reason = clean_text(got.get("reason"))
            evidence = clean_text(got.get("evidence"))
            if observed is None:
                reason = (reason + " [Post-processed: no valid integer observed_count; treated as mismatch.]").strip()
        out.append({
            "event_id": eid, "event_kind": se["kind"], "event_label": se["label"],
            "observed_count": observed,
            "required_count": required,
            "count_correct": count_correct,
            "reason": reason,
            "evidence": evidence,
        })
    return out


def _agg_label(labels: List[str], vacuous: str = "yes") -> str:
    labels = list(labels)
    if not labels:
        return vacuous
    return "yes" if all(l == "yes" for l in labels) else "no"


def _agg_field(per_event: List[dict], field: str) -> str:
    bits = []
    for pe in per_event:
        v = clean_text(pe.get(field))
        if v:
            bits.append(f'{pe["event_id"]} {quote_label(pe.get("event_label", ""))}: {v}')
    return " | ".join(bits)


def _agg_count_field(per_event: List[dict], field: str) -> str:
    bits = []
    for pe in per_event:
        v = clean_text(pe.get(field))
        if v:
            bits.append(f'{pe["event_id"]} {quote_label(pe.get("event_label", ""))}: {v}')
    return " | ".join(bits)


def _count_summary(per_event: List[dict]) -> str:
    bits = []
    for pe in per_event:
        tag = "match" if pe["count_correct"] else "mismatch"
        if not pe.get("count_pass", pe["count_correct"]):
            tag += "/preconditions-failed" if pe["count_correct"] else ""
        bits.append(
            f'{pe["event_id"]} {quote_label(pe.get("event_label", ""))}: '
            f'observed={pe["observed_count"]} required={pe["required_count"]} -> {tag}'
        )
    return " | ".join(bits)


def normalize_result(obj: dict, item_meta: dict) -> dict:
    scoring = build_scoring_events(item_meta)
    audio_events = [s for s in scoring if s["has_audio"]]
    binding_events = [s for s in scoring if s["has_binding"]]
    all_events = scoring

    # --- Per-event yes/no axes ---
    aec_pe = normalize_label_per_event(obj.get("audio_event_correctness"), audio_events, "audio_event_correctness")
    vec_pe = normalize_label_per_event(obj.get("visual_event_correctness"), all_events, "visual_event_correctness")
    avb_pe_raw = normalize_label_per_event(obj.get("audio_visual_binding"), binding_events, "audio_visual_binding")

    aec_map = {pe["event_id"]: pe["label"] for pe in aec_pe}
    vec_map = {pe["event_id"]: pe["label"] for pe in vec_pe}

    # Enforce the per-event AVB precondition: an event's binding requires that
    # same event's audio AND visual to be correct.
    avb_pe = []
    for pe in avb_pe_raw:
        eid = pe["event_id"]
        a = aec_map.get(eid, "no")
        v = vec_map.get(eid, "no")
        if a != "yes" or v != "yes":
            note = " [Precondition failed: this event's audio or visual component is not correct, so binding is not evaluable.]"
            pe = {**pe, "label": "no", "reason": (pe["reason"] + note).strip()}
        avb_pe.append(pe)
    avb_map = {pe["event_id"]: pe["label"] for pe in avb_pe}

    # --- Per-event count axis (with cascade for the pass decision) ---
    count_pe = normalize_count_per_event(obj.get("temporal_count_satisfaction"), all_events)
    for pe in count_pe:
        eid = pe["event_id"]
        kind = pe["event_kind"]
        if kind in {"speech", "sounding_action"}:
            core_ok = (aec_map.get(eid) == "yes" and vec_map.get(eid) == "yes" and avb_map.get(eid) == "yes")
        else:  # silent action: only the visual component gates the count.
            core_ok = (vec_map.get(eid) == "yes")
        pe["preconditions_ok"] = core_ok
        pe["count_pass"] = bool(pe["count_correct"] and core_ok)

    # --- Aggregate per-event arrays into axis-level labels (AND over events) ---
    aec_label = _agg_label([pe["label"] for pe in aec_pe])
    vec_label = _agg_label([pe["label"] for pe in vec_pe])
    avb_label = _agg_label([pe["label"] for pe in avb_pe])
    count_label = _agg_label(["yes" if pe["count_pass"] else "no" for pe in count_pe])

    relation = normalize_axis(obj.get("temporal_relation_satisfaction"), "temporal_relation_satisfaction")
    constraint = normalize_axis(obj.get("constraint_compliance"), "constraint_compliance")

    result: Dict[str, dict] = {}
    result["audio_event_correctness"] = {
        "label": aec_label, "reason": _agg_field(aec_pe, "reason"),
        "evidence": _agg_field(aec_pe, "evidence"), "per_event": aec_pe,
    }
    result["visual_event_correctness"] = {
        "label": vec_label, "reason": _agg_field(vec_pe, "reason"),
        "evidence": _agg_field(vec_pe, "evidence"), "per_event": vec_pe,
    }
    result["audio_visual_binding"] = {
        "label": avb_label, "reason": _agg_field(avb_pe, "reason"),
        "evidence": _agg_field(avb_pe, "evidence"), "per_event": avb_pe,
    }
    result["temporal_count_satisfaction"] = {
        "label": count_label, "reason": _count_summary(count_pe),
        "evidence": _agg_count_field(count_pe, "evidence"), "per_event": count_pe,
    }
    result["temporal_relation_satisfaction"] = relation
    result["constraint_compliance"] = constraint

    # Derive the combined Temporal Constraint Satisfaction = relation AND count.
    tc_label = "yes" if (relation["label"] == "yes" and count_label == "yes") else "no"
    result[DERIVED_TC_KEY] = {
        "label": tc_label,
        "reason": f"Derived = relation AND count (relation={relation['label']}; count={count_label}).",
        "evidence": (
            f"[relation] {relation['evidence']}".strip()
            + (" | " if relation["evidence"] and result["temporal_count_satisfaction"]["evidence"] else "")
            + (f"[count] {result['temporal_count_satisfaction']['evidence']}".strip()
               if result["temporal_count_satisfaction"]["evidence"] else "")
        ).strip(),
    }

    axis_labels = [result[axis]["label"] for axis in CORE_AXIS_KEYS]
    computed_overall = "yes" if all(label == "yes" for label in axis_labels) else "no"

    model_overall = clean_text(obj.get("overall_temporal_success")).lower()
    if model_overall not in {"yes", "no"}:
        model_overall = computed_overall

    result["overall_temporal_success"] = computed_overall
    result["overall_reason"] = clean_text(obj.get("overall_reason"))
    if model_overall != computed_overall:
        result["overall_reason"] = (
            result["overall_reason"]
            + f" [Post-processed: model overall was {model_overall!r}, but the required AND rule gives {computed_overall!r}.]"
        ).strip()
    result["observed_behavior_summary"] = clean_text(obj.get("observed_behavior_summary"))
    return result


def parse_model_json(raw_text: str) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback for rare cases where a model ignores response_mime_type.
        m = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def build_body_pose_section(
    client: genai.Client,
    video_path: Path,
    item_meta: dict,
    pose_evidence_mode: str,
    mediapipe_fps: float,
    mediapipe_model_complexity: int,
    mediapipe_near_threshold_norm: float,
    mediapipe_max_trajectory_samples: int,
    raw_pose_max_frames: int,
    pose_summary_lines: int,
    pose_detail_chars: int,
    focus_planner_model: str,
    focus_planner_thinking_level: Optional[str],
    focus_planner_fallback: bool,
) -> Tuple[str, str]:
    """Return (body_pose_section, error_message). Never raises.

    pose_evidence_mode:
      - none: Gemini-only baseline
      - raw: full raw MediaPipe pose+hand landmark dump, excluding face landmarks
      - focused_raw: Gemini-planned prompt-conditioned subset of raw landmarks

    In focused_raw mode, Gemini is used once as a focus planner. It receives only
    the original prompt, target events, temporal constraint, and the fixed
    MediaPipe landmark catalogs; it returns landmark names only. Python then
    filters the raw landmarks, and the final Gemini call performs the
    visual/temporal judgment.
    """
    if pose_evidence_mode == "none":
        return "", ""

    if pose_evidence_mode == "raw":
        if extract_raw_mediapipe is None or format_raw_mediapipe_as_section is None:
            return "", "Raw MediaPipe evidence requested, but mp_hint.raw_mediapipe imports failed. Check dependencies."
        try:
            raw = extract_raw_mediapipe(
                str(video_path),
                sample_fps=mediapipe_fps,
                model_complexity=mediapipe_model_complexity,
                max_frames=raw_pose_max_frames,
            )
            return format_raw_mediapipe_as_section(raw, max_detail_chars=pose_detail_chars), ""
        except Exception as exc:
            return "", f"{type(exc).__name__}: {exc}"

    if pose_evidence_mode == "focused_raw":
        if extract_focused_raw_mediapipe is None or format_focused_raw_mediapipe_as_section is None:
            return "", "Focused raw MediaPipe evidence requested, but mp_hint.focused_raw_mediapipe imports failed. Check dependencies."
        try:
            focused_raw = extract_focused_raw_mediapipe(
                str(video_path),
                item_meta=item_meta,
                planner_client=client,
                planner_model_name=focus_planner_model,
                planner_thinking_level=focus_planner_thinking_level,
                sample_fps=mediapipe_fps,
                model_complexity=mediapipe_model_complexity,
                max_frames=raw_pose_max_frames,
                allow_planner_fallback=focus_planner_fallback,
            )
            return format_focused_raw_mediapipe_as_section(focused_raw, max_detail_chars=pose_detail_chars), ""
        except Exception as exc:
            return "", f"{type(exc).__name__}: {exc}"

    return "", f"Unknown pose_evidence_mode: {pose_evidence_mode}"

def evaluate_video(
    client: genai.Client,
    model_name: str,
    video_path: Path,
    item_meta: dict,
    media_fps: Optional[float],
    thinking_level: Optional[str],
    timeout_seconds: float,
    pose_evidence_mode: str,
    mediapipe_fps: float,
    mediapipe_model_complexity: int,
    mediapipe_near_threshold_norm: float,
    mediapipe_max_trajectory_samples: int,
    raw_pose_max_frames: int,
    pose_summary_lines: int,
    pose_detail_chars: int,
    focus_planner_model: str,
    focus_planner_thinking_level: Optional[str],
    focus_planner_fallback: bool,
    audio_evidence_mode: str = "none",
    whisper_model_size: str = "large-v3",
    whisper_device: str = "auto",
    whisper_compute_type: str = "auto",
    whisper_language: Optional[str] = None,
    whisper_max_segments: int = 200,
    whisper_detail_chars: int = 8000,
    clap_negative_queries: Optional[List[str]] = None,
    clap_mode: str = "temporal",
    clap_window_seconds: float = 2.0,
    clap_hop_seconds: float = 1.0,
    clap_device: str = "auto",
    clap_max_frames: int = 60,
    clap_detail_chars: int = 8000,
) -> dict:
    # 1. Local body-pose evidence. Failure should never block Gemini eval.
    body_pose_section, mediapipe_error = build_body_pose_section(
        client=client,
        video_path=video_path,
        item_meta=item_meta,
        pose_evidence_mode=pose_evidence_mode,
        mediapipe_fps=mediapipe_fps,
        mediapipe_model_complexity=mediapipe_model_complexity,
        mediapipe_near_threshold_norm=mediapipe_near_threshold_norm,
        mediapipe_max_trajectory_samples=mediapipe_max_trajectory_samples,
        raw_pose_max_frames=raw_pose_max_frames,
        pose_summary_lines=pose_summary_lines,
        pose_detail_chars=pose_detail_chars,
        focus_planner_model=focus_planner_model,
        focus_planner_thinking_level=focus_planner_thinking_level,
        focus_planner_fallback=focus_planner_fallback,
    )
    if mediapipe_error:
        print(f"  [WARN] MediaPipe evidence unavailable for {video_path.name}: {mediapipe_error}")

    # 1b. Audio evidence (Whisper + CLAP). Failure should never block Gemini eval.
    if audio_evidence_mode == "none" or build_audio_evidence_section is None:
        audio_evidence_section, audio_evidence_error = "", ""
        if audio_evidence_mode != "none" and build_audio_evidence_section is None:
            audio_evidence_error = "Audio evidence requested but Tool_Use.audio_evidence import failed."
    else:
        audio_evidence_section, audio_evidence_error = build_audio_evidence_section(
            video_path=video_path,
            item_meta=item_meta,
            audio_evidence_mode=audio_evidence_mode,
            whisper_model_size=whisper_model_size,
            whisper_device=whisper_device,
            whisper_compute_type=whisper_compute_type,
            whisper_language=whisper_language,
            whisper_max_segments=whisper_max_segments,
            whisper_detail_chars=whisper_detail_chars,
            clap_negative_queries=clap_negative_queries,
            clap_mode=clap_mode,
            clap_window_seconds=clap_window_seconds,
            clap_hop_seconds=clap_hop_seconds,
            clap_device=clap_device,
            clap_max_frames=clap_max_frames,
            clap_detail_chars=clap_detail_chars,
        )
    if audio_evidence_error:
        print(f"  [WARN] Audio evidence issue for {video_path.name}: {audio_evidence_error}")

    # 2. Upload video to Gemini.
    uploaded = client.files.upload(file=str(video_path))
    uploaded = wait_until_active(client, uploaded, poll_seconds=5.0, timeout_seconds=timeout_seconds)

    user_text = make_user_text(
        item_meta,
        body_pose_section=body_pose_section,
        audio_evidence_section=audio_evidence_section,
    )

    config_kwargs = {
        "response_mime_type": "application/json",
        "response_json_schema": RESULT_SCHEMA,
        "system_instruction": build_system_prompt(pose_evidence_mode, audio_evidence_mode),
        "temperature": 0.0,
        "seed": 42,
    }

    if thinking_level and thinking_level.lower() != "none":
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)

    if media_fps is not None and media_fps > 0:
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
    parsed = parse_model_json(raw_text)
    result = normalize_result(parsed, item_meta)
    result["raw_output"] = raw_text
    result["uploaded_file_name"] = getattr(uploaded, "name", "")
    result["uploaded_file_uri"] = getattr(uploaded, "uri", "")
    result["user_prompt"] = user_text
    result["pose_evidence_mode"] = pose_evidence_mode
    result["mediapipe_hint_used"] = bool(body_pose_section)
    result["mediapipe_error"] = mediapipe_error
    result["mediapipe_summary"] = body_pose_section
    result["audio_evidence_mode"] = audio_evidence_mode
    result["audio_evidence_used"] = bool(audio_evidence_section)
    result["audio_evidence_error"] = audio_evidence_error
    result["audio_evidence_summary"] = audio_evidence_section
    return result


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------
def ensure_csv_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()


def append_row(csv_path: Path, row: dict) -> None:
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        clean_row = {field: row.get(field, "") for field in CSV_FIELDNAMES}
        writer.writerow(clean_row)


# ---------------------------------------------------------------------------
# Long-format per-event CSV (one row per video x event x per-event axis)
# ---------------------------------------------------------------------------
PER_EVENT_LONG_FIELDNAMES = [
    "video_relpath",
    "video_file",
    "item_id",
    "variant_index",
    "modality_combination",
    "event_id",
    "event_kind",
    "event_label",
    "axis",
    "label",
    "observed_count",
    "required_count",
    "count_correct",
    "preconditions_ok",
    "reason",
    "evidence",
]


def per_event_csv_path(output_csv: Path, override: Optional[Path] = None) -> Path:
    if override is not None:
        return override
    return output_csv.with_name(output_csv.stem + "_per_event" + output_csv.suffix)


def build_per_event_long_rows(row: dict, result: dict) -> List[dict]:
    base = {
        "video_relpath": row.get("video_relpath", ""),
        "video_file": row.get("video_file", ""),
        "item_id": row.get("item_id", ""),
        "variant_index": row.get("variant_index", ""),
        "modality_combination": row.get("modality_combination", ""),
    }
    long_rows: List[dict] = []
    for axis in PER_EVENT_AXIS_KEYS:
        is_count = axis == "temporal_count_satisfaction"
        for pe in result.get(axis, {}).get("per_event", []):
            long_rows.append({
                **base,
                "event_id": pe.get("event_id", ""),
                "event_kind": pe.get("event_kind", ""),
                "event_label": pe.get("event_label", ""),
                "axis": axis,
                # For count rows the pass/fail lives in count_correct / preconditions_ok.
                "label": "" if is_count else pe.get("label", ""),
                "observed_count": pe.get("observed_count", "") if is_count else "",
                "required_count": pe.get("required_count", "") if is_count else "",
                "count_correct": pe.get("count_correct", "") if is_count else "",
                "preconditions_ok": pe.get("preconditions_ok", "") if is_count else "",
                "reason": pe.get("reason", ""),
                "evidence": pe.get("evidence", ""),
            })
    return long_rows


def ensure_per_event_csv_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PER_EVENT_LONG_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()


def append_per_event_rows(csv_path: Path, long_rows: List[dict]) -> None:
    if not long_rows:
        return
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PER_EVENT_LONG_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        for lr in long_rows:
            writer.writerow({field: lr.get(field, "") for field in PER_EVENT_LONG_FIELDNAMES})


def build_success_row_base(
    relpath: str,
    video_path: Path,
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
        "temporal_type": temporal_type_label(item_meta.get("temporal_constraint", {})),
        "model": args.model,
        "media_fps": args.media_fps,
        "thinking_level": args.thinking_level,
        "mediapipe_fps": args.mediapipe_fps,
    }


def add_result_to_row(row: dict, result: dict) -> dict:
    for axis in AXIS_KEYS:
        row[axis] = result[axis]["label"]
        row[f"{axis}_reason"] = result[axis]["reason"]
        row[f"{axis}_evidence"] = result[axis]["evidence"]

    # Per-event breakdown as JSON for the per-event axes.
    for axis in PER_EVENT_AXIS_KEYS:
        per_event = result.get(axis, {}).get("per_event", [])
        row[f"{axis}_per_event"] = json.dumps(per_event, ensure_ascii=False)

    # Stash long-format per-event rows for the auxiliary CSV (not a CSV_FIELDNAMES
    # column, so it is dropped from the wide CSV by append_row).
    row["_per_event_long"] = build_per_event_long_rows(row, result)

    row["overall_temporal_success"] = result["overall_temporal_success"]
    row["overall_reason"] = result["overall_reason"]
    row["observed_behavior_summary"] = result["observed_behavior_summary"]
    row["pose_evidence_mode"] = result.get("pose_evidence_mode", "")
    row["mediapipe_hint_used"] = str(result.get("mediapipe_hint_used", ""))
    row["mediapipe_error"] = result.get("mediapipe_error", "")
    row["mediapipe_summary"] = result.get("mediapipe_summary", "")
    row["audio_evidence_mode"] = result.get("audio_evidence_mode", "")
    row["audio_evidence_used"] = str(result.get("audio_evidence_used", ""))
    row["audio_evidence_error"] = result.get("audio_evidence_error", "")
    row["audio_evidence_summary"] = result.get("audio_evidence_summary", "")
    row["uploaded_file_name"] = result["uploaded_file_name"]
    row["uploaded_file_uri"] = result["uploaded_file_uri"]
    row["user_prompt"] = result["user_prompt"]
    row["raw_output"] = result["raw_output"]
    return row


def add_error_to_row(row: dict, error: Exception, item_meta: dict, body_pose_section: str = "", mediapipe_error: str = "", audio_evidence_section: str = "", audio_evidence_error: str = "", audio_evidence_mode: str = "") -> dict:
    for axis in AXIS_KEYS:
        row[axis] = ""
        row[f"{axis}_reason"] = ""
        row[f"{axis}_evidence"] = ""
    for axis in PER_EVENT_AXIS_KEYS:
        row[f"{axis}_per_event"] = ""
    row["_per_event_long"] = []
    row["overall_temporal_success"] = ""
    row["overall_reason"] = f"ERROR: {type(error).__name__}: {error}"
    row["observed_behavior_summary"] = ""
    row["pose_evidence_mode"] = ""
    row["mediapipe_hint_used"] = str(bool(body_pose_section))
    row["mediapipe_error"] = mediapipe_error
    row["mediapipe_summary"] = body_pose_section
    row["audio_evidence_mode"] = audio_evidence_mode
    row["audio_evidence_used"] = str(bool(audio_evidence_section))
    row["audio_evidence_error"] = audio_evidence_error
    row["audio_evidence_summary"] = audio_evidence_section
    row["uploaded_file_name"] = ""
    row["uploaded_file_uri"] = ""
    row["user_prompt"] = make_user_text(item_meta, body_pose_section=body_pose_section, audio_evidence_section=audio_evidence_section)
    row["raw_output"] = ""
    return row



def compact_item_id(name: str) -> str:
    """Convert long benchmark item IDs to compact output IDs. Idempotent for compact IDs."""
    s = clean_text(name)
    if not s:
        return s

    # Already compact enough; still normalize leftover long tokens below.
    s = s.replace("speech_action_silent_action_sounding", "Sp_Si_So")
    s = s.replace("speech_action_silent", "Sp_Si")
    s = s.replace("speech_action_sounding", "Sp_So")
    s = s.replace("action_silent_action_sounding", "Si_So")

    s = s.replace("absolute", "abs")
    s = s.replace("relative", "rel")
    s = s.replace("synchronization", "sync")
    s = s.replace("order", "ord")
    s = s.replace("count", "cnt")

    s = s.replace("sounding_action", "So")
    s = s.replace("silent_action", "Si")
    s = s.replace("speech", "Sp")
    s = s.replace("_then_", "_")

    # Clean up earlier accidental partial conversions.
    s = s.replace("action_Si_So", "Si_So")
    s = s.replace("action_Si_sounding", "Si_So")
    s = s.replace("Sp_Si_sounding", "Sp_Si_So")
    s = s.replace("Sp_action_Si_action_So", "Sp_Si_So")

    s = re.sub(r"_+", "_", s).strip("_")
    s = re.sub(
        r"_ord_((?:Sp|Si|So)(?:_(?:Sp|Si|So))+)$",
        lambda m: "_ord_" + m.group(1).replace("_", ""),
        s,
    )
    return s


def check_id_map_only(outputs_dir: Path, item_meta_map: Dict[str, dict]) -> None:
    video_files = find_video_files(outputs_dir)
    output_item_ids = sorted({infer_item_id_from_path(p) for p in video_files})
    matched = [x for x in output_item_ids if x in item_meta_map]
    unmatched = [x for x in output_item_ids if x not in item_meta_map]

    print(f"[CHECK] total videos: {len(video_files)}")
    print(f"[CHECK] unique output item IDs: {len(output_item_ids)}")
    print(f"[CHECK] matched item IDs: {len(matched)}")
    print(f"[CHECK] unmatched item IDs: {len(unmatched)}")
    if unmatched:
        print("[CHECK] Unmatched IDs:")
        for item_id in unmatched:
            print(f"  - {item_id}")
    else:
        print("[CHECK] All output item IDs matched prompt metadata.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini 5-axis evaluator with optional open-vocabulary MediaPipe body evidence.")
    parser.add_argument("--prompt-json", type=Path, required=True)
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--model", type=str, default="gemini-3.1-pro-preview")
    parser.add_argument("--output-csv", type=Path, required=True) #.csv
    parser.add_argument("--per-event-csv", type=Path, default=None, help="Optional path for the long-format per-event CSV (one row per video x event x per-event axis). Defaults to <output-csv stem>_per_event.csv. Use --no-per-event-csv to disable.")
    parser.add_argument("--no-per-event-csv", action="store_true", help="Disable writing the long-format per-event CSV.")
    parser.add_argument("--media-fps", type=float, default=24.0, help="FPS metadata passed to Gemini. Use <=0 to omit.")
    parser.add_argument("--thinking-level", type=str, default="high", choices=["low", "high", "none"])
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--overwrite", action="store_true", help="Re-evaluate videos already present in output CSV.")
    parser.add_argument("--modality-filter", type=str, default=None, choices=SUPPORTED_MODALITIES)
    parser.add_argument("--item-overrides-json", type=Path, default=None)
    parser.add_argument("--variant-indices", type=int, nargs="*", default=None, help="Optional list of variant indices to evaluate, e.g. --variant-indices 1 2 3")
    parser.add_argument("--max-videos", type=int, default=None)
    parser.add_argument("--check-id-map-only", action="store_true", help="Only verify that output folder item IDs match prompt metadata; do not call Gemini or write CSV.")
    parser.add_argument("--relative-only", action="store_true", help="Evaluate only items with temporal_constraint.timing_type == 'relative'")

    parser.add_argument("--pose-evidence-mode", type=str, default="none", choices=["none", "raw", "focused_raw"], help="Pose evidence condition: none=Gemini-only, raw=full sampled MediaPipe pose/hand landmarks, focused_raw=Gemini-planned prompt-conditioned subset of raw landmarks.")
    parser.add_argument("--no-mediapipe-hint", action="store_true", help="Backward-compatible alias for --pose-evidence-mode none.")
    parser.add_argument("--mediapipe-fps", type=float, default=8.0, help="Sampling FPS for local MediaPipe evidence extraction.")
    parser.add_argument("--mediapipe-model-complexity", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--mediapipe-near-threshold-norm", type=float, default=0.60, help="Legacy argument kept for compatibility; unused by raw/focused_raw.")
    parser.add_argument("--mediapipe-max-trajectory-samples", type=int, default=12, help="Legacy argument kept for compatibility; unused by raw/focused_raw.")
    parser.add_argument("--raw-pose-max-frames", type=int, default=40, help="For --pose-evidence-mode raw, cap included sampled frames. <=0 means include all sampled frames.")
    parser.add_argument("--pose-summary-lines", type=int, default=80, help="Legacy argument kept for compatibility; unused by raw/focused_raw.")
    parser.add_argument("--pose-detail-chars", type=int, default=24000)
    parser.add_argument("--focus-planner-model", type=str, default=None, help="Gemini model used for the focused_raw landmark-selection planner. Defaults to --model.")
    parser.add_argument("--focus-planner-thinking-level", type=str, default="low", choices=["low", "high", "none"], help="Thinking level for the focused_raw planner call.")
    parser.add_argument("--no-focus-planner-fallback", action="store_true", help="If set, fail focused_raw evidence generation when the planner call fails instead of using a broad fallback subset.")

    # ---------------- Audio evidence (Whisper + CLAP) ----------------
    parser.add_argument("--audio-evidence-mode", type=str, default="none", choices=["none", "whisper", "clap", "both"], help="Audio evidence condition: none=Gemini-only, whisper=ASR transcription only, clap=open-vocab sound-event similarity only, both=Whisper+CLAP.")
    parser.add_argument("--whisper-model-size", type=str, default="large-v3-turbo", help="faster-whisper model size, e.g. tiny, base, small, medium, large-v3, large-v3-turbo.")
    parser.add_argument("--whisper-device", type=str, default="cuda", help="faster-whisper device: auto, cpu, cuda.")
    parser.add_argument("--whisper-compute-type", type=str, default="float16", help="faster-whisper compute_type: auto, int8, int8_float16, float16, float32.")
    parser.add_argument("--whisper-language", type=str, default="en", help="ISO-639-1 language code (e.g. en, ko). Omit for auto-detect.")
    parser.add_argument("--whisper-max-segments", type=int, default=200)
    parser.add_argument("--whisper-detail-chars", type=int, default=4000)
    parser.add_argument("--clap-mode", type=str, default="temporal", choices=["global", "temporal"], help="CLAP scoring mode: global (whole clip) or temporal (sliding window).")
    parser.add_argument("--clap-window-seconds", type=float, default=0.75)
    parser.add_argument("--clap-hop-seconds", type=float, default=0.25)
    parser.add_argument("--clap-device", type=str, default="cuda", help="CLAP device: auto, cpu, cuda.")
    parser.add_argument("--clap-max-frames", type=int, default=60)
    parser.add_argument("--clap-detail-chars", type=int, default=8000)
    parser.add_argument("--clap-negative-queries", type=str, nargs="*", default=None, help="Optional override for CLAP negative anchors. Defaults to silence/background noise/white noise.")

    args = parser.parse_args()
    if args.no_mediapipe_hint:
        args.pose_evidence_mode = "none"
    if args.focus_planner_model is None:
        args.focus_planner_model = args.model

    items = load_prompt_items(args.prompt_json)
    item_overrides = load_json_if_exists(args.item_overrides_json)
    item_meta_map = build_item_meta_map(
        items,
        modality_filter=args.modality_filter,
        item_overrides=item_overrides,
        relative_only=args.relative_only,
    )
    if not item_meta_map:
        raise RuntimeError("No prompt items matched the provided filters.")

    video_files = find_video_files(args.outputs_dir)
    if not video_files:
        raise RuntimeError(f"No mp4 files found under {args.outputs_dir}")

    if args.check_id_map_only:
        check_id_map_only(args.outputs_dir, item_meta_map)
        return

    ensure_csv_header(args.output_csv)

    per_event_csv = None
    if not args.no_per_event_csv:
        per_event_csv = per_event_csv_path(args.output_csv, args.per_event_csv)
        ensure_per_event_csv_header(per_event_csv)
        print(f"[INFO] Per-event long CSV: {per_event_csv}")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    processed = 0
    skipped = 0
    errors = 0

    print(f"[INFO] Loaded {len(item_meta_map)} prompt items")
    print(f"[INFO] Found {len(video_files)} mp4 files under {args.outputs_dir}")
    print(f"[INFO] Output CSV: {args.output_csv}")
    print(f"[INFO] Pose evidence mode: {args.pose_evidence_mode}")
    print(f"[INFO] Audio evidence mode: {args.audio_evidence_mode}")
    if args.pose_evidence_mode == "focused_raw":
        print(f"[INFO] Focus planner model: {args.focus_planner_model} | thinking={args.focus_planner_thinking_level} | fallback={not args.no_focus_planner_fallback}")

    for video_path in video_files:
        relpath = str(video_path.relative_to(args.outputs_dir))
        item_id = infer_item_id_from_path(video_path)
        variant_index = parse_variant_index(video_path.name)

        if args.variant_indices is not None and variant_index not in set(args.variant_indices):
            skipped += 1
            continue

        item_meta = item_meta_map.get(item_id)
        if item_meta is None:
            print(f"[SKIP] No prompt metadata for item_id={item_id} ({relpath})")
            skipped += 1
            continue

        if not args.overwrite and already_done(args.output_csv, relpath):
            print(f"[SKIP] Already evaluated: {relpath}")
            skipped += 1
            continue

        print(f"[EVAL] {relpath}")
        row = build_success_row_base(
            relpath=relpath,
            video_path=video_path,
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
                media_fps=args.media_fps if args.media_fps and args.media_fps > 0 else None,
                thinking_level=args.thinking_level,
                timeout_seconds=args.timeout_seconds,
                pose_evidence_mode=args.pose_evidence_mode,
                mediapipe_fps=args.mediapipe_fps,
                mediapipe_model_complexity=args.mediapipe_model_complexity,
                mediapipe_near_threshold_norm=args.mediapipe_near_threshold_norm,
                mediapipe_max_trajectory_samples=args.mediapipe_max_trajectory_samples,
                raw_pose_max_frames=args.raw_pose_max_frames,
                pose_summary_lines=args.pose_summary_lines,
                pose_detail_chars=args.pose_detail_chars,
                focus_planner_model=args.focus_planner_model,
                focus_planner_thinking_level=args.focus_planner_thinking_level,
                focus_planner_fallback=not args.no_focus_planner_fallback,
                audio_evidence_mode=args.audio_evidence_mode,
                whisper_model_size=args.whisper_model_size,
                whisper_device=args.whisper_device,
                whisper_compute_type=args.whisper_compute_type,
                whisper_language=args.whisper_language,
                whisper_max_segments=args.whisper_max_segments,
                whisper_detail_chars=args.whisper_detail_chars,
                clap_negative_queries=args.clap_negative_queries,
                clap_mode=args.clap_mode,
                clap_window_seconds=args.clap_window_seconds,
                clap_hop_seconds=args.clap_hop_seconds,
                clap_device=args.clap_device,
                clap_max_frames=args.clap_max_frames,
                clap_detail_chars=args.clap_detail_chars,
            )
            row = add_result_to_row(row, result)
            print(f"  -> overall_temporal_success={row['overall_temporal_success']} | pose_mode={row['pose_evidence_mode']} | pose_used={row['mediapipe_hint_used']} | audio_mode={row['audio_evidence_mode']} | audio_used={row['audio_evidence_used']}")
        except Exception as exc:
            errors += 1
            row = add_error_to_row(row, exc, item_meta)
            print(f"  [ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)

        append_row(args.output_csv, row)
        if per_event_csv is not None:
            append_per_event_rows(per_event_csv, row.get("_per_event_long", []))
        processed += 1

        if args.max_videos is not None and processed >= args.max_videos:
            print(f"[INFO] Reached --max-videos={args.max_videos}")
            break

    print(f"[DONE] processed={processed}, skipped={skipped}, errors={errors}, output={args.output_csv}")


if __name__ == "__main__":
    main()
