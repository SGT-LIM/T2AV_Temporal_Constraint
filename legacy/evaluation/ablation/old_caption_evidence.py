#!/usr/bin/env python3
"""Dense-caption evidence for the agentic T2AV evaluator.

Implements the "dense caption as tool evidence" ablation rows from the 08/05
meeting: instead of (or alongside) Whisper/FLAM/pose evidence, the axis agents
receive a textual dense caption of the video, injected through the exact same
evidence-section slot. Comparing

    (1) no evidence            --caption-evidence-mode none  (+ audio/pose none)
    (2) dense caption          --caption-evidence-mode gemini | external
    (3) specialist tools       --audio-evidence-mode whisper_flam

on the same items isolates the contribution of the specialist tools against a
cheap text-only intermediate representation.

Two backends:
  - "gemini":   a SEPARATE Gemini call (never the judge call itself) captions
                the video. This is the "Gemini generates the caption itself"
                row: if its timestamps are unreliable, that unreliability is
                the evidence for why specialist tools are needed.
  - "external": captions are precomputed by any specialist captioner (e.g.
                TimeChat-Captioner) and loaded from a JSON/JSONL file keyed by
                video path/filename/stem. Swapping captioners = swapping files;
                the eval pipeline never has to host the captioner.

Design decisions (deliberate, to keep the comparison controlled):
  - The captioning prompt is GENERIC (prompt-agnostic): the captioner never
    sees the generation prompt, item metadata, or evaluation criteria. This
    keeps the row a "task-agnostic text representation" baseline and lets one
    cached caption be reused across every axis and every item variant of the
    same video file.
  - Captions are cached on disk per (video, backend, model, style, prompt
    version), so a resumed or re-routed run never re-captions a video.
  - The evidence-use policy for captions lives in new_eval.CAPTION_GENERAL_GUIDE
    (system prompt, injected when caption evidence is active); this module's
    section carries only a provenance note.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional, Tuple

# NOTE: google.genai is imported lazily inside generate_caption_gemini so that
# environments without the Gemini SDK (e.g. the SALMONN captioning env) can
# still import CAPTION_PROMPTS from this module.

CAPTION_PROMPT_VERSION = "v1"

# ---------------------------------------------------------------------------
# Captioning prompts (generic: no item metadata, no target events)
# ---------------------------------------------------------------------------
_TIMESTAMPED_CAPTION_PROMPT = """You are a dense audio-visual captioning system.

Watch the video (including its audio track) and produce a chronological, \
timestamped list of ALL observable events. Cover BOTH modalities:
- Visible events: actions, gestures, poses, and movements. Always state which \
hand or body side is used when applicable, and describe the motion precisely \
(e.g. "raises RIGHT hand, thumb extended upward").
- Audible events: transcribe any speech verbatim; describe every non-speech \
sound (claps, slaps, impacts, music, noise). If the audio track is silent or \
absent, state that explicitly.

Output format, one event per line:
[<start_seconds>-<end_seconds>] (<visual|audio|audio-visual>) <description>

Rules:
- Timestamps in seconds with one decimal place, relative to the start of the video.
- List repeated occurrences of the same event as separate lines, one per occurrence.
- Report only what is directly observable. No interpretation of intent, no \
quality judgments, no guesses about off-screen causes.
- Order lines by start time.

Return only the caption lines, no preamble."""

_PLAIN_CAPTION_PROMPT = """You are a dense audio-visual captioning system.

Watch the video (including its audio track) and describe, in chronological \
order, everything that is visible and audible. Cover BOTH modalities:
- Visible events: actions, gestures, poses, and movements. Always state which \
hand or body side is used when applicable.
- Audible events: transcribe any speech verbatim; describe every non-speech \
sound. If the audio track is silent or absent, state that explicitly.

Rules:
- Write flowing prose in temporal order ("first ... then ... finally ...").
- Mention every repetition of a repeated event.
- Report only what is directly observable. No interpretation of intent, no \
quality judgments.
- Do NOT include numeric timestamps.

Return only the description, no preamble."""

CAPTION_PROMPTS = {
    "timestamped": _TIMESTAMPED_CAPTION_PROMPT,
    "plain": _PLAIN_CAPTION_PROMPT,
}

# Provenance note embedded in the evidence section. The evidence-use POLICY
# (how much weight the caption carries, conflict handling, citation rules)
# now lives in new_eval.CAPTION_GENERAL_GUIDE, injected into the system prompt
# when caption evidence is active — mirroring how the Whisper/FLAM guides work.
# Keeping policy out of this section avoids contradictory instructions.
_SECTION_GUIDE = """Provenance of this evidence:
- The dense caption below was produced by a separate captioning pass over the SAME video. The captioner did NOT see the generation prompt, the target events, or any evaluation criteria.
- The caption may miss events, mis-time events, merge repetitions, or hallucinate; its contents and timestamps are expert observations, not ground-truth labels.
- Interpret and weigh this caption according to the dense-caption evidence-use policy in the system instructions."""


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _cache_path(cache_dir: Path, video_path: Path, backend: str, model: str, style: str) -> Path:
    key = f"{video_path.resolve()}|{backend}|{model}|{style}|{CAPTION_PROMPT_VERSION}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", video_path.stem)[:60]
    return cache_dir / f"{safe_stem}__{backend}__{style}__{digest}.json"


def _cache_load(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        caption = data.get("caption", "")
        return caption if caption else None
    except Exception:
        return None


def _cache_store(path: Path, video_path: Path, backend: str, model: str, style: str, caption: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video": str(video_path),
        "backend": backend,
        "model": model,
        "style": style,
        "prompt_version": CAPTION_PROMPT_VERSION,
        "caption": caption,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def generate_caption_gemini(client, uploaded, model_name: str, style: str,
                            media_fps: float = 0.0) -> str:
    """One plain-text captioning call, reusing the already-uploaded video handle.

    Deliberately a separate call from the judge (temperature 0, fixed seed, no
    structured schema, thinking off) so the caption row measures the value of a
    caption-shaped intermediate representation, not extra judge reasoning.
    """
    from google.genai import types

    prompt = CAPTION_PROMPTS[style]
    if media_fps and media_fps > 0:
        contents = [
            types.Part(
                file_data=types.FileData(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
                video_metadata=types.VideoMetadata(fps=media_fps),
            ),
            prompt,
        ]
    else:
        contents = [uploaded, prompt]
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.0, seed=42),
    )
    return (response.text or "").strip()


def load_external_caption(external_json: Path, video_path: Path, videos_root: Optional[Path] = None) -> str:
    """Load a precomputed caption for `video_path` from a JSON or JSONL file.

    Accepted formats:
      - JSON object: {"<key>": "<caption>", ...}
      - JSON array / JSONL: entries like {"video": "<key>", "caption": "..."}
        ("video_id" or "path" also accepted as the key field)

    A key matches if it equals the video's relative path (when videos_root is
    given), its filename, or its stem.
    """
    candidates = {video_path.name, video_path.stem, str(video_path)}
    if videos_root is not None:
        try:
            candidates.add(str(video_path.relative_to(videos_root)))
        except ValueError:
            pass

    text = external_json.read_text(encoding="utf-8")
    entries = []
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            record_key = data.get("video") or data.get("video_id") or data.get("path")
            if "caption" in data and record_key:
                # A single {"video": ..., "caption": ...} record (e.g. 1-line JSONL).
                entries.append((record_key, data.get("caption", "")))
            else:
                for k, v in data.items():
                    entries.append((k, v if isinstance(v, str) else v.get("caption", "")))
        elif isinstance(data, list):
            for row in data:
                key = row.get("video") or row.get("video_id") or row.get("path") or ""
                entries.append((key, row.get("caption", "")))
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = row.get("video") or row.get("video_id") or row.get("path") or ""
            entries.append((key, row.get("caption", "")))

    # Exact key matches (e.g. relative paths) take priority; filename/stem
    # fallbacks run only if nothing matched exactly, so identical filenames in
    # different item folders never cross-match.
    for key, caption in entries:
        if key in candidates and caption:
            return caption
    for key, caption in entries:
        if (Path(key).name in candidates or Path(key).stem in candidates) and caption:
            return caption
    raise KeyError(
        f"No caption found for {video_path.name} in {external_json} "
        f"(tried keys: {sorted(candidates)})"
    )


# ---------------------------------------------------------------------------
# Section assembly (public entry point, mirrors build_audio_evidence_section)
# ---------------------------------------------------------------------------
def build_caption_evidence_section(
    client,
    uploaded,
    video_path: Path,
    mode: str = "none",
    caption_model: str = "",
    caption_style: str = "timestamped",
    cache_dir: Optional[Path] = None,
    external_json: Optional[Path] = None,
    videos_root: Optional[Path] = None,
    detail_chars: int = 8000,
    media_fps: float = 0.0,
) -> Tuple[str, str]:
    """Return (section_text, error). Never raises; on failure returns ("", err).

    mode: "none" | "gemini" | "external".
    """
    if mode in (None, "", "none"):
        return "", ""
    if caption_style not in CAPTION_PROMPTS:
        return "", f"Unknown caption style: {caption_style!r}"

    backend_model = caption_model if mode == "gemini" else (external_json.name if external_json else "external")
    cached = None
    cache_file = None
    if cache_dir is not None:
        cache_file = _cache_path(Path(cache_dir), video_path, mode, backend_model, caption_style)
        cached = _cache_load(cache_file)

    try:
        if cached is not None:
            caption = cached
        elif mode == "gemini":
            caption = generate_caption_gemini(client, uploaded, caption_model, caption_style, media_fps=media_fps)
        elif mode == "external":
            if external_json is None:
                return "", "caption-evidence-mode=external requires --caption-external-json."
            caption = load_external_caption(Path(external_json), video_path, videos_root=videos_root)
        else:
            return "", f"Unknown caption evidence mode: {mode!r}"
    except Exception as exc:  # evidence must never block evaluation
        return "", f"{type(exc).__name__}: {exc}"

    if not caption:
        return "", "Captioner returned an empty caption."

    if cache_file is not None and cached is None:
        try:
            _cache_store(cache_file, video_path, mode, backend_model, caption_style, caption)
        except Exception:
            pass  # cache failures are non-fatal

    body = caption.strip()
    truncated = ""
    if detail_chars and detail_chars > 0 and len(body) > detail_chars:
        body = body[:detail_chars]
        truncated = f"\n[... caption truncated at {detail_chars} chars ...]"

    section = (
        f"=== DENSE CAPTION EVIDENCE (backend={mode}, model={backend_model}, style={caption_style}) ===\n"
        f"{_SECTION_GUIDE}\n"
        f"Dense caption:\n{body}{truncated}\n"
        f"=== END DENSE CAPTION EVIDENCE ==="
    )
    return section, ""
