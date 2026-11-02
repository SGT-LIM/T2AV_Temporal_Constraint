"""OpenAI controller backend (third-controller experiment): chat completions with a JSON-schema response format.
Model, reasoning effort, key variable and service tier come from config/controller.yaml; a null service tier sends none
(the account default). Temperature / seed are sent only when set in the config (reasoning models may reject them).
Pacing: inside a CLI run the backend takes a slot from <run dir>/.pace/<key id> like the Gemini keys."""
import hashlib, os

from t2av_eval.gate.controller.base import Controller
from t2av_eval.run.pacing import Limiter


class OpenAIController(Controller):
    backend = "openai"
    required = ("reasoning_effort",)   # the experiment runs at the lowest effort; refusing beats silently sending the default

    def __init__(self, cfg, client=None):
        super().__init__(cfg)
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ[cfg["key_env"]])
        self._client = client
        key = os.environ[cfg["key_env"]]
        self.key_id = f"{cfg['key_env']}:{hashlib.sha256(key.encode()).hexdigest()[:8]}"
        d, n = os.environ.get("T2AV_RUN_DIR"), os.environ.get("T2AV_CALLS_PER_HOUR")
        self._lim = Limiter(os.path.join(d, ".pace", self.key_id.replace(":", "_")), int(n)) if d and n else None

    def request(self, system, user, schema):
        kw = dict(model=self.cfg["model"], messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                  response_format={"type": "json_schema", "json_schema": {"name": "controller_choice", "schema": schema}})
        if self.cfg.get("reasoning_effort"):
            kw["reasoning_effort"] = self.cfg["reasoning_effort"]
        if self.cfg.get("service_tier"):
            kw["service_tier"] = self.cfg["service_tier"]
        for k in ("temperature", "seed"):
            if self.cfg.get(k) is not None:
                kw[k] = self.cfg[k]
        return kw

    def _call(self, system, user, schema):
        from t2av_eval.run import stop as _stop
        _stop.check()
        if self._lim is not None:
            self._lim.acquire()
        resp = self._client.chat.completions.create(**self.request(system, user, schema))
        return resp.choices[0].message.content or ""
