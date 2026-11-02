"""Launch a media condition (row 1 / 2 / 3) on one or more sets: new run dir, README, Files check, one process per shard.

Shards: as the recorded launchers (n = number of videos of the set, step = ceil(n / shards), shard k = [k*step, (k+1)*step)).
Keys: shard i uses key i mod n_keys (GEMINI_API_KEY, GEMINI_API_KEY_2, ...); each key has its own calls-per-hour budget.
The launcher stays in the foreground (run it inside screen on a login node) and prints progress every minute; when STOP
appears it waits for every shard to exit, then writes the summary to the README.
"""
import json, math, os, subprocess, sys, time
from pathlib import Path

import pandas as pd
import yaml

from t2av_eval import paths as _P
from t2av_eval.judge import conditions as C
from t2av_eval.run import files as _files
from t2av_eval.run import keys as _keys
from t2av_eval.run import rundir as _rd

RUNS = yaml.safe_load(open(_P.CONFIG / "runs.yaml"))
THREADS = dict(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", NUMBA_NUM_THREADS="1")


def videos(d):
    return sorted(p for p in Path(d).rglob("*.mp4"))          # = core.find_video_files for real files


def ok_items(run, set_name):
    """item ids of a previous run with a row that is not an error row; --items-from reruns every other item"""
    fs = [f for f in sorted(Path(run).glob(f"{set_name}_shard*.csv")) if not f.name.endswith("_per_event.csv")]
    done = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in fs]) if fs else pd.DataFrame(columns=["item_id", "overall_reason"])
    ok = set(done[~done.overall_reason.str.startswith("ERROR")].item_id)
    return ok


def plan(condition, set_names, shards=None, items_from=None, run=None):
    out = []
    for s in set_names:
        info = C.set_info(s)
        args, env = C.media_command(condition, s)
        vids = videos(info["videos"])
        if items_from:
            ok = ok_items(items_from, s)
            P = [x for x in json.load(open(info["prompts"])) if x["item_id"] not in ok]
            if run is not None:
                sub = Path(run) / f"prompts_{s}_rerun.json"
                json.dump(P, open(sub, "w"), indent=1, ensure_ascii=False)
                args[args.index("--prompt-json") + 1] = str(sub)
            keep = {x["item_id"] for x in P}
            from t2av_eval.judge.media import core as NE
            vids_needed = [v for v in vids if NE.infer_item_id_from_path(v) in keep]
        else:
            vids_needed = vids
        ns = shards or info["shards"]
        step = math.ceil(len(vids) / ns) if vids else 0
        for k in range(ns):
            a, b = k * step, min((k + 1) * step, len(vids))
            if a >= b:
                continue
            out.append(dict(set=s, shard=k, start=a, end=b, args=args, env=env, info=info,
                            videos=[v for v in vids[a:b] if v in set(vids_needed)]))
    return out


def run_media(condition, set_names, name, n_keys=None, calls_per_hour=None, shards=None, items_from=None, dry_run=False):
    keys = _keys.gemini_keys()
    if not keys:
        sys.exit("no Gemini key: set GEMINI_API_KEY (and GEMINI_API_KEY_2, ... for rotation) in the environment")
    keys = keys[: n_keys or len(keys)]
    cph = calls_per_hour or RUNS["pacing"]["calls_per_hour_per_key"]
    if dry_run:
        for p in plan(condition, set_names, shards):
            name_, val = _keys.for_shard(p["shard"], keys)
            print(p["set"], p["shard"], p["start"], p["end"], _keys.key_id(name_, val), " ".join(p["args"][:4]), "...", p["env"])
        return None
    d = _rd.create(name)
    P = plan(condition, set_names, shards, items_from, run=d)
    # Gemini Files storage, per key, before launch
    from google import genai
    need = {}
    for i, p in enumerate(P):
        kn, kv = _keys.for_shard(i, keys)
        kid = _keys.key_id(kn, kv)
        c, n = need.get(kid, (None, 0.0))
        need[kid] = (c or genai.Client(api_key=kv), n + _files.needed_gb(p["videos"]))
    up = RUNS["uploads"]
    usage, bad = _files.check(need, up["files_cap_gb"], up["files_margin_gb"])
    info0 = P[0]["info"] if P else {}
    _rd.write_readme(
        d, purpose=f"{C.ROW[condition]} ({condition})", condition=condition, model="gemini-3.6-flash", thinking="high", sets=set_names,
        prompts={f"prompts {p['set']}": p["args"][p["args"].index("--prompt-json") + 1] for p in P},
        caches=dict({"audio evidence cache": os.environ.get("T2AV_AUDIO_EVIDENCE_CACHE", str(_P.DATA / "audio_evidence_cache"))}
                    if "--audio-evidence-mode" in P[0]["args"] and "whisper_flam" in P[0]["args"] else {},
                    **{f"captions {p['set']}": p["info"]["captions"] for p in P if "--caption-external-json" in p["args"]},
                    **({"synchformer sections": info0.get("sync")} if any("T2AV_SYNC_EVIDENCE_JSON" in p["env"] for p in P) else {})),
        keys={f"{p['set']} shard {p['shard']}": _keys.key_id(*_keys.for_shard(i, keys)) for i, p in enumerate(P)},
        command=_rd.argv(),
        extra={"pacing": f"{cph} calls / hour per key ({len(keys)} key(s))", "stop rule": RUNS["stop"]["rule"],
               "delete uploads after use": RUNS["uploads"]["delete_after_use"],
               "files storage before launch (used, free, needed GB)": json.dumps(usage),
               "rerun of": str(items_from) if items_from else "-", "shards": len(P)})
    if bad:
        _rd.event(d, "NOT LAUNCHED: Gemini Files storage: " + "; ".join(bad))
        sys.exit(1)
    procs = []
    for i, p in enumerate(P):
        kn, kv = _keys.for_shard(i, keys)
        env = _keys.shard_env(os.environ, kn, kv)
        env.update(p["env"], THREADS, T2AV_RUN_DIR=str(d), T2AV_SHARD=f"{p['set']}_shard{p['shard']}", T2AV_CALLS_PER_HOUR=str(cph),
                   PYTHONUNBUFFERED="1")
        if RUNS["uploads"]["delete_after_use"]:
            env["T2AV_DELETE_UPLOADS"] = "1"
        out = d / f"{p['set']}_shard{p['shard']}.csv"
        cmd = [sys.executable, "-m", "t2av_eval.run.shard", "--", *p["args"], "--output-csv", str(out),
               "--start-index", str(p["start"]), "--end-index", str(p["end"])]
        with open(d / "README.md", "a") as f:
            f.write(" ".join(f"{k}={v}" for k, v in p["env"].items()) + " " + " ".join(cmd[1:]) + "\n")
        log = open(out.with_suffix(".log"), "w")
        procs.append((p, subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=d, start_new_session=True)))
    _rd.event(d, f"started {len(procs)} shards")
    return watch(d, procs)


def rows_done(d):
    n = e = 0
    for f in Path(d).glob("*_shard*.csv"):
        if f.name.endswith("_per_event.csv"):
            continue
        t = pd.read_csv(f, dtype=str, keep_default_na=False)
        n += len(t); e += int(t.get("overall_reason", pd.Series(dtype=str)).str.startswith("ERROR").sum())
    return n, e


def watch(d, procs, every=60):
    stopped = False
    while any(p.poll() is None for _, p in procs):
        time.sleep(every)
        if not stopped and (d / "STOP").exists():
            stopped = True
            _rd.event(d, f"STOP: {(d / 'STOP').read_text().strip()}; waiting for every shard to exit")
        n, e = rows_done(d)
        print(f"[{d.name}] {time.strftime('%H:%M')} rows {n} (error rows {e}); shards running {sum(p.poll() is None for _, p in procs)}", flush=True)
    codes = [p.returncode for _, p in procs]
    n, e = rows_done(d)
    _rd.event(d, f"end: rows {n}, error rows {e}, shards exit codes {sorted(set(codes))}" + (" (3 = stopped by the stop rule)" if 3 in codes else "")
              + (f"; rerun the rest with --items-from {d}" if stopped or e else ""))
    return 3 if stopped else (1 if any(c not in (0, 3) for c in codes) else 0)
