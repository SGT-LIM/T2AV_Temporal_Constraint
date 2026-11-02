# Contributing

The rules of the project (CLAUDE.md of the main checkout) and where this package enforces them.

## Reporting

- Report acc / precision / recall per source and per generation model (LTX, MOVA, HD-EPIC original vs variant). Never pool
  LTX and MOVA. Balanced acc only as an internal diagnostic.
  - `t2av_eval.scoring.tables` keeps every group separate and refuses a group that mixes generation models.
- A between-condition difference within the no-result bound (`config/noise_bounds.yaml`) is reported as no result.
- Findings go to `docs/status/<topic>_<date>.md` in the main checkout: plain sentences, numbers per model, no metaphors.

## Runs

- Never mix runs from different days in one comparison. Each new run goes to a new dir with the date in its name; never
  overwrite or delete existing result dirs or caches (FLAM, Whisper, caption caches, Gemini Files).
  - `t2av_eval.run.rundir.create` appends the date and refuses an existing dir. Stage 2 copies a call cache
    (`--reuse-calls-from`) instead of writing into it. No command deletes a cache.
  - Gemini Files: only the clip a call just uploaded is deleted, after every call of its item succeeded. Never bulk-delete
    Gemini Files while any shard is running.
- API runs start in the terminal on a login node inside screen or nohup, not with qsub. GPU jobs (FLAM, Synchformer, Qwen,
  AVoCaDO) use a qrsh GPU session; `t2av-eval evidence` and `t2av-eval screen` refuse to run outside qrsh.
- Before any Gemini run: `conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval` and `t2av-eval check`. Keys come from
  the environment only (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, ...); a run without one stops before the first call.
- Every run dir has a README with model string, thinking setting, prompt version, cache versions and start time.
  `t2av_eval.run.rundir.write_readme` writes it; do not launch API work by hand outside the CLI.

## Code

- Do not change prompts, GT or gating while reproducing a baseline. Ask before changing anything in
  `gepa_stage2/manifests_v3/` or any GT file.
- Any change to a module moved from `legacy/` must keep `tests/test_moved_equivalence.py` passing. If the change is intended,
  add the name and a reason to `tests/moved_allowlist.json` in the same commit.
- `tests/test_replay_1101.py` must pass: it replays the 11/01 table with zero calls and fails on any prompt or label change.
- Tests: on a login node only `pytest tests -k "not test_rows_replay"` with one worker. Run the full suite only inside
  `qrsh -pe omp 4`, with OMP / MKL / OPENBLAS threads capped at 4.
- Small commits with clear messages; do not push before review.
