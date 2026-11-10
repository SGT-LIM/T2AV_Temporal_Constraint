#!/usr/bin/env python3
"""Deterministic checks of the corrected A-axis contract (no data, no API).
  python repro/avt_gate/a_axis_v3/tests/test_a_event_gate.py      (or: pytest repro/avt_gate/a_axis_v3/tests)
Data-dependent checks (equivalence with p12_calib_1108.open_rule on every cached unit, GT-independence of openings and requests,
the regression clip, non-A invariance) run in run_a_axis_correction.py score and are written to checks.json.
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import a_event_gate as AG                                                           # noqa: E402

CFGD = HERE.parents[1] / "configs"
CFG = {t: json.load(open(CFGD / p))["config"] for t, p in (("a01", "sensitivity/a01/frozen_config.json"), ("a05", "sensitivity/a05/frozen_config.json"),
                                                          ("a10", "sensitivity/a10/frozen_config.json"), ("main", "main/frozen_p12_config.json"))}
HEARD = {"below", "yes"}                     # transcript "below, yes." of 220 LTX hello-then-crossed_arms-then-yes__order


def sp(initial, text, heard=HEARD):
    return AG.decide(dict(kind="speech", initial=initial, target_text=text, heard=heard))


def snd(initial, x, cfg="a05"):
    return AG.decide(dict(kind="sounding", initial=initial, flam_max=x, cfg=CFG[cfg]))


def test_initial_pass_recognised_speech_is_closed_and_kept():
    d = sp("yes", "yes")
    assert d["recognized"] and not d["open"]
    assert AG.avt_judge_label("yes", d, "no") == ("yes", "closed: initial label kept")
    assert AG.gate_only_label("yes", d)[0] == "yes"


def test_initial_fail_own_target_recognised_opens():
    d = sp("no", "yes")
    assert d["open"] and d["matched_tokens"] == ["yes"]
    assert AG.gate_only_label("no", d)[0] == "yes"
    assert AG.avt_judge_label("no", d, "no")[0] == "no" and AG.avt_judge_label("no", d, "yes")[0] == "yes"   # opening does not force a revision


def test_other_events_word_does_not_open():
    d = sp("no", "hello")                          # 'yes' (another event's target) is heard, 'hello' is not
    assert not d["recognized"] and not d["open"]
    assert AG.avt_judge_label("no", d, "yes") == ("no", "closed: initial label kept")


def test_regression_hello_stays_pass():
    # 220 LTX hello-then-crossed_arms-then-yes__order: event_1 'hello' initial PASS; legacy clip gate opened by 'yes' revised it to FAIL
    d1, d3 = sp("yes", "hello"), sp("yes", "yes")
    assert not d1["open"] and not d3["open"]
    assert AG.avt_judge_label("yes", d1, "no")[0] == "yes" and AG.gate_only_label("yes", d1)[0] == "yes"


def test_exact_token_no_substring_or_fuzzy():
    assert not sp("no", "hello", heard={"hellooo", "hell", "yellow"})["open"]
    assert not sp("no", "help", heard={"helpful"})["open"]
    assert sp("no", "Hello!", heard={"hello"})["open"]            # existing normalisation (case / punctuation) kept
    assert AG.norm("Hello? Stop. Stop.") == ["hello", "stop", "stop"] and AG.norm("don't") == ["don't"]


def test_segment_filter_no_speech_prob():
    w = {"segments": [{"text": "hello", "no_speech_prob": 0.5}, {"text": "yes", "no_speech_prob": 0.4999}]}
    assert AG.heard_tokens(w) == {"yes"}
    assert AG.heard_tokens(None) is None and AG.heard_tokens({}) is None


def test_missing_transcript_closes():
    d = sp("no", "hello", heard=None)
    assert not d["open"] and "missing evidence" in d["reason"]
    assert not sp("no", "", heard={"x"})["open"]


def test_flam_never_opens_speech():
    # a speech event has no FLAM path: even a FAIL-evidence FLAM score cannot open it
    d = AG.decide(dict(kind="speech", initial="no", target_text="hello", heard={"yes"}, flam_max=0.0, cfg=CFG["a05"]))
    assert not d["open"]
    dec = {"event_1": d, "event_2": snd("yes", 0.01)}           # event_2 sounding opens (FLAM < t)
    assert AG.request_events(dec) == {"event_2": "A sound"}
    assert AG.avt_judge_label("no", dec["event_1"], "yes")[0] == "no"


def test_closed_sounding_not_changed_by_other_opening():
    dec = {"event_1": sp("no", "yes"), "event_2": snd("yes", 0.9)}          # speech opens; sounding closed (0.9 >= t)
    assert dec["event_1"]["open"] and not dec["event_2"]["open"]
    assert AG.request_events(dec) == {"event_1": "A speech"}
    assert AG.avt_judge_label("yes", dec["event_2"], "no")[0] == "yes" and AG.gate_only_label("yes", dec["event_2"])[0] == "yes"


def test_flam_boundaries_exact_operators_all_alphas():
    for a in ("a01", "a05", "a10"):
        tf, tp = CFG[a]["A_FAIL"]["params"][1], CFG[a]["A_PASS"]["params"][1]
        assert snd("yes", math.nextafter(tf, -1), a)["open"] and not snd("yes", tf, a)["open"]          # strict <
        assert snd("no", tp, a)["open"] and not snd("no", math.nextafter(tp, -1), a)["open"]             # inclusive >=
        assert snd("yes", 0.0, a)["direction"] == "no" and snd("no", 1.0, a)["direction"] == "yes"
    assert CFG["a05"]["A_FAIL"]["params"][1] == 0.3723524212837219 and CFG["a05"]["A_PASS"]["params"][1] == 0.989681363105774
    assert CFG["a05"]["A_FAIL"] == CFG["main"]["A_FAIL"] and CFG["a05"]["A_PASS"] == CFG["main"]["A_PASS"]


def test_legacy_threshold_not_used():
    # a score between the legacy T_flam (.2705) and the a05 FAIL threshold opens under a05 only because of the frozen value
    x = 0.30
    assert AG.LEGACY_T_FLAM < x < CFG["a05"]["A_FAIL"]["params"][1] and snd("yes", x)["open"]
    assert not snd("yes", 0.25, "a01")["open"]                   # below legacy T_flam but above the a01 threshold -> closed


def test_missing_flam_closes():
    assert not snd("yes", None)["open"] and not snd("no", float("nan"))["open"]


def test_absent_initial_judgment_unanswered():
    for d in (sp("", "yes"), sp(None, "yes"), snd("", 0.0)):
        assert not d["open"]
        assert AG.avt_judge_label("", d, "yes") == ("", "unanswered (no initial judgment)")
        assert AG.gate_only_label("", d)[0] == ""


def test_unresolved_response_not_filled():
    d = sp("no", "yes")
    assert AG.avt_judge_label("no", d, None) == ("", "open: unresolved model response (not filled)")
    assert AG.avt_judge_label("no", d, "maybe")[0] == ""


def test_same_openings_for_both_methods():
    for d in (sp("no", "yes"), sp("yes", "yes"), snd("yes", 0.1), snd("no", 0.995), snd("no", 0.5)):
        assert (AG.avt_judge_label("no", d, "no")[1].startswith("open")) == d["open"] == AG.gate_only_label("no", d)[1].startswith("open")


def test_gt_not_an_input():
    import inspect
    for f in (AG.speech_decision, AG.sound_decision, AG.decide, AG.avt_judge_label, AG.gate_only_label, AG.request_events):
        assert not any("gt" == p or p.startswith("gt_") for p in inspect.signature(f).parameters)


def test_no_inheritance_from_legacy_gate():
    import inspect
    src = inspect.getsource(AG)
    assert "original_gate" not in src.split('"""', 2)[2]          # code body never reads the legacy label


if __name__ == "__main__":
    fs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bad = 0
    for f in fs:
        try:
            f(); print("PASS", f.__name__)
        except AssertionError as e:
            bad += 1; print("FAIL", f.__name__, e)
    print(f"{len(fs) - bad}/{len(fs)} passed"); sys.exit(1 if bad else 0)
