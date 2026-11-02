#!/bin/bash
# 11/02: HD-EPIC AVB additions (eligible-class windows that overlap no existing window), rows 1 and 2, PACED.
#   bash gepa_stage2/launch_avbadd_1102.sh row1     # media-only anchor, all axes
#   bash gepa_stage2/launch_avbadd_1102.sh row2     # one call: Whisper+FLAM (hop 5, cache-only) + AVoCaDO caption + Synchformer section
# Pacing (user 11/01: stay under the quota that failed at 21:35 on 11/01): 11 shards at a time (P01/P02 3, P03-P09 8), about 2,700
# calls / hour. Watchdog: if a shard logs a 429 RESOURCE_EXHAUSTED error, every shard process of this run is killed (python children
# and this script's own subshells, not only the screen), the run waits 30 min, then relaunches; items already done are skipped
# (new_eval.already_done) and the newer row wins at scoring. At most 8 cycles. Run date and every cycle go to the README.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -u
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/t2av_eval/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}
export T2AV_DELETE_UPLOADS=1   # 11/02 (user): delete each uploaded Gemini File after its call succeeded (new_eval.maybe_delete_upload)
export GEMINI_API_KEY=$(cat ~/.gemini_key)
env | grep -q '^GEMINI_API_KEY=.' || { echo "GEMINI_API_KEY missing"; exit 1; }
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1
ABL=$LEGACY_CODE
A=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_avbadd_1102
RES=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results
declare -A NS=([p12]=3 [p3p9]=8)
cd $ABL
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none"
case $1 in
row1) D=$RES/hdepic_avbadd_row1_anchor_g36_1102; ENVP="X=1"; EXTRA() { echo "--audio-evidence-mode none --caption-evidence-mode none"; } ;;
row2) D=$RES/hdepic_avbadd_row2_onecall_sync_g36_1102; ENVP="T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 T2AV_SYNC_EVIDENCE_JSON=$A/sync_sections_avbadd.json"
      EXTRA() { echo "--audio-evidence-mode whisper_flam --flam-hop-sec 5 --caption-evidence-mode external --caption-style plain --caption-external-json $A/captions_$1.json"; } ;;
*) echo "usage: row1|row2"; exit 1 ;;
esac
mkdir -p $D
if [ ! -e $D/README.md ]; then
  { echo "# $(basename $D)"; echo; echo "- purpose: $1 for the HD-EPIC AVB additions (11/01 eligible-anchor rule: open / close, cut / chop, stir / mix / whisk; no collision class; windows that overlap no existing window; no loudness filter; >= 20 dB subset flagged in items_avbadd.json)"
    echo "- run date: $(date +%F) (start $(date -Iseconds) on $(hostname)); paced: 11 shards, 429 watchdog (30 min pause, <= 8 cycles)"
    echo "- model: gemini-3.6-flash; thinking: high; media: video with audio, media_fps 24; --axes all"
    for g in p12 p3p9; do echo "- prompts $g: $A/$g/prompts_avbadd.json (md5 $(md5sum < $A/$g/prompts_avbadd.json | cut -c1-32)); videos $A/$g/eval"; done
    echo "- code md5:"; echo '```'; md5sum run_agentic_eval.py agentic_common.py new_eval.py axis_*.py caption_evidence.py; echo '```'; echo "## commands / cycles"; } > $D/README.md
fi
pids=()
start() {
  pids=()
  for g in p12 p3p9; do
    n=$(ls $A/$g/eval | wc -l); ns=${NS[$g]}; st=$(( (n + ns - 1) / ns ))
    for k in $(seq 0 $((ns - 1))); do
      a=$((k * st)); b=$(((k + 1) * st)); [ $b -gt $n ] && b=$n
      x=$(EXTRA $g); x=${x/captions_row2/captions_$g}
      echo "$ENVP python -u run_agentic_eval.py --prompt-json $A/$g/prompts_avbadd.json --outputs-dir $A/$g/eval --output-csv $D/${g}_shard$k.csv --axes all $COMMON $x --start-index $a --end-index $b" >> $D/README.md
      env $ENVP python -u run_agentic_eval.py --prompt-json $A/$g/prompts_avbadd.json --outputs-dir $A/$g/eval --output-csv $D/${g}_shard$k.csv \
          --axes all $COMMON $x --start-index $a --end-index $b >> $D/${g}_shard$k.log 2>&1 &
      pids+=($!)
    done
  done
}
# 11/02: CYCLES=1 (set by auto_0800_1102.sh) = no pause / relaunch: on the first 429 kill the shards and exit 3.
CYCLES=${CYCLES:-8}
for cycle in $(seq 1 $CYCLES); do
  echo "- cycle $cycle start $(date -Iseconds)" >> $D/README.md
  base=$(cat $D/*_shard*.log 2>/dev/null | grep -c '\[ERROR\].*429')
  start
  hit=0
  while :; do
    alive=0; for p in "${pids[@]}"; do kill -0 $p 2>/dev/null && alive=1; done
    now=$(cat $D/*_shard*.log 2>/dev/null | grep -c '\[ERROR\].*429')
    if [ $now -gt $base ]; then hit=1; for p in "${pids[@]}"; do kill $p 2>/dev/null; done; sleep 5
      for p in "${pids[@]}"; do kill -9 $p 2>/dev/null; done; break; fi
    [ $alive = 0 ] && break
    sleep 60
  done
  if [ $hit = 1 ] && [ $cycle -ge $CYCLES ]; then echo "- cycle $cycle: 429 seen at $(date -Iseconds); all shards killed; no further cycle (CYCLES=$CYCLES)" >> $D/README.md; echo "[$1] stopped on 429 $(date '+%F %H:%M')"; exit 3; fi
  if [ $hit = 1 ]; then echo "- cycle $cycle: 429 seen at $(date -Iseconds); all shards killed; pause 30 min" >> $D/README.md; sleep 1800; continue; fi
  echo "- cycle $cycle: all shards exited $(date -Iseconds)" >> $D/README.md
  break
done
echo "[$1] done $(date '+%F %H:%M')"
