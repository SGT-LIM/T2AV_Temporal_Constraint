#!/usr/bin/env python3
"""Offline checks of the evidence-gate behaviour (no data, no API). Runs the code used in the experiments:
p12_calib_1108.open_rule (combined gate openings) and alpha_sensitivity.gate_only_labels (Gate-only decisions), with the frozen
configurations in repro/avt_gate/configs.
  python repro/avt_gate/tests/test_gate_rules.py        (or: pytest repro/avt_gate/tests)
"""
import json, math, os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as R

REPO = Path(__file__).resolve().parents[3]
for k in ("T2AV_WORKSPACE", "T2AV_DATA"):
    os.environ.setdefault(k, "/nonexistent/offline_test")       # paths are only formatted, never read, by these functions
os.environ.setdefault("T2AV_OUT_DIR", tempfile.mkdtemp())
sys.path[:0] = [str(REPO / "evaluation/ablation/gepa_stage2"), str(REPO / "evaluation/ablation"), str(REPO / "repro/avt_gate/analysis")]
import p12_calib_1108 as P12                                    # noqa: E402
import alpha_sensitivity as AS                                  # noqa: E402

CFG = {t: json.load(open(REPO / f"repro/avt_gate/configs/{p}"))["config"] for t, p in
       (("main", "main/frozen_p12_config.json"), ("a01", "sensitivity/a01/frozen_config.json"), ("a10", "sensitivity/a10/frozen_config.json"))}
NAN = float("nan")


def u(axis, initial, family=None, flam_max=NAN, vcap=None, off=NAN, prob=NAN):
    return R(axis=axis, initial=initial, family=family or {"A": "A sound", "V": "V", "AVB": "AVB"}.get(axis), flam_max=flam_max, vcap=vcap, off=off, prob=prob)


def opened(r, cfg="main"):
    return P12.open_rule(CFG[cfg], r)[0]


def test_main_config_values():
    c = CFG["main"]
    assert c["A_FAIL"]["params"] == ["t", 0.3723524212837219] and c["A_PASS"]["params"] == ["t", 0.989681363105774]
    assert c["AVB_FAIL"]["params"] == ["T", 1.2, "P", 0.1278] and c["AVB_PASS"]["params"] == ["S", 0.2, "Q", 0.3453]
    assert c["V_FAIL"]["active"] and c["V_PASS"]["active"]
    assert not c["A_SPEECH_FAIL (Whisper absence)"]["active"] and not c["A_SPEECH_PASS (word heard, p >= .5)"]["active"]


def test_flam_boundaries_and_direction():
    t_fail, t_pass = CFG["main"]["A_FAIL"]["params"][1], CFG["main"]["A_PASS"]["params"][1]
    assert opened(u("A", "yes", flam_max=math.nextafter(t_fail, 0)))          # strictly below t opens the FAIL-evidence branch
    assert not opened(u("A", "yes", flam_max=t_fail))                         # equal to t does not
    assert opened(u("A", "no", flam_max=t_pass))                              # >= t opens the PASS-evidence branch
    assert not opened(u("A", "no", flam_max=math.nextafter(t_pass, 0)))
    assert not opened(u("A", "yes", flam_max=0.9999))                         # high FLAM never opens an initial PASS (wrong direction)
    assert not opened(u("A", "no", flam_max=0.0))                             # low FLAM never opens an initial FAIL


def test_synchformer_boundaries_and_direction():
    assert opened(u("AVB", "yes", off=1.2, prob=0.1278))
    assert not opened(u("AVB", "yes", off=1.0, prob=0.99))                    # offset below T
    assert not opened(u("AVB", "yes", off=2.0, prob=math.nextafter(0.1278, 0)))
    assert opened(u("AVB", "no", off=0.2, prob=0.3453))
    assert not opened(u("AVB", "no", off=0.4, prob=0.99))                     # offset above S
    assert not opened(u("AVB", "no", off=0.0, prob=math.nextafter(0.3453, 0)))
    assert not opened(u("AVB", "yes", off=0.0, prob=0.99))                    # in-sync reading never opens an initial PASS
    assert not opened(u("AVB", "no", off=2.0, prob=0.99))                     # large offset never opens an initial FAIL


def test_caption_omission_vs_contradiction():
    assert opened(u("V", "yes", vcap="contradicts"))
    assert not opened(u("V", "yes", vcap="not_mentioned"))                    # omission is not FAIL evidence
    assert not opened(u("V", "yes", vcap="describes"))
    assert opened(u("V", "no", vcap="describes"))
    assert not opened(u("V", "no", vcap="not_mentioned"))                     # omission is not PASS evidence either
    assert not opened(u("V", "no", vcap="contradicts"))


def test_missing_evidence_keeps_gate_closed():
    for r in (u("A", "yes", flam_max=NAN), u("A", "no", flam_max=NAN), u("AVB", "yes"), u("AVB", "no"), u("V", "yes", vcap=None), u("V", "no", vcap="")):
        op, key, fb = P12.open_rule(CFG["main"], r)
        assert not op, r


def test_speech_and_temporal_axes_closed_in_combined_rule():
    assert not opened(u("A", "yes", family="A speech", flam_max=0.0))         # open_rule is closed for speech: its label comes from the original-gate A call (GATE_SPEC 4.1)
    for ax in ("TCC", "TCR"):
        assert not opened(R(axis=ax, initial="yes", family=None, flam_max=NAN, vcap=None, off=NAN, prob=NAN))


def test_inactive_branch_at_alpha01():
    assert not opened(u("V", "yes", vcap="contradicts"), "a01")              # caption predicates exceed 1 % on P01/P02 -> closed
    assert not opened(u("V", "no", vcap="describes"), "a01")
    assert opened(u("AVB", "no", off=0.0, prob=0.8888), "a01") and not opened(u("AVB", "no", off=0.2, prob=0.99), "a01")
    assert opened(u("AVB", "no", off=0.4, prob=0.2247), "a10")


def test_gate_only_mapping_and_closed_gate_keeps_initial():
    import pandas as pd
    U = pd.DataFrame([dict(scored_row1=True, family="A sound", initial="yes", direct_orig_ref="yes"),
                      dict(scored_row1=True, family="A sound", initial="no", direct_orig_ref="no"),
                      dict(scored_row1=True, family="V", initial="yes", direct_orig_ref="yes"),
                      dict(scored_row1=True, family="A speech", initial="no", direct_orig_ref="yes"),
                      dict(scored_row1=False, family="AVB", initial="", direct_orig_ref="")])
    out = AS.gate_only_labels(U, [True, True, False, False, True])
    assert out == ["no", "yes", "yes", "yes", ""]                               # flip when open; keep when closed; speech = Whisper mapping; no Stage-1 -> unanswered


if __name__ == "__main__":
    n = 0
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); n += 1; print("ok", k)
    print(f"{n} tests passed")
