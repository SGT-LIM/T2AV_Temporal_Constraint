#!/usr/bin/env python3
import argparse
import numpy as np
import pandas as pd
from pathlib import Path


# =========================
# Default paths / CLI args
# =========================
DEFAULT_HUMAN_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/human_FIVE_axis_labels.csv"
)

DEFAULT_GEMINI_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/eval_outputs_without-Tool/new-axis_temporal_eval.csv"
)

DEFAULT_OUT_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/compare_results_without-Tool/compare_human_FIVE_axis_vs_gemini.csv"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare human 5-axis labels against one Gemini evaluation CSV."
    )
    parser.add_argument(
        "--human-path",
        type=Path,
        default=DEFAULT_HUMAN_PATH,
        help="Path to human GT CSV. Default: %(default)s",
    )
    parser.add_argument(
        "--gemini-path",
        type=Path,
        default=DEFAULT_GEMINI_PATH,
        help="Path to Gemini/raw/focused_raw evaluation CSV. Default: %(default)s",
    )
    parser.add_argument(
        "--out-path",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help="Path to save row-level comparison CSV. Summary is saved next to it. Default: %(default)s",
    )
    return parser.parse_args()


args = parse_args()
HUMAN_PATH = args.human_path
GEMINI_PATH = args.gemini_path
OUT_PATH = args.out_path


# =========================
# Utilities
# =========================
def binary_to_int(x):
    if pd.isna(x):
        return np.nan

    s = str(x).strip().lower()

    if s in {"1", "y", "yes", "true"}:
        return 1
    if s in {"0", "n", "no", "false"}:
        return 0

    return np.nan


def yesno_to_int(x):
    if pd.isna(x):
        return np.nan

    s = str(x).strip().lower()

    if s in {"yes", "y", "1", "true"}:
        return 1
    if s in {"no", "n", "0", "false"}:
        return 0

    return np.nan


def compute_binary_metrics(pred, gt):
    valid = pd.DataFrame({"pred": pred, "gt": gt}).dropna()

    if len(valid) == 0:
        return {
            "n": 0,
            "match": 0,
            "agreement": np.nan,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
            "accuracy": np.nan,
            "precision": np.nan,
            "positive_recall": np.nan,
            "negative_recall": np.nan,
            "balanced_accuracy": np.nan,
            "f1": np.nan,
        }

    pred = valid["pred"].astype(int)
    gt = valid["gt"].astype(int)

    tp = int(((pred == 1) & (gt == 1)).sum())
    tn = int(((pred == 0) & (gt == 0)).sum())
    fp = int(((pred == 1) & (gt == 0)).sum())
    fn = int(((pred == 0) & (gt == 1)).sum())

    n = len(valid)
    match = int((pred == gt).sum())
    agreement = match / n

    accuracy = agreement
    precision = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    positive_recall = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    negative_recall = tn / (tn + fp) if (tn + fp) > 0 else np.nan
    balanced_accuracy = np.nanmean([positive_recall, negative_recall])

    if (
        not np.isnan(precision)
        and not np.isnan(positive_recall)
        and (precision + positive_recall) > 0
    ):
        f1 = 2 * precision * positive_recall / (precision + positive_recall)
    else:
        f1 = np.nan

    return {
        "n": n,
        "match": match,
        "agreement": agreement,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "accuracy": accuracy,
        "precision": precision,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": balanced_accuracy,
        "f1": f1,
    }


def print_axis_result(axis_name, metrics):
    print(f"\n========== {axis_name} ==========")
    print(f"Agreement: {metrics['match']}/{metrics['n']} = {metrics['agreement']:.3f}")
    print(
        f"Confusion matrix [[TN, FP], [FN, TP]] = "
        f"[[{metrics['tn']}, {metrics['fp']}], [{metrics['fn']}, {metrics['tp']}]]"
    )
    print(f"Accuracy={metrics['accuracy']:.3f}")
    print(f"BalancedAcc={metrics['balanced_accuracy']:.3f}")
    print(f"Precision={metrics['precision']:.3f}")
    print(f"PosRecall={metrics['positive_recall']:.3f}")
    print(f"NegRecall={metrics['negative_recall']:.3f}")
    print(f"F1={metrics['f1']:.3f}")


# =========================
# Load
# =========================
human = pd.read_csv(HUMAN_PATH)
gemini = pd.read_csv(GEMINI_PATH)

print(f"[INFO] Human rows: {len(human)}")
print(f"[INFO] Gemini rows: {len(gemini)}")


# =========================
# Validate columns
# =========================
required_human_cols = [
    "video_id",
    "item_id",
    "variant",
    "A",
    "V",
    "AVB",
    "TC",
    # "CC",
    # "Overall",
]

required_gemini_cols = [
    "item_id",
    "variant_index",
    "audio_event_correctness",
    "visual_event_correctness",
    "audio_visual_binding",
    "temporal_constraint_satisfaction",
    "constraint_compliance",
    "overall_temporal_success",
]

for col in required_human_cols:
    if col not in human.columns:
        raise ValueError(f"Human CSV missing column: {col}. Columns: {human.columns.tolist()}")

for col in required_gemini_cols:
    if col not in gemini.columns:
        raise ValueError(f"Gemini CSV missing column: {col}. Columns: {gemini.columns.tolist()}")


# =========================
# Normalize keys
# =========================
human = human.copy()
gemini = gemini.copy()

human["item_id"] = human["item_id"].astype(str).str.strip()
gemini["item_id"] = gemini["item_id"].astype(str).str.strip()

# human variant is like v1/v2/v3
human["variant_idx"] = (
    human["variant"]
    .astype(str)
    .str.extract(r"(\d+)")[0]
    .astype("Int64")
)

gemini["variant_idx"] = pd.to_numeric(
    gemini["variant_index"], errors="coerce"
).astype("Int64")


# =========================
# Convert human labels
# =========================
human_axis_map = {
    "A": "human_A",
    "V": "human_V",
    "AVB": "human_AVB",
    "TC": "human_TC",
    # "CC": "human_CC",
    # "Overall": "human_Overall",
}

for src, dst in human_axis_map.items():
    human[dst] = human[src].map(binary_to_int)

# Optional: recompute human temporal-only overall from A,V,AVB,TC
# human["human_Overall_recomputed_no_CC"] = np.where(
#     human[["human_A", "human_V", "human_AVB", "human_TC"]].eq(1).all(axis=1),
#     1,
#     0,
# )

# Optional: recompute human strict overall with CC
# human["human_Overall_recomputed_with_CC"] = np.where(
#     human[["human_A", "human_V", "human_AVB", "human_TC", "human_CC"]].eq(1).all(axis=1),
#     1,
#     0,
# )


# =========================
# Convert Gemini labels
# =========================
gemini_axis_map = {
    "audio_event_correctness": "gemini_A",
    "visual_event_correctness": "gemini_V",
    "audio_visual_binding": "gemini_AVB",
    "temporal_constraint_satisfaction": "gemini_TC",
    # "constraint_compliance": "gemini_CC",
    # "overall_temporal_success": "gemini_Overall_original",
}

for src, dst in gemini_axis_map.items():
    gemini[dst] = gemini[src].map(yesno_to_int)

# # Recompute Gemini temporal-only overall from A,V,AVB,TC
# gemini["gemini_Overall_recomputed_no_CC"] = np.where(
#     gemini[["gemini_A", "gemini_V", "gemini_AVB", "gemini_TC"]].eq(1).all(axis=1),
#     1,
#     0,
# )

# # Recompute Gemini strict overall with CC
# gemini["gemini_Overall_recomputed_with_CC"] = np.where(
#     gemini[["gemini_A", "gemini_V", "gemini_AVB", "gemini_TC", "gemini_CC"]].eq(1).all(axis=1),
#     1,
#     0,
# )


# =========================
# Merge
# =========================
df = human.merge(
    gemini,
    on=["item_id", "variant_idx"],
    how="inner",
    suffixes=("_human", "_gemini"),
)

print(f"[INFO] Merged rows: {len(df)}")

if len(df) == 0:
    raise RuntimeError("Merged dataframe is empty. Check item_id and variant matching.")

if len(df) < len(human):
    missing = human.merge(
        gemini[["item_id", "variant_idx"]],
        on=["item_id", "variant_idx"],
        how="left",
        indicator=True,
    )
    missing = missing[missing["_merge"] == "left_only"]
    print(f"[WARN] Human rows missing in Gemini result: {len(missing)}")
    print(missing[["video_id", "item_id", "variant"]].head(20).to_string(index=False))


# =========================
# Compare axes
# =========================
comparisons = [
    ("A", "human_A", "gemini_A"),
    ("V", "human_V", "gemini_V"),
    ("AVB", "human_AVB", "gemini_AVB"),
    ("TC", "human_TC", "gemini_TC"),
    # ("CC", "human_CC", "gemini_CC"),

#     # Your manually labeled Overall column
#     ("Overall_manual", "human_Overall", "gemini_Overall_recomputed_no_CC"),

#     # Temporal-only overall, recomputed from A,V,AVB,TC
#     ("Overall_recomputed_no_CC", "human_Overall_recomputed_no_CC", "gemini_Overall_recomputed_no_CC"),

#     # Strict prompt-level overall, recomputed from A,V,AVB,TC,CC
#     ("Overall_recomputed_with_CC", "human_Overall_recomputed_with_CC", "gemini_Overall_recomputed_with_CC"),
]

summary_rows = []

for axis_name, human_col, gemini_col in comparisons:
    metrics = compute_binary_metrics(
        pred=df[gemini_col],
        gt=df[human_col],
    )

    print_axis_result(axis_name, metrics)

    summary_rows.append({
        "axis": axis_name,
        "human_col": human_col,
        "gemini_col": gemini_col,
        **metrics,
    })


summary = pd.DataFrame(summary_rows)


# =========================
# Save one output CSV
# =========================
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

keep_cols = [
    "video_id",
    "item_id",
    "variant",
    "variant_idx",

    "human_A",
    "gemini_A",
    "human_V",
    "gemini_V",
    "human_AVB",
    "gemini_AVB",
    "human_TC",
    "gemini_TC",
    # "human_CC",
    # "gemini_CC",

    # "human_Overall",
    # "gemini_Overall_recomputed_no_CC",
    # "human_Overall_recomputed_no_CC",
    # "human_Overall_recomputed_with_CC",
    # "gemini_Overall_recomputed_with_CC",

    "audio_event_correctness_reason",
    "visual_event_correctness_reason",
    "audio_visual_binding_reason",
    "temporal_constraint_satisfaction_reason",
    "constraint_compliance_reason",
    "overall_reason",
]

keep_cols = [c for c in keep_cols if c in df.columns]

# Save row-level comparison
df[keep_cols].to_csv(OUT_PATH, index=False)

# Save summary next to it
SUMMARY_PATH = OUT_PATH.with_name(OUT_PATH.stem + "_summary.csv")
summary.to_csv(SUMMARY_PATH, index=False)

print(f"\n[SAVED] row-level comparison: {OUT_PATH}")
print(f"[SAVED] summary: {SUMMARY_PATH}")

print("\n========== Summary ==========")
print(summary[[
    "axis", "n", "match", "agreement", "tn", "fp", "fn", "tp",
    "precision", "positive_recall", "negative_recall", "f1"
]].to_string(index=False))