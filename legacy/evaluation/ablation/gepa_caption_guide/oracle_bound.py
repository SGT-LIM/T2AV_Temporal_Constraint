#!/usr/bin/env python3
"""Per-event V-axis comparison from EXISTING run CSVs: no-caption vs caption vs oracle.

For each manifest video (e.g. val_s2 / test hdepic rows) and each GT event:
    nocap  = V label from the no-caption run (multi_baseline)
    cap    = V label from the caption run    (multi_tools_wf_avocado; V receives caption only)
    oracle = correct if either one is correct (an ideal per-event gate)
Optionally a heldout_<tag>.csv from eval_guide.py (our seed re-judgement) as a 4th column.

    python oracle_bound.py --manifest manifests/val_s2.jsonl --source hdepic \
        --nocap "/projectnb/.../results/hdepic_medium_multi_baseline/shard*.csv" \
        --cap   "/projectnb/.../results/hdepic_medium_multi_tools_wf_avocado/shard*.csv" \
        [--heldout runs/base_s0/heldout_val_cand0.csv]

Prints event-level acc for each column, split by all / GT PASS / GT FAIL, plus how often
the two runs disagree and in which direction. Video-level (all events correct) row too.
"""
import argparse
import csv
import glob
import json
from collections import defaultdict
from pathlib import Path


def load_run(pattern):
    """video_relpath -> {event_id: 'PASS'/'FAIL'} from visual_event_correctness_per_event."""
    out = {}
    for f in sorted(glob.glob(pattern)):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pe = r.get("visual_event_correctness_per_event") or ""
                if not pe.startswith("["):
                    continue
                try:
                    lst = json.loads(pe)
                except json.JSONDecodeError:
                    continue
                out[r["video_relpath"]] = {e["event_id"]: ("PASS" if e.get("label") == "yes" else "FAIL") for e in lst}
    return out


def load_heldout(path):
    out = defaultdict(dict)
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["relpath"]][r["event_id"]] = r["pred"]
    return out


def acc(rows, key):
    xs = [r[key] for r in rows if r[key] is not None]
    return (sum(xs) / len(xs), len(xs)) if xs else (float("nan"), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--source", default="hdepic")
    ap.add_argument("--nocap", required=True)
    ap.add_argument("--cap", required=True)
    ap.add_argument("--heldout", type=Path, default=None)
    a = ap.parse_args()

    items = [json.loads(l) for l in a.manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [it for it in items if it["source"] == a.source]
    nocap, cap = load_run(a.nocap), load_run(a.cap)
    held = load_heldout(a.heldout) if a.heldout else None
    print(f"manifest videos ({a.source}): {len(items)} | nocap run: {len(nocap)} videos | cap run: {len(cap)} videos")

    rows, missing = [], 0
    for it in items:
        rp = it["relpath"]
        n, c = nocap.get(rp), cap.get(rp)
        if n is None or c is None:
            missing += 1
            continue
        h = held.get(rp) if held else None
        for eid, gt in it["gt"].items():
            r = {"relpath": rp, "eid": eid, "gt": gt,
                 "nocap": None if eid not in n else float(n[eid] == gt),
                 "cap": None if eid not in c else float(c[eid] == gt),
                 "seed": None if not h or eid not in h else float(h[eid] == gt)}
            r["oracle"] = None if r["nocap"] is None or r["cap"] is None else max(r["nocap"], r["cap"])
            r["disagree"] = (n.get(eid) != c.get(eid))
            rows.append(r)
    if missing:
        print(f"[WARN] {missing} manifest videos not found in one of the runs")

    cols = ["nocap", "cap", "oracle"] + (["seed"] if held else [])
    print(f"\n{'subset':12} {'n':>5} " + " ".join(f"{c:>8}" for c in cols))
    for name, sub in [("all", rows), ("gt=PASS", [r for r in rows if r["gt"] == "PASS"]), ("gt=FAIL", [r for r in rows if r["gt"] == "FAIL"])]:
        vals = [acc(sub, c) for c in cols]
        print(f"{name:12} {len(sub):5d} " + " ".join(f"{v[0]:8.3f}" for v in vals))
    dis = [r for r in rows if r["disagree"]]
    cap_wins = sum(1 for r in dis if r["cap"] == 1.0)
    print(f"\nevents where caption/no-caption disagree: {len(dis)} / {len(rows)} "
          f"({len(dis)/max(1,len(rows)):.1%}); caption right in {cap_wins}, no-caption right in {len(dis)-cap_wins}")
    fail_dis = [r for r in dis if r["gt"] == "FAIL"]
    print(f"  of which GT=FAIL: {len(fail_dis)} (caption right {sum(1 for r in fail_dis if r['cap']==1.0)})")

    # video level: all GT events correct
    by_v = defaultdict(list)
    for r in rows:
        by_v[r["relpath"]].append(r)
    print(f"\n{'video-level':12} {'n':>5} " + " ".join(f"{c:>8}" for c in cols))
    vals = []
    for c in cols:
        ok = [all((x[c] or 0.0) == 1.0 for x in v) for v in by_v.values() if all(x[c] is not None for x in v)]
        vals.append(sum(ok) / len(ok) if ok else float("nan"))
    print(f"{'all':12} {len(by_v):5d} " + " ".join(f"{v:8.3f}" for v in vals))


if __name__ == "__main__":
    main()
