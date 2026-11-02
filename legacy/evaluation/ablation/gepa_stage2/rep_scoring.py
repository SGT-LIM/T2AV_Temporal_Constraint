#!/usr/bin/env python3
"""No API calls. One scoring rule for every media-only / one-call run on the v3 test rows (10/28).

Rule = how heldout `stage1` is built (run_two_stage.stage1_lookup + eval_v3.item_label):
  per-event JSON of the run, only the GT event ids of the row, events whose reason matches SKIP_RE
  (precondition / not evaluated / not evaluable / skipped) dropped; row = "no" if any kept event is "no",
  "yes" if all kept are "yes", "" (dropped) if none kept. TCR: item label unless its reason matches SKIP_RE.
  TCC: observed_count == required_count per event.
The item-level axis columns of the run csv are NOT used (they count gated events as FAIL).

Runs per source (sources_v3.json layout; hdepic = medium then regen, regen wins on duplicates):
  rep1 = the anchors in sources_v3.json (HD-EPIC 10/16 medium, 10/25 regen + move; 220 10/16)
  rep2 / rep3 = media-only reruns of 10/28 (launch_anchor_reps_1028.sh)
  220 only: d1027 = media-only 10/27, oc1016 / oc1027 = one call (tools) 10/16 / 10/27

  python gepa_stage2/rep_scoring.py            # writes runs/v3_test/anchor_reps_1028_rows.csv (refuses to overwrite)
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results"
R = (_LEGACY_ROOT + "/eval_results/multi_agent")
MAN = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "manifests_v3/test.jsonl"
HELD = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/v3_test/heldout_v3.csv"
OUT = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/v3_test/anchor_reps_1028_rows.csv"
SKIP_RE = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)     # = run_two_stage.SKIP_RE
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
MODEL = {"ltx": "LTX_2p3", "mova": "MOVA"}


def hd(rep):
    med, reg, mov = (f"{E}/hdepic_{k}_multi_baseline_g36{rep}" for k in ("medium", "regen", "move"))
    return {"hdepic": [med, reg], "hdfoot": [med], "hdmove": [mov]}


RUNS = {
    "rep1": {**hd(""), "ltx": [f"{R}/baseline_min3_g36/rep1/LTX_2p3_agentic_baseline.csv"],
             "mova": [f"{R}/baseline_min3_g36/rep1/MOVA_agentic_baseline.csv"]},
    **{rep: {**hd(f"_{rep}_1028"), **{s: [f"{R}/baseline_min3_g36_{rep}_1028/{m}.csv"] for s, m in MODEL.items()}}
       for rep in ("rep2", "rep3")},
    "d1027": {s: [f"{R}/baseline_min3_g36_1027/{m}.csv"] for s, m in MODEL.items()},
    "oc1016": {s: [f"{R}/tools_wf_avocado_min3_g36/rep1/{m}_agentic_wf_avocado.csv"] for s, m in MODEL.items()},
    "oc1027": {s: [f"{R}/tools_min3_g36_1027/{m}.csv"] for s, m in MODEL.items()},
}
DAY = {"rep1": "HD-EPIC 10/16 (medium) + 10/25 (regen, move); 220 10/16", "rep2": "10/28", "rep3": "10/28",
       "d1027": "10/27", "oc1016": "10/16", "oc1027": "10/27"}


def load(paths):
    """item_id -> row; same as run_two_stage.load_stage1 (shard?.csv or all.csv in a dir, or one csv), later paths win."""
    fs = []
    for p in paths:
        p = Path(p)
        fs += [p] if p.suffix == ".csv" else (sorted(p.glob("shard?.csv")) or sorted(p.glob("all.csv")))
    if not fs:
        sys.exit(f"no csv under {paths}")
    df = pd.concat(pd.read_csv(f, engine="python") for f in fs)
    return df.drop_duplicates("item_id", keep="last").set_index("item_id")


def row_label(df, item_id, axis, gt):
    """heldout stage1 rule for one manifest row; '' if the row has nothing judged."""
    if item_id not in df.index:
        return ""
    r = df.loc[item_id]
    if axis == "TCR":
        lab = str(r.get(COL[axis], "")).strip().lower()
        return lab if lab in ("yes", "no") and not SKIP_RE.search(str(r.get(COL[axis] + "_reason", ""))) else ""
    try:
        pe = json.loads(r[COL[axis] + "_per_event"])
    except Exception:
        return ""
    want = [e for e in gt if e != "__item__"] or None
    labs = []
    for e in pe:
        if want is not None and e.get("event_id") not in want:
            continue
        if SKIP_RE.search(str(e.get("reason", ""))):
            continue
        if axis == "TCC":
            oc, rc = e.get("observed_count"), e.get("required_count")
            if oc is None or rc is None:
                continue
            try:
                labs.append("yes" if int(oc) == int(rc) else "no")
            except (TypeError, ValueError):
                continue
        else:
            lab = str(e.get("label", "")).strip().lower()
            if lab in ("yes", "no"):
                labs.append(lab)
    return "no" if "no" in labs else ("yes" if labs else "")


def score_rows(man, runs=RUNS):
    rows = pd.DataFrame([dict(uid=m["uid"], source=m["source"], item_id=m["item_id"], axis=m["axis"], variant=m["variant"],
                              y="no" if "no" in m["gt"].values() else "yes", gt=m["gt"]) for m in man])
    for name, by_src in runs.items():
        col = []
        dfs = {s: load(p) for s, p in by_src.items()}
        for _, m in rows.iterrows():
            df = dfs.get(m.source)
            col.append(row_label(df, m.item_id, m.axis, m["gt"]) if df is not None else np.nan)
        rows[name] = col
    return rows.drop(columns="gt")


def metrics(y, p):
    y, p = np.asarray(y) == "no", np.asarray(p) == "no"
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    f = lambda a, b: a / b if b else np.nan
    return dict(n=int(len(y)), n_fail=int(y.sum()), acc=f(tp + tn, len(y)), prec=f(tp, tp + fp), rec=f(tp, tp + fn),
                FAR=f(fp, fp + tn))


def main():
    man = [json.loads(l) for l in open(MAN)]
    rows = score_rows(man)
    # check against the stored heldout stage1 column (it also filled some gated anchor events from the fresh stage-1 cache)
    h = pd.read_csv(HELD)
    h = h[h.tag == h.tag.unique()[0]].set_index("uid").stage1.fillna("")
    s = rows.set_index("uid").rep1.fillna("")
    both = s.index.intersection(h.index)
    same = (s[both] == h[both])
    print(f"rep1 vs stored heldout stage1: {same.sum()}/{len(both)} identical; differing by source:")
    print(rows.set_index("uid").loc[both[~same.values]].groupby(["source", "axis"]).size().to_string())
    if OUT.exists():
        sys.exit(f"exists, not overwriting: {OUT}")
    rows.to_csv(OUT, index=False)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
