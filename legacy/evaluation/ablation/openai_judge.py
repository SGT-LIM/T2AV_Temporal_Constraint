#!/usr/bin/env python3
"""OpenAI judge backend for the agentic evaluator (B5: second closed-source judge).

Drop this file next to agentic_common.py. It is only reached when
ctx.config["judge_backend"] == "openai" (see the small dispatch patch in
agentic_common.call_gemini_json). Everything upstream (evidence, routing,
prompts, schemas, CSV writers) is untouched, so a run differs from the Gemini
run ONLY in the judge call.

Media handling per --media-input-mode:
  language_only : text only                         -> any GPT text model (gpt-5.5)
  audio_only    : extracted wav inlined as input_audio -> gpt-audio (chat.completions)
  video         : frames sampled at --frame-fps (default 8) as ordered images,
                  NO audio. A MEDIA INPUT NOTE saying so is prepended to the
                  user text. -> gpt-5.5 (image input)

Structured output: response_format json_schema (non-strict, same schema dicts
as Gemini). Output is parsed with new_eval.parse_model_json like before.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import List, Optional

import new_eval as NE

try:
    from openai import OpenAI
    from openai import APIConnectionError, APIStatusError, RateLimitError
except ImportError as e:  # pragma: no cover
    raise RuntimeError("pip install openai  (needed for --judge-backend openai)") from e


FRAMES_NOTE_TMPL = (
    "MEDIA INPUT NOTE: For this call the video is given as {n} still frames sampled at "
    "{fps} fps in temporal order (video length {dur:.2f}s). Each frame is preceded by its "
    "timestamp. NO audio track is provided. Judge visual components from the frames; for "
    "any audio component rely only on the tool-output / caption evidence text if present, "
    "and treat unsupported audio requirements as failure."
)


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------
_CLIENT: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _CLIENT
    if _CLIENT is None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set")
        _CLIENT = OpenAI()
    return _CLIENT


# ---------------------------------------------------------------------------
# frame extraction (cached, like extract_audio_only_file)
# ---------------------------------------------------------------------------
def video_duration_sec(video_path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out) if out else 0.0


def extract_frames(video_path: Path, fps: float, cache_dir: Optional[Path]) -> List[Path]:
    """JPEG frames at `fps`, cached by (path, mtime, fps). Native resolution
    (LTX 768x512 -> ~461 tokens/frame on gpt-5.5; MOVA 360p -> ~288)."""
    cache_dir = Path(cache_dir) if cache_dir else Path("frame_cache")
    tag = hashlib.md5(f"{video_path.resolve()}|{video_path.stat().st_mtime_ns}|{fps}".encode()).hexdigest()[:10]
    out_dir = cache_dir / f"{video_path.stem}_{tag}_fps{fps:g}"
    if out_dir.exists() and any(out_dir.glob("*.jpg")):
        return sorted(out_dir.glob("*.jpg"))
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
         "-vf", f"fps={fps}", "-q:v", "3", str(out_dir / "f%04d.jpg")],
        check=True, stdin=subprocess.DEVNULL,
    )
    frames = sorted(out_dir.glob("*.jpg"))
    if not frames:
        raise RuntimeError(f"frame extraction produced nothing for {video_path}")
    return frames


def _b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode("ascii")


# ---------------------------------------------------------------------------
# message assembly
# ---------------------------------------------------------------------------
def build_messages(ctx, system_prompt: str, user_text: str):
    """Return (messages, provenance_str)."""
    cfg = ctx.config
    mode = cfg.get("media_input_mode", "video") or "video"

    if mode == "language_only":
        content = [{"type": "text", "text": user_text}]
        prov = "openai:text"

    elif mode == "audio_only":
        wav = cfg.get("audio_only_path")
        if not wav:
            raise RuntimeError("audio_only mode but no extracted audio path in ctx.config.")
        content = [
            {"type": "text", "text": user_text},
            {"type": "input_audio", "input_audio": {"data": _b64(Path(wav)), "format": "wav"}},
        ]
        prov = "openai:audio_only"

    else:  # video -> frames
        video_path = Path(cfg["video_path"])
        fps = float(cfg.get("frame_fps") or 8)
        frames = extract_frames(video_path, fps, cfg.get("frame_cache_dir"))
        dur = video_duration_sec(video_path)
        note = FRAMES_NOTE_TMPL.format(n=len(frames), fps=f"{fps:g}", dur=dur)
        content = [{"type": "text", "text": note + "\n\n" + user_text}]
        for i, f in enumerate(frames):
            t = i / fps
            content.append({"type": "text", "text": f"[frame {i + 1}/{len(frames)} t={t:.3f}s]"})
            content.append({"type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}",
                                          "detail": cfg.get("frame_detail") or "low"}})  # astra_patched
        prov = f"openai:frames:{fps:g}fps:n={len(frames)}:{cfg.get('frame_detail') or 'low'}:no_audio"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]
    return messages, prov


# ---------------------------------------------------------------------------
# the call
# ---------------------------------------------------------------------------
def call_openai_json(ctx, system_prompt: str, user_text: str, schema: dict):
    client = get_client()
    model = ctx.model_name
    messages, prov = build_messages(ctx, system_prompt, user_text)
    ctx.config["last_media_provenance"] = prov

    kwargs = dict(
        model=model, service_tier=os.environ.get("OPENAI_SERVICE_TIER", "flex"),
        messages=messages,
        response_format={"type": "json_schema",
                         "json_schema": {"name": "axis_result", "schema": schema, "strict": False}},
    )
    if "audio" in model:
        kwargs.pop("response_format")
    # gpt-5.x reasoning models reject temperature; older/audio models accept it.
    if not model.startswith(("gpt-5", "gpt-6")):
        kwargs["temperature"] = 0.0
        kwargs["seed"] = 42
    else:
        kwargs["reasoning_effort"] = ctx.config.get("openai_reasoning_effort") or "low"

    delays = [30, 60, 120]
    for attempt in range(len(delays) + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            break
        except (RateLimitError, APIConnectionError) as e:
            if attempt == len(delays):
                raise
            print(f"    [RETRY {attempt + 1}/{len(delays)}] {type(e).__name__}: retrying in {delays[attempt]}s", flush=True)
            time.sleep(delays[attempt])
        except APIStatusError as e:
            if e.status_code >= 500 and attempt < len(delays):
                print(f"    [RETRY {attempt + 1}/{len(delays)}] {e.status_code}: retrying in {delays[attempt]}s", flush=True)
                time.sleep(delays[attempt])
                continue
            # 400 on json_schema -> retry once with json_object (some models/modes)
            if e.status_code == 400 and "response_format" in kwargs:
                rf = kwargs["response_format"]["type"]
                if rf == "json_schema":
                    print("    [WARN] json_schema rejected; falling back to json_object", flush=True)
                    kwargs["response_format"] = {"type": "json_object"}
                else:
                    print("    [WARN] response_format unsupported; relying on prompt + parse_model_json", flush=True)
                    kwargs.pop("response_format")
                continue
            raise
    raw = resp.choices[0].message.content or ""
    u = getattr(resp, "usage", None)
    if u is not None:
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        reason = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
        write = getattr(getattr(u, "prompt_tokens_details", None), "cache_write_tokens", 0) or 0
        sysh = hashlib.md5(system_prompt.encode()).hexdigest()[:6]; userh = hashlib.md5(user_text[:600].encode()).hexdigest()[:6]
        print(f"    [USAGE] {model} in={u.prompt_tokens} cached={cached} write={write} out={u.completion_tokens} reasoning={reason} sys={sysh} user600={userh}", flush=True)
    parsed = NE.parse_model_json(raw)
    # models answering without response_format sometimes wrap the object one level deeper
    # ({"audio_event_correctness": {"per_event": [...]}}); unwrap a single-key dict wrapper.
    if isinstance(parsed, dict) and "per_event" not in parsed and "label" not in parsed and len(parsed) == 1:
        inner = next(iter(parsed.values()))
        if isinstance(inner, dict): parsed = inner
    return parsed, raw
