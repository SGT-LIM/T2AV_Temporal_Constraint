# SparseSync handoff: P01/P02 calibration set of the Synchformer AVB gate

This folder holds the exact items, input windows, labels and threshold procedure that set the current Synchformer AVB gate:
T = 1.8 s and P = .25 (`provenance/PREREGISTERED_RULE.json`, written 2026-10-30). Use it to calibrate SparseSync the same way.
It contains no video files. The P03–P09 test data are not included and must not be used for calibration.

## Contents

| file | content |
|---|---|
| `manifest.jsonl` | One line per item (110): item, video relpath, sha256 and size, labels, calibration role, binding events and Synchformer windows (details below). |
| `event_windows.csv` | One row per binding-event occurrence (153): action span, Synchformer input window, Synchformer reading, event GT. |
| `calibration_membership.csv` | One row per item: calibration membership, item-level Synchformer reading, `used_for_T`, `used_for_P`, `fires_at_rule`. |
| `hf_mapping.csv` | Item → Hugging Face path, with the HF LFS sha256 and size and the local sha256 (all 110 match). |
| `tools/calibrate_thresholds.py` | Portable: `reproduce` (rebuilds T and P from this folder), `verify` (checks local videos), `derive` (T and P for SparseSync readings). |
| `provenance/` | The original scripts (verbatim, with their BU SCC paths): `gate_b110_v2_1030.py` (threshold selection), `sync_action_1030.py` (Synchformer windows), `make_clips.py` (cuts and audio shifts), `sparsesync_handoff_1106.py` and `export_portable.py` (this export), plus `checks.json` (counts and md5 of all sources) and `hf_match_internal.csv`. |

Each line of `manifest.jsonl` holds:
- item id, participant, source video id and source clip window, variant, `audio_shift_s`
- `video_relpath`, `video_sha256`, size
- GT, calibration role, media-only verdict
- binding events with their per-occurrence action spans, Synchformer input windows and readings

## Videos: Hugging Face mapping (verified 2026-11-06)

**Dataset and layout**
- Dataset: `dghadiya/T2AV_TemporalConstraint_HDEPIC`, public, pinned revision `bc8e844b5e2b0f1bb77ac9c5f0c2f97e7c193e8b` (last modified 2026-09-26).
- Each item's video is at `videos/<item_id>/<item_id>_v1_raw.mp4` (`video_relpath` in the manifest).

**How identity was checked.** A matching filename was not taken as proof. Identity was checked by content:
- **Videos:** all 110 items are at that path at the pinned revision, and the HF LFS sha256 equals the sha256 of the clip used in the
  calibration run, for every item. That covers the 95 threshold-selection items (51 originals, 23 early, 21 late) and the 15 other
  items (7 / 6 / 2). There are no missing, ambiguous or mismatched items. No two items share a video file.
- **These are the files Synchformer read:** the local clips were last modified on 2026-09-14/15, before the Synchformer run of
  2026-10-30.
- **Metadata:** the dataset's `items_hdepic_medium_with_clips_v2.json`, `hdepic_medium_prompts.json` and `hdepic_medium_gt.csv`
  are byte-identical (md5) to the copies the calibration used. The clip windows, variants and `media.shift_s` of all 110 items agree.

**Download only the 110 calibration videos** (read-only; 0.31 GB in total):

```python
import json
from huggingface_hub import snapshot_download
rel = [json.loads(l)["video_relpath"] for l in open("manifest.jsonl")]
root = snapshot_download("dghadiya/T2AV_TemporalConstraint_HDEPIC", repo_type="dataset",
                         revision="bc8e844b5e2b0f1bb77ac9c5f0c2f97e7c193e8b", allow_patterns=rel, local_dir="hdepic_videos")
```

**Point the tools at the videos and verify them:**

```bash
export T2AV_HDEPIC_VIDEO_ROOT=/path/to/hdepic_videos     # the directory that contains videos/
python tools/calibrate_thresholds.py verify --sha256      # expects: all 110 videos OK
```

On BU SCC the same files live under `T2AV_data/real_av/eval/hdepic_v3test_1028/medium/<item_id>/<item_id>_v1_raw.mp4`. That
directory has no `videos/` level, so link it as `<root>/videos`.

## Items and labels

- **Item set:** the 110 "B" AVB items of the P01/P02 v3 test split (HD-EPIC, real video): 58 originals, 29 early shifts, 23 late shifts.
- **Calibration rows:** 95 of the 110 (`in_calibration`). They are the items with a same-day media-only verdict.
  - The 51 originals set T; `used_for_T` marks them.
  - The 21 shifted items with |offset| > T set P; `used_for_P` marks them.
  - The 15 other items were read by Synchformer but not used. They were left out only because they had no verdict that day.
- **Labels:** an original is AVB PASS; a shifted item is AVB FAIL on its shifted sounding event.
  - `gt_row` / `gt_avb` per event come from the project's v3 GT manifest (`evaluation/ablation/gepa_stage2/manifests_v3/test.jsonl`).
  - These labels are not in the HF dataset.

## Shifts: magnitude and sign

- **Values:** `audio_shift_s` ∈ {−3.0, −2.5, −2.0, −1.5, +1.5, +2.0, +2.5, +3.0} s; originals 0.
  - Most are ±2.0 s: 22 early and 17 late.
- **Sign:** negative = audio EARLY (the sound plays before its action), positive = audio LATE.
- **Implementation:** `provenance/make_clips.py`, op `cut+audio_shift`.
  - The video is cut at [lo, hi] of the source; the audio is read from lo − shift.
  - The audio is padded with silence when that start is below 0, then trimmed to the clip length.
  - So video time t carries the source audio of time t − shift.
- **Synchformer readings use the same sign:** early shifts read negative offsets.

## Input windows

- **Tool and settings:** Synchformer checkpoint 24-01-04T16-39-21, tool synchformer-event-v4, mode `window_if_alone_multi`, margin 0.64 s.
- **Clips:** clip time 0 = start of the clip.
- **Spans:** per binding (sounding) event, each annotated visible occurrence gives an action span (`action_start_s`, `action_end_s`).
  These are annotation times; FLAM was not used.
- **Input window:** the segment Synchformer read for that span is `input_start_s`, `input_end_s`. Give SparseSync the same windows,
  or record where its input differs.

## Threshold selection (`provenance/gate_b110_v2_1030.py`)

1. **Per-event reading:** the occurrence with the lowest p(offset 0); ties go to the larger |offset|.
2. **Per-item reading:** the event with the largest |offset|; ties go to the higher probability.
3. **T:** the 95th percentile of |offset| over the 51 originals, rounded to the offset grid (0.2 s). Result: 1.8 s.
4. **P:** the 5th percentile of probability over the shifted calibration items with |offset| > T (21), rounded to 0.01. Result: .25.
5. **Rule:** the gate fires if |offset| ≥ T and probability ≥ P.
6. **Acceptance check:** at most round(0.05 × 51) = 3 originals that the media-only verdict judged correctly may be flipped. Result: 1.

`python tools/calibrate_thresholds.py reproduce` rebuilds all of these numbers from this folder (T 1.8, P .25, 25 fired,
1 broken original). For SparseSync, write one reading per row of `event_windows.csv` and run `derive --readings <csv> --grid <step>`.

## Not verified / caveats

- **HF dataset card:** the shift semantics above come from `make_clips.py` and the item metadata, not from the HF dataset card.
- **Offset range:** Synchformer's offsets end at ±2.0 s, so ±2.5 s and ±3.0 s shifts are not read at their true size. If SparseSync
  uses another offset grid or range, T must be rounded to that grid; the procedure does not say how to map between grids.
- **Media-only verdicts:** `media_only_anchor_verdict` (gemini-3.6-flash, 2026-10-30) is needed only for the acceptance check. It is
  a project output, not part of the HF dataset.
- **Licence:** the HF dataset's license and the HD-EPIC terms of use were not checked here.
