#!/usr/bin/env python3
"""
Gemini timestamp+caption sanity check for T2AV videos.

Purpose:
  Randomly sample N videos (default 5) from an outputs directory, ask Gemini to
  produce timestamped event captions (audio / visual / audio-visual) from the
  video ALONE (blind by default), and emit:

    1. <out>/captions_<video>.json       raw structured output per video
    2. <out>/summary.csv                 one row per detected event
    3. <out>/review_sheet.md             human review sheet with a pre-registered
                                         rubric (fill in PASS/FAIL while watching)

Conditions:
  --condition blind     (default) Gemini sees only the video. Tests perception.
  --condition prompted  Gemini also sees the generation prompt / expected events
                        (requires --prompt-json). Tests grounding w/ context.

Sampling is seeded (--seed) so the same 5 videos can be re-drawn reproducibly.

Usage:
  export GEMINI_API_KEY=...
  python gemini_caption_sanity_check.py \
      --outputs-dir /path/to/outputs \
      --out-dir ./caption_sanity \
      --num-videos 5 --seed 42

  # prompted condition, restricted to variant 1:
  python gemini_caption_sanity_check.py \
      --outputs-dir /path/to/outputs --out-dir ./caption_sanity_prompted \
      --condition prompted --prompt-json prompts.json --variant-indices 1
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from google import genai
from google.genai import types


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "start_time_sec": {"type": "number", "description": "Event onset in seconds from video start."},
        "end_time_sec": {"type": "number", "description": "Event offset in seconds from video start."},
        "modality": {"type": "string", "enum": ["audio", "visual", "audio-visual"]},
        "caption": {"type": "string", "description": "Short open-vocabulary description of the event."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["start_time_sec", "end_time_sec", "modality", "caption", "confidence"],
}

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "global_caption": {
            "type": "string",
            "description": "One- or two-sentence summary of the whole clip (scene, subjects, overall action).",
        },
        "events": {
            "type": "array",
            "items": EVENT_SCHEMA,
            "description": "All distinct audio, visual, and audio-visual events with timestamps, in chronological order.",
        },
        "speech_transcript": {
            "type": "string",
            "description": "Verbatim transcript of any speech, or empty string if no speech.",
        },
        "notes": {
            "type": "string",
            "description": "Anything ambiguous or uncertain (e.g., low audio quality, occlusion, unclear event boundaries).",
        },
    },
    "required": ["global_caption", "events", "speech_transcript", "notes"],
}


SYSTEM_PROMPT_BLIND = """You are a careful audio-visual event annotator.

You will watch a short generated video WITH audio. Your job:

1. Identify every distinct event in the clip. An event may be:
   - "visual": something visible happens with no matched sound (e.g., a silent gesture),
   - "audio": a sound with no clearly visible source on screen,
   - "audio-visual": a visible action with its corresponding sound (e.g., hands clap and a clap is heard).
2. For each event, report onset and offset timestamps in SECONDS with one decimal
   place of precision where possible (e.g., 1.3, not "around 1 second").
3. Write a short, concrete caption for each event. Describe only what you can
   actually see or hear. Do NOT guess intent or invent events.
4. If the same action repeats (e.g., three knocks), report each repetition as a
   separate event so the count is explicit.
5. Transcribe any speech verbatim.
6. Report events in chronological order by onset.

Be conservative: if you are unsure whether a sound or action occurred, either omit
it or mark confidence as "low" and explain in notes. Precision of timestamps and
faithfulness of captions matter more than completeness of interpretation."""

SYSTEM_PROMPT_PROMPTED_SUFFIX = """

You are also given the text prompt that was used to GENERATE this video, plus the
list of intended events. Use them only as vocabulary hints for naming events.
Do NOT assume the intended events actually occur: report only what is truly
present in the video, including missing or extra events."""


USER_TEXT_BLIND = (
    "Annotate this video. Return timestamped captions for every audio, visual, "
    "and audio-visual event, a global caption, and a speech transcript, following "
    "the JSON schema."
)


# ---------------------------------------------------------------------------
# Helpers (conventions follow new_eval__8_.py)
# ---------------------------------------------------------------------------

def find_video_files(outputs_dir: Path) -> List[Path]:
    return sorted(p for p in outputs_dir.rglob("*.mp4") if p.is_file())


def infer_item_id_from_path(video_path: Path) -> str:
    return video_path.parent.name


def parse_variant_index(filename: str) -> Optional[int]:
    m = re.search(r"_v(\d+)_", filename)
    return int(m.group(1)) if m else None


def load_prompt_items(json_path: Path) -> Dict[str, dict]:
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        raise ValueError("--prompt-json must contain a list of item dictionaries.")
    out: Dict[str, dict] = {}
    for it in items:
        item_id = str(it.get("id") or it.get("item_id") or "").strip()
        if item_id:
            out[item_id] = it
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
            raise TimeoutError(f"Timed out waiting for ACTIVE: {getattr(current, 'name', 'unknown file')}")
        time.sleep(poll_seconds)
        current = client.files.get(name=current.name)


def parse_model_json(raw_text: str) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def build_prompted_user_text(item_meta: dict) -> str:
    prompt_text = str(item_meta.get("prompt") or item_meta.get("text") or "")
    events = item_meta.get("events") or item_meta.get("content") or {}
    return (
        USER_TEXT_BLIND
        + "\n\n--- Generation context (hints only; verify against the actual video) ---\n"
        + f"Generation prompt: {prompt_text}\n"
        + f"Intended events (may or may not appear): {json.dumps(events, ensure_ascii=False)}"
    )


def caption_video(
    client: genai.Client,
    model_name: str,
    video_path: Path,
    condition: str,
    item_meta: Optional[dict],
    media_fps: Optional[float],
    thinking_level: Optional[str],
    timeout_seconds: float,
) -> dict:
    uploaded = client.files.upload(file=str(video_path))
    uploaded = wait_until_active(client, uploaded, poll_seconds=5.0, timeout_seconds=timeout_seconds)

    system_prompt = SYSTEM_PROMPT_BLIND
    user_text = USER_TEXT_BLIND
    if condition == "prompted":
        system_prompt += SYSTEM_PROMPT_PROMPTED_SUFFIX
        user_text = build_prompted_user_text(item_meta or {})

    config_kwargs = {
        "response_mime_type": "application/json",
        "response_json_schema": RESULT_SCHEMA,
        "system_instruction": system_prompt,
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
    parsed["_raw_output"] = raw_text
    parsed["_uploaded_file_name"] = getattr(uploaded, "name", "")
    return parsed


# ---------------------------------------------------------------------------
# Outputs: CSV + review sheet
# ---------------------------------------------------------------------------

CSV_FIELDNAMES = [
    "video_relpath", "item_id", "variant_index", "condition",
    "event_index", "start_time_sec", "end_time_sec", "modality",
    "caption", "confidence", "global_caption", "speech_transcript", "notes",
]


def write_summary_csv(out_dir: Path, rows: List[dict]) -> Path:
    path = out_dir / "summary.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    return path


RUBRIC_BLOCK = """
**Manual review rubric (fill while watching; decided before scoring):**

| # | Criterion | Pass condition | Result (P/F) | Notes |
|---|-----------|----------------|--------------|-------|
| 1 | Onset accuracy | Each real event's predicted onset within ±0.5 s | | |
| 2 | Event coverage | No salient audio/visual event missing | | |
| 3 | No hallucination | No predicted event absent from the video | | |
| 4 | Modality correctness | audio / visual / audio-visual labels correct | | |
| 5 | Count fidelity | Repeated actions reported once per repetition | | |
| 6 | Speech transcript | Verbatim within minor punctuation differences (N/A if no speech) | | |
"""


def write_review_sheet(
    out_dir: Path,
    per_video: List[dict],
    condition: str,
    model_name: str,
    seed: int,
    total_pool: int,
) -> Path:
    lines = [
        "# Gemini Timestamp+Caption Sanity Check — Review Sheet",
        "",
        f"- Model: `{model_name}`  |  Condition: `{condition}`  |  Sampling seed: `{seed}`",
        f"- Sampled {len(per_video)} of {total_pool} videos (uniform random, seeded).",
        "- Verdict rule (pre-registered): a video PASSES only if rubric rows 1–5 all pass"
        " (row 6 when speech exists). Record borderline cases in Notes rather than"
        " silently rounding up.",
        "",
    ]
    for i, v in enumerate(per_video, 1):
        r = v["result"]
        lines += [
            f"## Video {i}: `{v['relpath']}`",
            "",
            f"- item_id: `{v['item_id']}`  |  variant: `{v['variant_index']}`",
        ]
        if v.get("gen_prompt"):
            lines.append(f"- Generation prompt (for your reference): {v['gen_prompt']}")
        lines += [
            "",
            f"**Global caption (Gemini):** {r.get('global_caption', '')}",
            "",
            "**Predicted events:**",
            "",
            "| # | start (s) | end (s) | modality | caption | conf |",
            "|---|-----------|---------|----------|---------|------|",
        ]
        for j, ev in enumerate(r.get("events", []), 1):
            lines.append(
                f"| {j} | {ev.get('start_time_sec')} | {ev.get('end_time_sec')} "
                f"| {ev.get('modality')} | {ev.get('caption')} | {ev.get('confidence')} |"
            )
        transcript = r.get("speech_transcript", "")
        lines += [
            "",
            f"**Speech transcript:** {transcript if transcript else '(none)'}",
            f"**Gemini notes:** {r.get('notes', '')}",
            RUBRIC_BLOCK,
            "**Overall verdict (P/F):** ____",
            "",
            "---",
            "",
        ]
    path = out_dir / "review_sheet.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini timestamp+caption sanity check (manual review, N random videos).")
    parser.add_argument("--outputs-dir", type=Path, required=True, help="Directory containing item_id/*.mp4 videos.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for JSON/CSV/review sheet outputs.")
    parser.add_argument("--num-videos", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (reproducible draw).")
    parser.add_argument("--model", type=str, default="gemini-3.1-pro-preview")
    parser.add_argument("--condition", type=str, default="blind", choices=["blind", "prompted"])
    parser.add_argument("--prompt-json", type=Path, default=None, help="Prompt items JSON (required for --condition prompted; optional otherwise, used to show the generation prompt in the review sheet).")
    parser.add_argument("--variant-indices", type=int, nargs="*", default=None, help="Restrict sampling to these variant indices, e.g. --variant-indices 1")
    parser.add_argument("--media-fps", type=float, default=24.0, help="FPS metadata passed to Gemini. Use <=0 to omit.")
    parser.add_argument("--thinking-level", type=str, default="high", choices=["low", "high", "none"])
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    args = parser.parse_args()

    if args.condition == "prompted" and args.prompt_json is None:
        parser.error("--condition prompted requires --prompt-json")

    item_meta_map: Dict[str, dict] = {}
    if args.prompt_json is not None:
        item_meta_map = load_prompt_items(args.prompt_json)
        print(f"[INFO] Loaded {len(item_meta_map)} prompt items")

    pool = find_video_files(args.outputs_dir)
    if args.variant_indices is not None:
        allowed = set(args.variant_indices)
        pool = [p for p in pool if parse_variant_index(p.name) in allowed]
    if not pool:
        raise RuntimeError(f"No matching mp4 files under {args.outputs_dir}")

    rng = random.Random(args.seed)
    sampled = sorted(rng.sample(pool, min(args.num_videos, len(pool))))
    print(f"[INFO] Pool={len(pool)} videos; sampled {len(sampled)} with seed={args.seed}:")
    for p in sampled:
        print(f"  - {p.relative_to(args.outputs_dir)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    csv_rows: List[dict] = []
    per_video: List[dict] = []

    for video_path in sampled:
        relpath = str(video_path.relative_to(args.outputs_dir))
        item_id = infer_item_id_from_path(video_path)
        variant_index = parse_variant_index(video_path.name)
        item_meta = item_meta_map.get(item_id)
        print(f"[CAPTION] {relpath}")

        try:
            result = caption_video(
                client=client,
                model_name=args.model,
                video_path=video_path,
                condition=args.condition,
                item_meta=item_meta,
                media_fps=args.media_fps if args.media_fps and args.media_fps > 0 else None,
                thinking_level=args.thinking_level,
                timeout_seconds=args.timeout_seconds,
            )
        except Exception as exc:
            print(f"  [ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
            result = {"global_caption": f"ERROR: {exc}", "events": [], "speech_transcript": "", "notes": ""}

        json_path = args.out_dir / f"captions_{video_path.stem}.json"
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {len(result.get('events', []))} events | saved {json_path.name}")

        gen_prompt = ""
        if item_meta:
            gen_prompt = str(item_meta.get("prompt") or item_meta.get("text") or "")

        per_video.append({
            "relpath": relpath,
            "item_id": item_id,
            "variant_index": variant_index,
            "gen_prompt": gen_prompt,
            "result": result,
        })

        events = result.get("events", [])
        base = {
            "video_relpath": relpath, "item_id": item_id, "variant_index": variant_index,
            "condition": args.condition, "global_caption": result.get("global_caption", ""),
            "speech_transcript": result.get("speech_transcript", ""), "notes": result.get("notes", ""),
        }
        if events:
            for j, ev in enumerate(events, 1):
                csv_rows.append({**base, "event_index": j,
                                 "start_time_sec": ev.get("start_time_sec"),
                                 "end_time_sec": ev.get("end_time_sec"),
                                 "modality": ev.get("modality"),
                                 "caption": ev.get("caption"),
                                 "confidence": ev.get("confidence")})
        else:
            csv_rows.append({**base, "event_index": 0, "start_time_sec": "", "end_time_sec": "",
                             "modality": "", "caption": "(no events returned)", "confidence": ""})

    csv_path = write_summary_csv(args.out_dir, csv_rows)
    sheet_path = write_review_sheet(args.out_dir, per_video, args.condition, args.model, args.seed, len(pool))
    print(f"[DONE] CSV: {csv_path}")
    print(f"[DONE] Review sheet: {sheet_path}")
    print("[NEXT] Open review_sheet.md side-by-side with each video and fill the rubric.")


if __name__ == "__main__":
    main()
