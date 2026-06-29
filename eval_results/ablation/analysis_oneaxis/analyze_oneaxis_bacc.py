#!/usr/bin/env python3
"""
(a) One-axis-at-a-time ICL analysis.

For each ICL condition (full, a, v, avb, tc_relation, tc_count), compute the
PER-AXIS balanced accuracy of the Gemini judge against human labels (GT), and
draw a grouped bar chart (x = evaluation axis, bars = ICL condition).

Balanced accuracy = mean of the per-class recalls (yes-recall + no-recall)/2,
which is the metric the project uses because the GT is class-imbalanced
(majority "yes"), so plain accuracy flatters the judge.

Schemas this expects (already produced by your pipeline):
  Human GT  : <workbook>.xlsx, sheet "Annotation", columns row_id + human_label.
              row_id parses as  <item_id>__<variant><event_or_relation>__<axis_suffix>
              e.g.  Sp_Si_So_rel_sync_cnt__0event_1__A
                    Sp_Si_So_rel_sync_cnt__0relation__TC-Relation
  Gemini    : per-event CSV (item_csv stem + "_per_event"): one row per
              video x event x per-event axis. A/V/AVB use the `label` column;
              temporal_count_satisfaction uses `count_correct`.
              TC-Relation is NOT per-event; it lives in the main item CSV column
              `temporal_relation_satisfaction`.

EDIT THE CONFIG BLOCK BELOW, then:  python analyze_oneaxis_bacc.py
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ===========================================================================
# CONFIG  --  edit these paths to point at your files.
# ===========================================================================

GEM = "/home/coder/T2AV/eval_results/gemini"
ONEAXIS = f"{GEM}/mova-icl-oneaxis"          # per-axis (a) runs live here
FULL_ITEM = f"{GEM}/MOVA/NoTools-ICL.csv"    # current-state full ICL
NO_ICL_ITEM = f"{GEM}/MOVA/NoTools.csv"

# One entry per ICL condition. "item" = the main per-video CSV (used for
# TC-Relation); "per_event" = its _per_event sibling (A / V / AVB / TC-Count).
# The harness writes <stem>_per_event.csv next to each result CSV automatically;
# if yours are named differently, fix the per_event paths below.
CONDITIONS: dict[str, dict] = {
    "no_icl":      {"item": NO_ICL_ITEM, "per_event": NO_ICL_ITEM.replace(".csv", "_per_event.csv")},
    "full":        {"item": FULL_ITEM,                    "per_event": FULL_ITEM.replace(".csv", "_per_event.csv")},
    "a":           {"item": f"{ONEAXIS}/result_a.csv",            "per_event": f"{ONEAXIS}/result_a_per_event.csv"},
    "v":           {"item": f"{ONEAXIS}/result_v.csv",            "per_event": f"{ONEAXIS}/result_v_per_event.csv"},
    "avb":         {"item": f"{ONEAXIS}/result_avb.csv",          "per_event": f"{ONEAXIS}/result_avb_per_event.csv"},
    "tcr": {"item": f"{ONEAXIS}/result_tcr.csv",  "per_event": f"{ONEAXIS}/result_tcr_per_event.csv"},
    "tcc":    {"item": f"{ONEAXIS}/result_tcc.csv",     "per_event": f"{ONEAXIS}/result_tcc_per_event.csv"},
}

# Human GT workbook(s). MOVA only for this run.
HUMAN_GT_XLSX: list[str] = [
    "/home/coder/T2AV/eval_results/human/YS_eval_annotation_mova.xlsx",
]
HUMAN_SHEET = "Annotation"               # change if your sheet is named differently

OUT_DIR = Path("/home/coder/T2AV/eval_results/ablation_analysis_oneaxis")   # where to write outputs
RESULTS_CSV = OUT_DIR / "oneaxis_balanced_accuracy.csv"
CHART_PNG   = OUT_DIR / "oneaxis_balanced_accuracy.png"

# Fixed display order.
AXIS_ORDER = ["A", "V", "AVB", "TC-Relation", "TC-Count"]
CONDITION_ORDER = ["no_icl", "full", "a", "v", "avb", "tcr", "tcc"]

# Which axis each condition is *teaching* (for the on-diagonal "*" marker).
CONDITION_TAUGHT_AXIS = {
    "a": "A", "v": "V", "avb": "AVB",
    "tcr": "TC-Relation", "tcc": "TC-Count",
}

# Gemini axis field -> short axis suffix used in the GT row_id.
AXIS_FIELD_TO_SUFFIX = {
    "audio_event_correctness": "A",
    "visual_event_correctness": "V",
    "audio_visual_binding": "AVB",
    "temporal_count_satisfaction": "TC-Count",
    "temporal_relation_satisfaction": "TC-Relation",
}

# ===========================================================================
# Helpers
# ===========================================================================

_YES = {"yes", "y", "true", "1", "pass", "correct"}
_NO = {"no", "n", "false", "0", "fail", "incorrect"}


def norm_label(v) -> str | float:
    """Normalize any yes/no-ish value to 'yes'/'no'; unknown -> NaN."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    s = str(v).strip().lower()
    if s in _YES:
        return "yes"
    if s in _NO:
        return "no"
    return np.nan


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean of per-class recalls over the classes present in y_true."""
    recalls = []
    for c in ("yes", "no"):
        mask = y_true == c
        n = int(mask.sum())
        if n == 0:
            continue
        recalls.append(float((y_pred[mask] == c).mean()))
    return float(np.mean(recalls)) if recalls else float("nan")


def parse_row_id(rid: str):
    """<item_id>__<variant><event_or_relation>__<axis_suffix> -> (item, ev, suffix)."""
    import re
    m = re.match(r"^(.*?)__(\d+)(event_\d+|relation)__(.+)$", str(rid))
    if not m:
        return (np.nan, np.nan, np.nan)
    item_id, _variant, ev, suffix = m.groups()
    return (item_id, ev, suffix)


def load_human(xlsx_paths: list[str]) -> pd.DataFrame:
    frames = []
    for p in xlsx_paths:
        if not Path(p).exists():
            print(f"[WARN] human GT not found, skipping: {p}")
            continue
        h = pd.read_excel(p, sheet_name=HUMAN_SHEET)
        if "row_id" not in h.columns or "human_label" not in h.columns:
            print(f"[WARN] {p} missing row_id/human_label; columns={list(h.columns)}")
            continue
        parsed = h["row_id"].apply(parse_row_id)
        h = h.assign(
            item_id=[z[0] for z in parsed],
            ev=[z[1] for z in parsed],
            axis_suffix=[z[2] for z in parsed],
        )
        h["key"] = h["item_id"].astype(str) + "|" + h["ev"].astype(str) + "|" + h["axis_suffix"].astype(str)
        h["human"] = h["human_label"].map(norm_label)
        frames.append(h[["key", "axis_suffix", "human"]])
    if not frames:
        sys.exit("[FATAL] no usable human GT workbook found. Fix HUMAN_GT_XLSX.")
    out = pd.concat(frames, ignore_index=True).dropna(subset=["human"])
    # Drop duplicate keys (e.g. multiple annotators) -> keep first; adjust if you
    # want majority vote across annotators.
    out = out.drop_duplicates(subset=["key"], keep="first")
    return out


def load_gemini(item_csv: str | None, per_event_csv: str | None) -> pd.DataFrame:
    """Return long Gemini predictions: columns [key, axis_suffix, pred]."""
    rows = []

    # A / V / AVB / TC-Count from the per-event file.
    if per_event_csv and Path(per_event_csv).exists():
        pe = pd.read_csv(per_event_csv)
        for _, r in pe.iterrows():
            suffix = AXIS_FIELD_TO_SUFFIX.get(str(r.get("axis", "")))
            if suffix is None or suffix == "TC-Relation":
                continue
            if suffix == "TC-Count":
                pred = norm_label(r.get("count_correct"))
            else:
                pred = norm_label(r.get("label"))
            key = f'{r.get("item_id")}|{r.get("event_id")}|{suffix}'
            rows.append((key, suffix, pred))
    elif per_event_csv:
        print(f"[WARN] per_event CSV not found: {per_event_csv}")

    # TC-Relation from the main item file (one row per video).
    if item_csv and Path(item_csv).exists():
        it = pd.read_csv(item_csv)
        if "temporal_relation_satisfaction" in it.columns:
            for _, r in it.iterrows():
                key = f'{r.get("item_id")}|relation|TC-Relation'
                rows.append((key, "TC-Relation", norm_label(r.get("temporal_relation_satisfaction"))))
        else:
            print(f"[WARN] {item_csv} has no temporal_relation_satisfaction column.")
    elif item_csv:
        print(f"[WARN] item CSV not found: {item_csv}")

    g = pd.DataFrame(rows, columns=["key", "axis_suffix", "pred"]).dropna(subset=["pred"])
    g = g.drop_duplicates(subset=["key"], keep="first")
    return g


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    human = load_human(HUMAN_GT_XLSX)
    print(f"[INFO] human GT rows: {len(human)}  "
          f"(yes={int((human.human=='yes').sum())}, no={int((human.human=='no').sum())})")

    records = []
    for cond in CONDITION_ORDER:
        if cond not in CONDITIONS:
            continue
        cfg = CONDITIONS[cond]
        g = load_gemini(cfg.get("item"), cfg.get("per_event"))
        if g.empty:
            print(f"[WARN] condition '{cond}': no Gemini predictions loaded; skipping.")
            continue
        merged = g.merge(human[["key", "human"]], on="key", how="inner")
        for axis in AXIS_ORDER:
            sub = merged[merged.axis_suffix == axis]
            if sub.empty:
                records.append(dict(condition=cond, axis=axis, balanced_accuracy=np.nan,
                                    n=0, n_yes_gt=0, n_no_gt=0))
                continue
            yt = sub["human"].to_numpy()
            yp = sub["pred"].to_numpy()
            bacc = balanced_accuracy(yt, yp)
            records.append(dict(
                condition=cond, axis=axis, balanced_accuracy=bacc,
                n=int(len(sub)),
                n_yes_gt=int((yt == "yes").sum()),
                n_no_gt=int((yt == "no").sum()),
            ))

    res = pd.DataFrame.from_records(records)
    if res.empty:
        sys.exit("[FATAL] no results. Check that the condition files exist and keys match the GT.")

    res.to_csv(RESULTS_CSV, index=False)

    # Pretty wide table (condition x axis), with a '*' on the taught (diagonal) cell.
    wide = res.pivot(index="condition", columns="axis", values="balanced_accuracy")
    wide = wide.reindex(index=[c for c in CONDITION_ORDER if c in wide.index],
                        columns=[a for a in AXIS_ORDER if a in wide.columns])
    print("\n=== Per-axis balanced accuracy (rows: ICL condition, cols: axis) ===")
    print("    (* = axis shown in the ICL example answer)\n")
    header = "condition   " + "  ".join(f"{a:>12}" for a in wide.columns)
    print(header)
    for cond, row in wide.iterrows():
        cells = []
        for a in wide.columns:
            val = row[a]
            star = "*" if CONDITION_TAUGHT_AXIS.get(cond) == a else " "
            cells.append(f"{'' if pd.isna(val) else f'{val:.3f}'}{star}".rjust(12))
        print(f"{cond:<11} " + "  ".join(cells))

    # n per cell (so thin cells are visible).
    nwide = res.pivot(index="condition", columns="axis", values="n").reindex(
        index=wide.index, columns=wide.columns)
    print("\n--- n (matched event/relation units per cell) ---")
    print(nwide.to_string())
    print(f"\n[OK] wrote {RESULTS_CSV}")

    plot_grouped_bars(res)
    print(f"[OK] wrote {CHART_PNG}")


def plot_grouped_bars(res: pd.DataFrame) -> None:
    conds = [c for c in CONDITION_ORDER if c in set(res.condition)]
    axes_present = [a for a in AXIS_ORDER if a in set(res.axis)]
    lut = {(r.condition, r.axis): r.balanced_accuracy for r in res.itertuples()}

    n_groups = len(axes_present)
    n_bars = len(conds)
    x = np.arange(n_groups)
    width = min(0.8 / max(n_bars, 1), 0.16)
    cmap = plt.get_cmap("tab10")

    fig, ax = plt.subplots(figsize=(max(8, n_groups * 1.7), 5.2))
    for i, cond in enumerate(conds):
        offsets = x + (i - (n_bars - 1) / 2) * width
        vals = [lut.get((cond, a), np.nan) for a in axes_present]
        bars = ax.bar(offsets, [0 if pd.isna(v) else v for v in vals],
                      width=width, label=cond, color=cmap(i % 10),
                      edgecolor="white", linewidth=0.4)
        for off, v, a in zip(offsets, vals, axes_present):
            if pd.isna(v):
                continue
            ax.text(off, v + 0.012, f"{v:.2f}", ha="center", va="bottom",
                    fontsize=7, rotation=90)
            # mark the on-diagonal (taught) cell.
            if CONDITION_TAUGHT_AXIS.get(cond) == a:
                ax.text(off, v + 0.10, "*", ha="center", va="bottom",
                        fontsize=12, fontweight="bold", color="black")

    ax.axhline(0.5, color="grey", ls="--", lw=1, zorder=0)
    ax.text(n_groups - 0.5, 0.505, "chance (0.5)", ha="right", va="bottom",
            fontsize=8, color="grey")
    ax.set_xticks(x)
    ax.set_xticklabels(axes_present)
    ax.set_ylabel("Balanced accuracy (vs human GT)")
    ax.set_ylim(0, 1.18)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_title("Per-axis balanced accuracy by one-axis ICL condition\n"
                 "(* = axis shown in the ICL example answer)")
    ax.legend(title="ICL condition", ncol=min(len(conds), 6),
              loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_PNG, dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
