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
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_PROMPT_JSON = Path(
    "/home/coder/T2V_Gen/prompt_gen/output/3-comb_temporal_selected_specs_prompts.json"
    # "/home/coder/T2V_Gen/prompt_gen/output/4-comb_temporal_selected_specs_prompts.json"
)
DEFAULT_OUTPUT_ROOT = Path(
    # "/home/coder/T2V_Gen/hf_datasets/T2AV_TemporalConstraint/"
    # "LTX-2.3/3-seed42-dev_outputs-comb-temporal_reorganized-test"
    "/home/coder/T2V_Gen/LTX-2/outputs/old_prompt_JSONForPrompt"
)
DEFAULT_PYTHON_BIN = Path("/home/coder/miniforge3/envs/ltx23/bin/python")
DEFAULT_LTX_REPO = Path("/home/coder/T2V_Gen/LTX-2")
DEFAULT_CHECKPOINT = Path(
    "/home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors"
)
DEFAULT_GEMMA_ROOT = Path("/home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it")

MODALITY_TO_CATEGORY = {
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
        if "item_id" not in item:
            raise ValueError(f"Missing item_id at index {i}")
        if "generated_prompt" not in item:
            raise ValueError(f"Missing generated_prompt for item {item.get('item_id', i)}")
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


def infer_label(item: dict[str, Any]) -> str:
    content = item.get("content", {})
    if not isinstance(content, dict):
        return "unknown"
    values = [str(content[k]) for k in LABEL_ORDER if k in content]
    return "_".join(values) if values else "unknown"


def normalized_temporal_constraint(item: dict[str, Any]) -> dict[str, Any]:
    """Match the old txt convention: JSON uses sync_count, old txt wrote count."""
    temporal = copy.deepcopy(item.get("temporal_constraint", {}))
    if isinstance(temporal, dict) and temporal.get("type") == "sync_count":
        temporal["type"] = "count"
    return temporal


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
) -> None:
    lines = [
        f"index: {index}",
        f"item_id: {item['item_id']}",
        f"category: {infer_category(item)}",
        f"label: {infer_label(item)}",
        f"seed: {seed}",
        f"modality_combination: {item.get('modality_combination', '')}",
        "content: " + json.dumps(item.get("content", {}), ensure_ascii=False),
        "temporal_constraint: "
        + json.dumps(normalized_temporal_constraint(item), ensure_ascii=False),
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
    parser.add_argument("--variants", type=int, default=3)
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
    args = parser.parse_args()

    validate_generation_args(args)

    items = load_items(args.prompt_json)
    item_filter = parse_item_filter(args.item_id)

    if not args.dry_run:
        for path, label in [
            (args.prompt_json, "prompt json"),
            (args.python_bin, "python binary"),
            (args.checkpoint_path, "checkpoint"),
            (args.gemma_root, "Gemma root"),
        ]:
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
        # prompt = item["generated_prompt"]
        prompt = build_full_json_prompt(item)
        item_dir = args.output_root / item_id
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
            mp4_path = item_dir / f"{item_id}_v{variant}_raw.mp4"
            txt_path = item_dir / f"{item_id}_v{variant}_raw.txt"

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
