# Gemini tool-option analysis

This report treats the human labels as GT and compares each Gemini/tool setting against them.

## Methods analyzed

- `no_tool`
- `mediapipe`
- `whisper`
- `clap`
- `whisper_clap`
- `all_tools`

## Ranking, TC-first

| rank_TC_first | method | TC_balanced_accuracy | TC_accuracy | TC_f1 | TC_fp | TC_fn | macro_balanced_accuracy_all_axes | macro_accuracy_all_axes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | whisper | 0.8105 | 0.8333 | 0.5833 | 16 | 4 | 0.7360 | 0.7600 |
| 2 | all_tools | 0.8072 | 0.8667 | 0.6190 | 11 | 5 | 0.7194 | 0.7783 |
| 3 | clap | 0.7990 | 0.8917 | 0.6486 | 7 | 6 | 0.6414 | 0.6333 |
| 4 | whisper_clap | 0.7794 | 0.8583 | 0.5854 | 11 | 6 | 0.7192 | 0.7883 |
| 5 | mediapipe | 0.7500 | 0.8083 | 0.5106 | 17 | 6 | 0.6677 | 0.6900 |
| 6 | no_tool | 0.7141 | 0.8250 | 0.4878 | 13 | 8 | 0.7391 | 0.7400 |

## Axis-level summary

| method | axis | n | accuracy | balanced_accuracy | precision | positive_recall | negative_recall | f1 | tn | fp | fn | tp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_tool | A | 120 | 0.7250 | 0.7870 | 0.9878 | 0.7168 | 0.8571 | 0.8308 | 6 | 1 | 32 | 81 |
| no_tool | V | 120 | 0.7250 | 0.7130 | 0.7442 | 0.5926 | 0.8333 | 0.6598 | 55 | 11 | 22 | 32 |
| no_tool | AVB | 120 | 0.5917 | 0.6449 | 0.9385 | 0.5755 | 0.7143 | 0.7135 | 10 | 4 | 45 | 61 |
| no_tool | TC | 120 | 0.8250 | 0.7141 | 0.4348 | 0.5556 | 0.8725 | 0.4878 | 89 | 13 | 8 | 10 |
| no_tool | CC | 120 | 0.8333 | 0.8367 | 0.8833 | 0.8030 | 0.8704 | 0.8413 | 47 | 7 | 13 | 53 |
| mediapipe | A | 120 | 0.7250 | 0.7200 | 0.9762 | 0.7257 | 0.7143 | 0.8325 | 5 | 2 | 31 | 82 |
| mediapipe | V | 120 | 0.6083 | 0.6069 | 0.5614 | 0.5926 | 0.6212 | 0.5766 | 41 | 25 | 22 | 32 |
| mediapipe | AVB | 120 | 0.6083 | 0.5613 | 0.9041 | 0.6226 | 0.5000 | 0.7374 | 7 | 7 | 40 | 66 |
| mediapipe | TC | 120 | 0.8083 | 0.7500 | 0.4138 | 0.6667 | 0.8333 | 0.5106 | 85 | 17 | 6 | 12 |
| mediapipe | CC | 120 | 0.7000 | 0.7003 | 0.7419 | 0.6970 | 0.7037 | 0.7188 | 38 | 16 | 20 | 46 |
| whisper | A | 120 | 0.8417 | 0.7819 | 0.9796 | 0.8496 | 0.7143 | 0.9100 | 5 | 2 | 17 | 96 |
| whisper | V | 120 | 0.7000 | 0.7088 | 0.6324 | 0.7963 | 0.6212 | 0.7049 | 41 | 25 | 11 | 43 |
| whisper | AVB | 120 | 0.7417 | 0.6988 | 0.9412 | 0.7547 | 0.6429 | 0.8377 | 9 | 5 | 26 | 80 |
| whisper | TC | 120 | 0.8333 | 0.8105 | 0.4667 | 0.7778 | 0.8431 | 0.5833 | 86 | 16 | 4 | 14 |
| whisper | CC | 120 | 0.6833 | 0.6801 | 0.7121 | 0.7121 | 0.6481 | 0.7121 | 35 | 19 | 19 | 47 |
| clap | A | 120 | 0.5167 | 0.5424 | 0.9508 | 0.5133 | 0.5714 | 0.6667 | 4 | 3 | 55 | 58 |
| clap | V | 120 | 0.5917 | 0.5749 | 0.5641 | 0.4074 | 0.7424 | 0.4731 | 49 | 17 | 32 | 22 |
| clap | AVB | 120 | 0.4333 | 0.5553 | 0.9130 | 0.3962 | 0.7143 | 0.5526 | 10 | 4 | 64 | 42 |
| clap | TC | 120 | 0.8917 | 0.7990 | 0.6316 | 0.6667 | 0.9314 | 0.6486 | 95 | 7 | 6 | 12 |
| clap | CC | 120 | 0.7333 | 0.7357 | 0.7833 | 0.7121 | 0.7593 | 0.7460 | 41 | 13 | 19 | 47 |
| whisper_clap | A | 120 | 0.9000 | 0.6789 | 0.9633 | 0.9292 | 0.4286 | 0.9459 | 3 | 4 | 8 | 105 |
| whisper_clap | V | 120 | 0.6833 | 0.6886 | 0.6250 | 0.7407 | 0.6364 | 0.6780 | 42 | 24 | 14 | 40 |
| whisper_clap | AVB | 120 | 0.7750 | 0.7177 | 0.9438 | 0.7925 | 0.6429 | 0.8615 | 9 | 5 | 22 | 84 |
| whisper_clap | TC | 120 | 0.8583 | 0.7794 | 0.5217 | 0.6667 | 0.8922 | 0.5854 | 91 | 11 | 6 | 12 |
| whisper_clap | CC | 120 | 0.7250 | 0.7315 | 0.8000 | 0.6667 | 0.7963 | 0.7273 | 43 | 11 | 22 | 44 |
| all_tools | A | 120 | 0.8583 | 0.6568 | 0.9615 | 0.8850 | 0.4286 | 0.9217 | 3 | 4 | 13 | 100 |
| all_tools | V | 120 | 0.6417 | 0.6574 | 0.5714 | 0.8148 | 0.5000 | 0.6718 | 33 | 33 | 10 | 44 |
| all_tools | AVB | 120 | 0.8250 | 0.7770 | 0.9570 | 0.8396 | 0.7143 | 0.8945 | 10 | 4 | 17 | 89 |
| all_tools | TC | 120 | 0.8667 | 0.8072 | 0.5417 | 0.7222 | 0.8922 | 0.6190 | 91 | 11 | 5 | 13 |
| all_tools | CC | 120 | 0.7000 | 0.6987 | 0.7344 | 0.7121 | 0.6852 | 0.7231 | 37 | 17 | 19 | 47 |

## TC breakdown notes

### by_temporal_type

| method | temporal_type | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | 36 | 0.6667 | 0.6883 | 9 | 3 | 11 | 13 |
| all_tools | absolute_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| all_tools | relative_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| all_tools | relative_synchronization | 12 | 0.9167 | 0.9500 | 1 | 0 | 2 | 9 |
| all_tools | absolute_order | 36 | 0.9722 | 0.9722 | 1 | 0 | 0 | 35 |
| all_tools | absolute_synchronization | 12 | 1.0000 | 1.0000 | 0 | 0 | 0 | 12 |
| clap | relative_order | 36 | 0.8056 | 0.7890 | 3 | 4 | 10 | 19 |
| clap | absolute_order | 36 | 0.9167 | 0.9167 | 3 | 0 | 0 | 33 |
| clap | absolute_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| clap | absolute_synchronization | 12 | 0.9167 | 0.9167 | 1 | 0 | 0 | 11 |
| clap | relative_synchronization | 12 | 0.9167 | 0.7500 | 0 | 1 | 1 | 10 |
| clap | relative_sync_count | 12 | 1.0000 | 1.0000 | 0 | 0 | 1 | 11 |
| mediapipe | relative_order | 36 | 0.6389 | 0.6526 | 9 | 4 | 10 | 13 |
| mediapipe | relative_synchronization | 12 | 0.7500 | 0.6500 | 2 | 1 | 1 | 8 |
| mediapipe | absolute_order | 36 | 0.8611 | 0.8611 | 5 | 0 | 0 | 31 |
| mediapipe | absolute_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| mediapipe | relative_sync_count | 12 | 0.9167 | 0.9545 | 1 | 0 | 1 | 10 |
| mediapipe | absolute_synchronization | 12 | 1.0000 | 1.0000 | 0 | 0 | 0 | 12 |
| no_tool | relative_order | 36 | 0.6389 | 0.6266 | 7 | 6 | 8 | 15 |
| no_tool | absolute_order | 36 | 0.8611 | 0.8611 | 5 | 0 | 0 | 31 |
| no_tool | absolute_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| no_tool | absolute_synchronization | 12 | 0.9167 | 0.9167 | 1 | 0 | 0 | 11 |
| no_tool | relative_sync_count | 12 | 0.9167 | 0.5000 | 0 | 1 | 0 | 11 |
| no_tool | relative_synchronization | 12 | 1.0000 | 1.0000 | 0 | 0 | 2 | 10 |
| whisper | relative_order | 36 | 0.7500 | 0.7825 | 8 | 1 | 13 | 14 |
| whisper | relative_sync_count | 12 | 0.7500 | 0.4091 | 2 | 1 | 0 | 9 |
| whisper | absolute_sync_count | 12 | 0.8333 | 0.4545 | 1 | 1 | 0 | 10 |
| whisper | relative_synchronization | 12 | 0.8333 | 0.7000 | 1 | 1 | 1 | 9 |
| whisper | absolute_order | 36 | 0.9167 | 0.9167 | 3 | 0 | 0 | 33 |
| whisper | absolute_synchronization | 12 | 0.9167 | 0.9167 | 1 | 0 | 0 | 11 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_modality_combination

| method | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | Speech + Action (sounding) | 24 | 0.7917 | 0.7917 | 5 | 0 | 0 | 19 |
| all_tools | Action (silent) + Action (sounding) | 24 | 0.8333 | 0.7222 | 1 | 3 | 3 | 17 |
| all_tools | Speech + Action (silent) + Action (sounding) | 48 | 0.8542 | 0.7738 | 5 | 2 | 4 | 37 |
| all_tools | Speech + Action (silent) | 24 | 1.0000 | 1.0000 | 0 | 0 | 6 | 18 |
| clap | Speech + Action (silent) + Action (sounding) | 48 | 0.8333 | 0.6190 | 4 | 4 | 2 | 38 |
| clap | Action (silent) + Action (sounding) | 24 | 0.9167 | 0.8889 | 1 | 1 | 5 | 17 |
| clap | Speech + Action (silent) | 24 | 0.9167 | 0.8889 | 1 | 1 | 5 | 17 |
| clap | Speech + Action (sounding) | 24 | 0.9583 | 0.9583 | 1 | 0 | 0 | 23 |
| mediapipe | Speech + Action (sounding) | 24 | 0.7500 | 0.7500 | 6 | 0 | 0 | 18 |
| mediapipe | Speech + Action (silent) + Action (sounding) | 48 | 0.7708 | 0.7262 | 9 | 2 | 4 | 33 |
| mediapipe | Speech + Action (silent) | 24 | 0.8333 | 0.7222 | 1 | 3 | 3 | 17 |
| mediapipe | Action (silent) + Action (sounding) | 24 | 0.9167 | 0.8889 | 1 | 1 | 5 | 17 |
| no_tool | Speech + Action (silent) + Action (sounding) | 48 | 0.7708 | 0.6548 | 8 | 3 | 3 | 34 |
| no_tool | Action (silent) + Action (sounding) | 24 | 0.7917 | 0.6944 | 2 | 3 | 3 | 16 |
| no_tool | Speech + Action (sounding) | 24 | 0.8750 | 0.8750 | 3 | 0 | 0 | 21 |
| no_tool | Speech + Action (silent) | 24 | 0.9167 | 0.8333 | 0 | 2 | 4 | 18 |
| whisper | Action (silent) + Action (sounding) | 24 | 0.7500 | 0.7778 | 5 | 1 | 5 | 13 |
| whisper | Speech + Action (sounding) | 24 | 0.7500 | 0.7500 | 6 | 0 | 0 | 18 |
| whisper | Speech + Action (silent) + Action (sounding) | 48 | 0.8542 | 0.7738 | 5 | 2 | 4 | 37 |
| whisper | Speech + Action (silent) | 24 | 0.9583 | 0.9167 | 0 | 1 | 5 | 18 |
| whisper_clap | Action (silent) + Action (sounding) | 24 | 0.7500 | 0.6667 | 3 | 3 | 3 | 15 |
| whisper_clap | Speech + Action (sounding) | 24 | 0.7500 | 0.7500 | 6 | 0 | 0 | 18 |
| whisper_clap | Speech + Action (silent) + Action (sounding) | 48 | 0.9167 | 0.8095 | 2 | 2 | 4 | 40 |
| whisper_clap | Speech + Action (silent) | 24 | 0.9583 | 0.9167 | 0 | 1 | 5 | 18 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_temporal_type_x_modality_combination

| method | temporal_type | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | Speech + Action (sounding) | 6 | 0.3333 | 0.3333 | 4 | 0 | 0 | 2 |
| all_tools | relative_order | Action (silent) + Action (sounding) | 6 | 0.5000 | 0.3000 | 1 | 2 | 3 | 0 |
| all_tools | absolute_sync_count | Speech + Action (silent) + Action (sounding) | 3 | 0.6667 | 0.5000 | 0 | 1 | 0 | 2 |
| all_tools | relative_sync_count | Action (silent) + Action (sounding) | 3 | 0.6667 | 0.5000 | 0 | 1 | 0 | 2 |
| all_tools | relative_synchronization | Speech + Action (sounding) | 3 | 0.6667 | 0.6667 | 1 | 0 | 0 | 2 |
| all_tools | relative_order | Speech + Action (silent) + Action (sounding) | 18 | 0.7222 | 0.7462 | 4 | 1 | 4 | 9 |
| all_tools | absolute_order | Speech + Action (silent) + Action (sounding) | 18 | 0.9444 | 0.9444 | 1 | 0 | 0 | 17 |
| all_tools | absolute_order | Action (silent) + Action (sounding) | 6 | 1.0000 | 1.0000 | 0 | 0 | 0 | 6 |
| all_tools | absolute_order | Speech + Action (silent) | 6 | 1.0000 | 1.0000 | 0 | 0 | 0 | 6 |
| all_tools | absolute_order | Speech + Action (sounding) | 6 | 1.0000 | 1.0000 | 0 | 0 | 0 | 6 |
| all_tools | absolute_sync_count | Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_sync_count | Speech + Action (silent) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_sync_count | Speech + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_synchronization | Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_synchronization | Speech + Action (silent) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_synchronization | Speech + Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | absolute_synchronization | Speech + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | relative_order | Speech + Action (silent) | 6 | 1.0000 | 1.0000 | 0 | 0 | 4 | 2 |
| all_tools | relative_sync_count | Speech + Action (silent) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | relative_sync_count | Speech + Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | relative_sync_count | Speech + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | relative_synchronization | Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| all_tools | relative_synchronization | Speech + Action (silent) | 3 | 1.0000 | 1.0000 | 0 | 0 | 2 | 1 |
| all_tools | relative_synchronization | Speech + Action (silent) + Action (sounding) | 3 | 1.0000 | 1.0000 | 0 | 0 | 0 | 3 |
| clap | absolute_sync_count | Speech + Action (silent) + Action (sounding) | 3 | 0.6667 | 0.5000 | 0 | 1 | 0 | 2 |
| clap | absolute_synchronization | Speech + Action (silent) + Action (sounding) | 3 | 0.6667 | 0.6667 | 1 | 0 | 0 | 2 |
| clap | relative_order | Action (silent) + Action (sounding) | 6 | 0.6667 | 0.4000 | 1 | 1 | 4 | 0 |
| clap | relative_synchronization | Speech + Action (silent) | 3 | 0.6667 | 0.7500 | 0 | 1 | 1 | 1 |
| clap | relative_order | Speech + Action (silent) + Action (sounding) | 18 | 0.7778 | 0.6615 | 1 | 3 | 2 | 12 |
| clap | absolute_order | Speech + Action (silent) | 6 | 0.8333 | 0.8333 | 1 | 0 | 0 | 5 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

## Recommended reading order

1. `method_ranking.csv`: decide which method is best under a TC-first criterion.
2. `tc_breakdown_by_temporal_type.csv`: check whether synchronization, order, count, or absolute timing drives differences.
3. `tc_method_disagreement_cases.csv`: inspect cases where tool options disagree.
4. `qualitative_examples.md` and `details/*.txt`: read model reasons/evidence for TP/TN/FP/FN examples.
