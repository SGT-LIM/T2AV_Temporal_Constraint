#!/usr/bin/env python3
"""Offline validation of the agentic pipeline: mock the Gemini client, run the
orchestrator over hand-built item_meta, and check gating + CSV assembly.
No network calls.

Covers the split of the old combined Temporal axis into two fully
independent final axes:
  - temporal_relation_satisfaction (BETWEEN-event, single overall judgment)
  - temporal_count_satisfaction (WITHIN-event, per-event occurrence counts)
"""

import json
import sys
import types as _t
from pathlib import Path

# sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gemini"))

import new_eval as NE
import agentic_common as AC
from agentic_common import build_context
from agentic_orchestrator import evaluate_video_agentic


# ---- Fakes -----------------------------------------------------------------
class FakeResp:
    def __init__(self, text): self.text = text

# Maps the axis name embedded in the "Task: Evaluate exactly ONE axis..." line
# to the short key used in each test's mock `script` dict.
_AXIS_TO_SCRIPT_KEY = {
    "audio_event_correctness": "audio",
    "visual_event_correctness": "visual",
    "audio_visual_binding": "binding",
    "temporal_relation_satisfaction": "temporal_relation",
    "temporal_count_satisfaction": "temporal_count",
    "constraint_compliance": "compliance",
}

class FakeModels:
    def __init__(self, script): self.script = script; self.calls = []
    def generate_content(self, model, contents, config):
        import re
        user_text = contents[-1]
        m = re.search(r"Evaluate exactly ONE axis of this generated video: (\w+)\.", user_text)
        axis_name = m.group(1)
        key = _AXIS_TO_SCRIPT_KEY[axis_name]
        self.calls.append(key)
        return FakeResp(json.dumps(self.script[key]))

class FakeFiles:
    def upload(self, file):
        return _t.SimpleNamespace(name="files/mock", uri="mock://uri", mime_type="video/mp4")

class FakeClient:
    def __init__(self, script):
        self.models = FakeModels(script); self.files = FakeFiles()


def fake_wait(client, uploaded, poll_seconds, timeout_seconds): return uploaded
NE.wait_until_active = fake_wait  # avoid polling the fake file


def make_item_meta():
    """speech 'help' (event_0, order-before) -> silent thumbs-up (event_1)."""
    events = [
        {"index": 0, "kind": "speech", "label": "help", "source_id": "speech_help", "aliases": ["speech_help"]},
        {"index": 1, "kind": "silent_action", "label": "thumbs up", "source_id": "act_thumb", "aliases": ["act_thumb"]},
    ]
    return {
        "item_id": "demo_item",
        "label": "speech_then_silent",
        "modality_combination": "Speech + Action (silent)",
        "generated_prompt": "A person says 'help' then gives a thumbs up.",
        "content": {"speech": "help", "silent_action": "thumbs up"},
        "temporal_constraint": {"timing_type": "relative", "relation": "order",
                                 "sequence": ["speech_help", "act_thumb"]},
        "scene_hint": "indoor room",
        "camera_hint": "static medium shot",
        "events": events,
    }


def make_item_meta_single_speech():
    """Single audio-bearing event, used to test the 'no eligible events -> skip
    the model call entirely' rule for both AVB and TC-Count."""
    events = [
        {"index": 0, "kind": "speech", "label": "help", "source_id": "speech_help", "aliases": ["speech_help"]},
    ]
    return {
        "item_id": "demo_item_single",
        "label": "speech_only",
        "modality_combination": "Speech",
        "generated_prompt": "A person says 'help'.",
        "content": {"speech": "help"},
        "temporal_constraint": {},
        "scene_hint": "indoor room",
        "camera_hint": "static medium shot",
        "events": events,
    }


def make_item_meta_sync():
    """speech 'help' (event_0) required simultaneous with clap (event_1)."""
    events = [
        {"index": 0, "kind": "speech", "label": "help", "source_id": "speech_help", "aliases": ["speech_help"]},
        {"index": 1, "kind": "sounding_action", "label": "clap", "source_id": "clap", "aliases": ["clap"]},
    ]
    return {
        "item_id": "demo_item_sync",
        "label": "help_clap_sync",
        "modality_combination": "Speech + Action (sounding)",
        "generated_prompt": "A person says 'help' while clapping, simultaneously.",
        "content": {"speech": "help", "sounding_action": "clap"},
        "temporal_constraint": {
            "relation_type": "synchronization",
            "timing_type": "relative",
            "value": {"events": ["speech_help", "clap"]},
        },
        "scene_hint": "indoor room",
        "camera_hint": "static medium shot",
        "events": events,
    }


class Args:  # minimal args for build_context (evidence off -> no tool imports)
    model = "gemini-mock"
    media_fps = 0.0
    thinking_level = "none"
    timeout_seconds = 10.0
    pose_evidence_mode = "none"
    mediapipe_fps = 8.0; mediapipe_model_complexity = 1
    mediapipe_near_threshold_norm = 0.6; mediapipe_max_trajectory_samples = 12
    raw_pose_max_frames = 40; pose_summary_lines = 80; pose_detail_chars = 24000
    focus_planner_model = "gemini-mock"; focus_planner_thinking_level = "low"
    no_focus_planner_fallback = False
    audio_evidence_mode = "none"
    whisper_model_size = whisper_device = whisper_compute_type = whisper_language = "x"
    whisper_max_segments = 200; whisper_detail_chars = 4000
    clap_mode = "temporal"; clap_window_seconds = 0.75; clap_hop_seconds = 0.25
    clap_device = "cpu"; clap_max_frames = 60; clap_detail_chars = 8000; clap_negative_queries = None
    flam_model_name = "v1"; flam_device = "cpu"; flam_ckpt_path = "/tmp"; flam_method = "unbiased"
    flam_max_duration_sec = 10.0; flam_threshold = 0.98; flam_min_duration_sec = 0.05
    flam_merge_gap_sec = 0.1; flam_median_filter_size = 3; flam_top_k = 5; flam_detail_chars = 8000
    no_audio_tools = no_visual_tools = no_binding_tools = no_compliance_tools = False
    no_temporal_relation_tools = no_temporal_count_tools = no_temporal_tools = False


def y(eid): return {"event_id": eid, "label": "yes", "reason": "ok", "evidence": "e"}
def n(eid): return {"event_id": eid, "label": "no", "reason": "bad", "evidence": "e"}
def c(eid, k): return {"event_id": eid, "observed_count": k, "reason": "ok", "evidence": "e"}
def rel(label, reason="rel"): return {"label": label, "reason": reason, "evidence": "e"}


def run(script, item_meta=None):
    item_meta = item_meta or make_item_meta()
    client = FakeClient(script)
    ctx = build_context(client, Path("/tmp/x.mp4"), item_meta, Args())
    result = evaluate_video_agentic(ctx)
    # CSV assembly must not raise.
    row = NE.build_success_row_base("x.mp4", Path("x.mp4"), item_meta["item_id"], 1, item_meta, Args())
    row = AC.add_result_to_row(row, result)
    long_rows = row["_per_event_long"]
    return result, client.models.calls, row, long_rows


def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    assert cond, name


print("Case 1: everything passes")
res1, calls1, row1, long_rows1 = run({
    "audio": {"per_event": [y("event_0")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},
    "temporal_relation": rel("yes", "ordered"),
    "temporal_count": {"per_event": [c("event_0", 1), c("event_1", 1)]},
})
check("call order is audio,visual,compliance,binding,temporal_relation,temporal_count",
      calls1 == ["audio", "visual", "compliance", "binding", "temporal_relation", "temporal_count"])
check("temporal_relation_satisfaction == yes", res1["temporal_relation_satisfaction"]["label"] == "yes")
check("temporal_count_satisfaction == yes", res1["temporal_count_satisfaction"]["label"] == "yes")
check("overall_temporal_success == yes", res1["overall_temporal_success"] == "yes")
for pe in res1["temporal_count_satisfaction"]["per_event"]:
    check(f"{pe['event_id']}: observed==required", pe["observed_count"] == pe["required_count"])
    check(f"{pe['event_id']}: preconditions_ok", pe["preconditions_ok"] is True)
    check(f"{pe['event_id']}: count_correct", pe["count_correct"] is True)
check("temporal_constraint_satisfaction not in result", "temporal_constraint_satisfaction" not in res1)
check("row has all agentic CSV columns", all(k in row1 for k in AC.CSV_FIELDNAMES))
check("per-event long rows == 7 (A1+V2+AVB1+Count2+Relation1)", len(long_rows1) == 7)


print("\nCase 2: visual fails on a silent event -> TC-Relation skipped, TC-Count still called for the eligible event")
res2, calls2, row2, _ = run({
    "audio": {"per_event": [y("event_0")]},
    "visual": {"per_event": [y("event_0"), n("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},
    "temporal_count": {"per_event": [c("event_0", 1)]},
})
check("temporal_relation NOT called (aggregate gate closed)", "temporal_relation" not in calls2)
check("temporal_count IS called (event_0 still eligible)", "temporal_count" in calls2)
check("overall_temporal_success == no", res2["overall_temporal_success"] == "no")
check("visual label == no", res2["visual_event_correctness"]["label"] == "no")
check("relation reason marks skip", "Skipped" in res2["temporal_relation_satisfaction"]["reason"])
event1_count = next(pe for pe in res2["temporal_count_satisfaction"]["per_event"] if pe["event_id"] == "event_1")
check("event_1 (ineligible) observed_count == 0", event1_count["observed_count"] == 0)
check("event_1 (ineligible) preconditions_ok == False", event1_count["preconditions_ok"] is False)
check("event_1 (ineligible) count_correct == False", event1_count["count_correct"] is False)
check("aggregate temporal_count_satisfaction == no", res2["temporal_count_satisfaction"]["label"] == "no")


print("\nCase 3: audio fails on the audio-bearing event -> binding skipped for it, TC-Count still runs for the silent event")
res3, calls3, _, _ = run({
    "audio": {"per_event": [n("event_0")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "no", "reason": "bgm", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},  # should be ignored: event_0 not eligible for binding
    "temporal_count": {"per_event": [c("event_1", 1)]},
})
check("binding model NOT called (no eligible binding events)", "binding" not in calls3)
check("temporal_relation NOT called", "temporal_relation" not in calls3)
check("temporal_count IS called (event_1 still eligible)", "temporal_count" in calls3)
check("avb label == no (synth precondition)", res3["audio_visual_binding"]["label"] == "no")
check("avb per_event carries precondition note", "Precondition failed" in res3["audio_visual_binding"]["per_event"][0]["reason"])
check("overall_temporal_success == no", res3["overall_temporal_success"] == "no")
check("CC still evaluated independently == no", res3["constraint_compliance"]["label"] == "no")
event0_count = next(pe for pe in res3["temporal_count_satisfaction"]["per_event"] if pe["event_id"] == "event_0")
check("event_0 (ineligible) observed_count == 0", event0_count["observed_count"] == 0)
check("event_0 (ineligible) preconditions_ok == False", event0_count["preconditions_ok"] is False)
check("event_0 (ineligible) count_correct == False", event0_count["count_correct"] is False)
check("event_0 reason mentions Audio/Visual/Binding", "Audio" in event0_count["reason"] or "Binding" in event0_count["reason"])
check("aggregate temporal_count_satisfaction == no", res3["temporal_count_satisfaction"]["label"] == "no")


print("\nCase 3b: single audio-bearing event fails audio -> no eligible events for AVB or TC-Count -> both model calls skipped")
res3b, calls3b, _, _ = run({
    "audio": {"per_event": [n("event_0")]},
    "visual": {"per_event": [y("event_0")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},  # should be ignored entirely
    "temporal_count": {"per_event": [c("event_0", 1)]},  # should be ignored entirely
}, item_meta=make_item_meta_single_speech())
check("binding model NOT called", "binding" not in calls3b)
check("temporal_relation NOT called", "temporal_relation" not in calls3b)
check("temporal_count model NOT called (no eligible events)", "temporal_count" not in calls3b)
only_count = res3b["temporal_count_satisfaction"]["per_event"][0]
check("event_0 synthesized observed_count == 0", only_count["observed_count"] == 0)
check("event_0 synthesized preconditions_ok == False", only_count["preconditions_ok"] is False)
check("event_0 synthesized count_correct == False", only_count["count_correct"] is False)
check("aggregate temporal_count_satisfaction == no", res3b["temporal_count_satisfaction"]["label"] == "no")


print("\nCase 4: Relation fails, Count passes -> both Temporal calls still occur")
res4, calls4, _, _ = run({
    "audio": {"per_event": [y("event_0")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},
    "temporal_relation": rel("no", "sequential not sync"),
    "temporal_count": {"per_event": [c("event_0", 1), c("event_1", 1)]},
})
check("temporal_relation called", "temporal_relation" in calls4)
check("temporal_count called", "temporal_count" in calls4)
check("temporal_relation_satisfaction == no", res4["temporal_relation_satisfaction"]["label"] == "no")
check("temporal_count_satisfaction == yes", res4["temporal_count_satisfaction"]["label"] == "yes")
check("overall_temporal_success == no", res4["overall_temporal_success"] == "no")


print("\nCase 5: Relation passes, Count fails")
res5, calls5, _, _ = run({
    "audio": {"per_event": [y("event_0")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},
    "temporal_relation": rel("yes", "ordered"),
    "temporal_count": {"per_event": [c("event_0", 2), c("event_1", 1)]},  # event_0 required=1, observed=2
})
check("temporal_relation_satisfaction == yes", res5["temporal_relation_satisfaction"]["label"] == "yes")
check("temporal_count_satisfaction == no", res5["temporal_count_satisfaction"]["label"] == "no")
check("overall_temporal_success == no", res5["overall_temporal_success"] == "no")
check("at least one event has count_correct == False",
      any(pe["count_correct"] is False for pe in res5["temporal_count_satisfaction"]["per_event"]))


print("\nCase 6: Partial Temporal Count eligibility (mixed eligible/ineligible events)")
res6, calls6, _, _ = run({
    "audio": {"per_event": [y("event_0"), y("event_1")]},
    "visual": {"per_event": [y("event_0"), n("event_1")]},  # event_1 visual fails
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},  # only event_0 is eligible for binding
    "temporal_count": {"per_event": [c("event_0", 1)]},  # only event_0 sent to the model
}, item_meta=make_item_meta_sync())
check("temporal_count called with only the eligible event", calls6.count("temporal_count") == 1)
pe_map6 = {pe["event_id"]: pe for pe in res6["temporal_count_satisfaction"]["per_event"]}
check("eligible event_0 uses model-reported observed_count", pe_map6["event_0"]["observed_count"] == 1)
check("eligible event_0 preconditions_ok == True", pe_map6["event_0"]["preconditions_ok"] is True)
check("eligible event_0 count_correct computed from required_count",
      pe_map6["event_0"]["count_correct"] == (pe_map6["event_0"]["observed_count"] == pe_map6["event_0"]["required_count"]))
check("ineligible event_1 observed_count == 0", pe_map6["event_1"]["observed_count"] == 0)
check("ineligible event_1 preconditions_ok == False", pe_map6["event_1"]["preconditions_ok"] is False)
check("ineligible event_1 count_correct == False", pe_map6["event_1"]["count_correct"] is False)
check("aggregate temporal_count_satisfaction == no", res6["temporal_count_satisfaction"]["label"] == "no")


print("\nCase 7: no derived or redundant fields")
check("temporal_constraint_satisfaction not in result", "temporal_constraint_satisfaction" not in res1)
for count_result in res1["temporal_count_satisfaction"]["per_event"]:
    check(f"{count_result['event_id']}: has observed_count", "observed_count" in count_result)
    check(f"{count_result['event_id']}: has preconditions_ok", "preconditions_ok" in count_result)
    check(f"{count_result['event_id']}: has count_correct", "count_correct" in count_result)
    check(f"{count_result['event_id']}: no count_pass", "count_pass" not in count_result)


print("\nCase 8: simultaneous 'help' + clap")

print("  8a: both occur once and simultaneously")
res8a, _, _, _ = run({
    "audio": {"per_event": [y("event_0"), y("event_1")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0"), y("event_1")]},
    "temporal_relation": rel("yes", "simultaneous"),
    "temporal_count": {"per_event": [c("event_0", 1), c("event_1", 1)]},
}, item_meta=make_item_meta_sync())
check("TC-Relation == yes", res8a["temporal_relation_satisfaction"]["label"] == "yes")
check("TC-Count == yes", res8a["temporal_count_satisfaction"]["label"] == "yes")
check("Overall == yes", res8a["overall_temporal_success"] == "yes")

print("  8b: both occur once but sequentially")
res8b, _, _, _ = run({
    "audio": {"per_event": [y("event_0"), y("event_1")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0"), y("event_1")]},
    "temporal_relation": rel("no", "sequential, not simultaneous"),
    "temporal_count": {"per_event": [c("event_0", 1), c("event_1", 1)]},
}, item_meta=make_item_meta_sync())
check("TC-Relation == no", res8b["temporal_relation_satisfaction"]["label"] == "no")
check("TC-Count == yes", res8b["temporal_count_satisfaction"]["label"] == "yes")
check("Overall == no", res8b["overall_temporal_success"] == "no")

print("  8c: help occurs once, clap occurs twice")
res8c, _, _, _ = run({
    "audio": {"per_event": [y("event_0"), y("event_1")]},
    "visual": {"per_event": [y("event_0"), y("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0"), y("event_1")]},
    "temporal_relation": rel("yes", "the required simultaneous occurrence happened"),
    "temporal_count": {"per_event": [c("event_0", 1), c("event_1", 2)]},  # clap required=1, observed=2
}, item_meta=make_item_meta_sync())
check("TC-Relation == yes", res8c["temporal_relation_satisfaction"]["label"] == "yes")
check("TC-Count == no", res8c["temporal_count_satisfaction"]["label"] == "no")
check("Overall == no", res8c["overall_temporal_success"] == "no")
clap_pe = next(pe for pe in res8c["temporal_count_satisfaction"]["per_event"] if pe["event_id"] == "event_1")
check("extra clap handled by TC-Count only", clap_pe["observed_count"] == 2 and clap_pe["count_correct"] is False)

print("  8d: clap visual fails")
res8d, calls8d, _, _ = run({
    "audio": {"per_event": [y("event_0"), y("event_1")]},
    "visual": {"per_event": [y("event_0"), n("event_1")]},
    "compliance": {"label": "yes", "reason": "clean", "evidence": "e"},
    "binding": {"per_event": [y("event_0")]},  # only event_0 eligible for binding
    "temporal_count": {"per_event": [c("event_0", 1)]},  # only event_0 eligible for count
}, item_meta=make_item_meta_sync())
clap_pe_d = next(pe for pe in res8d["temporal_count_satisfaction"]["per_event"] if pe["event_id"] == "event_1")
check("clap observed_count == 0", clap_pe_d["observed_count"] == 0)
check("clap preconditions_ok == False", clap_pe_d["preconditions_ok"] is False)
check("clap count_correct == False", clap_pe_d["count_correct"] is False)
check("TC-Relation skipped (aggregate A/V/AVB gate failed)", "temporal_relation" not in calls8d)
check("Overall == no", res8d["overall_temporal_success"] == "no")


print("\nAll scenarios passed.")
