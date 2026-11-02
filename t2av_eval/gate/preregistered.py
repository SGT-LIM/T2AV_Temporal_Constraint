"""Pre-registered gate thresholds, read from the artifact files named in config/recipe_v4.yaml (paths relative to DATA).

Each artifact was written before any result of the sets it is applied to was read. load checks that flag and that the
values equal the ones in the config; any mismatch raises. FILES overrides a file path (tests point it at a fixture copy).
"""
import json

import yaml

from t2av_eval import paths as _P

RECIPE = _P.CONFIG / "recipe_v4.yaml"
FILES = {}      # name -> path override


def recipe():
    return yaml.safe_load(open(RECIPE))


def _file(name):
    return FILES.get(name) or _P.DATA / recipe()["gate"][name]["file"]


def avb_rule():
    """the PREREGISTERED_RULE.json dict (T, P, derivation, written, ...)"""
    g, f = recipe()["gate"]["avb_rule"], _file("avb_rule")
    r = json.load(open(f))
    if r.get("holdout_results_seen") is not False:
        raise ValueError(f"{f}: holdout_results_seen is not false")
    if (r["T"], r["P"]) != (g["T"], g["P"]):
        raise ValueError(f"{f}: T/P {r['T']}/{r['P']} differ from recipe_v4.yaml {g['T']}/{g['P']}")
    return r


def t_flam():
    g, f = recipe()["gate"]["a_flam"], _file("a_flam")
    r = json.load(open(f))
    if r.get("generated_set_results_seen") is not False:
        raise ValueError(f"{f}: generated_set_results_seen is not false")
    if r["T_flam"] != g["T_flam"]:
        raise ValueError(f"{f}: T_flam {r['T_flam']} differs from recipe_v4.yaml {g['T_flam']}")
    return r["T_flam"]
