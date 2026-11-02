#!/bin/bash
# Replaced by t2av_eval/evidence/captions_gen (t2av-eval evidence captions); this copy is kept to reproduce the 10/30-11/02 caption runs.
# 10/31 fallback: AVoCaDO on a 46 GB RTX A6000 at the unchanged settings (peak 19.6-20.4 GB in the 5-clip test, 0 errors).
# Usage: avocado_a6000_fallback_1031.sh <shard 0|1>   (865 P03-P09 clips split in 2; shard 1 then also does the 149)
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)  # legacy path root (legacy/README.md): outputs go to legacy/evaluation/ablation/captions/, never the main checkout
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/qwen3_cap/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}   # as module load ffmpeg/8.1
export OMP_NUM_THREADS=2 HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd $LEGACY_CODE
V=/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/clips865_1031
if [ $1 = 0 ]; then S=0; E=433; else S=433; E=865; fi
echo "shard $1 start $(date '+%F %H:%M') on $(hostname) GPU $CUDA_VISIBLE_DEVICES"
python -u run_qwen3_captions.py --backend avocado --videos-dir $V --output-json captions/avocado_fps2_plain_v3_hdepic_p3p9_clips_a6000_s$1.json \
    --fps 2 --caption-style plain --start-index $S --end-index $E > captions/avocado_fps2_plain_v3_hdepic_p3p9_clips_a6000_s$1.log 2>&1
echo "p3p9 shard $1 done $(date '+%F %H:%M'): $(grep -c ERROR captions/avocado_fps2_plain_v3_hdepic_p3p9_clips_a6000_s$1.log) errors"
if [ $1 = 1 ]; then
  python -u run_qwen3_captions.py --backend avocado --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/videos \
      --output-json captions/avocado_fps8_plain_v3_gen149_a6000.json --fps 8 --caption-style plain > captions/avocado_fps8_plain_v3_gen149_a6000.log 2>&1
  echo "149 done $(date '+%F %H:%M'): $(grep -c ERROR captions/avocado_fps8_plain_v3_gen149_a6000.log) errors"
fi
