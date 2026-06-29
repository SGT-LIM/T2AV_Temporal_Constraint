#!/usr/bin/env python3
"""V-axis-only Molmo2 evaluator for T2AV videos.

Uses the same V-axis prompt format as eval_vaxis_gemini.py, but runs Molmo2 locally
through Hugging Face Transformers.
"""
from __future__ import annotations

import argparse, csv, importlib.util, json, re, sys
from pathlib import Path

import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

try:
    from molmo_utils import process_vision_info
except Exception:
    process_vision_info = None

CSV_FIELDS = [
    "video_relpath", "video_file", "item_id", "variant_index",
    "label_name", "label_type", "modality_combination", "event_summary", "temporal_type",
    "event_id", "event_kind", "event_label",
    "visual_event_correctness", "visual_event_correctness_reason", "visual_event_correctness_evidence",
    "model", "backend", "max_fps", "temperature", "seed", "user_prompt", "raw_output",
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


def build_v_prompt(base, item_meta: dict) -> str:
    events = item_meta.get("events", []) or []
    scoring = base.build_scoring_events(item_meta)
    event_lines = "\n".join(f"- {base.describe_event(e)}" for e in events) if events else "- See original prompt."
    target_lines = "\n".join(
        f'- {se["event_id"]} ({base.humanize_token(se["kind"])}): "{base.humanize_token(se["label"])}"'
        for se in scoring
    ) or "- No parsed events."

    return f"""You are a strict visual-only evaluator for text-to-audio-video generation.

Evaluate ONLY visual_event_correctness for the generated video. Do NOT evaluate audio correctness, audio-visual binding, temporal relation, temporal count, or constraint compliance.

Visual Event Correctness definition:
- For a speech event: judge only whether the speaker's face/mouth is visible when required and shows plausible speaking mouth/lip motion. Do NOT judge whether the spoken word is correct.
- For a silent action event: judge whether the required visible action/pose is clearly visible and correctly performed.
- For a sounding action event: judge whether the required visible motion/contact/action is clearly visible and correctly performed. Do NOT judge whether the corresponding sound is audible.
- Be conservative: unclear, weak, ambiguous, incomplete, mismatched, wrong-side, or approximate visual evidence should be judged as failure.
- If the prompt specifies left/right body side, judge body-side laterality, not viewer-left/viewer-right.

Original generation prompt:
{item_meta.get('generated_prompt', '')}

Item metadata:
- item_id: {item_meta.get('item_id', '')}
- modality_combination: {item_meta.get('modality_combination', '')}
- content: {json.dumps(item_meta.get('content', {}) or {}, ensure_ascii=False)}
- temporal_constraint: {json.dumps(item_meta.get('temporal_constraint', {}) or {}, ensure_ascii=False)}

Target events inferred from content:
{event_lines}

Per-event V-axis scoring targets. Use these exact event_id strings:
{target_lines}

Shared visual-relevant definitions:
{base.GUIDELINE_DEFINITIONS}

V-axis criteria:
{base.build_visual_axis_criteria(events)}

Return JSON only in exactly this shape:
{{
  "visual_event_correctness": {{
    "per_event": [
      {{"event_id": "event_1", "label": "yes" or "no", "reason": "...", "evidence": "..."}}
    ]
  }},
  "observed_behavior_summary": "..."
}}
"""


def load_molmo(model_id: str):
    processor = AutoProcessor.from_pretrained(
        model_id, trust_remote_code=True, use_fast=False
    )
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, trust_remote_code=True, dtype="auto", device_map="auto"
    )
    model.config.use_cache = False
    model.generation_config.use_cache = False
    model.eval()
    return processor, model


def molmo_generate(processor, model, video_path: Path, prompt: str, max_fps: float, max_new_tokens: int) -> str:
    # Molmo2 HF docs support video content in chat messages; process_vision_info is used for robust local video handling.
    video_entry = {"type": "video", "video": str(video_path)}
    if max_fps and max_fps > 0:
        video_entry["max_fps"] = max_fps
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}, video_entry]}]

    if process_vision_info is not None:
        _, videos, video_kwargs = process_vision_info(messages)
        videos, video_metadatas = zip(*videos)
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(
            videos=list(videos),
            video_metadata=list(video_metadatas),
            text=text,
            padding=True,
            return_tensors="pt",
            **video_kwargs,
        )
    else:
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True
        )

    inputs = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in inputs.items()}
    with torch.inference_mode():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            # temperature=False,
            use_cache=False,
        )
    prompt_len = inputs["input_ids"].size(1)
    generated_tokens = generated_ids[0, prompt_len:]
    return processor.tokenizer.decode(generated_tokens, skip_special_tokens=True)


def eval_one(base, processor, model, args, video_path: Path, item_meta: dict) -> list[dict]:
    prompt = build_v_prompt(base, item_meta)
    raw = molmo_generate(processor, model, video_path, prompt, args.max_fps, args.max_new_tokens)
    parsed = parse_json(raw)
    scoring_events = base.build_scoring_events(item_meta)
    v_rows = base.normalize_label_per_event(parsed.get("visual_event_correctness"), scoring_events, "visual_event_correctness")

    relpath = str(video_path.relative_to(args.outputs_dir))
    return [{
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
        "backend": "molmo2",
        "max_fps": args.max_fps,
        "temperature": 0.0,
        "seed": args.seed,
        "user_prompt": prompt,
        "raw_output": raw,
    } for vr in v_rows]


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


def done_relpaths(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8", newline="") as f:
        return {r.get("video_relpath", "") for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-script", type=Path, default=Path("eval_5axis_per_event_mmpose.py"))
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--outputs-dir", type=Path, required=True)
    ap.add_argument("--output-csv", type=Path, required=True)
    ap.add_argument("--model", default="allenai/Molmo2-8B")
    ap.add_argument("--max-fps", type=float, default=8.0)
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--relative-only", action="store_true")
    ap.add_argument("--modality-filter", default=None)
    ap.add_argument("--item-overrides-json", type=Path, default=None)
    ap.add_argument("--variant-indices", type=int, nargs="*", default=None)
    ap.add_argument("--max-videos", type=int, default=None)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    base = load_base(args.base_script)
    items = base.load_prompt_items(args.prompt_json)
    overrides = base.load_json_if_exists(args.item_overrides_json) if args.item_overrides_json else {}
    meta_map = base.build_item_meta_map(items, args.modality_filter, overrides, args.relative_only)

    processor, model = load_molmo(args.model)
    ensure_header(args.output_csv)
    done = set() if args.overwrite else done_relpaths(args.output_csv)

    videos = base.find_video_files(args.outputs_dir)
    n = 0
    wanted_variants = set(args.variant_indices) if args.variant_indices is not None else None
    for vp in videos:
        if wanted_variants is not None and base.parse_variant_index(vp.name) not in wanted_variants:
            continue
        item_id = base.infer_item_id_from_path(vp)
        if item_id not in meta_map:
            print(f"[SKIP] no prompt metadata for {item_id}")
            continue
        relpath = str(vp.relative_to(args.outputs_dir))
        if not args.overwrite and relpath in done:
            print(f"[SKIP] already evaluated: {relpath}")
            continue
        print(f"[EVAL][Molmo2 V] {relpath}")
        rows = eval_one(base, processor, model, args, vp, meta_map[item_id])
        append_rows(args.output_csv, rows)
        n += 1
        if args.max_videos and n >= args.max_videos:
            break
    print(f"[DONE] evaluated {n} videos -> {args.output_csv}")


if __name__ == "__main__":
    main()
