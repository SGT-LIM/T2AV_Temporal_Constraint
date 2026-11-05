# First live run through the t2av-eval CLI: P03-P09 mute_anchor A, row 1 (2026-11-04)

## Run

- Command: `t2av-eval judge media_only --sets ma_p3p9 --name hdepic_ma39_row1_clicheck2` (branch refactor/pipeline-v4 at cdbf73a).
- Run dir: `T2AV_refactor/runs/results/hdepic_ma39_row1_clicheck2_20261104/` (README records model, prompts, key id, Files check).
- gemini-3.6-flash, thinking high, `--axes a`, media only; 3 shards, 1 key, pacing 2,000 calls / hour; delete-after-use on.
- Start 21:13:52, end 21:25:52; 118 rows, 0 error rows, no STOP. Files storage: 0.01 GB used before launch.
- A first launch (`hdepic_ma39_row1_clicheck_20261104`) stopped before any shard or judge call on a launcher bug
  (`env.update` with two mappings), fixed in cdbf73a.

## Reference

- `T2AV_data/real_av/eval/results/hdepic_main_ma39_row1_A_g36_1101`: 113 items from the 11/02 rerun, 5 items whose only row
  is from 11/01. Cross-day: 11/02 (and 11/01) vs 11/04.
- Scoring: stage1_lookup on the 118 GT rows (40 mute_anchor, 40 original, 38 sham), FAIL positive.

## Result

- A user prompts: identical on 118 of 118 items. The CLI runs the recorded procedure.
- Labels: 6 of 118 rows flip (.051), 2 in each part. The HD-EPIC A bound (same-day flip rate, 10/28) is .02.

| run | acc | precision | recall (mute_anchor) | FA original | FA sham |
|---|---|---|---|---|---|
| 11/02 reference | .653 | .33 | .025 | .00 | .05 |
| 11/04 CLI | .669 | .60 | .075 | .05 | .00 |

- Accuracy differs by +.017, within the bound: no result for accuracy.
- The flip rate (.051) is above the same-day bound. The two runs are two days apart; on the generated sets, A labels with an
  identical prompt flipped .12-.18 across three days against .06 within a day (event_time_field_2026-11-02.md). This run
  cannot separate day-to-day change from a difference in the CLI path; the prompts being identical points to the former.
- Precision moves from .33 to .60 on 3 and 5 FAIL calls; with 40 muted anchors, both runs miss nearly all of them.
