LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
cd $LEGACY_CODE
module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval
export GEMINI_API_KEY=$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache PYTHONUTF8=1 LC_ALL=C.UTF-8
export E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval D=/projectnb/ivc-ml/youngsun/T2AV_data
export R=$LROOT/eval_results
export P=$LROOT/new_prompts/generated/relative_500_v5_fixed.json
export G=gepa_stage2 V=/projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/min3_gt/gt_video.csv
export T2AV_DELETE_UPLOADS=1   # 11/02 (user): delete each uploaded Gemini File after its call succeeded (new_eval.maybe_delete_upload)
