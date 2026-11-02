#!/usr/bin/env python3
"""absent_sound (HD-EPIC test, A axis): per item, what FLAM text showed, what each condition answered, what the reason cites.
Run from evaluation/ablation (no API calls; reads caches + heldout csvs):
  python gepa_stage2/absent_check.py > gepa_stage2/runs/absent_check.txt
Conditions: s1v = stage-1 video, s1t = stage-1 + tools, s2 = stage-2 axis-wise, orch = orchestrator; seed / best each."""
import hashlib, json, re, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, "gepa_stage2")
from stage1_adapter import Stage1Adapter
from adapter import axis_rules, AXIS_MOD
import run_two_stage as TS

G = Path("gepa_stage2"); R = G / "runs"
src = json.load(open(G / "sources.json"))
rows = [json.loads(l) for l in open(G / "manifests_s1/test.jsonl")]
rows = [r for r in rows if r["source"] == "hdepic" and r["axis"] == "A" and r["variant"] in ("absent_sound", "original")]
print(f"{len(rows)} A rows (absent_sound + original)")

# ---- labels from heldout csvs (item level: no if any event no)
def item_labels(csv):
    df = pd.read_csv(csv)
    g = df.groupby("uid")["pred"].apply(lambda s: "no" if (s == "no").any() else ("yes" if (s == "yes").any() else ""))
    return g.to_dict()
COND = {"s1v_seed": R / "s1video_A/heldout_test_seed.csv", "s1v_best": R / "s1video_A/heldout_test_best.csv",
        "s1t_seed": R / "s1tools_A/heldout_test_seed.csv", "s1t_best": R / "s1tools_A/heldout_test_best.csv",
        "s2_seed": R / "s0_s1test/heldout_test_seed.csv", "s2_best": R / "s0_s1test/heldout_test_best.csv",
        "orch_seed": R / "orch_s1test/heldout_test_orch_seed.csv", "orch_best": R / "orch_s1test/heldout_test_orch_best.csv"}
labs = {k: item_labels(p) for k, p in COND.items() if p.exists()}

# ---- reasons from stage-1 tools caches (seed / best) and stage-2 axis caches
def s1_sha(mode, rules): return hashlib.sha1(f"{mode}|A|{rules}".encode()).hexdigest()[:12]
def s2_sha(rules): return hashlib.sha1(rules.encode()).hexdigest()[:12]
seed_rules = axis_rules(AXIS_MOD["A"])
REASON_DIRS = {
    "s1v_seed": R / "s1video_A/cache" / s1_sha("video", seed_rules),
    "s1v_best": R / "s1video_A/cache" / s1_sha("video", (R / "s1video_A/best_candidate.txt").read_text()),
    "s1t_seed": R / "s1tools_A/cache" / s1_sha("tools", seed_rules),
    "s1t_best": R / "s1tools_A/cache" / s1_sha("tools", (R / "s1tools_A/best_candidate.txt").read_text()),
    "s2_seed": R / "s0_s1test/cache" / s2_sha((R / "s0/seed_candidate.txt").read_text()),
    "s2_best": R / "s0_s1test/cache" / s2_sha((R / "s0/best_candidate.txt").read_text()),
}
def reason(cond, uid):
    p = REASON_DIRS[cond] / (re.sub(r"[^A-Za-z0-9_.|-]", "_", uid) + ".json")
    if not p.exists(): return ""
    rec = json.load(open(p))
    return " | ".join(str(v) for v in rec["out"].get("reasons", {}).values())

# ---- FLAM text per item (from the pipeline context, evidence cache only)
ad = Stage1Adapter(src, R / "_absent_tmp", axis="A", mode="tools", workers=1, log=lambda s: None)
def flam_status(iid):
    ctx = ad._context("hdepic", iid)
    txt = "\n".join(str(v) for v in ctx.evidence.values())
    scores = [float(x) for x in re.findall(r"max_score[^0-9]*([0-9.]+)", txt)]
    peaks = re.findall(r"peaks?[^\n]*?(\d+\.\d+)s", txt)
    det_none = bool(re.search(r"detections above threshold:\s*none", txt, re.I))
    speech = re.search(r"has_speech:\s*(True|False)", txt)
    return dict(max_score=max(scores) if scores else None, n_peaks=len(peaks), det_none=det_none,
                speech=speech.group(1) if speech else "?", flam_len=len(txt))

CITE = {"flam": re.compile(r"flam|detect|peak|score", re.I), "visual": re.compile(r"\b(see|seen|visible|visibly|hand|shows|motion|action)\b", re.I),
        "silent": re.compile(r"silen|no sound|absent|not audible|inaudible", re.I)}
out = []
for r in rows:
    uid, iid = r["uid"], r["item_id"]
    fs = flam_status(iid)
    rec = dict(variant=r["variant"], item=iid.replace("hdepic_", ""), **fs)
    for c in labs: rec[c] = labs[c].get(uid, "")
    for c in ("s1v_seed", "s1t_seed", "s2_seed", "s1t_best"):
        rs = reason(c, uid)
        rec[f"{c}_cites"] = "+".join(k for k, rx in CITE.items() if rx.search(rs))
    out.append(rec)
df = pd.DataFrame(out)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
df.to_csv(R / "absent_check.csv", index=False)

conds = [c for c in COND if c in labs]
print("\n== absent_sound: fraction judged no (= recall of FAIL), split by FLAM text state")
ab = df[df.variant == "absent_sound"]
ab["flam_state"] = ab.apply(lambda x: "empty" if (x.n_peaks == 0 or (x.max_score is not None and x.max_score < 0.05)) else "peaks", axis=1)
print(ab.groupby("flam_state")[conds].apply(lambda g: (g == "no").mean()).round(2).assign(n=ab.groupby("flam_state").size()).to_string())
print("\n== original: fraction judged no (= false alarm), split by FLAM text state")
og = df[df.variant == "original"]
og["flam_state"] = og.apply(lambda x: "empty" if (x.n_peaks == 0 or (x.max_score is not None and x.max_score < 0.05)) else "peaks", axis=1)
print(og.groupby("flam_state")[conds].apply(lambda g: (g == "no").mean()).round(2).assign(n=og.groupby("flam_state").size()).to_string())
print("\n== absent_sound: max_score distribution of FLAM text")
print(ab.max_score.describe().round(2).to_string())
print("\n== absent_sound: what the reason cites (stage-1 video seed / stage-1 tools seed / stage-2 seed / stage-1 tools best)")
for c in ("s1v_seed", "s1t_seed", "s2_seed", "s1t_best"):
    col = f"{c}_cites"
    print(f"  {c:9s}", ab[col].value_counts().to_dict())
print("\n== per item")
print(df[["variant", "item", "max_score", "n_peaks", "det_none"] + conds + ["s1t_seed_cites"]].to_string(index=False))
print(f"\n-> {R}/absent_check.csv")
