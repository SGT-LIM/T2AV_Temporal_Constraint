#!/usr/bin/env python3
"""Grouped bar charts of accuracy / precision / recall vs human GT for a few
eval conditions, one figure per generation model, one panel per axis.

Default comparison: single-agent pure Gemini vs multi-agent pure Gemini.

    python plot_conditions.py \
        --gt /projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/min3_gt/gt_video.csv \
        --eval-root /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results \
        --cond "single pure Gemini=single_agent/baseline_min3/{M}_pure_gemini.csv" \
        --cond "multi-agent pure Gemini=multi_agent/baseline_min3/{M}_agentic_pure_gemini.csv" \
        --axes A V AVB --out-dir /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/figs \
        --tag single_vs_multi

{M} is replaced by the model name (LTX_2p3, MOVA). Add more --cond lines to
compare more conditions in the same chart (e.g. + Whisper/FLAM, + captions).

Positive class for precision/recall is FAIL by default (the judge's job is to
catch generation failures); --positive PASS flips it. The majority-class baseline is kept in the CSV (majority_acc) but not drawn.
Rows are de-duplicated on video_file; GT TIE rows are dropped.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PRED_COLS = {"A": "audio_event_correctness", "V": "visual_event_correctness",
             "AVB": "audio_visual_binding", "TCREL": "temporal_relation_satisfaction",
             "TCCNT": "temporal_count_satisfaction", "CC": "constraint_compliance"}
AXIS_TITLE = {"A": "Audio correctness (A)", "V": "Visual correctness (V)",
              "AVB": "Audio-visual binding (AVB)", "TCREL": "Temporal relation (TC-Rel)",
              "TCCNT": "Temporal count (TC-Count)", "CC": "Constraint compliance (CC)"}
MODELS = ["LTX_2p3", "MOVA"]


def norm(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in ("yes", "pass", "true", "1", "y"):
        return "PASS"
    if s in ("no", "fail", "false", "0", "n"):
        return "FAIL"
    return None


def load_cond(root: Path, pattern: str, model: str, gt: pd.DataFrame):
    f = root / pattern.format(M=model)
    if not f.exists():
        raise FileNotFoundError(f)
    df = pd.read_csv(f)
    df = df[~df["overall_reason"].fillna("").str.startswith("ERROR")]
    df = df.drop_duplicates("video_file", keep="last").copy()
    for ax, col in PRED_COLS.items():
        df[f"{ax}_pred"] = df[col].map(norm) if col in df.columns else None
    df["model"] = model
    return df.merge(gt[gt.model == model], on=["model", "video_file"], how="inner")


def scores(j: pd.DataFrame, ax: str, pos: str):
    p, g = f"{ax}_pred", f"{ax}_gt"
    sub = j[j[p].notna() & j[g].isin(["PASS", "FAIL"])]
    if sub.empty:
        return None
    tp = ((sub[p] == pos) & (sub[g] == pos)).sum()
    fp = ((sub[p] == pos) & (sub[g] != pos)).sum()
    fn = ((sub[p] != pos) & (sub[g] == pos)).sum()
    acc = (sub[p] == sub[g]).mean()
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    maj = max((sub[g] == "PASS").mean(), (sub[g] == "FAIL").mean())
    return {"n": len(sub), "acc": acc, "precision": prec, "recall": rec,
            "majority_acc": maj, "gt_pos_rate": (sub[g] == pos).mean(),
            "pred_pos_rate": (sub[p] == pos).mean()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", type=Path, required=True)
    ap.add_argument("--eval-root", type=Path, required=True)
    ap.add_argument("--cond", action="append", required=True,
                    help='"Label=relative/path/{M}_file.csv" (repeatable)')
    ap.add_argument("--axes", nargs="+", default=["A", "V", "AVB"])
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--positive", default="FAIL", choices=["FAIL", "PASS"])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--tag", default="conditions")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gt = pd.read_csv(args.gt)
    gt = gt[["model", "video_file"] + [c for c in gt.columns if c.endswith("_gt")]]
    conds = [c.split("=", 1) for c in args.cond]

    rows = []
    for model in args.models:
        # width grows with the number of conditions so 5-6 bars per group stay readable
        panel_w = max(4.2, 1.1 + 0.85 * len(conds))
        fig, axes = plt.subplots(1, len(args.axes), figsize=(panel_w * len(args.axes), 4.6), sharey=True)
        if len(args.axes) == 1:
            axes = [axes]
        for k, ax_name in enumerate(args.axes):
            axp = axes[k]
            metrics = ["acc", "precision", "recall"]
            width = 0.8 / len(conds)
            maj = None
            for ci, (label, pattern) in enumerate(conds):
                j = load_cond(args.eval_root, pattern, model, gt)
                s = scores(j, ax_name, args.positive)
                if s is None:
                    continue
                maj = s["majority_acc"]
                rows.append({"model": model, "axis": ax_name, "condition": label, **s})
                xs = [i + (ci - (len(conds) - 1) / 2) * width for i in range(len(metrics))]
                vals = [s[m] for m in metrics]
                bars = axp.bar(xs, vals, width * 0.95, label=label)
                for b, v in zip(bars, vals):
                    if v == v:  # not nan
                        axp.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.2f}",
                                 ha="center", va="bottom", fontsize=7, rotation=90 if len(conds) > 3 else 0)
            axp.set_xticks(range(len(metrics)))
            axp.set_xticklabels(["accuracy", f"precision\n({args.positive})", f"recall\n({args.positive})"])
            axp.set_ylim(0, 1.18)
            axp.set_title(f"{AXIS_TITLE.get(ax_name, ax_name)}  n={s['n'] if s else 0}", fontsize=10)
            axp.grid(axis="y", alpha=0.3)
        axes[0].set_ylabel("score vs. human majority GT")
        handles, labels = axes[0].get_legend_handles_labels()
        ncol = min(len(conds), 3)
        fig.legend(handles, labels, loc="lower center", ncol=ncol, fontsize=9, frameon=False,
                   bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"{model}: judge vs. human GT (min3, {len(gt[gt.model==model])} videos)", fontsize=11)
        legend_rows = -(-len(conds) // ncol)
        fig.tight_layout(rect=(0, 0.06 + 0.05 * legend_rows, 1, 1))
        out = args.out_dir / f"{args.tag}_{model}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"[INFO] wrote {out}")

    res = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print("\n" + res.round(3).to_string(index=False))
    res.to_csv(args.out_dir / f"{args.tag}.csv", index=False)


if __name__ == "__main__":
    main()
