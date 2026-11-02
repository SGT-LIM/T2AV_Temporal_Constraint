#!/bin/bash
# Replaced by t2av_eval/evidence/captions_gen (t2av-eval evidence captions); this copy is kept to reproduce the 10/30-11/02 caption runs.
# AVoCaDO captions on an 80 GB A100 (10/30). Usage: avocado_a100_1030_job.sh greedy149 | sample <seed>
# greedy149: the 149 caption used by today's rows (same settings as the 220 captions: fps 8, plain, greedy).
# sample <seed>: one sampled caption per video (T2AV_CAPTION_SAMPLE_SEED, temperature 0.7, top_p 0.9) on the 220 and 149,
#                for the later tool screening table only.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)  # legacy path root (legacy/README.md): outputs go to legacy/evaluation/ablation/captions/, never the main checkout
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/qwen3_cap/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH   # absolute env (no module/conda in qrsh shells)
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}   # as module load ffmpeg/8.1
export OMP_NUM_THREADS=4 HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache
cd $LEGACY_CODE
# 11/01 thread caps: SCC killed CLAP job 8382945 for 3.7 cores on 1 slot. Threads = granted slots (-pe omp 4 -> 4).
T=${NSLOTS:-4}; export OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T OPENBLAS_NUM_THREADS=$T NUMBA_NUM_THREADS=$T TOKENIZERS_PARALLELISM=false
exec < /dev/null   # 11/01: ffmpeg children must not read the qrsh terminal
echo "host $(hostname) $(date)"; nvidia-smi --query-gpu=name,memory.total --format=csv
MIN3=/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3
V149=/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/videos
cap() { python -u run_qwen3_captions.py --backend avocado --videos-dir $1 --output-json $2 --fps 8 --caption-style plain > ${2%.json}.log 2>&1; echo "done $2 $(date)"; }
if [ "$1" = hdmove ]; then
  # 11/01: the 142 P01/P02 movement-set test items (HD-EPIC main table row 2), same settings as the P01/P02 captions (fps 2, plain)
  python -u run_qwen3_captions.py --backend avocado --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_main_1101/hdmove_p12 \
      --output-json captions/avocado_fps2_plain_v3_hdmove_p12.json --fps 2 --caption-style plain > captions/avocado_fps2_plain_v3_hdmove_p12.log 2>&1
  echo "done captions/avocado_fps2_plain_v3_hdmove_p12.json $(date)"
elif [ "$1" = p3p9 ]; then
  # 10/31: the 865 P03-P09 clips (383 originals + 482 audio-shifted), same settings as the P01/P02 HD-EPIC captions (fps 2, plain)
  python -u run_qwen3_captions.py --backend avocado --videos-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/clips865_1031 \
      --output-json captions/avocado_fps2_plain_v3_hdepic_p3p9_clips.json --fps 2 --caption-style plain > captions/avocado_fps2_plain_v3_hdepic_p3p9_clips.log 2>&1
  echo "done captions/avocado_fps2_plain_v3_hdepic_p3p9_clips.json $(date)"
elif [ "$1" = greedy149 ]; then
  cap $V149 captions/avocado_fps8_plain_v3_gen149.json
else
  export T2AV_CAPTION_SAMPLE_SEED=$2
  cap $V149 captions/avocado_fps8_plain_v3_gen149_s$2.json
  cap $MIN3/LTX_2p3 captions/avocado_fps8_plain_v3_LTX_2p3_s$2.json
  cap $MIN3/MOVA captions/avocado_fps8_plain_v3_MOVA_s$2.json
fi
