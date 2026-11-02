"""Controller backends: text only, settings from config/controller.yaml, refusal while a required value is unset."""
import inspect
from types import SimpleNamespace

import pytest

from t2av_eval.gate import controller as CT
from t2av_eval.gate.controller.openai import OpenAIController

CFG = dict(model="gpt-6-astra-test", reasoning_effort="minimal-test", key_env="OPENAI_API_KEY", service_tier=None)


class FakeOpenAI:
    def __init__(self):
        self.kw = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.kw = kw
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"event_id": "event_2", "axis": "A", '
                                        '"action": "flam", "window": [1.0, 3.0], "question": "close drawer", "stop": false}'))])


def test_config_openai_unset_values_refuse(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    cfg = CT.load_config()["openai"]
    assert cfg["key_env"] == "OPENAI_API_KEY" and cfg["service_tier"] is None
    if cfg["model"] is None or cfg["reasoning_effort"] is None:
        with pytest.raises(ValueError):
            CT.make("openai")


def test_openai_request_and_choose(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.delenv("T2AV_RUN_DIR", raising=False)
    fake = FakeOpenAI()
    c = OpenAIController(dict(CFG), client=fake)
    parsed, raw = c.choose("sys", "user text")
    assert parsed["axis"] == "A" and parsed["window"] == [1.0, 3.0]
    kw = fake.kw
    assert kw["model"] == "gpt-6-astra-test" and kw["reasoning_effort"] == "minimal-test"
    assert "service_tier" not in kw and "temperature" not in kw and "seed" not in kw
    assert [m["role"] for m in kw["messages"]] == ["system", "user"]
    assert kw["response_format"]["json_schema"]["schema"] == CT.STAGE3_SCHEMA
    assert "OPENAI_API_KEY:" in c.key_id and "k" != c.key_id.split(":")[1]


def test_missing_effort_or_key_refuses(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    with pytest.raises(ValueError):
        OpenAIController(dict(CFG, reasoning_effort=None), client=FakeOpenAI())
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(RuntimeError):
        OpenAIController(dict(CFG), client=FakeOpenAI())


def test_interface_is_text_only():
    params = set(inspect.signature(CT.Controller.choose).parameters)
    assert params == {"self", "system", "user", "schema"}


def test_media_judge_is_gemini_only(monkeypatch):
    from t2av_eval.judge.media import common as AC
    ctx = SimpleNamespace(config={"judge_backend": "openai"})
    with pytest.raises(RuntimeError, match="not part of the t2av_eval package"):
        AC.call_gemini_json(ctx, "s", "u", {})
