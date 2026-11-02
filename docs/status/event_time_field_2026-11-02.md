# Event-time field and generated-set stage-1 labels (2026-11-02)

Question: does `T2AV_EVENT_TIME_FIELD=1` (structured `event_time_s` in the V and AVB prompts; on in the 10/30 generated row 1,
off in the 11/01 HD-EPIC row 1) change stage-1 labels on the generated sets? Existing runs only, no new calls.

## Runs

- Field off: `eval_results/multi_agent/baseline_min3_g36_1027` (media-only, 10/27, 220 test split, 35 videos per model).
- Field on: `eval_results/multi_agent/gen_row1_anchor_g36_1030` (row 1, 10/30).
- Same-day reference: `baseline_min3_g36_rep2_1028` and `_rep3_1028` (media-only, field off, 10/28).
- No same-day on / off pair exists: the field was added on 10/30, and every 10/30 generated media-only run has it on (the
  smoke run is one video, also on).
- Scoring: the stage1_lookup rule on the manifests_v3 rows of the 220 (ltx, mova); rows compared where both runs give a label.

## Prompts

- V and AVB user prompts differ on every item (31 AVB items, 35 V items per model).
- A and compliance user prompts are byte-identical in both runs.
- TCR / TCC user prompts differ on 21 items, only in the list of eligible events ("Score ONLY these event_ids"), which follows
  from the upstream labels; the field text is in none of the changed lines.

## Labels

| model | axis | n | flips off vs on | flip rate | same-day flip rate | acc off | acc on | delta acc | bound |
|---|---|---|---|---|---|---|---|---|---|
| LTX | A | 34 | 4 | .12 | .06 | .79 | .79 | .00 | .06 |
| LTX | V | 35 | 5 | .14 | .00 | .74 | .77 | +.03 | .00 |
| LTX | AVB | 24 | 8 | .33 | .15 | .50 | .75 | +.25 | .12 |
| LTX | TCR | 4 | 1 | .25 | .00 | .75 | 1.00 | +.25 | – |
| LTX | TCC | 6 | 1 | .17 | .17 | .83 | 1.00 | +.17 | – |
| MOVA | A | 34 | 6 | .18 | .06 | .82 | .76 | −.06 | .06 |
| MOVA | V | 35 | 4 | .11 | .06 | .83 | .94 | +.11 | .06 |
| MOVA | AVB | 21 | 4 | .19 | .14 | .52 | .43 | −.10 | .14 |
| MOVA | TCC | 3 | 0 | .00 | .33 | .67 | .67 | .00 | – |

## Reading

- V and AVB labels flip more often between the two runs than between the two same-day reps: LTX V .14 vs .00, AVB .33 vs .15;
  MOVA V .11 vs .06, AVB .19 vs .14.
- A, whose prompt is identical in both runs, also flips more across these days than within a day: LTX .12 vs .06, MOVA .18
  vs .06.
- The off and on runs are three days apart, so the field and the day-to-day change cannot be separated. This is no result
  for the field.
- Delta acc: V +.03 (LTX) and +.11 (MOVA), AVB +.25 (LTX) and −.10 (MOVA); the AVB n is 21–24.
- Answering the question needs one same-day pair, field on and off, on the 220; that is a new run and was not made.
