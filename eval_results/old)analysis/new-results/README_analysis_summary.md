# Gemini tool-option analysis

This report treats the human labels as GT and compares each Gemini/tool setting against them.

## Methods analyzed

- `no_tool`
- `mediapipe`
- `whisper`
- `clap`
- `mediapipe_whisper`
- `mediapipe_clap`
- `whisper_clap`
- `all_tools`

## Ranking, TC-first

| rank_TC_first | method | TC_balanced_accuracy | TC_accuracy | TC_f1 | TC_fp | TC_fn | macro_balanced_accuracy_all_axes | macro_accuracy_all_axes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | all_tools | 0.8571 | 0.8000 | 0.7500 | 4 | 0 | 0.6767 | 0.6917 |
| 2 | mediapipe | 0.8214 | 0.7500 | 0.7059 | 5 | 0 | 0.6927 | 0.6750 |
| 3 | mediapipe_whisper | 0.8095 | 0.8000 | 0.7143 | 3 | 1 | 0.5934 | 0.6417 |
| 4 | no_tool | 0.7619 | 0.8000 | 0.6667 | 2 | 2 | 0.6270 | 0.6750 |
| 5 | whisper_clap | 0.7262 | 0.7500 | 0.6154 | 3 | 2 | 0.6479 | 0.7167 |
| 6 | whisper | 0.7262 | 0.7500 | 0.6154 | 3 | 2 | 0.6328 | 0.6667 |
| 7 | clap | 0.6429 | 0.7000 | 0.5000 | 3 | 3 | 0.5168 | 0.5500 |
| 8 | mediapipe_clap | 0.5595 | 0.6500 | 0.3636 | 3 | 4 | 0.4670 | 0.4833 |

## Axis-level summary

| method | axis | n | accuracy | balanced_accuracy | precision | positive_recall | negative_recall | f1 | tn | fp | fn | tp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_tool | A | 20 | 0.7500 | 0.6389 | 0.9333 | 0.7778 | 0.5000 | 0.8485 | 1 | 1 | 4 | 14 |
| no_tool | V | 20 | 0.5500 | 0.5625 | 0.6667 | 0.5000 | 0.6250 | 0.5714 | 5 | 3 | 6 | 6 |
| no_tool | AVB | 20 | 0.6000 | 0.6061 | 0.6667 | 0.5455 | 0.6667 | 0.6000 | 6 | 3 | 5 | 6 |
| no_tool | TC_REL | 20 | 0.8000 | 0.7619 | 0.6667 | 0.6667 | 0.8571 | 0.6667 | 12 | 2 | 2 | 4 |
| no_tool | TC_COUNT | 20 | 0.7000 | 0.5312 | 0.2500 | 0.2500 | 0.8125 | 0.2500 | 13 | 3 | 3 | 1 |
| no_tool | CC | 20 | 0.6500 | 0.6616 | 0.7500 | 0.5455 | 0.7778 | 0.6316 | 7 | 2 | 5 | 6 |
| mediapipe | A | 20 | 0.8500 | 0.9167 | 1.0000 | 0.8333 | 1.0000 | 0.9091 | 2 | 0 | 3 | 15 |
| mediapipe | V | 20 | 0.6500 | 0.6042 | 0.6667 | 0.8333 | 0.3750 | 0.7407 | 3 | 5 | 2 | 10 |
| mediapipe | AVB | 20 | 0.6500 | 0.6313 | 0.6429 | 0.8182 | 0.4444 | 0.7200 | 4 | 5 | 2 | 9 |
| mediapipe | TC_REL | 20 | 0.7500 | 0.8214 | 0.5455 | 1.0000 | 0.6429 | 0.7059 | 9 | 5 | 0 | 6 |
| mediapipe | TC_COUNT | 20 | 0.6500 | 0.6875 | 0.3333 | 0.7500 | 0.6250 | 0.4615 | 10 | 6 | 1 | 3 |
| mediapipe | CC | 20 | 0.5000 | 0.4949 | 0.5455 | 0.5455 | 0.4444 | 0.5455 | 4 | 5 | 5 | 6 |
| whisper | A | 20 | 0.8500 | 0.6944 | 0.9412 | 0.8889 | 0.5000 | 0.9143 | 1 | 1 | 2 | 16 |
| whisper | V | 20 | 0.5500 | 0.5208 | 0.6154 | 0.6667 | 0.3750 | 0.6400 | 3 | 5 | 4 | 8 |
| whisper | AVB | 20 | 0.5500 | 0.5505 | 0.6000 | 0.5455 | 0.5556 | 0.5714 | 5 | 4 | 5 | 6 |
| whisper | TC_REL | 20 | 0.7500 | 0.7262 | 0.5714 | 0.6667 | 0.7857 | 0.6154 | 11 | 3 | 2 | 4 |
| whisper | TC_COUNT | 20 | 0.7000 | 0.7188 | 0.3750 | 0.7500 | 0.6875 | 0.5000 | 11 | 5 | 1 | 3 |
| whisper | CC | 20 | 0.6000 | 0.5859 | 0.6154 | 0.7273 | 0.4444 | 0.6667 | 4 | 5 | 3 | 8 |
| clap | A | 20 | 0.6000 | 0.5556 | 0.9167 | 0.6111 | 0.5000 | 0.7333 | 1 | 1 | 7 | 11 |
| clap | V | 20 | 0.4500 | 0.4792 | 0.5714 | 0.3333 | 0.6250 | 0.4211 | 5 | 3 | 8 | 4 |
| clap | AVB | 20 | 0.4500 | 0.4697 | 0.5000 | 0.2727 | 0.6667 | 0.3529 | 6 | 3 | 8 | 3 |
| clap | TC_REL | 20 | 0.7000 | 0.6429 | 0.5000 | 0.5000 | 0.7857 | 0.5000 | 11 | 3 | 3 | 3 |
| clap | TC_COUNT | 20 | 0.6000 | 0.4688 | 0.1667 | 0.2500 | 0.6875 | 0.2000 | 11 | 5 | 3 | 1 |
| clap | CC | 20 | 0.5000 | 0.4848 | 0.5385 | 0.6364 | 0.3333 | 0.5833 | 3 | 6 | 4 | 7 |
| mediapipe_whisper | A | 20 | 0.6500 | 0.3611 | 0.8667 | 0.7222 | 0.0000 | 0.7879 | 0 | 2 | 5 | 13 |
| mediapipe_whisper | V | 20 | 0.5000 | 0.4792 | 0.5833 | 0.5833 | 0.3750 | 0.5833 | 3 | 5 | 5 | 7 |
| mediapipe_whisper | AVB | 20 | 0.6000 | 0.5960 | 0.6364 | 0.6364 | 0.5556 | 0.6364 | 5 | 4 | 4 | 7 |
| mediapipe_whisper | TC_REL | 20 | 0.8000 | 0.8095 | 0.6250 | 0.8333 | 0.7857 | 0.7143 | 11 | 3 | 1 | 5 |
| mediapipe_whisper | TC_COUNT | 20 | 0.7000 | 0.7188 | 0.3750 | 0.7500 | 0.6875 | 0.5000 | 11 | 5 | 1 | 3 |
| mediapipe_whisper | CC | 20 | 0.6000 | 0.5960 | 0.6364 | 0.6364 | 0.5556 | 0.6364 | 5 | 4 | 4 | 7 |
| mediapipe_clap | A | 20 | 0.6000 | 0.7778 | 1.0000 | 0.5556 | 1.0000 | 0.7143 | 2 | 0 | 8 | 10 |
| mediapipe_clap | V | 20 | 0.3500 | 0.3542 | 0.4444 | 0.3333 | 0.3750 | 0.3810 | 3 | 5 | 8 | 4 |
| mediapipe_clap | AVB | 20 | 0.3500 | 0.3586 | 0.3750 | 0.2727 | 0.4444 | 0.3158 | 4 | 5 | 8 | 3 |
| mediapipe_clap | TC_REL | 20 | 0.6500 | 0.5595 | 0.4000 | 0.3333 | 0.7857 | 0.3636 | 11 | 3 | 4 | 2 |
| mediapipe_clap | TC_COUNT | 20 | 0.5000 | 0.3125 | 0.0000 | 0.0000 | 0.6250 |  | 10 | 6 | 4 | 0 |
| mediapipe_clap | CC | 20 | 0.4500 | 0.4394 | 0.5000 | 0.5455 | 0.3333 | 0.5217 | 3 | 6 | 5 | 6 |
| whisper_clap | A | 20 | 0.8500 | 0.4722 | 0.8947 | 0.9444 | 0.0000 | 0.9189 | 0 | 2 | 1 | 17 |
| whisper_clap | V | 20 | 0.6500 | 0.6458 | 0.7273 | 0.6667 | 0.6250 | 0.6957 | 5 | 3 | 4 | 8 |
| whisper_clap | AVB | 20 | 0.6500 | 0.6515 | 0.7000 | 0.6364 | 0.6667 | 0.6667 | 6 | 3 | 4 | 7 |
| whisper_clap | TC_REL | 20 | 0.7500 | 0.7262 | 0.5714 | 0.6667 | 0.7857 | 0.6154 | 11 | 3 | 2 | 4 |
| whisper_clap | TC_COUNT | 20 | 0.7500 | 0.7500 | 0.4286 | 0.7500 | 0.7500 | 0.5455 | 12 | 4 | 1 | 3 |
| whisper_clap | CC | 20 | 0.6500 | 0.6414 | 0.6667 | 0.7273 | 0.5556 | 0.6957 | 5 | 4 | 3 | 8 |
| all_tools | A | 20 | 0.8000 | 0.6667 | 0.9375 | 0.8333 | 0.5000 | 0.8824 | 1 | 1 | 3 | 15 |
| all_tools | V | 20 | 0.5500 | 0.5208 | 0.6154 | 0.6667 | 0.3750 | 0.6400 | 3 | 5 | 4 | 8 |
| all_tools | AVB | 20 | 0.6000 | 0.5859 | 0.6154 | 0.7273 | 0.4444 | 0.6667 | 4 | 5 | 3 | 8 |
| all_tools | TC_REL | 20 | 0.8000 | 0.8571 | 0.6000 | 1.0000 | 0.7143 | 0.7500 | 10 | 4 | 0 | 6 |
| all_tools | TC_COUNT | 20 | 0.6500 | 0.6875 | 0.3333 | 0.7500 | 0.6250 | 0.4615 | 10 | 6 | 1 | 3 |
| all_tools | CC | 20 | 0.7500 | 0.7424 | 0.7500 | 0.8182 | 0.6667 | 0.7826 | 6 | 3 | 2 | 9 |

## TC breakdown notes

### by_temporal_type

| method | temporal_type | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| all_tools | relative_sync_count | 4 | 0.7500 | 0.8333 | 1 | 0 | 1 | 2 |
| all_tools | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| clap | relative_order | 12 | 0.5000 | 0.4857 | 3 | 3 | 2 | 4 |
| clap | relative_sync_count | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| clap | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe | relative_sync_count | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| mediapipe | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| mediapipe | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe_clap | relative_order | 12 | 0.5000 | 0.4857 | 3 | 3 | 2 | 4 |
| mediapipe_clap | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe_clap | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe_whisper | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| mediapipe_whisper | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe_whisper | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| no_tool | relative_order | 12 | 0.6667 | 0.6571 | 2 | 2 | 3 | 5 |
| no_tool | relative_sync_count | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| no_tool | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| whisper | relative_sync_count | 4 | 0.5000 | 0.3333 | 1 | 1 | 0 | 2 |
| whisper | relative_order | 12 | 0.7500 | 0.7571 | 2 | 1 | 4 | 5 |
| whisper | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| whisper_clap | relative_order | 12 | 0.6667 | 0.6857 | 3 | 1 | 4 | 4 |
| whisper_clap | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| whisper_clap | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_modality_combination

| method | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | Action (silent) + Action (sounding) | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| all_tools | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 1 | 0 | 2 | 1 |
| all_tools | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| all_tools | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| clap | Action (silent) + Action (sounding) | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| clap | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 0 | 1 | 1 | 2 |
| clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |
| clap | Speech + Action (sounding) | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe | Action (silent) + Action (sounding) | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| mediapipe | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.8333 | 2 | 0 | 2 | 4 |
| mediapipe | Speech + Action (sounding) | 4 | 0.7500 | 0.8333 | 1 | 0 | 1 | 2 |
| mediapipe | Speech + Action (silent) | 4 | 1.0000 | 1.0000 | 0 | 0 | 2 | 2 |
| mediapipe_clap | Action (silent) + Action (sounding) | 4 | 0.2500 | 0.1667 | 2 | 1 | 0 | 1 |
| mediapipe_clap | Speech + Action (silent) | 4 | 0.5000 | 0.5000 | 0 | 2 | 0 | 2 |
| mediapipe_clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |
| mediapipe_clap | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| mediapipe_whisper | Action (silent) + Action (sounding) | 4 | 0.2500 | 0.1667 | 2 | 1 | 0 | 1 |
| mediapipe_whisper | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| mediapipe_whisper | Speech + Action (silent) | 4 | 1.0000 | 1.0000 | 0 | 0 | 2 | 2 |
| mediapipe_whisper | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| no_tool | Action (silent) + Action (sounding) | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| no_tool | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 0 | 1 | 1 | 2 |
| no_tool | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.7500 | 0 | 1 | 1 | 6 |
| no_tool | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| whisper | Action (silent) + Action (sounding) | 4 | 0.5000 | 0.3333 | 1 | 1 | 0 | 2 |
| whisper | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 1 | 0 | 2 | 1 |
| whisper | Speech + Action (sounding) | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| whisper | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| whisper_clap | Action (silent) + Action (sounding) | 4 | 0.2500 | 0.1667 | 2 | 1 | 0 | 1 |
| whisper_clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_temporal_type_x_modality_combination

| method | temporal_type | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | Action (silent) + Action (sounding) | 2 | 0.0000 | 0.0000 | 2 | 0 | 0 | 0 |
| all_tools | relative_sync_count | Speech + Action (silent) | 1 | 0.0000 | 0.0000 | 1 | 0 | 0 | 0 |
| all_tools | relative_order | Speech + Action (silent) + Action (sounding) | 6 | 0.8333 | 0.8750 | 1 | 0 | 2 | 3 |
| all_tools | relative_order | Speech + Action (silent) | 2 | 1.0000 | 1.0000 | 0 | 0 | 2 | 0 |
| all_tools | relative_order | Speech + Action (sounding) | 2 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 |
| all_tools | relative_sync_count | Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 1 | 0 |
| all_tools | relative_sync_count | Speech + Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| all_tools | relative_sync_count | Speech + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| all_tools | relative_synchronization | Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| all_tools | relative_synchronization | Speech + Action (silent) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| all_tools | relative_synchronization | Speech + Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| all_tools | relative_synchronization | Speech + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_order | Action (silent) + Action (sounding) | 2 | 0.0000 | 0.0000 | 2 | 0 | 0 | 0 |
| clap | relative_order | Speech + Action (silent) | 2 | 0.5000 | 0.5000 | 0 | 1 | 1 | 0 |
| clap | relative_order | Speech + Action (sounding) | 2 | 0.5000 | 0.5000 | 0 | 1 | 0 | 1 |
| clap | relative_order | Speech + Action (silent) + Action (sounding) | 6 | 0.6667 | 0.6250 | 1 | 1 | 1 | 3 |
| clap | relative_sync_count | Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 1 | 0 |
| clap | relative_sync_count | Speech + Action (silent) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_sync_count | Speech + Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_sync_count | Speech + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_synchronization | Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_synchronization | Speech + Action (silent) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_synchronization | Speech + Action (silent) + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| clap | relative_synchronization | Speech + Action (sounding) | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| mediapipe | relative_order | Action (silent) + Action (sounding) | 2 | 0.0000 | 0.0000 | 2 | 0 | 0 | 0 |
| mediapipe | relative_sync_count | Speech + Action (silent) + Action (sounding) | 1 | 0.0000 | 0.0000 | 1 | 0 | 0 | 0 |
| mediapipe | relative_sync_count | Speech + Action (sounding) | 1 | 0.0000 | 0.0000 | 1 | 0 | 0 | 0 |
| mediapipe | relative_order | Speech + Action (silent) + Action (sounding) | 6 | 0.8333 | 0.8750 | 1 | 0 | 2 | 3 |
| mediapipe | relative_order | Speech + Action (silent) | 2 | 1.0000 | 1.0000 | 0 | 0 | 2 | 0 |
| mediapipe | relative_order | Speech + Action (sounding) | 2 | 1.0000 | 1.0000 | 0 | 0 | 1 | 1 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

## Recommended reading order

1. `method_ranking.csv`: decide which method is best under a TC-first criterion.
2. `tc_breakdown_by_temporal_type.csv`: check whether synchronization, order, count, or absolute timing drives differences.
3. `tc_method_disagreement_cases.csv`: inspect cases where tool options disagree.
4. `qualitative_examples.md` and `details/*.txt`: read model reasons/evidence for TP/TN/FP/FN examples.
