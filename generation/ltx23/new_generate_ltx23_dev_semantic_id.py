#!/usr/bin/env python3
"""
Generate T2AV temporal-constraint videos with LTX-2.3 dev using the official
ltx_pipelines.ti2vid_one_stage CLI, and write one metadata .txt next to each .mp4.

Default output layout:
  <output_root>/<item_id>/<item_id>_v<variant>_raw.mp4
  <output_root>/<item_id>/<item_id>_v<variant>_raw.txt

This script is designed to reproduce the style of the previously saved raw files.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_PROMPT_JSON = Path(
    # "/home/coder/T2AV/prompts/generated/6-comb_temporal_selected_specs_prompts.json"
    "/home/coder/T2AV/new_prompts/generated/relative_50_v3_prompts.json"
)
DEFAULT_OUTPUT_ROOT = Path(
    # "/home/coder/T2V_Gen/hf_datasets/T2AV_TemporalConstraint/"
    # "LTX-2.3/3-seed42-dev_outputs-comb-temporal_reorganized-test"
    # "/home/coder/T2V_Gen/LTX-2/outputs/refined_prompt_ver3"
    "./outputs/50_prompts"
)
DEFAULT_PYTHON_BIN = Path("/home/coder/miniforge3/envs/ltx23/bin/python")
DEFAULT_LTX_REPO = Path("/home/coder/T2V_Gen/LTX-2")
DEFAULT_CHECKPOINT = Path(
    "/home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors"
)
DEFAULT_GEMMA_ROOT = Path("/home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it")

SUPPORTED_RELATION_TYPES = {"synchronization", "sync_count", "order", "order_count"}

MODALITY_TO_CATEGORY = {
    "Speech": "speech",
    "Action (silent)": "silent",
    "Action (sounding)": "sounding",
    "Speech + Action (silent)": "speech_silent",
    "Speech + Action (sounding)": "speech_sounding",
    "Action (silent) + Action (sounding)": "silent_sounding",
    "Speech + Action (silent) + Action (sounding)": "speech_silent_sounding",
}
LABEL_ORDER = ("speech", "silent_action", "sounding_action")


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(data).__name__}")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Expected item at index {i} to be an object, got {type(item).__name__}")
        for key in ("item_id", "generated_prompt", "temporal_constraint"):
            if key not in item:
                raise ValueError(f"Missing {key} at index {i}")
        if not item["generated_prompt"]:
            raise ValueError(f"Empty generated_prompt for item {item['item_id']}")

        tc = item["temporal_constraint"]
        if not isinstance(tc, dict):
            raise ValueError(f"temporal_constraint must be an object for item {item['item_id']}")
        relation_type = tc.get("relation_type")
        timing_type = tc.get("timing_type")
        if timing_type != "relative":
            raise ValueError(
                f"This script is currently configured for relative prompts; "
                f"item {item['item_id']} has timing_type={timing_type!r}"
            )
        if relation_type not in SUPPORTED_RELATION_TYPES:
            raise ValueError(
                f"Unsupported relation_type={relation_type!r} for item {item['item_id']}. "
                f"Supported: {sorted(SUPPORTED_RELATION_TYPES)}"
            )
    return data


def infer_category(item: dict[str, Any]) -> str:
    modality = item.get("modality_combination", "")
    if modality in MODALITY_TO_CATEGORY:
        return MODALITY_TO_CATEGORY[modality]
    # Conservative fallback for future modality strings.
    return (
        modality.lower()
        .replace("speech", "speech")
        .replace("action (silent)", "silent")
        .replace("action (sounding)", "sounding")
        .replace(" + ", "_")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
    )


def safe_token(text: Any) -> str:
    text = str(text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def event_to_label_token(event: dict[str, Any]) -> str:
    modality = event.get("modality")

    if modality == "speech":
        return safe_token(event.get("text", event.get("id", "speech")))

    if modality in {"silent_action", "sounding_action"}:
        return safe_token(event.get("action", event.get("id", modality)))

    return safe_token(event.get("id", "unknown"))


def infer_label(item: dict[str, Any]) -> str:
    """
    Create a compact human-readable label from the new schema.

    Current benchmark example:
      speech + thumbs_up + slapping_the_thigh
      -> help_thumbs_up_slapping_the_thigh

    For order_count items, append _xN when N > 1 so metadata makes the
    repeated-count target obvious even without re-reading temporal_constraint.
    """
    events = item.get("events")
    if isinstance(events, list) and events:
        label = "_".join(event_to_label_token(ev) for ev in events)
    else:
        # Backward compatibility for old schema.
        content = item.get("content", {})
        if not isinstance(content, dict):
            label = "unknown"
        else:
            tokens = []
            for key in LABEL_ORDER:
                if key not in content:
                    continue
                value = content[key]

                if isinstance(value, str):
                    tokens.append(safe_token(value))
                elif isinstance(value, dict):
                    if key == "speech":
                        tokens.append(safe_token(value.get("text", key)))
                    else:
                        tokens.append(safe_token(value.get("action", key)))

            label = "_".join(tokens) if tokens else "unknown"

    tc = item.get("temporal_constraint", {})
    value = tc.get("value", {}) if isinstance(tc, dict) else {}
    if tc.get("relation_type") == "order_count" and isinstance(value, dict):
        count = value.get("count")
        if count not in (None, 1, "1"):
            label = f"{label}_x{count}"
    return label


def metadata_temporal_constraint(item: dict[str, Any]) -> dict[str, Any]:
    """
    Store the temporal constraint exactly as used by the new schema:
      relation_type + timing_type + value
    """
    return copy.deepcopy(item.get("temporal_constraint", {}))


def build_full_json_prompt(item: dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, indent=2)

def parse_item_filter(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def seed_for_item(index: int, variant: int, base_seed: int, seed_mode: str, num_items: int, variants: int) -> int:
    """
    v1 always becomes base_seed + index.
    For index=9 and base_seed=42, v1 seed is 51, matching the recovered raw txt.
    """
    if seed_mode == "adjacent":
        return base_seed + index + (variant - 1)
    if seed_mode == "block":
        return base_seed + index + (variant - 1) * num_items
    if seed_mode == "global":
        return base_seed + index * variants + (variant - 1)
    raise ValueError(f"Unknown seed_mode: {seed_mode}")


def build_ltx_command(
    *,
    python_bin: Path,
    checkpoint_path: Path,
    gemma_root: Path,
    prompt: str,
    output_path: Path,
    width: int,
    height: int,
    num_frames: int,
    frame_rate: float,
    seed: int,
    extra_ltx_args: str,
) -> list[str]:
    cmd = [
        str(python_bin),
        "-m",
        "ltx_pipelines.ti2vid_one_stage",
        "--checkpoint-path",
        str(checkpoint_path),
        "--gemma-root",
        str(gemma_root),
        "--prompt",
        prompt,
        "--output-path",
        str(output_path),
        "--width",
        str(width),
        "--height",
        str(height),
        "--num-frames",
        str(num_frames),
        "--frame-rate",
        str(frame_rate),
        "--seed",
        str(seed),
    ]
    if extra_ltx_args.strip():
        cmd.extend(shlex.split(extra_ltx_args))
    return cmd


def write_metadata_txt(
    *,
    txt_path: Path,
    index: int,
    item: dict[str, Any],
    seed: int,
    command: list[str],
    compact_item_id: str,
) -> None:
    tc = metadata_temporal_constraint(item)
    value = tc.get("value", {}) if isinstance(tc, dict) else {}
    lines = [
        f"index: {index}",
        f"compact_item_id: {compact_item_id}",
        f"event_signature: {event_signature(item)}",
        f"category: {infer_category(item)}",
        f"label: {infer_label(item)}",
        f"seed: {seed}",
        f"modality_combination: {item.get('modality_combination', '')}",
        "subjects: " + json.dumps(item.get("subjects", []), ensure_ascii=False),
        "events: " + json.dumps(item.get("events", []), ensure_ascii=False),
        "content: " + json.dumps(item.get("content", {}), ensure_ascii=False),
        "temporal_constraint: " + json.dumps(tc, ensure_ascii=False),
        f"temporal_relation_type: {tc.get('relation_type', '') if isinstance(tc, dict) else ''}",
        f"temporal_timing_type: {tc.get('timing_type', '') if isinstance(tc, dict) else ''}",
        "temporal_sequence: " + json.dumps(value.get("sequence", value.get("events", [])), ensure_ascii=False),
        "temporal_count: " + json.dumps(value.get("count", ""), ensure_ascii=False),
        f"scene_hint: {item.get('scene_hint', '')}",
        f"camera_hint: {item.get('camera_hint', '')}",
        f"prompt: {item['generated_prompt']}",
        "command: " + shlex.join(command),
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_generation_args(args: argparse.Namespace) -> None:
    if args.width % 32 != 0 or args.height % 32 != 0:
        raise ValueError("LTX requires width and height to be divisible by 32.")
    if (args.num_frames - 1) % 8 != 0:
        raise ValueError("LTX requires num_frames to be 8*k + 1, e.g., 121.")
    if args.variant_start < 1:
        raise ValueError("--variant-start must be >= 1")
    if args.variants < 1:
        raise ValueError("--variants must be >= 1")

def compact_id(name: str) -> str:
    s = name

    # modality combinations
    s = s.replace(
        "speech_action_silent_action_sounding",
        "Sp_Si_So"
    )
    s = s.replace(
        "speech_action_silent",
        "Sp_Si"
    )
    s = s.replace(
        "speech_action_sounding",
        "Sp_So"
    )
    s = s.replace(
        "action_silent_action_sounding",
        "Si_So"
    )

    # temporal
    # Compound relation names must be handled before their components.
    s = s.replace("order_count", "ord_cnt")
    s = s.replace("sync_count", "sync_cnt")
    s = s.replace("absolute", "abs")
    s = s.replace("relative", "rel")
    s = s.replace("synchronization", "sync")
    s = s.replace("order", "ord")
    s = s.replace("count", "cnt")

    # order chains
    s = s.replace("speech", "Sp")
    s = s.replace("silent_action", "Si")
    s = s.replace("sounding_action", "So")
    s = s.replace("_then_", "_")

    # compress order tail
    s = re.sub(
        r"_ord_((?:Sp|Si|So)(?:_(?:Sp|Si|So))+)$",
        lambda m: "_ord_" + m.group(1).replace("_", ""),
        s,
    )

    s = re.sub(r"_+", "_", s).strip("_")

    return s

EVENT_TOKEN_ALIASES = {
    "thumbs_up": "thumb",
    "raise_open_palm": "palm",
    "slapping_the_thigh": "slap",
    "clapping_hands": "clap",
}


def event_token(event: dict[str, Any]) -> str:
    """Return the concrete event label, not only the modality name."""
    modality = event.get("modality", "")
    if modality == "speech":
        raw = event.get("text") or event.get("id") or "speech"
    else:
        raw = event.get("action") or event.get("text") or event.get("id") or modality or "event"
    raw = str(raw)
    raw = EVENT_TOKEN_ALIASES.get(raw, raw)
    raw = raw.lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return raw or "event"


def event_signature(item: dict[str, Any]) -> str:
    """
    Signature of the actual event types in item['events'].
    This distinguishes help vs stop, thumbs_up vs open_palm, slap vs clap,
    including repeated/interleaved same-modality events.
    """
    events = item.get("events", [])
    if not isinstance(events, list) or not events:
        return "manual"
    return "_".join(event_token(ev) for ev in events)


def generation_id(item: dict[str, Any]) -> str:
    """
    Folder/file id used for saving outputs.

    The old compact_id(item_id) collapses generic ids such as
      speech_action_silent_rel_order_speech_then_silent_action
    into
      Sp_Si_rel_ord_SpSi
    which does not show whether the actual events are help/stop or
    thumbs_up/open_palm. Prefixing the concrete event_signature fixes that.
    """
    item_id = item.get("item_id", "manual_prompt")
    return f"{event_signature(item)}__{compact_id(str(item_id))}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate T2AV videos with LTX-2.3 dev and write raw metadata txt files."
    )
    parser.add_argument("--prompt-json", type=Path, default=DEFAULT_PROMPT_JSON)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--python-bin", type=Path, default=DEFAULT_PYTHON_BIN)
    parser.add_argument("--ltx-repo", type=Path, default=DEFAULT_LTX_REPO)
    parser.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--gemma-root", type=Path, default=DEFAULT_GEMMA_ROOT)

    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--num-frames", type=int, default=121)
    parser.add_argument("--frame-rate", type=float, default=24.0)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--variants", type=int, default=1)
    parser.add_argument("--variant-start", type=int, default=1)
    parser.add_argument(
        "--seed-mode",
        choices=("adjacent", "block", "global"),
        default="adjacent",
        help=(
            "adjacent: v1=base+index, v2=base+index+1; "
            "block: v2 jumps by number of items; global: enumerate all item/variant pairs."
        ),
    )

    parser.add_argument(
        "--item-id",
        type=str,
        default=None,
        help="Optional comma-separated item_id filter, e.g. silent_sounding_count_01,speech_silent_sync_01",
    )
    parser.add_argument("--start-index", type=int, default=None)
    parser.add_argument("--end-index", type=int, default=None, help="Inclusive end index")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate even if .mp4 already exists")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without running them")
    parser.add_argument(
        "--extra-ltx-args",
        type=str,
        default="",
        help='Extra args appended to ltx_pipelines, e.g. "--num-inference-steps 50"',
    )
    parser.add_argument(
        "--manual-prompt",
        type=str,
        default=None,
        help="Directly provide a prompt string instead of loading from JSON"
    )
    args = parser.parse_args()

    validate_generation_args(args)

    # Convert filesystem arguments to absolute paths before launching subprocesses.
    # The LTX command is executed with cwd=args.ltx_repo, so relative output paths
    # would otherwise point inside the LTX repo, not the directory from which this
    # wrapper script was invoked.
    args.prompt_json = args.prompt_json.expanduser().resolve()
    args.output_root = args.output_root.expanduser().resolve()
    args.python_bin = args.python_bin.expanduser().resolve()
    args.ltx_repo = args.ltx_repo.expanduser().resolve()
    args.checkpoint_path = args.checkpoint_path.expanduser().resolve()
    args.gemma_root = args.gemma_root.expanduser().resolve()

    # items = load_items(args.prompt_json)
    if args.manual_prompt is not None:
        items = [{
            "item_id": "manual_prompt",
            "generated_prompt": args.manual_prompt,
            "modality_combination": "manual",
            "events": [],
            "content": {},
            "temporal_constraint": {},
        }]
    else:
        items = load_items(args.prompt_json)
    item_filter = parse_item_filter(args.item_id)
    if item_filter is not None:
        available = {x["item_id"] for x in items}
        missing = sorted(item_filter - available)
        if missing:
            raise ValueError(f"--item-id contains ids not found in JSON: {missing}")

    if not args.dry_run:
        paths_to_check = [
            (args.python_bin, "python binary"),
            (args.checkpoint_path, "checkpoint"),
            (args.gemma_root, "Gemma root"),
        ]
        if args.manual_prompt is None:
            paths_to_check.insert(0, (args.prompt_json, "prompt json"))
        for path, label in paths_to_check:
            if not path.exists():
                raise FileNotFoundError(f"Missing {label}: {path}")
        args.output_root.mkdir(parents=True, exist_ok=True)

    total_jobs = 0
    completed_jobs = 0
    skipped_jobs = 0

    for index, item in enumerate(items):
        if args.start_index is not None and index < args.start_index:
            continue
        if args.end_index is not None and index > args.end_index:
            continue
        if item_filter is not None and item["item_id"] not in item_filter:
            continue

        item_id = item["item_id"]
        compact_item_id = generation_id(item)
        prompt = item["generated_prompt"]
        # prompt = build_full_json_prompt(item) #use whole json as prompt
        # item_dir = args.output_root / item_id
        item_dir = args.output_root / compact_item_id
        if not args.dry_run:
            item_dir.mkdir(parents=True, exist_ok=True)

        for variant in range(args.variant_start, args.variant_start + args.variants):
            total_jobs += 1
            seed = seed_for_item(
                index=index,
                variant=variant,
                base_seed=args.base_seed,
                seed_mode=args.seed_mode,
                num_items=len(items),
                variants=args.variants,
            )
            mp4_path = item_dir / f"{compact_item_id}_v{variant}_raw.mp4"
            txt_path = item_dir / f"{compact_item_id}_v{variant}_raw.txt"

            command = build_ltx_command(
                python_bin=args.python_bin,
                checkpoint_path=args.checkpoint_path,
                gemma_root=args.gemma_root,
                prompt=prompt,
                output_path=mp4_path,
                width=args.width,
                height=args.height,
                num_frames=args.num_frames,
                frame_rate=args.frame_rate,
                seed=seed,
                extra_ltx_args=args.extra_ltx_args,
            )

            if mp4_path.exists() and not args.overwrite:
                print(f"[SKIP] {mp4_path}")
                if not txt_path.exists():
                    write_metadata_txt(
                        txt_path=txt_path,
                        index=index,
                        item=item,
                        seed=seed,
                        command=command,
                        compact_item_id=compact_item_id,
                    )
                    print(f"       wrote missing metadata: {txt_path}")
                skipped_jobs += 1
                continue

            print(f"[RUN] index={index} item_id={item_id} variant=v{variant} seed={seed}")
            print("      " + shlex.join(command))
            if args.dry_run:
                continue

            result = subprocess.run(command, cwd=str(args.ltx_repo), check=False)
            if result.returncode != 0:
                print(
                    f"[ERROR] LTX command failed with return code {result.returncode}: {item_id} v{variant}",
                    file=sys.stderr,
                )
                return result.returncode

            write_metadata_txt(
                txt_path=txt_path,
                index=index,
                item=item,
                seed=seed,
                command=command,
                compact_item_id=compact_item_id,
            )
            print(f"[DONE] {mp4_path}")
            print(f"       {txt_path}")
            completed_jobs += 1

    print(
        f"Finished. jobs={total_jobs}, completed={completed_jobs}, "
        f"skipped={skipped_jobs}, dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
