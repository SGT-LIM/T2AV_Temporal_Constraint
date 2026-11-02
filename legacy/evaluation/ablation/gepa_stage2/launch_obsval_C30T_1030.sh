#!/bin/bash
# 10/30 set C30T (TCC on the hdmove movement set, v3 test: count_off 69 + original 73): same-day media-only anchor on the
# 142 move items, then the two-stage qwen_ts_text observation (Qwen3-VL timestamps re-run 10/30, calibrated 5/8 exact).
# usage: bash gepa_stage2/launch_obsval_C30T_1030.sh dry|run
set -euo pipefail
MODE=${1:-dry}
CODE=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
VD=$E/hdepic_v3test_1028/move
OUT=$E/results/hdepic_move_TCC_baseline_g36_obsval_1030
PJ=$E/hdepic_move_prompts.json
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
CAPS="export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 NUMBA_NUM_THREADS=4"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; $CAPS; export GEMINI_API_KEY=\$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"
if [ -e "$OUT/README.md" ]; then echo "EXISTS, abort: $OUT"; exit 1; fi
N=$(ls $VD | wc -l); H=$(( (N + 3) / 4 )); ANC=""; LOGS=""
for k in 0 1 2 3; do
  R="--start-index $((k * H))"; if [ $k -lt 3 ]; then R="$R --end-index $(((k + 1) * H))"; fi
  C="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $VD --output-csv $OUT/shard$k.csv --axes all $COMMON $R > $OUT/shard$k.log 2>&1"
  echo "[obsv_C30T_anchor] $C"; ANC+="$C & "; LOGS+="$OUT/shard$k.log "
done
L=gepa_stage2/runs/obsval_1028
OBS="python -u gepa_stage2/obs_judge_1028.py run --set C30T --cond qwen_ts_text --workers 6 > $L/run_C30T_qwen_ts_text.log 2>&1"
echo "[obsv_C30T_obs] (after the 4 anchor logs) $OBS"
WAIT="for f in $LOGS; do until grep -q '^\[DONE\] processed=' \$f 2>/dev/null; do sleep 30; done; done"
[ "$MODE" = run ] || exit 0
mkdir -p $OUT
printf "# hdepic_move_TCC_baseline_g36_obsval_1030 (same-day anchor for set C30T)\n- model gemini-3.6-flash; thinking high; media_fps 24; evidence none; axes all\n- items: %s (%s v3-test move items)\n- prompt json %s (md5 %s)\n- start %s; launcher gepa_stage2/launch_obsval_C30T_1030.sh; thread caps: %s\n- commands: %s\n- observation (screen obsv_C30T_obs, after the 4 anchor logs): %s\n" \
  "$VD" "$N" "$PJ" "$(md5sum $PJ | cut -c1-32)" "$(date -Iseconds)" "$CAPS" "$ANC" "$OBS" > $OUT/README.md
screen -dmS obsv_C30T_anchor bash -c "$ENVS; $ANC wait; echo done; exec bash"
screen -dmS obsv_C30T_obs bash -c "$ENVS; sleep 60; $WAIT; $OBS; echo done; exec bash"
screen -ls | grep obsv_C30T
