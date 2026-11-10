# Evidence gate used in the latest experiments (verified from code, frozen configs and run outputs)

> **Correction (2026-11-10, branch `fix/a-axis-event-gate-2026-11-10`).** The A-speech behaviour of AVT-Judge described below (§3 row "A speech / Whisper" and §4.1: the speech label is inherited from the clip-level original-gate call) is the *historical* implementation. It does not match the intended event-level rule and is superseded by `a_axis_v3/A_AXIS_CONTRACT.md` (contract v3). Everything else in this file is unchanged.


Sources:
- code: the portable copies in this branch (`evaluation/ablation/gepa_stage2/*`); originals and hashes are listed in
  `provenance/ORIGINAL_CODE_SHA256.txt`;
- configs: `configs/`;
- runs: `final_benchmark_1108`, `sanjoy_two_baselines_2026-11-08`, `sensitivity_2026-11-10` (see README).

## 1. Which configuration is "main"

**Paper benchmark.** `final_benchmark_1108` (`docs/final_benchmark_2026-11-08.md` in the workspace) evaluates the combined gate with
`calibration_v2`:
- `configs/main/frozen_p12_config.json`, md5 `e495ea7bb902b4cfc02c38a29badd74d`;
- empirical admission limit alpha = .05.

**Same configuration in later work:**
- The paper-table handoff (2026-11-09) checks the same file.
- The 2026-11-10 sensitivity study treats alpha = .05 as the existing reference and reproduces it exactly (`configs/sensitivity/a05` has the
  same rules and counts).
- The alpha = .01 / .10 configurations are sensitivity settings only. They are not a default and were not selected on test results.

**Historical.** `configs/historical/v1_frozen_p12_config.json` is the pre-correction configuration (AVB PASS conf ≥ .3221). It was selected
before the 39 explicit AVB answers were restored to the calibration population.

## 2. Methods built on the gate

| name in paper / tables | code column | what happens when the gate opens | when closed |
|---|---|---|---|
| AVT-Judge (combined gated two-stage, v2) | `combined` | one text-only Stage-2 reconsideration call per opened (dataset, item, axis); its per-event label is used | media-only (Stage-1) label kept |
| Gate-only (direct-combined-v2) | `direct_comb` | the admitted evidence direction is assigned directly (initial PASS → FAIL, initial FAIL → PASS); no model call | media-only label kept |
| original paper gate (baseline) | `original_gate` | Stage-2 call (rules in §4) | media-only label kept |

## 3. Combined gate v2 (AVT-Judge and Gate-only), alpha = .05

For A sounding, V and AVB, the branch is chosen by the media-only (initial) label of each event × axis unit only:
- initial PASS → FAIL-evidence branch;
- initial FAIL → PASS-evidence branch.

A speech is not branch-based (§4.1).

`p12_calib_1108.open_rule`:

| axis / tool | initial PASS: opens if (FAIL evidence) | initial FAIL: opens if (PASS evidence) | Stage-2 payload (AVT-Judge) |
|---|---|---|---|
| A sounding / FLAM (first query of the event, whole-clip max score) | FLAM max **< 0.3723524212837219** | FLAM max **≥ 0.989681363105774** | FLAM lines of the opened sounding events only |
| A speech / Whisper | **not branch-based.** Speech events take the original-gate A label (§4, A), whatever the initial label; see §4.1 | (same rule) | the original-gate A request |
| V / caption check of the AVoCaDO caption (verdict per event: describes / contradicts / not_mentioned) | verdict **= contradicts** | verdict **= describes** | the caption text |
| AVB / Synchformer action-window reading of the event (\|offset\| s, confidence of the reported offset) | \|offset\| **≥ 1.2** and conf **≥ 0.1278** | \|offset\| **≤ 0.2** and conf **≥ 0.3453** | the Synchformer lines of the item |
| TC, TR | closed (no gate) | closed | – |

**Rule details:**
- **Boundaries:** FAIL-evidence FLAM is strict (<). All other thresholds are inclusive (≥ / ≤).
- **Missing tool output:** missing evidence (no FLAM record or query, no Synchformer reading, no caption-check verdict) keeps the gate
  closed. The unit gets the media-only label. A missing tool output never counts as evidence.
- **Caption omission vs contradiction:** "not_mentioned" opens neither branch. An omission is never treated as contradiction or as support.
- **No media-only label:** units without a valid media-only label are never opened. They stay unanswered by the established prerequisite
  rules.

**Stage-2 call (AVT-Judge):**
- Builder: `obs_judge_1028.build_call` via `final_benchmark_1108.comb_call`.
- System prompt: `new_eval.build_system_prompt("none","none","none", single_axis=True)`.
- User prompt: generation prompt, axis criteria, `OBS_RULES` (md5 `556c2b2ef432344bbe8a53bfef15e0b1`), Stage-1 block, observation.
  - The Stage-1 block holds all non-gated Stage-1 events of the axis, using the corrected AVB anchor builder.
- Output: JSON, schema `run_two_stage.SCHEMA[axis]`.
- Media: text only; no video or audio.
- Model: `gemini-3.6-flash`, thinking `high`, temperature 0, seed 42.
- Label: the per-event label (`audit_1106.s2_event`). A failed or empty output is **missing**; it is never filled.
- Retries: up to 3 attempts per request, and a billing-cap error stops the run.

**Gate-only:**
- Same openings as AVT-Judge.
- An opened unit gets the opposite of its initial label, because each branch is directional.
- For A speech it uses the direct-original Whisper mapping (`sanjoy_controls.direct_labels`):
  - if the original A gate opened for the clip and **this event's own** target word is heard → PASS;
  - otherwise the initial label is kept.
  - It never assigns FAIL to a speech event, so it changes only initially-FAIL speech events.

## 4. Original paper gate (baseline; `PREREGISTERED_RULE.json`, `flam_threshold.json`)

**A (row level, one decision per clip).** Code: `gen_stage2_1030.a_parts` / `a_text` and `section6_1106.a_gate`.

The gated A text contains:
- the Whisper transcript, if **any** target word of **any** speech event of the clip is heard in a segment with no_speech_prob < 0.5
  (`present` in `a_parts`);
- the FLAM line of each sounding event whose max score is < T_flam = 0.2705.

How the call is chosen:
- If the gated text is empty, the gate is closed and all A events keep their media-only labels.
- If it is non-empty, one A-axis call is made for the clip:
  - when the gated text equals the always-shown A text, the cached always-shown call is used (G4 / K4 / M4);
  - otherwise a call on the gated text is made (G5 / K5 / M5; `gen_stage2_1030.stage_rows5`, `final_cov_1108` M5).

### 4.1 Whisper in practice (verified on cached outputs; `audit/whisper_trace.py`)

**Answers to the specific questions:**
- **Does the initial PASS / FAIL label limit the transcript?** No. The A gate does not look at the initial label. Speech events with an
  initial PASS are opened as often as initial-FAIL ones.
- **Is the transcript condition per event?** No. It is per clip: the transcript is sent if any speech event's target word is heard.
- **Can Whisper and FLAM appear in the same A call?** Yes. The request carries the transcript and the FLAM lines of sounding events below
  T_flam together.
- **Can a call opened by another event revise a speech label?** Yes. The call covers every A event of the clip (the Stage-1 anchor), so:
  - a speech event whose own word was not heard can still be revised;
  - an opening caused only by a FLAM line (no transcript in the request) can also revise speech labels.
- **AVT-Judge vs Gate-only for speech:**
  - AVT-Judge takes the original-gate call label, which can move in either direction.
  - Gate-only only turns initial FAIL into PASS, and only when the event's own word is heard.
- **The combined-v2 configuration does not change speech.** A speech uses the original-gate label at every alpha. In `final_benchmark_1108`,
  `combined` = `original_gate` for all 2,248 scored A-speech units. `p12_calib_1108.open_rule` shows speech as "closed", but the label still
  comes from the original-gate call: `final_benchmark_1108.comb_labels`, the `A speech` branch.
- The rebuilt openings equal the stored ones on 2,248 / 2,248 units. The two word tokenizers (`gen_stage2_1030.norm` vs
  `sanjoy_controls.norm`) disagree on 0 units.

**Counts** (scored A-speech units; AVT-Judge = original-gate label):

| group | initial | units | opened | opened with transcript | opened by a FLAM line only | AVT-Judge revised (correct) | Gate-only revised (correct) |
|---|---|---|---|---|---|---|---|
| LTX | PASS | 1,726 | 1,449 | 1,445 | 4 | 13 (2) | 0 |
| LTX | FAIL | 43 | 27 | 26 | 1 | 15 (15) | 24 (24) |
| MOVA | PASS | 439 | 418 | 418 | 0 | 2 (0) | 0 |
| MOVA | FAIL | 40 | 20 | 20 | 0 | 1 (0) | 7 (5) |

- **Transcript and FLAM lines in the same opened request:** LTX 34 (initial PASS) + 3 (initial FAIL); MOVA 2 + 0.
- **Opened although the event's own word was not heard:** LTX 5 + 3; MOVA 7 + 13.

**Examples.** For each, the cached record's user-prompt md5 equals the md5 of the rebuilt request:
- `220 LTX hello-then-crossed_arms-then-yes__order` event_1 ("hello", GT PASS). Initial PASS; set G4. Transcript "below, yes." The judge
  revised to FAIL: "Whisper transcribed 'below' … instead of 'hello'". The call was opened by the word "yes" of another event.
- `220 LTX clap-then-okay-then-peace_sign__order` event_1 ("okay", GT PASS). Initial FAIL; set G5. Transcript "Okay?" The judge revised to
  PASS.
- `220 LTX hello-then-thumbs_up-then-thumbs_up_left-then-stop__order` event_4 ("stop", GT PASS). Initial PASS. Transcript
  "Hello? Stop. Stop." The judge revised to FAIL because the word appears twice.

Full list: `examples.csv` of the audit output.

**V (row level).** The gate opens when the caption check says "contradicts" for any GT event of the row. The call is made on the caption.

**AVB.** The pre-registered Synchformer rule: strongest binding-event reading with \|offset\| ≥ 1.8 s and p ≥ 0.25. The call is made on the
Synchformer text.

**TC / TR.** Closed.

## 5. Calibration (P01/P02 only)

**Population.** `final_benchmark_1108/calibration_v2/p12_calibration_units.csv`, the corrected HD-EPIC P01/P02 population. It includes 39
AVB judgments that the old free-text skip match had excluded. This is data and is not committed (see README).

**Procedure** (`p12_calib_1108.select_family` / `stage_select`), for each tool and initial-label branch:
- maximise admission of initially **incorrect** units;
- subject to admission of initially **correct** units ≤ alpha (empirical; rounded rate ≤ alpha, verified on exact integer counts);
- with a support requirement of at least 20 initially correct units;
- ties are broken by lower risk, then the conservative order.

Caption predicates are fixed and are activated only if they meet alpha. A branch without a useful feasible rule stays closed.

**Observed calibration admission of initially correct units** (k / n; rounded-vs-exact discrepancy: none):

| branch | alpha = .01 | alpha = .05 (main) | alpha = .10 |
|---|---|---|---|
| A FAIL-ev. | FLAM < .0207260568; 2 / 509 | < .3723524213; 24 / 509 | < .6685766578; 49 / 509 |
| A PASS-ev. | FLAM ≥ .9981793165; 2 / 207 | ≥ .9896813631; 9 / 207 | ≥ .9771832228; 16 / 207 |
| AVB FAIL-ev. | \|off\| ≥ 1.6, conf ≥ .2189; 2 / 234 | ≥ 1.2, ≥ .1278; 11 / 234 | ≥ 0.8, ≥ .1278; 23 / 234 |
| AVB PASS-ev. | off ≤ 0.0, conf ≥ .8888; 0 / 179 | ≤ 0.2, ≥ .3453; 8 / 179 | ≤ 0.4, ≥ .2247; 17 / 179 |
| V FAIL-ev. (contradicts) | closed (36 / 2,074 = .0174 > .01) | active; 36 / 2,074 | active |
| V PASS-ev. (describes) | closed (19 / 388 = .0490 > .01) | active; 19 / 388 | active |
| A speech (Whisper) | original-gate row-level rule (§4.1), not calibrated, same at every alpha | same | same |
| TC / TR | closed | closed | closed |

**Calibration target vs final false-alarm rate.**
- alpha bounds only the observed rate at which the gate admits evidence against initially correct judgments, measured on P01/P02.
- It is not a bound on the final judge's false-alarm rate (GT-PASS judged FAIL) on the test sets, and no formal test-set guarantee is
  claimed.
- Example final false-alarm rates of AVT-Judge at alpha = .05 (six-method common subset): P03-P09 AVB 9 / 139 = .065; LTX V 989 / 3,443 =
  .287; MOVA AVB 49 / 420 = .117.

## 6. Evaluation scope (unchanged established rules)

- **Datasets:** P03-P09 (HD-EPIC; perturbation GT); LTX (220 LTX 110 videos, 149 LTX, 2k_25 LTX); unified MOVA (old 220 MOVA 110 + MOVA390
  390). The 220 GT is rebuilt from the min-3 majority (v4 manifests), not from the obsolete GEPA splits.
- **Hierarchy** (see §7):
  - AVB needs the same event's A and V PASS, in GT and in the judge output.
  - TC needs **the same event's** prerequisites only: A, V and AVB for an audio event, V for a silent event.
  - TR needs **every event** of the video to pass A / V / AVB.
  - Revised labels are never propagated across axes.
  - TR is scored per video; the other axes per event.
- **Views:**
  - fixed six-method common subset (`final_benchmark_1108/subset_manifests.csv`, "six-method common");
  - per-method answered units;
  - fixed GT-eligible denominator with coverage.
- **Metrics:** FAIL is the positive class (`comprehensive_report_1108.metrics`).

## 7. TC / TR prerequisites: where each condition is applied (verified; `audit/tc_tr_prereq.py`)

| stage | TC (temporal count, per event) | TR (temporal relation, per video) | code |
|---|---|---|---|
| GT construction / aggregation | **none.** Per event, majority over raters of "rater's count = required count" (ties / < 2 labels: no GT). 220 from `min3_gt/gt_event.csv`; 149 from raw Prolific files; 2k_25 and MOVA390 from the `TCC` rows of `gt_*.jsonl` (`prolific2k25_adapter_1104.build`; same rule for MOVA390). P03-P09: count_override from the perturbation. | **none.** Video-level majority of `tcRel` (order / sync items only). P03-P09: order-swap perturbation. | `tc_per_event_1105.py`, `prolific2k25_adapter_1104.py`, `gen149_adapter_1030.py`, `audit_1106.units` |
| GT eligibility used in scoring | the **same event's** GT A, V and AVB are PASS (audio event) or V is PASS (silent event). HD-EPIC: always true by construction. | **every** event's GT A / V / AVB PASS (HD-EPIC: always true) | `audit_1106.gt_ok`, `gt_eligible` |
| MLLM Stage 1 (agentic harness; media-only and one-call runs) | the count call includes only events whose **own** A / V / AVB (or V for silent) are "yes". Other events get a harness entry "preconditions did not all pass" (count 0). | the relation call is made only if the clip's A, V and AVB axis labels are all "yes" (every event); otherwise a harness "Skipped" no. | `agentic_orchestrator._count_eligible`, `_synth_ineligible_count`, `relation_gate`, `_skipped_relation` |
| Stage 2 (always shown) | the anchor holds only the count entries Stage 1 actually judged (skip / gating reasons are dropped) | the anchor exists only if Stage 1 made the relation call | `run_two_stage.stage1_lookup` |
| final scoring | a TC event is scored if its **own** GT and media-only judge prerequisites pass and its count entry is a direct output. Failures of other events do not matter. | a TR video is scored only if **every** event passes the GT and judge prerequisites and the TR label is a direct output | `audit_1106.label_unit`, `judge_ok` |

**Observed in the reported runs.** These are media-only scored units whose item has another event failing A or V:

| dataset | scored TC events | … another event GT A/V FAIL | … another event judge A/V FAIL | scored TR videos with any failing event |
|---|---|---|---|---|
| 2k_25 LTX | 977 | 662 | 800 | 0 / 53 |
| MOVA390 | 254 | 140 | 157 | 0 / 34 |
| 220 LTX | 24 | 0 | 6 | 0 / 14 |
| 149 LTX / 220 MOVA | 16 / 2 | 0 / 0 | 0 / 0 | 0 / 4, 0 / 4 |
| P03-P09 | 2,592 | – (GT holds by construction) | 278 | 0 / 320 |

**Example** (`2k_25 LTX bird-with-fist_pose-with-slap_left__sync_count_x3`):
- event_3 (slap) has GT V FAIL and media-only V "no".
- event_1 (speech "bird") has media-only A and V "yes", and its count was judged and scored. Its TC GT is FAIL; media-only TC is FAIL.

**Summary.** TC uses the event's own prerequisites; TR uses all events. A description that says "TC requires all events to pass" does not
match the implementation.
