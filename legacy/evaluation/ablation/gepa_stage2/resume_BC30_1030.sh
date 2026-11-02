#!/bin/bash
# Watch the B30 / C30 TCR chain running under old job 8343460. If it finishes there, do nothing. As soon as that job ends or its
# obsv_BC30 screens die (whichever first), relaunch the SAME commands from this job: unfinished anchor shards (run_agentic_eval
# skips items already in the CSV), then the 4 observation runs (calls already cached are skipped). New log names (_r); old logs kept.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
OLD=8343460
CODE=$LEGACY_CODE
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
SUB=$E/obsval_1028/BC30_medium_subset; OUT=$E/results/hdepic_medium_BC_baseline_g36_obsval_1030; PJ=$E/hdepic_medium_prompts.json
L=$LROOT/evaluation/ablation/gepa_stage2/runs/obsval_1028
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
OBS_SPECS="B30:synchformer_text B30:qwen_ts_text B30:qwen_plus_synchformer_text C30:qwen_ts_text"
obs_done() { for sc in $OBS_SPECS; do st=${sc%%:*}; c=${sc#*:}; grep -q "^\[DONE\] $c" $L/run_${st}_$c.log 2>/dev/null || grep -q "^\[DONE\] $c" $L/run_${st}_${c}_r.log 2>/dev/null || return 1; done; return 0; }
alive() { qstat -j $OLD >/dev/null 2>&1 && screen -ls | grep -v Dead | grep -q "obsv_BC30_anchor\|obsv_BC30_obs"; }
while true; do
  if obs_done; then echo "$(date +%H:%M) B30/C30 TCR finished under the old job; nothing to relaunch"; exit 0; fi
  alive || break
  sleep 30
done
echo "$(date +%H:%M) old job ended or BC30 screens died; relaunching from job $JOB_ID"
cd $CODE
N=$(ls $SUB | wc -l); H=$(( (N + 3) / 4 )); LOGS=""
for k in 0 1 2 3; do
  if grep -q '^\[DONE\] processed=' $OUT/shard$k.log 2>/dev/null; then continue; fi
  R="--start-index $((k * H))"; if [ $k -lt 3 ]; then R="$R --end-index $(((k + 1) * H))"; fi
  C="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $SUB --output-csv $OUT/shard$k.csv --axes all $COMMON $R > $OUT/shard${k}_r.log 2>&1"
  echo "[relaunch anchor] $C"; printf -- "- relaunch %s (job %s): %s\n" "$(date -Iseconds)" "$JOB_ID" "$C" >> $OUT/README.md
  eval "$C &"; LOGS+="$OUT/shard${k}_r.log "
done
wait
for f in $LOGS; do grep -q '^\[DONE\] processed=' $f || { echo "anchor resume did not finish: $f"; exit 1; }; done
for sc in $OBS_SPECS; do st=${sc%%:*}; c=${sc#*:}
  C="python -u gepa_stage2/obs_judge_1028.py run --set $st --cond $c --workers 6 > $L/run_${st}_${c}_r.log 2>&1"
  echo "[relaunch obs] $C"; eval "$C &"
done
wait; echo "$(date +%H:%M) relaunched B30/C30 TCR finished"
