#!/bin/bash
# Launch set C30T once the Qwen move pass is complete: 142 files, and both GPU jobs (8352027, 8352815) done writing.
Q=/projectnb/ivc-ml/youngsun/T2AV_data/tools/qwen_timestamps_1030
done_job() { grep -q "move done" $1 2>/dev/null || ! qstat -j $2 >/dev/null 2>&1; }
until [ "$(ls $Q/move_1030/hdepicmove | wc -l)" -ge 142 ] && done_job $Q/qrsh_1030.out 8352027 && done_job $Q/qrsh_1030_rev.out 8352815; do sleep 60; done
echo "$(date +%H:%M) Qwen move pass complete: $(ls $Q/move_1030/hdepicmove | wc -l) files; tracebacks: $(cat $Q/move_1030.log $Q/move_1030_rev.log 2>/dev/null | grep -ci traceback)"
cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
python gepa_stage2/obs_judge_1028.py rows_bc30 --part TCC 2>&1 | grep -v Warn || exit 1
bash gepa_stage2/launch_obsval_C30T_1030.sh run
