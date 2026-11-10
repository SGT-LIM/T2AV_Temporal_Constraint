# Validation of this branch (2026-11-10, BU SCC, conda env t2av_eval, Python 3.11.16)

All checks were run from this branch's portable code with `T2AV_*` pointing at the lab data. No Gemini or GPU call was made.

| check | command | result |
|---|---|---|
| offline gate behaviour | `python repro/avt_gate/tests/test_gate_rules.py` (no `T2AV_*` set) | 8 / 8 tests pass: main thresholds; boundaries; initial-label branch selection; missing evidence → closed; caption omission ≠ contradiction; A speech / TC / TR closed in the combined rule; inactive branches at alpha = .01; Gate-only mapping and closed gate keeps the initial label |
| main config re-scoring from cache | `rescore_cached.py --config configs/main/frozen_p12_config.json --tag main_alpha05` | AVT-Judge labels = stored `final_benchmark_1108` combined labels on 25,628 / 25,628 GT-eligible units; Gate-only = stored direct-combined labels 25,628 / 25,628; openings = stored v2 openings 20,647 / 20,647 (non-speech); recomputed Whisper direct mapping = stored 25,628 / 25,628 |
| main metrics vs published paper-table handoff | `metrics_three_views.csv` vs `paper_tables_handoff_2026-11-09/tables/metrics_wide_all_views.csv` | 1,800 metric / count cells compared (3 methods × 3 views × 3 datasets × 7 axis views), 0 mismatches |
| sensitivity alpha = .01 | `rescore_cached.py --config configs/sensitivity/a01/frozen_config.json --tag sens_alpha01 --stored-tag a01` | openings, AVT-Judge and Gate-only labels = stored sensitivity run 25,628 / 25,628 each; 0 missing outputs |
| sensitivity alpha = .10 | same with `a10` | 25,628 / 25,628 each |
| unresolved output | – | 1 opened request has no output in every run that opens it: `220 MOVA|slap-then-help-then-thumbs_up__order|V`. It failed repeatedly in the original runs and stays missing; it is outside the six-method common subset. |
| secrets / personal paths | `grep` over the committed files | no API key; no lab absolute path in the portable code or configs. The two provenance JSONs had their paths rewritten to `$T2AV_*` (noted in `configs/`). |

**Not verified:**
- **Fresh machine without the lab file system:** the data were reached through the SCC paths. Access for people outside the `ivc-ml`
  group is not documented.
- **Re-running Stage 1, the one call, tool extraction (Whisper / FLAM / Synchformer / AVoCaDO) or Stage-2 calls from this branch:** not
  run, to avoid paid / GPU work. The commands are the recorded ones.
- **A live Stage-2 API smoke call:** not made. The cached re-scoring shows that every opened request of the main configuration has a cached
  output (except the unresolved one above), so no call is needed to reproduce the reported numbers.
- **Running the original stage modules** (e.g. `final_benchmark_1108.py score`) from this branch: not run, because they write into
  `runs/`. They are byte-identical to the experiment code after path substitution.
