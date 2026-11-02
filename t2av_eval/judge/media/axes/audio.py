#!/usr/bin/env python3
"""A-axis: Audio Event Correctness. Per-event, over events with an audio component."""

from __future__ import annotations

import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
import new_eval as NE
from agentic_common import (
    EvalContext,
    PER_EVENT_AXIS_SCHEMA,
    axis_system_prompt,
    build_axis_user_text,
    call_gemini_json,
)

AXIS = "audio_event_correctness"

_RULES = (
    "- This axis is PER-EVENT over events that have an audio component (speech, sounding action).\n"
    "- Return one entry per applicable event_id: label yes/no, reason, evidence.\n"
    "- Judge only whether the required speech/sound is present and correct in the AUDIO.\n"
    "- Do NOT judge visible motion here (that is Visual Event Correctness)."
)


def evaluate(ctx: EvalContext) -> dict:
    """Return {'per_event': [...normalized...], 'raw': str, 'user_text': str}."""
    if not ctx.audio_events:
        # No audio-bearing event: vacuously satisfied downstream; no model call.
        return {"per_event": [], "raw": "", "user_text": ""}

    criteria = NE.build_audio_axis_criteria(ctx.item_meta["events"])
    user_text = build_axis_user_text(
        ctx, AXIS, criteria, _RULES,
        only_event_ids=[s["event_id"] for s in ctx.audio_events],
    )
    system_prompt = axis_system_prompt(ctx, AXIS)
    parsed, raw = call_gemini_json(ctx, system_prompt, user_text, PER_EVENT_AXIS_SCHEMA)
    per_event = NE.normalize_label_per_event(parsed, ctx.audio_events, AXIS)
    return {"per_event": per_event, "raw": raw, "user_text": user_text}
