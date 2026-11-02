"""
OpenFLAM frame-wise language-audio evidence for T2AV evaluation.

Uses OpenFLAM (Frame-Wise Language-Audio Modeling) to localize free-form
sound/text queries in the audio track of a video. Returns raw frame-wise
similarities and post-processed detection intervals, formatted as a text section
suitable for inclusion in a Gemini user prompt.

Design mirrors Tool_Use.whisper_audio and Tool_Use.clap_audio:
  - extract_flam_evidence(...)  -> dict of raw/localized evidence
  - format_flam_as_section(...) -> str labeled section for Gemini
  - derive_queries_from_item_meta(...) -> query generation from prompt metadata

The formatted section is RAW evidence: text-query similarities, timestamped
candidate detections, and top frame peaks. It deliberately contains no
correctness labels and no alignment judgment vs. the original prompt. Gemini
does the judgment.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

try:
    import librosa
    import numpy as np
    import scipy.ndimage
    import torch
    import openflam
except ImportError:  # pragma: no cover
    librosa = None
    np = None
    scipy = None
    torch = None
    openflam = None


_FLAM_CACHE: Dict[str, "openflam.OpenFLAM"] = {}
DEFAULT_FLAM_QUERIES = [
    "speech",
    "a person speaking",
    "a person saying help",
    "hand clap",
    "clapping hands",
    "slapping thigh",
    "a slap sound",
]


def _normalize_device(device: str = "auto") -> str:
    if device == "auto":
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    return device


def _get_flam_model(
    model_name: str = "v1-base",
    device: str = "auto",
    ckpt_path: str = "/tmp/openflam",
):
    if openflam is None or torch is None:
        raise ImportError("openflam not installed. Run: pip install openflam librosa scipy")
    resolved_device = _normalize_device(device)
    key = f"{model_name}|{resolved_device}|{ckpt_path}"
    if key not in _FLAM_CACHE:
        model = openflam.OpenFLAM(model_name=model_name, default_ckpt_path=ckpt_path)
        model.to(resolved_device)
        model.eval()
        _FLAM_CACHE[key] = model
    return _FLAM_CACHE[key]


def _extract_audio_wav(video_path: str, target_sr: int = 48000) -> str:
    """Extract mono PCM s16le wav at target_sr from video. Returns temp path."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH; required for audio extraction.")
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="flam_audio_")
    os.close(fd)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", str(target_sr),
        "-acodec", "pcm_s16le",
        wav_path,
    ]
    subprocess.run(cmd, check=True)
    return wav_path


def _clean_label(value) -> str:
    return str(value or "").strip()


def _humanize_label(value: str) -> str:
    return _clean_label(value).replace("_", " ")


def _event_label(event: Dict) -> str:
    return _clean_label(
        event.get("label")
        or event.get("action")
        or event.get("text")
        or event.get("utterance")
        or event.get("id")
        or event.get("event_id")
    )


def _event_kind(event: Dict) -> str:
    raw = _clean_label(event.get("kind") or event.get("modality") or event.get("type") or event.get("id")).lower()
    if "speech" in raw or raw in {"sp", "utterance"}:
        return "speech"
    if "sounding" in raw or raw in {"so", "so_action", "action_sounding"}:
        return "sounding_action"
    if "silent" in raw or raw in {"si", "si_action", "action_silent"}:
        return "silent_action"
    return raw or "unknown"


def _queries_for_label(kind: str, label: str) -> List[str]:
    label_h = _humanize_label(label)
    low = label_h.lower()
    queries: List[str] = []
    if not label_h:
        return queries
    if kind == "speech":
        queries.extend([
            f'a person says "{label_h}"',
            f"a person saying {label_h}",
            "a person speaking",
            "speech",
        ])
    elif kind == "sounding_action":
        queries.append(label_h)
        if "clap" in low:
            queries.extend(["hand clap", "clapping hands", "a clap sound"])
        if "slap" in low or "thigh" in low:
            queries.extend(["slapping thigh", "a slap sound", "a hand slapping a thigh"])
        if "knock" in low:
            queries.extend(["knocking sound", "a knock"])
    return queries


def derive_queries_from_item_meta(item_meta: Dict, include_speech: bool = True) -> List[str]:
    """Derive OpenFLAM text queries from evaluator item metadata.

    Includes speech and sounding-action events because both have audio components.
    Silent-only actions are intentionally skipped.
    """
    queries: List[str] = []
    events = item_meta.get("events") or []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = _event_kind(event)
        if kind == "speech" and not include_speech:
            continue
        if kind not in {"speech", "sounding_action"}:
            continue
        queries.extend(_queries_for_label(kind, _event_label(event)))

    # Fallback for older metadata where event list may not be populated.
    if not queries:
        text = " ".join(str(v) for v in item_meta.values()).lower()
        if include_speech and "help" in text:
            queries.extend(['a person says "help"', "a person saying help", "speech"])
        if "clap" in text:
            queries.extend(["hand clap", "clapping hands", "a clap sound"])
        if "slap" in text or "thigh" in text:
            queries.extend(["slapping thigh", "a slap sound", "a hand slapping a thigh"])

    # De-duplicate while preserving order.
    seen = set()
    out = []
    for q in queries:
        q = _clean_label(q)
        if q and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def _intervals_from_scores(
    scores,
    duration_sec: float,
    threshold: float,
    min_duration_sec: float,
    merge_gap_sec: float,
    top_k: int,
) -> Tuple[List[Dict], List[Dict]]:
    """Convert a 1D frame-wise score sequence into intervals and top peaks."""
    scores = np.asarray(scores, dtype=float)
    n = int(scores.shape[0])
    if n == 0 or duration_sec <= 0:
        return [], []
    frame_sec = duration_sec / n

    above = scores >= threshold
    intervals = []
    i = 0
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i + 1
        while j < n and above[j]:
            j += 1
        start = i * frame_sec
        end = j * frame_sec
        if end - start >= min_duration_sec:
            chunk = scores[i:j]
            peak_rel = int(chunk.argmax())
            intervals.append({
                "start": float(start),
                "end": float(end),
                "peak_time": float((i + peak_rel + 0.5) * frame_sec),
                "peak_score": float(chunk.max()),
                "mean_score": float(chunk.mean()),
            })
        i = j

    # Merge nearby intervals for the same query.
    if intervals and merge_gap_sec > 0:
        merged = [intervals[0]]
        for cur in intervals[1:]:
            prev = merged[-1]
            if cur["start"] - prev["end"] <= merge_gap_sec:
                prev["end"] = cur["end"]
                if cur["peak_score"] > prev["peak_score"]:
                    prev["peak_score"] = cur["peak_score"]
                    prev["peak_time"] = cur["peak_time"]
                prev["mean_score"] = max(prev["mean_score"], cur["mean_score"])
            else:
                merged.append(cur)
        intervals = merged

    if top_k and top_k > 0:
        idxs = np.argsort(scores)[::-1][:top_k]
        peaks = [
            {"time": float((int(idx) + 0.5) * frame_sec), "score": float(scores[int(idx)])}
            for idx in idxs
        ]
    else:
        peaks = []
    return intervals, peaks


def extract_flam_evidence(
    video_path: str,
    queries: Optional[List[str]] = None,
    model_name: str = "v1-base",
    device: str = "auto",
    ckpt_path: str = "/tmp/openflam",
    method: str = "unbiased",
    sample_rate: int = 48000,
    max_duration_sec: float = 10.0,
    threshold: float = 0.98,
    min_duration_sec: float = 0.05,
    merge_gap_sec: float = 0.10,
    median_filter_size: int = 3,
    top_k: int = 5,
    hop_sec: float = 0.0,
) -> Dict:
    """Run OpenFLAM local sound-event localization on a video's audio track.

    Returns a dict with model metadata, query list, frame rate information, and
    per-query detections. OpenFLAM scores are frame-wise similarity / activation
    values, not calibrated probabilities.
    """
    if librosa is None or np is None or torch is None or openflam is None:
        raise ImportError("openflam dependencies missing. Run: pip install openflam librosa scipy")
    if not queries:
        queries = list(DEFAULT_FLAM_QUERIES)

    wav_path = _extract_audio_wav(video_path, target_sr=sample_rate)
    try:
        audio, sr = librosa.load(wav_path, sr=sample_rate, mono=True)
        original_duration = float(len(audio) / sample_rate) if len(audio) else 0.0
        if original_duration <= 0:
            raise RuntimeError("No audio samples found after ffmpeg extraction.")

        # README examples feed 10 seconds at 48 kHz. Short clips are padded to
        # max_duration_sec. Long clips: if hop_sec > 0, slide a max_duration_sec
        # window with stride hop_sec and stitch frame scores with max over
        # overlaps; otherwise truncate (legacy behaviour).
        resolved_device = _normalize_device(device)
        model = _get_flam_model(model_name=model_name, device=resolved_device, ckpt_path=ckpt_path)
        model_queries = list(queries)
        if len(model_queries) == 1:
            model_queries = model_queries + ["background room noise"]

        def _run(chunk):
            t = torch.tensor(chunk, dtype=torch.float32).unsqueeze(0).to(resolved_device)
            with torch.no_grad():
                am = model.get_local_similarity(t, model_queries, method=method, cross_product=True).cpu().numpy()
            am = am[:, :len(queries), :] if am.ndim == 3 else am
            if am.ndim != 3:
                raise RuntimeError(f"Unexpected OpenFLAM local similarity shape: {am.shape}")
            return am[0]  # [num_queries, num_frames]

        win_len = int(max_duration_sec * sample_rate)
        if win_len <= 0 or len(audio) <= win_len or hop_sec <= 0:
            if win_len > 0 and len(audio) < win_len:
                audio_for_model = np.pad(audio, (0, win_len - len(audio)))
            elif win_len > 0:
                audio_for_model = audio[:win_len]
            else:
                audio_for_model = audio
            model_duration = float(len(audio_for_model) / sample_rate)
            scores_by_query = _run(audio_for_model)
        else:
            hop_len = int(hop_sec * sample_rate)
            starts = list(range(0, max(1, len(audio) - win_len) + 1, hop_len))
            if starts[-1] + win_len < len(audio):
                starts.append(len(audio) - win_len)
            first = _run(audio[starts[0]:starts[0] + win_len])
            n_frames_win = first.shape[1]
            frame_dt = max_duration_sec / n_frames_win
            total_frames = int(np.ceil(len(audio) / sample_rate / frame_dt))
            scores_by_query = np.full((len(queries), total_frames), -np.inf, dtype=np.float32)
            for si, st in enumerate(starts):
                sc = first if si == 0 else _run(audio[st:st + win_len])
                f0 = int(round(st / sample_rate / frame_dt))
                f1 = min(total_frames, f0 + sc.shape[1])
                scores_by_query[:, f0:f1] = np.maximum(scores_by_query[:, f0:f1], sc[:, :f1 - f0])
            scores_by_query = np.where(np.isfinite(scores_by_query), scores_by_query, 0.0)
            model_duration = float(total_frames * frame_dt)
        if median_filter_size and median_filter_size > 1:
            scores_by_query = scipy.ndimage.median_filter(scores_by_query, size=(1, int(median_filter_size)))

        query_results = []
        for qi, query in enumerate(queries):
            scores = scores_by_query[qi]
            intervals, peaks = _intervals_from_scores(
                scores=scores,
                duration_sec=model_duration,
                threshold=threshold,
                min_duration_sec=min_duration_sec,
                merge_gap_sec=merge_gap_sec,
                top_k=top_k,
            )
            # Keep only intervals/peaks inside actual extracted audio duration,
            # not padded silence after the end of short clips.
            intervals = [d for d in intervals if d["start"] < original_duration]
            for d in intervals:
                d["end"] = min(d["end"], original_duration)
                d["peak_time"] = min(d["peak_time"], original_duration)
            peaks = [p for p in peaks if p["time"] <= original_duration]
            query_results.append({
                "query": query,
                "max_score": float(np.max(scores)) if len(scores) else 0.0,
                "mean_score": float(np.mean(scores)) if len(scores) else 0.0,
                "detections": intervals,
                "top_peaks": peaks,
                # Rounded compact raw trace for debugging/reproducibility.
                "frame_scores": [float(x) for x in scores.tolist()],
            })

        return {
            "model": f"openflam:{model_name}",
            "method": method,
            "sample_rate": sample_rate,
            "audio_duration": original_duration,
            "model_duration": model_duration,
            "num_frames": int(scores_by_query.shape[-1]),
            "threshold": float(threshold),
            "min_duration_sec": float(min_duration_sec),
            "merge_gap_sec": float(merge_gap_sec),
            "median_filter_size": int(median_filter_size),
            "queries": query_results,
            "note": "OpenFLAM local scores are raw frame-wise audio-text activations/similarities, not calibrated probabilities.",
        }
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


def format_flam_as_section(evidence: Dict, max_detail_chars: int = 8000, include_frame_scores: bool = False) -> str:
    """Render OpenFLAM raw temporal evidence as a labeled text section for Gemini."""
    if not evidence:
        return ""

    header = [
        "OpenFLAM frame-wise language-audio evidence (raw sound-event localization):",
        f"- model: {evidence.get('model', 'openflam')}",
        f"- method: {evidence.get('method', 'unbiased')}",
        f"- audio sample rate (Hz): {evidence.get('sample_rate', 48000)}",
        f"- extracted audio duration (s): {evidence.get('audio_duration', 0):.2f}",
        f"- model input duration incl. padding/truncation (s): {evidence.get('model_duration', 0):.2f}",
        f"- local frames: {evidence.get('num_frames', 0)}",
        f"- detection threshold: {evidence.get('threshold', 0):.3f}",
        "- Scores are RAW frame-wise audio-text activations/similarities, not calibrated probabilities or correctness labels.",
        "- Use detections as approximate audio timing evidence only; defer to the audio itself if disagreement occurs.",
        "- Queries cover NON-SPEECH sound events only. For speech content/timing, use the Whisper ASR section instead.",
        "",
        "Queries:",
    ]

    body: List[str] = []
    for result in evidence.get("queries", []):
        body.append(
            f"  Query: {result.get('query')!r} "
            f"(max_score={result.get('max_score', 0):.3f}, mean_score={result.get('mean_score', 0):.3f})"
        )
        detections = result.get("detections") or []
        if detections:
            body.append("    detections above threshold:")
            for det in detections:
                body.append(
                    f"      [{det['start']:6.2f} - {det['end']:6.2f}] "
                    f"peak@{det['peak_time']:.2f}s score={det['peak_score']:.3f}, "
                    f"mean={det['mean_score']:.3f}"
                )
        else:
            body.append("    detections above threshold: none")
        peaks = result.get("top_peaks") or []
        if peaks:
            peak_s = ", ".join(f"{p['time']:.2f}s:{p['score']:.3f}" for p in peaks)
            body.append(f"    top frame peaks: {peak_s}")
        if include_frame_scores and result.get("frame_scores"):
            compact = ", ".join(f"{x:.3f}" for x in result["frame_scores"])
            body.append(f"    raw frame_scores: [{compact}]")

    if not body:
        body.append("  (no OpenFLAM query results)")

    full = "\n".join(header + body)
    if max_detail_chars and len(full) > max_detail_chars:
        full = full[:max_detail_chars] + "\n  [... truncated ...]"
    return full
