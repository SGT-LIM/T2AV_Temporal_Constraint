#!/usr/bin/env python3
"""
ICL ablation analysis: per-AXIS and per-EVENT-KIND balanced accuracy.

Motivation
----------
The ICL example was changed from a 3-event clip (Speech + silent Action +
sounding Action) to a 2-event clip (Speech + silent Action only). Looking at
per-axis accuracy alone hides whether dropping the sounding-action demonstration
hurts the judge specifically on sounding-action *events*. So this script reports
balanced accuracy two ways and lets you compare ICL conditions side by side:

  1. PER-AXIS        : A / V / AVB / TC-Relation / TC-Count          (as before)
  2. PER-EVENT-KIND  : speech / silent_action / sounding_action      (new)
     plus an EVENT-KIND x AXIS breakdown table.

Balanced accuracy = mean of per-class recalls = (yes-recall + no-recall) / 2,
which the project uses because the human GT is class-imbalanced (so plain
accuracy flatters the judge). NOTE: when a cell's GT contains only ONE class
(e.g. TC-Relation here is all "no"), balanced accuracy collapses to that single
class's recall -- the script flags those cells so you don't over-read them.

Schemas (already produced by your pipeline)
-------------------------------------------
  Human GT  : <workbook>.xlsx, sheet "Annotation".
              Needs columns: row_id, human_label.
              row_id parses as  <item_id>__<variant><event_or_relation>__<axis>
              e.g.  Si_So_rel_ord_SiSo__01event_1__V
                    Si_So_rel_ord_SiSo__99relation__TC-Relation
  Gemini    : per-event CSV (<stem>_per_event.csv): one row per
              video x event x per-event axis. A/V/AVB use `label`;
              TC-Count uses `count_correct`; event kind is in `event_kind`.
              TC-Relation is NOT per-event; it lives in the main item CSV
              column `temporal_relation_satisfaction`.

Edit the CONFIG block, then:  python analyze_icl_event_axis.py
"""

from __future__ import annotations
import re
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
GEM = "/home/coder/T2AV/eval_results/gemini/MOVA"

# One entry per ICL condition you want to compare.
#   item      = main per-video CSV (used for TC-Relation)
#   per_event = its _per_event sibling (A / V / AVB / TC-Count)
#   label     = pretty name shown in tables/legends
CONDITIONS: dict[str, dict] = {
    "NoTools": {
        "label": "No Tools",
        "item":      "/home/coder/T2AV/eval_results/gemini/Test_ltx_notool/results.csv",
        "per_event": "/home/coder/T2AV/eval_results/gemini/Test_ltx_notool/results_per_event.csv",
    },
    "Mediapipe": {
        "label": "Mediapipe",
        "item":      "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results.csv",
        "per_event": "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results_per_event.csv",
    },
    "Mediapipe_Input": {
        "label": "Use Mediapipe overlay video as an input",
        # <-- the new (b) run. Point these at wherever you saved it.
        "item":      "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results_use_mediapipe_as_inputvideo/results.csv", 
        "per_event": "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results_use_mediapipe_as_inputvideo/results_per_event.csv", 
    },
}

# Human GT workbook(s). MOVA only for this run.
HUMAN_GT_XLSX: list[str] = [
    "/home/coder/T2AV/eval_results/human/Test_ltx_converted.csv",
]
HUMAN_SHEET = "Annotation"

OUT_DIR = Path("./analysis_results")

# Display order.
CONDITION_ORDER = ["NoTools", "Mediapipe", "Mediapipe_Input"]
# CONDITION_ORDER = ["original", "less_guide"]
AXIS_ORDER = ["A", "V", "AVB", "TC-Relation", "TC-Count"]
KIND_ORDER = ["speech", "silent_action", "sounding_action"]

# Which event kinds the ICL example *demonstrates* (for the legend / context).
# Used only for an informational note, not for any computation.
CONDITION_DEMOED_KINDS = {
    "no_icl": set(),
    "original": {"speech", "silent_action", "sounding_action"},
    "less_guide": {"speech", "silent_action"},
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


def norm_label(v):
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


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray):
    """Mean of per-class recalls over the classes present in y_true.

    Returns (bacc, n_classes_present). When only one class is present, bacc is
    that class's recall and n_classes_present == 1 (a flag for the caller).
    """
    recalls = []
    for c in ("yes", "no"):
        mask = y_true == c
        if int(mask.sum()) == 0:
            continue
        recalls.append(float((y_pred[mask] == c).mean()))
    if not recalls:
        return float("nan"), 0
    return float(np.mean(recalls)), len(recalls)


def parse_row_id(rid: str):
    """<item_id>__<variant><event_or_relation>__<axis_suffix> -> (item, ev, suffix)."""
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
        # h = pd.read_excel(p, sheet_name=HUMAN_SHEET)
        if str(p).endswith(".csv"):
            h = pd.read_csv(p)
        elif str(p).endswith(".xlsx"):
            h = pd.read_excel(p, sheet_name=HUMAN_SHEET)
        else:
            raise ValueError(f"Unsupported file type: {p}")
        if "row_id" not in h.columns or "human_label" not in h.columns:
            print(f"[WARN] {p} missing row_id/human_label; columns={list(h.columns)}")
            continue
        parsed = h["row_id"].apply(parse_row_id)
        h = h.assign(
            item_id=[z[0] for z in parsed],
            ev=[z[1] for z in parsed],
            axis_suffix=[z[2] for z in parsed],
        )
        h["key"] = (h["item_id"].astype(str) + "|" + h["ev"].astype(str)
                    + "|" + h["axis_suffix"].astype(str))
        h["human"] = h["human_label"].map(norm_label)
        frames.append(h[["key", "axis_suffix", "human"]])
    if not frames:
        sys.exit("[FATAL] no usable human GT workbook found. Fix HUMAN_GT_XLSX.")
    out = pd.concat(frames, ignore_index=True).dropna(subset=["human"])
    out = out.drop_duplicates(subset=["key"], keep="first")
    return out


def load_gemini(item_csv: str | None, per_event_csv: str | None) -> pd.DataFrame:
    """Return long Gemini predictions: columns [key, axis_suffix, kind, pred]."""
    rows = []

    # A / V / AVB / TC-Count from the per-event file (carries event_kind).
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
            rows.append((key, suffix, str(r.get("event_kind")), pred))
    elif per_event_csv:
        print(f"[WARN] per_event CSV not found: {per_event_csv}")

    # TC-Relation from the main item file (one row per video; no single kind).
    if item_csv and Path(item_csv).exists():
        it = pd.read_csv(item_csv)
        if "temporal_relation_satisfaction" in it.columns:
            for _, r in it.iterrows():
                key = f'{r.get("item_id")}|relation|TC-Relation'
                rows.append((key, "TC-Relation", "relation",
                             norm_label(r.get("temporal_relation_satisfaction"))))
        else:
            print(f"[WARN] {item_csv} has no temporal_relation_satisfaction column.")
    elif item_csv:
        print(f"[WARN] item CSV not found: {item_csv}")

    g = pd.DataFrame(rows, columns=["key", "axis_suffix", "kind", "pred"])
    g = g.dropna(subset=["pred"]).drop_duplicates(subset=["key"], keep="first")
    return g


def merged_predictions(cond_cfg: dict, human: pd.DataFrame) -> pd.DataFrame:
    g = load_gemini(cond_cfg.get("item"), cond_cfg.get("per_event"))
    if g.empty:
        return g
    return g.merge(human[["key", "human"]], on="key", how="inner")

# ===========================================================================
# Analyses
# ===========================================================================

def per_axis_table(conds: list[str], human: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for cond in conds:
        merged = merged_predictions(CONDITIONS[cond], human)
        if merged.empty:
            print(f"[WARN] condition '{cond}': no predictions; skipping.")
            continue
        for axis in AXIS_ORDER:
            sub = merged[merged.axis_suffix == axis]
            if sub.empty:
                recs.append(dict(condition=cond, axis=axis, balanced_accuracy=np.nan,
                                 n=0, n_yes_gt=0, n_no_gt=0, one_class=False))
                continue
            yt, yp = sub.human.to_numpy(), sub.pred.to_numpy()
            bacc, ncls = balanced_accuracy(yt, yp)
            recs.append(dict(
                condition=cond, axis=axis, balanced_accuracy=bacc, n=int(len(sub)),
                n_yes_gt=int((yt == "yes").sum()), n_no_gt=int((yt == "no").sum()),
                one_class=(ncls == 1),
            ))
    return pd.DataFrame.from_records(recs)


def per_kind_table(conds: list[str], human: pd.DataFrame) -> pd.DataFrame:
    """Per-event-kind, pooled over the per-event axes (A/V/AVB/TC-Count).

    TC-Relation is excluded (it is whole-video, not tied to one event kind).
    """
    recs = []
    for cond in conds:
        merged = merged_predictions(CONDITIONS[cond], human)
        if merged.empty:
            continue
        mk = merged[merged.axis_suffix != "TC-Relation"]
        for kind in KIND_ORDER:
            sub = mk[mk.kind == kind]
            if sub.empty:
                recs.append(dict(condition=cond, kind=kind, balanced_accuracy=np.nan,
                                 n=0, n_yes_gt=0, n_no_gt=0, one_class=False))
                continue
            yt, yp = sub.human.to_numpy(), sub.pred.to_numpy()
            bacc, ncls = balanced_accuracy(yt, yp)
            recs.append(dict(
                condition=cond, kind=kind, balanced_accuracy=bacc, n=int(len(sub)),
                n_yes_gt=int((yt == "yes").sum()), n_no_gt=int((yt == "no").sum()),
                one_class=(ncls == 1),
            ))
    return pd.DataFrame.from_records(recs)


def kind_axis_table(conds: list[str], human: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for cond in conds:
        merged = merged_predictions(CONDITIONS[cond], human)
        if merged.empty:
            continue
        mk = merged[merged.axis_suffix != "TC-Relation"]
        for kind in KIND_ORDER:
            for axis in ["A", "V", "AVB", "TC-Count"]:
                sub = mk[(mk.kind == kind) & (mk.axis_suffix == axis)]
                if sub.empty:
                    continue
                yt, yp = sub.human.to_numpy(), sub.pred.to_numpy()
                bacc, ncls = balanced_accuracy(yt, yp)
                recs.append(dict(condition=cond, kind=kind, axis=axis,
                                 balanced_accuracy=bacc, n=int(len(sub)),
                                 one_class=(ncls == 1)))
    return pd.DataFrame.from_records(recs)

# ===========================================================================
# Printing + plotting
# ===========================================================================

def _print_wide(res: pd.DataFrame, col: str, col_order: list[str], title: str) -> None:
    conds = [c for c in CONDITION_ORDER if c in set(res.condition)]
    wide = res.pivot(index="condition", columns=col, values="balanced_accuracy")
    nwide = res.pivot(index="condition", columns=col, values="n")
    cols = [c for c in col_order if c in wide.columns]
    wide = wide.reindex(index=conds, columns=cols)
    nwide = nwide.reindex(index=conds, columns=cols)
    print(f"\n=== {title} (rows: ICL condition, cols: {col}) ===")
    print("    (! = GT has only one class in that cell -> BAcc is single-class recall)\n")
    print("condition       " + "  ".join(f"{c:>14}" for c in cols))
    flag = res.set_index(["condition", col])["one_class"].to_dict()
    for cond in conds:
        cells = []
        for c in cols:
            v = wide.loc[cond, c]
            mark = "!" if flag.get((cond, c), False) else " "
            cells.append((f"{v:.3f}{mark}" if pd.notna(v) else "  -  ").rjust(14))
        print(f"{cond:<15} " + "  ".join(cells))
    print("\n--- n per cell ---")
    print(nwide.to_string())


def plot_grouped(res: pd.DataFrame, col: str, col_order: list[str],
                 title: str, out_png: Path) -> None:
    conds = [c for c in CONDITION_ORDER if c in set(res.condition)]
    groups = [g for g in col_order if g in set(res[col])]
    lut = {(r.condition, getattr(r, col)): r.balanced_accuracy for r in res.itertuples()}
    flag = {(r.condition, getattr(r, col)): r.one_class for r in res.itertuples()}

    x = np.arange(len(groups))
    nb = max(len(conds), 1)
    width = min(0.8 / nb, 0.26)
    cmap = plt.get_cmap("tab10")

    fig, ax = plt.subplots(figsize=(max(7, len(groups) * 1.9), 5.0))
    for i, cond in enumerate(conds):
        offs = x + (i - (nb - 1) / 2) * width
        vals = [lut.get((cond, g), np.nan) for g in groups]
        ax.bar(offs, [0 if pd.isna(v) else v for v in vals], width=width,
               label=CONDITIONS[cond]["label"], color=cmap(i % 10),
               edgecolor="white", linewidth=0.5)
        for off, v, g in zip(offs, vals, groups):
            if pd.isna(v):
                continue
            txt = f"{v:.2f}" + ("!" if flag.get((cond, g)) else "")
            ax.text(off, v + 0.012, txt, ha="center", va="bottom", fontsize=7, rotation=90)

    ax.axhline(0.5, color="grey", ls="--", lw=1, zorder=0)
    ax.text(len(groups) - 0.5, 0.505, "chance (0.5)", ha="right", va="bottom",
            fontsize=8, color="grey")
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Balanced accuracy (vs human GT)")
    ax.set_ylim(0, 1.12)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_title(title)
    ax.legend(title="condition", ncol=min(len(conds), 3),
              loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] wrote {out_png}")

# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    human = load_human(HUMAN_GT_XLSX)
    print(f"[INFO] human GT rows: {len(human)} "
          f"(yes={int((human.human=='yes').sum())}, no={int((human.human=='no').sum())})")

    conds = [c for c in CONDITION_ORDER if c in CONDITIONS]

    ax_res = per_axis_table(conds, human)
    kd_res = per_kind_table(conds, human)
    ka_res = kind_axis_table(conds, human)
    if ax_res.empty:
        sys.exit("[FATAL] no results. Check condition files exist and keys match the GT.")

    ax_res.to_csv(OUT_DIR / "per_axis_balanced_accuracy.csv", index=False)
    kd_res.to_csv(OUT_DIR / "per_event_kind_balanced_accuracy.csv", index=False)
    ka_res.to_csv(OUT_DIR / "event_kind_by_axis_balanced_accuracy.csv", index=False)

    _print_wide(ax_res, "axis", AXIS_ORDER, "PER-AXIS balanced accuracy")
    _print_wide(kd_res, "kind", KIND_ORDER, "PER-EVENT-KIND balanced accuracy (A/V/AVB/TC-Count pooled)")

    print("\n=== EVENT-KIND x AXIS balanced accuracy ===")
    if not ka_res.empty:
        piv = ka_res.pivot_table(index=["condition", "kind"], columns="axis",
                                 values="balanced_accuracy")
        print(piv.to_string())

    plot_grouped(ax_res, "axis", AXIS_ORDER,
                 "Per-axis balanced accuracy",
                 OUT_DIR / "per_axis_balanced_accuracy.png")
    plot_grouped(kd_res, "kind", KIND_ORDER,
                 "Per-event-kind balanced accuracy\n"
                 "(pooled over A / V / AVB / TC-Count)",
                 OUT_DIR / "per_event_kind_balanced_accuracy.png")

    print(f"\n[OK] all outputs in {OUT_DIR}")


if __name__ == "__main__":
    main()
