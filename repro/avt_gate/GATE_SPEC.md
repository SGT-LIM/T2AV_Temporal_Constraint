# Evidence gate used in the latest experiments (verified from code, frozen configs and run outputs)

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

The branch is chosen by the media-only (initial) label of each event × axis unit only:
- initial PASS → FAIL-evidence branch;
- initial FAIL → PASS-evidence branch.

`p12_calib_1108.open_rule`:

| axis / tool | initial PASS: opens if (FAIL evidence) | initial FAIL: opens if (PASS evidence) | Stage-2 payload (AVT-Judge) |
|---|---|---|---|
| A sounding / FLAM (first query of the event, whole-clip max score) | FLAM max **< 0.3723524212837219** | FLAM max **≥ 0.989681363105774** | FLAM lines of the opened sounding events only |
| A speech / Whisper | not calibrated (P01/P02 has no speech): the original-gate rule is inherited unchanged (§4, A) | same | as original gate |
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
- For A speech it uses the direct-original Whisper mapping: event's own target word heard → PASS; otherwise keep the initial label.

## 4. Original paper gate (baseline; `PREREGISTERED_RULE.json`, `flam_threshold.json`)

**A (row level).** The gated text contains:
- the Whisper transcript, only if a target speech word is heard in a segment with no_speech_prob < 0.5;
- FLAM lines only for sounding events whose max score is < T_flam = 0.2705.

If the gated text is empty, the gate is closed. If it equals the always-shown A text, the always-shown call is used; otherwise a call on the
gated text is made.

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
| A speech (Whisper) | original-gate rule, unchanged | unchanged | unchanged |
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
- **Hierarchy:** AVB needs A and V PASS (GT and judge); TC / TR need every event's A / V / AVB PASS. Revised labels are never propagated
  across axes. TR is scored per video; the other axes per event.
- **Views:**
  - fixed six-method common subset (`final_benchmark_1108/subset_manifests.csv`, "six-method common");
  - per-method answered units;
  - fixed GT-eligible denominator with coverage.
- **Metrics:** FAIL is the positive class (`comprehensive_report_1108.metrics`).
