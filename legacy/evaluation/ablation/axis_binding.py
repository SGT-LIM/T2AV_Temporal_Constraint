#!/usr/bin/env python3
# Replaced by t2av_eval/judge/media/axes/binding.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""AVB-axis: Audio-Visual Binding. Per-event, GATED per-event on A and V.

An event's binding is evaluated only when that same event's Audio Event
Correctness AND Visual Event Correctness are both "yes" (the hierarchical
precondition). Ineligible events are synthesized as "no" without a model call,
and if no event is eligible the model call is skipped entirely.
"""

from __future__ import annotations

from typing import Dict

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

AXIS = "audio_visual_binding"

_PRECOND_NOTE = (
    " [Precondition failed: this event's audio or visual component is not correct, "
    "so binding is not evaluable.]"
)

_RULES = (
    "- Audio-Visual Binding is judged WITHIN each event: whether that event's audio and visual "
    "components are temporally and causally aligned, ASSUMING both are present and correct.\n"
    "- Only the event_ids listed above reached this axis (their audio and visual already passed).\n"
    "- Return one entry per listed event_id: label yes/no, reason, evidence.\n"
    "- Mark no if the audio and visual are offset, disconnected, or otherwise not bound."
)


def evaluate(ctx: EvalContext, aec_map: Dict[str, str], vec_map: Dict[str, str]) -> dict:
    """Return {'per_event': [...over all binding_events...], 'raw', 'user_text'}."""
    binding_events = ctx.binding_events
    if not binding_events:
        return {"per_event": [], "raw": "", "user_text": ""}

    eligible = [
        s for s in binding_events
        if aec_map.get(s["event_id"]) == "yes" and vec_map.get(s["event_id"]) == "yes"
    ]

    raw, user_text = "", ""
    model_map: Dict[str, dict] = {}
    if eligible:
        criteria = NE.build_av_binding_axis_criteria(ctx.item_meta["events"])
        user_text = build_axis_user_text(
            ctx,
            AXIS,
            criteria,
            _RULES + (EVENT_TIME_RULE if EVENT_TIME_FIELD else ""),
            only_event_ids=[s["event_id"] for s in eligible],
        )
        system_prompt = axis_system_prompt(ctx, AXIS)

        print(
            f"[START] AVB Gemini call | "
            f"eligible_events={[s['event_id'] for s in eligible]} | "
            f"user_text_len={len(user_text)}",
            flush=True,
        )

        parsed, raw = call_gemini_json(
            ctx,
            system_prompt,
            user_text,
            per_event_schema_with_time(PER_EVENT_AXIS_SCHEMA),
        )

        print("[DONE] AVB Gemini call", flush=True)

        model_pe = NE.normalize_label_per_event(parsed, eligible, AXIS)
        model_map = {pe["event_id"]: pe for pe in model_pe}

    # Reassemble over ALL binding events, synthesizing "no" for ineligible ones.
    per_event = []
    for s in binding_events:
        eid = s["event_id"]
        if eid in model_map:
            per_event.append(model_map[eid])
        else:
            per_event.append({
                "event_id": eid,
                "event_kind": s["kind"],
                "event_label": s["label"],
                "label": "no",
                "reason": ("Binding not evaluated." + _PRECOND_NOTE).strip(),
                "evidence": "",
            })
    return {"per_event": per_event, "raw": raw, "user_text": user_text}
