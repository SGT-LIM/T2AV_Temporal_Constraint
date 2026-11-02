"""config/sets.yaml rebuilds the recorded commands exactly: HD-EPIC 11/01 (fixture commands.json) and the generated 10/30 runs
(their run READMEs, read-only; skipped where the main checkout is not mounted)."""
import json, shlex
from pathlib import Path

import pytest

from t2av_eval.judge import conditions as C

FX = Path(__file__).resolve().parent / "fixtures/replay_1101"
R1030 = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent")


def _parse(line):
    tok = shlex.split(line.strip(), comments=True)
    if ">" in tok:
        tok = tok[: tok.index(">")]
    i = tok.index("python")
    env = dict(t.split("=", 1) for t in tok[:i])
    a, out, j = tok[i + 3:], [], 0
    while j < len(a):
        if a[j] in ("--output-csv", "--start-index", "--end-index"):
            j += 2; continue
        out.append(a[j]); j += 1
    return env, out, tok[i + 3:][tok[i + 3:].index("--output-csv") + 1] if "--output-csv" in tok else ""


@pytest.mark.parametrize("key", sorted(json.load(open(FX / "commands.json"))))
def test_hdepic_1101(key):
    rec = json.load(open(FX / "commands.json"))[key]
    row, s = key.split("|")
    args, env = C.media_command({"row1": "media_only", "row2": "all_tools"}[row], s)
    assert args == rec["args"]
    assert env == {k: v for k, v in rec["env"].items() if k != "X"}


@pytest.mark.skipif(not R1030.exists(), reason="10/30 run READMEs not mounted")
@pytest.mark.parametrize("cond,run", [("media_only", "gen_row1_anchor_g36_1030"), ("all_tools", "gen_row2_onecall_sync_g36_1030"),
                                      ("routing", "gen_row3_routing_g36_1030")])
def test_generated_1030(cond, run):
    tag = {"LTX_2p3": "ltx220", "MOVA": "mova220", "gen149": "gen149"}
    seen = 0
    for line in open(R1030 / run / "README.md"):
        if "python -u run_agentic_eval.py" not in line:
            continue
        env, args, out = _parse(line)
        args0, env0 = C.media_command(cond, tag[Path(out).name.rsplit("_shard", 1)[0]])
        assert args0 == args and env0 == env, line[:200]
        seen += 1
    assert seen


def test_stage2_prerequisites():
    assert C.stage2_steps(["gated"]) == ["two_stage_ungated", "gated"]
    assert C.stage2_steps(["framing", "gated"]) == ["two_stage_ungated", "gated", "framing"]
    with pytest.raises(ValueError):
        C.stage2_steps(["media_only"])


R1101 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results")


@pytest.mark.skipif(not R1101.exists(), reason="11/01 run READMEs not mounted")
@pytest.mark.parametrize("set_name,run", [("ma_p12", "hdepic_main_ma_row1_A_g36_1101"), ("ma_p3p9", "hdepic_main_ma39_row1_A_g36_1101")])
def test_mute_anchor_1101(set_name, run):
    lines = [l for l in open(R1101 / run / "README.md") if "python -u run_agentic_eval.py" in l]
    assert lines
    for line in lines:
        env, args, _ = _parse(line)
        assert C.media_command("media_only", set_name) == (args, {})


def test_mute_anchor_sets_refuse_other_conditions():
    with pytest.raises(ValueError):
        C.media_command("all_tools", "ma_p12")
