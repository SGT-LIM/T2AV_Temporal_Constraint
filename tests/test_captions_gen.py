"""AVoCaDO caption jobs: the package targets reproduce the runner arguments of the recorded job scripts
(legacy/evaluation/ablation/captions/*.sh), the 48 GB profile is the recorded request, and the job runs only inside qrsh."""
import re, shlex
from pathlib import Path

import pytest

from t2av_eval.evidence.captions_gen import job as J

L = Path(__file__).resolve().parents[1] / "legacy/evaluation/ablation/captions"


def recorded(script, out_name):
    """(videos dir, fps) of the runner call that writes out_name in a recorded script (cap() expanded for the A100 job)"""
    s = (L / script).read_text().replace("\\\n", " ")
    v = dict(re.findall(r"^(\w+)=(\S+)$", s, re.M))
    for line in s.splitlines():
        if out_name in line and ("run_qwen3_captions.py" in line or line.strip().startswith("cap ")):
            tok = shlex.split(line.split(">")[0])
            if tok[0] == "cap":
                return re.sub(r"\$(\w+)", lambda m: v[m.group(1)], tok[1]), "8"
            return tok[tok.index("--videos-dir") + 1], tok[tok.index("--fps") + 1]
    raise AssertionError(f"{out_name} not in {script}")


@pytest.mark.parametrize("target,script", [("gen149", "avocado_a100_1030_job.sh"), ("hdepic_p3p9_clips", "avocado_a100_1030_job.sh"),
                                           ("hdmove_p12", "avocado_hdmove_fallback48g_1101.sh")])
def test_targets_match_recorded_jobs(target, script):
    out = J.CFG["targets"][target]["recorded"]
    vids, fps = recorded(script, out.replace(".json", "") if target != "gen149" else "avocado_fps8_plain_v3_gen149.json")
    cmd = J.command(target, Path("/tmp/x.json"))
    assert cmd[cmd.index("--videos-dir") + 1] == vids
    assert float(cmd[cmd.index("--fps") + 1]) == float(fps)
    assert cmd[3:7] == ["--backend", "avocado", "--caption-style", "plain"]


def test_48g_profile_is_the_recorded_request():
    hw = J.CFG["hardware"]["gpu_48g"]
    assert hw["qrsh"] == "qrsh -pe omp 4 -l gpu_memory=48G -l gpu_c=8.0" and hw["env"]["PYTORCH_CUDA_ALLOC_CONF"] == "expandable_segments:True"
    assert "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" in (L / "avocado_hdmove_fallback48g_1101.sh").read_text()


def test_qrsh_only(monkeypatch):
    monkeypatch.delenv("JOB_ID", raising=False)
    with pytest.raises(SystemExit, match="qrsh"):
        J.main(["--target", "gen149", "--hardware", "a100_80g", "--name", "x"])
