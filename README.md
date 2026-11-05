# t2av_eval: T2AV evaluation, pipeline v4

Agentic evaluation of text-to-audio-video generation. A Gemini judge (gemini-3.6-flash, thinking high) labels each check item
on five axes: A (audio event), V (visual event), AVB (audio-visual binding), TCR (temporal relation), TCC (temporal count).
FAIL is the positive class. Two dataset families:

- **HD-EPIC** real kitchen videos with perturbation GT: P01/P02 (v3 test), P03–P09 (holdout), and the mute_anchor A sets.
- **Generated** videos with human majority labels: the 220 (LTX, MOVA) and the 149 (LTX).

Design: `docs/pipeline_v4_2026-10-27.md`. Main table: `docs/hdepic_main_table_2026-11-01.md` (both in the main checkout).
`legacy/` holds the scripts that produced the 10/28–11/02 results; every module here was moved from them and is checked
against them (see Tests).

## Install

```bash
module load miniconda
conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval
pip install -e .[dev]          # [tools] adds the GPU evidence dependencies (Whisper, FLAM, CLAP)
t2av-eval check                # keys (ids only), roots, every set's prompts / videos / captions, recipe artifacts
```

## Data and paths

`t2av_eval/config/paths.yaml` holds three roots; each can be overridden by an environment variable.

| root | variable | default | holds |
|---|---|---|---|
| DATA | `T2AV_DATA_ROOT` | `/projectnb/ivc-ml/youngsun/T2AV_data` | videos, prompt files, tool records (FLAM, Synchformer, captions) |
| INPUTS | `T2AV_INPUTS_ROOT` | `/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint` | read-only: v3 manifests, caption json, 220 prompts, earlier run CSVs |
| WORK | `T2AV_WORK_ROOT` | `<repo>/runs` | everything this package writes; refused inside INPUTS |

**Caches off SCC.** Video paths inside cache keys (Whisper / FLAM audio evidence, Synchformer sections, caption cache) are
written under the fixed root `cache_key_data_root` (`/projectnb/ivc-ml/youngsun/T2AV_data`). Copy T2AV_data with the same
layout, point `T2AV_DATA_ROOT` at the copy, and copy these caches as they are; every entry is hit:

- `T2AV_data/audio_evidence_cache/` (Whisper + FLAM sections),
- the Synchformer section json and per-event CSVs under `T2AV_data/tools/`,
- the caption json files (`T2AV_data/real_av/eval/hdepic_main_1101_captions/`, INPUTS `evaluation/ablation/captions/`),
- a stage-2 run's `calls/` (pass it with `--reuse-calls-from`).

The Gemini call cache, the stored prompts and the stage-1 lookup carry no paths (`tests/test_cache_keys.py`).

## Keys and API runs

- Keys come from the environment only: `GEMINI_API_KEY`, and `GEMINI_API_KEY_2`, `_3`, ... for rotation. Each shard gets one key
  as `GEMINI_API_KEY` and no other key variable. READMEs and logs show a key as `name:sha256-prefix`; the key itself is never written.
- Start API runs on a login node inside `screen` (the launcher stays in the foreground and prints progress every minute).
  GPU work (evidence, screening) runs in a qrsh GPU session.
- **Pacing:** per key, at most `calls_per_hour_per_key` (2,000) `generate_content` attempts per rolling hour, shared by every
  shard of the run (`config/runs.yaml`, `--calls-per-hour`).
- **Stop rule:** a call that fails after all its retries with 429 / RESOURCE_EXHAUSTED writes `STOP` in the run dir and every
  shard exits at its next call. A 429 inside a retry is not a stop; other failures stay error rows. Rerun the rest into a new
  dir with `--items-from <stopped run>` (items with an error row or no row).
- **Uploads:** each uploaded clip is deleted after every call of its item succeeded (`T2AV_DELETE_UPLOADS=1`). Before a launch
  that uploads, free Gemini Files storage per key (20 GB cap) must cover the clips of that key's shards plus 0.3 GB; otherwise
  nothing is launched.

## One command per table row

Every run goes to a new dir `WORK/results/<name>_<YYYYMMDD>/` with a README (see Run dirs). `--dry-run` prints the plan.

**HD-EPIC (P01/P02 and P03–P09).**

| row | command |
|---|---|
| 1 media-only | `t2av-eval judge media_only --sets hdepic_p12,hdfoot_p12,hdmove_p12,p3p9 --name hdepic_main_row1` |
| 2 all tools in one call | `t2av-eval judge all_tools --sets hdepic_p12,hdfoot_p12,hdmove_p12,p3p9 --name hdepic_main_row2` |
| 3 routing | `t2av-eval judge routing --sets hdepic_p12,hdfoot_p12,hdmove_p12,p3p9 --name hdepic_main_row3` (not run on HD-EPIC before) |
| 4, 5, framing | `t2av-eval judge two_stage_ungated,gated,framing --stage1 <row 1 dir> --sets hdepic_p12,hdfoot_p12,p3p9 --name hdepic_main_stage2` |

Row 5 is reported as the gated judge (`row5`) and the code rule (`row5_rule`, AVB). TCR / TCC have no stage 2 (decided 10/30).
Stage 2 needs the tool records: FLAM records (`t2av-eval evidence records -- audio --set hdA`), the AVoCaDO captions, and the
Synchformer action-window readings (`t2av-eval evidence synchformer-action -- --set ...`).

**HD-EPIC mute_anchor A sets** (the paper's A numbers; P01/P02 78 anchors, P03–P09 40):

| row | command |
|---|---|
| 1 | `t2av-eval judge media_only --sets ma_p12,ma_p3p9 --name hdepic_ma_row1` |
| 4, 5 | `t2av-eval judge two_stage_ungated,gated --stage1 <row 1 dir> --sets ma_p12,ma_p3p9 --name hdepic_ma_stage2` |

**Generated (220-LTX, 220-MOVA, 149-LTX).**

| row | command |
|---|---|
| 1 | `t2av-eval judge media_only --sets ltx220,mova220,gen149 --name gen_row1` |
| 2 | `t2av-eval judge all_tools --sets ltx220,mova220,gen149 --name gen_row2` |
| 3 | `t2av-eval judge routing --sets ltx220,mova220,gen149 --name gen_row3` |
| 4, 5, framing | `t2av-eval judge two_stage_ungated,gated,framing --stage1 <row 1 dir> --sets ltx220,mova220,gen149 --name gen_stage2` |

The launch settings of each set and row (flags, environment, shards) are copied from the recorded launches in
`config/sets.yaml`; `tests/test_conditions.py` rebuilds the recorded 11/01 and 10/30 commands from it exactly.

**Recorded per-row settings that differ between the families.** They are kept as recorded, so the CLI reproduces the
recorded runs; a new comparison across families has to take them into account.

| row | setting | HD-EPIC (11/01) | generated (10/30) | mute_anchor A sets (11/01) |
|---|---|---|---|---|
| 1 media-only | `T2AV_EVENT_TIME_FIELD` (structured `event_time_s` in the V and AVB prompts) | off | on | off |
| 1 media-only | `--axes` | all | all | a |
| 2 all tools | FLAM `--flam-hop-sec` | 5 | default (none) | – |
| 2 all tools | Synchformer section | action window (`synchformer_action_1030`) | anchor-time window (`synchformer_gen_1030`) | – |
| 2 all tools | AVoCaDO captions | fps 2, plain | fps 8, plain | – |
| 3 routing | run before | no | 220 only (10/30) | – |

**Does the event-time field change stage-1 labels on the generated sets?** No new calls; existing runs only. There is no
same-day pair with the field on and off (the field first existed on 10/30, and every 10/30 generated media-only run has it on).
The closest comparison is the 10/27 media-only run (off) against the 10/30 row 1 (on), on the 220 test items (35 per model;
AVB 24 LTX / 21 MOVA rows with a label in both). The field changes the V and AVB user prompts on every item; the A and
compliance prompts are byte-identical; the TCR / TCC prompts differ only in the list of eligible events (21 items), which
follows from the upstream labels, never in the field text.

| model | axis | flips off vs on | flip rate | same-day flip rate (10/28 reps) | acc off → on | bound |
|---|---|---|---|---|---|---|
| LTX | A (prompt unchanged) | 4 / 34 | .12 | .06 | .79 → .79 | .06 |
| LTX | V | 5 / 35 | .14 | .00 | .74 → .77 | .00 |
| LTX | AVB | 8 / 24 | .33 | .15 | .50 → .75 | .12 |
| MOVA | A (prompt unchanged) | 6 / 34 | .18 | .06 | .82 → .76 | .06 |
| MOVA | V | 4 / 35 | .11 | .06 | .83 → .94 | .06 |
| MOVA | AVB | 4 / 21 | .19 | .14 | .52 → .43 | .14 |

V and AVB labels change between the two runs more often than the same-day flip rate. But A, whose prompt is identical in
both runs, also flips at two to three times its same-day rate across these days. The comparison therefore cannot separate
the field from day-to-day change: no result. A same-day run with the field off and on would be needed to answer it.
Details: `docs/status/event_time_field_2026-11-02.md`.

**Tables.**

```bash
t2av-eval score --sets hdepic_p12,hdfoot_p12,hdmove_p12,p3p9 --media row1=<dir>,row2=<dir> --stage2 <stage-2 dir> --name hdepic_main_tables
```

## The final recipe

`t2av_eval/config/recipe_v4.yaml`, one threshold block for both families:

- AVB: FAIL evidence when the strongest binding-event Synchformer reading (action window) has |offset| ≥ 1.8 s and p ≥ .25
  (`PREREGISTERED_RULE.json`, written 2026-10-30 11:12, before any holdout result was read).
- A: a FLAM line is shown for an event whose first-query whole-clip max score is below T_flam = .2705
  (`flam_threshold.json`, written 2026-10-30 14:11, before any generated-set result was read); a Whisper transcript is
  shown when it contains a required word (never fires on HD-EPIC, which has no speech events).
- V: the caption is shown only when a text-only check finds an explicit contradiction of a GT event.
- A row 5 call whose text equals the row 4 text reuses the row 4 call.

`t2av_eval.gate.preregistered` loads both artifacts and refuses them if their results-seen flag is set or their values differ
from the config. **Drift check:** the label-free T_batch / P_batch per generated set is reported (`t2av-eval gate drift-check`),
never used as a gate.

**Discrepancy to verify.** The 10/30 generated row 5 (in `docs/generated_block_2026-10-30.md`) was produced with batch
thresholds; it is to be re-assembled under the pre-registered thresholds. `judge gated` on the generated sets now uses the
pre-registered rule; `--avb-thresholds batch` reproduces the 10/30 outputs and is not the recipe. The generated stage-2 rows
file keeps its 10/30 column name `row5_rule_batch`; its thresholds follow `--avb-thresholds`.

## Scoring

- **Rule:** stage1_lookup (`t2av_eval.scoring.lookup.row_label`): only the GT event ids of a row, events whose reason says
  precondition / not evaluated / skipped are dropped, a row is FAIL if any kept event is FAIL, and has no label (dropped from that
  condition) if no event is kept. TCC compares observed and required counts; TCR uses the item label.
- **Metrics** (`t2av_eval.scoring.tables`): acc, precision, recall per group and axis, FAIL positive, plus the false-alarm rate
  on PASS rows (on HD-EPIC, the originals) and acc on originals and variants. Groups are never pooled: P01P02, P03P09,
  P01P02-hdfoot, the two mute_anchor groups, 220-LTX, 220-MOVA, 149-LTX; a group mixing generation models is refused.
- **No-result bound** (`config/noise_bounds.yaml`): the same-day flip rate of the 10/28 media-only reps. A difference with
  |Δacc| ≤ bound is no result. P03–P09 uses the P01/P02 values; the 149 has no measured bound ("no bound").
- **Fixed / broken** vs row 1, with broken PASS rows; **AVB operating points**: recall on shifted rows vs false alarms on originals.

## AVoCaDO captions (GPU, qrsh)

```bash
qrsh -pe omp 4 -l gpu_memory=48G -l gpu_c=8.0          # the recorded 48 GB request; or an 80 GB A100
t2av-eval evidence captions -- --target gen149 --hardware a100_80g --name gen149_caps
```

`t2av_eval.evidence.captions_gen` holds the caption runner (moved from `run_qwen3_captions.py`) and a job entry that runs it in
the `qwen3_cap` env with the recorded settings of each target (`config/captions_gen.yaml`): fps 8 plain for the generated sets,
fps 2 plain for HD-EPIC, AVoCaDO full frame, greedy (`--sample-seed` for the screening samples). Output goes to a new dir
`WORK/captions/<name>_<YYYYMMDD>/`; existing caption files are never written. Hardware profiles, as recorded:

| profile | recorded | settings |
|---|---|---|
| `a100_80g` | scc-212, NVIDIA A100 80GB PCIe (10/31 149 and P03–P09 captions, the ones the tables use; 11/02 hdmove run). Request line unrecorded, use these flags: `qrsh -pe omp 4 -l gpu_memory=80G -l gpu_c=8.0` | no extra env |
| `gpu_48g` | `qrsh -pe omp 4 -l gpu_memory=48G -l gpu_c=8.0` (job 8386642, 11/01); ran on scc-502, NVIDIA L40S 46 GB; the hdmove captions of row 2 | `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` |
| `a6000_session` | 10/31 fallback, RTX A6000 46 GB, peak 19.6–20.4 GB; not used by the tables | same, `OMP_NUM_THREADS=2` |

Captions are byte-identical on a repeat on the same GPU but differ across GPU hardware (10/31: similarity .16–.91 to captions
made on other hardware), so each run README records the GPU from `nvidia-smi`. The recorded job scripts are in
`legacy/evaluation/ablation/captions/`.

## Tool screening

`t2av-eval screen clap | imagebind | vqascore | qwen3s` (qrsh). Each tool's FAIL threshold is the value at which 5% of the
P01/P02 PASS rows of its axis are called FAIL (`t2av-eval gate calibrate`), written with a timestamp before any other set is
scored, then applied unchanged to P03–P09, the 220 and the 149. A tool is added to a row only if, where it opens, it agrees
with the human label more often than the media-only judge on the same rows. Outcome (11/02): Synchformer (AVB) and FLAM (A)
pass; Qwen3-VL 3-sample, VQAScore, CLAP and ImageBind are closed.

## Controller experiment (pipeline v4 stage 3)

`t2av_eval.gate.controller`: a text-only interface, `choose(system, user, schema) -> (parsed, raw)`, with a Gemini and an
OpenAI backend (`config/controller.yaml`). It has no media argument; the media judge is Gemini only and never uses it.

```bash
t2av-eval controller choose --backend openai --prompt controller_prompt.yaml --inputs stage1_texts.jsonl --name ctl_openai
```

The prompt file holds `system` and `user` (with `{text}`); inputs are JSONL `{id, text}`; choices land in `choices.jsonl` with
the stage-3 schema `{event_id, axis, action, window, question, stop}`. OpenAI backend: `gpt-6-astra` (the API has no dated
snapshot; its listing date 2026-08-27 goes into every controller run README), reasoning effort `low` (the lowest the model
accepts), key `OPENAI_API_KEY`, no service-tier override, no temperature (the model rejects it). The Gemini backend uses
gemini-3.6-flash, thinking high, temperature 0, seed 42.

## Run dirs

Each `README.md` records: purpose and condition, run date, start time and host, model and thinking, the sets, prompt files and
in-code prompt modules with md5, git state, cache versions (audio cache, caption json, Synchformer sections, call cache; md5 or
entry counts), the key id of each shard, pacing, the stop rule, delete-after-use, the Files storage check, the exact command
and every shard command; events (start, STOP, end summary with rows and error rows) are appended. `run.json` holds the same.

## Tests

```bash
# login node: single worker, no media-runner replay
pytest tests -k "not test_rows_replay"
# full suite (includes the media-runner replay): only inside qrsh, threads capped at 4
qrsh -pe omp 4 -l h_rt=4:00:00 bash -c 'export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4; cd <repo>; pytest tests'
```

- `test_replay_1101.py`: 3 rows per axis of the 11/01 HD-EPIC table are replayed from the stored calls with zero Gemini calls,
  through the legacy code, the package and the CLI shard path; prompts (user, system, schema) and labels must equal 11/01.
- `test_moved_equivalence.py`: every moved module equals its legacy source apart from imports, path roots and the edits listed
  with a reason in `tests/moved_allowlist.json`.
- `test_conditions.py`, `test_run_control.py`, `test_controller.py`, `test_cache_keys.py`, `test_cli_and_tables.py`,
  `test_vendored.py`, `test_no_legacy_imports.py`.

## Legacy

`legacy/evaluation/ablation/` keeps every script runnable for reproduction; each has a first line pointing to its package
module. Their main-checkout paths go through `T2AV_LEGACY_ROOT` (default `<repo>/legacy_root`); see `legacy/README.md`.

## For a new collaborator

### Your own Gemini key

The package reads keys from the environment only; nothing in the repo or the config holds a key.

```bash
export GEMINI_API_KEY=<your key>          # in your shell or ~/.bashrc, never in a file inside the repo
export GEMINI_API_KEY_2=<second key>      # optional: shards rotate over the keys, each with its own calls-per-hour budget
t2av-eval check --files                   # shows GEMINI_API_KEY:<sha256 prefix> and your Files storage; never the key
```

Run READMEs record that id, so two people's runs can be told apart. Pacing and the Files check are per key, but the quota
behind them is per Google Cloud project: if your key shares a project with someone else's runs, lower `--calls-per-hour`.
Uploads count against the project's 20 GB Gemini Files storage until deleted (the CLI deletes each clip after its item).

### A new AVB evidence model (for example SparseFormer)

AVB evidence enters in two steps; the second needs the first.

1. **Screening, against the gate** (no judge calls). Copy `t2av_eval/screening/imagebind.py` to
   `screening/sparseformer.py`: its `run` stage scores every row of `gate.reliability.rows("p1p2" | "p3p9" | "220" | "149")`
   (row score = the weakest binding event), its `threshold` stage calls `gate.reliability.write_threshold("sparseformer", "AVB",
   <scores of the P01/P02 PASS rows>, low_is_fail=...)`, which sets the value that flags 5% of the P01/P02 PASS rows and
   writes it with a timestamp to `T2AV_data/tools/screen_1031/sparseformer/thresholds.json` before any other set is scored,
   and its `report` stage (`gate.reliability.report`) gives open rate, precision when open, recall, and the media-only judge
   on the same rows. Add the module to `PASS["screen"]` in `cli.py`; run it in qrsh. The tool passes only if the 5% holds
   outside P01/P02 and it beats the media-only judge where it opens (ImageBind failed both).
2. **AVB evidence next to Synchformer.** `t2av_eval/evidence/synchformer_action.py` writes per-event readings to
   `T2AV_data/tools/synchformer_action_1030/<set>/per_event_shard*.csv` with the columns `item_id, variant, event_id, label,
   status, offset, prob, p_offset0, n_occ, method`; stage 2 reads them through `judge/stage2/hdepic.py` (`sync_pe`,
   `avb_text`, `fires`). A SparseFormer module (`evidence/sparseformer_action.py`) that writes the same columns to its own
   `tools/sparseformer_action_<date>/` dir can feed the same code. If it reports an offset and a probability, derive its rule
   with `gate/avb_rule_derive.py` (T = 95th percentile of |offset| on the P01/P02 originals, P = 5th percentile of p on the
   shifted rows above T, 5% broken originals at most) and write its own pre-registered rule file before any holdout result;
   if it reports one score, the threshold of step 1 is its calibration. Making it part of `recipe_v4.yaml` changes the
   recipe and is decided before any evaluation-set result is read.

### A new dataset (BRITE)

There is no BRITE adapter in the package, in `legacy/` or in the main checkout yet. A new dataset enters at these points:

- **Items:** a prompt file in the item format the judge reads (`judge/media/core.build_item_meta_map`; examples:
  `T2AV_data/gen_holdout_149_1030/prompts_gen149.json`) and a videos dir with one `<item_id>/<item_id>_v1_raw.mp4` per item.
- **A set** in `config/sets.yaml` (family, prompts, videos, captions, shards); `t2av-eval judge media_only --sets <name>`
  then runs row 1 and `tests/test_conditions.py`-style checks can pin its command.
- **Captions:** a target in `config/captions_gen.yaml`, then `t2av-eval evidence captions -- --target <name> ...`.
- **GT for scoring:** a loader returning rows `{set, model, item_id, axis, gt}` like `scoring/generated_rows.gt()`
  (majority labels: `data/generated_gt.py`), added to `scoring/runs.py`.

## Open items

- No BRITE adapter exists yet (see "A new dataset").
- MediaPipe pose evidence and the OpenAI / local media-judge backends stay in `legacy/` (not used by the main table).
