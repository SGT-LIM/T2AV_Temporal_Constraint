#!/bin/bash
# 10/30 sets B30 (AVB shift + originals, 110) and C30 TCR (61): same-day media-only anchor on the 138 unique items, then
# two-stage tool-text observations: B30 synchformer_text, qwen_ts_text, qwen_plus_synchformer_text; C30 TCR qwen_ts_text.
# usage: bash gepa_stage2/launch_obsval_BC30_1030.sh dry|run
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -euo pipefail
MODE=${1:-dry}
CODE=$LEGACY_CODE
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
SUB=$E/obsval_1028/BC30_medium_subset
OUT=$E/results/hdepic_medium_BC_baseline_g36_obsval_1030
PJ=$E/hdepic_medium_prompts.json
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
CAPS="export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 NUMBA_NUM_THREADS=4"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; $CAPS; export GEMINI_API_KEY=\$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"
if [ -e "$OUT/README.md" ]; then echo "EXISTS, abort: $OUT"; exit 1; fi
N=$(ls $SUB | wc -l); H=$(( (N + 3) / 4 )); ANC=""; LOGS=""
for k in 0 1 2 3; do
  R="--start-index $((k * H))"; if [ $k -lt 3 ]; then R="$R --end-index $(((k + 1) * H))"; fi
  C="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $SUB --output-csv $OUT/shard$k.csv --axes all $COMMON $R > $OUT/shard$k.log 2>&1"
  echo "[obsv_BC30_anchor] $C"; ANC+="$C & "; LOGS+="$OUT/shard$k.log "
done
L=gepa_stage2/runs/obsval_1028; OBS=""
for SC in "B30 synchformer_text" "B30 qwen_ts_text" "B30 qwen_plus_synchformer_text" "C30 qwen_ts_text"; do read -r ST C <<< "$SC"
  OBS+="python -u gepa_stage2/obs_judge_1028.py run --set $ST --cond $C --workers 6 > $L/run_${ST}_$C.log 2>&1 & "
done
echo "[obsv_BC30_obs] (after the 4 anchor logs) $OBS wait"
WAIT="for f in $LOGS; do until grep -q '^\[DONE\] processed=' \$f 2>/dev/null; do sleep 30; done; done"
[ "$MODE" = run ] || exit 0
mkdir -p $OUT
printf "# hdepic_medium_BC_baseline_g36_obsval_1030 (same-day anchor for sets B30 / C30 TCR)\n- model gemini-3.6-flash; thinking high; media_fps 24; evidence none; axes all\n- items: %s (%s items = B 110 + C TCR 61, 33 shared)\n- prompt json %s (md5 %s)\n- start %s; launcher gepa_stage2/launch_obsval_BC30_1030.sh; thread caps: %s\n- commands: %s\n- observations (screen obsv_BC30_obs, after the 4 anchor logs): %s\n" \
  "$SUB" "$N" "$PJ" "$(md5sum $PJ | cut -c1-32)" "$(date -Iseconds)" "$CAPS" "$ANC" "$OBS" > $OUT/README.md
screen -dmS obsv_BC30_anchor bash -c "$ENVS; $ANC wait; echo done; exec bash"
screen -dmS obsv_BC30_obs bash -c "$ENVS; sleep 60; $WAIT; $OBS wait; echo done; exec bash"
screen -ls | grep obsv_BC30
