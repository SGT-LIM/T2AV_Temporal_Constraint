#!/bin/bash -l
# Replaced by t2av_eval/evidence/captions_gen (t2av-eval evidence captions); this copy is kept to reproduce the 10/30-11/02 caption runs.
# AVoCaDO captions for the 149 generated holdout videos; same settings as the cached 220 captions (fps 8, plain, no pixel cap).
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)  # legacy path root (legacy/README.md): outputs go to legacy/evaluation/ablation/captions/, never the main checkout
module load miniconda ffmpeg/8.1
conda activate /projectnb/ivc-ml/youngsun/conda_envs/qwen3_cap
export OMP_NUM_THREADS=4 HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache
cd $LEGACY_CODE
echo "host $(hostname) $(date)"; nvidia-smi --query-gpu=name,memory.total --format=csv
python -u run_qwen3_captions.py --backend avocado --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/videos --output-json captions/avocado_fps8_plain_v3_gen149.json --fps 8 --caption-style plain > captions/avocado_fps8_plain_v3_gen149.log 2>&1
echo "captions done $(date)"
