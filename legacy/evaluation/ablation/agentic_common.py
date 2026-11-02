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

# Which evidence family each axis is ALLOWED to see:
# (use_pose, use_audio, use_caption).
# The per-axis toggle in EvalContext.use_tools is ANDed on top of this.
#
# The dense caption is inherently audio-visual, so it routes to EVERY axis by
# default; the caption-vs-tools comparison is then controlled per axis by the
# evidence mode flags, not by asymmetric routing.
#
# Temporal Relation (BETWEEN-event judgment: order/sync/spacing/rhythm/timing)
# and Temporal Count (WITHIN-event judgment: occurrences per event_id) are two
# fully independent axes, each with its own Gemini call, schema, and prompt.
AXIS_EVIDENCE_ROUTE: Dict[str, tuple] = {
    "audio_event_correctness":        (False, True, False),  # Whisper/CLAP/FLAM only; caption is visual-track evidence (2026-09-24)
    "visual_event_correctness":       (True, False, True),   # MediaPipe (+caption)
    "audio_visual_binding":           (True, True, True),    # both (cross-modal timing)
    "temporal_relation_satisfaction": (True, True, True),    # both (between-event timing)
    "temporal_count_satisfaction":    (True, True, True),    # both (per-event counting)
    "constraint_compliance":          (False, False, False), # not scored; no evidence (2026-09-24)
}

AXIS_TOGGLE_KEYS = list(AXIS_EVIDENCE_ROUTE.keys())

# Structured event time (10/30, generated block). Off unless T2AV_EVENT_TIME_FIELD=1: then the V and AVB
# per-event schemas gain a nullable `event_time_s` and one rule line asks for it. The value is read back
# from raw_output; label normalization is unchanged. Used for the Synchformer anchor-time window.
EVENT_TIME_FIELD = __import__("os").environ.get("T2AV_EVENT_TIME_FIELD", "0") == "1"
EVENT_TIME_RULE = (
    "\n- Also return event_time_s for each event: the time in seconds from the start of the video at which the "
    "event's visible action begins, as you observed it; null if you did not observe the action."
)


def per_event_schema_with_time(schema: dict) -> dict:
    if not EVENT_TIME_FIELD:
        return schema
    item = json.loads(json.dumps(schema["properties"]["per_event"]["items"]))
    item["properties"]["event_time_s"] = {"type": "number", "nullable": True}
    item["required"] = list(item["required"]) + ["event_time_s"]
    return {**schema, "properties": {"per_event": {"type": "array", "items": item}}}

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

# Caption evidence bookkeeping columns (inserted right after the audio
# evidence meta block so the provenance columns stay grouped).
_CAPTION_META_FIELDS = [
    "caption_evidence_mode",
    "caption_evidence_used",
    "caption_evidence_error",
    "caption_evidence_summary",
]
if "caption_evidence_mode" not in CSV_FIELDNAMES:
    _anchor = (CSV_FIELDNAMES.index("audio_evidence_summary") + 1
               if "audio_evidence_summary" in CSV_FIELDNAMES else len(CSV_FIELDNAMES))
    CSV_FIELDNAMES = CSV_FIELDNAMES[:_anchor] + _CAPTION_META_FIELDS + CSV_FIELDNAMES[_anchor:]

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
    row["caption_evidence_mode"] = result.get("caption_evidence_mode", "")
    row["caption_evidence_used"] = str(result.get("caption_evidence_used", ""))
    row["caption_evidence_error"] = result.get("caption_evidence_error", "")
    row["caption_evidence_summary"] = result.get("caption_evidence_summary", "")
    row["uploaded_file_name"] = result["uploaded_file_name"]
    row["uploaded_file_uri"] = result.get("media_provenance") or result["uploaded_file_uri"]
    row["user_prompt"] = result["user_prompt"]
    row["raw_output"] = result["raw_output"]
    return row


def add_error_to_row(row: dict, error: Exception, item_meta: dict, body_pose_section: str = "", mediapipe_error: str = "", audio_evidence_section: str = "", audio_evidence_error: str = "", audio_evidence_mode: str = "", caption_evidence_section: str = "", caption_evidence_error: str = "", caption_evidence_mode: str = "") -> dict:
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
    row["caption_evidence_mode"] = caption_evidence_mode
    row["caption_evidence_used"] = str(bool(caption_evidence_section))
    row["caption_evidence_error"] = caption_evidence_error
    row["caption_evidence_summary"] = caption_evidence_section
    row["uploaded_file_name"] = ""
    row["uploaded_file_uri"] = ""
    row["user_prompt"] = NE.make_user_text(item_meta, body_pose_section=body_pose_section, audio_evidence_section=audio_evidence_section)
    row["raw_output"] = ""
    return row


# ---------------------------------------------------------------------------
# Media input modes (input-modality ablation for the Audio axis)
# ---------------------------------------------------------------------------
# "video"         : (default) upload the full video; identical to before.
# "audio_only"    : upload ONLY the extracted audio track. Blocks Gemini's
#                   visual dominance on the Audio axis. A-axis only.
# "language_only" : upload NOTHING. The judge sees only the tool-output text
#                   (Whisper/FLAM) plus prompt/metadata. Measures how far the
#                   expert signals alone go, with no judge-captioner
#                   independence concern. A-axis only.
MEDIA_INPUT_MODES = ["video", "audio_only", "language_only"]

MEDIA_INPUT_NOTES_CAPTION_ONLY = (
    "MEDIA INPUT NOTE: For this call you are given NO video and NO audio. The ONLY "
    "observation available is the dense video caption included in the user message, "
    "produced by a separate captioning model over the same video. Base your judgment "
    "SOLELY on that caption text plus the prompt/metadata. If any evidence-section "
    "boilerplate tells you to verify against the video itself, ignore it: no video is "
    "provided, so the caption text is the final observation. If the caption does not "
    "clearly support an event's required visual component, judge that event as failure."
)

MEDIA_INPUT_NOTES = {
    "audio_only": (
        "MEDIA INPUT NOTE: For this call you are given ONLY the AUDIO TRACK of the "
        "generated video (no visual frames). Wherever the instructions refer to the "
        "video, apply them to this audio track. Judge ONLY the audio components of "
        "each event; do NOT attempt to infer or judge any visual component."
    ),
    "language_only": (
        "MEDIA INPUT NOTE: For this call you are given NO video and NO audio. The ONLY "
        "observation available is the tool-output evidence text included in the user "
        "message (e.g., Whisper ASR transcription and OpenFLAM sound-event detections). "
        "Base your judgment SOLELY on that evidence text plus the prompt/metadata. If "
        "any evidence-section boilerplate tells you to defer to the audio itself, ignore "
        "it: no audio is provided, so the evidence text is the final observation. If the "
        "evidence text does not clearly support an event's required audio component, "
        "judge that event as failure."
    ),
}


def _select_media_note(cfg) -> str:
    """language_only + external caption (caption-only V) -> caption note; else per-mode note."""
    mode = cfg.get("media_input_mode", "video") or "video"
    cap_mode = cfg.get("caption_evidence_mode", "none") or "none"
    has_cap = cap_mode == "external" or bool(cfg.get("caption_external_json"))
    if mode == "language_only" and has_cap:
        return MEDIA_INPUT_NOTES_CAPTION_ONLY
    return MEDIA_INPUT_NOTES.get(mode, "")


def extract_audio_only_file(video_path: Path, cache_dir: Optional[Path]) -> Path:
    """Extract the audio track of `video_path` into `cache_dir` and return the path.

    Always re-encodes to 16-bit PCM .wav: the Gemini Developer API's supported
    audio formats are WAV/MP3/AIFF/AAC/OGG/FLAC, and uploading an .m4a
    (audio/mp4 container) can fail with an opaque 403 PERMISSION_DENIED.
    Results are cached keyed by absolute path + mtime, so resumed runs skip
    re-extraction.
    """
    import hashlib
    import shutil as _shutil
    import subprocess as _subprocess

    if _shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH; required for --media-input-mode audio_only.")

    cache_dir = Path(cache_dir) if cache_dir else Path("audio_only_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.md5(
        f"{video_path.resolve()}|{video_path.stat().st_mtime_ns}".encode("utf-8")
    ).hexdigest()[:10]
    wav_path = cache_dir / f"{video_path.stem}_{tag}.wav"

    if wav_path.exists() and wav_path.stat().st_size > 0:
        return wav_path

    _subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
         "-vn", "-acodec", "pcm_s16le", str(wav_path)],
        check=True,
    )
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise RuntimeError(f"Audio extraction produced an empty file for {video_path}")
    return wav_path


AUDIO_UPLOAD_MIME = {".wav": "audio/wav"}


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

    # Evidence text, generated once. Keys: "pose", "audio", "caption".
    evidence: Dict[str, str]
    # Generation modes that produced the evidence (drives which tool guides the
    # system prompt includes). Keys: "pose", "audio", "caption". The caption
    # guide travels inside its own evidence section, so the system prompt only
    # consumes the pose/audio modes.
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
            flam_hop_sec=args.flam_hop_sec,
            flam_threshold=args.flam_threshold,
            flam_min_duration_sec=args.flam_min_duration_sec,
            flam_merge_gap_sec=args.flam_merge_gap_sec,
            flam_median_filter_size=args.flam_median_filter_size,
            flam_top_k=args.flam_top_k,
            flam_detail_chars=args.flam_detail_chars,
        )
    if audio_error:
        print(f"  [WARN] Audio evidence issue for {video_path.name}: {audio_error}")

    # language_only sanity guard: the evidence text is the judge's ONLY
    # observation, so an empty section must be a hard error, never a silent
    # structural "no".
    _media_input_mode_early = getattr(args, "media_input_mode", "video") or "video"
    _caption_mode_early = getattr(args, "caption_evidence_mode", "none") or "none"
    if _media_input_mode_early == "language_only" and not audio_section and _caption_mode_early in (None, "", "none"):
        raise RuntimeError(
            "language_only requires a non-empty audio evidence section but got none"
            + (f" (audio evidence error: {audio_error})" if audio_error else "")
        )

    # 3. Upload the media ONCE; reuse the handle across every axis call
    #    (including the captioning call, which is why captioning runs after
    #    the upload). What gets uploaded depends on --media-input-mode:
    #      video         -> the full video (default, unchanged behavior)
    #      audio_only    -> the extracted audio track only
    #      language_only -> nothing; the judge sees only tool-output text
    media_input_mode = getattr(args, "media_input_mode", "video") or "video"
    audio_only_path = None
    if media_input_mode == "language_only":
        uploaded = None
    elif media_input_mode == "audio_only":
        # Inline the wav bytes into each request instead of going through the
        # Files API (which returned opaque 403 PERMISSION_DENIED for audio
        # uploads on some keys). Inline request limit is ~20MB; short clips
        # are well under that.
        audio_path = extract_audio_only_file(video_path, getattr(args, "audio_cache_dir", None))
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb > 18:
            raise RuntimeError(
                f"Extracted wav is {size_mb:.1f}MB (> inline limit); "
                f"downsample or shorten {audio_path}."
            )
        uploaded = None
        audio_only_path = str(audio_path)
    elif (getattr(args, "judge_backend", "gemini") or "gemini") in ("openai", "local"):
        # openai: frames extracted lazily in openai_judge. local: the server reads the file path itself.
        uploaded = None  # judge_backend_local_patched
    else:
        uploaded = NE.upload_and_wait(client, video_path, poll_seconds=5.0, timeout_seconds=args.timeout_seconds)

    # 4. Dense-caption evidence (separate captioning pass or precomputed file).
    #    Never blocks evaluation.
    caption_mode = getattr(args, "caption_evidence_mode", "none")
    if caption_mode not in (None, "", "none") and media_input_mode != "video" and not (
            media_input_mode == "language_only" and caption_mode == "external"):
        raise RuntimeError(
            f"--caption-evidence-mode {caption_mode} requires --media-input-mode video "
            f"(got {media_input_mode}); captions are visual-track evidence."
        )
    if (getattr(args, "judge_backend", "gemini") or "gemini") in ("openai", "local") and caption_mode not in (None, "", "none", "external"):
        raise RuntimeError("--judge-backend openai/local supports only --caption-evidence-mode external (precomputed captions).")
    if caption_mode in (None, "", "none"):
        caption_section, caption_error = "", ""
    else:
        import caption_evidence as CE
        caption_section, caption_error = CE.build_caption_evidence_section(
            client=client,
            uploaded=uploaded,
            video_path=video_path,
            mode=caption_mode,
            caption_model=getattr(args, "caption_model", "") or args.model,
            caption_style=getattr(args, "caption_style", "timestamped"),
            cache_dir=getattr(args, "caption_cache_dir", None),
            external_json=getattr(args, "caption_external_json", None),
            videos_root=getattr(args, "outputs_dir", None),
            detail_chars=getattr(args, "caption_detail_chars", 8000),
            media_fps=args.media_fps,
        )
    if caption_error:
        print(f"  [WARN] Caption evidence issue for {video_path.name}: {caption_error}")
    # caption-only V: the caption text is the judge's ONLY observation -> empty must be a hard error
    if media_input_mode == "language_only" and not audio_section and not caption_section:
        raise RuntimeError("language_only with caption evidence requires a non-empty caption section but got none"
                           + (f" (caption error: {caption_error})" if caption_error else ""))

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
        evidence={"pose": pose_section, "audio": audio_section, "caption": caption_section,
                  "sync": sync_section(video_path)},
        evidence_modes={"pose": args.pose_evidence_mode, "audio": args.audio_evidence_mode,
                        "caption": caption_mode},
        evidence_meta={
            "pose_evidence_mode": args.pose_evidence_mode,
            "pose_error": pose_error,
            "pose_summary": pose_section,
            "audio_evidence_mode": args.audio_evidence_mode,
            "audio_error": audio_error,
            "audio_summary": audio_section,
            "caption_evidence_mode": caption_mode,
            "caption_error": caption_error,
            "caption_summary": caption_section,
        },
        use_tools=use_tools,
        config={"thinking_level": args.thinking_level, "media_fps": args.media_fps,
                "caption_evidence_mode": getattr(args, "caption_evidence_mode", "none") or "none",
                "axes": getattr(args, "axes", "all"),
                "media_input_mode": media_input_mode,
                "audio_only_path": audio_only_path,
                "judge_backend": getattr(args, "judge_backend", "gemini") or "gemini",
                "video_path": str(video_path),
                "frame_fps": getattr(args, "frame_fps", 8),
                "frame_cache_dir": getattr(args, "frame_cache_dir", None),
                "frame_detail": getattr(args, "frame_detail", "low"),  # astra_patched
                "openai_reasoning_effort": getattr(args, "openai_reasoning_effort", "low"),
                "local_judge_url": getattr(args, "local_judge_url", None)},
    )


# ---------------------------------------------------------------------------
# Evidence routing + prompt assembly
# ---------------------------------------------------------------------------
# Row 2 / 2b (10/30): Synchformer reading as one more tool section. Off unless T2AV_SYNC_EVIDENCE_JSON points to a
# {resolved video path: section text} map (built by gepa_stage2/sync_gen_1030.py from the anchor-time-window pass).
# The section is appended to the audio evidence of the axes that see both modalities' timing (AVB, TCR, TCC).
SYNC_AXES = ("audio_visual_binding", "temporal_relation_satisfaction", "temporal_count_satisfaction")
_SYNC_MAP = None


def sync_section(video_path) -> str:
    global _SYNC_MAP
    p = __import__("os").environ.get("T2AV_SYNC_EVIDENCE_JSON")
    if not p:
        return ""
    if _SYNC_MAP is None:
        _SYNC_MAP = json.load(open(p))
    return _SYNC_MAP.get(str(Path(video_path).resolve()), "")


def routed_evidence(ctx: EvalContext, axis: str):
    """Return (pose_text, audio_text, caption_text, use_pose, use_audio, use_caption)."""
    use_pose, use_audio, use_caption = AXIS_EVIDENCE_ROUTE[axis]
    if not ctx.use_tools.get(axis, True):
        use_pose = use_audio = use_caption = False
    pose = ctx.evidence.get("pose", "") if use_pose else ""
    audio = ctx.evidence.get("audio", "") if use_audio else ""
    if use_audio and axis in SYNC_AXES and ctx.evidence.get("sync"):
        audio = (audio + "\n\n" + ctx.evidence["sync"]).strip()
    caption = ctx.evidence.get("caption", "") if use_caption else ""
    return pose, audio, caption, use_pose, use_audio, use_caption


def axis_system_prompt(ctx: EvalContext, axis: str) -> str:
    """System prompt whose tool guides match the evidence actually routed here.

    Pose/audio/caption modes all feed new_eval.build_system_prompt; the caption
    evidence-use policy (CAPTION_GENERAL_GUIDE) is injected whenever caption
    evidence is routed to this axis, mirroring the Whisper/FLAM guides.
    """
    _, _, _, use_pose, use_audio, use_caption = routed_evidence(ctx, axis)
    pose_mode = ctx.evidence_modes["pose"] if use_pose else "none"
    audio_mode = ctx.evidence_modes["audio"] if use_audio else "none"
    caption_mode = ctx.evidence_modes.get("caption", "none") if use_caption else "none"
    prompt = NE.build_system_prompt(pose_mode, audio_mode, caption_mode, single_axis=True)
    # caption-only V: the video-vs-caption weighing policy makes no sense without a video;
    # swap it for the caption-only policy (video+caption runs are untouched).
    cfg = ctx.config
    if (cfg.get("media_input_mode", "video") or "video") == "language_only" and \
            (cfg.get("caption_evidence_mode", "none") or "none") == "external" and caption_mode != "none":
        if NE.CAPTION_GENERAL_GUIDE in prompt:
            prompt = prompt.replace(NE.CAPTION_GENERAL_GUIDE, NE.CAPTION_ONLY_GUIDE)
        else:
            print("  [WARN] caption-only: CAPTION_GENERAL_GUIDE not found in system prompt; guide not swapped")
    # GEPA hook: replace the caption evidence-use policy with the candidate text.
    _ov = cfg.get("caption_guide_override")
    if _ov and caption_mode != "none":
        if NE.CAPTION_GENERAL_GUIDE in prompt:
            prompt = prompt.replace(NE.CAPTION_GENERAL_GUIDE, _ov)
        elif NE.CAPTION_ONLY_GUIDE in prompt:
            prompt = prompt.replace(NE.CAPTION_ONLY_GUIDE, _ov)
        else:
            print("  [WARN] caption_guide_override set but no caption guide found in prompt")
    media_note = _select_media_note(ctx.config)
    if media_note:
        prompt = media_note + "\n\n" + prompt
    return prompt


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
    pose, audio, caption, _, _, _ = routed_evidence(ctx, axis)
    pose_block = (pose.strip() + "\n\n") if pose else ""
    audio_block = (audio.strip() + "\n\n") if audio else ""
    caption_block = (caption.strip() + "\n\n") if caption else ""
    scope = ""
    if only_event_ids is not None:
        scope = "Score ONLY these event_ids for this axis: " + ", ".join(only_event_ids) + ".\n\n"

    media_note = _select_media_note(ctx.config)
    media_note_block = (media_note + "\n\n") if media_note else ""

    return f"""Task: Evaluate exactly ONE axis of this generated video: {axis}.
Judge only this axis. Other axes are handled by separate calls.

{media_note_block}{header}

{pose_block}{audio_block}{caption_block}Axis criteria for {axis}:
{criteria_text}

{scope}Decision rules:
{decision_rules}
- Be conservative: unclear, weak, ambiguous, incomplete, or mismatched evidence is a failure.
- Return the JSON object only.
"""


def call_gemini_json(ctx: EvalContext, system_prompt: str, user_text: str, schema: dict):
    """Single structured-JSON Gemini call reusing the shared uploaded video."""
    if (ctx.config.get("judge_backend") or "gemini") == "openai":
        import openai_judge as OJ
        return OJ.call_openai_json(ctx, system_prompt, user_text, schema)
    if (ctx.config.get("judge_backend") or "gemini") == "local":
        import local_judge as LJ
        return LJ.call_local_json(ctx, system_prompt, user_text, schema)
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

    media_input_mode = ctx.config.get("media_input_mode", "video")
    media_fps = ctx.config.get("media_fps")

    if media_input_mode == "language_only":
        # language_only: no media part at all; the judge sees only text.
        contents = [user_text]
    elif media_input_mode == "audio_only":
        # audio_only: inline the extracted wav bytes (no Files API involvement,
        # no VideoMetadata which is a video-only field).
        audio_only_path = ctx.config.get("audio_only_path")
        if not audio_only_path:
            raise RuntimeError("audio_only mode but no extracted audio path in ctx.config.")
        audio_bytes = Path(audio_only_path).read_bytes()
        contents = [
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            user_text,
        ]
    elif ctx.uploaded is None:
        contents = [user_text]
    elif media_fps and media_fps > 0:
        contents = [
            types.Part(
                file_data=types.FileData(file_uri=ctx.uploaded.uri, mime_type=ctx.uploaded.mime_type),
                video_metadata=types.VideoMetadata(fps=media_fps),
            ),
            user_text,
        ]
    else:
        contents = [ctx.uploaded, user_text]

    # Per-call retry on transient API errors (503 high demand, 429 rate limit, 500).
    # Retrying here, instead of re-running the whole video in run_agentic_eval,
    # avoids redoing every earlier axis call when only the last one failed.
    import time
    from google.genai import errors as genai_errors
    delays = [30, 60, 120]
    for attempt in range(len(delays) + 1):
        try:
            response = ctx.client.models.generate_content(
                model=ctx.model_name,
                contents=contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            break
        except (genai_errors.ServerError, genai_errors.ClientError) as e:
            code = getattr(e, "code", None)
            transient = isinstance(e, genai_errors.ServerError) or code in (429, 500, 503)
            if not transient or attempt == len(delays):
                raise
            print(f"    [RETRY {attempt + 1}/{len(delays)}] {type(e).__name__} {code}: retrying this call in {delays[attempt]}s", flush=True)
            time.sleep(delays[attempt])
    raw = response.text or ""
    return NE.parse_model_json(raw), raw
