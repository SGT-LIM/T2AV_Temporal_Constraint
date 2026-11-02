"""Judge conditions and evaluation sets (config/sets.yaml) -> the exact run_agentic_eval arguments and environment of the
recorded launches. Argument order is the launchers': --prompt-json, --outputs-dir, --axes all, the judge arguments, then the
condition's arguments (tests/test_conditions.py compares with the recorded 11/01 and 10/30 commands).

Media conditions (one shard = one run_agentic_eval process):  media_only (row 1), all_tools (row 2), routing (row 3)
Stage-2 conditions (text-only calls on a media_only run):      two_stage_ungated (row 4), gated (row 5), framing (b / c)
"""
import yaml

from t2av_eval import paths as _P

SETS_YAML = _P.CONFIG / "sets.yaml"
MEDIA = ("media_only", "all_tools", "routing")
STAGE2 = ("two_stage_ungated", "gated", "framing")
ROW = {"media_only": "row 1", "all_tools": "row 2", "routing": "row 3", "two_stage_ungated": "row 4", "gated": "row 5",
       "framing": "framing b / c"}


def config():
    return yaml.safe_load(open(SETS_YAML))


def resolve(p):
    """'data:rel' -> DATA/rel, 'inputs:rel' -> INPUTS/rel"""
    root, rel = p.split(":", 1)
    return str({"data": _P.DATA, "inputs": _P.INPUTS}[root] / rel)


def set_info(name, cfg=None):
    cfg = cfg or config()
    if name not in cfg["sets"]:
        raise KeyError(f"unknown set {name}; known: {', '.join(cfg['sets'])}")
    s = dict(cfg["sets"][name], name=name)
    for k in ("prompts", "videos", "captions"):
        s[k] = resolve(s[k]) if s.get(k) else None
    s["sync"] = resolve(cfg["sync_sections"][s["family"]])
    return s


def media_command(condition, set_name, cfg=None):
    """(args, env) of one shard, without --output-csv / --start-index / --end-index"""
    if condition not in MEDIA:
        raise ValueError(f"{condition} is not a media condition ({', '.join(MEDIA)})")
    cfg = cfg or config()
    s = set_info(set_name, cfg)
    c = cfg["conditions"][condition][s["family"]]
    if s.get("mute_anchor") and condition != "media_only":
        raise ValueError(f"{set_name}: mute_anchor sets have row 1 (media_only) and the A stage 2 only")
    if any("{captions}" in x for x in c["args"]) and not s["captions"]:
        raise ValueError(f"{set_name}: {condition} needs captions, the set has none")
    fill = lambda v: v.format(captions=s["captions"], sync=s["sync"])
    args = ["--prompt-json", s["prompts"], "--outputs-dir", s["videos"], "--axes", s.get("axes", "all"), *cfg["judge_args"],
            *map(fill, c["args"])]
    return args, {k: fill(v) for k, v in c["env"].items()}


def stage2_steps(conditions):
    """conditions plus what they need, in run order"""
    need = config()["stage2_conditions"]
    out = []

    def add(c):
        for n in need[c]["needs"]:
            add(n)
        if c not in out:
            out.append(c)
    for c in conditions:
        if c not in STAGE2:
            raise ValueError(f"{c} is not a stage-2 condition ({', '.join(STAGE2)})")
        add(c)
    return [c for c in STAGE2 if c in out]
