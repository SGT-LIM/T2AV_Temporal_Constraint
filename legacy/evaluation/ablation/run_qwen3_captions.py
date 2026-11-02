#!/usr/bin/env python3
# Replaced by t2av_eval/evidence/captions_gen/runner.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Dump Qwen3-VL or Qwen3-Omni dense captions for every video under --videos-dir
into a JSON file consumable by the agentic evaluator's caption evidence.

    # Qwen3-VL, visual only, 8 fps
    python run_qwen3_captions.py --backend vl --fps 8 \
        --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3/LTX_2p3 \
        --output-json captions/qwen3vl_fps8_LTX_2p3.json

    # Qwen3-Omni, audio + visual, 8 fps
    python run_qwen3_captions.py --backend omni --fps 8 \
        --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3/LTX_2p3 \
        --output-json captions/qwen3omni_fps8_LTX_2p3.json

    python run_agentic_eval.py ... --caption-evidence-mode external \
        --caption-external-json captions/qwen3vl_fps8_LTX_2p3.json

Output format: {"<relative video path>": {"caption": "...", "fps_requested": 8,
"nframes": 40, "model": "...", "backend": "vl", "style": "timestamped"}, ...}.
caption_evidence.load_external_caption reads the "caption" field of dict values,
so this is a drop-in replacement for the plain-string format.

Resumable: existing entries are kept and skipped; the file is rewritten
atomically after every video. Run inside an env with transformers>=4.57,
qwen-vl-utils, qwen-omni-utils (e.g. conda_envs/qwen3_cap).

Inference code is copied from qwen/qwen3_check_action.py and
qwen/qwen3-omni_action_check.py so the processor/generate calls match what
already ran; only the prompt, fps, and output handling differ.
"""

from __future__ import annotations

import argparse
import os
import json
import sys
import time
import traceback
from pathlib import Path

# Same instruction text as the Gemini and SALMONN caption rows.
try:
    from caption_evidence import CAPTION_PROMPTS, CAPTION_PROMPT_VERSION
except ImportError:
    CAPTION_PROMPTS = None
    CAPTION_PROMPT_VERSION = "unknown"

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
DEFAULT_MODELS = {
    "vl": "Qwen/Qwen3-VL-8B-Instruct",
    "omni": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
    "avocado": "AVoCaDO-Captioner/AVoCaDO",
}


# ---------------------------------------------------------------------------
# Qwen3-VL (from qwen/qwen3_check_action.py)
# ---------------------------------------------------------------------------
def load_vl(model_name: str):
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

    print(f"[INFO] Loading {model_name} (dtype=auto, device_map=auto)...")
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_name, torch_dtype="auto", device_map="auto",
    )
    model.eval()
    processor = AutoProcessor.from_pretrained(model_name)
    return {"model": model, "processor": processor}


def caption_vl(handle, video_path: Path, prompt: str, fps: float,
               max_pixels: int | None, max_new_tokens: int):
    import torch
    from qwen_vl_utils import process_vision_info

    model, processor = handle["model"], handle["processor"]

    video_item = {"type": "video", "video": str(video_path), "fps": fps}
    if max_pixels:
        video_item["max_pixels"] = max_pixels
    messages = [{"role": "user", "content": [video_item, {"type": "text", "text": prompt}]}]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    image_inputs, video_inputs, video_kwargs = process_vision_info(
        messages, image_patch_size=16, return_video_kwargs=True, return_video_metadata=True,
    )
    video_metadatas = None
    if video_inputs is not None:
        video_inputs, video_metadatas = zip(*video_inputs)
        video_inputs = list(video_inputs)
        video_metadatas = list(video_metadatas)

    inputs = processor(
        text=[text], images=image_inputs, videos=video_inputs,
        video_metadata=video_metadatas, padding=True, return_tensors="pt",
        do_resize=False, **video_kwargs,
    )
    nframes = int(video_inputs[0].shape[0]) if video_inputs else None
    inputs = inputs.to(model.device)

    with torch.inference_mode():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)

    trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], output_ids)]
    out = processor.batch_decode(trimmed, skip_special_tokens=True,
                                 clean_up_tokenization_spaces=False)[0]

    meta = {"fps_requested": fps, "nframes": nframes}
    if video_metadatas and isinstance(video_metadatas[0], dict):
        meta["fps_effective"] = video_metadatas[0].get("fps")
        meta["total_num_frames"] = video_metadatas[0].get("total_num_frames")
    return out, meta


# ---------------------------------------------------------------------------
# Qwen3-Omni (from qwen/qwen3-omni_action_check.py)
# ---------------------------------------------------------------------------
def load_omni(model_name: str):
    from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor

    print(f"[INFO] Loading {model_name} (dtype=auto, device_map=auto, no audio output)...")
    model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
        model_name, dtype="auto", device_map="auto", enable_audio_output=False,
    )
    model.eval()
    processor = Qwen3OmniMoeProcessor.from_pretrained(model_name)
    return {"model": model, "processor": processor}


def caption_omni(handle, video_path: Path, prompt: str, fps: float,
                 max_new_tokens: int, use_audio_in_video: bool = True):
    import torch
    from qwen_omni_utils import process_mm_info

    model, processor = handle["model"], handle["processor"]

    messages = [{"role": "user", "content": [
        {"type": "video", "video": str(video_path), "fps": fps},
        {"type": "text", "text": prompt},
    ]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(messages, use_audio_in_video=use_audio_in_video)

    inputs = processor(
        text=text, audio=audios, images=images, videos=videos,
        return_tensors="pt", padding=True, fps=fps, use_audio_in_video=use_audio_in_video,
    )
    nframes = None
    if "video_grid_thw" in inputs:
        # grid t is in temporal patches; Qwen uses temporal_patch_size=2.
        nframes = int(inputs["video_grid_thw"][0][0]) * 2
    inputs = inputs.to(model.device).to(model.dtype)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            use_audio_in_video=use_audio_in_video, return_audio=False,
        )
    if isinstance(output_ids, tuple):
        output_ids = output_ids[0]

    trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], output_ids)]
    out = processor.batch_decode(trimmed, skip_special_tokens=True,
                                 clean_up_tokenization_spaces=False)[0]

    meta = {"fps_requested": fps, "nframes": nframes,
            "use_audio_in_video": use_audio_in_video}
    return out, meta


# ---------------------------------------------------------------------------
# AVoCaDO (Qwen2.5-Omni-7B finetune; from AVoCaDO-Captioner/AVoCaDO inference.py)
# ---------------------------------------------------------------------------
AVOCADO_SYSTEM_PROMPT = (
    "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, "
    "capable of perceiving auditory and visual inputs, as well as generating text and speech."
)
AVOCADO_VIDEO_MAX_PIXELS = 401408          # 512*28*28 per frame, as in the repo
AVOCADO_VIDEO_TOTAL_PIXELS = 20070400      # 512*28*28*50, as in the repo


def load_avocado(model_name: str, attn_impl: str = "sdpa"):
    import os
    # The repo sets this env var before qwen_omni_utils is imported.
    os.environ.setdefault("VIDEO_MAX_PIXELS", str(AVOCADO_VIDEO_TOTAL_PIXELS))
    import torch
    from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor

    print(f"[INFO] Loading {model_name} (bf16, device_map=auto, attn={attn_impl}, talker off)...")
    model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
        model_name, dtype=torch.bfloat16, device_map="auto", attn_implementation=attn_impl,
    )
    model.disable_talker()
    model.eval()
    processor = Qwen2_5OmniProcessor.from_pretrained(model_name)
    return {"model": model, "processor": processor}


def caption_avocado(handle, video_path: Path, prompt: str, fps: float,
                    max_new_tokens: int, use_audio_in_video: bool = True):
    import torch
    from qwen_omni_utils import process_mm_info

    model, processor = handle["model"], handle["processor"]

    # 10/31: opt-in lower per-frame pixel cap for the 46-48 GB memory test (T2AV_AVOCADO_MAX_PIXELS); default as in the repo
    video_item = {"type": "video", "video": str(video_path),
                  "max_pixels": int(os.environ.get("T2AV_AVOCADO_MAX_PIXELS", AVOCADO_VIDEO_MAX_PIXELS))}
    if fps:
        video_item["fps"] = fps
    messages = [
        {"role": "system", "content": [{"type": "text", "text": AVOCADO_SYSTEM_PROMPT}]},
        {"role": "user", "content": [video_item, {"type": "text", "text": prompt}]},
    ]
    text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(messages, use_audio_in_video=use_audio_in_video)

    kw = dict(text=text, audio=audios, images=images, videos=videos,
              return_tensors="pt", padding=True, use_audio_in_video=use_audio_in_video)
    fps_to_processor = True
    try:
        inputs = processor(fps=fps, **kw) if fps else processor(**kw)
    except TypeError:
        fps_to_processor = False
        inputs = processor(**kw)
    nframes = None
    if "video_grid_thw" in inputs:
        nframes = int(inputs["video_grid_thw"][0][0]) * 2
    inputs = inputs.to(model.device).to(model.dtype)

    # 10/30: opt-in sampling for repeated captions (tool screening). Off unless T2AV_CAPTION_SAMPLE_SEED is set;
    # then each video gets seed = sample seed + crc32(video name), temperature / top_p from the env (default 0.7 / 0.9).
    _seed = os.environ.get("T2AV_CAPTION_SAMPLE_SEED")
    gen_kw = dict(do_sample=False)
    if _seed is not None:
        import zlib
        torch.manual_seed(int(_seed) + zlib.crc32(str(video_path).split("/")[-1].encode()))
        gen_kw = dict(do_sample=True, thinker_do_sample=True,
                      thinker_temperature=float(os.environ.get("T2AV_CAPTION_TEMPERATURE", "0.7")),
                      thinker_top_p=float(os.environ.get("T2AV_CAPTION_TOP_P", "0.9")))
    with torch.inference_mode():
        output_ids = model.generate(
            **inputs, use_audio_in_video=use_audio_in_video, return_audio=False,
            thinker_max_new_tokens=max_new_tokens, **gen_kw,
        )
    if isinstance(output_ids, tuple):
        output_ids = output_ids[0]

    trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], output_ids)]
    out = processor.batch_decode(trimmed, skip_special_tokens=True,
                                 clean_up_tokenization_spaces=False)[0]
    meta = {"fps_requested": fps, "nframes": nframes,
            "use_audio_in_video": use_audio_in_video,
            "fps_passed_to_processor": fps_to_processor}
    if os.environ.get("T2AV_CAPTION_MEMLOG") == "1":
        meta.update(peak_mem_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2), max_pixels=video_item["max_pixels"])
        torch.cuda.reset_peak_memory_stats()
    if _seed is not None:
        meta.update(sample_seed=int(_seed), temperature=gen_kw["thinker_temperature"], top_p=gen_kw["thinker_top_p"])
    return out, meta


# ---------------------------------------------------------------------------
# Driver (mirrors run_salmonn_captions.py)
# ---------------------------------------------------------------------------
def find_videos(root: Path):
    vids = [p for p in sorted(root.rglob("*")) if p.suffix.lower() in VIDEO_EXTS]
    if not vids:
        raise RuntimeError(f"No video files found under {root}")
    return vids


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dump Qwen3-VL / Qwen3-Omni dense captions to JSON.")
    ap.add_argument("--backend", choices=["vl", "omni", "avocado"], required=True)
    ap.add_argument("--videos-dir", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--model", type=str, default=None,
                    help=f"HF model id. Defaults: {DEFAULT_MODELS}")
    ap.add_argument("--fps", type=float, default=8.0,
                    help="Visual frame sampling rate passed to the processor (default 8; "
                         "the old check_action scripts used the library default of 2).")
    ap.add_argument("--max-pixels", type=int, default=None,
                    help="[vl only] per-frame max_pixels for qwen_vl_utils; None = library default.")
    ap.add_argument("--no-audio", action="store_true",
                    help="[omni/avocado] drop the audio track (use_audio_in_video=False).")
    ap.add_argument("--attn-impl", type=str, default="sdpa",
                    help="[avocado] attention backend (repo uses flash_attention_2; sdpa if unavailable).")
    ap.add_argument("--caption-style", type=str, default="timestamped", choices=["timestamped", "plain"])
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--max-videos", type=int, default=None)
    ap.add_argument("--start-index", type=int, default=0)
    ap.add_argument("--end-index", type=int, default=None)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    model_name = args.model or DEFAULT_MODELS[args.backend]

    if CAPTION_PROMPTS is not None:
        prompt = CAPTION_PROMPTS[args.caption_style]
    else:
        print("[WARN] caption_evidence.py not importable; using embedded plain prompt. "
              "Put this script next to caption_evidence.py.", file=sys.stderr)
        prompt = _FALLBACK_PLAIN_PROMPT

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
          f"(backend={args.backend}, model={model_name}, fps={args.fps}, style={args.caption_style})")
    if not todo:
        print("[DONE] Nothing to do.")
        return

    if args.backend == "vl":
        handle = load_vl(model_name)
    elif args.backend == "omni":
        handle = load_omni(model_name)
    else:
        handle = load_avocado(model_name, args.attn_impl)

    done = errors = 0
    failed: list = []
    for i, video in enumerate(todo, 1):
        t0 = time.perf_counter()
        try:
            if args.backend == "vl":
                caption, meta = caption_vl(handle, video, prompt, args.fps,
                                           args.max_pixels, args.max_new_tokens)
            elif args.backend == "omni":
                caption, meta = caption_omni(handle, video, prompt, args.fps,
                                             args.max_new_tokens,
                                             use_audio_in_video=not args.no_audio)
            else:
                caption, meta = caption_avocado(handle, video, prompt, args.fps,
                                                args.max_new_tokens,
                                                use_audio_in_video=not args.no_audio)
            caption = caption.strip()
            if not caption:
                raise RuntimeError("empty caption")
            captions[relkey(video)] = {
                "caption": caption, "model": model_name, "backend": args.backend,
                "style": args.caption_style, "prompt_version": CAPTION_PROMPT_VERSION, **meta,
            }
            done += 1
            print(f"[{i}/{len(todo)}] {video.name} ok ({time.perf_counter() - t0:.1f}s, "
                  f"{len(caption)} chars, nframes={meta.get('nframes')})")
        except Exception as exc:
            errors += 1
            failed.append(relkey(video))
            print(f"[{i}/{len(todo)}] {video.name} ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc()
        atomic_write_json(args.output_json, captions)

    print(f"[DONE] captioned={done} errors={errors} total_in_file={len(captions)} -> {args.output_json}")
    if failed:
        fail_path = args.output_json.with_suffix(".failed.txt")
        fail_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"[INFO] Failed list written to {fail_path}; rerun the same command to retry them.")


if __name__ == "__main__":
    main()
