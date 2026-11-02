#!/usr/bin/env python3
"""openai_judge.py / run_agentic_eval.py: GPT-6 Astra support. Idempotent, fails loudly.
  cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint && python evaluation/ablation/patch_openai_astra.py
Changes: gpt-6* treated as reasoning model (reasoning_effort, no temperature); frame detail configurable
(--frame-detail, default low); per-call usage line in the shard log; frame-fps default unchanged (pass --frame-fps 2).
"""
import shutil, sys
from pathlib import Path

ROOT = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation")
OJ, RAE, AC = ROOT / "openai_judge.py", ROOT / "run_agentic_eval.py", ROOT / "agentic_common.py"


def patch(path, pairs, marker):
    src = path.read_text()
    if marker in src:
        print(f"[skip] {path.name} already patched"); return
    shutil.copy(path, str(path) + ".bak_astra")
    for old, new in pairs:
        if src.count(old) != 1:
            sys.exit(f"[FAIL] {path.name}: expected 1 match for:\n{old}")
        src = src.replace(old, new)
    path.write_text(src)
    print(f"[ok] {path.name}")


patch(OJ, [
    ('                            "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}", "detail": "high"}})\n'
     '        prov = f"openai:frames:{fps:g}fps:n={len(frames)}:no_audio"\n',
     '                            "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}",\n'
     '                                          "detail": cfg.get("frame_detail") or "low"}})  # astra_patched\n'
     '        prov = f"openai:frames:{fps:g}fps:n={len(frames)}:{cfg.get(\'frame_detail\') or \'low\'}:no_audio"\n'),
    ('    if not model.startswith("gpt-5"):\n',
     '    if not model.startswith(("gpt-5", "gpt-6")):\n'),
    ('    raw = resp.choices[0].message.content or ""\n'
     '    parsed = NE.parse_model_json(raw)\n',
     '    raw = resp.choices[0].message.content or ""\n'
     '    u = getattr(resp, "usage", None)\n'
     '    if u is not None:\n'
     '        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0\n'
     '        reason = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0\n'
     '        print(f"    [USAGE] {model} in={u.prompt_tokens} cached={cached} out={u.completion_tokens} reasoning={reason}", flush=True)\n'
     '    parsed = NE.parse_model_json(raw)\n'),
], "astra_patched")

patch(RAE, [
    ('    parser.add_argument("--frame-cache-dir", default="frame_cache")\n',
     '    parser.add_argument("--frame-cache-dir", default="frame_cache")\n'
     '    parser.add_argument("--frame-detail", default="low", choices=["low", "high", "auto"],\n'
     '                        help="openai backend: image detail per frame (low = cheapest)")  # astra_patched\n'),
], "astra_patched")

patch(AC, [
    ('                "frame_cache_dir": getattr(args, "frame_cache_dir", None),\n',
     '                "frame_cache_dir": getattr(args, "frame_cache_dir", None),\n'
     '                "frame_detail": getattr(args, "frame_detail", "low"),  # astra_patched\n'),
], "astra_patched")
print("done")
