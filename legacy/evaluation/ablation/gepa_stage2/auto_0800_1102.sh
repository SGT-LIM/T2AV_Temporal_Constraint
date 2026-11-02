#!/bin/bash
# 11/02 timed auto-start (user, 11/02 01:00). Runs detached on scc1 (screen auto0800 + nohup).
#   08:00  probe call. Not 429 -> submit the AVB-additions GPU jobs (submit_0800.sh) and start AVB-additions row 1 with the paced
#          launcher (launch_avbadd_1102.sh row1, 11 shards, CYCLES=1).
#   11:00  probe call. Not 429 -> start the paced reruns (launch_reruns_1102.sh: P03-P09 mute_anchor row 1 + option (ii) row 1
#          remainder, then their stage 2). If AVB-additions row 1 is still running at 11:00, the reruns wait for it to end, so no more
#          than 11 full-video shards run at once.
#   Any 429 (probe, or any line with 429 in a log of this morning's API runs, retries included) -> kill every API process started
#   here (whole process groups), write HOLD with the reason, start nothing more. GPU jobs make no Gemini calls and keep running.
#   A probe error other than 429 is retried 3 times, 5 min apart, then HOLD.
# Log: $W/auto_0800_1102.out; README and HOLD in $W.
set -u
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/t2av_eval/bin:$PATH
export GEMINI_API_KEY=$(cat ~/.gemini_key)
ABL=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation; GS=$ABL/gepa_stage2; G=$GS/runs/obsval_1028
W=$G/auto_0800_1102; mkdir -p $W
R=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results
AVB1=$R/hdepic_avbadd_row1_anchor_g36_1102
LOGS="$AVB1/*_shard*.log $R/hdepic_main_ma39_row1_A_g36_1101/shard*.log $R/hdepic_main_row1_p12all_g36_1101/shard*.log $G/run_*_1102.log"
P429='ClientError:? 429|429 RESOURCE_EXHAUSTED'   # not a bare 429: item ids such as _0042999 contain it
n429() { cat $LOGS 2>/dev/null | grep -cE "$P429"; }
say() { echo "$(date '+%F %H:%M:%S') $*" | tee -a $W/README.md; }
pg=()
hold() { say "HOLD: $*"; for p in "${pg[@]}"; do kill -- -$p 2>/dev/null; done; sleep 10; for p in "${pg[@]}"; do kill -9 -- -$p 2>/dev/null; done
         { echo "HOLD $(date -Iseconds)"; echo "$*"; echo "API process groups killed: ${pg[*]:-none}. GPU jobs left running (no Gemini calls)."; } > $W/HOLD; exit 2; }
wait_until() { while [ $(date +%s) -lt $(date -d "$1" +%s) ]; do sleep 30; done; }
probe() {
  for t in 1 2 3; do
    rc=$(cd $ABL && python gepa_stage2/probe_gemini_1102.py > $W/probe_last.txt 2>&1; echo $?); out=$(tail -1 $W/probe_last.txt)
    say "probe $1 try $t: rc $rc: $out"
    [ $rc = 0 ] && return 0
    [ $rc = 2 ] && hold "probe at $1 returned 429: $out"
    sleep 300
  done
  hold "probe at $1 failed 3 times (not 429): $out"
}
watch_429() {   # watch_429 BASE: returns when every group in pg has exited; HOLD on a new 429 line
  while :; do
    [ $(n429) -gt $1 ] && hold "429 in a run log at $(date '+%H:%M'): $(cat $LOGS 2>/dev/null | grep -hE "$P429" | tail -1 | cut -c1-200)"
    alive=0; for p in "${pg[@]}"; do pgrep -g $p > /dev/null && alive=1; done
    [ $alive = 0 ] && return 0
    [ $(date +%s) -ge $(date -d "11:00" +%s) ] && [ "${2:-}" = "until11" ] && return 0
    sleep 30
  done
}

[ -e $W/README.md ] || { echo "# auto_0800_1102"; echo; echo "- armed $(date -Iseconds) on $(hostname); run date 2026-11-02; model gemini-3.6-flash, thinking high (probe: thinking low)"
  echo "- scripts: auto_0800_1102.sh, probe_gemini_1102.py, launch_avbadd_1102.sh (CYCLES=1), launch_reruns_1102.sh, real_av/eval/hdepic_avbadd_1102/gpu/submit_0800.sh"
  echo "## log"; } > $W/README.md
say "armed; waiting for 08:00"
wait_until "2026-11-02 08:00"
probe 08:00
bash /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_avbadd_1102/gpu/submit_0800.sh > $W/submit_0800.out 2>&1
say "GPU jobs submitted: $(grep -c 'avbadd' $W/submit_0800.out) lines in qstat (submit_0800.out)"
B=$(n429)
CYCLES=1 setsid bash $GS/launch_avbadd_1102.sh row1 > $W/avbadd_row1.out 2>&1 &
sleep 2; pg+=($(ps -o pgid= -p $! | tr -d ' ')); say "AVB-additions row 1 started (pgid ${pg[-1]}); 429 lines before start: $B"
watch_429 $B until11
wait_until "2026-11-02 11:00"
probe 11:00
if pgrep -g ${pg[0]} > /dev/null; then say "AVB-additions row 1 still running at 11:00; reruns wait for it"; watch_429 $B; fi
say "AVB-additions row 1 exited: $(tail -1 $W/avbadd_row1.out)"
B=$(n429)
setsid bash $GS/launch_reruns_1102.sh > $W/reruns.out 2>&1 &
sleep 2; pg+=($(ps -o pgid= -p $! | tr -d ' ')); say "reruns started (pgid ${pg[-1]}); 429 lines before start: $B"
watch_429 $B
say "reruns exited: $(tail -1 $W/reruns.out)"
say "auto-start finished without a 429; AVB-additions stage 2 and row 2 are left for the morning check"
