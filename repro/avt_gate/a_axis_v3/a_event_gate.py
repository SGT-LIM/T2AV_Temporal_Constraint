#!/usr/bin/env python3
"""Corrected A-axis evidence gate: one explicit decision per event (A-axis contract v3, 2026-11-10).

Pure functions only (no data access, no model calls); the data layer is run_a_axis_correction.py. GT is never an input here.

Speech events (Whisper; predefined rule, identical at every alpha, not calibrated):
  open  <=> the event's own initial A judgment is FAIL ('no') AND one of the event's own requested target tokens occurs among the
            tokens of the Whisper segments with no_speech_prob < 0.5 (existing normalisation gen_stage2_1030.norm, exact token
            equality; no substring / fuzzy matching).
  closed otherwise: every initially-PASS speech event; own target not recognised (even if another event's target is recognised);
            missing record / transcript / target text (missing evidence is never evidence of absence); no valid initial judgment.
  FLAM never opens a speech event.
Sounding events (FLAM; frozen event-level rule of the given alpha, exact thresholds and operators read from the frozen config):
  initial PASS ('yes') -> FAIL-evidence branch A_FAIL: open <=> flam_max <  t   (strict)
  initial FAIL ('no')  -> PASS-evidence branch A_PASS: open <=> flam_max >= t   (inclusive)
  closed: branch inactive in the config, missing FLAM score, or no valid initial judgment. The legacy T_flam = 0.2705 is not used.
Final labels:
  AVT-Judge  opened event -> the label returned for THAT event by the (clip, A) reconsideration request built from the admitted
             evidence; unresolved / invalid response -> '' (unresolved, never filled). Closed event -> its initial label, exactly,
             whatever the response says about it.
  Gate-only  same openings; opened speech -> 'yes' (PASS); opened sounding -> the admitted direction (A_FAIL -> 'no', A_PASS -> 'yes');
             closed -> initial label.
"""
import math
import re

LEGACY_T_FLAM = 0.2705          # documented only so that tests can assert it is never used
SPEECH_NSP_MAX = 0.5            # segment filter: no_speech_prob < 0.5


def norm(t):
    """gen_stage2_1030.norm, unchanged: lower-case, strip everything except [a-z0-9'] inside each whitespace token."""
    return [w for w in (re.sub(r"[^a-z0-9']", "", x.lower()) for x in (t or "").split()) if w]


def heard_tokens(whisper):
    """token set of the segments with no_speech_prob < 0.5; None when the record or its segments are missing."""
    if not whisper or not isinstance(whisper.get("segments"), list):
        return None
    segs = [s for s in whisper["segments"] if s.get("no_speech_prob") is not None and s["no_speech_prob"] < SPEECH_NSP_MAX]
    return {w for s in segs for w in norm(s.get("text", ""))}


def speech_decision(initial, target_text, heard):
    """-> dict(open, branch, reason, recognized, target_tokens, matched_tokens). heard = token set or None (no transcript)."""
    tgt = sorted(set(norm(target_text)))
    matched = sorted(set(tgt) & heard) if heard is not None else []
    rec = bool(matched)
    d = dict(open=False, branch="A_SPEECH (Whisper, own target)", recognized=rec, target_tokens=tgt, matched_tokens=matched)
    if initial not in ("yes", "no"):
        return dict(d, reason="closed: no valid initial A judgment (unanswered)")
    if initial == "yes":
        return dict(d, reason="closed: initial PASS (speech gate never opens for an initially-PASS event)")
    if heard is None:
        return dict(d, reason="closed: no Whisper record / transcript (missing evidence is not evidence)")
    if not tgt:
        return dict(d, reason="closed: event has no requested target text")
    if not rec:
        return dict(d, reason="closed: own target word not recognised (other events' words do not count)")
    return dict(d, open=True, reason="open: initial FAIL and own target word recognised", direction="yes")


def sound_decision(initial, flam_max, cfg):
    """frozen event-level FLAM rule. cfg = the 'config' dict of a frozen configuration (A_FAIL / A_PASS entries)."""
    if initial not in ("yes", "no"):
        return dict(open=False, branch="", reason="closed: no valid initial A judgment (unanswered)", threshold=None, operator="")
    k = "A_FAIL" if initial == "yes" else "A_PASS"
    c = cfg[k]
    op = "<" if k == "A_FAIL" else ">="
    if not c.get("active"):
        return dict(open=False, branch=k, reason=f"closed: branch {k} inactive in the frozen config", threshold=None, operator=op)
    t = c["params"][1]
    if not isinstance(t, (int, float)) or isinstance(t, bool):
        raise ValueError(f"non-numeric threshold in frozen config for {k}: {t!r}")
    if flam_max is None or (isinstance(flam_max, float) and math.isnan(flam_max)):
        return dict(open=False, branch=k, reason="closed: no FLAM score (missing evidence)", threshold=t, operator=op)
    o = (flam_max < t) if k == "A_FAIL" else (flam_max >= t)
    return dict(open=bool(o), branch=k, threshold=t, operator=op, direction=("no" if k == "A_FAIL" else "yes"),
                reason=f"{'open' if o else 'closed'}: FLAM max {flam_max!r} {op} {t!r} is {bool(o)}")


def decide(event):
    """event: dict(kind in {'speech','sounding'}, initial, target_text, heard, flam_max, cfg). -> decision dict."""
    if event["kind"] == "speech":
        return dict(speech_decision(event["initial"], event.get("target_text", ""), event.get("heard")), kind="speech")
    if event["kind"] == "sounding":
        return dict(sound_decision(event["initial"], event.get("flam_max"), event["cfg"]), kind="sounding")
    return dict(open=False, kind=event["kind"], branch="", reason="closed: not an A-axis speech / sounding event")


def avt_judge_label(initial, decision, response_label):
    """-> (label, source). response_label = the per-event label parsed from the request ('yes'/'no') or None."""
    if not decision["open"]:
        return (initial if initial in ("yes", "no") else ""), ("closed: initial label kept" if initial in ("yes", "no") else "unanswered (no initial judgment)")
    if response_label in ("yes", "no"):
        return response_label, "open: reconsideration label"
    return "", "open: unresolved model response (not filled)"


def gate_only_label(initial, decision):
    if not decision["open"]:
        return (initial if initial in ("yes", "no") else ""), ("closed: initial label kept" if initial in ("yes", "no") else "unanswered (no initial judgment)")
    return decision["direction"], f"open: admitted direction ({decision['kind']})"


def request_events(decisions):
    """events whose gates opened, with the evidence family admitted for each (grouping key: clip x A)."""
    return {e: ("A speech" if d["kind"] == "speech" else "A sound") for e, d in decisions.items() if d["open"]}
