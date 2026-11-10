#!/bin/bash
# Link the experiment's data directories (which the code addresses relative to its own location) from $T2AV_WORKSPACE into this
# checkout. Read access is enough for rescore_cached.py; it never writes into these links. Existing paths are never replaced.
set -eu
: "${T2AV_WORKSPACE:?set T2AV_WORKSPACE (see repro/avt_gate/env.example)}"
REPO=$(cd "$(dirname "$0")/../.." && pwd)
link() {  # link <path relative to repo / workspace>
  if [ -e "$REPO/$1" ] || [ -L "$REPO/$1" ]; then echo "keep  $1 (exists)"; return; fi
  if [ ! -e "$T2AV_WORKSPACE/$1" ]; then echo "MISSING in workspace: $1"; return; fi
  mkdir -p "$(dirname "$REPO/$1")"; ln -s "$T2AV_WORKSPACE/$1" "$REPO/$1"; echo "link  $1"
}
link evaluation/ablation/gepa_stage2/runs           # Stage-1 anchors index, Stage-2 call caches, final_benchmark_1108, calibration_v2, ...
link evaluation/ablation/gepa_stage2/manifests_v3   # historical v3 manifests (P01/P02 rows; 220 TCR/TCC rows)
link evaluation/ablation/gepa_stage2/panels_1028    # only for the 10/28 observation sets
link evaluation/ablation/gepa_stage2/focus_1028     # only for the 10/28 observation sets
link evaluation/ablation/captions                   # AVoCaDO captions used by V / AVB payloads and caption checks
link new_prompts/generated/relative_500_v5_fixed.json   # the 500 generated prompts (220-batch and MOVA390 items)
