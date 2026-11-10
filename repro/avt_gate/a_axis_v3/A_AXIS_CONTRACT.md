# A-axis evidence gate, contract v3 (event-level; 2026-11-10)

This supersedes the A-speech behaviour of AVT-Judge and Gate-only described in `../GATE_SPEC.md` §3 (row "A speech / Whisper") and §4.1
("The combined-v2 configuration does not change speech"). Everything else in `GATE_SPEC.md` is unchanged:
- V, AVB, TC and TR;
- the FLAM thresholds;
- calibration;
- the original paper gate as a baseline;
- the evaluation scope.

## 1. Historical implementation (what produced the 11-08 / 11-10 results)

**A speech in AVT-Judge** took the label of the *original paper gate*. That gate is a clip-level decision:
- **Opening:** the gate opened when Whisper heard a requested word of *any* speech event of the clip, or when any sounding event had FLAM
  max below 0.2705. One text call then covered every A event of the clip.
- **Initial label ignored:** the initial PASS / FAIL label was not consulted.
- **Effect:** a speech event could be revised although its own word was not heard, or although the call was triggered only by a FLAM line.
  This is the case in the regression clip `220 LTX hello-then-crossed_arms-then-yes__order`: event_1 "hello" (initial PASS, GT PASS) was
  revised to FAIL after "yes" opened the clip.
- **Scale:** legacy openings of scored speech units were 1,449 + 27 on LTX and 418 + 20 on MOVA (initial PASS + initial FAIL).

**Gate-only** already used the own-word rule for initially-FAIL speech events. Because a heard own word always opened the clip-level gate,
its speech labels are unchanged by this correction.

## 2. Intended rule (implemented in `a_event_gate.py`)

**Decision.** Each event gets an explicit decision from its own initial A judgment and its own tool evidence.

| event | open when | closed when | admitted evidence | direction (Gate-only) |
|---|---|---|---|---|
| speech | initial FAIL **and** one of the event's own target tokens is among the tokens of Whisper segments with no_speech_prob < 0.5 (`gen_stage2_1030.norm`, exact token equality) | initial PASS; own target not recognised (even if another target is); no record / transcript / target; no initial judgment | the full cached Whisper transcript line, unchanged (`gen_stage2_1030.a_parts`) | PASS |
| sounding | initial PASS: FLAM max **<** t_FAIL(alpha); initial FAIL: FLAM max **>=** t_PASS(alpha). Exact values from the frozen config | branch inactive; missing FLAM score; no initial judgment | the FLAM line of this event only | A_FAIL → FAIL; A_PASS → PASS |

**What does not open a gate:**
- FLAM never opens a speech event.
- The Whisper rule is predefined, identical at alpha .01 / .05 / .10, and not calibrated.
- The legacy 0.2705 threshold is not used.

**Requests.**
- One text-only reconsideration request is made per (clip, A) with at least one opened event.
- It uses the existing builders: `bidir_pilot_1106.payload` with the opened events and their true family, and `obs_judge_1028.build_call`
  with `gt={}`.
- The Whisper transcript is included only if a speech event opened; the FLAM lines only for opened sounding events.
- The Stage-1 block lists all A events of the clip, as before.

**Labels.**
- **AVT-Judge:** an opened event takes the label returned for that event. If the output is unresolved, the label stays unresolved and is
  never filled.
- **Gate-only:** the admitted direction.
- **Closed events:** the initial label, exactly, whatever the response says.
- No label is inherited from `original_gate`.

**Reuse of earlier responses.**
- A historical response is reused only when all of these hold:
  - the user content is identical (md5: generation prompt, criteria, rules, Stage-1 judgments, evidence);
  - the same model and settings (gemini-3.6-flash, thinking high, temperature 0, seed 42, JSON schema);
  - text only;
  - the record is newer than 2026-11-02T02:11:48.
- That date is the first point at which the system-prompt / schema builder is verified identical to the current one: the verbatim
  snapshot in refactor commit 786d16e renders the same system md5 `1ac460ed…`, and `run_two_stage.py` is byte-identical.
- Records do not store their system prompt, so older records cannot be verified and are re-called.

## 3. Files

| file | what |
|---|---|
| `a_event_gate.py` | the pure rules (no data, no GT) |
| `tests/test_a_event_gate.py` | 17 deterministic regression tests |
| `run_a_axis_correction.py` | features / select_example / plan / run stages (write-guarded) |
| `a_axis_score.py` | walkthrough / score stages |
| `paper_replacement_A.tex` | replacement method text and the list of superseded A-axis claims |
| `README.md` | commands and output locations |

Frozen configs used (unchanged):
- `../configs/sensitivity/a01|a05|a10/frozen_config.json`;
- a05 equals `../configs/main/frozen_p12_config.json` on A_FAIL / A_PASS.
