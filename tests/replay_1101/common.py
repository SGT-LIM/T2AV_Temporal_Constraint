"""Shared by freeze.py and tests/test_replay_1101.py: build the replay subprocess for one recorded 11/01 command."""
import os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRUB = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "T2AV_AUDIO_EVIDENCE_CACHE", "T2AV_SYNC_EVIDENCE_JSON", "T2AV_AUDIO_EVIDENCE_CACHE_ONLY")


def clean_env(**extra):
    """the caller's environment without API keys or evidence overrides, plus extra"""
    env = {k: v for k, v in os.environ.items() if k not in SCRUB}
    env.update(extra)
    return env


def rows_cmd(fx, code, row, s, cmd, out_csv, report):
    """(argv, env) replaying recorded command `cmd` of (row, set s) on fixture fx with the code in `code`"""
    fx = Path(fx)
    args = list(cmd["args"])
    args[args.index("--prompt-json") + 1] = str(fx / "prompts" / f"{s}.json")
    args[args.index("--outputs-dir") + 1] = str(fx / "videos" / s)
    env = clean_env(**{k: v for k, v in cmd["env"].items() if k != "T2AV_SYNC_EVIDENCE_JSON"})
    if row == "row2":
        args[args.index("--caption-external-json") + 1] = str(fx / "row2_inputs/captions" / f"{s}.json")
        env.update(T2AV_SYNC_EVIDENCE_JSON=str(fx / "row2_inputs/sync_sections.json"),
                   T2AV_AUDIO_EVIDENCE_CACHE=str(fx / "row2_inputs/audio_cache"))
    argv = [sys.executable, str(HERE / "run_rows.py"), "--code", str(code), "--stored-csv", str(fx / "rows" / row / f"{s}.csv"),
            "--report", str(report), "--workdir", str(Path(out_csv).parent / "cwd"), "--", *args, "--output-csv", str(out_csv)]
    return argv, env


def stage2_cmd(fx_copy, code, report):
    return [sys.executable, str(HERE / "run_stage2.py"), "--code", str(code), "--fixture", str(fx_copy), "--report", str(report)], clean_env()
