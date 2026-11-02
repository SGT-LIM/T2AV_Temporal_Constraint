#!/usr/bin/env python3
# Replaced by t2av_eval/data/filters.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Scoring-only filters, no API calls (2026-10-25).
  python gepa_stage2/filters.py names
  python gepa_stage2/filters.py move [--run DIR]
  python gepa_stage2/filters.py tcr  --run DIR [DIR ...]"""
import argparse, glob, json, os, re, sys
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
PILOT = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot"
NAMES_CSV = f"{E}/move_names.csv"
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
FIXTURE = re.compile(r"\b(door|drawer|cupboard|cabinet|fridge|freezer|oven|microwave|dishwasher|tap|sink|hob|stove|"
                     r"counter|countertop|shelf|wall|floor|window|handle|knob|switch|bin lid)\b")

def lab(x):
    s = str(x).strip().lower()
    return "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else "")

def prf(y, p):
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    f = lambda a, b: a / b if b else float("nan")
    return f(tp + tn, tp + fp + fn + tn), f(tp, tp + fp), f(tp, tp + fn), f(fp, fp + tn), int(tp + fp + fn + tn), int(tp + fn)

def line(tag, y, p):
    acc, pr, rc, far, n, nf = prf(y, p)
    return f"  {tag:34s} n {n:4d} (FAIL {nf:3d})  acc {acc:.2f}  prec {pr:.2f}  rec {rc:.2f}  FAR {far:.2f}"

def load_run(d):
    fs = sorted(glob.glob(f"{d}/shard?.csv")) or [f"{d}/all.csv"]
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")

def cmd_names(a):
    items = json.load(open(f"{E}/hdepic_move_prompts.json"))
    cnt = {}
    for x in items:
        if not x["item_id"].endswith("_pass"): continue
        for e in x["events"]:
            nm = e["action"].replace("move ", "", 1); cnt[nm] = cnt.get(nm, 0) + 1
    df = pd.DataFrame(sorted(cnt.items(), key=lambda t: -t[1]), columns=["name", "windows"])
    df["exclude"] = df.name.apply(lambda n: int(bool(FIXTURE.search(n))))
    df.to_csv(NAMES_CSV, index=False)
    print(f"{len(df)} names, {df.exclude.sum()} flagged as fixture ({df[df.exclude == 1].windows.sum()} windows)")
    print("flagged:", ", ".join(df[df.exclude == 1].name))
    print("\nall names (edit exclude column in the csv to add typos / unclear names):")
    print(", ".join(f"{n}({w})" for n, w in zip(df.name, df.windows)))
    print("->", NAMES_CSV)

def cmd_move(a):
    run = load_run(a.run[0] if a.run else f"{E}/results/hdepic_move_multi_baseline")
    gt = pd.read_csv(f"{E}/hdepic_move_gt.csv").set_index("item_id")
    items = {x["item_id"]: x for x in json.load(open(f"{E}/hdepic_move_prompts.json"))}
    bad = set(pd.read_csv(NAMES_CSV).query("exclude == 1").name)
    ids = [i for i in run.index if i in gt.index]
    has_bad = {i: any(e["action"].replace("move ", "", 1) in bad for e in items[i]["events"]) for i in ids}
    d = pd.DataFrame({"y": gt.loc[ids, COL["TCC"]].map(lab) == "no", "p": run.loc[ids, COL["TCC"]].map(lab) == "no",
                      "A": run.loc[ids, COL["A"]].map(lab), "V": run.loc[ids, COL["V"]].map(lab),
                      "bad": [has_bad[i] for i in ids]}, index=ids)
    d = d[run.loc[ids, COL["TCC"]].map(lab) != ""]
    par = (d.A != "no") & (d.V != "no")
    print(f"excluded names: {len(bad)} | items with an excluded name: {int(d.bad.sum())} / {len(d)}")
    print("TCC")
    print(line("all", d.y, d.p)); print(line("all, A and V judged PASS", d.y[par], d.p[par]))
    k = ~d.bad
    print(line("names excluded", d.y[k], d.p[k])); print(line("names excluded, A and V PASS", d.y[k & par], d.p[k & par]))
    print("V false-alarm rate (GT all PASS)")
    print(f"  all {(d.V == 'no').mean():.2f} | items with excluded name {(d[d.bad].V == 'no').mean():.2f} | others {(d[~d.bad].V == 'no').mean():.2f}")

def find_seq():
    cands = [f"{E}/items_hdepic_medium_with_clips_v2.json"] + sorted(glob.glob(f"{PILOT}/**/*.json", recursive=True)) + \
            sorted(glob.glob(f"{E}/*items*.json"))
    for f in cands:
        if not os.path.exists(f) or os.path.getsize(f) > 500e6: continue
        try: d = json.load(open(f))
        except Exception: continue
        if isinstance(d, dict): d = d.get("items", list(d.values()))
        if isinstance(d, list) and d and isinstance(d[0], dict) and "sequence" in d[0] and "item_id" in d[0]:
            return f, {x["item_id"]: x["sequence"] for x in d}
    return None, {}

def min_gap(seq):
    gaps = [t2 - t1 for (t1, i1), (t2, i2) in zip(seq, seq[1:]) if i1 != i2]
    return min(gaps) if gaps else float("inf")

def cmd_tcr(a):
    f, seq = find_seq()
    if not seq: sys.exit("no item file with 'sequence' found; tell Claude which json has event times")
    print(f"event times from {f} ({len(seq)} items)")
    gt = pd.read_csv(f"{E}/hdepic_medium_gt.csv").set_index("item_id")
    keep = [i for i in gt.index if i.endswith(("_pass", "_TCR"))]
    gap = {}
    for i in keep:
        w = i.rsplit("_", 1)[0]
        s = seq.get(w + "_pass") or seq.get(i)
        gap[i] = min_gap(s) if s else float("nan")
    g = pd.Series(gap)
    print(f"windows with all neighbouring events >= {a.gap} s apart: {(g[[i for i in keep if i.endswith('_pass')]] >= a.gap).sum()} "
          f"/ {len(keep) // 2} (no time found {g.isna().sum()})")
    for d in a.run:
        run = load_run(d); ids = [i for i in keep if i in run.index and lab(run.loc[i, COL["TCR"]]) != ""]
        y = gt.loc[ids, COL["TCR"]].map(lab) == "no"; p = run.loc[ids, COL["TCR"]].map(lab) == "no"
        par = pd.Series([all(lab(run.loc[i, COL[x]]) != "no" for x in ("A", "V", "AVB")) for i in ids], index=ids)
        ok = pd.Series([gap.get(i, float("nan")) >= a.gap for i in ids], index=ids)
        print(f"\n{d}   (items: original + order_swap)")
        print(line("flat", y, p)); print(line("A, V, AVB judged PASS", y[par], p[par]))
        print(line(f"gap >= {a.gap} s", y[ok], p[ok])); print(line(f"gap >= {a.gap} s and parents PASS", y[ok & par], p[ok & par]))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["names", "move", "tcr"])
    ap.add_argument("--run", nargs="*", default=[]); ap.add_argument("--gap", type=float, default=1.0)
    a = ap.parse_args()
    {"names": cmd_names, "move": cmd_move, "tcr": cmd_tcr}[a.cmd](a)
