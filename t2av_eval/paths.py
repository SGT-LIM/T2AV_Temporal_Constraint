"""Data, input and output roots (config/paths.yaml, each overridable by an environment variable).

DATA    T2AV_data: videos, prompt files, tool records.
INPUTS  read-only inputs that live in the main checkout (v3 manifests, caption json, 220 prompts, earlier run CSVs).
WORK    everything this package writes: run dirs, call caches, tables. Never inside INPUTS.
"""
import os
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parent / "config"
REPO = Path(__file__).resolve().parents[1]
_Y = yaml.safe_load(open(CONFIG / "paths.yaml"))


def _root(key, env, default=None):
    v = os.environ.get(env) or _Y.get(key) or default
    return Path(os.path.abspath(Path(v).expanduser()))      # no resolve(): path strings feed cache keys


DATA = _root("data_root", "T2AV_DATA_ROOT")
INPUTS = _root("inputs_root", "T2AV_INPUTS_ROOT")
WORK = _root("work_root", "T2AV_WORK_ROOT", REPO / "runs")
if WORK.resolve() == INPUTS.resolve() or INPUTS.resolve() in WORK.resolve().parents:
    raise RuntimeError(f"work_root {WORK} is inside inputs_root {INPUTS}; outputs must not go into the main checkout")
