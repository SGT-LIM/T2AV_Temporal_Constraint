#!/usr/bin/env python3
"""V-axis-only Gemini evaluator for T2AV videos.

This script reuses parsing/helpers from your existing eval_5axis_per_event_mmpose.py,
but asks the model to return ONLY visual_event_correctness per event.
"""
from __future__ import annotations

import argparse, csv, importlib.util, json, re, sys, time
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

V_SCHEMA = {
    "type": "object",
    "properties": {
        "visual_event_correctness": {
            "type": "object",
            "properties": {
                "per_event": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string"},
                            "label": {"type": "string", "enum": ["yes", "no"]},
                            "reason": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["event_id", "label", "reason", "evidence"],
                    },
                }
            },
            "required": ["per_event"],
        },
        "observed_behavior_summary": {"type": "string"},
    },
    "required": ["visual_event_correctness", "observed_behavior_summary"],
}

CSV_FIELDS = [
    "video_relpath", "video_file", "item_id", "variant_index",
    "label_name", "label_type", "modality_combination", "event_summary", "temporal_type",
    "event_id", "event_kind", "event_label",
    "visual_event_correctness", "visual_event_correctness_reason", "visual_event_correctness_evidence",
    "model", "backend", "media_fps", "temperature", "seed",
    "uploaded_file_name", "uploaded_file_uri", "user_prompt", "raw_output",
]


def load_base(base_script: Path):
    spec = importlib.util.spec_from_file_location("base_eval", str(base_script))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import base script: {base_script}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["base_eval"] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", flags=re.S)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}


def build_v_system_prompt() -> str:
    return """You are a strict visual-only evaluator for text-to-audio-video generation.

Your job:
- Inspect ONLY the visual content of the video.
- Evaluate ONLY visual_event_correctness, per target event.
- Do NOT evaluate audio correctness, audio-visual binding, temporal relation, temporal count, or constraint compliance.
- Be conservative: unclear, weak, ambiguous, incomplete, mismatched, or approximate visual evidence should be judged as failure.
- Do not reward a video merely because it is plausible; the visible behavior must satisfy the original prompt-specific visual requirement.

Visual Event Correctness definition:
- For a speech event: judge only whether the speaker's face/mouth is visible when required and shows plausible speaking mouth/lip motion. Do NOT judge whether the spoken word is correct.
- For a silent action event: judge whether the required visible action/pose is clearly visible and correctly performed.
- For a sounding action event: judge whether the required visible motion/contact/action is clearly visible and correctly performed. Do NOT judge whether the corresponding sound is audible.

Laterality and perspective:
- If the prompt specifies the person's left/right body side, judge body-side laterality, not viewer-left/viewer-right.
- If left/right is ambiguous, do not give credit for a side-specific requirement unless the target body side is clearly supported.

Output rules:
- Return ONLY the requested JSON object.
- visual_event_correctness must contain one per_event entry for EVERY target event_id listed in the user message.
- Each entry must contain event_id, label yes/no, reason, and evidence.
- Keep reason/evidence concise and concrete."""


def build_v_user_text(base, item_meta: dict) -> str:
    events = item_meta.get("events", []) or []
    scoring = base.build_scoring_events(item_meta)
    event_lines = "\n".join(f"- {base.describe_event(e)}" for e in events) if events else "- See original prompt."
    target_lines = []
    for se in scoring:
        target_lines.append(
            f'- {se["event_id"]} ({base.humanize_token(se["kind"])}): "{base.humanize_token(se["label"])}"'
        )
    target_text = "\n".join(target_lines) if target_lines else "- No parsed events."

    return f"""Task: Evaluate ONLY the V-axis / visual_event_correctness for this generated video.

Original generation prompt:
{item_meta.get('generated_prompt', '')}

Item metadata:
- item_id: {item_meta.get('item_id', '')}
- modality_combination: {item_meta.get('modality_combination', '')}
- content: {json.dumps(item_meta.get('content', {}) or {}, ensure_ascii=False)}
- temporal_constraint: {json.dumps(item_meta.get('temporal_constraint', {}) or {}, ensure_ascii=False)}
- scene_hint: {item_meta.get('scene_hint', '')}
- camera_hint: {item_meta.get('camera_hint', '')}

Target events inferred from content:
{event_lines}

Per-event V-axis scoring targets. Use these exact event_id strings:
{target_text}

Shared visual-relevant definitions:
{base.GUIDELINE_DEFINITIONS}

V-axis criteria:
{base.build_visual_axis_criteria(events)}

Decision rules:
- Return one visual_event_correctness entry for every target event_id above.
- For speech, judge visible speaking/mouth/lip motion only, not speech audio/content.
- For sounding actions, judge visible motion/contact only, not sound.
- If visual evidence is missing, ambiguous, wrong side/wrong body part, incomplete, or unclear, label that event "no".
- Return JSON only."""


def wait_until_active(client, uploaded_file, timeout_seconds: float):
    start = time.time()
    cur = uploaded_file
    while True:
        state = getattr(getattr(cur, "state", None), "name", None)
        if state == "ACTIVE":
            return cur
        if state == "FAILED":
            raise RuntimeError(f"Gemini file processing failed: {getattr(cur, 'name', '')}")
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out waiting for Gemini upload: {getattr(cur, 'name', '')}")
        time.sleep(5)
        cur = client.files.get(name=cur.name)


def eval_one(base, client, args, video_path: Path, item_meta: dict) -> list[dict]:
    uploaded = client.files.upload(file=str(video_path))
    uploaded = wait_until_active(client, uploaded, args.timeout_seconds)
    user_text = build_v_user_text(base, item_meta)

    if args.media_fps and args.media_fps > 0:
        contents = [
            types.Part(
                file_data=types.FileData(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
                video_metadata=types.VideoMetadata(fps=args.media_fps),
            ),
            user_text,
        ]
    else:
        contents = [uploaded, user_text]

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=V_SCHEMA,
        system_instruction=build_v_system_prompt(),
        temperature=0.0,
        seed=42,
    )
    if args.thinking_level.lower() != "none":
        config.thinking_config = types.ThinkingConfig(thinking_level=args.thinking_level)

    resp = client.models.generate_content(model=args.model, contents=contents, config=config)
    raw = resp.text or ""
    parsed = parse_json(raw)
    scoring_events = base.build_scoring_events(item_meta)
    v_rows = base.normalize_label_per_event(parsed.get("visual_event_correctness"), scoring_events, "visual_event_correctness")

    relpath = str(video_path.relative_to(args.outputs_dir))
    out = []
    for vr in v_rows:
        out.append({
            "video_relpath": relpath,
            "video_file": video_path.name,
            "item_id": item_meta.get("item_id", base.infer_item_id_from_path(video_path)),
            "variant_index": base.parse_variant_index(video_path.name),
            "label_name": item_meta.get("label", ""),
            "label_type": base.label_type_from_modality(item_meta.get("modality_combination", "")),
            "modality_combination": item_meta.get("modality_combination", ""),
            "event_summary": " | ".join(base.describe_event(e) for e in item_meta.get("events", []) or []),
            "temporal_type": base.temporal_type_label(item_meta.get("temporal_constraint", {}) or {}),
            "event_id": vr.get("event_id", ""),
            "event_kind": vr.get("event_kind", ""),
            "event_label": vr.get("event_label", ""),
            "visual_event_correctness": vr.get("label", ""),
            "visual_event_correctness_reason": vr.get("reason", ""),
            "visual_event_correctness_evidence": vr.get("evidence", ""),
            "model": args.model,
            "backend": "gemini",
            "media_fps": args.media_fps,
            "temperature": 0.0,
            "seed": 42,
            "uploaded_file_name": getattr(uploaded, "name", ""),
            "uploaded_file_uri": getattr(uploaded, "uri", ""),
            "user_prompt": user_text,
            "raw_output": raw,
        })
    return out


def ensure_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()


def append_rows(path: Path, rows: list[dict]):
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})


def done_keys(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        return {(r.get("video_relpath", ""), r.get("event_id", "")) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-script", type=Path, default=Path("eval_5axis_per_event_mmpose.py"))
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--outputs-dir", type=Path, required=True)
    ap.add_argument("--output-csv", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--media-fps", type=float, default=24.0)
    ap.add_argument("--thinking-level", default="none", choices=["none", "low", "high"])
    ap.add_argument("--timeout-seconds", type=float, default=600.0)
    ap.add_argument("--relative-only", action="store_true")
    ap.add_argument("--modality-filter", default=None)
    ap.add_argument("--item-overrides-json", type=Path, default=None)
    ap.add_argument("--variant-indices", type=int, nargs="*", default=None)
    ap.add_argument("--max-videos", type=int, default=None)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    base = load_base(args.base_script)
    items = base.load_prompt_items(args.prompt_json)
    overrides = base.load_json_if_exists(args.item_overrides_json) if args.item_overrides_json else {}
    meta_map = base.build_item_meta_map(items, args.modality_filter, overrides, args.relative_only)

    client = genai.Client()
    ensure_header(args.output_csv)
    existing = set() if args.overwrite else done_keys(args.output_csv)

    videos = base.find_video_files(args.outputs_dir)
    n = 0
    for vp in videos:
        if args.variant_indices is not None and base.parse_variant_index(vp.name) not in set(args.variant_indices):
            continue
        item_id = base.infer_item_id_from_path(vp)
        if item_id not in meta_map:
            print(f"[SKIP] no prompt metadata for {item_id}")
            continue
        relpath = str(vp.relative_to(args.outputs_dir))
        # skip only if all event rows for that video already exist
        if not args.overwrite and any(k[0] == relpath for k in existing):
            print(f"[SKIP] already evaluated: {relpath}")
            continue
        print(f"[EVAL][Gemini V] {relpath}")
        rows = eval_one(base, client, args, vp, meta_map[item_id])
        append_rows(args.output_csv, rows)
        n += 1
        if args.max_videos and n >= args.max_videos:
            break
    print(f"[DONE] evaluated {n} videos -> {args.output_csv}")


if __name__ == "__main__":
    main()
