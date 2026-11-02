"""Gemini controller backend: structured JSON, temperature / seed / thinking from config/controller.yaml. Inside a CLI run the
client is the paced client (t2av_eval.run.client), so the controller shares the run's per-key pacing and stop rule."""
import os

from t2av_eval.gate.controller.base import Controller


class GeminiController(Controller):
    backend = "gemini"

    def __init__(self, cfg):
        super().__init__(cfg)
        from google import genai
        self._client = genai.Client(api_key=os.environ[cfg["key_env"]])

    def _call(self, system, user, schema):
        from google.genai import types
        kw = dict(response_mime_type="application/json", response_json_schema=schema, system_instruction=system)
        for k in ("temperature", "seed"):
            if self.cfg.get(k) is not None:
                kw[k] = self.cfg[k]
        if self.cfg.get("thinking"):
            kw["thinking_config"] = types.ThinkingConfig(thinking_level=self.cfg["thinking"])
        resp = self._client.models.generate_content(model=self.cfg["model"], contents=[user], config=types.GenerateContentConfig(**kw))
        return resp.text or ""
