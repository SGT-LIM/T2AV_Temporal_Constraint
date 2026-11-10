# Corrected A-axis evaluation (contract v3, event-level gate)

The rule is in `A_AXIS_CONTRACT.md`. Results are written to `$T2AV_OUT_DIR/a_axis_event_gate_v3_2026-11-10/`; historical runs are never
written.

```bash
export T2AV_WORKSPACE=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint T2AV_DATA=/projectnb/ivc-ml/youngsun/T2AV_data
export T2AV_OUT_DIR=$T2AV_WORKSPACE/eval_results/analysis PYTHONDONTWRITEBYTECODE=1
./repro/avt_gate/link_workspace.sh                                   # once per checkout
cd repro/avt_gate/a_axis_v3
python tests/test_a_event_gate.py                                    # 17 deterministic contract tests (no data, no API)
python run_a_axis_correction.py features                             # per-event openings at alpha .01 / .05 / .10 (no GT)
python run_a_axis_correction.py select_example                       # freezes the walkthrough clip (refuses to change it)
python run_a_axis_correction.py plan                                 # corrected requests; exact-request reuse or "new call"
GEMINI_API_KEY=... python run_a_axis_correction.py run --workers 4   # only the planned new calls; 3 attempts max; billing error -> HOLD
python run_a_axis_correction.py plan                                 # refresh actions after the run
python run_a_axis_correction.py walkthrough                          # walkthrough/WALKTHROUGH.md (+ regression clip)
python run_a_axis_correction.py score                                # predictions/, tables/, checks.json, cost.json
python make_package.py                                               # MANIFEST.json, perturbation .tex, ZIP
```

**Guards.**
- Every stage installs an audit hook that aborts any file write under `$T2AV_WORKSPACE`, `$T2AV_DATA` or the repo, except the output
  directory.
- No model is called outside `run`.
- Opened events without a complete output stay unresolved.
