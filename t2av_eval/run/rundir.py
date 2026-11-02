"""Run directories: <work_root>/results/<name>_<YYYYMMDD>, always new (an existing dir is refused, never reused or
overwritten), with a README.md that records what CLAUDE.md asks for: model string, thinking, prompt version (prompt files and
in-code prompt modules, md5), cache versions, start time, host, key ids, the exact command. Events (shard starts, STOP, end
summary) are appended as they happen."""
import hashlib, json, socket, subprocess, sys, time
from pathlib import Path

from t2av_eval import paths as _P

PKG = Path(__file__).resolve().parents[1]
PROMPT_MODULES = ["judge/media/core.py", "judge/media/common.py", "judge/media/orchestrator.py", "judge/media/axes/audio.py",
                  "judge/media/axes/visual.py", "judge/media/axes/binding.py", "judge/media/axes/temporal_relation.py",
                  "judge/media/axes/temporal_count.py", "judge/media/axes/compliance.py", "evidence/captions.py",
                  "judge/stage2/obs_judge.py", "judge/stage2/two_stage.py", "judge/stage2/hdepic.py", "judge/stage2/generated.py"]


def md5(path):
    p = Path(path)
    return hashlib.md5(p.read_bytes()).hexdigest() if p.is_file() else "missing"


def git_state():
    def g(*a):
        r = subprocess.run(["git", "-C", str(_P.REPO), *a], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else "?"
    return dict(head=g("rev-parse", "--short", "HEAD"), dirty=bool(g("status", "--porcelain", "--", "t2av_eval")))


def create(name, root=None):
    if any(ch in name for ch in "/ "):
        raise ValueError(f"run name must not contain '/' or spaces: {name}")
    d = Path(root or _P.WORK / "results") / f"{name}_{time.strftime('%Y%m%d')}"
    if d.exists():
        raise FileExistsError(f"run dir exists, not reusing it: {d} (pick another --name)")
    d.mkdir(parents=True)
    return d


def write_readme(d, *, purpose, condition, model, thinking, sets, prompts, caches, keys, command, extra=None):
    """prompts: {label: path}; caches: {label: path or description}; keys: {shard or worker label: key id}"""
    g = git_state()
    L = [f"# {Path(d).name}", "",
         f"- purpose: {purpose}",
         f"- condition: {condition}",
         f"- run date: {time.strftime('%Y-%m-%d')} (start {time.strftime('%Y-%m-%dT%H:%M:%S%z')} on {socket.gethostname()})",
         f"- model: {model}; thinking: {thinking}; temperature 0, seed 42 (in-code call settings)",
         f"- sets: {', '.join(sets)}",
         f"- code: t2av_eval at git {g['head']}{' + uncommitted edits in t2av_eval/' if g['dirty'] else ''}", "",
         "## prompt version", ""]
    L += [f"- {k}: {v} (md5 {md5(v)})" for k, v in prompts.items()]
    L += [f"- in-code {m}: md5 {md5(PKG / m)}" for m in PROMPT_MODULES]
    L += ["", "## cache versions", ""]
    for k, v in caches.items():
        p = Path(str(v))
        L.append(f"- {k}: {v}" + (f" (md5 {md5(p)})" if p.is_file() else (f" ({sum(1 for _ in p.iterdir())} entries at start)" if p.is_dir() else "")))
    L += ["", "## keys (variable name : sha256 prefix; the keys themselves are not recorded)", ""]
    L += [f"- {k}: {v}" for k, v in keys.items()]
    if extra:
        L += ["", "## settings", ""] + [f"- {k}: {v}" for k, v in extra.items()]
    L += ["", "## command", "", "```", " ".join(command), "```", "", "## events", ""]
    (Path(d) / "README.md").write_text("\n".join(L) + "\n")
    json.dump(dict(condition=condition, model=model, thinking=thinking, sets=sets, prompts=prompts, caches={k: str(v) for k, v in caches.items()},
                   keys=keys, command=command, git=g, extra=extra or {}), open(Path(d) / "run.json", "w"), indent=1)


def event(d, text):
    with open(Path(d) / "README.md", "a") as f:
        f.write(f"- {time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")
    print(f"[{Path(d).name}] {text}", flush=True)


def argv():
    return [Path(sys.argv[0]).name] + sys.argv[1:]
