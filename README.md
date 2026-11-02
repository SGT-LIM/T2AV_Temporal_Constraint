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
`config/sets.yaml`; `tests/test_conditions.py` rebuilds the recorded 11/01 and 10/30 commands from it exactly. Note the
recorded differences: generated row 1 runs with `T2AV_EVENT_TIME_FIELD=1`, HD-EPIC row 1 without; HD-EPIC row 2 uses FLAM
hop 5, generated row 2 the default; the mute_anchor sets run `--axes a`.

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
the stage-3 schema `{event_id, axis, action, window, question, stop}`. The OpenAI backend (the GPT-6 Astra tier, key
`OPENAI_API_KEY`, no service-tier override) refuses to start until `model` (the exact dated id) and `reasoning_effort` (the
lowest the model accepts) are filled in `config/controller.yaml`.

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

## Open items

- The AVoCaDO caption jobs (`evaluation/ablation/captions/avocado_*.sh` in the main checkout) are not in the package; it reads
  the caption json files they produced.
- MediaPipe pose evidence and the OpenAI / local media-judge backends stay in `legacy/` (not used by the main table).
