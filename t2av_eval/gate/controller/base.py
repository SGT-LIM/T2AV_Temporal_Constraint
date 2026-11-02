"""Controller interface. A backend answers choose(system, user, schema) with (parsed JSON, raw text); text in, JSON out.
Settings come from config/controller.yaml; a backend refuses to start while its model or key variable is unset."""
import json, os, re, time
from abc import ABC, abstractmethod

import yaml

from t2av_eval import paths as _P
from t2av_eval.run import stop as _stop

CONFIG = _P.CONFIG / "controller.yaml"

# pipeline_v4_2026-10-27.md section 1, stage 3: {event_id, axis, action, window, question, stop}
STAGE3_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "axis": {"type": "string", "enum": ["A", "V", "AVB", "TCR", "TCC"]},
        "action": {"type": "string"},
        "window": {"type": "array", "items": {"type": "number"}},
        "question": {"type": "string"},
        "stop": {"type": "boolean"},
    },
    "required": ["event_id", "axis", "action", "window", "question", "stop"],
}
RETRY_DELAYS = (30, 60, 120)


def load_config():
    return yaml.safe_load(open(CONFIG))


def parse_json(raw):
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw or "", re.S)
        return json.loads(m.group(0)) if m else {}


class Controller(ABC):
    backend = ""
    required = ()          # config keys a backend needs besides model and key_env

    def __init__(self, cfg):
        self.cfg = cfg
        for k in ("model", "key_env") + self.required:
            if not cfg.get(k):
                raise ValueError(f"controller backend {self.backend}: '{k}' is not set in config/controller.yaml")
        if not os.environ.get(cfg["key_env"], "").strip():
            raise RuntimeError(f"controller backend {self.backend}: {cfg['key_env']} is not set in the environment")

    @abstractmethod
    def _call(self, system, user, schema):
        """one attempt -> raw text"""

    def _transient(self, exc):
        return _stop.is_quota(exc) or 500 <= int(getattr(exc, "status_code", getattr(exc, "code", 0)) or 0) < 600

    def choose(self, system, user, schema=STAGE3_SCHEMA):
        """(parsed, raw); retries 30 / 60 / 120 s on 429 / 5xx; a failure after all retries goes to the stop rule"""
        for i, d in enumerate(RETRY_DELAYS + (None,)):
            try:
                raw = self._call(system, user, schema)
                return parse_json(raw), raw
            except Exception as e:
                if d is None or not self._transient(e):
                    _stop.on_final_error(e, where=f"controller {self.backend}")
                    raise
                time.sleep(d)

    def describe(self):
        """settings for the run README (no key)"""
        return {k: v for k, v in dict(self.cfg, backend=self.backend).items() if k != "key"}


def make(backend, cfg=None):
    cfg = (cfg or load_config())[backend]
    if backend == "gemini":
        from t2av_eval.gate.controller.gemini import GeminiController
        return GeminiController(cfg)
    if backend == "openai":
        from t2av_eval.gate.controller.openai import OpenAIController
        return OpenAIController(cfg)
    raise ValueError(f"unknown controller backend {backend}")
