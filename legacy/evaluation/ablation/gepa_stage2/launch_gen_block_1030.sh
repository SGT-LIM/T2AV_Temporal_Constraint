#!/bin/bash
# Generated-set block, 10/30. Judge gemini-3.6-flash, thinking high. Run on scc1 inside screen.
#   bash gepa_stage2/launch_gen_block_1030.sh smoke            # 1 video, row 1 settings, event_time_s check
#   bash gepa_stage2/launch_gen_block_1030.sh row1             # media-only anchor, event_time_s flag on (220 + 149)
#   bash gepa_stage2/launch_gen_block_1030.sh row3 220|149     # routing: A Whisper+FLAM, V caption, AVB/TCR/TCC media only
#   bash gepa_stage2/launch_gen_block_1030.sh row2 220|149     # one call, all tools + Synchformer section
#   bash gepa_stage2/launch_gen_block_1030.sh row2b            # row 2 with neutral tool wording, 220 only
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -u
module load miniconda ffmpeg/8.1 >/dev/null 2>&1
conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval
export GEMINI_API_KEY=$(cat ~/.gemini_key)
env | grep -q '^GEMINI_API_KEY=.' || { echo "GEMINI_API_KEY missing"; exit 1; }
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1
ABL=$LEGACY_CODE
RES=$LROOT/eval_results/multi_agent
REL500=$LROOT/new_prompts/generated/relative_500_v5_fixed.json
MIN3=/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3
G149=/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030
SYNC=/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_gen_1030/sync_sections_oncall.json
cd $ABL
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none"

readme() {  # dir, row description, extra lines
  local d=$1; mkdir -p $d
  [ -e $d/README.md ] && { echo "README exists in $d, not overwriting"; return; }
  {
    echo "# $(basename $d)"; echo; echo "- purpose: $2"
    echo "- model: gemini-3.6-flash; thinking: high; media: video with audio, media_fps 24"
    echo "- prompts: $REL500 (md5 $(md5sum < $REL500 | cut -c1-32)); $G149/prompts_gen149.json (md5 $(md5sum < $G149/prompts_gen149.json | cut -c1-32))"
    echo "- prompt version: in-code prompts at git $(git rev-parse --short HEAD) plus uncommitted 10/30 edits (md5 below)"
    echo "- start: $(date -Iseconds) on $(hostname)"; echo -e "$3"
    echo; echo '## code md5'; echo '```'; md5sum run_agentic_eval.py agentic_common.py new_eval.py axis_*.py caption_evidence.py; echo '```'
    echo; echo '## commands'; echo '```'
  } > $d/README.md
}

launch() {  # dir, tag, prompt json, videos dir, nshards, n videos, env prefix, extra args
  local d=$1 tag=$2 pj=$3 vd=$4 ns=$5 n=$6 envp=$7 extra=$8
  local step=$(( (n + ns - 1) / ns ))
  for k in $(seq 0 $((ns - 1))); do
    local s=$((k * step)) e=$(((k + 1) * step)); [ $e -gt $n ] && e=$n
    local out=$d/${tag}_shard$k.csv
    [ -e $out ] && { echo "exists, skipping: $out"; continue; }
    local cmd="$envp python -u run_agentic_eval.py --prompt-json $pj --outputs-dir $vd --output-csv $out --axes all $COMMON $extra --start-index $s --end-index $e"
    echo "$cmd > ${out%.csv}.log 2>&1 &" >> $d/README.md
    env $envp python -u run_agentic_eval.py --prompt-json $pj --outputs-dir $vd --output-csv $out --axes all $COMMON $extra \
        --start-index $s --end-index $e > ${out%.csv}.log 2>&1 &
  done
}

TOOLS220() { echo "--audio-evidence-mode whisper_flam --caption-evidence-mode external --caption-style plain --caption-external-json $LROOT/evaluation/ablation/captions/avocado_fps8_plain_v3_$1.json"; }
TOOLS149="--audio-evidence-mode whisper_flam --caption-evidence-mode external --caption-style plain --caption-external-json $LROOT/evaluation/ablation/captions/avocado_fps8_plain_v3_gen149.json"
MEDIA="--audio-evidence-mode none --caption-evidence-mode none"
ROUTE="--no-binding-tools --no-temporal-tools"
CACHE="T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"

case $1 in
smoke)
  d=$RES/gen_smoke_eventtime_g36_1030
  readme $d "smoke test of the event_time_s flag (1 video, row 1 settings)" "- flags: T2AV_EVENT_TIME_FIELD=1; evidence none"
  launch $d LTX_2p3 $REL500 $MIN3/LTX_2p3 1 1 "T2AV_EVENT_TIME_FIELD=1" "$MEDIA" ;;
row1)
  d=$RES/gen_row1_anchor_g36_1030
  readme $d "row 1: media-only anchor, all axes, structured event_time_s (V, AVB)" "- flags: T2AV_EVENT_TIME_FIELD=1\n- evidence: none (pose, audio, caption)\n- caches: none"
  launch $d LTX_2p3 $REL500 $MIN3/LTX_2p3 5 110 "T2AV_EVENT_TIME_FIELD=1" "$MEDIA"
  launch $d MOVA $REL500 $MIN3/MOVA 5 110 "T2AV_EVENT_TIME_FIELD=1" "$MEDIA"
  launch $d gen149 $G149/prompts_gen149.json $G149/videos 7 149 "T2AV_EVENT_TIME_FIELD=1" "$MEDIA" ;;
row3)
  d=$RES/gen_row3_routing_g36_1030
  readme $d "row 3: routing pre-Synchformer, one call per axis: A media+Whisper+FLAM, V media+caption, AVB/TCR/TCC media only" \
    "- flags: --no-binding-tools --no-temporal-tools; T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1\n- caches: audio_evidence_cache (whisper_flam, run_agentic_eval defaults, as tools_min3_g36_1027); AVoCaDO fps8 plain v3 captions"
  if [ $2 = 220 ]; then
    launch $d LTX_2p3 $REL500 $MIN3/LTX_2p3 5 110 "$CACHE" "$(TOOLS220 LTX_2p3) $ROUTE"
    launch $d MOVA $REL500 $MIN3/MOVA 5 110 "$CACHE" "$(TOOLS220 MOVA) $ROUTE"
  else
    launch $d gen149 $G149/prompts_gen149.json $G149/videos 7 149 "$CACHE" "$TOOLS149 $ROUTE"
  fi ;;
row2)
  d=$RES/gen_row2_onecall_sync_g36_1030
  readme $d "row 2: all tools in one call (tools_min3_g36_1027 command) plus the Synchformer section (AVB/TCR/TCC)" \
    "- flags: T2AV_SYNC_EVIDENCE_JSON=$SYNC; T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1\n- caches: audio_evidence_cache; AVoCaDO fps8 plain v3; synchformer_gen_1030 (anchor-time window)"
  if [ $2 = 220 ]; then
    launch $d LTX_2p3 $REL500 $MIN3/LTX_2p3 5 110 "$CACHE T2AV_SYNC_EVIDENCE_JSON=$SYNC" "$(TOOLS220 LTX_2p3)"
    launch $d MOVA $REL500 $MIN3/MOVA 5 110 "$CACHE T2AV_SYNC_EVIDENCE_JSON=$SYNC" "$(TOOLS220 MOVA)"
  else
    launch $d gen149 $G149/prompts_gen149.json $G149/videos 7 149 "$CACHE T2AV_SYNC_EVIDENCE_JSON=$SYNC" "$TOOLS149"
  fi ;;
row2b)
  d=$RES/gen_row2b_onecall_neutral_g36_1030
  readme $d "row 2b: row 2 with neutral tool wording (no 'primary expert' / 'MUST'; stage-2 OBS_RULES sentence verbatim), 220 only" \
    "- flags: T2AV_NEUTRAL_TOOL_WORDING=1; T2AV_SYNC_EVIDENCE_JSON=$SYNC; T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1"
  launch $d LTX_2p3 $REL500 $MIN3/LTX_2p3 5 110 "$CACHE T2AV_SYNC_EVIDENCE_JSON=$SYNC T2AV_NEUTRAL_TOOL_WORDING=1" "$(TOOLS220 LTX_2p3)"
  launch $d MOVA $REL500 $MIN3/MOVA 5 110 "$CACHE T2AV_SYNC_EVIDENCE_JSON=$SYNC T2AV_NEUTRAL_TOOL_WORDING=1" "$(TOOLS220 MOVA)" ;;
esac
echo '```' >> $d/README.md
wait
echo "[$1 ${2:-}] all shards exited $(date +%H:%M)"
