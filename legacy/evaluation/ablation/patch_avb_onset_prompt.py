#!/usr/bin/env python3
"""C1b: opt-in AVB prompt variant with explicit onset comparison.

Run from evaluation/ablation/:  python patch_avb_onset_prompt.py
Backup: new_eval.py.bak_avb_onset

Activation: env var  T2AV_AVB_PROMPT=onset   (unset / anything else = original prompt).
Only build_av_binding_axis_criteria changes; every other axis text is untouched, so
baseline vs revised differ in exactly this block. Works for both new_eval.py
(single agent, HD-EPIC runs) and the agentic axis_binding (imports the same builder).
"""
import shutil
from pathlib import Path

NE = Path("new_eval.py")
src = NE.read_text()
shutil.copy(NE, NE.with_suffix(".py.bak_avb_onset"))

old_head = 'def build_av_binding_axis_criteria(events: List[dict]) -> str:\n    lines = [\n'
assert old_head in src, "build_av_binding_axis_criteria not found"

new_block = '''AVB_ONSET_THRESHOLD_SEC = float(__import__("os").environ.get("T2AV_AVB_ONSET_THRESHOLD", "0.5"))


def _avb_prompt_variant() -> str:
    return (__import__("os").environ.get("T2AV_AVB_PROMPT", "default") or "default").lower()


def build_av_binding_axis_criteria_onset(events: List[dict]) -> str:
    """C1b variant: explicit onset estimation + lag report + threshold."""
    thr = AVB_ONSET_THRESHOLD_SEC
    lines = [
        "- Audio-Visual Binding is evaluated WITHIN each event: whether that event's audio component and visual component are correctly bound in time, assuming both are present and correct.",
        "- Precondition (hierarchical): evaluate this axis only when the event's required audio (Audio Event Correctness) AND required visual component (Visual Event Correctness) are both correct. If either is incorrect or missing, mark this axis no.",
        "- PROCEDURE (mandatory for every evaluated event):",
        "  1. Estimate the AUDIO ONSET: the time in seconds when the required sound / spoken word begins. Use tool timestamps (Whisper word times, FLAM intervals) when provided; otherwise listen for it directly.",
        "  2. Estimate the VISUAL ONSET: the time in seconds when the visible action that should produce that sound begins (the contact moment for impacts, the first lip movement for speech).",
        f"  3. Compute lag = audio_onset - visual_onset in seconds. Report all three numbers in the evidence field exactly as: audio_onset=<s>, visual_onset=<s>, lag=<s>.",
        f"  4. Mark no if |lag| > {thr:g} s, in EITHER direction. A sound that starts before its visible cause is misaligned just as much as a sound that starts after it; do not treat early audio as an anticipation cue.",
        "  5. If you cannot locate one of the two onsets, say which one and mark no (unlocatable onset = binding not verifiable).",
        "- Do NOT judge binding from general impressions such as 'the sound matches the action' or 'the clip looks natural'. Only the onset comparison above counts.",
    ]
    for event in events_of_kind(events, "speech"):
        lines.append(f'- Speech event {quote_label(event["label"])}: audio onset = first phoneme of the word; visual onset = first visible lip/jaw movement for it.')
    for event in events_of_kind(events, "sounding_action"):
        lines.append(f'- Sounding action {quote_label(event["label"])}: audio onset = start of the impact/contact sound; visual onset = the frame where the contact (or the sound-producing motion) begins.')
    if not events_of_kind(events, "speech") and not events_of_kind(events, "sounding_action"):
        lines.append("- There is no explicit audio-visual binding requirement to evaluate for this axis (e.g., a silent-only action). Mark yes unless the prompt implies a required audio-visual link that is violated, subject to the precondition above.")
    return "\\n".join(lines)


def build_av_binding_axis_criteria(events: List[dict]) -> str:
    if _avb_prompt_variant() == "onset":
        return build_av_binding_axis_criteria_onset(events)
    return _build_av_binding_axis_criteria_default(events)


def _build_av_binding_axis_criteria_default(events: List[dict]) -> str:
    lines = [
'''
src = src.replace(old_head, new_block, 1)
NE.write_text(src)
print("patched new_eval.py; activate with  T2AV_AVB_PROMPT=onset  (threshold env T2AV_AVB_ONSET_THRESHOLD, default 0.5)")
