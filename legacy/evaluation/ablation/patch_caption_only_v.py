#!/usr/bin/env python
"""V축 캡션 전용(language_only + external caption) 모드 허용 패치.

허용되는 새 조합:  --axes v --media-input-mode language_only --caption-evidence-mode external --caption-external-json X
                  (--audio-evidence-mode none 이어도 됨: judge는 캡션 텍스트만 봄)
기존 A축 language_only(오디오 도구 텍스트만) 동작은 그대로.

사용: cd evaluation/ablation && python patch_caption_only_v.py      (백업: *.bak_caponly)
"""
import re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
changed = []

def patch(path: Path, replacements):
    src = path.read_text(encoding="utf-8")
    out = src
    for old, new, desc in replacements:
        if old not in out:
            if new in out:
                print(f"  [skip] {path.name}: already patched ({desc})"); continue
            sys.exit(f"  [FAIL] {path.name}: pattern not found ({desc}). 코드가 예상과 다름, 수동 확인 필요.")
        if out.count(old) != 1:
            sys.exit(f"  [FAIL] {path.name}: pattern not unique ({desc})")
        out = out.replace(old, new); changed.append(f"{path.name}: {desc}")
    if out != src:
        shutil.copy(path, path.with_suffix(path.suffix + ".bak_caponly"))
        path.write_text(out, encoding="utf-8")

# ---------------- run_agentic_eval.py : 인자 검증 ----------------
rae = HERE / "run_agentic_eval.py"
patch(rae, [
(
'''    if args.media_input_mode != "video":
        if args.axes != "a":
            parser.error(f"--media-input-mode {args.media_input_mode} requires --axes a "
                         "(Visual/AVB/Temporal/CC axes need the visual track).")
        if args.caption_evidence_mode not in (None, "", "none"):
            parser.error(f"--media-input-mode {args.media_input_mode} is incompatible with "
                         "--caption-evidence-mode (captions are visual-track evidence).")''',
'''    # caption-only V: judge sees ONLY a precomputed caption (no video/audio). Mirrors the
    # A-axis language_only ablation for the Visual axis.
    caption_only_v = (args.media_input_mode == "language_only" and args.axes == "v"
                      and args.caption_evidence_mode == "external")
    if args.media_input_mode != "video" and not caption_only_v:
        if args.axes != "a":
            parser.error(f"--media-input-mode {args.media_input_mode} requires --axes a "
                         "(Visual/AVB/Temporal/CC axes need the visual track), or --axes v with "
                         "--media-input-mode language_only --caption-evidence-mode external (caption-only V).")
        if args.caption_evidence_mode not in (None, "", "none"):
            parser.error(f"--media-input-mode {args.media_input_mode} is incompatible with "
                         "--caption-evidence-mode (captions are visual-track evidence).")''',
 "allow --axes v + language_only + external caption"),
(
'''    if args.media_input_mode == "language_only" and args.audio_evidence_mode == "none":
        parser.error(''',
'''    if args.media_input_mode == "language_only" and args.audio_evidence_mode == "none" and not caption_only_v:
        parser.error(''',
 "audio evidence not required for caption-only V"),
(
'''    if args.media_input_mode == "language_only" and NE.build_audio_evidence_section is None:
        parser.error(''',
'''    if args.media_input_mode == "language_only" and NE.build_audio_evidence_section is None and args.audio_evidence_mode != "none":
        parser.error(''',
 "audio tools import only needed when audio evidence is on"),
])

# ---------------- agentic_common.py : 런타임 가드 + 캡션 허용 + 프롬프트 노트 ----------------
ac = HERE / "agentic_common.py"
patch(ac, [
(
'''    _media_input_mode_early = getattr(args, "media_input_mode", "video") or "video"
    if _media_input_mode_early == "language_only" and not audio_section:
        raise RuntimeError(''',
'''    _media_input_mode_early = getattr(args, "media_input_mode", "video") or "video"
    _caption_mode_early = getattr(args, "caption_evidence_mode", "none") or "none"
    if _media_input_mode_early == "language_only" and not audio_section and _caption_mode_early in (None, "", "none"):
        raise RuntimeError(''',
 "language_only guard: caption may replace audio evidence"),
(
'''    caption_mode = getattr(args, "caption_evidence_mode", "none")
    if caption_mode not in (None, "", "none") and media_input_mode != "video":
        raise RuntimeError(''',
'''    caption_mode = getattr(args, "caption_evidence_mode", "none")
    if caption_mode not in (None, "", "none") and media_input_mode != "video" and not (
            media_input_mode == "language_only" and caption_mode == "external"):
        raise RuntimeError(''',
 "allow external caption in language_only"),
(
'''    if caption_error:
        print(f"  [WARN] Caption evidence issue for {video_path.name}: {caption_error}")
''',
'''    if caption_error:
        print(f"  [WARN] Caption evidence issue for {video_path.name}: {caption_error}")
    # caption-only V: the caption text is the judge's ONLY observation -> empty must be a hard error
    if media_input_mode == "language_only" and not audio_section and not caption_section:
        raise RuntimeError("language_only with caption evidence requires a non-empty caption section but got none"
                           + (f" (caption error: {caption_error})" if caption_error else ""))
''',
 "hard error when caption-only V has no caption"),
(
'''MEDIA_INPUT_NOTES = {
    "audio_only": (''',
'''MEDIA_INPUT_NOTES_CAPTION_ONLY = (
    "MEDIA INPUT NOTE: For this call you are given NO video and NO audio. The ONLY "
    "observation available is the dense video caption included in the user message, "
    "produced by a separate captioning model over the same video. Base your judgment "
    "SOLELY on that caption text plus the prompt/metadata. If any evidence-section "
    "boilerplate tells you to verify against the video itself, ignore it: no video is "
    "provided, so the caption text is the final observation. If the caption does not "
    "clearly support an event's required visual component, judge that event as failure."
)

MEDIA_INPUT_NOTES = {
    "audio_only": (''',
 "add caption-only prompt note"),
])

# 노트 선택 지점: MEDIA_INPUT_NOTES[<mode>] 사용처를 찾아 캡션 전용일 때 다른 노트를 쓰도록 교체
src = ac.read_text(encoding="utf-8")
uses = [m for m in re.finditer(r"MEDIA_INPUT_NOTES\[([^\]]+)\]", src)]
uses = [m for m in uses if "MEDIA_INPUT_NOTES_CAPTION_ONLY" not in src[max(0, m.start()-200):m.start()]]
if uses:
    out = src
    for m in reversed(uses):
        key = m.group(1)
        out = out[:m.start()] + f'(MEDIA_INPUT_NOTES_CAPTION_ONLY if ({key} == "language_only" and (getattr(args, "caption_evidence_mode", "none") or "none") == "external") else MEDIA_INPUT_NOTES[{key}])' + out[m.end():]
    ac.write_text(out, encoding="utf-8"); changed.append(f"agentic_common.py: note selection at {len(uses)} site(s)")
else:
    print("  [WARN] MEDIA_INPUT_NOTES[...] 사용처를 못 찾음. 아래 grep 결과를 보고 노트 선택을 수동으로 넣어야 함:")
    for i, line in enumerate(src.splitlines(), 1):
        if "MEDIA_INPUT_NOTES" in line: print(f"    {i}: {line.strip()}")

print("\npatched:"); [print("  -", c) for c in changed]
print("\ncheck:  python -c \"import ast;ast.parse(open('agentic_common.py').read());ast.parse(open('run_agentic_eval.py').read());print('syntax ok')\"")
