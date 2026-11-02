#!/usr/bin/env python3
"""Patch agentic_common.py + run_agentic_eval.py for --judge-backend openai.

Run from evaluation/ablation/:  python patch_openai_backend.py
Backups: agentic_common.py.bak_openai, run_agentic_eval.py.bak_openai

Changes (all additive, Gemini path byte-identical when backend != openai):
 1. call_gemini_json: dispatch to openai_judge.call_openai_json when
    ctx.config["judge_backend"] == "openai".
 2. build_context: when backend == openai and media_input_mode == video,
    skip the Gemini Files upload (uploaded=None) -- frames are extracted
    lazily by openai_judge. Stash video_path / frame_fps / frame_cache_dir /
    judge_backend / openai_reasoning_effort in ctx.config.
 3. build_context: the language_only+caption guard and the caption_evidence
    call are unchanged (external captions never need `uploaded`).
 4. run_agentic_eval.py: new CLI args.
 5. add_result_to_row: uploaded_file_uri carries the media provenance string
    (e.g. openai:frames:8fps:n=40:no_audio) so the CSV records how the judge
    saw the video without a schema change.
"""
import re
import shutil
from pathlib import Path

AC = Path("agentic_common.py")
RA = Path("run_agentic_eval.py")


def patch_common():
    src = AC.read_text()
    shutil.copy(AC, AC.with_suffix(".py.bak_openai"))

    # 1. dispatch at top of call_gemini_json
    old = 'def call_gemini_json(ctx: EvalContext, system_prompt: str, user_text: str, schema: dict):\n    """Single structured-JSON Gemini call reusing the shared uploaded video."""\n'
    new = old + (
        '    if (ctx.config.get("judge_backend") or "gemini") == "openai":\n'
        '        import openai_judge as OJ\n'
        '        return OJ.call_openai_json(ctx, system_prompt, user_text, schema)\n'
    )
    assert old in src, "call_gemini_json header not found"
    src = src.replace(old, new, 1)

    # 2. skip Gemini upload for openai backend in video mode
    old = '    else:\n        uploaded = NE.upload_and_wait(client, video_path, poll_seconds=5.0, timeout_seconds=args.timeout_seconds)\n'
    new = (
        '    elif (getattr(args, "judge_backend", "gemini") or "gemini") == "openai":\n'
        '        # OpenAI has no video input: frames are extracted lazily in openai_judge.\n'
        '        uploaded = None\n'
        '    else:\n        uploaded = NE.upload_and_wait(client, video_path, poll_seconds=5.0, timeout_seconds=args.timeout_seconds)\n'
    )
    assert old in src, "upload_and_wait block not found"
    src = src.replace(old, new, 1)

    # 2b. caption_evidence with a Gemini-generated caption needs `uploaded`; for openai
    #     backend only external captions are allowed.
    old = '    if caption_mode in (None, "", "none"):\n        caption_section, caption_error = "", ""\n'
    new = (
        '    if (getattr(args, "judge_backend", "gemini") or "gemini") == "openai" and caption_mode not in (None, "", "none", "external"):\n'
        '        raise RuntimeError("--judge-backend openai supports only --caption-evidence-mode external (precomputed captions).")\n'
        + old
    )
    assert old in src
    src = src.replace(old, new, 1)

    # 2c. config keys
    old = '                "media_input_mode": media_input_mode,\n                "audio_only_path": audio_only_path},\n'
    new = (
        '                "media_input_mode": media_input_mode,\n                "audio_only_path": audio_only_path,\n'
        '                "judge_backend": getattr(args, "judge_backend", "gemini") or "gemini",\n'
        '                "video_path": str(video_path),\n'
        '                "frame_fps": getattr(args, "frame_fps", 8),\n'
        '                "frame_cache_dir": getattr(args, "frame_cache_dir", None),\n'
        '                "openai_reasoning_effort": getattr(args, "openai_reasoning_effort", "low")},\n'
    )
    assert old in src, "config dict tail not found"
    src = src.replace(old, new, 1)

    # 5. provenance into uploaded_file_uri (only when openai)
    old = '    row["uploaded_file_name"] = result["uploaded_file_name"]\n    row["uploaded_file_uri"] = result["uploaded_file_uri"]\n'
    new = (
        '    row["uploaded_file_name"] = result["uploaded_file_name"]\n'
        '    row["uploaded_file_uri"] = result.get("media_provenance") or result["uploaded_file_uri"]\n'
    )
    assert old in src
    src = src.replace(old, new, 1)

    AC.write_text(src)
    print("agentic_common.py patched")


def patch_orchestrator():
    """result['media_provenance'] from ctx.config (set by openai_judge on each call)."""
    p = Path("agentic_orchestrator.py")
    src = p.read_text()
    shutil.copy(p, p.with_suffix(".py.bak_openai"))
    old = '    result["uploaded_file_uri"] = getattr(ctx.uploaded, "uri", "")\n'
    new = old + '    result["media_provenance"] = ctx.config.get("last_media_provenance", "")\n'
    n = src.count(old)
    assert n == 2, f"expected 2 occurrences, found {n}"
    src = src.replace(old, new)
    p.write_text(src)
    print("agentic_orchestrator.py patched (2 sites)")


def patch_runner():
    src = RA.read_text()
    shutil.copy(RA, RA.with_suffix(".py.bak_openai"))
    # find the media-input-mode argument and add ours right after it
    m = re.search(r'\n(\s*)parser\.add_argument\(\s*"--media-input-mode".*?\)\n', src, flags=re.S)
    assert m, "--media-input-mode add_argument not found in run_agentic_eval.py"
    indent = m.group(1)
    add = (
        f'{indent}parser.add_argument("--judge-backend", choices=["gemini", "openai"], default="gemini",\n'
        f'{indent}                    help="openai: judge calls go to OpenAI (text / input_audio / frames). Evidence + prompts unchanged.")\n'
        f'{indent}parser.add_argument("--frame-fps", type=float, default=8.0,\n'
        f'{indent}                    help="openai backend, video mode: frame sampling rate (frames sent as ordered images, no audio).")\n'
        f'{indent}parser.add_argument("--frame-cache-dir", default="frame_cache")\n'
        f'{indent}parser.add_argument("--openai-reasoning-effort", default="low", choices=["minimal", "low", "medium", "high"])\n'
    )
    src = src[:m.end()] + add + src[m.end():]
    RA.write_text(src)
    print("run_agentic_eval.py patched")


if __name__ == "__main__":
    patch_common()
    patch_orchestrator()
    patch_runner()
    print("done. Verify: python -c 'import agentic_common, openai_judge'")
