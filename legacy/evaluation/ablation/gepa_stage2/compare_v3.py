#!/usr/bin/env python3
"""No API calls. Test rows of GEPA v3: video only (anchor) vs tools one-shot vs two-stage seed vs GEPA best (b0-b2).
Cells = acc/prec/rec (FAIL = positive), per source x axis. Tools-run rows that were gated out are dropped (n_tools shown).
  python gepa_stage2/compare_v3.py"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import glob, json, re
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
R = (_LEGACY_ROOT + "/eval_results/multi_agent/tools_wf_avocado_min3_g36/rep1")
TOOLS = {"hdepic": f"{E}/results/hdepic_medium_multi_tools_wf_hop5_g36", "hdfoot": f"{E}/results/hdepic_footstep48_tools_wf_hop5_g36",
         "ltx": f"{R}/LTX_2p3_agentic_wf_avocado.csv", "mova": f"{R}/MOVA_agentic_wf_avocado.csv"}
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
SKIP = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)
lab = lambda x: "no" if str(x).strip().lower() in ("no", "fail", "false") else ("yes" if str(x).strip().lower() in ("yes", "pass", "true") else "")

def load(p):
    fs = [p] if p.endswith(".csv") else (sorted(glob.glob(f"{p}/shard?.csv")) or [f"{p}/all.csv"])
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")

def tools_pred(df, row):
    iid, ax = row["item_id"], row["axis"]
    if df is None or iid not in df.index: return ""
    r = df.loc[iid]
    if "__item__" in row["gt"]:
        return "" if SKIP.search(str(r.get(COL[ax] + "_reason", ""))) else lab(r.get(COL[ax], ""))
    try: pe = {e["event_id"]: e for e in json.loads(r[COL[ax] + "_per_event"])}
    except Exception: return ""
    labs = []
    for e in row["gt"]:
        x = pe.get(e)
        if x is None or SKIP.search(str(x.get("reason", ""))): return ""
        labs.append(lab(x.get("label")))
    return "no" if "no" in labs else ("yes" if labs and "" not in labs else "")

def m(y, p):
    y, p = y == "no", p == "no"; n = len(y)
    if not n: return "-"
    tp, fp, fn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum()
    f = lambda a, b: f"{a / b:.2f}" if b else " nan"
    return f"{(y == p).mean():.2f}/{f(tp, tp + fp)}/{f(tp, tp + fn)}"

rows = {json.loads(l)["uid"]: json.loads(l) for l in open("gepa_stage2/manifests_v3/test.jsonl")}
h = pd.read_csv("gepa_stage2/runs/v3_test/heldout_v3.csv")
w = h.pivot_table(index="uid", columns="tag", values="pred", aggfunc="first")
base = h[h.tag == "seed"].set_index("uid")[["source", "axis", "y", "stage1"]]
d = base.join(w)
tl = {s: (load(p) if glob.glob(p if p.endswith(".csv") else f"{p}/*.csv") else None) for s, p in TOOLS.items()}
d["tools"] = [tools_pred(tl.get(d.loc[u, "source"]), rows[u]) for u in d.index]
out = []
for (s, ax), g in d.groupby(["source", "axis"]):
    gt = g[g.tools != ""]
    out.append(dict(source=s, axis=ax, n=len(g), fail=int((g.y == "no").sum()), video=m(g.y, g.stage1), n_tools=len(gt),
                    tools=m(gt.y, gt.tools) if len(gt) else "-", **{t: m(g.y, g[t]) for t in ("seed", "b0", "b1", "b2") if t in g}))
print("cells: acc/prec/rec (FAIL = positive). tools = one call with W+F+caption; seed/b* = two-stage.")
print(pd.DataFrame(out).to_string(index=False))
d.to_csv("gepa_stage2/runs/v3_test/compare_v3.csv")
print("-> gepa_stage2/runs/v3_test/compare_v3.csv")
