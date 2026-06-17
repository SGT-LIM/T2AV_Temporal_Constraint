#!/usr/bin/env bash
set -euo pipefail

# Run 8 evaluation settings for LTX-2.3 and MOVA.
# Usage:
#   export GEMINI_API_KEY='YOUR_KEY'
#   bash run_ltx_mova_8evals.sh
#
# Optional:
#   OVERWRITE=1 bash run_ltx_mova_8evals.sh
#   DRY_RUN=1 bash run_ltx_mova_8evals.sh


# -------------------------
# Paths
# -------------------------
PROMPT_5=/home/coder/T2AV/prompts/generated/5-comb_temporal_selected_specs_prompts.json
PROMPT_6=/home/coder/T2AV/prompts/generated/6-comb_temporal_selected_specs_prompts.json

LTX_SCRIPT=eval_5axis_per_event_multi_prompt.py
LTX_OUTPUTS=/home/coder/T2V_Gen/LTX-2/outputs/refined_prompt_ver2
LTX_OUTDIR=/home/coder/T2AV/eval_results/gemini/LTX-2.3

MOVA_SCRIPT=eval_5axis_per_event.py
MOVA_OUTPUTS=/home/coder/T2AV/generation/MOVA/outputs/refined_prompt_ver2
MOVA_OUTDIR=/home/coder/T2AV/eval_results/gemini/MOVA

mkdir -p "$LTX_OUTDIR" "$MOVA_OUTDIR"

COMMON_ARGS=(
  --variant-indices 1
  --relative-only
)

if [[ "${OVERWRITE:-0}" == "1" ]]; then
  COMMON_ARGS+=(--overwrite)
fi

# method_name|pose_evidence_mode|audio_evidence_mode
METHODS=(
  "MediaPipe|focused_raw|none"
  "Whisper|none|whisper"
  "CLAP|none|clap"
  "MediaPipe_Whisper|focused_raw|whisper"
  "MediaPipe_CLAP|focused_raw|clap"
  "Whisper_CLAP|none|both"
  "AllTools|focused_raw|both"
)

run_cmd() {
  echo
  echo "[RUN] $*"
  if [[ "${DRY_RUN:-0}" == "1" ]]; then
    return 0
  fi
  "$@"
}

run_ltx() {
  local method="$1"
  local pose="$2"
  local audio="$3"
  local out_csv="$LTX_OUTDIR/${method}.csv"

  run_cmd python "$LTX_SCRIPT" \
    --prompt-json "$PROMPT_5" \
    --prompt-json-6 "$PROMPT_6" \
    --outputs-dir "$LTX_OUTPUTS" \
    --output-csv "$out_csv" \
    --pose-evidence-mode "$pose" \
    --audio-evidence-mode "$audio" \
    "${COMMON_ARGS[@]}"
}

run_mova() {
  local method="$1"
  local pose="$2"
  local audio="$3"
  local out_csv="$MOVA_OUTDIR/${method}.csv"

  run_cmd python "$MOVA_SCRIPT" \
    --prompt-json "$PROMPT_6" \
    --outputs-dir "$MOVA_OUTPUTS" \
    --output-csv "$out_csv" \
    --pose-evidence-mode "$pose" \
    --audio-evidence-mode "$audio" \
    "${COMMON_ARGS[@]}"
}

for spec in "${METHODS[@]}"; do
  IFS='|' read -r method pose audio <<< "$spec"
  echo
  echo "=============================="
  echo "[LTX]  method=$method pose=$pose audio=$audio"
  echo "=============================="
  run_ltx "$method" "$pose" "$audio"
done

for spec in "${METHODS[@]}"; do
  IFS='|' read -r method pose audio <<< "$spec"
  echo
  echo "=============================="
  echo "[MOVA] method=$method pose=$pose audio=$audio"
  echo "=============================="
  run_mova "$method" "$pose" "$audio"
done

echo
echo "[DONE] All evaluations finished."
echo "LTX results:  $LTX_OUTDIR"
echo "MOVA results: $MOVA_OUTDIR"
