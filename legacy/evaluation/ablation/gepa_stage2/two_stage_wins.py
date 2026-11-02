#!/usr/bin/env python3
"""Deepti 10/21: 220 two-stage vs video only, event level, no API calls (2026-10-25)."""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, re
from pathlib import Path
import pandas as pd

R = (_LEGACY_ROOT + "/eval_results/multi_agent")
RUNS = {"video": "baseline_min3/{m}_agentic_pure_gemini.csv",
        "oneshot": "tools_wf_avocado_min3/{m}_agentic_wf_avocado.csv",
        "two": "two_stage_min3/rep1/{m}_agentic_two_stage.csv"}
MODELS = {"LTX_2p3": "ltx", "MOVA": "mova"}
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
EVID = {"A": "audio_evidence_summary", "V": "caption_evidence_summary", "AVB": "audio_evidence_summary",
        "TCR": "caption_evidence_summary", "TCC": "caption_evidence_summary"}
SKIP = re.compile(r"precondition|not evaluable|not evaluated|skipped|did not all pass", re.I)
OUT = Path("gepa_stage2/runs"); OUT.mkdir(parents=True, exist_ok=True)

def lab(x):
    s = str(x).strip().lower()
    return "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else "")

def load(path):
    return pd.read_csv(path, engine="python").drop_duplicates("item_id", keep="last").set_index("item_id")

def judged(row, ax, eid):
    if row is None: return None, "missing"
    if eid == "__item__":
        l, why = lab(row.get(COL[ax])), str(row.get(COL[ax] + "_reason", ""))
        return (None, why) if (not l or SKIP.search(why[:200])) else (l, why)
    try: pe = {e.get("event_id"): e for e in json.loads(row.get(COL[ax] + "_per_event") or "[]")}
    except Exception: return None, "parse"
    e = pe.get(eid)
    if not e: return None, "no event"
    why = str(e.get("reason", "")); l = lab(e.get("label"))
    return (None, why) if (not l or SKIP.search(why[:200])) else (l, why)

rows = []
for m, src in MODELS.items():
    runs = {k: load(f"{R}/{v.format(m=m)}") for k, v in RUNS.items()}
    for line in open(f"gepa_stage2/manifests/gt_{src}.jsonl"):
        g = json.loads(line); ax, iid = g["axis"], g["item_id"]
        for eid, want in g["gt"].items():
            got = {k: judged(d.loc[iid] if iid in d.index else None, ax, eid) for k, d in runs.items()}
            if any(v[0] is None for v in got.values()): continue
            two = runs["two"].loc[iid]
            rows.append(dict(model=src, axis=ax, item=iid, event=eid, y=want,
                             video=got["video"][0], oneshot=got["oneshot"][0], two=got["two"][0],
                             video_reason=got["video"][1][:300], two_reason=got["two"][1][:300],
                             evidence=str(two.get(EVID[ax], ""))[:400], prompt=str(two.get("event_summary", ""))[:200]))
d = pd.DataFrame(rows)
d["v_ok"] = d.video == d.y; d["o_ok"] = d.oneshot == d.y; d["t_ok"] = d.two == d.y
d["change"] = d.video != d.two
d["kind"] = "same"
d.loc[d.change & ~d.v_ok & d.t_ok, "kind"] = "fixed"
d.loc[d.change & d.v_ok & ~d.t_ok, "kind"] = "broken"
d["revise"] = d.two_reason.str.match(r"\s*REVISE", case=False)

print("== per model x axis (judged by all three runs; FAIL = GT no)")
print(f"{'model':5s} {'axis':4s} {'n':>4s} {'FAIL':>4s} | {'acc video':>9s} {'oneshot':>7s} {'two':>5s} | {'fixed':>5s} {'broken':>6s} | fixed by GT: FAIL/PASS | fixed also by oneshot")
for (mo, ax), g in d.groupby(["model", "axis"], sort=False):
    fx, br = g[g.kind == "fixed"], g[g.kind == "broken"]
    print(f"{mo:5s} {ax:4s} {len(g):4d} {(g.y == 'no').sum():4d} | {g.v_ok.mean():9.2f} {g.o_ok.mean():7.2f} {g.t_ok.mean():5.2f} | "
          f"{len(fx):5d} {len(br):6d} | {(fx.y == 'no').sum():3d}/{(fx.y == 'yes').sum():3d}           | {fx.o_ok.sum():3d}/{len(fx)}")
print("\n== how often stage 2 changed stage 1, and whether it said REVISE")
print(f"  changed {d.change.mean():.2f} of events | REVISE prefix {d.revise.mean():.2f} | changed without REVISE {(d.change & ~d.revise).sum()}")
for mo in d.model.unique():
    g = d[d.model == mo]
    print(f"  {mo}: fixed {(g.kind == 'fixed').sum()} (with REVISE {((g.kind == 'fixed') & g.revise).sum()}), "
          f"broken {(g.kind == 'broken').sum()} (with REVISE {((g.kind == 'broken') & g.revise).sum()})")
print("\n== examples: fixed with REVISE")
for _, x in d[(d.kind == "fixed") & d.revise].groupby(["model", "axis"]).head(2).iterrows():
    print(f"[{x.model} {x.axis} GT {x.y}] {x.item} {x.event}\n   stage1: {x.video_reason[:150]}\n   stage2: {x.two_reason[:200]}\n   evid:   {x.evidence[:160]}")
print("\n== examples: broken with REVISE")
for _, x in d[(d.kind == "broken") & d.revise].groupby(["model", "axis"]).head(1).iterrows():
    print(f"[{x.model} {x.axis} GT {x.y}] {x.item} {x.event}\n   stage1: {x.video_reason[:150]}\n   stage2: {x.two_reason[:200]}\n   evid:   {x.evidence[:160]}")
d[d.change].to_csv(OUT / "two_stage_wins_cases.csv", index=False)
print(f"\n-> {OUT / 'two_stage_wins_cases.csv'} ({int(d.change.sum())} changed events)")
