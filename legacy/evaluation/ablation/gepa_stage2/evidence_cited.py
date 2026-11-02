#!/usr/bin/env python3
"""No API calls. How often the judge's reason text names the tool evidence (Deepti 10/14: how much do judges rely on tool info).
  stage 2 : test cache gepa_stage2/runs/v3_test/cache/<sha>/*.json (seed = the folder with every test row; others = GEPA paragraphs)
  one call: HD-EPIC tools run (hop 5) and 220 tools runs, test items only; video-only runs as control (should be ~0)
  python gepa_stage2/evidence_cited.py | tee gepa_stage2/runs/evidence_cited.txt"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import glob, json, os, re, sys
from collections import defaultdict
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
R = (_LEGACY_ROOT + "/eval_results/multi_agent")
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
KW = {"FLAM": r"flam|detect|activation|sound[- ]event", "Whisper": r"whisper|transcri|\basr\b", "caption": r"caption"}
SKIP = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)

def share(texts, pat):
    t = [x for x in texts if x]
    return (sum(bool(re.search(pat, x, re.I)) for x in t) / len(t)) if t else float("nan")

def report(tag, by_axis):
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        t = by_axis.get(ax, [])
        if not t: continue
        anyk = "|".join(KW.values())
        print(f"  {tag:14s} {ax:4s} n {len(t):4d}  any tool {share(t, anyk):.2f}  " + "  ".join(f"{k} {share(t, v):.2f}" for k, v in KW.items()))

# ---------- stage 2 (two-stage seed and GEPA), from the test cache
cache = "gepa_stage2/runs/v3_test/cache"
folders = {d: len(os.listdir(os.path.join(cache, d))) for d in os.listdir(cache)}
seed_sha = max(folders, key=folders.get)
s2 = defaultdict(lambda: defaultdict(list)); rev = defaultdict(lambda: defaultdict(list))
for sha, n in folders.items():
    tag = "two-stage seed" if sha == seed_sha else "GEPA"
    for f in glob.glob(f"{cache}/{sha}/*.json"):
        rec = json.load(open(f)); out = rec.get("out", {})
        for e, r in out.get("reasons", {}).items():
            s2[tag][rec["axis"]].append(str(r))
            if str(r).strip().upper().startswith("REVISE"): rev[tag][rec["axis"]].append(str(r))
print("== stage-2 reasons naming the evidence (share of reasons), test rows")
for tag in ("two-stage seed", "GEPA"): report(tag, s2[tag])
print("== REVISE reasons only: share, and how many name the evidence")
for tag in ("two-stage seed", "GEPA"):
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        a, b = s2[tag].get(ax, []), rev[tag].get(ax, [])
        if a: print(f"  {tag:14s} {ax:4s} REVISE {len(b):4d}/{len(a):4d} ({len(b)/len(a):.2f})  naming a tool {share(b, '|'.join(KW.values())):.2f}")

# ---------- one call and video only, test items only
test = [json.loads(l) for l in open("gepa_stage2/manifests_v3/test.jsonl")]
ids = defaultdict(set)
for r in test: ids[r["source"]].add(r["item_id"])
def load(p):
    fs = [p] if p.endswith(".csv") else (sorted(glob.glob(f"{p}/shard?.csv")) or [f"{p}/all.csv"])
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
RUNS = {"one call": {"hdepic": f"{E}/results/hdepic_medium_multi_tools_wf_hop5_g36", "hdfoot": f"{E}/results/hdepic_footstep48_tools_wf_hop5_g36",
                     "ltx": f"{R}/tools_wf_avocado_min3_g36/rep1/LTX_2p3_agentic_wf_avocado.csv", "mova": f"{R}/tools_wf_avocado_min3_g36/rep1/MOVA_agentic_wf_avocado.csv"},
        "video only": {"hdepic": f"{E}/results/hdepic_medium_multi_baseline_g36", "hdfoot": f"{E}/results/hdepic_medium_multi_baseline_g36",
                       "ltx": f"{R}/baseline_min3_g36/rep1/LTX_2p3_agentic_baseline.csv", "mova": f"{R}/baseline_min3_g36/rep1/MOVA_agentic_baseline.csv"}}
for tag, srcs in RUNS.items():
    by = defaultdict(list)
    for src, p in srcs.items():
        if not (os.path.exists(p) or glob.glob(f"{p}/*.csv")): continue
        df = load(p)
        for iid in ids[src] & set(df.index):
            r = df.loc[iid]
            for ax, c in COL.items():
                if ax == "TCR":
                    t = str(r.get(c + "_reason", ""));
                    if t and t != "nan" and not SKIP.search(t): by[ax].append(t)
                    continue
                try: pe = json.loads(r[c + "_per_event"])
                except Exception: continue
                by[ax] += [str(e.get("reason", "")) for e in pe if not SKIP.search(str(e.get("reason", "")))]
    print(f"== {tag} reasons naming the evidence, test items (HD-EPIC + footstep + 220 pooled)")
    report(tag, by)
