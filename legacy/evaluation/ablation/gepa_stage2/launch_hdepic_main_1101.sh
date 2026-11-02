#!/bin/bash
# HD-EPIC main table (P01/P02 v3 test + P03-P09), started 11/01. Judge gemini-3.6-flash, thinking high. Run on scc1 in screen.
#   bash gepa_stage2/launch_hdepic_main_1101.sh smoke     # 1 item per prompt set, row 1 settings
#   bash gepa_stage2/launch_hdepic_main_1101.sh row1      # media-only anchor (30 shards)
#   bash gepa_stage2/launch_hdepic_main_1101.sh row2 ["sets"]   # one call: Whisper+FLAM (hop 5) + AVoCaDO caption + Synchformer section
# Prompt sets: hdepic_p12 (v2 prompts), hdfoot_p12 (old prompts), hdmove_p12 (movement prompts), p3p9 (holdout prompts).
# Videos: T2AV_data/real_av/eval/hdepic_main_1101/<set>/<item>/<item>_v1_raw.mp4 (symlinks to the existing files).
# Same-day rule dropped 11/01 (user): every README records the run date; cross-day comparisons are marked in the tables.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -u
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/t2av_eval/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}
export GEMINI_API_KEY=$(cat ~/.gemini_key)
env | grep -q '^GEMINI_API_KEY=.' || { echo "GEMINI_API_KEY missing"; exit 1; }
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1
ABL=$LEGACY_CODE
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval
V=$E/hdepic_main_1101
RES=$E/results
HO=/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028
declare -A PJ=([hdepic_p12]=$E/hdepic_medium_prompts_v2.json [hdfoot_p12]=$E/hdepic_medium_prompts.json
               [hdmove_p12]=$E/hdepic_move_prompts.json [p3p9]=$HO/prompts_hdepic_p3p9.json)
declare -A NS=([hdepic_p12]=3 [hdfoot_p12]=1 [hdmove_p12]=2 [p3p9]=24)
CAPJ=$E/hdepic_main_1101_captions          # per-set caption json keyed <item>/<item>_v1_raw.mp4 (row 2)
SYNC=/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030/hdepic_main_sync_sections_1101.json
cd $ABL
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none"

readme() {
  local d=$1; mkdir -p $d
  [ -e $d/README.md ] && { echo "README exists in $d, not overwriting"; return; }
  {
    echo "# $(basename $d)"; echo; echo "- purpose: $2"; echo "- run date: $(date +%F) (start $(date -Iseconds) on $(hostname))"
    echo "- model: gemini-3.6-flash; thinking: high; media: video with audio, media_fps 24"
    for s in "${!PJ[@]}"; do echo "- prompts $s: ${PJ[$s]} (md5 $(md5sum < ${PJ[$s]} | cut -c1-32))"; done
    echo "- videos: $V/<set>/ (P01/P02 v3 test items; P03-P09 items except fail_mute and order swaps failing the 1.0 s gap)"
    echo "- prompt version: in-code prompts at git $(git rev-parse --short HEAD) plus uncommitted edits (md5 below; flags off unless listed)"
    echo -e "$3"
    echo; echo '## code md5'; echo '```'; md5sum run_agentic_eval.py agentic_common.py new_eval.py axis_*.py caption_evidence.py; echo '```'
    echo; echo '## commands'; echo '```'
  } > $d/README.md
}

launch() {  # dir set n_items envprefix extra
  local d=$1 s=$2 n=$3 envp=$4 extra=$5 ns=${NS[$2]}
  local step=$(( (n + ns - 1) / ns ))
  for k in $(seq 0 $((ns - 1))); do
    local a=$((k * step)) b=$(((k + 1) * step)); [ $b -gt $n ] && b=$n
    local out=$d/${s}_shard$k.csv
    [ -e $out ] && { echo "exists, skipping: $out"; continue; }
    echo "$envp python -u run_agentic_eval.py --prompt-json ${PJ[$s]} --outputs-dir $V/$s --output-csv $out --axes all $COMMON $extra --start-index $a --end-index $b" >> $d/README.md
    env $envp python -u run_agentic_eval.py --prompt-json ${PJ[$s]} --outputs-dir $V/$s --output-csv $out --axes all $COMMON $extra \
        --start-index $a --end-index $b > ${out%.csv}.log 2>&1 &
  done
}

count() { ls $V/$1 | wc -l; }
MEDIA="--audio-evidence-mode none --caption-evidence-mode none"
case $1 in
smoke)
  d=$RES/hdepic_main_smoke_g36_1101
  readme $d "smoke test, row 1 settings, 1 item per prompt set" "- evidence: none"
  for s in hdepic_p12 hdfoot_p12 hdmove_p12 p3p9; do NS[$s]=1; launch $d $s 1 "X=1" "$MEDIA"; done ;;
row1)
  d=$RES/hdepic_main_row1_anchor_g36_1101
  readme $d "row 1: media-only anchor, all axes (stage 1 for rows 4 / 5)" "- evidence: none (pose, audio, caption)\n- caches: none\n- flags: none (T2AV_EVENT_TIME_FIELD off; the Synchformer window comes from the annotation)"
  for s in hdepic_p12 hdfoot_p12 hdmove_p12 p3p9; do launch $d $s $(count $s) "X=1" "$MEDIA"; done ;;
row2)
  d=$RES/hdepic_main_row2_onecall_sync_g36_1101
  readme $d "row 2: all tools in one call (as hdepic_medium_multi_tools_wf_hop5_g36) plus the Synchformer section (AVB/TCR/TCC)" \
    "- evidence: whisper_flam (FLAM hop 5), AVoCaDO fps2 plain (P01/P02: avocado_fps2_plain_v3_hdepic_items.json; P03-P09 and hdmove: A100 runs of 10/31-11/01), Synchformer action-window (synchformer_action_1030)\n- flags: T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1; T2AV_SYNC_EVIDENCE_JSON=$SYNC"
  SETS="${2:-hdepic_p12 hdfoot_p12 hdmove_p12 p3p9}"     # 11/01: partial start (the movement set is added when its inputs land)
  echo "- $(date -Iseconds): row2 sets: $SETS" >> $d/README.md
  for s in $SETS; do
    launch $d $s $(count $s) "T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 T2AV_SYNC_EVIDENCE_JSON=$SYNC" \
      "--audio-evidence-mode whisper_flam --flam-hop-sec 5 --caption-evidence-mode external --caption-style plain --caption-external-json $CAPJ/$s.json"
  done ;;
esac
echo '```' >> $d/README.md
wait
echo "[$1] all shards exited $(date '+%F %H:%M')"
