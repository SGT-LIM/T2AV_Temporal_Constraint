#!/usr/bin/env python3
"""V-axis: Visual Event Correctness. Per-event, over every target event."""

from __future__ import annotations

import new_eval as NE
from agentic_common import (
    EvalContext,
    PER_EVENT_AXIS_SCHEMA,
    EVENT_TIME_RULE,
    EVENT_TIME_FIELD,
    per_event_schema_with_time,
    axis_system_prompt,
    build_axis_user_text,
    call_gemini_json,
)

AXIS = "visual_event_correctness"

_RULES = (
    "- This axis is PER-EVENT over EVERY target event_id.\n"
    "- For speech events: judge visible speaking behavior only (mouth/lips visible when required, "
    "plausible speaking motion). Do NOT judge whether the spoken word is correct.\n"
    "- For silent/sounding actions: judge whether the visible action is present and correctly performed.\n"
    "- Return one entry per event_id: label yes/no, reason, evidence."
)


def evaluate(ctx: EvalContext) -> dict:
    if not ctx.all_events:
        return {"per_event": [], "raw": "", "user_text": ""}

    criteria = NE.build_visual_axis_criteria(ctx.item_meta["events"])
    user_text = build_axis_user_text(
        ctx, AXIS, criteria, _RULES + (EVENT_TIME_RULE if EVENT_TIME_FIELD else ""),
        only_event_ids=[s["event_id"] for s in ctx.all_events],
    )
    system_prompt = axis_system_prompt(ctx, AXIS)
    parsed, raw = call_gemini_json(ctx, system_prompt, user_text, per_event_schema_with_time(PER_EVENT_AXIS_SCHEMA))
    per_event = NE.normalize_label_per_event(parsed, ctx.all_events, AXIS)
    return {"per_event": per_event, "raw": raw, "user_text": user_text}
