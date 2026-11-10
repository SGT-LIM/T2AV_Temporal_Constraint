# Reproducing the AVT-Judge evidence gate (combined gate v2) and the alpha sensitivity study

This directory makes the evidence gate of the latest T2AV experiments reproducible from a fresh clone.

**Status before this branch.** The code that produced the experiments (`evaluation/ablation/` on the lab workspace) was **not on GitHub**:
- not on `main`;
- not on `refactor/pipeline-v4`, whose `legacy/` copy is an 11/06 snapshot. It lacks the combined gate, calibration_v2, the AVB scorer /
  anchor fixes and the 2k_25 / MOVA390 / restored-220 scope, and its overlapping files differ.

**This branch adds:**
- portable copies of exactly the experiment code (`evaluation/ablation/**`, `repro/avt_gate/analysis/*`). They were produced by
  `tools/make_portable.py`, which replaces only the absolute lab paths with `T2AV_*` environment variables. Every edit is logged in
  `provenance/portable_substitutions.csv`; the originals' sha256 / md5 are in `provenance/ORIGINAL_CODE_SHA256.txt`.
- the frozen gate configurations (`configs/`);
- the gate specification (`GATE_SPEC.md`);
- a cached re-scoring entry point (`rescore_cached.py`);
- offline tests (`tests/`).

| path | content |
|---|---|
| `GATE_SPEC.md` | the gate rules and thresholds actually used, the bidirectional branches, missing-evidence and closed-gate behaviour, calibration, main vs sensitivity |
| `configs/main/` | **main** configuration used by the paper benchmark (`final_benchmark_1108`): `frozen_p12_config.json` = calibration_v2, alpha = .05 |
| `configs/sensitivity/a01, a05, a10/` | sensitivity configurations (alpha = .01 / .05 reference / .10), with constraint-compliance checks |
| `configs/original_gate/` | original paper gate: `PREREGISTERED_RULE.json` (Synchformer), `flam_threshold.json` (T_flam) |
| `configs/historical/` | v1 configuration, before the calibration-population correction (not used by current results) |
| `configs/controls/` | no-tool control template and frozen settings (Sanjoy controls) |
| `rescore_cached.py` | recompute gate openings, AVT-Judge and Gate-only labels, and the three evaluation views from cached outputs; compare with the stored run |
| `analysis/` | portable copies of the scripts that produced the controls, the paper-table handoff and the alpha sensitivity study |
| `tools/make_portable.py`, `tools/portable_map.tsv` | how the portable copies were generated |
| `audit/` | cached-output audits of the Whisper path and of the TC / TR prerequisite scope |
| `paper/replacement_sentences.tex` | candidate paper text for the Whisper rule, the TC / TR prerequisites and the evaluation protocol |
| `DATA_INVENTORY.md` | files needed for cached re-scoring vs a full re-run from videos |
| `requirements-rescore.txt`, `requirements-full-freeze.txt` | minimal deps for cached re-scoring; full freeze of the experiment env (`t2av_eval`, Python 3.11.16) |

## 1. Install

```bash
git clone git@github.com:SGT-LIM/T2AV_Temporal_Constraint.git
cd T2AV_Temporal_Constraint
git checkout repro/avt-gate-v2-2026-11-10
conda create -y -n t2av_repro python=3.11 && conda activate t2av_repro
pip install -r repro/avt_gate/requirements-rescore.txt   # cached re-scoring only
# full tool / model re-runs: pip install -r repro/avt_gate/requirements-full-freeze.txt  (CUDA 12.8 torch build; ffmpeg 8.1 on PATH)
```

## 2. Configure data locations (no personal paths in code; keys only via environment)

```bash
cp repro/avt_gate/env.example repro/avt_gate/env.local    # env.local is git-ignored; edit the paths
source repro/avt_gate/env.local
./repro/avt_gate/link_workspace.sh                         # links the data dirs the code addresses relative to itself
```

**Variables:**
- `T2AV_WORKSPACE` (experiment workspace) and `T2AV_DATA` (data root) are required.
- `T2AV_HF_CACHE` and `T2AV_EXT_TMP` are needed only for tool re-extraction.
- `T2AV_OUT_DIR` receives every new output.
- `GEMINI_API_KEY` must be exported in your shell only when model calls are re-run. Never write it into a file in the repo.

## 3. Verify the gate offline (no data, no API)

```bash
python repro/avt_gate/tests/test_gate_rules.py
```

The tests check:
- the main thresholds;
- boundary values (strict < for FLAM FAIL evidence; inclusive elsewhere);
- that each branch is chosen only by the initial PASS / FAIL label;
- missing evidence → closed;
- caption `not_mentioned` (omission) vs `contradicts`;
- `open_rule` returns closed for A speech (the speech label is then taken from the original-gate call; see `GATE_SPEC.md` §4.1) and for TC / TR;
- inactive branches at alpha = .01;
- Gate-only mapping and closed gate → initial label kept.

## Key behaviours in short (verified; details and code locations in `GATE_SPEC.md`)

- **Whisper (A speech)** is not calibrated and not branch-based.
  - The original A gate reopens the whole clip's A check when any requested speech word is heard or any sounding event has FLAM < T_flam.
  - One text call can revise every A event of the clip, for initial PASS and initial FAIL alike.
  - AVT-Judge uses that label for speech at every alpha.
  - Gate-only turns a speech event to PASS only when its own word is heard.
- **TC** is scored per event, using that event's own A / V / AVB prerequisites (V for a silent event).
- **TR** is scored per video and needs every event to pass.
- GT is aggregated without prerequisites; they are applied in the Stage-1 harness and at scoring.

Re-run the two audits (cached outputs only):
```bash
python repro/avt_gate/audit/whisper_trace.py --tag whisper_trace     # -> $T2AV_OUT_DIR/whisper_trace/
python repro/avt_gate/audit/tc_tr_prereq.py  --tag tc_tr_prereq      # -> $T2AV_OUT_DIR/tc_tr_prereq/
```

## 4. Re-run the gate and the evaluation from cached outputs (no API / GPU; verified, also from a fresh clone and env, see `VALIDATION.md`)

```bash
# main configuration (paper): calibration_v2, alpha = .05
python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/main/frozen_p12_config.json --tag main_alpha05 --out "$T2AV_OUT_DIR"
# sensitivity (separate tags; outputs never overwrite each other or the historical runs)
S=$T2AV_WORKSPACE/eval_results/analysis/sensitivity_2026-11-10/results/unit_labels_openings.csv
python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/sensitivity/a01/frozen_config.json --tag sens_alpha01 --out "$T2AV_OUT_DIR" --stored-labels "$S" --stored-tag a01
python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/sensitivity/a10/frozen_config.json --tag sens_alpha10 --out "$T2AV_OUT_DIR" --stored-labels "$S" --stored-tag a10
```

**Each `--tag` directory contains:**
- `unit_labels.csv` (per unit: GT, initial label, features, opening, branch, AVT-Judge label and request md5, Gate-only label);
- `metrics_three_views.csv`: fixed six-method common subset / per-method answered / fixed GT-eligible denominator, for MLLM-only,
  AVT-Judge and Gate-only, with full PASS / FAIL metrics, confusion counts and coverage;
- `checks.json` (agreement with the stored run);
- `run_manifest.json` (git commit and dirty flag, exact command, config sha256 and branch thresholds, Stage-2 model settings, md5 of every
  input table, number of cached call records, environment variables set or unset, wall time).

**Contract:**
- An existing tag is refused.
- Opened units without a cached output are reported as missing; they are never filled.
- No model is called.

**What is recomputed vs read from cache:**
- **Recomputed:** gate openings, Gate-only labels, the Whisper direct mapping, the AVT-Judge label lookup (exact prompt md5 of the
  rebuilt request), all subsets and metrics.
- **Read from cache:** Stage-1 (media-only) labels and eligibility, tool features (FLAM, Synchformer, caption-check verdicts) and Stage-2
  outputs, from `final_benchmark_1108/unit_results_final.csv`, the Stage-2 call caches and the sensitivity call records.

## 5. Re-running the original analysis scripts (portable copies)

`analysis/sanjoy_controls.py`, `analysis/alpha_sensitivity.py` and `analysis/score_handoff.py` are the scripts that produced the
controls, the sensitivity study and the paper-table handoff. They write only below `$T2AV_OUT_DIR/<original dir name>`. To re-score from
cached calls, first copy the historical run directory there, for example:
```bash
cp -r "$T2AV_WORKSPACE/eval_results/analysis/sensitivity_2026-11-10" "$T2AV_OUT_DIR/"
python repro/avt_gate/analysis/alpha_sensitivity.py reproduce     # alpha .05 == calibration_v2 and stored labels
python repro/avt_gate/analysis/alpha_sensitivity.py score
```
The `run` stages make Gemini calls; use them only with your own key and a fresh copy.

## 6. Re-running from tool extraction and model calls (expensive; not re-verified from a fresh clone)

Order used by the experiments. Commands are the recorded ones; the stage modules write into `evaluation/ablation/gepa_stage2/runs/` and
`$T2AV_DATA/tools/`, so run them on a **writable copy** of the workspace, never on the shared one.

1. **Stage 1, media-only** (one call per item, all axes; flags `T2AV_EVENT_TIME_FIELD=1 T2AV_DELETE_UPLOADS=1`):
   ```bash
   cd evaluation/ablation
   python -u run_agentic_eval.py --prompt-json <prompts.json> --outputs-dir <videos> --output-csv <row1_dir>/shard<k>.csv --axes all \
          --model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none \
          --start-index <a> --end-index <b>
   ```
2. **Tools.** Whisper large-v3-turbo + OpenFLAM v1-base records: `gepa_stage2/gen_evidence_1030.py audio --set <set>` (GPU). AVoCaDO
   captions: fps 8 for generated, fps 2 for HD-EPIC, plain style, greedy. Synchformer action-window readings: `gepa_stage2/sync_gen_1030.py`
   / `sync_action_1030.py`; these need the external Synchformer checkout under `$T2AV_EXT_TMP`. For MOVA390 the same steps are wrapped in
   `gepa_stage2/mova390_pipeline_1108.py links | audio | cache | captions | sync | synctexts`.
3. **One call plus tools (baseline):** the same command as step 1 with `--audio-evidence-mode whisper_flam --caption-evidence-mode external
   --caption-style plain --caption-external-json <captions.json>`, and `T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1
   T2AV_SYNC_EVIDENCE_JSON=<sync_sections.json>`.
4. **Benchmark scope, gate calibration, Stage-2 calls and scoring:**
   `gepa_stage2/final_benchmark_1108.py manifests | calib | plan | run | score`.
   - `calib` reruns the P01/P02 selection.
   - `plan` lists every missing Stage-2 request and reuses exact-md5 cached outputs.
   - `run` needs `GEMINI_API_KEY`.
   - `score` rebuilds eligibility, hierarchy and the subsets.
5. **Controls and sensitivity:** `analysis/sanjoy_controls.py verify | freeze | plan | run | score` and
   `analysis/alpha_sensitivity.py calib | reproduce | plan | run | score`.

## 7. External data (not in git)

**Lab location.** The data live on BU SCC: `/projectnb/ivc-ml/youngsun/` (group `ivc-ml`). The **access method for people outside that group
is not documented in the records; ask the data owner.** The references below are the ones recorded in the workspace.

| what | location (relative to the variable) | used for |
|---|---|---|
| Stage-1 / one-call run outputs | `$T2AV_WORKSPACE/eval_results/multi_agent/`, `$T2AV_DATA/real_av/eval/results/` | initial labels, eligibility |
| Stage-2 caches, benchmark outputs, calibration_v2 | `$T2AV_WORKSPACE/evaluation/ablation/gepa_stage2/runs/obsval_1028/` (`calls/gen_tool_text`, `calls/vcap_check`, `final_benchmark_1108/`, `p12_calib_1108/`, `final_cov_1108/`, ...) | cached re-scoring |
| captions | `$T2AV_WORKSPACE/evaluation/ablation/captions/` | V payload, caption checks |
| prompts | `$T2AV_WORKSPACE/new_prompts/generated/relative_500_v5_fixed.json`; `$T2AV_DATA/gen_holdout_149_1030/`, `gen_prolific2k25_1104/`, `gen_prolific_mova390_1108_rev650fe5ae/` (prompts, GT, video links) | items, GT |
| GT | 220: `$T2AV_DATA/gt_annotations/min3_gt/gt_event_majority.csv`; 149 / 2k_25 / MOVA390: `gt_*.jsonl` in the dirs above; HD-EPIC P03-P09: perturbation GT under `$T2AV_DATA/real_av_holdout_p3p9_1028/` | evaluation |
| raw annotations | `$T2AV_DATA/gt_annotations/`, `$T2AV_WORKSPACE/generation/prolific_2k_25/` | GT provenance |
| videos | generated: `$T2AV_DATA/videos_repo/main_videos/<MODEL>/` (records name the HF dataset `dghadiya/T2AV_TemporalConstraint`; access controlled); HD-EPIC clips: `$T2AV_DATA/real_av_holdout_p3p9_1028/clips/` and `$T2AV_DATA/real_av/` (HD-EPIC dataset terms apply) | Stage-1 / tool re-runs only |
| tool outputs | `$T2AV_DATA/tools/gen_evidence_1030/` (Whisper + FLAM), `tools/synchformer_action_1030/`, `tools/synchformer_gen_1030/` | gate features |
| results of the controls / sensitivity | `$T2AV_WORKSPACE/eval_results/analysis/{sanjoy_two_baselines_2026-11-08, sensitivity_2026-11-10, paper_tables_handoff_2026-11-09}/` | comparisons |

For the exact list of files the cached re-scoring reads, and what a full re-run additionally needs, see `DATA_INVENTORY.md`.

**Not committed:**
- the P01/P02 calibration population `final_benchmark_1108/calibration_v2/p12_calibration_units.csv` (843 KB);
- the enumerated admission sets (515 KB each).

Both are under `runs/` and are reached through `link_workspace.sh`.

## 8. Results-affecting settings (all recorded in `run_manifest.json` and `configs/`)

- **Stage-2 call:** `gemini-3.6-flash`, thinking `high`, temperature 0.0, seed 42, `response_mime_type=application/json` with
  `run_two_stage.SCHEMA[axis]`. Text only.
- **Prompt:** `obs_judge_1028.build_call`, with `OBS_RULES` md5 `556c2b2ef432344bbe8a53bfef15e0b1`.
- **Retries:** `obs_judge_1028.call` retries on 429 / 5xx (30 / 60 / 120 s). The runners allow at most 3 attempts per request.
- **Stage 1 and one call:** `gemini-3.6-flash`, thinking high, via `run_agentic_eval.py` (flags above).
- **Tools:** Whisper large-v3-turbo (faster-whisper 1.2.1, beam 5, VAD on); OpenFLAM v1-base (10 s windows, hop 5 s, detection threshold
  .98); Synchformer action-window mode; AVoCaDO greedy captions.
- **Gate:** see `GATE_SPEC.md` and `configs/`.
