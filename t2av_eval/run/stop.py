"""Stop rule (main checkout, 11/02): a call that fails after ALL its retries with 429 / RESOURCE_EXHAUSTED stops the run.
A 429 inside a retry is not a stop; other failures stay error rows / error records as before.

The first such failure writes <run dir>/STOP (time, shard, key id, where, the error) and raises StopRun; every other shard
raises StopRun at its next call attempt. StopRun is a BaseException, so the judge code's `except Exception` handlers (error
rows, error records) do not swallow it. Outside a CLI run (T2AV_RUN_DIR unset) nothing here does anything.
"""
import json, os, time
from pathlib import Path


class StopRun(BaseException):
    pass


def run_dir():
    d = os.environ.get("T2AV_RUN_DIR")
    return Path(d) if d else None


def stop_file():
    d = run_dir()
    return d / "STOP" if d else None


def check():
    f = stop_file()
    if f is not None and f.exists():
        raise StopRun(f"run stopped: {f.read_text().strip()[:300]}")


def is_quota(exc):
    s = f"{type(exc).__name__}: {exc}"
    return 429 in (getattr(exc, "code", None), getattr(exc, "status_code", None)) or "429" in s and ("RESOURCE_EXHAUSTED" in s or "ClientError" in s) or "RESOURCE_EXHAUSTED" in s


def on_final_error(exc, where=""):
    """called with the exception of a call that failed after all its retries"""
    f = stop_file()
    if f is None or not is_quota(exc):
        return
    rec = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S%z"), shard=os.environ.get("T2AV_SHARD", ""), key=os.environ.get("T2AV_KEY_ID", ""),
               where=where, error=f"{type(exc).__name__}: {str(exc)[:500]}")
    try:
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "w") as h:
            h.write(json.dumps(rec) + "\n")
    except FileExistsError:
        pass
    raise StopRun(f"stop: {rec['error']}")
