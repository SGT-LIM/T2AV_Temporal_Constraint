#!/bin/bash
# P03-P09 HOLDOUT, AVB shift_early / shift_late + their originals (785 items): same-day media-only anchor, run on scc1 (login node).
# usage (on scc1): bash launch_holdout_avb_anchor_1030.sh dry|run
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -euo pipefail
MODE=${1:-dry}
CODE=$LEGACY_CODE
HO=/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028
SUB=$HO/eval_avb_subset_1030; PJ=$HO/prompts_hdepic_p3p9.json
OUT=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_holdout_p3p9_AVB_baseline_g36_1030
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
CAPS="export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; $CAPS; export GEMINI_API_KEY=\$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"
if [ -e "$OUT/README.md" ]; then echo "EXISTS, abort: $OUT"; exit 1; fi
NS=12; N=$(ls $SUB | wc -l); H=$(( (N + NS - 1) / NS )); ANC=""
for k in $(seq 0 $((NS - 1))); do
  R="--start-index $((k * H))"; if [ $k -lt $((NS - 1)) ]; then R="$R --end-index $(((k + 1) * H))"; fi
  C="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $SUB --output-csv $OUT/shard$k.csv --axes all $COMMON $R > $OUT/shard$k.log 2>&1"
  echo "[holdout_avb_anchor] $C"; ANC+="$C & "
done
[ "$MODE" = run ] || exit 0
mkdir -p $OUT
printf "# hdepic_holdout_p3p9_AVB_baseline_g36_1030 (HOLDOUT, same-day anchor for the Synchformer rule check)\n- model gemini-3.6-flash; thinking high; media_fps 24; evidence none; axes all\n- items %s (%s: shift_early 248, shift_late 234, originals 303); prompt json %s\n- start %s on %s; thread caps: %s\n- commands: %s\n" "$SUB" "$N" "$PJ" "$(date -Iseconds)" "$(hostname)" "$CAPS" "$ANC" > $OUT/README.md
screen -dmS holdout_avb_anchor bash -c "$ENVS; $ANC wait; echo done; exec bash"
screen -ls | grep holdout_avb
