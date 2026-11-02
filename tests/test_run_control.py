"""Run control: keys (ids only), per-key pacing, the stop rule, the paced client, Files check, run dirs. No network."""
import json, os
from pathlib import Path
from types import SimpleNamespace

import pytest

from t2av_eval.run import client as CL
from t2av_eval.run import files as F
from t2av_eval.run import keys as K
from t2av_eval.run import pacing as PA
from t2av_eval.run import rundir as RD
from t2av_eval.run import stop as ST


class Quota(Exception):
    code = 429

    def __str__(self):
        return "429 RESOURCE_EXHAUSTED. quota"


def test_keys_order_ids_and_shard_env():
    env = {"GEMINI_API_KEY_2": "bbb", "GEMINI_API_KEY": "aaa", "GEMINI_API_KEY_10": "ccc", "GEMINI_API_KEY_3": " ", "PATH": "/bin"}
    ks = K.gemini_keys(env)
    assert [n for n, _ in ks] == ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_10"]
    assert K.for_shard(4, ks)[0] == "GEMINI_API_KEY_2"
    kid = K.key_id(*ks[1])
    assert kid.startswith("GEMINI_API_KEY_2:") and "bbb" not in kid and len(kid.split(":")[1]) == 8
    se = K.shard_env(env, *ks[1])
    assert se["GEMINI_API_KEY"] == "bbb" and se["T2AV_KEY_ID"] == kid and "GEMINI_API_KEY_2" not in se and se["PATH"] == "/bin"
    with pytest.raises(RuntimeError):
        K.for_shard(0, [])


def test_pacing_waits_when_the_hour_is_full(tmp_path):
    t = [1000.0]
    slept = []
    lim = PA.Limiter(tmp_path / "k", 3, clock=lambda: t[0], sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)))
    for _ in range(3):
        assert lim.acquire() == 0
    assert lim.count() == 3
    t[0] = 1000.0 + 3590
    assert lim.acquire() >= 10 - 1e-6           # waits until the first attempt is an hour old
    lim2 = PA.Limiter(tmp_path / "k", 3, clock=lambda: t[0])   # a second process reads the same budget file
    assert lim2.count() == lim.count() == 1                     # the three attempts of t = 1000 are now an hour old


def test_stop_rule(tmp_path, monkeypatch):
    monkeypatch.delenv("T2AV_RUN_DIR", raising=False)
    ST.on_final_error(Quota())                   # outside a run: nothing
    monkeypatch.setenv("T2AV_RUN_DIR", str(tmp_path)); monkeypatch.setenv("T2AV_SHARD", "p3p9_shard2")
    ST.on_final_error(ValueError("bad json"))    # not a quota failure: no stop
    assert not (tmp_path / "STOP").exists()
    ST.check()
    with pytest.raises(ST.StopRun):
        ST.on_final_error(Quota(), where="media item x")
    rec = json.loads((tmp_path / "STOP").read_text())
    assert rec["shard"] == "p3p9_shard2" and "429" in rec["error"] and rec["where"] == "media item x"
    with pytest.raises(ST.StopRun):
        ST.check()
    assert issubclass(ST.StopRun, BaseException) and not issubclass(ST.StopRun, Exception)


def test_paced_client_checks_stop_and_takes_a_slot(tmp_path, monkeypatch):
    monkeypatch.setenv("T2AV_RUN_DIR", str(tmp_path))
    calls = []
    inner = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **k: calls.append(k) or "resp"),
                            files=SimpleNamespace(upload=lambda **k: "up", delete=lambda **k: None))
    lim = PA.Limiter(tmp_path / ".pace" / "k", 10)
    c = CL.PacedClient(inner, lim)
    assert c.models.generate_content(model="m", contents=["x"]) == "resp" and calls == [dict(model="m", contents=["x"])]
    assert lim.count() == 1 and c.files.upload(file="f") == "up"
    (tmp_path / "STOP").write_text("{}")
    with pytest.raises(ST.StopRun):
        c.models.generate_content(model="m", contents=["x"])
    with pytest.raises(ST.StopRun):
        c.files.upload(file="f")
    assert len(calls) == 1


def test_stop_hooks_write_the_error_row_first(tmp_path, monkeypatch):
    from t2av_eval.judge.media import common as AC
    from t2av_eval.judge.stage2 import obs_judge as O
    saved = AC.add_error_to_row, AC.append_row, O.call, getattr(AC, "_t2av_hooked", False)
    written = []
    monkeypatch.setattr(AC, "add_error_to_row", lambda row, exc, *a, **k: dict(row, overall_reason=f"ERROR: {exc}"))
    monkeypatch.setattr(AC, "append_row", lambda path, row: written.append(row))
    monkeypatch.setattr(O, "call", lambda *a, **k: (_ for _ in ()).throw(Quota()))
    monkeypatch.setattr(AC, "_t2av_hooked", False, raising=False)
    monkeypatch.setenv("T2AV_RUN_DIR", str(tmp_path))
    CL.install_stop_hooks()
    row = AC.add_error_to_row({"item_id": "i1"}, Quota(), {})
    with pytest.raises(ST.StopRun):
        AC.append_row("x.csv", row)
    assert written and written[0]["overall_reason"].startswith("ERROR")        # the row is in the CSV before the stop
    (tmp_path / "STOP").unlink()
    with pytest.raises(ST.StopRun):
        O.call(None, "m", {}, {})
    AC.add_error_to_row, AC.append_row, O.call, AC._t2av_hooked = saved


def test_files_check():
    used = {"a": 19.5, "b": 2.0}
    out, bad = F.check({"K1": ("a", 0.4), "K2": ("b", 3.0)}, 20.0, 0.3, used=lambda c: used[c])
    assert out["K1"] == (19.5, 0.5, 0.4) and len(bad) == 1 and bad[0].startswith("K1")


def test_rundir_new_only_and_readme(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value-123")
    d = RD.create("hdepic_main_row1", root=tmp_path)
    assert d.name.startswith("hdepic_main_row1_20") and len(d.name.split("_")[-1]) == 8
    with pytest.raises(FileExistsError):
        RD.create("hdepic_main_row1", root=tmp_path)
    p = tmp_path / "prompts.json"; p.write_text("[]")
    RD.write_readme(d, purpose="row 1", condition="media_only", model="gemini-3.6-flash", thinking="high", sets=["p3p9"],
                    prompts={"prompts p3p9": str(p)}, caches={"captions": str(p)}, keys={"shard 0": K.key_id("GEMINI_API_KEY", "secret-value-123")},
                    command=["t2av-eval", "judge"])
    RD.event(d, "STOP: x")
    txt = (d / "README.md").read_text()
    for s in ("gemini-3.6-flash", "thinking: high", "run date:", "md5", "## cache versions", "GEMINI_API_KEY:", "STOP: x", "in-code judge/media/core.py"):
        assert s in txt
    assert "secret-value-123" not in txt and "secret-value-123" not in (d / "run.json").read_text()
