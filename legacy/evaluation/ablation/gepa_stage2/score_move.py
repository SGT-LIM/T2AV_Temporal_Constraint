#!/usr/bin/env python3
"""Score the HD-EPIC object-movement TCC set (2026-10-24). No API calls."""
import argparse, glob, json, re
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
AN = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/annotations"
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCC": "temporal_count_satisfaction"}

def lab(x):
    s = str(x).strip().lower()
    return "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else "")

def prf(y, p):
    tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
    f = lambda a, b: a / b if b else float("nan")
    return f(tp + tn, tp + fp + fn + tn), f(tp, tp + fp), f(tp, tp + fn), f(fp, fp + tn), int(tp + fp + fn + tn)

def line(tag, d):
    acc, pr, rc, far, n = prf(d.y == "no", d.pred == "no")
    return f"  {tag:28s} n {n:4d}  acc {acc:.2f}  prec {pr:.2f}  rec {rc:.2f}  FAR {far:.2f}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", default=f"{E}/results/hdepic_move_multi_baseline"); a = ap.parse_args()
    fs = sorted(f for f in glob.glob(f"{a.run}/shard?.csv"))
    run = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
    gt = pd.read_csv(f"{E}/hdepic_move_gt.csv").set_index("item_id")
    items = {x["item_id"]: x for x in json.load(open(f"{E}/hdepic_move_prompts.json"))}
    ids = [i for i in run.index if i in gt.index]
    print(f"run {a.run}\nitems judged {len(ids)} / {len(gt)}")

    print("\n== 1. A / V / AVB: fraction judged FAIL (GT is PASS for all, so = false-alarm rate)")
    for ax in ("A", "V", "AVB"):
        p = run.loc[ids, COL[ax]].map(lab)
        print(f"  {ax:4s} FAIL {(p == 'no').mean():.2f}   (labeled {(p != '').sum()})")

    d = pd.DataFrame({"y": gt.loc[ids, "temporal_count_satisfaction"].map(lab), "pred": run.loc[ids, COL["TCC"]].map(lab),
                      "A": run.loc[ids, COL["A"]].map(lab), "V": run.loc[ids, COL["V"]].map(lab)}, index=ids)
    d = d[d.pred != ""]
    starts = {i: json.loads(gt.loc[i, "move_starts_sec"]) for i in ids}
    d["maxN"] = [max(len(v) for v in starts[i].values()) for i in d.index]
    d["nobj"] = [len(starts[i]) for i in d.index]
    print("\n== 2. TCC (FAIL = positive)")
    print(line("flat", d))
    print(line("A and V judged PASS", d[(d.A != "no") & (d.V == "yes")]))
    print("\n== 3. TCC by window")
    for k, g in d.groupby("maxN"): print(line(f"max N = {k}", g))
    for k, g in d.groupby("nobj"): print(line(f"objects = {k}", g))
    print("  PASS items judged FAIL (FAR) vs count_off judged PASS (miss):")
    print(f"    original  FAIL rate {(d[d.y == 'yes'].pred == 'no').mean():.2f}   count_off  PASS rate {(d[d.y == 'no'].pred == 'yes').mean():.2f}")

    print("\n== 4. per-event counts on PASS items (judge observed vs annotation)")
    A = json.load(open(f"{AN}/data/scene-and-object-movements/assoc_info.json"))
    base = lambda n: re.sub(r"\d+$", "", n.strip().lower()).strip()
    rows = []
    for i in d[d.y == "yes"].index:
        m = re.match(r"hdepicmove_(.+)_(\d{7})_pass$", i); v, t0 = m.group(1), int(m.group(2)) / 1000
        try: pe = {e.get("event_id"): e for e in json.loads(run.loc[i, f"{COL['TCC']}_per_event"])}
        except Exception: continue
        for k, ev in enumerate(items[i]["events"], 1):
            j = pe.get(f"event_{k}", {}); oc = j.get("observed_count")
            if oc is None: continue
            nm = ev["action"].replace("move ", "", 1)
            durs = [e - s for o in A[v].values() if base(o["name"]) == nm for t in o["tracks"]
                    for s, e in [t["time_segment"]] if t0 <= s <= t0 + 25]
            rows.append(dict(item=i, obj=nm, req=ev["count"], obs=int(oc), short=min(durs) < 1.0 if durs else None,
                             reason=str(j.get("reason", ""))[:160]))
    r = pd.DataFrame(rows)
    if r.empty: print("  (no per-event rows)"); return
    r["err"] = r.obs - r.req
    print(f"  events {len(r)} | exact {(r.err == 0).mean():.2f} | over {(r.err > 0).mean():.2f} | under {(r.err < 0).mean():.2f}")
    for k, g in r.groupby("req"): print(f"    required {k}: n {len(g):4d}  exact {(g.err == 0).mean():.2f}  over {(g.err > 0).mean():.2f}  under {(g.err < 0).mean():.2f}")
    for k, g in r.groupby("short"): print(f"    has move < 1 s = {k}: n {len(g):4d}  exact {(g.err == 0).mean():.2f}  over {(g.err > 0).mean():.2f}  under {(g.err < 0).mean():.2f}")
    print("  over-count by size:", dict(r[r.err > 0].err.value_counts().sort_index()))
    print("\n  examples of over-count (judge reason):")
    for _, x in r[r.err > 0].head(8).iterrows(): print(f"    {x['obj']}: req {x['req']} obs {x['obs']} | {x['reason']}")
    print("  examples of under-count:")
    for _, x in r[r.err < 0].head(5).iterrows(): print(f"    {x['obj']}: req {x['req']} obs {x['obs']} | {x['reason']}")
    r.to_csv(f"{a.run}/move_event_errors.csv", index=False)
    print(f"\n-> {a.run}/move_event_errors.csv")

if __name__ == "__main__":
    main()
