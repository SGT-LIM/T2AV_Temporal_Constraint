#!/usr/bin/env python3
"""Split + subsample the item x axis GT rows into GEPA train / val / test manifests.

Two ways to split:
  (a) --old-manifests DIR...   reuse the caption-GEPA split (seed 0, 60/15/25): HD-EPIC by clip, 220 by video. Rows whose
      split_key is not in the old manifests get a deterministic hash split with the same 60/15/25 (warned).
  (b) --resplit 40/30/30       fresh deterministic hash split (seed) of every split_key (HD-EPIC clip, 220 video) with these
      train/val/test percentages. Used for the stage-1 GEPA (10/21): bigger val from the 220 set, test stays >= 30%.
Either way the same clip / video lands in one split for all axes and variants (split_key is the clip / video).

Subsample: per axis, train = HD-EPIC --train-hd (FAIL fraction --fail-frac) + --train-gen (ltx/mova half each, same fraction);
val = HD-EPIC --val-hd (FAIL/PASS balanced) + --val-gen (ltx/mova half each, natural ratio); test = everything in the test
split (incl. eval_only rows). eval_only rows never enter train/val. If a pool is smaller than asked, it is used whole.

Stage-2 GEPA (10/20):
  python gepa_stage2/manifest.py --gt gepa_stage2/manifests/gt_*.jsonl --old-manifests gepa_caption_guide/manifests gepa_caption_guide/manifests_ltx \
        --out-dir gepa_stage2/manifests --seed 0 --fail-frac 0.45 --train-hd 20 --train-gen 10 --val-hd 10 --val-gen 6
Stage-1 GEPA (10/21, 1:1 HD-EPIC : 220 in train and val):
  python gepa_stage2/manifest.py --gt gepa_stage2/manifests/gt_*.jsonl --resplit 40/30/30 \
        --out-dir gepa_stage2/manifests_s1 --seed 0 --fail-frac 0.45 --train-hd 40 --train-gen 40 --val-hd 30 --val-gen 30
"""
import argparse, glob, hashlib, json, os, random, re
from collections import defaultdict
from pathlib import Path

import pandas as pd

CLIP_RE = re.compile(r"(P\d+-\d+-\d+_\d+)")


def load_rows(paths):
    rows = []
    for p in paths:
        for g in glob.glob(p):
            rows += [json.loads(l) for l in open(g)]
    return rows


def old_split_map(dirs):
    """split_key -> 'train'|'val'|'test' from the caption-GEPA manifests."""
    m = {}
    for d in dirs:
        for sp in ("train", "val", "test"):
            p = f"{d}/{sp}.jsonl"
            if not os.path.exists(p):
                continue
            for l in open(p):
                r = json.loads(l)
                base = os.path.basename(r["relpath"])
                mm = CLIP_RE.search(base)
                key = mm.group(1) if mm else os.path.splitext(base)[0]
                m[key] = sp
                stem = os.path.splitext(base)[0]
                m[stem] = sp
                m[re.sub(r"_*v\d+_raw$", "", stem)] = sp      # 220: clap-..__order_v1_raw -> item_id
    return m


def hash_split(key, seed, pct=(60, 15, 25)):
    h = int(hashlib.md5(f"{seed}:{key}".encode()).hexdigest(), 16) % 100
    return "train" if h < pct[0] else "val" if h < pct[0] + pct[1] else "test"


def is_fail(r):
    return "no" in r["gt"].values()


def pick(rows, n, fail_frac, rng):
    """n rows with about fail_frac FAIL; falls back to what exists."""
    f = [r for r in rows if is_fail(r)]; p = [r for r in rows if not is_fail(r)]
    rng.shuffle(f); rng.shuffle(p)
    nf = min(len(f), round(n * fail_frac)); np_ = min(len(p), n - nf)
    if nf + np_ < n:                       # top up from whichever side has more
        extra = (f[nf:] + p[np_:])[: n - nf - np_]
        return f[:nf] + p[:np_] + extra
    return f[:nf] + p[:np_]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", nargs="+", required=True)
    ap.add_argument("--old-manifests", nargs="*", default=[], help="reuse the caption-GEPA split (mode a)")
    ap.add_argument("--resplit", default=None, help="fresh hash split, e.g. 40/30/30 (mode b)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fail-frac", type=float, default=0.45)
    ap.add_argument("--train-hd", type=int, default=20); ap.add_argument("--train-gen", type=int, default=10)
    ap.add_argument("--val-hd", type=int, default=10); ap.add_argument("--val-gen", type=int, default=6)
    a = ap.parse_args()
    if bool(a.old_manifests) == bool(a.resplit):
        ap.error("give exactly one of --old-manifests or --resplit")
    rng = random.Random(a.seed)

    rows = load_rows(a.gt)
    if a.resplit:
        pct = tuple(int(x) for x in a.resplit.split("/"))
        assert len(pct) == 3 and sum(pct) == 100, "--resplit must be three percentages summing to 100"
        for r in rows:
            r["split"] = hash_split(r["split_key"], a.seed, pct)
        print(f"[split] fresh hash split {pct} seed {a.seed} over {len({r['split_key'] for r in rows})} clips / videos")
    else:
        smap = old_split_map(a.old_manifests)
        unmapped = 0
        for r in rows:
            sp = smap.get(r["split_key"])
            if sp is None:
                sp = hash_split(r["split_key"], a.seed); unmapped += 1
            r["split"] = sp
        if unmapped:
            print(f"[warn] {unmapped}/{len(rows)} rows had no split in the old manifests -> hash split")

    # videos / clips per split and source (sanity: 220 should be ~44/33/33 per model with 40/30/30)
    keys = defaultdict(set)
    for r in rows:
        keys[(r["source"], r["split"])].add(r["split_key"])
    print("== clips / videos per split:")
    for src in ("hdepic", "ltx", "mova"):
        print(f"  {src:6s} " + "  ".join(f"{sp} {len(keys[(src, sp)]):4d}" for sp in ("train", "val", "test")))

    # same clip / video must land in one split for all axes & variants (it does, split_key is the clip)
    pools = defaultdict(list)
    for r in rows:
        pools[(r["split"], r["source"], r["axis"])].append(r)

    train, val = [], []
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        hd = [r for r in pools[("train", "hdepic", ax)] if not r["eval_only"]]
        train += pick(hd, a.train_hd, a.fail_frac, rng)
        for src in ("ltx", "mova"):
            train += pick([r for r in pools[("train", src, ax)]], a.train_gen // 2, a.fail_frac, rng)
        hdv = [r for r in pools[("val", "hdepic", ax)] if not r["eval_only"]]
        val += pick(hdv, a.val_hd, 0.5, rng)                       # balanced
        for src in ("ltx", "mova"):
            g = list(pools[("val", src, ax)]); rng.shuffle(g)
            val += g[: a.val_gen // 2]                             # natural ratio
    test = [r for r in rows if r["split"] == "test"]

    Path(a.out_dir).mkdir(parents=True, exist_ok=True)
    for name, rs in (("train", train), ("val", val), ("test", test), ("all", rows)):
        with open(f"{a.out_dir}/{name}.jsonl", "w") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")
        df = pd.DataFrame(rs)
        if len(df):
            df["fail"] = df.apply(is_fail, axis=1)
            print(f"== {name}: {len(df)} rows")
            print(df.groupby(["source", "axis"]).fail.agg(n="size", n_fail="sum").to_string())
    # leakage check
    tk = {r["split_key"] for r in train + val}
    leak = [r for r in test if r["split_key"] in tk]
    print(f"\nleak check: {len(leak)} test rows share a clip/video with train or val (must be 0)")


if __name__ == "__main__":
    main()
