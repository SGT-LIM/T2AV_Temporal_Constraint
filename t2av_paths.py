"""Portable path roots for the T2AV evaluation code (see repro/avt_gate/README.md).

The experiment code originally used absolute lab paths. repro/avt_gate/tools/make_portable.py replaced them with these attributes:
  WORKSPACE  $T2AV_WORKSPACE  experiment workspace with the original repo-relative data layout (eval_results/, new_prompts/,
                              generation/prolific_2k_25/, eval_results/analysis/...)            [required]
  DATA       $T2AV_DATA       T2AV data root (videos, GT, tool outputs, real_av, gt_annotations ...)  [required]
  HF_CACHE   $T2AV_HF_CACHE   model-weight cache (OpenFLAM checkpoint: $T2AV_HF_CACHE/openflam)   [tool re-extraction only]
  EXT_TMP    $T2AV_EXT_TMP    external code checkouts (Synchformer, t2av_multiagent)              [tool re-extraction only]
out_dir(name) returns $T2AV_OUT_DIR/<name> for the analysis scripts, so new results never overwrite the historical ones.
API keys are never read here; the Gemini callers read GEMINI_API_KEY themselves.
"""
import os
from pathlib import Path


def _get(env, required):
    v = os.environ.get(env, "").rstrip("/")
    if v:
        return v
    if required:
        raise RuntimeError(f"environment variable {env} is not set (see repro/avt_gate/README.md and repro/avt_gate/env.example)")
    return f"/UNSET_{env}"          # optional roots: any use fails with an explicit file-not-found path


WORKSPACE = _get("T2AV_WORKSPACE", True)
DATA = _get("T2AV_DATA", True)
HF_CACHE = _get("T2AV_HF_CACHE", False)
EXT_TMP = _get("T2AV_EXT_TMP", False)


def out_dir(name):
    root = os.environ.get("T2AV_OUT_DIR")
    if not root:
        raise RuntimeError("T2AV_OUT_DIR is not set: analysis scripts write only below $T2AV_OUT_DIR/<name> (historical results are never written)")
    return Path(root) / name
