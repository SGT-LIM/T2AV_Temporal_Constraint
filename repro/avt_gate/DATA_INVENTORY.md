# Data inventory

There are two levels of reproduction:
- **A. Cached re-scoring.** Verified in a fresh clone (see `VALIDATION.md`). It recomputes the gate, the labels and the metrics from stored
  model outputs and tool features.
- **B. Full re-run from videos.** Not verified from this branch. It needs everything in A plus the videos, the tool models and a Gemini key.

All paths are relative to the two variables in `env.example`:
- `$T2AV_WORKSPACE` = experiment workspace;
- `$T2AV_DATA` = data root.

On BU SCC both are under `/projectnb/ivc-ml/youngsun/` (group `ivc-ml`).

## A. Files needed for cached re-scoring (main configuration)

The list below comes from a traced run (`rescore_cached.py --trace-files`, which writes `files_read.csv`):
- 33,974 files, 392 MB in total.
- The full grouped list is in `provenance/rescore_inputs_2026-11-10.txt`.
- The audits in `audit/` read a subset of the same files.

| group | location | files / MB | content |
|---|---|---|---|
| Stage-1 (media-only) outputs, generated | `$T2AV_WORKSPACE/eval_results/multi_agent/{gen_row1_anchor_g36_1030, gen2k25_row1_anchor_g36_1104, mova390_row1_anchor_g36_1108}/` | 42 / 102 | initial labels, eligibility |
| Stage-1 outputs, HD-EPIC P03-P09 | `$T2AV_DATA/real_av/eval/results/{hdepic_main_row1_anchor_g36_1101, hdepic_main_ma39_row1_A_g36_1101}/` | 27 / 145 | initial labels |
| Stage-2 call caches and benchmark tables | `$T2AV_WORKSPACE/evaluation/ablation/gepa_stage2/runs/obsval_1028/` (`calls/gen_tool_text/` 30,896 files; `final_benchmark_1108/`, `final_cov_1108/`, `p12_calib_1108/`, `avb_anchorfix_1108/`, `bidir_*`, `av_full_1107/`, `a_sound_ltx_exp_1107/`, `flam3_1108/`) | 31,905 / 99 | AVT-Judge outputs (matched by request md5), `unit_results_final.csv`, `subset_manifests.csv`, calibration_v2 |
| historical manifest | `$T2AV_WORKSPACE/evaluation/ablation/gepa_stage2/manifests_v3/all.jsonl` | 1 | P01/P02 rows, 220 TCR/TCC rows |
| captions (AVoCaDO) | `$T2AV_WORKSPACE/evaluation/ablation/captions/avocado_fps8_plain_v3_*.json`; `$T2AV_DATA/real_av/eval/hdepic_main_1101_captions/p3p9.json` | 6 / 9 | V payload |
| Whisper + FLAM records | `$T2AV_DATA/tools/gen_evidence_1030/{149,220,gen2k25,mova390,ma39}/`, `flam_threshold.json` | 1,901 / 2 | A features, Whisper transcript |
| Synchformer readings | `$T2AV_DATA/tools/synchformer_action_1030/{avbadd,b110,holdout,p12all}/`, `PREREGISTERED_RULE.json`; `$T2AV_DATA/tools/synchformer_gen_1030/` | 14 / 1 | AVB features |
| prompts and GT | `$T2AV_WORKSPACE/new_prompts/generated/relative_500_v5_fixed.json`; `$T2AV_DATA/gen_holdout_149_1030/`, `gen_prolific2k25_1104/`, `gen_prolific_mova390_1108_rev650fe5ae/`, `real_av_holdout_p3p9_1028/`; `$T2AV_DATA/gt_annotations/min3_gt/gt_event_majority.csv` | 7 / 25 | items, GT |
| stored comparison runs | `$T2AV_WORKSPACE/eval_results/analysis/sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv`; `.../sensitivity_2026-11-10/calls/` | 72 / 10 | Gate-only reference, sensitivity call records |

`link_workspace.sh` links `gepa_stage2/runs`, `manifests_v3`, `panels_1028`, `focus_1028`, `captions` and the 500-prompt file into the
checkout. The remaining paths are read through the two variables. Read access is enough: the re-scoring never writes into these paths.

Not needed for A: videos, model checkpoints, GPU, `GEMINI_API_KEY`.

## B. Additional inputs for a full re-run from videos (not verified from this branch)

| item | where it was taken from | used by | notes |
|---|---|---|---|
| generated videos (LTX-2.3, MOVA) | `$T2AV_DATA/videos_repo/main_videos/<MODEL>/`; records name the HF dataset `dghadiya/T2AV_TemporalConstraint` | Stage 1, tools | HF access controlled |
| raw human annotations | `$T2AV_DATA/gt_annotations/`, `$T2AV_WORKSPACE/generation/prolific_2k_25/`; records name HF `dghadiya/t2av_eval_annotations` | GT rebuild | GT files listed in A are enough for scoring |
| HD-EPIC clips and perturbations | `$T2AV_DATA/real_av_holdout_p3p9_1028/clips/`, `$T2AV_DATA/real_av/` | Stage 1, tools | HD-EPIC dataset terms apply |
| Gemini key | environment variable `GEMINI_API_KEY` only | Stage 1, one call, Stage 2 | model `gemini-3.6-flash`, thinking high |
| Whisper | faster-whisper 1.2.1, `large-v3-turbo` (downloaded to the HF hub cache) | `gen_evidence_1030.py audio` | GPU; env `t2av_eval` |
| OpenFLAM | checkpoint `v1-base` at `$T2AV_HF_CACHE/openflam` (1.3 GB) | `gen_evidence_1030.py audio` | GPU |
| Synchformer | external checkouts `$T2AV_EXT_TMP/Synchformer` and `$T2AV_EXT_TMP/t2av_multiagent` (synchformer-avb), checkpoint `24-01-04T16-39-21`, mode `window_if_alone_multi` | `sync_action_1030.py`, `sync_gen_1030.py` | GPU; separate env `t2av_eval_sync` (no freeze file in this branch) |
| AVoCaDO captioner | HF `AVoCaDO-Captioner/AVoCaDO`; script `evaluation/ablation/run_qwen3_captions.py` in the workspace (**not in this branch**) | caption JSONs in A | GPU; separate env `qwen3_cap` (no freeze file in this branch); fps 8 generated / fps 2 HD-EPIC, plain style, greedy |
| ffmpeg | 8.1 on `PATH` | tools | |

The commands and their order are in `README.md` §6. The stage modules write into `gepa_stage2/runs/` and `$T2AV_DATA/tools/`, so use a
writable copy, never the shared directories.

## Instructions for SCC colleagues (group `ivc-ml`)

```bash
git clone git@github.com:SGT-LIM/T2AV_Temporal_Constraint.git && cd T2AV_Temporal_Constraint
git checkout repro/avt-gate-v2-2026-11-10
module load miniconda
conda create -y -p <your_env_dir> python=3.11 && conda activate <your_env_dir>
pip install -r repro/avt_gate/requirements-rescore.txt
cp repro/avt_gate/env.example repro/avt_gate/env.local     # keep the shared T2AV_WORKSPACE / T2AV_DATA; set T2AV_OUT_DIR to your own new dir
source repro/avt_gate/env.local && mkdir -p "$T2AV_OUT_DIR"
./repro/avt_gate/link_workspace.sh
python repro/avt_gate/tests/test_gate_rules.py
python repro/avt_gate/rescore_cached.py --config repro/avt_gate/configs/main/frozen_p12_config.json --tag main_alpha05 --out "$T2AV_OUT_DIR"
```

**Expected result:** `checks.json` reports 25,628 / 25,628 for AVT-Judge, Gate-only and the Whisper mapping, 20,647 / 20,647 for the openings,
and one known missing request (`220 MOVA|slap-then-help-then-thumbs_up__order|V`). The run took 53 s on an SCC login node.

## External colleagues (not verified)

How people outside `ivc-ml` get the shared data is not recorded. Possible routes:
- SCC group membership;
- the access-controlled HF datasets named above;
- a copy of the A-level files (392 MB).

None of them has been tested. Ask the data owner. The HF datasets cover videos and annotations; it is not known whether they contain the
Stage-1 outputs, the Stage-2 call caches or the tool records needed for A.
