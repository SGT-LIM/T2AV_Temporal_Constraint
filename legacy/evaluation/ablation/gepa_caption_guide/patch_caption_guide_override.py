#!/usr/bin/env python3
"""Patch agentic_common.axis_system_prompt so ctx.config["caption_guide_override"]
replaces CAPTION_GENERAL_GUIDE in the assembled system prompt.

Same pattern as patch_caption_only_guide.py: idempotent, keeps a .bak_gepa copy.
Only this one block is exposed to GEPA; the rest of the prompt is untouched.

    python patch_caption_guide_override.py path/to/agentic_common.py
"""
import shutil
import sys
from pathlib import Path

ANCHOR = "    media_note = _select_media_note(ctx.config)\n    if media_note:\n        prompt = media_note + \"\\n\\n\" + prompt\n    return prompt\n"
INSERT = (
    "    # GEPA hook: replace the caption evidence-use policy with the candidate text.\n"
    "    _ov = cfg.get(\"caption_guide_override\")\n"
    "    if _ov and caption_mode != \"none\":\n"
    "        if NE.CAPTION_GENERAL_GUIDE in prompt:\n"
    "            prompt = prompt.replace(NE.CAPTION_GENERAL_GUIDE, _ov)\n"
    "        elif NE.CAPTION_ONLY_GUIDE in prompt:\n"
    "            prompt = prompt.replace(NE.CAPTION_ONLY_GUIDE, _ov)\n"
    "        else:\n"
    "            print(\"  [WARN] caption_guide_override set but no caption guide found in prompt\")\n"
)

def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "agentic_common.py")
    src = path.read_text(encoding="utf-8")
    if "caption_guide_override" in src:
        print("already patched")
        return
    if ANCHOR not in src:
        raise SystemExit("anchor not found in axis_system_prompt; patch by hand (see INSERT)")
    shutil.copy(path, path.with_suffix(path.suffix + ".bak_gepa"))
    path.write_text(src.replace(ANCHOR, INSERT + ANCHOR), encoding="utf-8")
    print(f"patched {path}")

if __name__ == "__main__":
    main()
