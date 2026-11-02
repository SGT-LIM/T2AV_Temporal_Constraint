#!/usr/bin/env python3
"""Compare all min3 eval CSVs against the human majority-vote GT.

    python compare_min3.py \
        --gt /projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/min3_gt/gt_video.csv \
        --eval-root /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results \
        --out /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/summary_min3.csv

    # optional slicing of one axis by an eval-CSV column
    python compare_min3.py --gt ... --eval-root ... --by modality_combination --axis V

Every CSV under eval_root (excluding *_per_event.csv and *.bak) is one
condition x model. Rows are de-duplicated on video_file (first row kept) since
some runs were accidentally executed 2-3x in parallel. Predictions yes/pass ->
PASS, no/fail -> FAIL, skipped/blank -> ignored. GT TIE rows are ignored.

Metrics per condition x model x axis:
  n        videos with both a prediction and a non-TIE GT label
  acc      accuracy vs majority GT
  acc_u    accuracy on the unanimous-GT subset (n_u videos)
  fail_rec recall of GT FAIL (how many human-flagged failures the judge caught)
  pass_rec recall of GT PASS
  pred_pass / gt_pass  PASS rate of judge / of humans
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

PRED_COLS = {
    "A": "audio_event_correctness",
    "V": "visual_event_correctness",
    "AVB": "audio_visual_binding",
    "TCREL": "temporal_relation_satisfaction",
    "TCCNT": "temporal_count_satisfaction",
    "CC": "constraint_compliance",
}
MODELS = ["LTX_2p3", "MOVA"]


def norm(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in ("yes", "pass", "true", "1", "y"):
        return "PASS"
    if s in ("no", "fail", "false", "0", "n"):
        return "FAIL"
    return None  # skipped / unparsable


def find_eval_csvs(root: Path):
    out = []
    for f in sorted(root.rglob("*.csv")):
        if "_per_event" in f.name or f.suffix != ".csv" or ".bak" in f.name:
            continue
        m = next((m for m in MODELS if f.name.startswith(m + "_")), None)
        if m is None:
            continue
        cond = f"{f.parent.name}/{f.name[len(m) + 1:-4]}"
        out.append((cond, m, f))
    return out


def metrics(df, ax):
    p, g = f"{ax}_pred", f"{ax}_gt"
    sub = df[df[p].notna() & df[g].isin(["PASS", "FAIL"])]
    if sub.empty:
        return None
    hit = (sub[p] == sub[g])
    fails = sub[sub[g] == "FAIL"]
    passes = sub[sub[g] == "PASS"]
    un = sub[sub[f"{ax}_unanimous"].fillna(False).astype(bool)]
    return {
        "n": len(sub),
        "acc": round(hit.mean(), 3),
        "n_u": len(un),
        "acc_u": round((un[p] == un[g]).mean(), 3) if len(un) else None,
        "fail_rec": round((fails[p] == "FAIL").mean(), 3) if len(fails) else None,
        "pass_rec": round((passes[p] == "PASS").mean(), 3) if len(passes) else None,
        "pred_pass": round((sub[p] == "PASS").mean(), 3),
        "gt_pass": round((sub[g] == "PASS").mean(), 3),
        "maj_acc": round(max((sub[g] == "PASS").mean(), (sub[g] == "FAIL").mean()), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--eval-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--axes", nargs="+", default=list(PRED_COLS))
    ap.add_argument("--by", default=None, help="eval-CSV column to slice by (e.g. modality_combination, temporal_type)")
    ap.add_argument("--axis", default="V", help="axis used with --by")
    ap.add_argument("--filter", default=None, help="regex on condition name, e.g. 'caption|baseline'")
    args = ap.parse_args()

    gt = pd.read_csv(args.gt)
    gt_cols = ["model", "video_file"] + [c for c in gt.columns if c.endswith(("_gt", "_unanimous"))]
    gt = gt[gt_cols]

    long_rows, slice_rows = [], []
    for cond, model, f in find_eval_csvs(args.eval_root):
        if args.filter and not re.search(args.filter, cond):
            continue
        try:
            df = pd.read_csv(f)
        except Exception as exc:
            print(f"[WARN] {f}: {exc}")
            continue
        if "video_file" not in df.columns:
            continue
        n_raw = len(df)
        df = df[~df["overall_reason"].fillna("").str.startswith("ERROR")]
        df = df.drop_duplicates("video_file", keep="last").copy()
        for ax, col in PRED_COLS.items():
            df[f"{ax}_pred"] = df[col].map(norm) if col in df.columns else None
        df["model"] = model
        j = df.merge(gt[gt.model == model], on=["model", "video_file"], how="inner")
        row = {"condition": cond, "model": model, "rows_raw": n_raw, "videos": len(df), "matched_gt": len(j)}
        for ax in args.axes:
            m = metrics(j, ax)
            if m:
                for k, v in m.items():
                    row[f"{ax}_{k}"] = v
        long_rows.append(row)

        if args.by and args.by in j.columns:
            for g, sub in j.groupby(args.by):
                m = metrics(sub, args.axis)
                if m:
                    slice_rows.append({"condition": cond, "model": model, args.by: g, **{f"{args.axis}_{k}": v for k, v in m.items()}})

    res = pd.DataFrame(long_rows).sort_values(["condition", "model"])
    pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 500)

    print("\n=== coverage (rows_raw > videos means duplicated runs; matched_gt should equal videos) ===")
    print(res[["condition", "model", "rows_raw", "videos", "matched_gt"]].to_string(index=False))

    for ax in args.axes:
        cols = [c for c in res.columns if c.startswith(ax + "_")]
        if not cols:
            continue
        sub = res[["condition", "model"] + cols].dropna(subset=[f"{ax}_acc"])
        if sub.empty:
            continue
        print(f"\n=== axis {ax} ===")
        print(sub.to_string(index=False))

    if slice_rows:
        sl = pd.DataFrame(slice_rows)
        print(f"\n=== axis {args.axis} sliced by {args.by} ===")
        print(sl.to_string(index=False))
        if args.out:
            sl.to_csv(args.out.with_name(args.out.stem + f"_by_{args.by}.csv"), index=False)

    if args.out:
        res.to_csv(args.out, index=False)
        print(f"\n[INFO] wrote {args.out}")


if __name__ == "__main__":
    main()
