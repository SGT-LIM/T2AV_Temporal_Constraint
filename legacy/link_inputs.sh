#!/bin/bash
# Symlink the read-only inputs of the legacy scripts from the main checkout into $T2AV_LEGACY_ROOT (default <repo>/legacy_root).
# Only inputs: GT manifests, caption json, generation prompts. Output and cache folders are never linked (see legacy/README.md).
set -eu
MAIN=${T2AV_MAIN:-/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LROOT=${T2AV_LEGACY_ROOT:-$REPO/legacy_root}
case "$(realpath -m "$LROOT")" in "$(realpath "$MAIN")"*) echo "T2AV_LEGACY_ROOT is inside the main checkout; refusing"; exit 1;; esac
for p in evaluation/ablation/gepa_stage2/manifests_v3 evaluation/ablation/captions new_prompts; do
  mkdir -p "$LROOT/$(dirname $p)"
  if [ -e "$LROOT/$p" ] || [ -L "$LROOT/$p" ]; then echo "exists, skipping: $LROOT/$p"; continue; fi
  ln -s "$MAIN/$p" "$LROOT/$p" && echo "linked $p"
done
