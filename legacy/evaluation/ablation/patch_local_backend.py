#!/usr/bin/env python3
"""Add --judge-backend local (local_judge_server.py) to the agentic pipeline. Idempotent, fails loudly.

  cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint
  python evaluation/ablation/patch_local_backend.py
Backups: <file>.bak_local
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[3] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[0])  # legacy path roots, see legacy/README.md
import re, shutil, sys
from pathlib import Path

ROOT = Path(_LEGACY_ROOT)
AC = _pl.Path(_LEGACY_CODE) / "agentic_common.py"
RAE = _pl.Path(_LEGACY_CODE) / "run_agentic_eval.py"
SH = ROOT / "eval_results/scripts/run_parallel_multi.sh"


def patch(path, pairs):
    src = path.read_text()
    if "judge_backend_local_patched" in src:
        print(f"[skip] {path.name} already patched"); return
    shutil.copy(path, str(path) + ".bak_local")
    for old, new in pairs:
        n = src.count(old)
        if n != 1:
            sys.exit(f"[FAIL] {path.name}: expected 1 match, got {n} for:\n{old}")
        src = src.replace(old, new)
    path.write_text(src)
    print(f"[ok] {path.name}")


patch(AC, [
    # 1. no upload for local backend (same as openai)
    ('    elif (getattr(args, "judge_backend", "gemini") or "gemini") == "openai":\n'
     '        # OpenAI has no video input: frames are extracted lazily in openai_judge.\n'
     '        uploaded = None\n',
     '    elif (getattr(args, "judge_backend", "gemini") or "gemini") in ("openai", "local"):\n'
     '        # openai: frames extracted lazily in openai_judge. local: the server reads the file path itself.\n'
     '        uploaded = None  # judge_backend_local_patched\n'),
    # 2. caption mode guard covers local too
    ('    if (getattr(args, "judge_backend", "gemini") or "gemini") == "openai" and caption_mode not in (None, "", "none", "external"):\n'
     '        raise RuntimeError("--judge-backend openai supports only --caption-evidence-mode external (precomputed captions).")\n',
     '    if (getattr(args, "judge_backend", "gemini") or "gemini") in ("openai", "local") and caption_mode not in (None, "", "none", "external"):\n'
     '        raise RuntimeError("--judge-backend openai/local supports only --caption-evidence-mode external (precomputed captions).")\n'),
    # 3. pass the server url through ctx.config
    ('                "openai_reasoning_effort": getattr(args, "openai_reasoning_effort", "low")},\n',
     '                "openai_reasoning_effort": getattr(args, "openai_reasoning_effort", "low"),\n'
     '                "local_judge_url": getattr(args, "local_judge_url", None)},\n'),
    # 4. dispatch
    ('    if (ctx.config.get("judge_backend") or "gemini") == "openai":\n'
     '        import openai_judge as OJ\n'
     '        return OJ.call_openai_json(ctx, system_prompt, user_text, schema)\n',
     '    if (ctx.config.get("judge_backend") or "gemini") == "openai":\n'
     '        import openai_judge as OJ\n'
     '        return OJ.call_openai_json(ctx, system_prompt, user_text, schema)\n'
     '    if (ctx.config.get("judge_backend") or "gemini") == "local":\n'
     '        import local_judge as LJ\n'
     '        return LJ.call_local_json(ctx, system_prompt, user_text, schema)\n'),
])

patch(RAE, [
    ('    parser.add_argument("--judge-backend", choices=["gemini", "openai"], default="gemini",\n'
     '                        help="openai: judge calls go to OpenAI (text / input_audio / frames). Evidence + prompts unchanged.")\n',
     '    parser.add_argument("--judge-backend", choices=["gemini", "openai", "local"], default="gemini",\n'
     '                        help="openai: judge calls go to OpenAI (text / input_audio / frames). "\n'
     '                             "local: in-process vLLM server (local_judge_server.py), video+audio by file path. "\n'
     '                             "Evidence + prompts unchanged.")  # judge_backend_local_patched\n'
     '    parser.add_argument("--local-judge-url", default=None, help="local backend: server url (default env LOCAL_JUDGE_URL or http://127.0.0.1:8010)")\n'),
])

# shell: BACKEND=local adds the flags; GEMINI key only required for gemini backend
sh = SH.read_text()
if "judge_backend_local_patched" not in sh:
    shutil.copy(SH, str(SH) + ".bak_local")
    old_key = ('[ -z "$GEMINI_API_KEY" ] && { echo "GEMINI_API_KEY not set"; exit 1; }\n')
    new_key = ('BACKEND=${BACKEND:-gemini}   # judge_backend_local_patched\n'
               '[ "$BACKEND" = "gemini" ] && [ -z "$GEMINI_API_KEY" ] && { echo "GEMINI_API_KEY not set"; exit 1; }\n')
    old_args = 'ARGS="$ARGS --model $MODEL --thinking-level $THINK"\n'
    new_args = ('ARGS="$ARGS --model $MODEL --thinking-level $THINK"\n'
                '[ "$BACKEND" = "local" ] && ARGS="$ARGS --judge-backend local --local-judge-url ${LOCAL_JUDGE_URL:-http://127.0.0.1:8010}"\n')
    for o in (old_key, old_args):
        if sh.count(o) != 1:
            sys.exit(f"[FAIL] run_parallel_multi.sh: expected 1 match for:\n{o}")
    sh = sh.replace(old_key, new_key).replace(old_args, new_args)
    sh = sh.replace('echo "MODEL=$MODEL THINK=$THINK COND=$COND', 'echo "BACKEND=$BACKEND MODEL=$MODEL THINK=$THINK COND=$COND')
    SH.write_text(sh)
    print("[ok] run_parallel_multi.sh")
else:
    print("[skip] run_parallel_multi.sh already patched")
print("done. usage: BACKEND=local MODEL=nemotron-3-nano-omni-30b-fp8 SUF=_nemo bash run_parallel_multi.sh 6 baseline")
