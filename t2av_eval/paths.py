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


# Cache keys that embed a video path (Whisper/FLAM audio evidence, Synchformer sections, caption cache) use the path re-written
# under this fixed root. On SCC with the default data_root that is exactly str(Path(video).resolve()), the key every existing
# cache entry was written under, so no entry is renamed; with the data copied elsewhere (same layout) the keys are the same.
CACHE_KEY_DATA_ROOT = Path(_Y["cache_key_data_root"])


def canonical_video(video_path):
    """str(resolved video path), with the data_root prefix replaced by cache_key_data_root; outside data_root unchanged."""
    rp = Path(video_path).resolve()
    for root in (DATA, DATA.resolve()):
        try:
            return str(CACHE_KEY_DATA_ROOT / rp.relative_to(root))
        except ValueError:
            pass
    return str(rp)
