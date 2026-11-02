"""One shard of a media condition: python -m t2av_eval.run.shard -- <run_agentic_eval argv>
The launcher sets T2AV_RUN_DIR, T2AV_SHARD, T2AV_KEY_ID, T2AV_CALLS_PER_HOUR and GEMINI_API_KEY. This installs the paced client
(stop check + per-key pacing per attempt) and the stop hooks, then runs the moved run_agentic_eval unchanged.
Exit code 3 = stopped by the stop rule."""
import sys

from t2av_eval.run import client as _client
from t2av_eval.run import stop as _stop


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--":
        argv = argv[1:]
    _client.install()
    _client.install_stop_hooks()
    from t2av_eval.judge.media import runner
    sys.argv = ["run_agentic_eval.py"] + argv
    try:
        runner.main()
    except _stop.StopRun as e:
        print(f"[STOP] {e}", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
