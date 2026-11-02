"""
Open-vocabulary sound-event evidence for T2AV evaluation.

Backend: HuggingFace transformers.ClapModel with the LAION CLAP weights
(default: laion/clap-htsat-unfused). Same model weights as the `laion-clap`
PyPI package, but without that package's hard numpy<2 pin, which conflicts
with modern opencv-python (>=4.11) and openimageio used by MediaPipe.

Design mirrors Tool_Use.raw_mediapipe:
  - extract_clap_evidence(...)  -> dict of raw evidence
  - format_clap_as_section(...) -> str labeled section for Gemini
  - derive_queries_from_item_meta(...) helper for the dispatcher

Output schema is unchanged from the previous laion-clap-based version, so
audio_evidence.py and the main eval script need no edits.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Generator, List, Optional, Tuple

import numpy as np

try:
    import torch
    from transformers import ClapModel, ClapProcessor
except ImportError:  # pragma: no cover
    torch = None
    ClapModel = None
    ClapProcessor = None

try:
    import soundfile as sf
except ImportError:  # pragma: no cover
    sf = None


# (model_name, device) -> (model, processor, device_str)
_CLAP_CACHE: Dict[str, Tuple] = {}


def _get_clap(
    model_name: str = "laion/clap-htsat-unfused",
    device: str = "auto",
):
    if ClapModel is None or ClapProcessor is None or torch is None:
        raise ImportError(
            "transformers or torch not installed. "
            "Run: pip install 'transformers>=4.36' torch soundfile"
        )
    if device == "auto":
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        dev = device
    key = f"{model_name}|{dev}"
    if key not in _CLAP_CACHE:
        model = ClapModel.from_pretrained(model_name).to(dev).eval()
        processor = ClapProcessor.from_pretrained(model_name)
        _CLAP_CACHE[key] = (model, processor, dev)
    return _CLAP_CACHE[key]


def _extract_audio_wav(video_path: str, target_sr: int = 48000) -> str:
    """Extract mono PCM s16le wav at target_sr (CLAP wants 48 kHz)."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found on PATH; required for audio extraction.")
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="clap_audio_")
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


def _load_wav_mono(wav_path: str, target_sr: int = 48000) -> Tuple[np.ndarray, int]:
    if sf is None:
        raise ImportError("soundfile not installed. Run: pip install soundfile")
    audio, sr = sf.read(wav_path, always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if sr != target_sr:
        raise ValueError(f"Expected sr={target_sr} but got {sr}")
    return audio, sr


def _windowed(
    audio: np.ndarray, sr: int, win_s: float, hop_s: float
) -> Generator[Tuple[float, float, np.ndarray], None, None]:
    n_win = int(win_s * sr)
    n_hop = max(int(hop_s * sr), 1)
    if len(audio) <= n_win:
        yield 0.0, len(audio) / sr, audio
        return
    for start in range(0, len(audio) - n_win + 1, n_hop):
        end = start + n_win
        yield start / sr, end / sr, audio[start:end]


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-8)
    b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-8)
    return a @ b.T


def _encode_text(model, processor, device: str, texts: List[str]) -> np.ndarray:
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        emb = model.get_text_features(**inputs)
    return emb.cpu().numpy().astype(np.float32)


def _encode_audio(
    model, processor, device: str, audio_arr: np.ndarray, sr: int = 48000
) -> np.ndarray:
    inputs = processor(audios=audio_arr, sampling_rate=sr, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        emb = model.get_audio_features(**inputs)
    return emb.cpu().numpy().astype(np.float32)


DEFAULT_NEGATIVE_QUERIES = ["silence", "background noise", "white noise"]


def extract_clap_evidence(
    video_path: str,
    queries: List[str],
    negative_queries: Optional[List[str]] = None,
    mode: str = "temporal",                # 'global' or 'temporal'
    window_seconds: float = 2.0,
    hop_seconds: float = 1.0,
    model_name: str = "laion/clap-htsat-unfused",
    device: str = "auto",
    max_frames: int = 60,
    # ---- Back-compat kwargs (ignored under the transformers backend) ----
    ckpt: Optional[str] = None,
    enable_fusion: bool = False,
    amodel: str = "HTSAT-base",
) -> Dict:
    """Compute CLAP text-audio similarity using transformers ClapModel.

    Returns the same dict shape as the previous laion-clap-based version
    (model, queries, negative_queries, duration, mode, results, frames).
    """
    if not queries:
        return {
            "model": f"transformers-clap:{model_name}",
            "queries": [],
            "negative_queries": list(negative_queries or []),
            "duration": 0.0,
            "mode": mode,
            "results": [],
            "frames": [],
        }

    model, processor, dev = _get_clap(model_name=model_name, device=device)

    negatives = list(negative_queries or [])
    all_queries = list(queries) + negatives
    text_embeds = _encode_text(model, processor, dev, all_queries)  # (Q, D)

    wav_path = _extract_audio_wav(video_path, target_sr=48000)
    try:
        audio, sr = _load_wav_mono(wav_path, target_sr=48000)
        duration = len(audio) / sr

        # ---- Global similarity (whole clip) ----
        global_embed = _encode_audio(model, processor, dev, audio, sr=sr)  # (1, D)
        global_sims = _cosine_sim(global_embed, text_embeds)[0]            # (Q,)

        positives = global_sims[: len(queries)]
        ex = np.exp(positives - positives.max())
        softmax = ex / (ex.sum() + 1e-8)

        results: List[Dict] = []
        for i, q in enumerate(queries):
            results.append({
                "query": q,
                "similarity": float(global_sims[i]),
                "softmax_among_positives": float(softmax[i]),
            })
        for j, q in enumerate(negatives):
            results.append({
                "query": q,
                "similarity": float(global_sims[len(queries) + j]),
                "is_negative": True,
            })

        # ---- Sliding-window similarities ----
        frames: List[Dict] = []
        if mode == "temporal":
            for k, (t0, t1, chunk) in enumerate(
                _windowed(audio, sr, window_seconds, hop_seconds)
            ):
                if k >= max_frames:
                    break
                emb = _encode_audio(model, processor, dev, chunk, sr=sr)
                sims = _cosine_sim(emb, text_embeds)[0]
                frame = {
                    "start": float(t0),
                    "end": float(t1),
                    "scores": {q: float(sims[i]) for i, q in enumerate(queries)},
                }
                if negatives:
                    frame["negative_scores"] = {
                        q: float(sims[len(queries) + j])
                        for j, q in enumerate(negatives)
                    }
                frames.append(frame)

        return {
            "model": f"transformers-clap:{model_name}",
            "queries": list(queries),
            "negative_queries": negatives,
            "duration": float(duration),
            "mode": mode,
            "results": results,
            "frames": frames,
        }
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


def format_clap_as_section(evidence: Dict, max_detail_chars: int = 8000) -> str:
    """Render CLAP raw evidence as a labeled text section for Gemini."""
    if not evidence or not evidence.get("queries"):
        return ""

    header = [
        "CLAP open-vocabulary sound-event evidence (raw text-audio similarity):",
        f"- model: {evidence.get('model', 'laion-clap')}",
        f"- audio duration (s): {evidence.get('duration', 0):.2f}",
        f"- mode: {evidence.get('mode', 'global')}",
        f"- queries: {evidence.get('queries')}",
        f"- negative queries: {evidence.get('negative_queries', [])}",
        "- These are RAW cosine similarities, not correctness labels.",
        "- Higher cosine generally means closer audio-text match, but absolute thresholds are unreliable.",
        "- Compare positive queries against negative anchors and against other plausible competing queries.",
        "- Sliding-window scores are approximate chunk-level evidence. A high score means the queried sound may occur somewhere in that window, not exactly at the window center.",
    ]

    body_lines: List[str] = []

    if evidence.get("frames"):
        body_lines.append("")
        body_lines.append("Sliding-window similarities:")
        for frame in evidence["frames"]:
            pos_str = ", ".join(
                f'"{q}"={s:.3f}' for q, s in frame.get("scores", {}).items()
            )
            neg_scores = frame.get("negative_scores", {}) or {}
            neg_str = ", ".join(
                f'"{q}"={s:.3f}' for q, s in neg_scores.items()
            )

            line = f"  [{frame['start']:6.2f} - {frame['end']:6.2f}] positives: {pos_str}"
            if neg_str:
                line += f" | negatives: {neg_str}"
            body_lines.append(line)
    else:
        body_lines.append("")
        body_lines.append("No sliding-window similarities were produced.")

    full = "\n".join(header + body_lines)
    if max_detail_chars and len(full) > max_detail_chars:
        full = full[:max_detail_chars] + "\n  [... truncated ...]"
    return full


def derive_queries_from_item_meta(item_meta: Dict) -> List[str]:
    """Pick CLAP queries from item_meta.events.

    sounding_action labels -> direct CLAP queries.
    speech events          -> generic "a person speaking" anchor (Whisper handles content).
    silent_action labels   -> dropped (visual-only).
    """
    queries: List[str] = []
    has_speech = False
    for event in item_meta.get("events", []):
        kind = event.get("kind")
        label = (event.get("label") or "").strip()
        if not label:
            continue
        if kind == "sounding_action":
            queries.append(label)
        elif kind == "speech":
            has_speech = True
    if has_speech:
        queries.append("a person speaking")

    seen = set()
    out: List[str] = []
    for q in queries:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out
