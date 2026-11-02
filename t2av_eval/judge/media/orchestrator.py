#!/usr/bin/env python3
"""Agentic orchestrator: runs the per-axis evaluators in hierarchical order and
assembles a `result` dict compatible with the CSV writers in agentic_common
(add_result_to_row / build_per_event_long_rows).

Temporal Relation and Temporal Count are two fully independent final axes,
each backed by its own Gemini call (axis_temporal_relation / axis_temporal_count).
There is no derived/combined Temporal field.

Control flow:
    A, V, CC            run unconditionally (mutually independent)
    AVB                 per-event gate: only events whose A and V both passed
    TC-Relation         aggregate gate: only when A, V, AVB all aggregate to yes
    TC-Count            per-event gate: audio-bearing events need A+V+AVB=yes;
                         silent events need V=yes. Only eligible event_ids are
                         sent to the model; a Relation failure never blocks
                         this call.
    Overall             AND over A, V, AVB, TC-Relation, TC-Count
                         (constraint_compliance is reported separately and
                         excluded from overall_temporal_success).
"""

from __future__ import annotations

import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
import json
from typing import Dict, List

import new_eval as NE
from t2av_eval.judge.media.common import EvalContext, CORE_AXIS_KEYS
from t2av_eval.judge.media.axes import audio as axis_audio
from t2av_eval.judge.media.axes import visual as axis_visual
from t2av_eval.judge.media.axes import binding as axis_binding
from t2av_eval.judge.media.axes import temporal_relation as axis_temporal_relation
from t2av_eval.judge.media.axes import temporal_count as axis_temporal_count
from t2av_eval.judge.media.axes import compliance as axis_compliance


def _skipped_relation() -> dict:
    return {
        "label": "no",
        "reason": (
            "Skipped: Audio, Visual, and Audio-Visual Binding did not all pass, "
            "so the between-event temporal relationship is not evaluable."
        ),
        "evidence": "",
    }


def _count_eligible(se: dict, aec_map: Dict[str, str], vec_map: Dict[str, str], avb_map: Dict[str, str]) -> bool:
    """Per-event Temporal Count precondition (see agentic_common docstring).

    Audio-bearing events (speech, sounding action) require A, V, and AVB to
    all be "yes". Silent visual events require only V to be "yes".
    """
    eid = se["event_id"]
    if se["has_audio"]:
        return aec_map.get(eid) == "yes" and vec_map.get(eid) == "yes" and avb_map.get(eid) == "yes"
    return vec_map.get(eid) == "yes"


def _synth_ineligible_count(se: dict) -> dict:
    if se["has_audio"]:
        reason = (
            "Count failed because the event's Audio, Visual, or Audio-Visual Binding "
            "preconditions did not all pass. observed_count was set to 0 by the harness."
        )
    else:
        reason = (
            "Count failed because the event's Visual precondition did not pass. "
            "observed_count was set to 0 by the harness."
        )
    return {
        "event_id": se["event_id"],
        "event_kind": se["kind"],
        "event_label": se["label"],
        "observed_count": 0,
        "required_count": se["required_count"],
        "preconditions_ok": False,
        "count_correct": False,
        "reason": reason,
        "evidence": "",
    }


def _finalize_eligible_count(pe: dict, se: dict) -> dict:
    observed = pe.get("observed_count")
    if observed is None:
        observed = 0
    required = se["required_count"]
    return {
        "event_id": se["event_id"],
        "event_kind": se["kind"],
        "event_label": se["label"],
        "observed_count": observed,
        "required_count": required,
        "preconditions_ok": True,
        "count_correct": observed == required,
        "reason": pe.get("reason", ""),
        "evidence": pe.get("evidence", ""),
    }


def _count_summary(per_event: List[dict]) -> str:
    bits = []
    for pe in per_event:
        if not pe["preconditions_ok"]:
            tag = "preconditions-failed"
        elif pe["count_correct"]:
            tag = "match"
        else:
            tag = "mismatch"
        bits.append(
            f'{pe["event_id"]} {NE.quote_label(pe.get("event_label", ""))}: '
            f'observed={pe["observed_count"]} required={pe["required_count"]} -> {tag}'
        )
    return " | ".join(bits)


def _skipped_axis(note: str) -> dict:
    return {"label": "skipped", "reason": note, "evidence": "", "per_event": []}


def evaluate_video_agentic(ctx: EvalContext) -> dict:
    raws: Dict[str, str] = {}
    prompts: Dict[str, str] = {}

    # ---- A/V-only mode (evidence ablation rows: baseline / caption / tools) ----
    # Runs ONLY the Audio and Visual agents; AVB, TC-Relation, TC-Count and CC
    # are skipped entirely (no Gemini calls, no gating), and overall is not
    # computed. Per-axis A/V columns in the CSV are the comparison target.
    axes_mode = ctx.config.get("axes", "all")
    if axes_mode in ("av", "a", "v"):
        import time
        if axes_mode in ("av", "a"):
            t0 = time.perf_counter()
            a = axis_audio.evaluate(ctx)
            print(f"[TIME] Audio: {time.perf_counter() - t0:.2f}s")
            raws["audio_event_correctness"] = a["raw"]
            prompts["audio_event_correctness"] = a["user_text"]
            aec_pe = a["per_event"]
        else:
            aec_pe = []

        if axes_mode in ("av", "v"):
            t0 = time.perf_counter()
            v = axis_visual.evaluate(ctx)
            print(f"[TIME] Visual: {time.perf_counter() - t0:.2f}s")
            raws["visual_event_correctness"] = v["raw"]
            prompts["visual_event_correctness"] = v["user_text"]
            vec_pe = v["per_event"]
            note = ("Axis not run (--axes av: audio/visual-only evidence ablation)." if axes_mode == "av"
                    else "Axis not run (--axes v: visual-axis-only caption ablation).")
            visual_result = {
                "label": NE._agg_label([pe["label"] for pe in vec_pe]),
                "reason": NE._agg_field(vec_pe, "reason"),
                "evidence": NE._agg_field(vec_pe, "evidence"), "per_event": vec_pe,
            }
        else:
            note = "Axis not run (--axes a: audio-axis-only input-modality ablation)."
            visual_result = _skipped_axis(note)

        audio_result = ({
                "label": NE._agg_label([pe["label"] for pe in aec_pe]),
                "reason": NE._agg_field(aec_pe, "reason"),
                "evidence": NE._agg_field(aec_pe, "evidence"), "per_event": aec_pe,
            } if axes_mode in ("av", "a") else _skipped_axis(note))
        result: Dict[str, dict] = {
            "audio_event_correctness": audio_result,
            "visual_event_correctness": visual_result,
            "audio_visual_binding": _skipped_axis(note),
            "temporal_relation_satisfaction": {"label": "skipped", "reason": note, "evidence": ""},
            "temporal_count_satisfaction": _skipped_axis(note),
            "constraint_compliance": {"label": "skipped", "reason": note, "evidence": ""},
        }
        result["overall_temporal_success"] = ""
        if axes_mode == "av":
            result["overall_reason"] = (
                f"A/V-only run: A={result['audio_event_correctness']['label']}, "
                f"V={result['visual_event_correctness']['label']}. Other axes skipped."
            )
        elif axes_mode == "v":
            result["overall_reason"] = (
                f"V-only run ({ctx.config.get('media_input_mode', 'video')} input): "
                f"V={result['visual_event_correctness']['label']}. Other axes skipped."
            )
        else:
            result["overall_reason"] = (
                f"A-only run ({ctx.config.get('media_input_mode', 'video')} input): "
                f"A={result['audio_event_correctness']['label']}. Other axes skipped."
            )
        result["observed_behavior_summary"] = ""
        result["raw_output"] = json.dumps(raws, ensure_ascii=False)
        result["user_prompt"] = json.dumps(prompts, ensure_ascii=False)
        result["uploaded_file_name"] = getattr(ctx.uploaded, "name", "")
        result["uploaded_file_uri"] = getattr(ctx.uploaded, "uri", "")
        result["media_provenance"] = ctx.config.get("last_media_provenance", "")
        meta = ctx.evidence_meta
        result["pose_evidence_mode"] = meta["pose_evidence_mode"]
        result["mediapipe_hint_used"] = bool(meta["pose_summary"])
        result["mediapipe_error"] = meta["pose_error"]
        result["mediapipe_summary"] = meta["pose_summary"]
        result["audio_evidence_mode"] = meta["audio_evidence_mode"]
        result["audio_evidence_used"] = bool(meta["audio_summary"])
        result["audio_evidence_error"] = meta["audio_error"]
        result["audio_evidence_summary"] = meta["audio_summary"]
        result["caption_evidence_mode"] = meta.get("caption_evidence_mode", "")
        result["caption_evidence_used"] = bool(meta.get("caption_summary", ""))
        result["caption_evidence_error"] = meta.get("caption_error", "")
        result["caption_evidence_summary"] = meta.get("caption_summary", "")
        return result

    # ---- Full hierarchical pipeline ----

    # ---- Independent axes: A, V, CC ----
    # a = axis_audio.evaluate(ctx)
    # v = axis_visual.evaluate(ctx)
    # cc = axis_compliance.evaluate(ctx)
    import time
    parents = ctx.config.get("parent_labels")
    if parents:
        # Reuse A/V per-event labels from an earlier run; no Gemini call for A, V, CC.
        a = {"per_event": parents["audio_event_correctness"], "raw": "", "user_text": "(A labels reused from --parent-labels-csv)"}
        v = {"per_event": parents["visual_event_correctness"], "raw": "", "user_text": "(V labels reused from --parent-labels-csv)"}
        cc = {"constraint": {"label": "skipped", "reason": "CC not run (parent labels reused)", "evidence": ""}, "raw": "", "user_text": ""}
        print("[INFO] A/V/CC reused from parent labels")
    else:
        # ---- Audio ----
        t0 = time.perf_counter()
        a = axis_audio.evaluate(ctx)
        print(f"[TIME] Audio: {time.perf_counter() - t0:.2f}s")

        # ---- Visual ----
        t0 = time.perf_counter()
        v = axis_visual.evaluate(ctx)
        print(f"[TIME] Visual: {time.perf_counter() - t0:.2f}s")

        # ---- Compliance ----
        t0 = time.perf_counter()
        cc = axis_compliance.evaluate(ctx)
        print(f"[TIME] Compliance: {time.perf_counter() - t0:.2f}s")

    raws["audio_event_correctness"] = a["raw"]
    raws["visual_event_correctness"] = v["raw"]
    raws["constraint_compliance"] = cc["raw"]
    prompts["audio_event_correctness"] = a["user_text"]
    prompts["visual_event_correctness"] = v["user_text"]
    prompts["constraint_compliance"] = cc["user_text"]

    aec_pe = a["per_event"]
    vec_pe = v["per_event"]
    aec_map = {pe["event_id"]: pe["label"] for pe in aec_pe}
    vec_map = {pe["event_id"]: pe["label"] for pe in vec_pe}

    # ---- AVB: per-event gate on A and V ----
    # b = axis_binding.evaluate(ctx, aec_map, vec_map)
    t0 = time.perf_counter()
    b = axis_binding.evaluate(ctx, aec_map, vec_map)
    print(f"[TIME] AVB: {time.perf_counter() - t0:.2f}s")

    avb_pe = b["per_event"]
    raws["audio_visual_binding"] = b["raw"]
    prompts["audio_visual_binding"] = b["user_text"]
    avb_map = {pe["event_id"]: pe["label"] for pe in avb_pe}

    aec_label = NE._agg_label([pe["label"] for pe in aec_pe])
    vec_label = NE._agg_label([pe["label"] for pe in vec_pe])
    avb_label = NE._agg_label([pe["label"] for pe in avb_pe])

    # ---- TC-Relation: aggregate gate on A ^ V ^ AVB. Independent Gemini call. ----
    relation_gate = (aec_label == "yes" and vec_label == "yes" and avb_label == "yes")
    if relation_gate:
        print("[START] TC-Relation", flush=True)
        # r = axis_temporal_relation.evaluate(ctx)
        t0 = time.perf_counter()
        r = axis_temporal_relation.evaluate(ctx)
        print(f"[TIME] TC-Relation: {time.perf_counter() - t0:.2f}s")

        relation = r["relation"]
        raws["temporal_relation_satisfaction"] = r["raw"]
        prompts["temporal_relation_satisfaction"] = r["user_text"]
    else:
        relation = _skipped_relation()
        raws["temporal_relation_satisfaction"] = ""
        prompts["temporal_relation_satisfaction"] = ""

    # ---- TC-Count: per-event gate, independent of the Relation gate/result. ----
    eligible_events = [s for s in ctx.all_events if _count_eligible(s, aec_map, vec_map, avb_map)]

    if eligible_events:
        print(f"[START] TC-Count | eligible={len(eligible_events)}", flush=True)
        # t = axis_temporal_count.evaluate(ctx, eligible_events)
        t0 = time.perf_counter()
        t = axis_temporal_count.evaluate(ctx, eligible_events)
        print(f"[TIME] TC-Count: {time.perf_counter() - t0:.2f}s")

        raws["temporal_count_satisfaction"] = t["raw"]
        prompts["temporal_count_satisfaction"] = t["user_text"]
        model_map = {pe["event_id"]: pe for pe in t["count_pe"]}
    else:
        raws["temporal_count_satisfaction"] = ""
        prompts["temporal_count_satisfaction"] = ""
        model_map = {}

    count_pe: List[dict] = []
    for s in ctx.all_events:
        eid = s["event_id"]
        if eid in model_map:
            count_pe.append(_finalize_eligible_count(model_map[eid], s))
        else:
            count_pe.append(_synth_ineligible_count(s))

    count_label = "yes" if all(pe["count_correct"] for pe in count_pe) else "no"

    # ---- Assemble the result dict ----
    result: Dict[str, dict] = {}
    result["audio_event_correctness"] = {
        "label": aec_label, "reason": NE._agg_field(aec_pe, "reason"),
        "evidence": NE._agg_field(aec_pe, "evidence"), "per_event": aec_pe,
    }
    result["visual_event_correctness"] = {
        "label": vec_label, "reason": NE._agg_field(vec_pe, "reason"),
        "evidence": NE._agg_field(vec_pe, "evidence"), "per_event": vec_pe,
    }
    result["audio_visual_binding"] = {
        "label": avb_label, "reason": NE._agg_field(avb_pe, "reason"),
        "evidence": NE._agg_field(avb_pe, "evidence"), "per_event": avb_pe,
    }
    result["temporal_relation_satisfaction"] = relation
    result["temporal_count_satisfaction"] = {
        "label": count_label, "reason": _count_summary(count_pe),
        "evidence": NE._agg_count_field(count_pe, "evidence"), "per_event": count_pe,
    }
    result["constraint_compliance"] = cc["constraint"]

    # Overall = AND over the five core axes (constraint_compliance excluded).
    axis_labels = [result[axis]["label"] for axis in CORE_AXIS_KEYS]
    overall = "yes" if all(l == "yes" for l in axis_labels) else "no"
    result["overall_temporal_success"] = overall
    result["overall_reason"] = (
        f"Agentic AND over core axes: "
        f"A={result['audio_event_correctness']['label']}, "
        f"V={result['visual_event_correctness']['label']}, "
        f"AVB={result['audio_visual_binding']['label']}, "
        f"TC-Relation={result['temporal_relation_satisfaction']['label']}, "
        f"TC-Count={result['temporal_count_satisfaction']['label']} -> {overall}."
    )
    result["observed_behavior_summary"] = ""

    # ---- Meta + provenance for the CSV ----
    result["raw_output"] = json.dumps(raws, ensure_ascii=False)
    result["user_prompt"] = json.dumps(prompts, ensure_ascii=False)
    result["uploaded_file_name"] = getattr(ctx.uploaded, "name", "")
    result["uploaded_file_uri"] = getattr(ctx.uploaded, "uri", "")
    result["media_provenance"] = ctx.config.get("last_media_provenance", "")
    meta = ctx.evidence_meta
    result["pose_evidence_mode"] = meta["pose_evidence_mode"]
    result["mediapipe_hint_used"] = bool(meta["pose_summary"])
    result["mediapipe_error"] = meta["pose_error"]
    result["mediapipe_summary"] = meta["pose_summary"]
    result["audio_evidence_mode"] = meta["audio_evidence_mode"]
    result["audio_evidence_used"] = bool(meta["audio_summary"])
    result["audio_evidence_error"] = meta["audio_error"]
    result["audio_evidence_summary"] = meta["audio_summary"]
    result["caption_evidence_mode"] = meta.get("caption_evidence_mode", "")
    result["caption_evidence_used"] = bool(meta.get("caption_summary", ""))
    result["caption_evidence_error"] = meta.get("caption_error", "")
    result["caption_evidence_summary"] = meta.get("caption_summary", "")
    return result
