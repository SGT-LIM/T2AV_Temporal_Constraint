#!/bin/bash
# Replaced by t2av_eval/evidence/captions_gen (t2av-eval evidence captions); this copy is kept to reproduce the 10/30-11/02 caption runs.
# 11/01 fallback for the 142 movement-set captions on a 48 GB-class card (A6000 / L40S), -pe omp 4, unchanged settings (fps 2, plain,
# full frame, greedy), as the 10/31 A6000 fallback. Submitted only if A100 job 8382944 had not started by 14:00.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)  # legacy path root (legacy/README.md): outputs go to legacy/evaluation/ablation/captions/, never the main checkout
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/qwen3_cap/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}
export HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
T=${NSLOTS:-4}; export OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T OPENBLAS_NUM_THREADS=$T NUMBA_NUM_THREADS=$T TOKENIZERS_PARALLELISM=false
cd $LEGACY_CODE
exec < /dev/null
echo "host $(hostname) $(date)"; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python -u run_qwen3_captions.py --backend avocado --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_main_1101/hdmove_p12 \
    --output-json captions/avocado_fps2_plain_v3_hdmove_p12_fallback48g.json --fps 2 --caption-style plain > captions/avocado_fps2_plain_v3_hdmove_p12_fallback48g.log 2>&1
echo "done captions/avocado_fps2_plain_v3_hdmove_p12_fallback48g.json $(date)"
