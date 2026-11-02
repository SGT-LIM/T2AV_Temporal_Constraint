#!/usr/bin/env python3
"""Dump video-SALMONN 2+ dense captions for every video under --videos-dir into
a JSON file consumable by the agentic evaluator's caption evidence:

    python run_salmonn_captions.py \
        --videos-dir /home/coder/T2V_Gen/LTX-2/outputs/relative_500_v5 \
        --output-json salmonn_captions_ltx.json \
        --model-path tsinghua-ee/video-SALMONN2_plus_7B_full

    python run_agentic_eval.py ... \
        --caption-evidence-mode external \
        --caption-external-json salmonn_captions_ltx.json

Output format: {"<relative video path>": "<caption>", ...}. Keys are paths
relative to --videos-dir, so identical filenames in different item folders
never collide; caption_evidence.load_external_caption matches relpath keys
when the evaluator passes --outputs-dir as videos_root (it does).

Resumable: existing entries in --output-json are kept and skipped; the file is
rewritten atomically after every video, so a crash never loses finished work.

Model loading/generation is adapted from the repo's minimal inference
(video_SALMONN2_plus/inference.py); pass --salmonn-repo pointing at that
folder so qwenvl/ is importable. Run inside the salmonn conda env.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

# Keep the captioning instruction IDENTICAL to the Gemini caption row so the
# only variable between the two caption conditions is the captioner model.
try:
    from caption_evidence import CAPTION_PROMPTS
except ImportError:
    CAPTION_PROMPTS = None

_FALLBACK_PLAIN_PROMPT = (
    "Describe, in chronological order, everything that is visible and audible "
    "in this video. Cover both modalities: visible actions, gestures, and "
    "poses (state which hand or body side is used when applicable), and "
    "audible events (transcribe any speech verbatim; describe every non-speech "
    "sound; if the audio is silent, say so). Mention every repetition of a "
    "repeated event. Report only what is directly observable, with no "
    "interpretation of intent and no quality judgments."
)

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv"}


# ---------------------------------------------------------------------------
# video-SALMONN 2+ wiring (adapted from video_SALMONN2_plus/inference.py)
# ---------------------------------------------------------------------------
def _prepare_inputs(inputs):
    """Copied from video_SALMONN2_plus/inference.py: strip non-tensor fields
    and move tensors to the current CUDA device."""
    import torch
    inputs.pop("video", None)
    inputs.pop("image", None)
    inputs.pop("prompt", None)
    inputs.pop("ref", None)
    inputs.pop("audio", None)
    inputs.pop("use_audio", False)
    inputs.pop("should_use", True)
    return {k: v.to(f"cuda:{torch.cuda.current_device()}")
            for k, v in inputs.items() if isinstance(v, torch.Tensor)}


def load_captioner(model_path: str, device: str, salmonn_repo: str, attn_impl: str = "flash_attention_2"):
    """Load video-SALMONN 2+ once; returns a handle reused for every video.

    `salmonn_repo` must point to the repo's video_SALMONN2_plus/ folder (the
    one containing qwenvl/). All heavy imports are deferred to here so the
    script still parses without the repo or torch installed.
    """
    repo = Path(salmonn_repo).resolve()
    if not (repo / "qwenvl").exists():
        raise RuntimeError(
            f"--salmonn-repo must point to the video_SALMONN2_plus folder "
            f"(qwenvl/ not found under {repo})"
        )
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    import torch

    from qwenvl.model import modeling_qwen2_5_vl
    from qwenvl.model.modeling_qwen2_5_vl import video_SALMONN2_plus
    from qwenvl.data.dataset import make_supervised_data_module
    from qwenvl.data.image_processing_qwen2_vl_fast import Qwen2VLImageProcessorFast
    from qwenvl.train.argument import DataArguments
    from transformers import AutoTokenizer, WhisperFeatureExtractor

    # Liger kernel patches, same as the repo's inference.py (performance only;
    # skipped with a warning if liger-kernel is missing).
    try:
        from liger_kernel.transformers.qwen2vl_mrope import liger_multimodal_rotary_pos_emb
        from liger_kernel.transformers.rms_norm import LigerRMSNorm
        from liger_kernel.transformers.swiglu import LigerSwiGLUMLP
        modeling_qwen2_5_vl.apply_multimodal_rotary_pos_emb = liger_multimodal_rotary_pos_emb
        modeling_qwen2_5_vl.Qwen2RMSNorm = LigerRMSNorm
        modeling_qwen2_5_vl.Qwen2MLP = LigerSwiGLUMLP
        print("[INFO] Liger kernels applied.")
    except ImportError:
        print("[WARN] liger-kernel not installed; running without Liger patches "
              "(slower, otherwise identical).", file=sys.stderr)

    # DataArguments, verbatim from the repo's inference.py.
    data_args = DataArguments()
    data_args.video_max_frames = 768
    data_args.video_min_frames = 16
    data_args.base_interval = 0.1
    data_args.max_pixels = 61250
    data_args.video_max_frame_pixels = 61250
    data_args.run_test = True
    data_args.image_processor = Qwen2VLImageProcessorFast.from_pretrained(model_path)
    data_args.audio_processor = WhisperFeatureExtractor(
        feature_size=data_args.feature_size,
        sampling_rate=data_args.sampling_rate,
        hop_length=data_args.hop_length,
        chunk_length=data_args.chunk_length,
    )
    data_args.model_type = "qwen2.5vl"

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, model_max_length=131072, padding_side="right", use_fast=False,
    )
    print(f"[INFO] Loading {model_path} (bf16, {attn_impl})...")
    model = video_SALMONN2_plus.from_pretrained(
        model_path,
        attn_implementation=attn_impl,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
    )
    model.cuda()
    model.eval()

    data_module = make_supervised_data_module(tokenizer=tokenizer, data_args=data_args)
    return {"model": model, "tokenizer": tokenizer,
            "test_data": data_module["train_dataset"]}


def caption_one_video(handle, video_path: Path, prompt: str, max_new_tokens: int) -> str:
    """One greedy captioning pass (do_sample=False → deterministic)."""
    import torch

    input_dict = {
        "video": str(video_path),
        "use_audio": True,  # ingest the audio track alongside the frames
        "conversations": [
            {"from": "human", "value": "<video>\n" + prompt},
            {"from": "gpt", "value": ""},
        ],
    }
    inputs = handle["test_data"]._get_item(input_dict)
    inputs = _prepare_inputs(inputs)
    with torch.no_grad():
        outputs = handle["model"].generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
        )
    trimmed = outputs[0, len(inputs["input_ids"][0]):]
    return handle["tokenizer"].decode(
        trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False,
    )
# ---------------------------------------------------------------------------
# end video-SALMONN 2+ wiring
# ---------------------------------------------------------------------------


def find_videos(root: Path):
    vids = [p for p in sorted(root.rglob("*")) if p.suffix.lower() in VIDEO_EXTS]
    if not vids:
        raise RuntimeError(f"No video files found under {root}")
    return vids


def atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dump video-SALMONN 2+ dense captions to JSON.")
    ap.add_argument("--videos-dir", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--model-path", type=str, default="tsinghua-ee/video-SALMONN2_plus_7B_full")
    ap.add_argument("--device", type=str, default="cuda")
    ap.add_argument("--salmonn-repo", type=str, default="./video-SALMONN-2/video_SALMONN2_plus",
                    help="Path to the repo's video_SALMONN2_plus folder (must contain qwenvl/).")
    ap.add_argument("--attn-impl", type=str, default="flash_attention_2", choices=["flash_attention_2", "sdpa", "eager"],
                    help="Attention backend; use sdpa where flash-attn is unavailable (e.g. old glibc).")
    ap.add_argument("--caption-style", type=str, default="timestamped", choices=["timestamped", "plain"],
                    help="Shared caption instruction (same text as the Gemini caption row). "
                         "'timestamped' is the primary condition: the caption's best shot, "
                         "including timestamps. 'plain' is a contingency ablation to isolate "
                         "timestamp-anchoring effects if the timestamped results look anomalous.")
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--max-videos", type=int, default=None)
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--end-index", type=int, default=None)
    ap.add_argument("--overwrite", action="store_true", help="Re-caption videos already in the output JSON.")
    args = ap.parse_args()

    if CAPTION_PROMPTS is not None:
        prompt = CAPTION_PROMPTS[args.caption_style]
    else:
        if args.caption_style != "plain":
            print("[WARN] caption_evidence.py not importable; falling back to the embedded "
                  "plain prompt regardless of --caption-style.", file=sys.stderr)
        prompt = _FALLBACK_PLAIN_PROMPT
        print("[WARN] Using embedded fallback prompt. Put this script next to "
              "caption_evidence.py to share the exact instruction text.", file=sys.stderr)

    videos = find_videos(args.videos_dir)[args.start_index:args.end_index]
    if args.max_videos is not None:
        videos = videos[: args.max_videos]

    captions: dict = {}
    if args.output_json.exists():
        captions = json.loads(args.output_json.read_text(encoding="utf-8"))
        print(f"[INFO] Resuming: {len(captions)} captions already in {args.output_json}")

    def relkey(v: Path) -> str:
        return str(v.relative_to(args.videos_dir))

    todo = [v for v in videos if args.overwrite or relkey(v) not in captions]
    print(f"[INFO] {len(videos)} videos selected, {len(todo)} to caption "
          f"(style={args.caption_style}, model={args.model_path})")
    if not todo:
        print("[DONE] Nothing to do.")
        return

    handle = load_captioner(args.model_path, args.device, args.salmonn_repo, args.attn_impl)

    done = errors = 0
    failed: list = []
    for i, video in enumerate(todo, 1):
        t0 = time.perf_counter()
        try:
            caption = caption_one_video(handle, video, prompt, args.max_new_tokens).strip()
            if not caption:
                raise RuntimeError("empty caption")
            captions[relkey(video)] = caption
            done += 1
            print(f"[{i}/{len(todo)}] {video.name} ok "
                  f"({time.perf_counter() - t0:.1f}s, {len(caption)} chars)")
        except Exception as exc:
            errors += 1
            failed.append(relkey(video))
            print(f"[{i}/{len(todo)}] {video.name} ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc()
        # Atomic write after EVERY video so a crash never loses finished work.
        atomic_write_json(args.output_json, captions)

    print(f"[DONE] captioned={done} errors={errors} total_in_file={len(captions)} -> {args.output_json}")
    if failed:
        fail_path = args.output_json.with_suffix(".failed.txt")
        fail_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"[INFO] Failed list written to {fail_path}; rerun the same command to retry them.")


if __name__ == "__main__":
    main()
