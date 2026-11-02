#!/bin/bash
# Replaced by t2av_eval/evidence/captions_gen (t2av-eval evidence captions); this copy is kept to reproduce the 10/30-11/02 caption runs.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)  # legacy path root (legacy/README.md): outputs go to legacy/evaluation/ablation/captions/, never the main checkout
until grep -q "hd_fps2_full_rep done" /projectnb/ivc-ml/youngsun/T2AV_data/avocado_memtest_1031/repeat.out 2>/dev/null; do sleep 15; done
CUDA_VISIBLE_DEVICES=2 bash $LEGACY_CODE/captions/avocado_a6000_fallback_1031.sh 1
