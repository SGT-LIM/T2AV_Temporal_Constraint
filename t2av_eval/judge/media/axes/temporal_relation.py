#!/usr/bin/env python3
"""TC-Relation axis: Temporal Relation Satisfaction.

A BETWEEN-EVENT judgment: whether different target events satisfy the
required temporal relationship (order, synchronization, overlap, spacing,
rhythm, or start/end timing). This is a single overall yes/no judgment, not
per-event, and it never counts repetitions -- that is axis_temporal_count's
job, evaluated by a fully separate Gemini call.

Only invoked by the orchestrator once the aggregate Audio, Visual, and
Audio-Visual Binding gate has passed; otherwise the orchestrator synthesizes
a skipped "no" result without calling this module.
"""

from __future__ import annotations

from t2av_eval.judge.media import core as NE
from t2av_eval.judge.media.common import EvalContext, AXIS_RESULT_SCHEMA, axis_system_prompt, build_axis_user_text, call_gemini_json

AXIS = "temporal_relation_satisfaction"

_RULES = """Temporal Relation is a BETWEEN-EVENT judgment.

Evaluate only whether different target events satisfy the required temporal
relationship, such as order, synchronization, overlap, spacing, rhythm,
or start/end timing.

Do not count event repetitions.
Do not determine observed_count.
Do not fail merely because an event occurred the wrong number of times.
Repetition counting is handled by a separate Temporal Count agent.

For synchronized events, evaluate whether the relevant occurrences of the
different target events happened together as required.

For ordered events, evaluate whether the required event-to-event ordering
was satisfied.

Judge only the relationship between events, not the correctness or count
of each individual event.
- Return a SINGLE overall judgment: label yes/no, reason, evidence."""


def evaluate(ctx: EvalContext) -> dict:
    """Return {'relation': {label,reason,evidence}, 'raw': str, 'user_text': str}."""
    events = ctx.item_meta["events"]
    tc = ctx.item_meta.get("temporal_constraint", {}) or {}

    criteria = NE.build_temporal_relation_criteria(events, tc)
    user_text = build_axis_user_text(ctx, AXIS, criteria, _RULES)
    system_prompt = axis_system_prompt(ctx, AXIS)
    parsed, raw = call_gemini_json(ctx, system_prompt, user_text, AXIS_RESULT_SCHEMA)

    relation = NE.normalize_axis(parsed, AXIS)
    return {"relation": relation, "raw": raw, "user_text": user_text}
