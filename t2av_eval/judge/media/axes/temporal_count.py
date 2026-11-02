#!/usr/bin/env python3
"""TC-Count axis: Temporal Count Satisfaction.

A WITHIN-EVENT judgment: for each eligible target event, how many clear,
completed occurrences of that specific event happened. This is evaluated
per event_id, fully independent of Temporal Relation (a separate Gemini
call) -- it never judges ordering, synchronization, overlap, spacing,
rhythm, or audio-visual binding between events.

The orchestrator determines TC-Count eligibility per event (see
agentic_orchestrator._count_eligible) BEFORE calling this module, and sends
only the eligible event_ids. The model reports observed_count only; the
harness (orchestrator) supplies preconditions_ok and computes count_correct
by comparing observed_count against each event's required_count.
"""

from __future__ import annotations

import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
from typing import List

import new_eval as NE
from agentic_common import (
    EvalContext,
    PER_EVENT_COUNT_SCHEMA,
    axis_system_prompt,
    build_axis_user_text,
    call_gemini_json,
)

AXIS = "temporal_count_satisfaction"

_RULES = """Temporal Count is a WITHIN-EVENT judgment.

For each provided event_id independently, count the number of clear,
completed occurrences of that specific target event.

Do not evaluate relationships between different events.
Do not evaluate order, synchronization, overlap, spacing, rhythm,
audio-visual binding, or global sequence correctness.

Do not determine whether the count passes or fails.
Do not compare against required_count.

Only report:
- event_id
- observed_count
- reason
- evidence

The harness will apply event preconditions and compare observed_count
against the required count."""


def evaluate(ctx: EvalContext, eligible_events: List[dict]) -> dict:
    """Return {'count_pe': [...only eligible_events...], 'raw': str, 'user_text': str}.

    `eligible_events` must already be filtered to events whose counting
    preconditions passed (see agentic_orchestrator._count_eligible); this
    function never sends an ineligible event to the model.
    """
    if not eligible_events:
        return {"count_pe": [], "raw": "", "user_text": ""}

    criteria = NE.build_temporal_count_criteria(
        ctx.item_meta["events"], ctx.item_meta.get("temporal_constraint", {}) or {}
    )
    user_text = build_axis_user_text(
        ctx, AXIS, criteria, _RULES,
        only_event_ids=[s["event_id"] for s in eligible_events],
    )
    system_prompt = axis_system_prompt(ctx, AXIS)
    parsed, raw = call_gemini_json(ctx, system_prompt, user_text, PER_EVENT_COUNT_SCHEMA)

    count_pe = NE.normalize_count_per_event(parsed, eligible_events)
    return {"count_pe": count_pe, "raw": raw, "user_text": user_text}
