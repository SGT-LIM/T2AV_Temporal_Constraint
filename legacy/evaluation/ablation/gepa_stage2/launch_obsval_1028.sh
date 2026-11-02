#!/bin/bash
# Task 6 observation validation, all conditions on the same day (10/28). gemini-3.6-flash, thinking high.
# Prereqs (no API): obs_judge_1028.py rows --classes ... ; obs_judge_1028.py prep
# Screens:
#   obsv_anchor : same-day media-only anchor on the v3 test videos (B, C and D need it)      run_agentic_eval --axes all
#   obsv_A      : media-only anchor, axis A, on the mute_class subset (chosen classes x3 variants + excluded originals)
#   obsv_D      : V-only modality ablation, muted video, media-only prompt                     run_agentic_eval --axes v
#   obsv_obs    : waits for the anchors, then the two-stage observation calls (one process per condition)
# usage: bash gepa_stage2/launch_obsval_1028.sh dry|run [BCD]   (BCD: sets B, C, D only; set A anchor + observations held)
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -euo pipefail
MODE=${1:-dry}
ONLY=${2:-}
CODE=$LEGACY_CODE
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
T=$E/hdepic_v3test_1028
O=$E/obsval_1028
T220=/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3_test1027
R=$LROOT/eval_results/multi_agent
P220=$LROOT/new_prompts/generated/relative_500_v5_fixed.json
PMC=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/hdepic_mute_class_1028/prompts.json
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
CAPS="export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 NUMBA_NUM_THREADS=4"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; $CAPS; export GEMINI_API_KEY=\$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"

[ -s $LROOT/evaluation/ablation/gepa_stage2/runs/obsval_1028/rows.jsonl ] || { echo "run obs_judge_1028.py rows/prep first"; exit 1; }
NA=$( (ls $O/mute_eval_subset 2>/dev/null || true) | wc -l); NSA=6; HA=$(( (NA + NSA - 1) / NSA ))

# screen|outdir|prompt_json|videos_dir|csv_stem|axes|start|end
JOBS=(
 "obsv_anchor|$E/results/hdepic_medium_multi_baseline_g36_obsval_1028|$E/hdepic_medium_prompts.json|$T/medium|shard0|all|0|67"
 "obsv_anchor|$E/results/hdepic_medium_multi_baseline_g36_obsval_1028|$E/hdepic_medium_prompts.json|$T/medium|shard1|all|67|134"
 "obsv_anchor|$E/results/hdepic_medium_multi_baseline_g36_obsval_1028|$E/hdepic_medium_prompts.json|$T/medium|shard2|all|134|"
 "obsv_anchor|$E/results/hdepic_regen_multi_baseline_g36_obsval_1028|$E/hdepic_medium_prompts_v2.json|$T/regen|shard0|all|0|61"
 "obsv_anchor|$E/results/hdepic_regen_multi_baseline_g36_obsval_1028|$E/hdepic_medium_prompts_v2.json|$T/regen|shard1|all|61|"
 "obsv_anchor|$E/results/hdepic_move_multi_baseline_g36_obsval_1028|$E/hdepic_move_prompts.json|$T/move|shard0|all|0|71"
 "obsv_anchor|$E/results/hdepic_move_multi_baseline_g36_obsval_1028|$E/hdepic_move_prompts.json|$T/move|shard1|all|71|"
 "obsv_anchor|$R/baseline_min3_g36_obsval_1028|$P220|$T220/LTX_2p3|LTX_2p3|all|0|"
 "obsv_anchor|$R/baseline_min3_g36_obsval_1028|$P220|$T220/MOVA|MOVA|all|0|"
 "obsv_D|$E/results/hdepic_medium_V_muted_g36_obsval_1028|$E/hdepic_medium_prompts.json|$O/muted/medium|shard0|v|0|"
 "obsv_D|$E/results/hdepic_regen_V_muted_g36_obsval_1028|$E/hdepic_medium_prompts_v2.json|$O/muted/regen|shard0|v|0|"
 "obsv_D|$R/V_muted_min3_g36_obsval_1028|$P220|$O/muted/LTX_2p3|LTX_2p3|v|0|"
 "obsv_D|$R/V_muted_min3_g36_obsval_1028|$P220|$O/muted/MOVA|MOVA|v|0|"
)
for k in $(if [ "$ONLY" = BCD ]; then true; else seq 0 $((NSA - 1)); fi); do   # A anchor: 6 shards of the mute_class subset
  EN=$(( (k + 1) * HA )); [ $k -eq $((NSA - 1)) ] && EN=""
  JOBS+=("obsv_A|$E/results/hdepic_mute_class_A_baseline_g36_obsval_1028|$PMC|$O/mute_eval_subset|shard$k|a|$((k * HA))|$EN")
done
for j in "${JOBS[@]}"; do IFS='|' read -r _ OUT _ <<< "$j"; if [ -e "$OUT/README.md" ]; then echo "EXISTS, abort: $OUT"; exit 1; fi; done

START=$(date -Iseconds); GITH=$(cd $CODE && git rev-parse --short HEAD)
declare -A SEEN; declare -A SCR
for j in "${JOBS[@]}"; do
  IFS='|' read -r SC OUT PJ VD STEM AX S EN <<< "$j"
  RANGE="--start-index $S"; [ -n "$EN" ] && RANGE="$RANGE --end-index $EN"
  CMD="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $VD --output-csv $OUT/$STEM.csv --axes $AX $COMMON $RANGE > $OUT/$STEM.log 2>&1"
  SCR[$SC]+="$CMD & "
  echo "[$SC] $CMD"
  [ "$MODE" = run ] || continue
  mkdir -p "$OUT"
  if [ -z "${SEEN[$OUT]:-}" ]; then SEEN[$OUT]=1
    cat > "$OUT/README.md" <<EOF
# $(basename $OUT) (Task 6 observation validation, same-day run)
- model: gemini-3.6-flash; thinking: high; media_fps 24; evidence none (media only); axes: $AX
- media: $(case $OUT in *muted*) echo "video with the audio track removed (ffmpeg -an, video stream copied), V-only modality ablation";; *) echo "video with its original audio";; esac)
- prompt json: $PJ (md5 $(md5sum $PJ | cut -c1-32)); in-code prompts at git $GITH
- videos: $VD
- start: $START; launcher gepa_stage2/launch_obsval_1028.sh; thread caps: $CAPS
## commands
EOF
  fi
  printf '```\n%s\n```\n' "$CMD" >> "$OUT/README.md"
done

# observation calls: one process per condition, 6 threads each, after both anchors (obsv_anchor, obsv_A) have finished
ALOGS=""
for j in "${JOBS[@]}"; do IFS='|' read -r SC OUT _ _ STEM _ <<< "$j"; if [ "$SC" != obsv_D ]; then ALOGS+="$OUT/$STEM.log "; fi; done
WAIT="for f in $ALOGS; do until grep -q '^\[DONE\] processed=' \$f 2>/dev/null; do sleep 60; done; done"
OBSCMD=""
if [ "$ONLY" = BCD ]; then
  for SC in "B focus" "B panel_even" "B panel_peak" "C panel_even" "C panel_peak"; do read -r ST C <<< "$SC"
    OBSCMD+="python -u gepa_stage2/obs_judge_1028.py run --set $ST --cond $C --workers 6 > gepa_stage2/runs/obsval_1028/run_${ST}_$C.log 2>&1 & "
  done
else
  for C in audio_only flam_text panel_even panel_peak focus; do
    OBSCMD+="python -u gepa_stage2/obs_judge_1028.py run --cond $C --workers 6 > gepa_stage2/runs/obsval_1028/run_$C.log 2>&1 & "
  done
fi
echo "[obsv_obs] (after anchors) $OBSCMD wait"

[ "$MODE" = run ] || exit 0
for SC in obsv_anchor $([ "$ONLY" = BCD ] || echo obsv_A) obsv_D; do
  screen -dmS $SC bash -c "$ENVS; ${SCR[$SC]} wait; echo done; exec bash"
done
screen -dmS obsv_obs bash -c "$ENVS; sleep 120; $WAIT; $OBSCMD wait; echo done; exec bash"
screen -ls
