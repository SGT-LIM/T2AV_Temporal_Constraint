# Row-5 (gated) gate configuration: authoritative copies for pipeline v4 (2026-11-06)

These are byte-identical copies of the gate files used by every reported gated experiment:
- P03-P09: HG4 / HMB4 / HMB5 calls
- 220 / 149: G4 / G5
- 2k_25: K4 / K5
- the sensitivity table (`sens_1105`)

They are laid out under the same relative paths that pipeline v4 reads from its data root (`t2av_eval/config/recipe_v4.yaml`), so
they can be dropped into any data root without code changes. Check them with `sha256sum -c SHA256SUMS`.

| file | content | used by |
|---|---|---|
| `tools/synchformer_action_1030/PREREGISTERED_RULE.json` | AVB rule: T = 1.8 s, P = .25 (written 2026-10-30 11:12, holdout not seen) | `gate.preregistered.avb_rule()`, HD-EPIC `fires()`, generated `sync_fire()`, framing sentences |
| `tools/gen_evidence_1030/flam_threshold.json` | A gate: T_flam = .2705 (written 2026-10-30 14:11, generated results not seen) | `gate.preregistered.t_flam()`, HD-EPIC and generated `a_text(gated=True)` |
| `reference/sensitivity_cutoffs_1105.json` | 1 % / 5 % / 10 % cutoffs of the reported sensitivity table (5 % = the recipe). Reference only, not loaded by v4 | — |

## What was compared (refactor/pipeline-v4 @ a140c12 against the scripts and files behind the reported gated numbers)

**Threshold files.** The fixture copies (`tests/fixtures/replay_1101/stage2/sya/PREREGISTERED_RULE.json` and
`stage2/evd/flam_threshold.json`) are byte-identical to the authoritative files and to these copies:

| file | sha256 (first 16) |
|---|---|
| `PREREGISTERED_RULE.json` | `088c0dcc7010de5a` |
| `flam_threshold.json` | `06f23937293770e2` |

No threshold differs.

**Admission rules.** The rules in v4 equal the legacy code that produced the reported rows:
- Comparisons:
  - `judge/stage2/hdepic.py` against `hd_stage2_1101.py`, functions a_parts … admitted.
  - `judge/stage2/generated.py` against `gen_stage2_1030.py`: the caption-check prompt and schema, `a_text`, `vcheck`.
  - `sync_fire()` with `AVB_MAIN = "preregistered"` against `gen_row5_prereg_1102.fire_prereg`.
- The only differences are import and path wiring and one log line.
- **A:**
  - A FLAM line is shown for an event whose first-query whole-clip max score is below T_flam.
  - A Whisper transcript is shown when it contains a required speech word.
  - When the gated text equals the row-4 text, the row-4 call is reused.
- **V:** the caption is shown only when the text-only caption check says the caption contradicts a GT event of the row.
  2k_25 used the same prompt and schema.
- **AVB:** the gate fires when the strongest binding-event Synchformer reading has |offset| ≥ T and p ≥ P.
  - The gated judge sees the reading.
  - The code-rule variant sets FAIL.
- **TR / TC:** no gate.

**Framing config.** `t2av_eval/config/framing_config_1030.json` differs from the legacy file only in its `note` and `source`
fields. The package reads T and P through `avb_rule()`; the legacy file named the same rule file by absolute path. The sentences
and values are identical.

**Why the fixtures cannot stand in for the configuration.** They are test subsets:
- `sya/b110/per_event_shard0.csv` has 3 of 64 rows, and there are no holdout, p12all or avbadd readings.
- There are no generated-set Synchformer readings.
- There are 3 FLAM records and 3 caption checks.

Only `tests/replay_1101/run_stage2.py` points v4 at them. In a normal run v4 loads the files above from
`$T2AV_DATA_ROOT/tools/...`, and `config/paths.yaml` defaults that root to a BU SCC path.

**Other differences, not about thresholds:**
- **2k_25:** v4 has no 2k_25 stage-2 module. The reported 2k_25 gated rows came from `gen2k25_stage2_1104.py`, with the same rule,
  T_flam and caption-check prompt.
- **Missing stage-2 output:** v4 `generated.stage_score` fills a missing stage-2 label with the media-only label (`g4 or anc`), as
  the 10/30 tables did. `docs/section6_verified_results.md` (main branch) excludes such units as missing outputs instead.

## Using these thresholds on BRITE (Snigdha)

Do not recalibrate on BRITE. Do not run any of these on BRITE:
- `gate/avb_rule_derive.py`
- the `flam_threshold` stage of `evidence/gen_evidence.py`
- `t2av-eval gate calibrate`
- `drift-check` as a gate

`gate.preregistered` stops the run if the files or `recipe_v4.yaml` change. Commands:

```bash
git clone -b refactor/pipeline-v4 git@github.com:SGT-LIM/T2AV_Temporal_Constraint.git && cd T2AV_Temporal_Constraint
export T2AV_DATA_ROOT=/path/to/brite_data_root        # BRITE videos, prompts and tool records
export T2AV_INPUTS_ROOT=/path/to/inputs_root          # read-only inputs (see config/paths.yaml)
export T2AV_WORK_ROOT=/path/to/brite_runs             # all outputs and call caches
(cd gate_artifacts/row5_v4 && sha256sum -c SHA256SUMS)
mkdir -p "$T2AV_DATA_ROOT/tools" && cp -rn gate_artifacts/row5_v4/tools/. "$T2AV_DATA_ROOT/tools/"
t2av-eval check        # must print: AVB rule: T 1.8 P 0.25 written 2026-10-30T11:12:01; T_flam 0.2705
```

`cp -n` never overwrites. If `t2av-eval check` reports a mismatch, the data root already holds different files: stop and compare
checksums.

**Running the gated condition:** this needs a BRITE set in `config/sets.yaml`, which does not exist yet (README, "A new dataset
(BRITE)"). The pattern is the same as for the existing sets:

```bash
t2av-eval judge media_only --sets brite --name brite_row1
t2av-eval judge two_stage_ungated,gated --stage1 <brite_row1 run dir> --sets brite --name brite_stage2 --avb-thresholds preregistered
```

**Per-item tool readings.** The gate needs readings computed on BRITE itself; these are inputs, not thresholds:
- Synchformer readings, FLAM records, Whisper transcripts, captions, and the text-only caption check.
- The caption check is a Gemini call made on your side.
- Which readers apply depends on the set's family in `config/sets.yaml`:
  - `hdepic`-style reads action-window Synchformer readings and per-item FLAM records.
  - `generated`-style reads `synchformer_gen` readings and `gen_evidence` text.

**Unverified:** BRITE's family, adapter, and whether its readings reproduce the action-window spans used in calibration.
