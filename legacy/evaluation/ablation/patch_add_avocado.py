#!/usr/bin/env python3
"""Patch run_qwen3_captions.py in place:
  1. add --backend avocado (Qwen2.5-Omni-based AVoCaDO, from its repo inference.py)
  2. fix Omni backend: pass fps into the video element so frames are actually
     sampled at --fps (processor fps alone only sets TMRoPE timing).
Run from evaluation/ablation:  python patch_add_avocado.py
"""
from pathlib import Path

p = Path("run_qwen3_captions.py")
s = p.read_text()
bak = p.with_suffix(".py.pre_avocado.bak")
bak.write_text(s)

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, f"anchor count {s.count(old)} != {count}:\n{old}"
    s = s.replace(old, new)

# 1. default model
rep('''    "omni": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
}''', '''    "omni": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
    "avocado": "AVoCaDO-Captioner/AVoCaDO",
}''')

# 2. Omni: sample frames at --fps (not only tell the processor)
rep('''    messages = [{"role": "user", "content": [
        {"type": "video", "video": str(video_path)},
        {"type": "text", "text": prompt},
    ]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(messages, use_audio_in_video=use_audio_in_video)
''', '''    messages = [{"role": "user", "content": [
        {"type": "video", "video": str(video_path), "fps": fps},
        {"type": "text", "text": prompt},
    ]}]
    text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(messages, use_audio_in_video=use_audio_in_video)
''')

# 3. AVoCaDO backend, inserted before the driver section
AVOCADO_BLOCK = '''# ---------------------------------------------------------------------------
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

    video_item = {"type": "video", "video": str(video_path),
                  "max_pixels": AVOCADO_VIDEO_MAX_PIXELS}
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

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs, use_audio_in_video=use_audio_in_video, return_audio=False,
            do_sample=False, thinker_max_new_tokens=max_new_tokens,
        )
    if isinstance(output_ids, tuple):
        output_ids = output_ids[0]

    trimmed = [o[len(i):] for i, o in zip(inputs["input_ids"], output_ids)]
    out = processor.batch_decode(trimmed, skip_special_tokens=True,
                                 clean_up_tokenization_spaces=False)[0]
    meta = {"fps_requested": fps, "nframes": nframes,
            "use_audio_in_video": use_audio_in_video,
            "fps_passed_to_processor": fps_to_processor}
    return out, meta


'''
rep('''# ---------------------------------------------------------------------------
# Driver (mirrors run_salmonn_captions.py)''',
    AVOCADO_BLOCK + '''# ---------------------------------------------------------------------------
# Driver (mirrors run_salmonn_captions.py)''')

# 4. argparse + dispatch
rep('''    ap.add_argument("--backend", choices=["vl", "omni"], required=True)''',
    '''    ap.add_argument("--backend", choices=["vl", "omni", "avocado"], required=True)''')
rep('''    ap.add_argument("--no-audio", action="store_true",
                    help="[omni only] drop the audio track (use_audio_in_video=False).")''',
    '''    ap.add_argument("--no-audio", action="store_true",
                    help="[omni/avocado] drop the audio track (use_audio_in_video=False).")
    ap.add_argument("--attn-impl", type=str, default="sdpa",
                    help="[avocado] attention backend (repo uses flash_attention_2; sdpa if unavailable).")''')
rep('''    handle = load_vl(model_name) if args.backend == "vl" else load_omni(model_name)''',
    '''    if args.backend == "vl":
        handle = load_vl(model_name)
    elif args.backend == "omni":
        handle = load_omni(model_name)
    else:
        handle = load_avocado(model_name, args.attn_impl)''')
rep('''            else:
                caption, meta = caption_omni(handle, video, prompt, args.fps,
                                             args.max_new_tokens,
                                             use_audio_in_video=not args.no_audio)''',
    '''            elif args.backend == "omni":
                caption, meta = caption_omni(handle, video, prompt, args.fps,
                                             args.max_new_tokens,
                                             use_audio_in_video=not args.no_audio)
            else:
                caption, meta = caption_avocado(handle, video, prompt, args.fps,
                                                args.max_new_tokens,
                                                use_audio_in_video=not args.no_audio)''')

p.write_text(s)
print(f"patched {p}; backup at {bak}")
