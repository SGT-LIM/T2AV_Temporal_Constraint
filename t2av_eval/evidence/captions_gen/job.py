"""AVoCaDO caption job (qrsh GPU only):  t2av-eval evidence captions -- --target gen149 --hardware a100_80g --name gen149_caps

Runs the moved caption runner (captions_gen/runner.py) in the qwen3_cap env with the recorded settings of the target
(config/captions_gen.yaml) into a NEW dir WORK/captions/<name>_<YYYYMMDD>/<recorded file name>; existing caption files
are never written. The README records the target, hardware profile, GPU name and memory (nvidia-smi), host, env, runner
md5 and the exact command, because captions differ across GPU hardware.
  --sample-seed N   one sampled caption per video (T2AV_CAPTION_SAMPLE_SEED, temperature 0.7, top_p 0.9), as the screening samples
  --start-index / --end-index   a shard of the sorted video list, as the 10/31 A6000 fallback
"""
import argparse, os, subprocess, sys
from pathlib import Path

import yaml

from t2av_eval import paths as _P
from t2av_eval.run import rundir as _rd

CFG = yaml.safe_load(open(_P.CONFIG / "captions_gen.yaml"))
RUNNER = Path(__file__).resolve().parent / "runner.py"


def gpu():
    r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True)
    return r.stdout.strip().replace("\n", "; ") if r.returncode == 0 else "nvidia-smi failed"


def command(target, out_json, start=None, end=None):
    t = CFG["targets"][target]
    root, rel = t["videos"].split(":", 1)
    vids = str({"data": _P.DATA, "inputs": _P.INPUTS}[root] / rel)
    cmd = [CFG["python"], "-u", str(RUNNER), *CFG["runner_args"], "--videos-dir", vids, "--output-json", str(out_json), "--fps", str(t["fps"])]
    if start is not None:
        cmd += ["--start-index", str(start)]
    if end is not None:
        cmd += ["--end-index", str(end)]
    return cmd


def main(argv=None):
    ap = argparse.ArgumentParser(prog="t2av-eval evidence captions")
    ap.add_argument("--target", required=True, choices=sorted(CFG["targets"]))
    ap.add_argument("--hardware", required=True, choices=sorted(CFG["hardware"]))
    ap.add_argument("--name", required=True)
    ap.add_argument("--sample-seed", type=int)
    ap.add_argument("--start-index", type=int); ap.add_argument("--end-index", type=int)
    a = ap.parse_args(argv)
    if not os.environ.get("JOB_ID"):
        sys.exit(f"captions run on a GPU inside qrsh ({CFG['hardware'][a.hardware]['qrsh'] or 'see config/captions_gen.yaml'})")
    t, hw = CFG["targets"][a.target], CFG["hardware"][a.hardware]
    d = _rd.create(a.name, root=_P.WORK / "captions")
    name = t["recorded"] if a.sample_seed is None else t["recorded"].replace(".json", f"_s{a.sample_seed}.json")
    out = d / name
    cmd = command(a.target, out, a.start_index, a.end_index)
    T = os.environ.get("NSLOTS", "4")
    ff = CFG["ffmpeg"]
    env = dict(os.environ, PATH=f"{Path(CFG['python']).parent}:{ff}/bin:{os.environ.get('PATH', '')}",
               LD_LIBRARY_PATH=f"{ff}/lib:{CFG['cuda_lib']}:{os.environ.get('LD_LIBRARY_PATH', '')}", HF_HOME=CFG["hf_home"],
               PYTHONPATH=f"{_P.REPO}:{os.environ.get('PYTHONPATH', '')}", OMP_NUM_THREADS=T, MKL_NUM_THREADS=T, OPENBLAS_NUM_THREADS=T,
               NUMBA_NUM_THREADS=T, TOKENIZERS_PARALLELISM="false")
    env.update(hw["env"])
    if a.sample_seed is not None:
        env["T2AV_CAPTION_SAMPLE_SEED"] = str(a.sample_seed)
    g = gpu()
    _rd.write_readme(d, purpose=f"AVoCaDO captions, target {a.target}", condition="captions", model="AVoCaDO-Captioner/AVoCaDO",
                     thinking="-", sets=[a.target], prompts={"caption runner": str(RUNNER)}, caches={},
                     keys={"(no API key)": "-"}, command=cmd,
                     extra={"fps / style": f"{t['fps']} / plain", "decoding": "greedy" if a.sample_seed is None else
                            f"sampled, seed {a.sample_seed}, temperature 0.7, top_p 0.9", "hardware profile": f"{a.hardware}: {hw['recorded']}",
                            "GPU (nvidia-smi)": g, "host": os.uname().nodename, "job": os.environ.get("JOB_ID"), "env": hw["env"] or "-",
                            "recorded captions of this target": f"{t['recorded']} ({t['note']})", "python": CFG["python"]})
    with open(out.with_suffix(".log"), "w") as log:
        rc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
    n_err = sum(1 for l in open(out.with_suffix(".log")) if "ERROR" in l)
    _rd.event(d, f"end: exit {rc}, {n_err} ERROR lines in {out.with_suffix('.log').name}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
