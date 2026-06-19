# T2AV Gemini-Judge Evaluation: Analysis Report

Scope: human labels (`human/YS_eval_annotation_{ltx,mova}.xlsx`) as ground truth, restricted strictly
to the **20 relative-prompt ("_rel_") videos per model** (LTX-2.3, MOVA). Absolute-timing ("_abs_")
items are excluded from every table below. CC is never scored against human GT — **no human CC labels
exist** (the annotation guideline defines 5 scored axes only: A, V, AVB, TC-Relation, TC-Count; CC is
reported descriptively only, never as agreement/accuracy). All numbers were recomputed from the raw
per-event/per-item CSVs (code in `analysis/recompute/`), not taken from the prior rough analysis.

---

## 1. Executive Summary

- **Gemini-as-judge is moderate, not strong.** Pooled OVERALL accuracy across A/V/AVB/TC-Relation/TC-Count
  ranges ~0.62–0.80 depending on setting and model; balanced accuracy is consistently lower (~0.55–0.83),
  meaning Gemini is biased toward the majority "yes" class on several axes.
- **No single tool setting wins everywhere.** Best LTX setting by balanced accuracy: `Whisper_CLAP`
  (0.726). Best MOVA setting: `Whisper` alone (0.828, the best MOVA result overall, beating every
  combination). **CLAP is the worst or near-worst tool on almost every axis, in both models.**
  `MediaPipe_CLAP` is consistently the worst *combination*.
- **ICL (one worked example) helps overall for both models** (LTX bacc 0.719→0.745; MOVA bacc
  0.765→0.812), driven by gains on V, AVB, and TC-Count. **ICL reliably hurts the A (audio) axis**
  for both models (LTX bacc 0.782→0.580; MOVA 0.513→0.494).
- **MOVA's near-zero TC-Relation pass rate (0/20 by human GT) is a generation-quality finding, not
  an evaluator artifact.** 19 of 20 MOVA videos fail the left-hand slap visual constraint outright
  (per human annotation), which cascades into AVB and then TC-Relation failure. This is consistent
  with the task's caveat that MOVA's prompt set is harder (left-hand required on every slap) than
  LTX's (left-hand required only for the synchronized-action cases).
- **Gemini's hand-laterality judgment is unreliable in both directions**, independent of which model
  generated the video: it sometimes credits a video with the correct hand when the human reviewer
  marked it wrong (false "yes"), and sometimes claims the wrong hand was used when the human reviewer
  marked it correct (false "no"). Concrete examples in §5.
- **A genuine data-completeness gap**: `gemini/MOVA/AllTools_per_event.csv` is missing all per-event
  rows for item `Sp_Si_So_rel_ord_SiSpSo` (its per-item row exists in `AllTools.csv`, but no A/V/AVB/
  TC-Count breakdown). `gemini/LTX-2.3/NoTools*.csv` additionally contains 4 extra `_abs_` items not
  present in any other LTX setting or in the human GT — correctly excluded here, but worth fixing
  upstream so all settings cover an identical item set.

---

## 2. Metric Tables (Stage 2)

### 2.1 OVERALL (pooled A+V+AVB+TC-Relation+TC-Count, CC excluded), by model × setting

| Model | Setting | n | Accuracy | Balanced Acc. | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| LTX | Whisper_CLAP | 180 | 0.800 | **0.726** | 0.803 | 0.934 | 0.864 |
| LTX | NoTools | 180 | 0.767 | 0.719 | 0.812 | 0.852 | 0.832 |
| LTX | AllTools | 180 | 0.778 | 0.705 | 0.793 | 0.910 | 0.847 |
| LTX | Whisper | 180 | 0.767 | 0.701 | 0.794 | 0.885 | 0.837 |
| LTX | MediaPipe | 180 | 0.778 | 0.696 | 0.785 | 0.926 | 0.850 |
| LTX | MediaPipe_Whisper | 180 | 0.778 | 0.687 | 0.777 | 0.943 | 0.852 |
| LTX | CLAP | 180 | 0.711 | 0.683 | 0.802 | 0.762 | 0.782 |
| LTX | MediaPipe_CLAP | 180 | 0.622 | 0.545 | 0.705 | 0.762 | 0.732 |
| MOVA | Whisper | 180 | **0.833** | **0.828** | 0.781 | 0.803 | 0.792 |
| MOVA | MediaPipe_Whisper | 180 | 0.772 | 0.790 | 0.660 | 0.873 | 0.752 |
| MOVA | AllTools | 170\* | 0.765 | 0.784 | 0.655 | 0.846 | 0.738 |
| MOVA | Whisper_CLAP | 180 | 0.739 | 0.772 | 0.611 | 0.930 | 0.737 |
| MOVA | NoTools | 180 | 0.739 | 0.765 | 0.618 | 0.887 | 0.728 |
| MOVA | MediaPipe | 180 | 0.711 | 0.722 | 0.604 | 0.775 | 0.679 |
| MOVA | MediaPipe_CLAP | 180 | 0.678 | 0.692 | 0.568 | 0.761 | 0.651 |
| MOVA | CLAP | 180 | 0.667 | 0.663 | 0.568 | 0.648 | 0.605 |

\*170/180 — 10 rows unscoreable because `AllTools_per_event.csv` is missing item `Sp_Si_So_rel_ord_SiSpSo` (see §1).

**Reading caution**: "OVERALL" pools 5 axes of very different base rates and difficulty; a setting can
win OVERALL while losing on the axis that matters most (see §2.2 — `Whisper_CLAP` wins LTX OVERALL but
has *worse* A-axis balanced accuracy than `NoTools`).

### 2.2 Per-axis accuracy / balanced accuracy, NoTools, both models

| Model | Axis | n | Acc | BAcc | Precision | Recall | F1 | TP | FP | TN | FN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LTX | A | 32 | 0.875 | 0.782 | 0.963 | 0.897 | 0.929 | 26 | 1 | 2 | 3 |
| LTX | V | 48 | 0.792 | 0.705 | 0.865 | 0.865 | 0.865 | 32 | 5 | 6 | 5 |
| LTX | AVB | 32 | 0.719 | 0.614 | 0.833 | 0.800 | 0.816 | 20 | 4 | 3 | 5 |
| LTX | TC-Relation | 20 | 0.850 | 0.900 | 0.625 | 1.000 | 0.769 | 5 | 3 | 12 | 0 |
| LTX | TC-Count | 48 | 0.667 | 0.654 | 0.656 | 0.808 | 0.724 | 21 | 11 | 11 | 5 |
| MOVA | A | 32 | 0.625 | 0.513 | 0.818 | 0.692 | 0.750 | 18 | 4 | 2 | 8 |
| MOVA | V | 48 | 0.750 | 0.778 | 0.636 | 1.000 | 0.778 | 21 | 12 | 15 | 0 |
| MOVA | AVB | 32 | 0.781 | 0.854 | 0.533 | 1.000 | 0.696 | 8 | 7 | 17 | 0 |
| MOVA | TC-Relation | 20 | 0.800 | n/a\* | n/a | n/a | n/a | 0 | 4 | 16 | 0 |
| MOVA | TC-Count | 48 | 0.750 | 0.812 | 0.571 | 1.000 | 0.727 | 16 | 12 | 20 | 0 |

\*MOVA TC-Relation has **zero positive cases in human GT** (all 20 videos fail TC-Relation) — balanced
accuracy/precision/recall/F1 are undefined for a single-class GT; only accuracy is meaningful here.

Full per-axis × per-setting tables for both models are in `analysis/recompute/stage2_metrics_full.csv`.

### 2.3 Sanity check against the prior rough analysis

I cross-checked the A/V/AVB/TC-Relation numbers above against `analysis/ltx-2.3/metrics_long.csv`
(the existing rough analysis): NoTools accuracy for A (0.875), V (0.7917), AVB (0.7188), and
TC-Relation (0.850) match exactly. The prior analysis is **correct** as far as it goes — it just
doesn't compute precision/recall/F1, doesn't fold TC-Count into an OVERALL score, and (correctly,
given the brief) never attempted CC. No errors found in its core join logic.

---

## 3. ICL Analysis (Stage 3)

`NoTools` (zero-shot) vs. `ICL NoTools` (one worked example prepended), per model, per axis:

| Model | ICL | Axis | Acc | BAcc | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| LTX | no | A | 0.875 | **0.782** | 0.963 | 0.897 | 0.929 |
| LTX | yes | A | 0.781 | **0.580** | 0.923 | 0.828 | 0.873 |
| LTX | no | V | 0.792 | 0.705 | 0.865 | 0.865 | 0.865 |
| LTX | yes | V | 0.812 | **0.719** | 0.868 | 0.892 | 0.880 |
| LTX | no | AVB | 0.719 | 0.614 | 0.833 | 0.800 | 0.816 |
| LTX | yes | AVB | 0.719 | 0.614 | 0.833 | 0.800 | 0.816 |
| LTX | no | TC-Count | 0.667 | 0.654 | 0.656 | 0.808 | 0.724 |
| LTX | yes | TC-Count | 0.771 | **0.760** | 0.742 | 0.885 | 0.807 |
| MOVA | no | A | 0.625 | 0.513 | 0.818 | 0.692 | 0.750 |
| MOVA | yes | A | 0.594 | **0.494** | 0.810 | 0.654 | 0.723 |
| MOVA | no | V | 0.750 | 0.778 | 0.636 | 1.000 | 0.778 |
| MOVA | yes | V | 0.812 | **0.828** | 0.714 | 0.952 | 0.816 |
| MOVA | no | AVB | 0.781 | 0.854 | 0.533 | 1.000 | 0.696 |
| MOVA | yes | AVB | 0.844 | **0.854** | 0.636 | 0.875 | 0.737 |
| MOVA | no | TC-Count | 0.750 | 0.812 | 0.571 | 1.000 | 0.727 |
| MOVA | yes | TC-Count | 0.896 | **0.922** | 0.762 | 1.000 | 0.865 |
| LTX | no | OVERALL | 0.767 | 0.719 | 0.812 | 0.852 | 0.832 |
| LTX | yes | OVERALL | 0.783 | **0.745** | 0.832 | 0.852 | 0.842 |
| MOVA | no | OVERALL | 0.739 | 0.765 | 0.618 | 0.887 | 0.728 |
| MOVA | yes | OVERALL | 0.806 | **0.812** | 0.714 | 0.845 | 0.774 |

Item/event "flip" counts (zero-shot→ICL):

| Model | Fixed by ICL | Broken by ICL | Net |
|---|---|---|---|
| LTX | 21 | 18 | +3 |
| MOVA | 28 | 16 | +12 |

By axis, fixes cluster in **TC-Count** (LTX +5 net, MOVA +7 net) and **V/AVB**; breaks cluster
disproportionately in **A** (LTX 6 broken vs 3 fixed; MOVA 6 broken vs 5 fixed).

**Does ICL help?** Yes, net positive for both models, more so for MOVA (+12 net fixes, OVERALL bacc
+0.047) than LTX (+3 net, OVERALL bacc +0.026).
**Which axes improve?** V, AVB, and especially TC-Count improve consistently and substantially
(MOVA TC-Count bacc 0.812→0.922; LTX 0.654→0.760).
**Which axes remain hard / get worse?** A (audio correctness) degrades with ICL in both models. The
single worked example evidently anchors the model's behavior toward the visual/temporal reasoning
style of the example at a small cost to audio-specific calibration — plausibly because the one example
spends most of its worked reasoning on visual/temporal cues, so the model imitates that emphasis.
TC-Relation is roughly flat to slightly worse for LTX (bacc 0.900→0.833) and remains a degenerate
all-"no" axis for MOVA either way.

---

## 4. Tool Effectiveness (Stage 4)

### 4.1 Which tool helps Audio (A) most?

- **MOVA**: `Whisper` is unambiguously best — bacc 0.513→0.763, precision/specificity jump (specificity
  0.333→0.833). `MediaPipe_Whisper` is even better (bacc 0.885) but that combination's gain is carried
  entirely by Whisper (MediaPipe contributes nothing to audio by design).
- **LTX**: counter-intuitively, **every tool setting makes A balanced accuracy worse than NoTools**
  (NoTools 0.782 vs. Whisper 0.649, MediaPipe 0.649, CLAP 0.546, MediaPipe_Whisper 0.448, …). LTX's
  audio generation is already strong (29/32 GT-positive), so NoTools sits near a ceiling; adding any
  tool shifts Gemini toward over-trusting "yes" and collapses specificity (NoTools 0.667 → 0.000–0.333
  under tools). **Whisper helps where audio is genuinely weak (MOVA) and hurts where it's already
  strong (LTX)** — a ceiling/overtrust effect, not a tool-quality difference per se.

### 4.2 Which tool helps Visual (V) most?

No tool cleanly wins on **balanced** accuracy. For LTX, `CLAP` (0.665) and `Whisper_CLAP`/`MediaPipe`
(0.655) edge out NoTools (0.705)... actually NoTools is the *best* LTX V-bacc; every tool setting is
flat-to-worse. For MOVA, `NoTools` (0.778) and `Whisper_CLAP` (0.741) beat `MediaPipe` (0.730) on
balanced accuracy. **MediaPipe — the tool explicitly designed to give Gemini hand/pose landmarks —
does *not* improve V balanced accuracy for either model**, and in MOVA it doesn't reduce the
hand-laterality false-positive rate at all (FP stays at 12/27 negatives for both NoTools and MediaPipe).
This means raw pose landmarks alone aren't resolving the left/right ambiguity Gemini struggles with —
consistent with the tool's own documented caveat ("laterality may be unreliable when hands cross or
anatomy is distorted").

### 4.3 Which tool hurts performance?

**CLAP**, clearly and consistently. It is the single worst tool on nearly every axis for both models:

| Model | Axis | NoTools BAcc | CLAP BAcc |
|---|---|---|---|
| LTX | A | 0.782 | 0.546 |
| LTX | AVB | 0.614 | 0.646 (only axis CLAP helps) |
| LTX | TC-Relation | 0.900 | 0.767 |
| MOVA | A | 0.513 | 0.538 |
| MOVA | V | 0.778 | 0.653 |
| MOVA | AVB | 0.854 | 0.583 |
| MOVA | TC-Count | 0.812 | 0.734 |

`MediaPipe_CLAP` is the worst *combination* in nearly every row of the per-axis tables for both
models (e.g. LTX AVB bacc 0.411, lowest of all 16 model×setting cells for that axis). Pairing two
comparatively weak/noisy tools compounds rather than cancels their errors.

### 4.4 Are tool combinations better than single tools?

**Not uniformly.** For MOVA, the single best setting overall is `Whisper` alone (bacc 0.828) —
*every* combination that dilutes Whisper with another tool (CLAP, MediaPipe) is worse
(`MediaPipe_Whisper` 0.790, `Whisper_CLAP` 0.772, `AllTools` 0.784). For LTX, the best setting is a
combination (`Whisper_CLAP`, 0.726), but its A-axis performance is *worse* than NoTools alone, so the
"win" is concentrated in V/TC-Count, not a uniform improvement. **The data does not support a general
"more tools = better" claim**; it supports "the single strongest relevant tool (Whisper, when audio
quality is the bottleneck) helps, and adding a weak/noisy tool (CLAP) on top tends to drag it back
down."

### 4.5 Why?

Mechanistically: Whisper gives precise, low-noise word-level timestamps for speech — exactly what's
needed for A and TC-Count on speech events, and it never gets invoked for non-speech axes (so it can't
introduce noise there). CLAP's evidence is a noisy cosine-similarity signal with no reliable absolute
threshold (the system prompt itself warns "absolute thresholds are unreliable"); on short, acoustically
ambiguous events like a single slap, this regularly produces false confidence in either direction.
MediaPipe gives raw coordinates with no semantic or laterality interpretation — useful in principle,
but evidently not sufficient on its own to resolve the hand-side judgments that dominate the V/AVB
failure modes in this benchmark.

---

## 5. Error Analysis (Stage 5)

### 5.1 Hand-laterality errors — both directions, both models

Per the task's caveat, MOVA requires left-hand slaps universally while LTX requires left-hand slaps
only for the simultaneous (silent+sounding) cases. I confirmed empirically that **MOVA's generation
itself violates this constraint in 19/20 videos** (human V or AVB = "no" on the slap event), explaining
MOVA's near-zero TC-Relation pass rate independent of any evaluator issue.

Separately, I checked whether **Gemini's own judgment** is unreliable on laterality, in both directions:

- **False "yes" (Gemini over-credits)** — e.g. LTX `Si_So_rel_ord_SiSo` event_2 (required: right hand
  → right thigh): human V/AVB = no, Gemini V/AVB = yes, reason: *"The right hand strikes the right
  thigh."* Gemini's own stated observation matches the textual requirement but contradicts the human
  reviewer who watched the clip — i.e. Gemini's description is likely a hallucinated/unverified visual
  read, not a legitimate ambiguity. Same pattern recurs in MOVA (`Si_So_rel_ord_SiSo`, `Si_So_rel_sync`,
  `Sp_Si_So_rel_ord_SoSpSi`, `Sp_Si_So_rel_ord_SpSiSo` — all "left hand strikes the left thigh" claims
  the human reviewer disputed).
- **False "no" (Gemini over-penalizes)** — e.g. LTX `Sp_So_rel_ord_SoSp` event_2 (required: right hand
  → right thigh): human V/AVB = **yes** (correct hand), Gemini V/AVB = **no**, reason: *"The visible
  action is performed with the wrong hand."* This is the exact scenario flagged in the task brief —
  Gemini incorrectly penalizing a video for a left/right mismatch the ground truth says is actually
  correct. This is **not unique to LTX's conditional rule**; it is a general laterality-judgment
  weakness that shows up in both models' outputs.
- Across all settings pooled, **AVB false positives** (Gemini says "yes" where GT says "no") concentrate
  heavily on the slap event of a small set of repeat-offender items — `Si_So_rel_ord_SiSo`/event_2 and
  `Sp_So_rel_sync_cnt`/event_2 for LTX (8/8 settings each); `Sp_So_rel_ord_SoSp`/event_1 for MOVA
  (7/8 settings). These are videos where Gemini *consistently* and *across every tool configuration*
  fails to detect the same laterality or sync defect — a stable blind spot, not settings-dependent noise.

### 5.2 TC-Count failures

Of 48 NoTools events per model, 15/48 have an observed≠required mismatch in both LTX and MOVA. Breakdown
by event kind (NoTools): LTX — speech 6, sounding_action 5, silent_action 4; MOVA — sounding_action 8,
speech 4, silent_action 3. **MOVA's count errors concentrate on sounding actions** (the slap, again —
consistent with §5.1's generation-quality story: many of these "0 observed vs 1 required" rows are the
same slap events failing on V/AVB, where TC-Count is correctly gated to "no" via the precondition rather
than independently miscounted). LTX's count errors are more evenly spread, with speech slightly
dominant (extra "help" repetitions or missed second utterances in `_sync_cnt`/`_rel_sync_cnt` items).

### 5.3 Tool-specific hallucination: CLAP triggers phantom "Whisper" reasoning

This is the most surprising finding in the tool comparison. In the **CLAP-only** setting (no Whisper
in the system prompt or user message at all — confirmed in `eval_5axis_per_event.py`'s
`build_system_prompt`, which only injects `WHISPER_GUIDE` when `audio_evidence_mode` includes
"whisper"), several newly-introduced speech (A-axis) false negatives cite the *absence of Whisper
evidence* as justification:

- LTX `Sp_Si_So_rel_ord_SoSpSi`/event_1: *"There is no Whisper ASR evidence or clear audio indicating
  that the word 'help' is spoken."*
- MOVA `Sp_Si_So_rel_ord_SiSoSp`/event_1: *"No speech is audible and no Whisper transcription evidence
  is present to confirm the word 'help'."*

Gemini is treating the **absence of a tool that was never offered** as negative evidence, in a setting
where it was only given CLAP (a non-speech tool) and direct audio. This reads as a residual prior from
general training/expectations about how these evaluations are usually run, not a grounded inference from
the actual inputs — a concrete instance of tool-context hallucination. It also explains part of why CLAP
hurts the A axis: it doesn't just fail to help with speech (it isn't supposed to), it appears to make
the model *more* conservative about speech specifically because Whisper's absence becomes salient.

### 5.4 "Extra action" vs CC — descriptive only (no GT available)

Since there is no human CC ground truth, this is purely descriptive: Gemini does separate genuine extra
actions from core-axis failures, e.g. LTX `Sp_Si_So_rel_ord_SiSoSp` (NoTools): `overall_temporal_success
= yes` but `constraint_compliance = no`, reason *"The video includes an unprompted, extra hand gesture
that violates the constraint against extra actions."* This is the right place for such a finding under
the rubric (not folded into TC-Count or V), but **we cannot verify correctness** of any individual CC
call against ground truth — only note that Gemini's CC reasoning engine appears to behave as designed
in spot checks, without claim to systematic accuracy.

### 5.5 Data completeness issues found (recap)

- `gemini/LTX-2.3/NoTools[_per_event].csv`: 4 extra `_abs_` items (24 vs 20) not present in any other
  LTX setting, the LTX-ICL setting, or human GT — excluded from all analysis above.
- `gemini/MOVA/AllTools_per_event.csv`: missing all per-event rows for `Sp_Si_So_rel_ord_SiSpSo` (the
  per-item row exists in `AllTools.csv`). This silently drops 10 of 180 rows from MOVA/AllTools'
  per-axis denominators (n=170 instead of 180 in §2.1); flagged, not imputed.

---

## 6. Recommendations for Next Experiments

1. **Re-run `gemini/MOVA/AllTools` per-event scoring for `Sp_Si_So_rel_ord_SiSpSo`** and re-generate the
   LTX `NoTools` run to drop the 4 stray `_abs_` items, so every setting covers an identical 20-item set
   end-to-end (currently true for 7/8 LTX settings and 8/8 MOVA settings, but not LTX NoTools).
2. **Treat Whisper as the default audio tool, and test CLAP removal entirely** — across both models and
   every axis it touches, CLAP underperforms NoTools or ties at best, and actively degrades speech
   judgment via the phantom-Whisper hallucination in §5.3. A no-CLAP ablation (`Whisper` alone vs.
   `MediaPipe_Whisper`) would isolate whether MediaPipe is worth keeping at all once CLAP is removed.
3. **Investigate why ICL hurts the A axis** specifically — try an ICL example that foregrounds an audio
   failure case (the current one example is necessarily dominated by whichever axis it best illustrates)
   to see whether the audio regression is about example content rather than ICL itself.
4. **Add a dedicated laterality-verification step** (e.g., a short, explicit "which hand performed the
   contact, and is that the hand named in the prompt?" sub-question, possibly model-verified twice) given
   that laterality errors in both directions are the single most concretely-reproducible failure mode
   found here, and current MediaPipe landmark evidence does not resolve it.
5. **Collect human CC labels** for at least a subset of videos if CC accuracy is something the project
   wants to report eventually — right now it is structurally unscoreable.
6. **Report MOVA TC-Relation results with the caveat that GT is single-class (0/20 pass)** rather than a
   bare accuracy number — balanced accuracy/F1 are mathematically undefined, and a naive "always predict
   no" baseline would score a deceptively strong 1.000 there.
7. When characterizing MOVA-vs-LTX "model quality," separate the **generation-quality** finding (MOVA
   violates the left-hand constraint in 19/20 videos — a property of the video generator, found via
   human GT) from the **evaluator-quality** finding (Gemini's laterality judgment is noisy in both
   directions, in both models) — these are independent issues and were conflated in earlier informal
   discussion.

---

*Recomputation code: `analysis/recompute/{common.py, stage2_metrics.py, stage3_icl.py, stage5_errors.py,
stage5b_tool_errors.py}`. Full per-axis × per-setting metrics: `analysis/recompute/stage2_metrics_full.csv`.*
