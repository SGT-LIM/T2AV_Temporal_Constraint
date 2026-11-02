#!/usr/bin/env python3
"""Subsample a manifest per source, keeping the share of videos that contain a
FAIL event (stratified), so GEPA's train/val mix is balanced across datasets.

    python subsample.py --in manifests/train.jsonl --out manifests/train_s.jsonl --per-source hdepic=60 mova=40 --seed 0
    python subsample.py --in manifests/val.jsonl   --out manifests/val_s.jsonl   --per-source hdepic=30 mova=16 --seed 0

--fail-frac F overrides the natural share of FAIL-containing videos (e.g. 0.5 to
oversample hand/noun swap items in train). Omit to keep the source's own share.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-source", nargs="+", required=True, help="source=N ...")
    ap.add_argument("--fail-frac", type=float, default=None)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    caps = {k: int(v) for k, v in (s.split("=") for s in a.per_source)}
    rows = [json.loads(l) for l in a.inp.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = defaultdict(lambda: {"fail": [], "pass": []})
    for r in rows:
        by[r["source"]]["fail" if "FAIL" in r["gt"].values() else "pass"].append(r)
    out = []
    for src, n in caps.items():
        f, p = by[src]["fail"], by[src]["pass"]
        if not f and not p:
            print(f"{src}: not in manifest"); continue
        frac = a.fail_frac if a.fail_frac is not None else len(f) / (len(f) + len(p))
        nf = min(len(f), int(round(n * frac))); np_ = min(len(p), n - nf)
        rng.shuffle(f); rng.shuffle(p)
        pick = f[:nf] + p[:np_]
        rng.shuffle(pick)
        out += pick
        print(f"{src}: {len(pick)} videos (with FAIL={nf}, all-PASS={np_}) from {len(f)}+{len(p)}")
    rng.shuffle(out)
    with a.out.open("w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", a.out, len(out))


if __name__ == "__main__":
    main()
