#!/usr/bin/env python3
# Replaced by t2av_eval/screening/clap.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Tool screening: CLAP on the A axis (10/31). GPU, env t2av_eval. No judge calls.

Per sounding_action event of the row: query = the event's first pipeline FLAM query (flam_audio._queries_for_label), CLAP
(Tool_Use/clap_audio, laion/clap-htsat-unfused, temporal mode, 0.75 s windows, 0.5 s hop, up to 200 windows = the whole 25 s clip); event score = the
max window cosine similarity. Row score = the weakest sounding event; rows without a sounding event (speech-only) get no score.
FAIL when the row score is below the threshold (5% of p1p2 A PASS rows below it).
  python gepa_stage2/screen_clap_1031.py run --set p1p2|p3p9|220|149 [--shard k --nshards n]
  python gepa_stage2/screen_clap_1031.py threshold        # from p1p2 only; must run before 'report'
  python gepa_stage2/screen_clap_1031.py report
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "Tool_Use"))
import screen_common_1031 as S

TOOL = "clap"


def stage_run(a):
    import clap_audio as CA
    import flam_audio as FA
    od = S.OUT / TOOL / a.set
    od.mkdir(parents=True, exist_ok=True)
    R = [r for r in S.rows(a.set) if r["axis"] == "A"][a.shard::a.nshards]
    cache = {}
    out = []
    for k, r in enumerate(R):
        snd = [s for s in r["events"] if s["kind"] == "sounding_action"]
        if not snd:
            out.append(dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis="A", y=r["y"], score=np.nan, per_event="{}"))
            continue
        qs = {s["event_id"]: FA._queries_for_label("sounding_action", s["label"])[0] for s in snd}
        sc = {}
        for e, q in qs.items():
            key = (r["video"], q)
            if key not in cache:
                ev = CA.extract_clap_evidence(r["video"], queries=[q], mode="temporal", window_seconds=0.75, hop_seconds=0.5, device=os.environ.get("SCREEN_DEVICE", "cuda"),
                                              max_frames=200)
                fr = [f["scores"][q] for f in ev.get("frames", [])]
                cache[key] = float(max(fr)) if fr else np.nan
            sc[e] = cache[key]
        out.append(dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis="A", y=r["y"], score=min(sc.values()),
                        per_event=json.dumps(sc)))
        if k % 50 == 0:
            print(f"[clap] {a.set} {k + 1}/{len(R)}", flush=True)
            pd.DataFrame(out).to_csv(od / f"scores_shard{a.shard}.partial.csv", index=False)
    pd.DataFrame(out).to_csv(od / f"scores_shard{a.shard}.csv", index=False)
    print(f"[clap] {a.set} done {len(R)}", flush=True)


def load(which):
    fs = sorted(f for f in (S.OUT / TOOL / which).glob("scores_shard*.csv") if not f.name.endswith(".partial.csv"))   # 11/02: skip checkpoints
    return pd.concat(pd.read_csv(f) for f in fs) if fs else pd.DataFrame()


def stage_threshold(a):
    d = load("p1p2")
    thr = S.write_threshold(TOOL, "A", d[d.y == "yes"].score.dropna().tolist(), low_is_fail=True,
                            note="row score = min over sounding events of max-window CLAP cosine; first FLAM query")
    print("threshold A", thr)


def stage_report(a):
    th = json.load(open(S.OUT / TOOL / "thresholds.json"))["A"]["threshold"]
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
