#!/bin/bash
# Media-only (anchor) reruns rep2/rep3 on the v3 test videos (HD-EPIC) and the 220 test (LTX_2p3, MOVA).
# Same command as the anchors: hdepic_{medium,regen,move}_multi_baseline_g36 (10/16, 10/25) and baseline_min3_g36_1027 (10/27).
# usage: bash gepa_stage2/launch_anchor_reps_1028.sh dry|run
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -euo pipefail
MODE=${1:-dry}
CODE=$LEGACY_CODE
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
T=$E/hdepic_v3test_1028                                   # test-only symlinks (medium 199 = hdepic non-regen 183 + hdfoot 16, regen 122, move 142)
T220=/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3_test1027
R=$LROOT/eval_results/multi_agent
P220=$LROOT/new_prompts/generated/relative_500_v5_fixed.json
COMMON="--axes all --model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
ENVS="module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval; cd $CODE; export GEMINI_API_KEY=\$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"

# name|outdir|prompt_json|videos_dir|csv_stem|start|end   (end empty = to the end)
JOBS=()
for REP in rep2 rep3; do
  D=$E/results/hdepic_medium_multi_baseline_g36_${REP}_1028
  JOBS+=("$D|$E/hdepic_medium_prompts.json|$T/medium|shard0|0|67" "$D|$E/hdepic_medium_prompts.json|$T/medium|shard1|67|134" "$D|$E/hdepic_medium_prompts.json|$T/medium|shard2|134|")
  D=$E/results/hdepic_regen_multi_baseline_g36_${REP}_1028
  JOBS+=("$D|$E/hdepic_medium_prompts_v2.json|$T/regen|shard0|0|61" "$D|$E/hdepic_medium_prompts_v2.json|$T/regen|shard1|61|")
  D=$E/results/hdepic_move_multi_baseline_g36_${REP}_1028
  JOBS+=("$D|$E/hdepic_move_prompts.json|$T/move|shard0|0|71" "$D|$E/hdepic_move_prompts.json|$T/move|shard1|71|")
  D=$R/baseline_min3_g36_${REP}_1028
  JOBS+=("$D|$P220|$T220/LTX_2p3|LTX_2p3|0|" "$D|$P220|$T220/MOVA|MOVA|0|")
done

# refuse if any output dir already exists (never overwrite)
for j in "${JOBS[@]}"; do IFS='|' read -r OUT _ <<< "$j"; [ -e "$OUT" ] && { echo "EXISTS, abort: $OUT"; exit 1; }; done

START=$(date -Iseconds)
GITH=$(cd $CODE && git rev-parse --short HEAD)
HASHES=$(cd $CODE && md5sum run_agentic_eval.py agentic_common.py new_eval.py axis_*.py)
declare -A SEEN
for j in "${JOBS[@]}"; do
  IFS='|' read -r OUT PJ VD STEM S EN <<< "$j"
  RANGE="--start-index $S"; [ -n "$EN" ] && RANGE="$RANGE --end-index $EN"
  CMD="python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $VD --output-csv $OUT/$STEM.csv $COMMON $RANGE"
  FULL="nohup bash -c \"$ENVS; $CMD\" > $OUT/$STEM.log 2>&1 &"
  echo "$FULL"; echo
  [ "$MODE" = run ] || continue
  mkdir -p "$OUT"
  if [ -z "${SEEN[$OUT]:-}" ]; then
    SEEN[$OUT]=1
    cat > "$OUT/README.md" <<EOF
# Media-only anchor rerun ($(basename $OUT))

- purpose: media-only (audio+video, no tool evidence) anchor repeat for noise floor / 3-way agreement (pipeline v4 step 2)
- model: gemini-3.6-flash
- thinking: high
- media input: video (original audio included), media_fps 24 (default)
- evidence: pose none, audio none, caption none
- prompt version: in-code prompts of run_agentic_eval.py / agentic_common.py / new_eval.py / axis_*.py at git $GITH (md5 below); prompt json: $PJ (md5 $(md5sum $PJ | cut -c1-32))
- cache versions: no tool caches used (all evidence modes none)
- videos: $VD (test-only symlinks; manifest gepa_stage2/manifests_v3/test.jsonl)
- start time: $START
- launcher: gepa_stage2/launch_anchor_reps_1028.sh
- reproduces: $(case $OUT in *medium*) echo "$E/results/hdepic_medium_multi_baseline_g36 (10/16)";; *regen*) echo "$E/results/hdepic_regen_multi_baseline_g36 (10/25)";; *move*) echo "$E/results/hdepic_move_multi_baseline_g36 (10/25)";; *) echo "$R/baseline_min3_g36_1027 (10/27) and baseline_min3_g36/rep1 (10/16)";; esac)

## code md5
\`\`\`
$HASHES
\`\`\`

## commands
EOF
  fi
  printf '```\n%s\n```\n' "$FULL" >> "$OUT/README.md"
  nohup bash -c "$ENVS; $CMD" > "$OUT/$STEM.log" 2>&1 &
done
