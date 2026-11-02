#!/usr/bin/env python3
"""CC-axis: Constraint Compliance. Single overall judgment, independent of the
hierarchy and excluded from overall_temporal_success."""

from __future__ import annotations

from t2av_eval.judge.media import core as NE
from t2av_eval.judge.media.common import EvalContext, AXIS_RESULT_SCHEMA, axis_system_prompt, build_axis_user_text, call_gemini_json

AXIS = "constraint_compliance"

_RULES = (
    "- Single overall judgment: label yes/no, reason, evidence.\n"
    "- Check non-core constraints: scene, camera/shot, people count, subtitles/on-screen text, "
    "background music, extra sounds/speech/actions, and post-event stillness when required.\n"
    "- Allowed natural motion (blinking, breathing, minor posture, preparation, reset) must NOT fail this axis.\n"
    "- A count/repetition error belongs to Temporal Count, not here."
)


def evaluate(ctx: EvalContext) -> dict:
    """Return {'constraint': {label,reason,evidence}, 'raw', 'user_text'}."""
    criteria = NE.build_constraint_compliance_criteria(ctx.item_meta)
    user_text = build_axis_user_text(ctx, AXIS, criteria, _RULES)
    system_prompt = axis_system_prompt(ctx, AXIS)
    parsed, raw = call_gemini_json(ctx, system_prompt, user_text, AXIS_RESULT_SCHEMA)
    constraint = NE.normalize_axis(parsed, AXIS)
    return {"constraint": constraint, "raw": raw, "user_text": user_text}
