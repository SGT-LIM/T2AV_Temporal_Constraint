#!/usr/bin/env python3
"""No API calls. TC-Relation false alarms on GT-PASS items: Gemini 3.1 vs 3.6 (video only, multi-agent).
HD-EPIC: originals, parents (A, V, AVB) judged PASS by both, neighbouring events >= 1 s apart. 220: human GT PASS videos.
  python gepa_stage2/reason_31_36.py | tee gepa_stage2/runs/reason_31_36.txt"""
import glob, json, re, sys
import pandas as pd
sys.path.insert(0, "gepa_stage2")
import filters

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
R = "/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent"
RUNS = {"hdepic": (f"{E}/results/hdepic_medium_multi_baseline", f"{E}/results/hdepic_medium_multi_baseline_g36"),
        "ltx": (json.load(open("gepa_stage2/sources.json"))["ltx"]["stage1"], f"{R}/baseline_min3_g36/rep1/LTX_2p3_agentic_baseline.csv"),
        "mova": (json.load(open("gepa_stage2/sources.json"))["mova"]["stage1"], f"{R}/baseline_min3_g36/rep1/MOVA_agentic_baseline.csv")}
TCR, PAR = "temporal_relation_satisfaction", ("audio_event_correctness", "visual_event_correctness", "audio_visual_binding")
SKIP = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)
CATS = {"simultaneous / overlap": r"simultan|overlap|same time|at once|concurrent|together",
        "event not seen": r"not (observed|visible|seen|shown|present|occur)|never|missing|absent|no .{0,20}(visible|action)",
        "order reversed": r"before|after|revers|wrong order|precede|follow",
        "repeat / extra": r"repeat|again|twice|multiple|extra|additional",
        "timing unclear": r"unclear|ambiguous|difficult|hard to|cannot (determine|tell|confirm)|uncertain"}
CERT = r"\b(clearly|definitely|explicitly|obviously|certainly|unambiguous|undeniabl|plainly)\w*"
HEDGE = r"\b(appears?|seems?|likely|possibly|may|might|perhaps|suggests?|probably|roughly)\b"
lab = filters.lab

def load(p):
    fs = [p] if str(p).endswith(".csv") else (sorted(glob.glob(f"{p}/shard?.csv")) or [f"{p}/all.csv"])
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")

def pass_items(src, a, b):
    if src == "hdepic":
        _, seq = filters.find_seq()
        ids = [i for i in a.index.intersection(b.index) if i.endswith("_pass")]
        ok = lambda i: (seq.get(i) and filters.min_gap(seq[i]) >= 1.0)
        return [i for i in ids if ok(i) and all(lab(a.loc[i, c]) == "yes" and lab(b.loc[i, c]) == "yes" for c in PAR)]
    g = [json.loads(l) for l in open(f"gepa_stage2/manifests/gt_{src}.jsonl")]
    return [r["item_id"] for r in g if r["axis"] == "TCR" and r["gt"].get("__item__") == "yes" and r["item_id"] in a.index and r["item_id"] in b.index]

for src, (p31, p36) in RUNS.items():
    a, b = load(p31), load(p36)
    ids = pass_items(src, a, b)
    d = pd.DataFrame({"j31": [lab(a.loc[i, TCR]) for i in ids], "j36": [lab(b.loc[i, TCR]) for i in ids],
                      "r31": [str(a.loc[i, TCR + "_reason"]) for i in ids], "r36": [str(b.loc[i, TCR + "_reason"]) for i in ids]}, index=ids)
    d = d[(d.j31 != "") & (d.j36 != "") & ~d.r31.str.contains(SKIP) & ~d.r36.str.contains(SKIP)]
    n = len(d)
    print(f"\n===== {src}: GT-PASS items judged by both = {n}")
    if not n: continue
    both = ((d.j31 == "no") & (d.j36 == "no")).sum(); o31 = ((d.j31 == "no") & (d.j36 == "yes")).sum()
    o36 = ((d.j31 == "yes") & (d.j36 == "no")).sum()
    print(f"false alarm 3.1 {(d.j31 == 'no').mean():.2f}  3.6 {(d.j36 == 'no').mean():.2f} | both {both}  only 3.1 {o31}  only 3.6 {o36}  neither {n - both - o31 - o36}")
    for j in ("31", "36"):
        fa = d[d["j" + j] == "no"]["r" + j]
        if not len(fa): continue
        cats = "  ".join(f"{k} {fa.str.contains(v, case=False).mean():.2f}" for k, v in CATS.items())
        print(f"  3.{j[1]} false-alarm reasons (n {len(fa)}): {cats}")
    for j in ("31", "36"):
        r = d["r" + j]
        print(f"  3.{j[1]} all reasons: certain words {r.str.contains(CERT, case=False).mean():.2f}  hedge words {r.str.contains(HEDGE, case=False).mean():.2f}  mean length {r.str.len().mean():.0f}")
    ex = d[(d.j31 == "no") & (d.j36 == "yes")].head(4)
    for i, x in ex.iterrows():
        print(f"\n  [only 3.1 FAIL] {i}\n    3.1: {x.r31[:300]}\n    3.6: {x.r36[:300]}")
