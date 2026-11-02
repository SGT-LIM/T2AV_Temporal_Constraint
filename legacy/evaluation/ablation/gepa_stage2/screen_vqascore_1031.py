#!/usr/bin/env python3
"""Tool screening: VQAScore (t2v_metrics 3.0 CLIPT5Model, clip-flant5-xxl, default question template) on the V axis (10/31). GPU, env vqascore_1030. No judge calls.

Per row event: 4 frames evenly spaced inside the event's span (HD-EPIC: the annotated action span; generated: row 1 anchor
event_time_s +-0.5 s; else 4 frames evenly over the whole clip); text = the event's definition (prompt text, first sentence);
event score = the max over frames of VQAScore P("Yes" | "Does this figure show '<text>'?"). Row score = the weakest event.
FAIL when the row score is below the threshold (5% of p1p2 V PASS rows below it).
  python gepa_stage2/screen_vqascore_1031.py run --set p1p2|p3p9|220|149 [--shard k --nshards n]
  python gepa_stage2/screen_vqascore_1031.py threshold | report      (with the t2av_eval python)
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, re, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
TOOL = "vqascore"
OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/screen_1031")
NF = 4


def duration(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True)
    return float(r.stdout.strip())


def frames(video, t0, t1, d):
    ts = np.linspace(t0, t1, NF + 2)[1:-1]
    out = []
    for i, t in enumerate(ts):
        f = d / f"f{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", str(f)], check=True)
        out.append(str(f))
    return out


def stage_run(a):
    rows = json.load(open(OUT / "rows" / f"{a.set}.json"))
    rows = [r for r in rows if r["axis"] == "V"][a.shard::a.nshards]
    # t2v_metrics/__init__ imports every backend (LLaVA, flash_attn, ...); load only CLIP-FlanT5 by stubbing the package dirs
    import types, importlib.util, torch
    base = importlib.util.find_spec("t2v_metrics").submodule_search_locations[0]
    for name, sub in (("t2v_metrics", ""), ("t2v_metrics.models", "/models"), ("t2v_metrics.models.vqascore_models", "/models/vqascore_models")):
        m = types.ModuleType(name); m.__path__ = [base + sub]; sys.modules[name] = m
    from t2v_metrics.models.vqascore_models.clip_t5_model import CLIPT5Model
    model = CLIPT5Model(model_name="clip-flant5-xxl", device="cuda", cache_dir="/projectnb/ivc-ml/youngsun/.hf_cache/t2v_metrics")

    def score(images, texts):
        with torch.no_grad():
            return model.forward(images=images, texts=texts * len(images))
    od = OUT / TOOL / a.set
    od.mkdir(parents=True, exist_ok=True)
    cache, out = {}, []
    for k, r in enumerate(rows):
        sc = {}
        dur = duration(r["video"])
        for e in r["events"]:
            text = re.split(r"(?<=[.!?])\s", (r["definitions"].get(e) or "").strip())[0]
            w = r["windows"].get(e)
            t0, t1 = (max(0.0, w[0]), min(dur, w[1])) if w and w[1] > w[0] else (0.0, dur)
            key = (r["video"], round(t0, 2), round(t1, 2), text)
            if key not in cache:
                with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
                    fr = frames(r["video"], t0, t1, Path(td))
                    cache[key] = float(score(images=fr, texts=[text]).max().item())
            sc[e] = cache[key]
        out.append(dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis="V", y=r["y"],
                        score=min(sc.values()) if sc else np.nan, per_event=json.dumps(sc)))
        if k % 50 == 0:
            print(f"[vqascore] {a.set} {k + 1}/{len(rows)}", flush=True)
    pd.DataFrame(out).to_csv(od / f"scores_shard{a.shard}.csv", index=False)
    print(f"[vqascore] {a.set} done {len(rows)}", flush=True)


def load(which):
    fs = sorted((OUT / TOOL / which).glob("scores_shard*.csv"))
    return pd.concat(pd.read_csv(f) for f in fs) if fs else pd.DataFrame()


def stage_threshold(a):
    sys.path.insert(0, str(HERE))
    import screen_common_1031 as S
    d = load("p1p2")
    print("threshold V", S.write_threshold(TOOL, "V", d[d.y == "yes"].score.dropna().tolist(), low_is_fail=True,
                                           note="row score = min over events of max over 4 in-span frames of VQAScore(definition)"))


def stage_report(a):
    sys.path.insert(0, str(HERE))
    import screen_common_1031 as S
    th = json.load(open(OUT / TOOL / "thresholds.json"))["V"]["threshold"]
    d = pd.concat([load(s) for s in ("p1p2", "p3p9", "220", "149")])
    d["tool_fail"] = np.where(d.score.isna(), np.nan, d.score < th)
    S.report(TOOL, d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "threshold", "report"])
    ap.add_argument("--set", default="p1p2")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
