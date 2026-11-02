#!/usr/bin/env python3
"""GEPA v3 manifests: hash split 40/30/30 by clip / video, per-source quotas per axis, val FAIL minimum per axis.
Rows stay (item, axis); the adapter groups them into video units (source, item_id) for minibatches and reflection.

  python gepa_stage2/manifest_v3.py --gt gepa_stage2/manifests_v3/gt_*.jsonl gepa_stage2/manifests/gt_ltx.jsonl gepa_stage2/manifests/gt_mova.jsonl \
      --out-dir gepa_stage2/manifests_v3 --seed 0 --split 40/30/30 \
      --quota hdepic=40,30 hdfoot=16,12 hdmove=24,16 ltx=20,15 mova=20,15 --fail-frac 0.45 --val-fail-frac 0.5 --val-min-fail 8
quota = per axis, per source: train,val row counts (sources without that axis are skipped). A pool smaller than asked is used whole.
"""
import argparse, glob, hashlib, json, random
from collections import defaultdict
from pathlib import Path

import pandas as pd

AXES = ("A", "V", "AVB", "TCR", "TCC")


def load_rows(paths):
    rows = []
    for p in paths:
        for g in sorted(glob.glob(p)):
            rows += [json.loads(l) for l in open(g)]
    return rows


def hash_split(key, seed, pct):
    h = int(hashlib.md5(f"{seed}:{key}".encode()).hexdigest(), 16) % 100
    return "train" if h < pct[0] else "val" if h < pct[0] + pct[1] else "test"


def is_fail(r):
    return "no" in r["gt"].values()


def pick(rows, n, fail_frac, rng):
    f = [r for r in rows if is_fail(r)]; p = [r for r in rows if not is_fail(r)]
    rng.shuffle(f); rng.shuffle(p)
    nf = min(len(f), round(n * fail_frac)); np_ = min(len(p), n - nf)
    if nf + np_ < n:
        extra = (f[nf:] + p[np_:])[: n - nf - np_]
        return f[:nf] + p[:np_] + extra
    return f[:nf] + p[:np_]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", nargs="+", required=True); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--split", default="40/30/30")
    ap.add_argument("--quota", nargs="+", required=True, help="src=train,val (rows per axis)")
    ap.add_argument("--fail-frac", type=float, default=0.45); ap.add_argument("--val-fail-frac", type=float, default=0.5)
    ap.add_argument("--val-min-fail", type=int, default=8, help="warn if an axis has fewer FAIL rows in val")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    pct = tuple(int(x) for x in a.split.split("/")); assert sum(pct) == 100
    quota = {}
    for q in a.quota:
        src, tv = q.split("="); t, v = tv.split(","); quota[src] = (int(t), int(v))

    rows = load_rows(a.gt)
    for r in rows:
        r["split"] = hash_split(r["split_key"], a.seed, pct)
    pools = defaultdict(list)
    for r in rows:
        pools[(r["split"], r["source"], r["axis"])].append(r)
    srcs = sorted({r["source"] for r in rows})
    print(f"[split] {pct} seed {a.seed}; sources {srcs}")
    keys = defaultdict(set)
    for r in rows:
        keys[(r["source"], r["split"])].add(r["split_key"])
    for s in srcs:
        print(f"  {s:7s} clips/videos " + "  ".join(f"{sp} {len(keys[(s, sp)]):4d}" for sp in ("train", "val", "test")))

    train, val = [], []
    for ax in AXES:
        for s in srcs:
            if s not in quota:
                continue
            nt, nv = quota[s]
            tr = [r for r in pools[("train", s, ax)] if not r.get("eval_only")]
            va = [r for r in pools[("val", s, ax)] if not r.get("eval_only")]
            if tr: train += pick(tr, nt, a.fail_frac, rng)
            if va: val += pick(va, nv, a.val_fail_frac, rng)
    test = [r for r in rows if r["split"] == "test"]

    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for name, rs in (("train", train), ("val", val), ("test", test), ("all", rows)):
        with open(f"{a.out_dir}/{name}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")
        df = pd.DataFrame(rs)
        df["fail"] = df.apply(is_fail, axis=1)
        units = df.groupby(["source", "item_id"]).ngroups
        print(f"\n== {name}: {len(df)} rows, {units} video units")
        print(df.groupby(["axis", "source"]).fail.agg(n="size", n_fail="sum").to_string())
        if name == "val":
            byax = df.groupby("axis").fail.agg(n="size", n_fail="sum")
            for ax, r in byax.iterrows():
                if r.n_fail < a.val_min_fail or r.n - r.n_fail < a.val_min_fail:
                    print(f"  [warn] val axis {ax}: FAIL {int(r.n_fail)} / PASS {int(r.n - r.n_fail)} (< {a.val_min_fail})")
    tk = {r["split_key"] for r in train + val}
    leak = [r for r in test if r["split_key"] in tk]
    print(f"\nleak check: {len(leak)} test rows share a clip/video with train or val (must be 0)")


if __name__ == "__main__":
    main()