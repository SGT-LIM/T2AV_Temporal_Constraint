#!/usr/bin/env python3
# Replaced by t2av_eval/screening/imagebind.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Tool screening: ImageBind (imagebind_huge) on the AVB axis (10/31). GPU, env imagebind_1030. No judge calls.

Per binding event: a segment of the clip around the event (HD-EPIC: the annotated action span +-1 s; generated: the row 1 anchor
event_time_s +-1 s, else the whole clip) is cut with ffmpeg (video and 16 kHz mono audio); ImageBind vision and audio embeddings
(the library's own loaders and transforms); event score = cosine(audio, vision). Row score = the weakest binding event.
FAIL when the row score is below the threshold (5% of p1p2 AVB PASS rows below it).
  python gepa_stage2/screen_imagebind_1031.py run --set p1p2|p3p9|220|149 [--shard k --nshards n]
  python gepa_stage2/screen_imagebind_1031.py threshold
  python gepa_stage2/screen_imagebind_1031.py report        # run with the t2av_eval python (pandas, new_eval)
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
TOOL = "imagebind"
OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/screen_1031")
PAD = 1.0


def cut(video, t0, t1, d):
    v, a = d / "seg.mp4", d / "seg.wav"
    ss = ["-ss", f"{max(0.0, t0):.3f}", "-to", f"{t1:.3f}"] if t1 is not None else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ss, "-i", video, "-an", "-c:v", "libx264", "-preset", "ultrafast", str(v)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ss, "-i", video, "-vn", "-ac", "1", "-ar", "16000", str(a)], check=True)
    return str(v), str(a)


def stage_run(a):
    # rows come from a json dump written by the t2av_eval env (this env has no new_eval dependencies)
    rows = json.load(open(OUT / "rows" / f"{a.set}.json"))
    rows = [r for r in rows if r["axis"] == "AVB"][a.shard::a.nshards]
    import torch
    from imagebind import data
    from imagebind.models import imagebind_model
    from imagebind.models.imagebind_model import ModalityType
    os.chdir(OUT / TOOL)                                  # the library downloads its checkpoint to ./.checkpoints
    model = imagebind_model.imagebind_huge(pretrained=True).eval().to("cuda")
    od = OUT / TOOL / a.set
    od.mkdir(parents=True, exist_ok=True)
    cache, out = {}, []
    for k, r in enumerate(rows):
        sc = {}
        for e in r["events"]:
            w = r["windows"].get(e)
            t0, t1 = (w[0] - PAD, w[1] + PAD) if w else (0.0, None)
            key = (r["video"], round(t0, 2), None if t1 is None else round(t1, 2))
            if key not in cache:
                with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
                    v, au = cut(r["video"], t0, t1, Path(td))
                    inp = {ModalityType.VISION: data.load_and_transform_video_data([v], "cuda"),
                           ModalityType.AUDIO: data.load_and_transform_audio_data([au], "cuda")}
                    with torch.no_grad():
                        emb = model(inp)
                    cache[key] = float(torch.nn.functional.cosine_similarity(emb[ModalityType.AUDIO], emb[ModalityType.VISION]).item())
            sc[e] = cache[key]
        out.append(dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis="AVB", y=r["y"],
                        score=min(sc.values()) if sc else np.nan, per_event=json.dumps(sc)))
        if k % 50 == 0:
            print(f"[imagebind] {a.set} {k + 1}/{len(rows)}", flush=True)
    pd.DataFrame(out).to_csv(od / f"scores_shard{a.shard}.csv", index=False)
    print(f"[imagebind] {a.set} done {len(rows)}", flush=True)


def load(which):
    fs = sorted((OUT / TOOL / which).glob("scores_shard*.csv"))
    return pd.concat(pd.read_csv(f) for f in fs) if fs else pd.DataFrame()


def stage_threshold(a):
    sys.path.insert(0, str(HERE))
    import screen_common_1031 as S
    d = load("p1p2")
    print("threshold AVB", S.write_threshold(TOOL, "AVB", d[d.y == "yes"].score.dropna().tolist(), low_is_fail=True,
                                             note="row score = min over binding events of ImageBind cos(audio, vision), event span +-1 s"))


def stage_report(a):
    sys.path.insert(0, str(HERE))
    import screen_common_1031 as S
    th = json.load(open(OUT / TOOL / "thresholds.json"))["AVB"]["threshold"]
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
