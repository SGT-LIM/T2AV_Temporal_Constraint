#!/usr/bin/env python3
# Replaced by t2av_eval/screening/qwen3s.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Tool screening: Qwen3-VL-8B timestamps, 3 sampled runs, on V / TCR / TCC (10/31). GPU, env vllm020. No judge calls.

Same model, prompt (qwen_ts_1030.prompt_for, HD-EPIC or generated header), frames (2 fps, <= 448x448) and parser as the 10/30 Qwen
pass, but sampled: do_sample, temperature 0.7, top_p 0.9, seeds 1 / 2 / 3 (torch seed = seed + crc32(video|actions)). One set of 3
runs per unique (video, action list); actions = the non-speech actions of the item, alphabetical.
Row scores (0-3 = number of the 3 samples that say FAIL):
  V    per non-speech row event: samples with no span for its action; row = the max over events (speech-only rows: no score)
  TCR  order items: samples whose first-span order of the ordered events differs from the prompt order (actions shared by two
       events are skipped; a sample missing an event is undetermined and not counted)
  TCC  samples where any counted event's span count differs from the required count
Threshold: the smallest k in 1..3 such that "score >= k" flags at most 5% of p1p2 PASS rows of the axis (none -> never FAIL).
  python gepa_stage2/screen_qwen3s_1031.py run --set 220|149|p1p2|p3p9 [--shard k --nshards n]
  python gepa_stage2/screen_qwen3s_1031.py score     # thresholds from p1p2 (written first), then report
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, sys, time, zlib
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))

TOOL = "qwen3s"
SEEDS = (1, 2, 3)


def actions_of(item):
    return sorted({e["action"] for e in item["events"] if e.get("modality") != "speech" and e.get("action")})


OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/screen_1031")


def stage_run(a):
    """vllm020 env (no pandas): rows come from the json dump written by screen_common_1031.dump."""
    import torch
    import qwen_ts_1030 as QT
    od = OUT / TOOL / a.set / "runs"
    od.mkdir(parents=True, exist_ok=True)
    R = [r for r in json.load(open(OUT / "rows" / f"{a.set}.json")) if r["axis"] in ("V", "TCR", "TCC")]
    jobs = sorted({(r["video"], tuple(r["actions"])) for r in R if r["actions"]})[a.shard::a.nshards]
    kind = "hdepic" if a.set in ("p1p2", "p3p9") else "generated"
    PQ = QT.parse_qwen()
    Q = QT.Runner()
    orig_generate = Q.model.generate
    for k, (vid, acts) in enumerate(jobs):
        key = zlib.crc32(f"{vid}|{'|'.join(acts)}".encode())
        f = od / f"{key}.json"
        if f.exists():
            continue
        text = QT.prompt_for(list(acts), kind)
        rec = dict(video=vid, actions=list(acts), prompt=text, samples=[])
        for s in SEEDS:
            torch.manual_seed(s + key)
            Q.model.generate = lambda *x, **kw: orig_generate(*x, **{**kw, "do_sample": True, "temperature": 0.7, "top_p": 0.9})
            r = Q.reply(vid, text)
            spans, err = PQ.parse(r, list(acts))
            rec["samples"].append(dict(seed=s, reply=r, spans=spans, err=err))
        Q.model.generate = orig_generate
        rec.update(model=QT.MODEL, fps=QT.FPS, temperature=0.7, top_p=0.9, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(f, "w"), indent=1)
        if k % 10 == 0:
            print(f"[qwen3s] {a.set} shard {a.shard}: {k + 1}/{len(jobs)}", flush=True)
    print(f"[qwen3s] {a.set} shard {a.shard} done {len(jobs)}", flush=True)


def _starts(sp):
    return [float(x[0]) for x in (sp or []) if isinstance(x, (list, tuple)) and len(x) >= 1]


def row_score(r, rec):
    if rec is None:
        return np.nan
    item, ax = r["item"], r["axis"]
    act = {e["id"]: e.get("action") for e in item["events"] if e.get("modality") != "speech"}
    eids = {k + 1: e["id"] for k, e in enumerate(item["events"])}
    v = (item.get("temporal_constraint") or {}).get("value") or {}
    n = 0
    det = 0
    for smp in rec["samples"]:
        sp = smp["spans"] or {}
        if ax == "V":
            evs = [eids[int(s["event_id"].split("_")[-1])] for s in r["events"] if s["kind"] != "speech" and s["event_id"].startswith("event_")]
            evs = [e for e in evs if act.get(e)]
            if not evs:
                return np.nan
            det += 1
            n += any(not _starts(sp.get(act[e])) for e in evs)
        elif ax == "TCR":
            seq = v.get("ordered_events") or v.get("sequence")
            if not seq:
                return np.nan
            seq = [e for e in seq if act.get(e) and sum(a == act[e] for a in act.values()) == 1]
            st = [_starts(sp.get(act[e])) for e in seq]
            if len(seq) < 2 or any(not x for x in st):
                continue
            det += 1
            first = [min(x) for x in st]
            n += first != sorted(first)
        else:
            req = v.get("event_counts") or ({v["event"]: int(v["count"])} if "event" in v else
                                             {e["id"]: int(v.get("count", 1)) for e in item["events"]})
            req = {e: c for e, c in req.items() if act.get(e)}
            if not req:
                return np.nan
            det += 1
            byact = {}
            for e, c in req.items():
                byact[act[e]] = byact.get(act[e], 0) + int(c)
            n += any(len(_starts(sp.get(a_))) != c for a_, c in byact.items())
    return n if det else np.nan


def stage_score(a):
    import pandas as pd
    import screen_common_1031 as S
    recs = {}
    for f in S.OUT.glob(f"{TOOL}/*/runs/*.json"):
        x = json.load(open(f))
        recs[(x["video"], tuple(x["actions"]))] = x
    out = []
    for s in ("p1p2", "p3p9", "220", "149"):
        for r in S.rows(s):
            if r["axis"] not in ("V", "TCR", "TCC"):
                continue
            rec = recs.get((r["video"], tuple(actions_of(r["item"]))))
            out.append(dict(set=s, model=r["model"], item_id=r["item_id"], axis=r["axis"], y=r["y"], score=row_score(r, rec) if rec else np.nan))
    d = pd.DataFrame(out)
    d.to_csv(S.OUT / TOOL / "scores_all.csv", index=False)
    th_f = S.OUT / TOOL / "thresholds.json"
    th = json.load(open(th_f)) if th_f.exists() else {}
    for ax in ("V", "TCR", "TCC"):
        if ax in th:
            continue
        p = d[(d["set"] == "p1p2") & (d.axis == ax) & (d.y == "yes")].score.dropna()
        if not len(p):
            continue
        k = next((k for k in (1, 2, 3) if (p >= k).mean() <= S.FA), 4)
        th[ax] = dict(threshold=k, rule="FAIL if score >= k", n_pass=int(len(p)), fa_on_p1p2=float((p >= k).mean()) if k < 4 else 0.0,
                      written=time.strftime("%Y-%m-%dT%H:%M:%S"), other_sets_scored=False)
    json.dump(th, open(th_f, "w"), indent=1)
    print(json.dumps(th, indent=1))
    d["tool_fail"] = [np.nan if np.isnan(sc) or ax not in th else sc >= th[ax]["threshold"] for sc, ax in zip(d.score, d.axis)]
    S.report(TOOL, d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "score"])
    ap.add_argument("--set", default="220")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
