#!/usr/bin/env python
"""캡션 전용 V(language_only + external caption)일 때 system prompt의 CAPTION_GENERAL_GUIDE를
CAPTION_ONLY_GUIDE로 교체. video+caption 조건 프롬프트는 변경 없음. 백업 *.bak_caponly_guide
사용: cd evaluation/ablation && python patch_caption_only_guide.py
"""
import shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent

def patch(path, reps):
    src = path.read_text(encoding="utf-8"); out = src
    for old, new, desc in reps:
        if old not in out:
            if new in out: print(f"  [skip] {path.name}: {desc} (already)"); continue
            sys.exit(f"  [FAIL] {path.name}: not found: {desc}")
        if out.count(old) != 1: sys.exit(f"  [FAIL] {path.name}: not unique: {desc}")
        out = out.replace(old, new); print(f"  [ok] {path.name}: {desc}")
    if out != src:
        shutil.copy(path, path.with_suffix(path.suffix + ".bak_caponly_guide")); path.write_text(out, encoding="utf-8")

# ---- new_eval.py: 캡션 전용 가이드 추가 (CAPTION_GENERAL_GUIDE 바로 뒤) ----
patch(HERE / "new_eval.py", [
('''SYSTEM_PROMPT_CORE_TAIL = """Temporal reasoning:''',
'''CAPTION_ONLY_GUIDE = """Dense caption evidence interpretation guide (caption-only input):

Evidence-use policy (CRITICAL):
- No video or audio is provided in this call. The dense caption below, produced by a separate captioning model that inspected this exact video, is your ONLY observation of the video's content. There is no direct viewing to compare it with.
- If the caption explicitly describes the required visual event (the action, gesture, or visible speaking), treat that as evidence that the event occurred.
- If the caption does not mention the required visual event, or describes something that contradicts it (a different action, a different body side, no visible speaking), judge that event as failure. You cannot verify anything beyond the caption text.
- Where the prompt specifies a body side (left/right hand or arm) and the caption states a side, the stated side must match; a mismatch is a failure for that event. If the caption states no side, do not infer one.
- Caption statements are expert observations rather than final correctness labels. You must still compare them with the original prompt and apply the evaluation criteria yourself.
- Cite the caption phrase (with its timestamp if present) that supports or contradicts each event in the evidence field. Do not invent observations that are not in the caption."""

SYSTEM_PROMPT_CORE_TAIL = """Temporal reasoning:''', "add CAPTION_ONLY_GUIDE"),
])

# ---- agentic_common.py: axis_system_prompt에서 교체 ----
patch(HERE / "agentic_common.py", [
('''    prompt = NE.build_system_prompt(pose_mode, audio_mode, caption_mode, single_axis=True)
    media_note = _select_media_note(ctx.config)
    if media_note:
        prompt = media_note + "\\n\\n" + prompt
    return prompt''',
'''    prompt = NE.build_system_prompt(pose_mode, audio_mode, caption_mode, single_axis=True)
    # caption-only V: the video-vs-caption weighing policy makes no sense without a video;
    # swap it for the caption-only policy (video+caption runs are untouched).
    cfg = ctx.config
    if (cfg.get("media_input_mode", "video") or "video") == "language_only" and \\
            (cfg.get("caption_evidence_mode", "none") or "none") == "external" and caption_mode != "none":
        if NE.CAPTION_GENERAL_GUIDE in prompt:
            prompt = prompt.replace(NE.CAPTION_GENERAL_GUIDE, NE.CAPTION_ONLY_GUIDE)
        else:
            print("  [WARN] caption-only: CAPTION_GENERAL_GUIDE not found in system prompt; guide not swapped")
    media_note = _select_media_note(ctx.config)
    if media_note:
        prompt = media_note + "\\n\\n" + prompt
    return prompt''', "swap guide in axis_system_prompt for caption-only"),
])
print("done; run: python -c \"import ast;[ast.parse(open(f).read()) for f in [\x27new_eval.py\x27,\x27agentic_common.py\x27]];print(\x27syntax ok\x27)\"")
