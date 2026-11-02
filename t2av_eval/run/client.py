"""Wrap google.genai.Client for a CLI run: before every generate_content attempt and every upload, the stop rule is checked
and the per-key pacing slot is taken. Arguments and return values pass through unchanged, so prompts and labels are the same
as without the wrapper (tests/test_replay_1101.py runs the CLI path too).

install() replaces google.genai.Client in the current process; the judge code builds its clients as before.
"""
import os

from t2av_eval.run import stop as _stop
from t2av_eval.run.pacing import Limiter


class _Models:
    def __init__(self, inner, limiter):
        self._inner, self._lim = inner, limiter

    def generate_content(self, *a, **k):
        _stop.check()
        if self._lim is not None:
            self._lim.acquire()
        return self._inner.generate_content(*a, **k)

    def __getattr__(self, n):
        return getattr(self._inner, n)


class _Files:
    def __init__(self, inner):
        self._inner = inner

    def upload(self, *a, **k):
        _stop.check()
        return self._inner.upload(*a, **k)

    def __getattr__(self, n):
        return getattr(self._inner, n)


class PacedClient:
    def __init__(self, inner, limiter):
        self._inner = inner
        self.models = _Models(inner.models, limiter)
        self.files = _Files(inner.files)

    def __getattr__(self, n):
        return getattr(self._inner, n)


def limiter_from_env():
    d, kid, n = os.environ.get("T2AV_RUN_DIR"), os.environ.get("T2AV_KEY_ID"), os.environ.get("T2AV_CALLS_PER_HOUR")
    if not (d and kid and n):
        return None
    return Limiter(os.path.join(d, ".pace", kid.replace(":", "_")), int(n))


def install():
    import google.genai as genai
    if getattr(genai.Client, "_t2av_paced", False):
        return
    orig, lim = genai.Client, limiter_from_env()

    def factory(*a, **k):
        return PacedClient(orig(*a, **k), lim)
    factory._t2av_paced = True
    genai.Client = factory


def install_stop_hooks():
    """route every call that failed after its retries to the stop rule, without editing the judge code:
    media path: the item-level error row (common.add_error_to_row) is written first (common.append_row), then the rule runs;
    stage 2 / vcheck: obs_judge.call holds the retry loop, so an exception leaving it is a final failure."""
    from t2av_eval.judge.media import common as AC
    from t2av_eval.judge.stage2 import obs_judge as O
    if getattr(AC, "_t2av_hooked", False):
        return
    pending = {}
    add, app, call = AC.add_error_to_row, AC.append_row, O.call

    def add_error_to_row(row, exc, *a, **k):
        pending[id(row)] = exc
        out = add(row, exc, *a, **k)
        pending[id(out)] = exc
        return out

    def append_row(path, row, *a, **k):
        r = app(path, row, *a, **k)
        exc = pending.pop(id(row), None)
        if exc is not None:
            _stop.on_final_error(exc, where=f"media item {row.get('item_id', '')}")
        return r

    def obs_call(*a, **k):
        try:
            return call(*a, **k)
        except Exception as e:
            _stop.on_final_error(e, where="stage-2 call")
            raise

    AC.add_error_to_row, AC.append_row, O.call = add_error_to_row, append_row, obs_call
    AC._t2av_hooked = True
