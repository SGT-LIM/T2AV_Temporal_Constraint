#!/usr/bin/env python3
"""Held-out test for GEPA v3: seed vs best, same day, same test units. Metrics per source x axis with FAIL = positive:
acc, prec, rec, FAR, balanced acc; best - seed with paired bootstrap 95% CI over rows; changed-vs-stage-1 right / wrong.

  python -u gepa_stage2/eval_v3.py --sources gepa_stage2/sources_v3.json --manifest gepa_stage2/manifests_v3/test.jsonl \
      --cand seed=gepa_stage2/runs/v3_s0/seed_candidate.json best=gepa_stage2/runs/v3_s0/best_candidate.json \
      --run-dir gepa_stage2/runs/v3_s0 --workers 8
Ablation (best with one paragraph set back to seed): add  --ablate  -> tags best-minus-A ... best-minus-TCC.
Item-level verdict per row: 'no' if any judged event is 'no' (TCR is item-level already).
"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter_v3 import V3Adapter, AXES, COMP, load_units, set_weights


def item_label(d):
    labs = [v for v in d.values() if v in ("yes", "no")]
    return "no" if "no" in labs else ("yes" if labs else "")


def rows_frame(adapter, units, cand, tag):
    eb = adapter.evaluate(units, cand, capture_traces=True)
    recs = []
    for u, urec in zip(units, eb.outputs):
        byuid = {r["uid"]: r for r in urec["rows"]}
        for row in u["rows"]:
            r = byuid.get(row["uid"])
            if r is None or "error" in r:
                continue
            o = r["out"]
            gt_item = "no" if "no" in row["gt"].values() else "yes"
            if "__item__" in r["per"]:
                pred = r["per"]["__item__"][0]
            else:
                pred = item_label({e: p for e, (p, g) in r["per"].items()})
            s1 = item_label(o["stage1"]) if o["stage1"] else ""
            recs.append(dict(uid=row["uid"], source=row["source"], axis=row["axis"], variant=row["variant"],
                             y=gt_item, pred=pred, stage1=s1, ev_score=r["score"], tag=tag))
    return pd.DataFrame(recs)


def metrics(y, p):
    y, p = np.asarray(y) == "no", np.asarray(p) == "no"
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    f = lambda a, b: a / b if b else np.nan
    rec, far = f(tp, tp + fn), f(fp, fp + tn)
    bal = np.nanmean([rec, 1 - far]) if not (np.isnan(rec) and np.isnan(far)) else np.nan
    return dict(n=int(len(y)), n_fail=int(y.sum()), acc=f(tp + tn, len(y)), prec=f(tp, tp + fp), rec=rec, FAR=far, bal=bal)


def boot(a_ok, b_ok, n=5000, seed=0):
    a, b = np.asarray(a_ok, float), np.asarray(b_ok, float)
    if not len(a):
        return np.nan, np.nan, np.nan
    idx = np.random.default_rng(seed).integers(0, len(a), (n, len(a)))
    d = (b[idx] - a[idx]).mean(1)
    return (b - a).mean(), np.percentile(d, 2.5), np.percentile(d, 97.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True); ap.add_argument("--manifest", required=True)
    ap.add_argument("--cand", nargs="+", required=True, help="tag=candidate.json ... (first = reference)")
    ap.add_argument("--run-dir", required=True); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--judge-model", default="gemini-3.6-flash"); ap.add_argument("--thinking", default="high")
    ap.add_argument("--ablate", action="store_true")
    a = ap.parse_args()
    units = load_units(a.manifest); set_weights(units)
    adapter = V3Adapter(json.load(open(a.sources)), a.run_dir, model=a.judge_model, thinking=a.thinking,
                        workers=a.workers, max_chars=10 ** 6, log=lambda s: print(s, flush=True))
    cands = {t: json.load(open(p)) for t, p in (x.split("=", 1) for x in a.cand)}
    if a.ablate and "best" in cands and "seed" in cands:
        for ax in AXES:
            c = dict(cands["best"]); c[COMP[ax]] = cands["seed"][COMP[ax]]
            if c != cands["best"]:
                cands[f"best-minus-{ax}"] = c
    tags = list(cands)
    dfs = {t: rows_frame(adapter, units, c, t) for t, c in cands.items()}
    ref = tags[0]
    allr = pd.concat(dfs.values()); allr.to_csv(Path(a.run_dir) / "heldout_v3.csv", index=False)

    print("\n== per source x axis (FAIL = positive). stage1 = existing video-only run (anchor).")
    lines = []
    for (src, ax), g0 in dfs[ref].groupby(["source", "axis"]):
        rec = dict(source=src, axis=ax)
        m1 = metrics(g0.y, g0.stage1); rec.update(n=m1["n"], n_fail=m1["n_fail"], stage1=f"{m1['acc']:.2f}/{m1['rec']:.2f}/{m1['FAR']:.2f}")
        for t in tags:
            g = dfs[t][(dfs[t].source == src) & (dfs[t].axis == ax)]
            m = metrics(g.y, g.pred)
            rec[t] = f"{m['acc']:.2f}/{m['prec']:.2f}/{m['rec']:.2f}/{m['FAR']:.2f}"
        for t in tags[1:]:
            gb = dfs[t].set_index("uid"); ga = g0.set_index("uid").loc[[u for u in g0.uid if u in gb.index]]
            d, lo, hi = boot(ga.pred == ga.y, gb.loc[ga.index].pred == ga.y)
            rec[f"{t}-{ref}"] = f"{d:+.2f} [{lo:+.2f},{hi:+.2f}]"
        lines.append(rec)
    print("cells: acc/prec/rec/FAR (stage1: acc/rec/FAR)")
    print(pd.DataFrame(lines).to_string(index=False))

    print("\n== mean over axes of balanced acc (pooled sources), per tag")
    for t in tags:
        b = [metrics(g.y, g.pred)["bal"] for _, g in dfs[t].groupby("axis")]
        print(f"  {t:16s} {np.nanmean(b):.3f}   by axis " + " ".join(f"{ax} {metrics(g.y, g.pred)['bal']:.2f}" for ax, g in dfs[t].groupby('axis')))

    print("\n== stage 2 vs stage 1 (row verdicts): changed / right after change / wrong after change")
    for t in tags:
        for src, g in dfs[t].groupby("source"):
            ch = g[(g.pred != g.stage1) & (g.stage1 != "")]
            print(f"  {t:16s} {src:7s} changed {len(ch):4d}/{len(g):4d}  right {int((ch.pred == ch.y).sum()):4d}  wrong {int((ch.pred != ch.y).sum()):4d}")
    print(f"\n-> {a.run_dir}/heldout_v3.csv")


if __name__ == "__main__":
    main()