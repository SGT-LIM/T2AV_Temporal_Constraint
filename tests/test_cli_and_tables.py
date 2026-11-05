"""CLI dry runs (no calls, no run dir) and the scoring tables."""
import pandas as pd
import pytest

from t2av_eval import cli
from t2av_eval.scoring import tables as T


def test_dry_run_media_plan(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "a"); monkeypatch.setenv("GEMINI_API_KEY_2", "b")
    monkeypatch.setenv("T2AV_WORK_ROOT", str(tmp_path))
    assert cli.main(["judge", "media_only", "--sets", "hdmove_p12", "--name", "t", "--dry-run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 2 and "GEMINI_API_KEY:" in out[0] and "GEMINI_API_KEY_2:" in out[1]
    assert not list(tmp_path.glob("results/*"))


def test_stage2_needs_stage1():
    with pytest.raises(SystemExit):
        cli.main(["judge", "gated", "--sets", "p3p9", "--name", "t"])


def test_pass_through_guard(monkeypatch):
    monkeypatch.delenv("JOB_ID", raising=False)
    with pytest.raises(SystemExit, match="qrsh"):
        cli.main(["screen", "clap", "--", "rows"])


def W():
    return pd.DataFrame([
        dict(group="P01P02", axis="AVB", part="original", uid="o1", y="yes", row1="yes", row4="no", row5="yes"),
        dict(group="P01P02", axis="AVB", part="original", uid="o2", y="yes", row1="yes", row4="yes", row5="yes"),
        dict(group="P01P02", axis="AVB", part="variant", uid="v1", y="no", row1="yes", row4="no", row5="no"),
        dict(group="P01P02", axis="AVB", part="variant", uid="v2", y="no", row1="yes", row4="no", row5=""),
    ])


def test_tables():
    m = T.metrics_table(W()).set_index("cond")
    assert m.loc["row1", "acc"] == 0.5 and m.loc["row4", "rec"] == 1.0 and m.loc["row4", "FA"] == 0.5 and m.loc["row5", "n"] == 3
    c = T.compare_table(W()).set_index("cond")
    assert c.loc["row4", "fixed"] == 2 and c.loc["row4", "broken"] == 1 and c.loc["row4", "broken_pass"] == 1
    assert c.loc["row4", "bound"] == 0.07 and c.loc["row4", "verdict"] == "beyond bound"
    o = T.operating_points(W()).set_index("cond")
    assert o.loc["row4", "recall_fail"] == 1.0 and o.loc["row4", "FA_pass"] == 0.5


def test_never_pool_models():
    w = W().assign(model=["LTX_2p3", "MOVA", "LTX_2p3", "LTX_2p3"])
    with pytest.raises(ValueError, match="never pooled"):
        T.metrics_table(w)


def test_run_media_launches_shards(monkeypatch, tmp_path):
    """run_media past the dry run: Files check (fake client), README, one process per shard with the right env; no network"""
    import google.genai as genai
    from t2av_eval.run import launch as L
    monkeypatch.setenv("GEMINI_API_KEY", "a"); monkeypatch.setenv("GEMINI_API_KEY_2", "b")
    monkeypatch.setattr(L._rd, "create", lambda name, root=None: (tmp_path / f"{name}_x").mkdir() or tmp_path / f"{name}_x")
    monkeypatch.setattr(genai, "Client", lambda **k: __import__("types").SimpleNamespace(files=__import__("types").SimpleNamespace(list=lambda: [])))
    started = []

    class P:
        returncode = 0
        def __init__(self, cmd, env, **k):
            started.append((cmd, env))
        def poll(self):
            return 0
    monkeypatch.setattr(L, "subprocess", __import__("types").SimpleNamespace(Popen=P, STDOUT=-2))   # launch.py only
    monkeypatch.setattr(L, "watch", lambda d, procs, every=60: 0)
    assert L.run_media("media_only", ["ma_p3p9"], "t") == 0
    assert len(started) == 3
    cmd, env = started[1]
    assert cmd[1:3] == ["-m", "t2av_eval.run.shard"] and cmd[cmd.index("--axes") + 1] == "a"
    assert env["GEMINI_API_KEY"] == "b" and "GEMINI_API_KEY_2" not in env and env["T2AV_DELETE_UPLOADS"] == "1"
    assert env["T2AV_SHARD"] == "ma_p3p9_shard1" and env["OMP_NUM_THREADS"] == "1" and env["T2AV_CALLS_PER_HOUR"] == "2000"
    assert "files storage before launch" in (tmp_path / "t_x" / "README.md").read_text()
