#!/bin/bash
# 11/02: paced reruns of the two 11/01 row 1 runs that failed on quota, then their stage 2 (text calls, 6 workers).
#   P03-P09 mute_anchor row 1  -> results/hdepic_main_ma39_row1_A_g36_1101 (3 shards, same index ranges as 11/01)
#   option (ii) row 1 remainder -> results/hdepic_main_row1_p12all_g36_1101 (12 shards, same index ranges as 11/01)
# Same output csvs as 11/01, so done items are skipped (new_eval.already_done) and error rows are retried; the newer row wins at
# scoring. At most 11 shards at a time (the 11/02 pacing). Rows done on 11/02 are cross-day against the 11/01 rows and are marked so.
# Started by auto_0800_1102.sh, which stops everything (process group) on the first 429; this script has no retry cycles of its own.
LEGACY_CODE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); LROOT=${T2AV_LEGACY_ROOT:-$(cd "$LEGACY_CODE/../../.." && pwd)/legacy_root}  # legacy path roots, see legacy/README.md
set -u
export PATH=/projectnb/ivc-ml/youngsun/conda_envs/t2av_eval/bin:/share/pkg.8/ffmpeg/8.1/install/bin:$PATH
export LD_LIBRARY_PATH=/share/pkg.8/ffmpeg/8.1/install/lib:/share/pkg.8/cuda/12.8/install/lib64:${LD_LIBRARY_PATH:-}
export T2AV_DELETE_UPLOADS=1   # 11/02 (user): delete each uploaded Gemini File after its call succeeded (new_eval.maybe_delete_upload)
export GEMINI_API_KEY=$(cat ~/.gemini_key) OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
env | grep -q '^GEMINI_API_KEY=.' || { echo "GEMINI_API_KEY missing"; exit 1; }
ABL=$LEGACY_CODE; G=$LROOT/evaluation/ablation/gepa_stage2/runs/obsval_1028
R=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results
MA=$R/hdepic_main_ma39_row1_A_g36_1101; P12=$R/hdepic_main_row1_p12all_g36_1101
MAP=/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/mute_anchor_1101
P12V=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_main_1101/p12all_new
COMMON="--model gemini-3.6-flash --thinking-level high --pose-evidence-mode none --audio-evidence-mode none --caption-evidence-mode none"
cd $ABL
for d in $MA $P12; do echo "- 11/02 rerun (paced, <= 11 shards, stop on first 429 by auto_0800_1102.sh): start $(date -Iseconds) on $(hostname); rows from this run are cross-day vs 11/01" >> $d/README.md; done
jobs_=()
for k in 0 1 2; do jobs_+=("$MA|$MAP/prompts.json|$MAP/eval|a|$((k * 40))|$(((k + 1) * 40))|$k"); done
N=$(ls $P12V | wc -l); S=$(( (N + 11) / 12 ))
for k in $(seq 0 11); do a=$((k * S)); b=$(((k + 1) * S)); [ $b -gt $N ] && b=$N
  jobs_+=("$P12|/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_prompts_v2.json|$P12V|all|$a|$b|$k"); done
for j in "${jobs_[@]}"; do
  IFS='|' read -r D PJ OD AX a b k <<< "$j"
  while [ $(jobs -rp | wc -l) -ge 11 ]; do sleep 20; done
  echo "python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $OD --output-csv $D/shard$k.csv --axes $AX $COMMON --start-index $a --end-index $b   # 11/02" >> $D/README.md
  python -u run_agentic_eval.py --prompt-json $PJ --outputs-dir $OD --output-csv $D/shard$k.csv --axes $AX $COMMON --start-index $a --end-index $b >> $D/shard$k.log 2>&1 &
done
wait
echo "reruns row1 done $(date '+%F %H:%M'): ma39 errors $(grep -h '^\[DONE\] processed' $MA/shard*.log | tail -3 | grep -o 'errors=[0-9]*' | tr '\n' ' '); p12all errors $(grep -h '^\[DONE\] processed' $P12/shard*.log | tail -12 | grep -o 'errors=[0-9]*' | sort | uniq -c | tr '\n' ' ')"

# the 11/01 tables are rewritten by the scoring steps below: keep a copy of each first
SNAP=$G/snap_1101_before_reruns_1102; mkdir -p $SNAP
cp -n $G/hd_stage2_groups_1101.csv $G/hd_stage2_rows_1101.csv $G/hd_stage2_table_1101.csv $G/hd_framing_sentences_1101.json $G/hd_ma_rows*_1101.csv $G/hd_ma_table*_1101.csv $G/rows.jsonl $SNAP/ 2>/dev/null

# stage 2, P03-P09 mute_anchor (as hd_ma39_stage2_1101.sh, 6 workers)
python gepa_stage2/hd_stage2_1101.py ma_rows --src hm_ma39
python -u gepa_stage2/obs_judge_1028.py run --set HMB4 --cond gen_tool_text --workers 6 > $G/run_HMB4_1102.log 2>&1 &
python -u gepa_stage2/obs_judge_1028.py run --set HMB5 --cond gen_tool_text --workers 6 > $G/run_HMB5_1102.log 2>&1 &
wait; tail -qn1 $G/run_HMB4_1102.log $G/run_HMB5_1102.log
python gepa_stage2/hd_stage2_1101.py ma_score --src hm_ma39
echo "ma39 stage 2 done $(date '+%F %H:%M')"

# stage 2, option (ii) (as hd_p12new_stage2_1101.sh, 6 workers; cached calls are reused)
python gepa_stage2/hd_stage2_1101.py rows4
python -u gepa_stage2/obs_judge_1028.py run --set HG4 --cond gen_tool_text --workers 6 > $G/run_HG4_p12new_1102.log 2>&1 &
python -u gepa_stage2/hd_stage2_1101.py vcheck --workers 6 > $G/run_hd_vcap_check_p12new_1102.log 2>&1; tail -1 $G/run_hd_vcap_check_p12new_1102.log
python gepa_stage2/hd_stage2_1101.py rows5
python gepa_stage2/hd_stage2_1101.py framing
wait
for s in HG5 HFRb HFRc; do python -u gepa_stage2/obs_judge_1028.py run --set $s --cond gen_tool_text --workers 6 > $G/run_${s}_p12new_1102.log 2>&1; done
tail -qn1 $G/run_HG4_p12new_1102.log $G/run_HG5_p12new_1102.log $G/run_HFRb_p12new_1102.log $G/run_HFRc_p12new_1102.log
python gepa_stage2/hd_stage2_1101.py groups
python gepa_stage2/hd_stage2_1101.py score
echo "p12new stage 2 done $(date '+%F %H:%M')"
echo "reruns done $(date '+%F %H:%M')"
