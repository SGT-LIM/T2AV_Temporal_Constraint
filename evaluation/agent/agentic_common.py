#!/usr/bin/env python3
"""Shared infrastructure for the agentic (per-axis) T2AV evaluator.

This module owns everything that is axis-agnostic:
  - EvalContext: the per-video context passed to every axis evaluator.
  - Evidence generation (MediaPipe / Whisper / CLAP / FLAM) done ONCE per video.
  - Per-axis evidence ROUTING with a per-axis on/off toggle.
  - Per-axis system-prompt / user-text assembly.
  - Per-axis JSON schemas.
  - A single Gemini call wrapper that reuses one uploaded-video handle.

All the heavy lifting (criteria builders, schemas, normalizers) is imported
verbatim from the original single-pass module `new_eval` so the axis semantics
stay identical; only the orchestration changes.
"""

from __future__ import annotations

import csv
import json
import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from google import genai
from google.genai import types

# # `new_eval.py` lives in the sibling `gemini/` directory, not on sys.path by
# # default when this package is run from `evaluation/agent/`. Make it
# # importable without requiring external PYTHONPATH setup.
# _GEMINI_DIR = str(Path(__file__).resolve().parent.parent / "gemini")
# if _GEMINI_DIR not in _sys.path:
#     _sys.path.insert(0, _GEMINI_DIR)

import new_eval as NE  # the original module, reused as a helper library

# Sub-schemas reused as-is.
PER_EVENT_AXIS_SCHEMA = NE.PER_EVENT_AXIS_SCHEMA      # {per_event:[{event_id,label,reason,evidence}]}
PER_EVENT_COUNT_SCHEMA = NE.PER_EVENT_COUNT_SCHEMA    # {per_event:[{event_id,observed_count,...}]}
AXIS_RESULT_SCHEMA = NE.AXIS_RESULT_SCHEMA            # {label,reason,evidence}

# Which evidence family each axis is ALLOWED to see: (use_pose, use_audio).
# The per-axis toggle in EvalContext.use_tools is ANDed on top of this.
#
# Temporal Relation (BETWEEN-event judgment: order/sync/spacing/rhythm/timing)
# and Temporal Count (WITHIN-event judgment: occurrences per event_id) are two
# fully independent axes, each with its own Gemini call, schema, and prompt.
AXIS_EVIDENCE_ROUTE: Dict[str, tuple] = {
    "audio_event_correctness":        (False, True),   # Whisper/CLAP/FLAM only
    "visual_event_correctness":       (True, False),   # MediaPipe only
    "audio_visual_binding":           (True, True),    # both (cross-modal timing)
    "temporal_relation_satisfaction": (True, True),    # both (between-event timing)
    "temporal_count_satisfaction":    (True, True),    # both (per-event counting)
    "constraint_compliance":          (True, True),    # both (detect extra sound/action/people)
}

AXIS_TOGGLE_KEYS = list(AXIS_EVIDENCE_ROUTE.keys())

# ---------------------------------------------------------------------------
# Agentic-pipeline axis bookkeeping (kept local to this package rather than
# reusing new_eval's combined-Temporal constants: new_eval.py's own
# single-call pipeline still derives temporal_constraint_satisfaction =
# relation AND count, but the agentic pipeline keeps Relation and Count as
# two permanently separate final axes and must not resurrect that derived
# field).
# ---------------------------------------------------------------------------

# All final axes that receive label/reason/evidence columns in the CSV.
AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_relation_satisfaction",
    "temporal_count_satisfaction",
    "constraint_compliance",
]

# Axes ANDed into overall_temporal_success. constraint_compliance is excluded.
CORE_AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_relation_satisfaction",
    "temporal_count_satisfaction",
]

# Axes that carry a "per_event" array (JSON column + long-format CSV rows).
PER_EVENT_AXIS_KEYS = [
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_count_satisfaction",
]

# Same as new_eval.CSV_FIELDNAMES but with the derived
# temporal_constraint_satisfaction column trio dropped: Temporal Relation and
# Temporal Count are reported as independent final axes, not combined.
CSV_FIELDNAMES = [f for f in NE.CSV_FIELDNAMES if not f.startswith("temporal_constraint_satisfaction")]

# Long-format per-event CSV columns are already axis-agnostic (no derived
# field baked in), so they are reused as-is.
PER_EVENT_LONG_FIELDNAMES = NE.PER_EVENT_LONG_FIELDNAMES


def ensure_csv_header(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()


def append_row(csv_path: Path, row: dict) -> None:
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        clean_row = {field_name: row.get(field_name, "") for field_name in CSV_FIELDNAMES}
        writer.writerow(clean_row)


def build_per_event_long_rows(row: dict, result: dict) -> List[dict]:
    """One row per (video, event, axis) for A/V/AVB/TC-Count, plus one summary
    row for TC-Relation (a single between-event judgment, not per-event)."""
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

    relation = result.get("temporal_relation_satisfaction", {}) or {}
    long_rows.append({
        **base,
        "event_id": "",
        "event_kind": "",
        "event_label": "",
        "axis": "temporal_relation_satisfaction",
        "label": relation.get("label", ""),
        "observed_count": "",
        "required_count": "",
        "count_correct": "",
        "preconditions_ok": "",
        "reason": relation.get("reason", ""),
        "evidence": relation.get("evidence", ""),
    })
    return long_rows


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
    row["user_prompt"] = NE.make_user_text(item_meta, body_pose_section=body_pose_section, audio_evidence_section=audio_evidence_section)
    row["raw_output"] = ""
    return row


@dataclass
class EvalContext:
    client: genai.Client
    model_name: str
    uploaded: object                      # Gemini File handle, uploaded ONCE, reused per axis
    item_meta: dict

    # Decorated event lists (from build_scoring_events).
    all_events: List[dict]
    audio_events: List[dict]
    binding_events: List[dict]

    # Evidence text, generated once. Keys: "pose", "audio".
    evidence: Dict[str, str]
    # Generation modes that produced the evidence (drives which tool guides the
    # system prompt includes). Keys: "pose", "audio".
    evidence_modes: Dict[str, str]
    # Bookkeeping for the CSV meta columns.
    evidence_meta: Dict[str, str]

    # Per-axis tool on/off. Missing key defaults to True.
    use_tools: Dict[str, bool] = field(default_factory=dict)

    # Call config: thinking_level, media_fps.
    config: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Context construction (evidence built once, video uploaded once)
# ---------------------------------------------------------------------------
def build_context(client: genai.Client, video_path: Path, item_meta: dict, args) -> EvalContext:
    # 1. Local pose evidence. Never blocks evaluation.
    pose_section, pose_error = NE.build_body_pose_section(
        client=client,
        video_path=video_path,
        item_meta=item_meta,
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
    )
    if pose_error:
        print(f"  [WARN] MediaPipe evidence unavailable for {video_path.name}: {pose_error}")

    # 2. Audio evidence (Whisper + CLAP + FLAM). Never blocks evaluation.
    if args.audio_evidence_mode == "none" or NE.build_audio_evidence_section is None:
        audio_section, audio_error = "", ""
        if args.audio_evidence_mode != "none" and NE.build_audio_evidence_section is None:
            audio_error = "Audio evidence requested but Tool_Use.audio_evidence import failed."
    else:
        audio_section, audio_error = NE.build_audio_evidence_section(
            video_path=video_path,
            item_meta=item_meta,
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
            flam_model_name=args.flam_model_name,
            flam_device=args.flam_device,
            flam_ckpt_path=args.flam_ckpt_path,
            flam_method=args.flam_method,
            flam_max_duration_sec=args.flam_max_duration_sec,
            flam_threshold=args.flam_threshold,
            flam_min_duration_sec=args.flam_min_duration_sec,
            flam_merge_gap_sec=args.flam_merge_gap_sec,
            flam_median_filter_size=args.flam_median_filter_size,
            flam_top_k=args.flam_top_k,
            flam_detail_chars=args.flam_detail_chars,
        )
    if audio_error:
        print(f"  [WARN] Audio evidence issue for {video_path.name}: {audio_error}")

    # 3. Upload the video ONCE; reuse the handle across every axis call.
    uploaded = client.files.upload(file=str(video_path))
    uploaded = NE.wait_until_active(client, uploaded, poll_seconds=5.0, timeout_seconds=args.timeout_seconds)

    scoring = NE.build_scoring_events(item_meta)

    # --no-temporal-tools is a backward-compatible alias that disables tools
    # for BOTH Temporal axes; the two dedicated flags control each independently.
    no_temporal_relation_tools = args.no_temporal_relation_tools or args.no_temporal_tools
    no_temporal_count_tools = args.no_temporal_count_tools or args.no_temporal_tools
    use_tools = {
        "audio_event_correctness": not args.no_audio_tools,
        "visual_event_correctness": not args.no_visual_tools,
        "audio_visual_binding": not args.no_binding_tools,
        "temporal_relation_satisfaction": not no_temporal_relation_tools,
        "temporal_count_satisfaction": not no_temporal_count_tools,
        "constraint_compliance": not args.no_compliance_tools,
    }

    return EvalContext(
        client=client,
        model_name=args.model,
        uploaded=uploaded,
        item_meta=item_meta,
        all_events=scoring,
        audio_events=[s for s in scoring if s["has_audio"]],
        binding_events=[s for s in scoring if s["has_binding"]],
        evidence={"pose": pose_section, "audio": audio_section},
        evidence_modes={"pose": args.pose_evidence_mode, "audio": args.audio_evidence_mode},
        evidence_meta={
            "pose_evidence_mode": args.pose_evidence_mode,
            "pose_error": pose_error,
            "pose_summary": pose_section,
            "audio_evidence_mode": args.audio_evidence_mode,
            "audio_error": audio_error,
            "audio_summary": audio_section,
        },
        use_tools=use_tools,
        config={"thinking_level": args.thinking_level, "media_fps": args.media_fps},
    )


# ---------------------------------------------------------------------------
# Evidence routing + prompt assembly
# ---------------------------------------------------------------------------
def routed_evidence(ctx: EvalContext, axis: str):
    """Return (pose_text, audio_text, use_pose, use_audio) for this axis."""
    use_pose, use_audio = AXIS_EVIDENCE_ROUTE[axis]
    if not ctx.use_tools.get(axis, True):
        use_pose = use_audio = False
    pose = ctx.evidence.get("pose", "") if use_pose else ""
    audio = ctx.evidence.get("audio", "") if use_audio else ""
    return pose, audio, use_pose, use_audio


def axis_system_prompt(ctx: EvalContext, axis: str) -> str:
    """System prompt whose tool guides match the evidence actually routed here."""
    _, _, use_pose, use_audio = routed_evidence(ctx, axis)
    pose_mode = ctx.evidence_modes["pose"] if use_pose else "none"
    audio_mode = ctx.evidence_modes["audio"] if use_audio else "none"
    return NE.build_system_prompt(pose_mode, audio_mode)


def build_axis_header(item_meta: dict) -> str:
    """Shared top block: prompt, metadata, target events, per-event targets, defs.

    Mirrors the header portion of new_eval.make_user_text, minus evidence and
    minus the (all-axis) criteria block.
    """
    modality = item_meta["modality_combination"]
    generated_prompt = item_meta["generated_prompt"]
    events = item_meta["events"]
    temporal_constraint = item_meta.get("temporal_constraint", {}) or {}
    content = item_meta.get("content", {}) or {}
    event_lines = "\n".join(f"- {NE.describe_event(e)}" for e in events) if events else "- See the original generation prompt."

    return f"""Original generation prompt:
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

{NE.build_per_event_instructions(item_meta)}

{NE.GUIDELINE_DEFINITIONS}"""


def build_axis_user_text(
    ctx: EvalContext,
    axis: str,
    criteria_text: str,
    decision_rules: str,
    only_event_ids: Optional[List[str]] = None,
) -> str:
    header = build_axis_header(ctx.item_meta)
    pose, audio, _, _ = routed_evidence(ctx, axis)
    pose_block = (pose.strip() + "\n\n") if pose else ""
    audio_block = (audio.strip() + "\n\n") if audio else ""
    scope = ""
    if only_event_ids is not None:
        scope = "Score ONLY these event_ids for this axis: " + ", ".join(only_event_ids) + ".\n\n"

    return f"""Task: Evaluate exactly ONE axis of this generated video: {axis}.
Judge only this axis. Other axes are handled by separate calls.

{header}

{pose_block}{audio_block}Axis criteria for {axis}:
{criteria_text}

{scope}Decision rules:
{decision_rules}
- Be conservative: unclear, weak, ambiguous, incomplete, or mismatched evidence is a failure.
- Return the JSON object only.
"""


def call_gemini_json(ctx: EvalContext, system_prompt: str, user_text: str, schema: dict):
    """Single structured-JSON Gemini call reusing the shared uploaded video."""
    config_kwargs = {
        "response_mime_type": "application/json",
        "response_json_schema": schema,
        "system_instruction": system_prompt,
        "temperature": 0.0,
        "seed": 42,
    }
    tl = ctx.config.get("thinking_level")
    if tl and str(tl).lower() != "none":
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=tl)

    media_fps = ctx.config.get("media_fps")
    if media_fps and media_fps > 0:
        contents = [
            types.Part(
                file_data=types.FileData(file_uri=ctx.uploaded.uri, mime_type=ctx.uploaded.mime_type),
                video_metadata=types.VideoMetadata(fps=media_fps),
            ),
            user_text,
        ]
    else:
        contents = [ctx.uploaded, user_text]

    response = ctx.client.models.generate_content(
        model=ctx.model_name,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    raw = response.text or ""
    return NE.parse_model_json(raw), raw
