#!/usr/bin/env python3
import numpy as np
import pandas as pd
from pathlib import Path


# =========================
# Paths
# =========================
HUMAN_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/human_FIVE_axis_labels.csv"
    # "/home/coder/T2V_Gen/Gemini/human_eval_GT/human_labeling_newprompt_absolute.csv"
)

GEMINI_PATH = Path(
    # "/home/coder/T2V_Gen/Gemini/eval_outputs_without-Tool/new-axis_temporal_eval.csv"
    "/home/coder/T2V_Gen/Gemini/eval_output_tool_focused_raw/results_Gemini24fps-mediapipe-refine_absolute.csv"
)

OUT_PATH = Path(
    # "/home/coder/T2V_Gen/Gemini/human_eval_GT/compare_results_without-Tool/tc_detailed_analysis.csv"
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/compare_results_focused_raw/tc_detailed_analysis_24FPS-mediapipe-refine_absolute.csv"
)


# =========================
# Utils
# =========================
def to_binary(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s in {"1", "y", "yes", "true"}:
        return 1
    if s in {"0", "n", "no", "false"}:
        return 0
    return np.nan


def safe_div(a, b):
    return a / b if b else np.nan


def binary_metrics(pred, gt):
    valid = pd.DataFrame({"pred": pred, "gt": gt}).dropna()
    if len(valid) == 0:
        return {
            "n": 0, "human_pos": 0, "human_neg": 0,
            "pred_pos": 0, "pred_neg": 0,
            "tn": 0, "fp": 0, "fn": 0, "tp": 0,
            "accuracy": np.nan, "balanced_accuracy": np.nan,
            "precision": np.nan, "pos_recall": np.nan,
            "neg_recall": np.nan, "f1": np.nan,
            "always_no_acc": np.nan, "always_yes_acc": np.nan,
            "majority_baseline_acc": np.nan,
            "gain_over_majority": np.nan,
        }

    pred = valid["pred"].astype(int)
    gt = valid["gt"].astype(int)

    tp = int(((pred == 1) & (gt == 1)).sum())
    tn = int(((pred == 0) & (gt == 0)).sum())
    fp = int(((pred == 1) & (gt == 0)).sum())
    fn = int(((pred == 0) & (gt == 1)).sum())

    n = len(valid)
    human_pos = int((gt == 1).sum())
    human_neg = int((gt == 0).sum())
    pred_pos = int((pred == 1).sum())
    pred_neg = int((pred == 0).sum())

    acc = safe_div(tp + tn, n)
    pos_recall = safe_div(tp, tp + fn)
    neg_recall = safe_div(tn, tn + fp)
    balanced_acc = np.nanmean([pos_recall, neg_recall])

    precision = safe_div(tp, tp + fp)
    f1 = (
        2 * precision * pos_recall / (precision + pos_recall)
        if not np.isnan(precision)
        and not np.isnan(pos_recall)
        and (precision + pos_recall) > 0
        else np.nan
    )

    always_no_acc = safe_div(human_neg, n)
    always_yes_acc = safe_div(human_pos, n)
    majority_baseline_acc = max(always_no_acc, always_yes_acc)
    gain_over_majority = acc - majority_baseline_acc

    return {
        "n": n,
        "human_pos": human_pos,
        "human_neg": human_neg,
        "pred_pos": pred_pos,
        "pred_neg": pred_neg,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "accuracy": acc,
        "balanced_accuracy": balanced_acc,
        "precision": precision,
        "pos_recall": pos_recall,
        "neg_recall": neg_recall,
        "f1": f1,
        "always_no_acc": always_no_acc,
        "always_yes_acc": always_yes_acc,
        "majority_baseline_acc": majority_baseline_acc,
        "gain_over_majority": gain_over_majority,
    }


def print_metrics(title, m):
    print(f"\n========== {title} ==========")
    print(f"n={m['n']}")
    print(f"Human TC positive={m['human_pos']}, negative={m['human_neg']}")
    print(f"Gemini TC positive={m['pred_pos']}, negative={m['pred_neg']}")
    print(
        f"Confusion matrix [[TN, FP], [FN, TP]] = "
        f"[[{m['tn']}, {m['fp']}], [{m['fn']}, {m['tp']}]]"
    )
    print(f"Accuracy={m['accuracy']:.3f}")
    print(f"BalancedAcc={m['balanced_accuracy']:.3f}")
    print(f"Precision={m['precision']:.3f}")
    print(f"PosRecall={m['pos_recall']:.3f}")
    print(f"NegRecall={m['neg_recall']:.3f}")
    print(f"F1={m['f1']:.3f}")
    print(f"Always-No baseline Acc={m['always_no_acc']:.3f}")
    print(f"Always-Yes baseline Acc={m['always_yes_acc']:.3f}")
    print(f"Majority baseline Acc={m['majority_baseline_acc']:.3f}")
    print(f"Gain over majority baseline={m['gain_over_majority']:.3f}")


def add_interpretation(m):
    notes = []

    if m["n"] == 0:
        return "No valid samples."

    neg_rate = safe_div(m["human_neg"], m["n"])
    pos_rate = safe_div(m["human_pos"], m["n"])

    if neg_rate >= 0.65:
        notes.append(
            f"Human labels are negative-heavy: {m['human_neg']}/{m['n']} negatives ({neg_rate:.1%})."
        )
    elif pos_rate >= 0.65:
        notes.append(
            f"Human labels are positive-heavy: {m['human_pos']}/{m['n']} positives ({pos_rate:.1%})."
        )
    else:
        notes.append("Human TC labels are not extremely imbalanced.")

    if abs(m["accuracy"] - m["always_no_acc"]) < 0.05:
        notes.append(
            "Accuracy is close to the always-No baseline; high accuracy may be partly due to class imbalance."
        )
    elif m["accuracy"] > m["always_no_acc"] + 0.10:
        notes.append(
            "Accuracy is clearly above the always-No baseline, so Gemini is not merely saying No."
        )

    if m["pred_neg"] / m["n"] >= 0.80:
        notes.append(
            f"Gemini predicts No very often: {m['pred_neg']}/{m['n']} ({m['pred_neg']/m['n']:.1%})."
        )
    elif m["pred_pos"] / m["n"] >= 0.80:
        notes.append(
            f"Gemini predicts Yes very often: {m['pred_pos']}/{m['n']} ({m['pred_pos']/m['n']:.1%})."
        )
    else:
        notes.append("Gemini predictions are not dominated by a single class.")

    if not np.isnan(m["balanced_accuracy"]):
        if m["balanced_accuracy"] >= 0.75:
            notes.append(
                "Balanced accuracy is relatively high, suggesting performance is not explained only by imbalance."
            )
        elif m["balanced_accuracy"] < 0.60:
            notes.append(
                "Balanced accuracy is low, suggesting weak class-balanced TC performance."
            )

    if m["fp"] > m["fn"] * 2:
        notes.append(
            "Main error pattern: Gemini over-accepts TC failures as correct (many false positives)."
        )
    elif m["fn"] > m["fp"] * 2:
        notes.append(
            "Main error pattern: Gemini is overly strict and rejects many correct TC cases (many false negatives)."
        )
    else:
        notes.append("FP and FN are relatively balanced.")

    return " ".join(notes)


# =========================
# Load
# =========================
human = pd.read_csv(HUMAN_PATH)
gemini = pd.read_csv(GEMINI_PATH)

print(f"[INFO] Human rows: {len(human)}")
print(f"[INFO] Gemini rows: {len(gemini)}")


# =========================
# Validate
# =========================
required_human_cols = [
    "video_id", "item_id", "variant", "TC",
]

required_gemini_cols = [
    "item_id",
    "variant_index",
    "modality_combination",
    "temporal_type",
    "temporal_constraint_satisfaction",
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

human["variant_idx"] = (
    human["variant"]
    .astype(str)
    .str.extract(r"(\d+)")[0]
    .astype("Int64")
)

gemini["variant_idx"] = pd.to_numeric(
    gemini["variant_index"],
    errors="coerce",
).astype("Int64")


# =========================
# Labels
# =========================
human["human_TC"] = human["TC"].map(to_binary)
gemini["gemini_TC"] = gemini["temporal_constraint_satisfaction"].map(to_binary)


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
    raise RuntimeError("Merged dataframe is empty. Check item_id + variant matching.")


# =========================
# Overall TC metrics
# =========================
overall = binary_metrics(df["gemini_TC"], df["human_TC"])
print_metrics("TC overall", overall)
print("\nInterpretation:")
print(add_interpretation(overall))


# =========================
# Breakdown 1: temporal type
# =========================
summary_rows = []

def analyze_group(group_name, group_value, sub):
    m = binary_metrics(sub["gemini_TC"], sub["human_TC"])
    row = {
        "group": group_name,
        "value": group_value,
        **m,
        "interpretation": add_interpretation(m),
    }
    summary_rows.append(row)

    print_metrics(f"TC by {group_name}: {group_value}", m)
    print("Interpretation:")
    print(row["interpretation"])


for temporal_type, sub in df.groupby("temporal_type", dropna=False):
    analyze_group("temporal_type", temporal_type, sub)


# =========================
# Breakdown 2: modality combination
# =========================
for modality, sub in df.groupby("modality_combination", dropna=False):
    analyze_group("modality_combination", modality, sub)


# =========================
# Breakdown 3: temporal type × modality
# =========================
for (temporal_type, modality), sub in df.groupby(
    ["temporal_type", "modality_combination"],
    dropna=False,
):
    analyze_group("temporal_type_x_modality", f"{temporal_type} | {modality}", sub)


# =========================
# Error cases
# =========================
df["tc_error_type"] = np.select(
    [
        (df["human_TC"] == 0) & (df["gemini_TC"] == 1),
        (df["human_TC"] == 1) & (df["gemini_TC"] == 0),
        (df["human_TC"] == 1) & (df["gemini_TC"] == 1),
        (df["human_TC"] == 0) & (df["gemini_TC"] == 0),
    ],
    ["FP", "FN", "TP", "TN"],
    default="NA",
)

print("\n========== TC error case counts ==========")
print(df["tc_error_type"].value_counts().to_string())

print("\n========== TC false positives: Gemini TC=yes, Human TC=no ==========")
fp_cols = [
    "video_id",
    "item_id",
    "variant",
    "temporal_type",
    "modality_combination",
    "TC",
    "temporal_constraint_satisfaction",
    "temporal_constraint_satisfaction_reason",
    "temporal_constraint_satisfaction_evidence",
]
fp_cols = [c for c in fp_cols if c in df.columns]
print(df[df["tc_error_type"] == "FP"][fp_cols].to_string(index=False))

print("\n========== TC false negatives: Gemini TC=no, Human TC=yes ==========")
fn_cols = fp_cols
print(df[df["tc_error_type"] == "FN"][fn_cols].to_string(index=False))


# =========================
# Save one summary CSV
# =========================
summary = pd.DataFrame(summary_rows)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUT_PATH, index=False)

print(f"\n[SAVED] TC detailed summary: {OUT_PATH}")