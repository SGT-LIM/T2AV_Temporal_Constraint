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
| 1 | all_tools | 0.8750 | 0.8182 | 0.7500 | 4 | 0 | 0.6786 | 0.6944 |
| 2 | mediapipe | 0.8438 | 0.7727 | 0.7059 | 5 | 0 | 0.6479 | 0.6411 |
| 3 | mediapipe_whisper | 0.8229 | 0.8182 | 0.7143 | 3 | 1 | 0.5939 | 0.6418 |
| 4 | no_tool | 0.7708 | 0.8182 | 0.6667 | 2 | 2 | 0.6303 | 0.6645 |
| 5 | whisper_clap | 0.7396 | 0.7727 | 0.6154 | 3 | 2 | 0.6400 | 0.7103 |
| 6 | whisper | 0.7083 | 0.7273 | 0.5714 | 4 | 2 | 0.6206 | 0.6641 |
| 7 | clap | 0.6562 | 0.7273 | 0.5000 | 3 | 3 | 0.5370 | 0.5653 |
| 8 | mediapipe_clap | 0.5667 | 0.6667 | 0.3636 | 3 | 4 | 0.4659 | 0.4881 |

## Axis-level summary

| method | axis | n | accuracy | balanced_accuracy | precision | positive_recall | negative_recall | f1 | tn | fp | fn | tp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| no_tool | A | 22 | 0.7273 | 0.6250 | 0.9375 | 0.7500 | 0.5000 | 0.8333 | 1 | 1 | 5 | 15 |
| no_tool | V | 22 | 0.5000 | 0.5190 | 0.7000 | 0.4667 | 0.5714 | 0.5600 | 4 | 3 | 8 | 7 |
| no_tool | AVB | 22 | 0.5909 | 0.6026 | 0.7000 | 0.5385 | 0.6667 | 0.6087 | 6 | 3 | 6 | 7 |
| no_tool | TC_REL | 22 | 0.8182 | 0.7708 | 0.6667 | 0.6667 | 0.8750 | 0.6667 | 14 | 2 | 2 | 4 |
| no_tool | TC_COUNT | 21 | 0.7143 | 0.6062 | 0.4000 | 0.4000 | 0.8125 | 0.4000 | 13 | 3 | 3 | 2 |
| no_tool | CC | 22 | 0.6364 | 0.6581 | 0.7778 | 0.5385 | 0.7778 | 0.6364 | 7 | 2 | 6 | 7 |
| mediapipe | A | 22 | 0.8182 | 0.9000 | 1.0000 | 0.8000 | 1.0000 | 0.8889 | 2 | 0 | 4 | 16 |
| mediapipe | V | 22 | 0.5909 | 0.5095 | 0.6875 | 0.7333 | 0.2857 | 0.7097 | 2 | 5 | 4 | 11 |
| mediapipe | AVB | 22 | 0.5909 | 0.5684 | 0.6429 | 0.6923 | 0.4444 | 0.6667 | 4 | 5 | 4 | 9 |
| mediapipe | TC_REL | 22 | 0.7727 | 0.8438 | 0.5455 | 1.0000 | 0.6875 | 0.7059 | 11 | 5 | 0 | 6 |
| mediapipe | TC_COUNT | 21 | 0.6190 | 0.6125 | 0.3333 | 0.6000 | 0.6250 | 0.4286 | 10 | 6 | 2 | 3 |
| mediapipe | CC | 22 | 0.4545 | 0.4530 | 0.5455 | 0.4615 | 0.4444 | 0.5000 | 4 | 5 | 7 | 6 |
| whisper | A | 22 | 0.8182 | 0.6750 | 0.9444 | 0.8500 | 0.5000 | 0.8947 | 1 | 1 | 3 | 17 |
| whisper | V | 22 | 0.6364 | 0.5810 | 0.7333 | 0.7333 | 0.4286 | 0.7333 | 3 | 4 | 4 | 11 |
| whisper | AVB | 22 | 0.5455 | 0.5470 | 0.6364 | 0.5385 | 0.5556 | 0.5833 | 5 | 4 | 6 | 7 |
| whisper | TC_REL | 22 | 0.7273 | 0.7083 | 0.5000 | 0.6667 | 0.7500 | 0.5714 | 12 | 4 | 2 | 4 |
| whisper | TC_COUNT | 21 | 0.6667 | 0.6438 | 0.3750 | 0.6000 | 0.6875 | 0.4615 | 11 | 5 | 2 | 3 |
| whisper | CC | 22 | 0.5909 | 0.5684 | 0.6429 | 0.6923 | 0.4444 | 0.6667 | 4 | 5 | 4 | 9 |
| clap | A | 22 | 0.6364 | 0.5750 | 0.9286 | 0.6500 | 0.5000 | 0.7647 | 1 | 1 | 7 | 13 |
| clap | V | 22 | 0.4545 | 0.4857 | 0.6667 | 0.4000 | 0.5714 | 0.5000 | 4 | 3 | 9 | 6 |
| clap | AVB | 22 | 0.5000 | 0.5256 | 0.6250 | 0.3846 | 0.6667 | 0.4762 | 6 | 3 | 8 | 5 |
| clap | TC_REL | 22 | 0.7273 | 0.6562 | 0.5000 | 0.5000 | 0.8125 | 0.5000 | 13 | 3 | 3 | 3 |
| clap | TC_COUNT | 21 | 0.6190 | 0.5437 | 0.2857 | 0.4000 | 0.6875 | 0.3333 | 11 | 5 | 3 | 2 |
| clap | CC | 22 | 0.4545 | 0.4359 | 0.5385 | 0.5385 | 0.3333 | 0.5385 | 3 | 6 | 6 | 7 |
| mediapipe_whisper | A | 22 | 0.6364 | 0.3500 | 0.8750 | 0.7000 | 0.0000 | 0.7778 | 0 | 2 | 6 | 14 |
| mediapipe_whisper | V | 22 | 0.5455 | 0.5143 | 0.6923 | 0.6000 | 0.4286 | 0.6429 | 3 | 4 | 6 | 9 |
| mediapipe_whisper | AVB | 22 | 0.5909 | 0.5855 | 0.6667 | 0.6154 | 0.5556 | 0.6400 | 5 | 4 | 5 | 8 |
| mediapipe_whisper | TC_REL | 22 | 0.8182 | 0.8229 | 0.6250 | 0.8333 | 0.8125 | 0.7143 | 13 | 3 | 1 | 5 |
| mediapipe_whisper | TC_COUNT | 21 | 0.7143 | 0.7438 | 0.4444 | 0.8000 | 0.6875 | 0.5714 | 11 | 5 | 1 | 4 |
| mediapipe_whisper | CC | 22 | 0.5455 | 0.5470 | 0.6364 | 0.5385 | 0.5556 | 0.5833 | 5 | 4 | 6 | 7 |
| mediapipe_clap | A | 21 | 0.6190 | 0.7895 | 1.0000 | 0.5789 | 1.0000 | 0.7333 | 2 | 0 | 8 | 11 |
| mediapipe_clap | V | 21 | 0.3333 | 0.3214 | 0.5000 | 0.3571 | 0.2857 | 0.4167 | 2 | 5 | 9 | 5 |
| mediapipe_clap | AVB | 21 | 0.3810 | 0.3889 | 0.4444 | 0.3333 | 0.4444 | 0.3810 | 4 | 5 | 8 | 4 |
| mediapipe_clap | TC_REL | 21 | 0.6667 | 0.5667 | 0.4000 | 0.3333 | 0.8000 | 0.3636 | 12 | 3 | 4 | 2 |
| mediapipe_clap | TC_COUNT | 20 | 0.5000 | 0.3125 | 0.0000 | 0.0000 | 0.6250 |  | 10 | 6 | 4 | 0 |
| mediapipe_clap | CC | 21 | 0.4286 | 0.4167 | 0.5000 | 0.5000 | 0.3333 | 0.5000 | 3 | 6 | 6 | 6 |
| whisper_clap | A | 22 | 0.8636 | 0.4750 | 0.9048 | 0.9500 | 0.0000 | 0.9268 | 0 | 2 | 1 | 19 |
| whisper_clap | V | 22 | 0.5909 | 0.5857 | 0.7500 | 0.6000 | 0.5714 | 0.6667 | 4 | 3 | 6 | 9 |
| whisper_clap | AVB | 22 | 0.6364 | 0.6410 | 0.7273 | 0.6154 | 0.6667 | 0.6667 | 6 | 3 | 5 | 8 |
| whisper_clap | TC_REL | 22 | 0.7727 | 0.7396 | 0.5714 | 0.6667 | 0.8125 | 0.6154 | 13 | 3 | 2 | 4 |
| whisper_clap | TC_COUNT | 21 | 0.7619 | 0.7750 | 0.5000 | 0.8000 | 0.7500 | 0.6154 | 12 | 4 | 1 | 4 |
| whisper_clap | CC | 22 | 0.6364 | 0.6239 | 0.6923 | 0.6923 | 0.5556 | 0.6923 | 5 | 4 | 4 | 9 |
| all_tools | A | 22 | 0.7727 | 0.6500 | 0.9412 | 0.8000 | 0.5000 | 0.8649 | 1 | 1 | 4 | 16 |
| all_tools | V | 22 | 0.5909 | 0.5476 | 0.7143 | 0.6667 | 0.4286 | 0.6897 | 3 | 4 | 5 | 10 |
| all_tools | AVB | 22 | 0.5909 | 0.5684 | 0.6429 | 0.6923 | 0.4444 | 0.6667 | 4 | 5 | 4 | 9 |
| all_tools | TC_REL | 22 | 0.8182 | 0.8750 | 0.6000 | 1.0000 | 0.7500 | 0.7500 | 12 | 4 | 0 | 6 |
| all_tools | TC_COUNT | 21 | 0.6667 | 0.7125 | 0.4000 | 0.8000 | 0.6250 | 0.5333 | 10 | 6 | 1 | 4 |
| all_tools | CC | 22 | 0.7273 | 0.7179 | 0.7692 | 0.7692 | 0.6667 | 0.7692 | 6 | 3 | 3 | 10 |

## TC breakdown notes

### by_temporal_type

| method | temporal_type | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| all_tools | relative_sync_count | 4 | 0.7500 | 0.8333 | 1 | 0 | 1 | 2 |
| all_tools | absolute_order | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
| all_tools | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| clap | relative_order | 12 | 0.5000 | 0.4857 | 3 | 3 | 2 | 4 |
| clap | absolute_order | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
| clap | relative_sync_count | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| clap | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe | relative_sync_count | 4 | 0.5000 | 0.6667 | 2 | 0 | 1 | 1 |
| mediapipe | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| mediapipe | absolute_order | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
| mediapipe | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe_clap | relative_order | 12 | 0.5000 | 0.4857 | 3 | 3 | 2 | 4 |
| mediapipe_clap | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe_clap | absolute_order | 1 | 1.0000 | 1.0000 | 0 | 0 | 0 | 1 |
| mediapipe_clap | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| mediapipe_whisper | relative_order | 12 | 0.7500 | 0.7857 | 3 | 0 | 5 | 4 |
| mediapipe_whisper | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe_whisper | absolute_order | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
| mediapipe_whisper | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| no_tool | relative_order | 12 | 0.6667 | 0.6571 | 2 | 2 | 3 | 5 |
| no_tool | absolute_order | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
| no_tool | relative_sync_count | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| no_tool | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| whisper | absolute_order | 2 | 0.5000 | 0.5000 | 1 | 0 | 0 | 1 |
| whisper | relative_sync_count | 4 | 0.5000 | 0.3333 | 1 | 1 | 0 | 2 |
| whisper | relative_order | 12 | 0.7500 | 0.7571 | 2 | 1 | 4 | 5 |
| whisper | relative_synchronization | 4 | 1.0000 | 1.0000 | 0 | 0 | 0 | 4 |
| whisper_clap | relative_order | 12 | 0.6667 | 0.6857 | 3 | 1 | 4 | 4 |
| whisper_clap | relative_sync_count | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_modality_combination

| method | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | Action (silent) + Action (sounding) | 6 | 0.6667 | 0.8000 | 2 | 0 | 1 | 3 |
| all_tools | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 1 | 0 | 2 | 1 |
| all_tools | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| all_tools | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| clap | Action (silent) + Action (sounding) | 6 | 0.6667 | 0.8000 | 2 | 0 | 1 | 3 |
| clap | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 0 | 1 | 1 | 2 |
| clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |
| clap | Speech + Action (sounding) | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| mediapipe | Action (silent) + Action (sounding) | 6 | 0.6667 | 0.8000 | 2 | 0 | 1 | 3 |
| mediapipe | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.8333 | 2 | 0 | 2 | 4 |
| mediapipe | Speech + Action (sounding) | 4 | 0.7500 | 0.8333 | 1 | 0 | 1 | 2 |
| mediapipe | Speech + Action (silent) | 4 | 1.0000 | 1.0000 | 0 | 0 | 2 | 2 |
| mediapipe_clap | Action (silent) + Action (sounding) | 5 | 0.4000 | 0.2500 | 2 | 1 | 0 | 2 |
| mediapipe_clap | Speech + Action (silent) | 4 | 0.5000 | 0.5000 | 0 | 2 | 0 | 2 |
| mediapipe_clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |
| mediapipe_clap | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| mediapipe_whisper | Action (silent) + Action (sounding) | 6 | 0.5000 | 0.3000 | 2 | 1 | 0 | 3 |
| mediapipe_whisper | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| mediapipe_whisper | Speech + Action (silent) | 4 | 1.0000 | 1.0000 | 0 | 0 | 2 | 2 |
| mediapipe_whisper | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| no_tool | Action (silent) + Action (sounding) | 6 | 0.6667 | 0.8000 | 2 | 0 | 1 | 3 |
| no_tool | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 0 | 1 | 1 | 2 |
| no_tool | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.7500 | 0 | 1 | 1 | 6 |
| no_tool | Speech + Action (sounding) | 4 | 1.0000 | 1.0000 | 0 | 0 | 1 | 3 |
| whisper | Action (silent) + Action (sounding) | 6 | 0.5000 | 0.3000 | 2 | 1 | 0 | 3 |
| whisper | Speech + Action (silent) | 4 | 0.7500 | 0.7500 | 1 | 0 | 2 | 1 |
| whisper | Speech + Action (sounding) | 4 | 0.7500 | 0.5000 | 0 | 1 | 0 | 3 |
| whisper | Speech + Action (silent) + Action (sounding) | 8 | 0.8750 | 0.9167 | 1 | 0 | 2 | 5 |
| whisper_clap | Action (silent) + Action (sounding) | 6 | 0.5000 | 0.3000 | 2 | 1 | 0 | 3 |
| whisper_clap | Speech + Action (silent) + Action (sounding) | 8 | 0.7500 | 0.6667 | 1 | 1 | 1 | 5 |

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

### by_temporal_type_x_modality_combination

| method | temporal_type | modality_combination | n | accuracy | balanced_accuracy | fp | fn | tp | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all_tools | relative_order | Action (silent) + Action (sounding) | 2 | 0.0000 | 0.0000 | 2 | 0 | 0 | 0 |
| all_tools | relative_sync_count | Speech + Action (silent) | 1 | 0.0000 | 0.0000 | 1 | 0 | 0 | 0 |
| all_tools | relative_order | Speech + Action (silent) + Action (sounding) | 6 | 0.8333 | 0.8750 | 1 | 0 | 2 | 3 |
| all_tools | absolute_order | Action (silent) + Action (sounding) | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
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
| clap | absolute_order | Action (silent) + Action (sounding) | 2 | 1.0000 | 1.0000 | 0 | 0 | 0 | 2 |
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

Preview is sorted to surface weaker groups first. See the CSV files for the full table.

## Recommended reading order

1. `method_ranking.csv`: decide which method is best under a TC-first criterion.
2. `tc_breakdown_by_temporal_type.csv`: check whether synchronization, order, count, or absolute timing drives differences.
3. `tc_method_disagreement_cases.csv`: inspect cases where tool options disagree.
4. `qualitative_examples.md` and `details/*.txt`: read model reasons/evidence for TP/TN/FP/FN examples.
