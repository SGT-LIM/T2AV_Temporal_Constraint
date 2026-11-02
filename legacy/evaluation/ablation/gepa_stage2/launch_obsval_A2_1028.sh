#!/bin/bash
# Task 6 set A2 (mute_anchor 78 + shams 72 + originals 78 = 228 A rows), same day as sets B/C (10/28).
#   obsv_A2_anchor : media-only anchor, axis A, 3 shards        run_agentic_eval --axes a
#   obsv_A2_obs    : waits for '[DONE] processed=' in the 3 anchor logs, then audio_only / flam_text / panel_even / panel_peak
# usage: bash gepa_stage2/launch_obsval_A2_1028.sh dry|run
set -euo pipefail
MODE=${1:-dry}
CODE=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
MA=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/hdepic_mute_anchor_1028
OUT=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_mute_anchor_A_baseline_g36_obsval_1028
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
CAPS="export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 NUMBA_NUM_THREADS=4"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; $CAPS; export GEMINI_API_KEY=\$(cat ~/.gemini_key)"
if [ -e "$OUT/README.md" ]; then echo "EXISTS, abort: $OUT"; exit 1; fi
N=$(ls $MA/eval | wc -l); H=$(( (N + 2) / 3 ))
ANC=""; LOGS=""
for k in 0 1 2; do
  S=$((k * H)); RANGE="--start-index $S"; [ $k -lt 2 ] && RANGE="$RANGE --end-index $(( (k + 1) * H ))"
  CMD="python -u run_agentic_eval.py --prompt-json $MA/prompts.json --outputs-dir $MA/eval --output-csv $OUT/shard$k.csv --axes a $COMMON $RANGE > $OUT/shard$k.log 2>&1"
  echo "[obsv_A2_anchor] $CMD"; ANC+="$CMD & "; LOGS+="$OUT/shard$k.log "
done
L=gepa_stage2/runs/obsval_1028
OBS=""
for C in audio_only flam_text panel_even panel_peak; do
  OBS+="python -u gepa_stage2/obs_judge_1028.py run --set A2 --cond $C --workers 6 > $L/run_A2_$C.log 2>&1 & "
done
WAIT="for f in $LOGS; do until grep -q '^\[DONE\] processed=' \$f 2>/dev/null; do sleep 60; done; done"
echo "[obsv_A2_obs] (after the 3 anchor logs) $OBS wait"
[ "$MODE" = run ] || exit 0
mkdir -p $OUT
cat > $OUT/README.md <<EOR
# hdepic_mute_anchor_A_baseline_g36_obsval_1028 (Task 6 set A2, same-day media-only anchor)
- model: gemini-3.6-flash; thinking: high; media_fps 24; evidence none; axes: a
- items: $MA/prompts.json (228 rows: mute_anchor 78, sham 72, original 78); videos: $MA/eval
- start: $(date -Iseconds); launcher gepa_stage2/launch_obsval_A2_1028.sh; thread caps: $CAPS
- commands: $ANC
EOR
screen -dmS obsv_A2_anchor bash -c "$ENVS; $ANC wait; echo done; exec bash"
screen -dmS obsv_A2_obs bash -c "$ENVS; sleep 60; $WAIT; $OBS wait; echo done; exec bash"
screen -ls | grep obsv
