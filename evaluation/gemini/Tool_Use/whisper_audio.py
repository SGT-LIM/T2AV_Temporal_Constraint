"""
Open-vocabulary speech ASR evidence for T2AV evaluation.

Uses faster-whisper (large-v3 by default) to transcribe the audio track of a
video. Returns raw segment/word-level timestamps and no-speech probabilities,
formatted as a text section suitable for inclusion in a Gemini user prompt.

Design mirrors Tool_Use.raw_mediapipe:
  - extract_whisper_evidence(...)  -> dict of raw evidence
  - format_whisper_as_section(...) -> str labeled section for Gemini

The formatted section is RAW evidence: timestamps + transcript text + per-segment
confidences. It deliberately contains no correctness labels and no alignment
judgment vs. the original prompt. Gemini does the judgment.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None


_WHISPER_CACHE: Dict[str, "WhisperModel"] = {}


def _get_whisper_model(
    model_size: str = "large-v3",
    device: str = "auto",
    compute_type: str = "auto",
) -> "WhisperModel":
    if WhisperModel is None:
        raise ImportError(
            "faster-whisper not installed. Run: pip install faster-whisper"
        )
    key = f"{model_size}|{device}|{compute_type}"
    if key not in _WHISPER_CACHE:
        _WHISPER_CACHE[key] = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
    return _WHISPER_CACHE[key]


def _extract_audio_wav(video_path: str, target_sr: int = 16000) -> str:
    """Extract mono PCM s16le wav at target_sr from video. Returns temp path."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH; required for audio extraction.")
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="whisper_audio_")
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


def extract_whisper_evidence(
    video_path: str,
    model_size: str = "large-v3",
    device: str = "auto",
    compute_type: str = "auto",
    language: Optional[str] = None,
    word_timestamps: bool = True,
    beam_size: int = 5,
    vad_filter: bool = True,
    max_segments: int = 200,
) -> Dict:
    """Transcribe the audio track of a video and return raw Whisper evidence.

    Returns
    -------
    dict with:
        model, language, language_probability, duration,
        segments: list of {start, end, text, avg_logprob, no_speech_prob, words},
        no_speech_prob_overall (mean), has_speech (any seg with no_speech_prob<0.5)
    """
    wav_path = _extract_audio_wav(video_path, target_sr=16000)
    try:
        model = _get_whisper_model(model_size, device, compute_type)
        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            word_timestamps=word_timestamps,
            beam_size=beam_size,
            vad_filter=vad_filter,
        )

        segments: List[Dict] = []
        for seg in segments_iter:
            words = []
            if word_timestamps and seg.words:
                for w in seg.words:
                    if w.start is None or w.end is None:
                        continue
                    words.append({
                        "word": w.word,
                        "start": float(w.start),
                        "end": float(w.end),
                        "probability": float(w.probability) if w.probability is not None else None,
                    })
            segments.append({
                "start": float(seg.start),
                "end": float(seg.end),
                "text": (seg.text or "").strip(),
                "avg_logprob": float(seg.avg_logprob),
                "no_speech_prob": float(seg.no_speech_prob),
                "compression_ratio": float(seg.compression_ratio),
                "words": words,
            })
            if len(segments) >= max_segments:
                break

        no_speech_probs = [s["no_speech_prob"] for s in segments] or [1.0]
        mean_no_speech = sum(no_speech_probs) / len(no_speech_probs)
        has_speech = any(s["no_speech_prob"] < 0.5 for s in segments)

        return {
            "model": f"faster-whisper:{model_size}",
            "language": info.language,
            "language_probability": float(info.language_probability),
            "duration": float(info.duration),
            "segments": segments,
            "no_speech_prob_overall": float(mean_no_speech),
            "has_speech": bool(has_speech),
        }
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


def format_whisper_as_section(evidence: Dict, max_detail_chars: int = 8000) -> str:
    """Render Whisper raw evidence as a labeled text section for Gemini."""
    if not evidence:
        return ""

    header = [
        "Whisper ASR transcription (raw open-vocabulary speech evidence):",
        f"- model: {evidence.get('model', 'whisper')}",
        f"- detected language: {evidence.get('language')} (lang_prob={evidence.get('language_probability', 0):.2f})",
        f"- audio duration (s): {evidence.get('duration', 0):.2f}",
        f"- has_speech (any segment with no_speech_prob<0.5): {evidence.get('has_speech')}",
        f"- mean no_speech_prob across segments: {evidence.get('no_speech_prob_overall', 1.0):.3f}",
        "- This is RAW ASR output. It is not a correctness label. Use it as one piece of evidence and defer to the audio itself if disagreement occurs.",
        "",
        "Segments:",
    ]

    body_lines: List[str] = []
    for seg in evidence.get("segments", []):
        body_lines.append(
            f"  [{seg['start']:6.2f} - {seg['end']:6.2f}] "
            f"(no_speech_prob={seg['no_speech_prob']:.2f}, avg_logprob={seg['avg_logprob']:.2f}) "
            f"{seg['text']}"
        )
        if seg.get("words"):
            words_str = ", ".join(
                f"{w['word'].strip()}@{w['start']:.2f}-{w['end']:.2f}"
                for w in seg["words"]
            )
            if words_str:
                body_lines.append(f"    words: {words_str}")

    if not body_lines:
        body_lines.append("  (no speech segments detected)")

    full = "\n".join(header + body_lines)
    if max_detail_chars and len(full) > max_detail_chars:
        full = full[:max_detail_chars] + "\n  [... truncated ...]"
    return full
