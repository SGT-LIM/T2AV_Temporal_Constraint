#!/usr/bin/env python3
"""Apply one caption guide text to a manifest (held-out) and report per-source /
per-bucket V-axis metrics. Use it for seed vs best, and for the three held-out
questions: LTX (generation-model transfer), unseen HD-EPIC participants, and the
"cross" bucket (HD-EPIC good captions + generated bad captions).

    python eval_guide.py --manifest manifests/test.jsonl --guide gepa_runs/base_seed0/best_candidate.txt \
        --run-dir gepa_runs/base_seed0 --tag best
    python eval_guide.py --manifest manifests/test.jsonl --guide gepa_runs/base_seed0/seed_candidate.txt \
        --run-dir gepa_runs/base_seed0 --tag seed

Shares the eval cache with run_gepa.py (same run-dir), so val items already judged
under the same guide are not re-called. Writes <run-dir>/heldout_<tag>.csv (per event)
and prints acc / PASS P,R / FAIL P,R / false-PASS rate per source and bucket.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

from google import genai
from google.genai import types

from adapter import COMPONENT, CaptionGuideAdapter


def metrics(rows):
    n = len(rows)
    if not n:
        return {}
    tp = sum(1 for r in rows if r["gt"] == "PASS" and r["pred"] == "PASS")
    fp = sum(1 for r in rows if r["gt"] == "FAIL" and r["pred"] == "PASS")
    fn = sum(1 for r in rows if r["gt"] == "PASS" and r["pred"] == "FAIL")
    tn = sum(1 for r in rows if r["gt"] == "FAIL" and r["pred"] == "FAIL")
    d = lambda a, b: a / b if b else float("nan")
    return {"n": n, "acc": d(tp + tn, n), "pass_P": d(tp, tp + fp), "pass_R": d(tp, tp + fn),
            "fail_P": d(tn, tn + fn), "fail_R": d(tn, tn + fp), "false_pass_rate": d(fp, fp + tn)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--guide", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--thinking-level", default="high", choices=["low", "high", "none"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    items = [json.loads(l) for l in a.manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    guide = a.guide.read_text(encoding="utf-8")
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=600_000)) if api_key \
        else genai.Client(http_options=types.HttpOptions(timeout=600_000))
    adapter = CaptionGuideAdapter(client, a.model, a.run_dir, thinking_level=a.thinking_level,
                                  workers=a.workers, max_chars=10**9)
    eb = adapter.evaluate(items, {COMPONENT: guide}, capture_traces=True)

    out_rows = []
    for it, tr in zip(items, eb.trajectories):
        reason_of = {pe["event_id"]: pe for pe in tr["per_event"]}
        for eid, gt, pred, s in tr["rows"]:
            out_rows.append({"source": it["source"], "bucket": it.get("bucket", ""), "group": it.get("group", ""),
                             "relpath": it["relpath"], "event_id": eid, "gt": gt, "pred": pred, "score": s,
                             "caption_ok": it.get("caption_ok", {}).get(eid),
                             "reason": reason_of.get(eid, {}).get("reason", ""), "error": tr.get("error") or ""})
    out_csv = a.run_dir / f"heldout_{a.tag}.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)

    groups = defaultdict(list)
    for r in out_rows:
        groups[("all", "")].append(r)
        groups[(r["source"], "")].append(r)
        if r["bucket"]:
            groups[(r["source"], r["bucket"])].append(r)
        if r["caption_ok"] is not None:
            groups[(r["source"], "caption_ok=%d" % int(r["caption_ok"]))].append(r)
    print(f"guide={a.guide} tag={a.tag} chars={len(guide)}")
    print(f"{'source':10} {'bucket':14} {'n':>5} {'acc':>6} {'passP':>6} {'passR':>6} {'failP':>6} {'failR':>6} {'fPASS':>6}")
    for (src, b), rows in sorted(groups.items()):
        m = metrics(rows)
        print(f"{src:10} {b:14} {m['n']:5d} {m['acc']:6.3f} {m['pass_P']:6.3f} {m['pass_R']:6.3f} "
              f"{m['fail_P']:6.3f} {m['fail_R']:6.3f} {m['false_pass_rate']:6.3f}")
    print("wrote", out_csv)


if __name__ == "__main__":
    main()
