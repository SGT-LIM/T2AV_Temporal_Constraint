# Replaced by t2av_eval/evidence/audio/section.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""
Dispatcher that builds the audio-evidence text section for Gemini.

Mirrors the design of build_body_pose_section in the main evaluator:
  - Never raises; returns (audio_evidence_section, error_message).
  - Selects between Whisper-only, CLAP-only, or both based on mode.
  - CLAP queries are auto-derived from item_meta unless explicitly supplied.

Modes:
  - none    : no audio evidence
  - whisper : Whisper ASR only (speech transcription)
  - clap    : CLAP sound-event only
  - both    : Whisper + CLAP concatenated
  - flam    : OpenFLAM frame-wise sound-event localization only
  - whisper_flam : Whisper + OpenFLAM concatenated
  - clap_flam    : CLAP + OpenFLAM concatenated
  - all     : Whisper + CLAP + OpenFLAM concatenated
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

try:
    from .whisper_audio import extract_whisper_evidence, format_whisper_as_section
except Exception:  # pragma: no cover
    extract_whisper_evidence = None
    format_whisper_as_section = None

try:
    from .clap_audio import (
        extract_clap_evidence,
        format_clap_as_section,
        derive_queries_from_item_meta,
        DEFAULT_NEGATIVE_QUERIES,
    )
except Exception:  # pragma: no cover
    extract_clap_evidence = None
    format_clap_as_section = None
    derive_queries_from_item_meta = None
    DEFAULT_NEGATIVE_QUERIES = []

try:
    from .flam_audio import (
        extract_flam_evidence,
        format_flam_as_section,
        derive_queries_from_item_meta as derive_flam_queries_from_item_meta,
    )
except Exception:  # pragma: no cover
    extract_flam_evidence = None
    format_flam_as_section = None
    derive_flam_queries_from_item_meta = None


def build_audio_evidence_section(
    video_path,
    item_meta: Dict,
    audio_evidence_mode: str,
    # Whisper params
    whisper_model_size: str = "large-v3",
    whisper_device: str = "auto",
    whisper_compute_type: str = "auto",
    whisper_language: Optional[str] = None,
    whisper_max_segments: int = 200,
    whisper_detail_chars: int = 8000,
    # CLAP params
    clap_queries: Optional[List[str]] = None,
    clap_negative_queries: Optional[List[str]] = None,
    clap_mode: str = "temporal",
    clap_window_seconds: float = 2.0,
    clap_hop_seconds: float = 1.0,
    clap_device: str = "auto",
    clap_max_frames: int = 60,
    clap_detail_chars: int = 8000,
    # OpenFLAM params
    flam_queries: Optional[List[str]] = None,
    flam_model_name: str = "v1-base",
    flam_device: str = "auto",
    flam_ckpt_path: str = "/tmp/openflam",
    flam_method: str = "unbiased",
    flam_max_duration_sec: float = 10.0,
    flam_hop_sec: float = 0.0,
    flam_threshold: float = 0.98,
    flam_min_duration_sec: float = 0.05,
    flam_merge_gap_sec: float = 0.10,
    flam_median_filter_size: int = 3,
    flam_top_k: int = 5,
    flam_detail_chars: int = 8000,
) -> Tuple[str, str]:
    """Build the audio-evidence text section. Never raises.

    Returns
    -------
    (audio_evidence_section, error_message)
        Empty section + empty error  -> mode=='none', clean.
        Empty section + non-empty err -> tool failed; main caller logs and proceeds.
        Non-empty section + non-empty err -> partial success (e.g. Whisper OK, CLAP failed).
    """
    if audio_evidence_mode == "none":
        return "", ""

    parts: List[str] = []
    errs: List[str] = []

    do_whisper = audio_evidence_mode in {"whisper", "both", "whisper_flam", "all"}
    do_clap = audio_evidence_mode in {"clap", "both", "clap_flam", "all"}
    do_flam = audio_evidence_mode in {"flam", "whisper_flam", "clap_flam", "all"}

    if do_whisper:
        if extract_whisper_evidence is None or format_whisper_as_section is None:
            errs.append("Whisper evidence requested but Tool_Use.whisper_audio imports failed (faster-whisper missing?).")
        else:
            try:
                ev = extract_whisper_evidence(
                    str(video_path),
                    model_size=whisper_model_size,
                    device=whisper_device,
                    compute_type=whisper_compute_type,
                    language=whisper_language,
                    max_segments=whisper_max_segments,
                )
                section = format_whisper_as_section(ev, max_detail_chars=whisper_detail_chars)
                if section:
                    parts.append(section)
            except Exception as exc:
                errs.append(f"Whisper failed: {type(exc).__name__}: {exc}")

    if do_clap:
        if (
            extract_clap_evidence is None
            or format_clap_as_section is None
            or derive_queries_from_item_meta is None
        ):
            errs.append("CLAP evidence requested but Tool_Use.clap_audio imports failed (laion-clap missing?).")
        else:
            queries = clap_queries
            if not queries:
                queries = derive_queries_from_item_meta(item_meta)
            if not queries:
                errs.append("CLAP skipped: no queries derivable from item_meta (no speech/sounding_action events).")
            else:
                try:
                    ev = extract_clap_evidence(
                        str(video_path),
                        queries=queries,
                        negative_queries=clap_negative_queries or DEFAULT_NEGATIVE_QUERIES,
                        mode=clap_mode,
                        window_seconds=clap_window_seconds,
                        hop_seconds=clap_hop_seconds,
                        device=clap_device,
                        max_frames=clap_max_frames,
                    )
                    section = format_clap_as_section(ev, max_detail_chars=clap_detail_chars)
                    if section:
                        parts.append(section)
                except Exception as exc:
                    errs.append(f"CLAP failed: {type(exc).__name__}: {exc}")

    if do_flam:
        if (
            extract_flam_evidence is None
            or format_flam_as_section is None
        ):
            errs.append("OpenFLAM evidence requested but Tool_Use.flam_audio imports failed.")
        else:
            # queries = flam_queries
            # if not queries and derive_flam_queries_from_item_meta is not None:
            #     queries = derive_flam_queries_from_item_meta(item_meta)
            queries = flam_queries
            if not queries and derive_flam_queries_from_item_meta is not None:
                # FLAM = non-speech sound events only; speech is covered by Whisper.
                queries = derive_flam_queries_from_item_meta(item_meta, include_speech=False)

            if not queries:
                errs.append("OpenFLAM skipped: no non-speech sounding-action events in item_meta.")
            else:
                try:
                    ev = extract_flam_evidence(
                        str(video_path),
                        queries=queries,
                        model_name=flam_model_name,
                        device=flam_device,
                        ckpt_path=flam_ckpt_path,
                        method=flam_method,
                        max_duration_sec=flam_max_duration_sec,
                        hop_sec=flam_hop_sec,
                        threshold=flam_threshold,
                        min_duration_sec=flam_min_duration_sec,
                        merge_gap_sec=flam_merge_gap_sec,
                        median_filter_size=flam_median_filter_size,
                        top_k=flam_top_k,
                    )
                    section = format_flam_as_section(
                        ev,
                        max_detail_chars=flam_detail_chars,
                    )
                    if section:
                        parts.append(section)
                except Exception as exc:
                    errs.append(f"OpenFLAM failed: {type(exc).__name__}: {exc}")

    section_text = "\n\n".join(parts)
    error_msg = " | ".join(errs)
    return section_text, error_msg
