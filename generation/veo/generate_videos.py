#!/usr/bin/env python3
import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types


def load_items(prompt_json_path: Path) -> List[Dict[str, Any]]:
    with prompt_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Prompt JSON must contain a list of items.")
    return data


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, obj: Dict[str, Any]):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def poll_operation(client, operation, poll_seconds: float = 10.0, timeout_seconds: float = 1800.0):
    start = time.time()
    while not operation.done:
        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Timed out after {timeout_seconds} seconds while waiting for video generation.")
        print("  Waiting for video generation to complete...")
        time.sleep(poll_seconds)
        operation = client.operations.get(operation)
    return operation


def build_config(
    resolution: Optional[str] = None,
):
    # Keep this minimal and official-doc-aligned.
    # You can extend later if needed.
    if resolution is None:
        return None
    return types.GenerateVideosConfig(
        resolution=resolution,
    )


def generate_one_video(
    client,
    model: str,
    prompt: str,
    out_mp4_path: Path,
    metadata_path: Path,
    item: Dict[str, Any],
    variant_index: int,
    resolution: Optional[str],
    poll_seconds: float,
    timeout_seconds: float,
):
    config = build_config(resolution=resolution)

    print(f"  Prompt:\n{prompt}\n")
    if config is None:
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
        )
    else:
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=config,
        )

    operation_name = getattr(operation, "name", "")
    print(f"  Started operation: {operation_name}")

    operation = poll_operation(
        client=client,
        operation=operation,
        poll_seconds=poll_seconds,
        timeout_seconds=timeout_seconds,
    )

    if not hasattr(operation, "response") or operation.response is None:
        raise RuntimeError("Operation completed but no response was returned.")

    generated_videos = getattr(operation.response, "generated_videos", None)
    if not generated_videos:
        raise RuntimeError("Operation completed but generated_videos is empty.")

    generated_video = generated_videos[0]

    # Download to local cache and save to desired location
    client.files.download(file=generated_video.video)
    ensure_dir(out_mp4_path.parent)
    generated_video.video.save(str(out_mp4_path))

    meta = {
        "item_id": item.get("item_id"),
        "variant_index": variant_index,
        "model": model,
        "resolution": resolution,
        "prompt": prompt,
        "operation_name": operation_name,
        "output_mp4": str(out_mp4_path),
        "modality_combination": item.get("modality_combination"),
        "content": item.get("content"),
        "temporal_constraint": item.get("temporal_constraint"),
        "scene_hint": item.get("scene_hint"),
        "camera_hint": item.get("camera_hint"),
    }
    save_json(metadata_path, meta)

    print(f"  Saved video to: {out_mp4_path}")
    print(f"  Saved metadata to: {metadata_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prompt-json",
        type=Path,
        default=Path("/home/coder/T2V_Gen/prompt_gen/output/3-comb_temporal_selected_specs_prompts.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/home/coder/T2V_Gen/Veo-3.1/3-comb_temporal_outputs"),
    )
    parser.add_argument(
        "--model",
        type=str,
        default="veo-3.1-generate-001",
    )
    parser.add_argument(
        "--variants-per-item",
        type=int,
        default=1,
        help="How many videos to generate per item. Saved as _v1_raw.mp4, _v2_raw.mp4, ...",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default=None,
        choices=[None, "720p", "1080p", "4k"],
        help="Optional output resolution.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=10.0,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=1800.0,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional: only generate the first N items.",
    )
    parser.add_argument(
        "--item-ids",
        type=str,
        nargs="*",
        default=None,
        help="Optional: only generate these item_ids.",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Please run: export GEMINI_API_KEY='your_api_key_here'"
        )

    client = genai.Client(api_key=api_key)

    items = load_items(args.prompt_json)

    if args.item_ids is not None and len(args.item_ids) > 0:
        wanted = set(args.item_ids)
        items = [x for x in items if x.get("item_id") in wanted]

    if args.limit is not None:
        items = items[:args.limit]

    ensure_dir(args.output_dir)

    run_manifest = {
        "prompt_json": str(args.prompt_json),
        "output_dir": str(args.output_dir),
        "model": args.model,
        "variants_per_item": args.variants_per_item,
        "resolution": args.resolution,
        "num_items": len(items),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_json(args.output_dir / "run_manifest.json", run_manifest)

    num_success = 0
    num_fail = 0
    failures = []

    for idx, item in enumerate(items, start=1):
        item_id = item.get("item_id")
        prompt = item.get("generated_prompt", "")

        if not item_id:
            print(f"[{idx}/{len(items)}] Skipping item with missing item_id")
            continue
        if not prompt:
            print(f"[{idx}/{len(items)}] Skipping {item_id} because generated_prompt is empty")
            continue

        item_dir = args.output_dir / item_id
        ensure_dir(item_dir)

        print(f"\n[{idx}/{len(items)}] item_id={item_id}")

        for v in range(1, args.variants_per_item + 1):
            out_mp4 = item_dir / f"{item_id}_v{v}_raw.mp4"
            out_meta = item_dir / f"{item_id}_v{v}_raw.meta.json"

            if out_mp4.exists() and not args.overwrite:
                print(f"  [SKIP] Exists: {out_mp4}")
                continue

            try:
                generate_one_video(
                    client=client,
                    model=args.model,
                    prompt=prompt,
                    out_mp4_path=out_mp4,
                    metadata_path=out_meta,
                    item=item,
                    variant_index=v,
                    resolution=args.resolution,
                    poll_seconds=args.poll_seconds,
                    timeout_seconds=args.timeout_seconds,
                )
                num_success += 1

            except Exception as e:
                num_fail += 1
                print(f"  [ERROR] {item_id} v{v}: {e}")
                failures.append({
                    "item_id": item_id,
                    "variant_index": v,
                    "error": str(e),
                })

    summary = {
        "num_success": num_success,
        "num_fail": num_fail,
        "failures": failures,
    }
    save_json(args.output_dir / "generation_summary.json", summary)

    print("\n=== Generation finished ===")
    print(f"Success: {num_success}")
    print(f"Fail:    {num_fail}")
    print(f"Output dir: {args.output_dir}")


if __name__ == "__main__":
    main()