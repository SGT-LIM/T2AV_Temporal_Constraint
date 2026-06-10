#!/usr/bin/env python3
"""
Analyze Gemini 5-axis T2AV evaluations against human GT across multiple tool options.

Main use case:
  - Human GT CSV is treated as ground truth.
  - Each Gemini CSV is one evaluation setting, e.g.
      mediapipe
      whisper
      clap
      whisper_clap
      mediapipe_whisper_clap
      no_tool   # optional, can be added later
  - The script computes 5-axis metrics, TC-focused breakdowns, pairwise method
    transitions, and qualitative disagreement examples.

Expected human GT columns:
  Required:
    item_id, variant
  Axis columns:
    A, V, AVB, TC, and optionally CC
  Optional:
    video_id, Failure reason, prompt

Expected Gemini result columns:
  Required:
    item_id, variant_index
    audio_event_correctness
    visual_event_correctness
    audio_visual_binding
    temporal_constraint_satisfaction
  Optional but recommended:
    constraint_compliance
    *_reason, *_evidence columns
    temporal_type, modality_combination
    video_relpath, video_file
    observed_behavior_summary, overall_reason, user_prompt, raw_output
    pose_evidence_mode, audio_evidence_mode, mediapipe_summary, audio_evidence_summary

Outputs:
  out_dir/
    method_axis_summary.csv
    method_ranking.csv
    row_level_long.csv
    row_level_wide_core.csv
    tc_breakdown_by_temporal_type.csv
    tc_breakdown_by_modality_combination.csv
    tc_breakdown_by_temporal_type_x_modality_combination.csv
    pairwise_method_transitions.csv
    tc_method_disagreement_cases.csv
    tc_all_methods_wrong_cases.csv
    qualitative_examples.csv
    qualitative_examples.md
    details/*.txt

Example:
python may26_analyze_gemini_tool_options_vs_human.py \
  --human-path /home/coder/T2AV/eval_results/human/YS_rel_v1_20.csv \
  --method no_tool=/home/coder/T2AV/eval_results/gemini/wo_tools.csv \
  --method mediapipe=/home/coder/T2AV/eval_results/gemini/mediapipe_focused_raw.csv \
  --method whisper=/home/coder/T2AV/eval_results/gemini/whisper.csv \
  --method clap=/home/coder/T2AV/eval_results/gemini/clap.csv \
  --method mediapipe_whisper=/home/coder/T2AV/eval_results/gemini/mediapipe_whisper.csv \
  --method mediapipe_clap=/home/coder/T2AV/eval_results/gemini/mediapipe_clap.csv \
  --method whisper_clap=/home/coder/T2AV/eval_results/gemini/whisper_clap.csv \
  --method all_tools=/home/coder/T2AV/eval_results/gemini/All_tools.csv \
  --out-dir /home/coder/T2AV/eval_results/analysis/new-results

When no-tool finishes, just add:
  --method no_tool=/path/to/no_tool_results.csv
"""

from __future__ import annotations

import argparse
import itertools
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


AXES = {
    "A": {
        "long_name": "audio_event_correctness",
        "human_col": "A_audio_event_correctness",
        "pred_col": "audio_event_correctness",
        "reason_col": "audio_event_correctness_reason",
        "evidence_col": "audio_event_correctness_evidence",
    },
    "V": {
        "long_name": "visual_event_correctness",
        "human_col": "V_visual_event_correctness",
        "pred_col": "visual_event_correctness",
        "reason_col": "visual_event_correctness_reason",
        "evidence_col": "visual_event_correctness_evidence",
    },
    "AVB": {
        "long_name": "audio_visual_binding",
        "human_col": "AVB_audio_visual_binding",
        "pred_col": "audio_visual_binding",
        "reason_col": "audio_visual_binding_reason",
        "evidence_col": "audio_visual_binding_evidence",
    },
    "TC_REL": {
        "long_name": "temporal_relation_satisfaction",
        "human_col": "temporal_relation_satisfaction",
        "pred_col": "temporal_relation_satisfaction",
        "reason_col": "temporal_relation_satisfaction_reason",
        "evidence_col": "temporal_relation_satisfaction_evidence",
    },
    "TC_COUNT": {
        "long_name": "temporal_count_satisfaction",
        "human_col": "temporal_count_satisfaction",
        "pred_col": "temporal_count_satisfaction",
        "reason_col": "temporal_count_satisfaction_reason",
        "evidence_col": "temporal_count_satisfaction_evidence",
    },
    "CC": {
        "long_name": "constraint_compliance",
        "human_col": "CC_constraint_compliance",
        "pred_col": "constraint_compliance",
        "reason_col": "constraint_compliance_reason",
        "evidence_col": "constraint_compliance_evidence",
    },
}

CORE_AXES_FOR_OVERALL = [
    "A",
    "V",
    "AVB",
    "TC_REL",
    "TC_COUNT",
]

META_COLS = [
    "video_id",
    "item_id",
    "variant",
    "variant_idx",
    "video_relpath",
    "video_file",
    "label_name",
    "label_type",
    "modality_combination",
    "event_summary",
    "temporal_type",
    "model",
    "media_fps",
    "thinking_level",
    "pose_evidence_mode",
    "mediapipe_hint_used",
    "mediapipe_fps",
    "mediapipe_error",
    "audio_evidence_mode",
    "audio_evidence_used",
    "audio_evidence_error",
]

LONG_TEXT_COLS = [
    "user_prompt",
    "raw_output",
    "observed_behavior_summary",
    "overall_reason",
    "mediapipe_summary",
    "audio_evidence_summary",
]

REASON_KEYWORDS = {
    "synchronization": ["sync", "simultaneous", "synchronized", "together", "overlap", "aligned", "alignment"],
    "absolute_timing": ["1.5", "3.5", "second", "timestamp", "timing", "too early", "too late", "around"],
    "order": ["order", "before", "after", "then", "reversed", "sequence", "sequential"],
    "count_repetition": ["count", "once", "twice", "repeat", "repeated", "extra occurrence", "again"],
    "missing_event": ["missing", "absent", "not present", "does not occur", "no visible", "not heard"],
    "extra_event": ["extra", "additional", "after the final", "background", "unwanted", "not required"],
    "unclear_ambiguous": ["unclear", "ambiguous", "weak", "not clear", "uncertain", "difficult"],
    "audio_issue": ["audio", "sound", "heard", "speech", "word", "whisper", "clap"],
    "visual_issue": ["visual", "visible", "hand", "mouth", "gesture", "contact", "pose", "mediapipe"],
    "laterality": ["left", "right", "side", "opposite", "laterality"],
}


# ---------------------------------------------------------------------
# CLI / basic utilities
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare human 5-axis labels against multiple Gemini evaluation CSVs "
            "and produce TC-focused tool-option analysis."
        )
    )
    parser.add_argument("--human-path", type=Path, default="/home/coder/T2V_Gen/results/human/human_labeling_new_refined_may26.csv")
    parser.add_argument(
        "--method",
        action="append",
        required=True,
        help=(
            "Method specification NAME=CSV_PATH. Repeat for each tool option. "
            "Example: --method mediapipe=/path/results.csv"
        ),
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--video-root", type=Path, default=None)
    parser.add_argument("--examples-per-type", type=int, default=3)
    parser.add_argument("--detail-max-chars", type=int, default=60000)
    parser.add_argument("--excerpt-chars", type=int, default=1200)
    parser.add_argument(
        "--min-group-n",
        type=int,
        default=1,
        help="Minimum n for TC breakdown groups to keep in summary CSVs.",
    )
    parser.add_argument(
        "--include-wide-text",
        action="store_true",
        help="Include long reason/evidence excerpts in row_level_wide_core.csv.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="If set, fail when optional CC is missing from either human or Gemini CSV.",
    )
    return parser.parse_args()


def parse_method_specs(specs: List[str]) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--method must be NAME=PATH, got: {spec!r}")
        name, path = spec.split("=", 1)
        name = safe_name(name.strip())
        if not name:
            raise ValueError(f"Empty method name in --method {spec!r}")
        if name in out:
            raise ValueError(f"Duplicate method name: {name}")
        out[name] = Path(path).expanduser()
    return out


def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(text).strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def safe_filename(text: str, max_len: int = 180) -> str:
    text = safe_name(text)
    return text[:max_len] or "example"


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def truncate_text(x, max_chars: int) -> str:
    text = clean_text(x)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [TRUNCATED to {max_chars} chars]"


def to_binary(x) -> float:
    """Convert yes/no/1/0 labels to 1.0/0.0/np.nan."""
    if pd.isna(x):
        return np.nan

    # handle numeric 1.0 / 0.0
    if isinstance(x, (int, float, np.integer, np.floating)):
        if float(x) == 1.0:
            return 1.0
        if float(x) == 0.0:
            return 0.0

    s = str(x).strip().lower()

    if s in {"1", "1.0", "y", "yes", "true", "t"}:
        return 1.0
    if s in {"0", "0.0", "n", "no", "false", "f"}:
        return 0.0
    return np.nan




def df_to_markdown(df: pd.DataFrame, index: bool = False) -> str:
    """Small dependency-free markdown table renderer.

    pandas.DataFrame.to_markdown requires the optional `tabulate` package, which
    may not be installed in the evaluation environment. This helper keeps the
    script self-contained.
    """
    if df is None or df.empty:
        return ""
    if index:
        df = df.reset_index()
    else:
        df = df.reset_index(drop=True)
    cols = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(str(c) for c in cols) + " |")
    rows.append("| " + " | ".join("---" for _ in cols) + " |")
    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                if math.isnan(v):
                    s = ""
                else:
                    s = f"{v:.4f}"
            else:
                s = "" if pd.isna(v) else str(v)
            s = s.replace("\n", " ").replace("|", "\\|")
            vals.append(s)
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def format_label(x) -> str:
    if pd.isna(x):
        return "NA"
    try:
        return "yes" if int(x) == 1 else "no"
    except Exception:
        return str(x)


def safe_div(a: float, b: float) -> float:
    return a / b if b else np.nan


def infer_variant_idx_from_human_variant(series: pd.Series) -> pd.Series:
    extracted = series.astype(str).str.extract(r"(\d+)")[0]
    return pd.to_numeric(extracted, errors="coerce").astype("Int64")


def infer_variant_idx_from_gemini(df: pd.DataFrame) -> pd.Series:
    if "variant_index" in df.columns:
        return pd.to_numeric(df["variant_index"], errors="coerce").astype("Int64")
    if "video_file" in df.columns:
        extracted = df["video_file"].astype(str).str.extract(r"_v(\d+)(?:_raw)?\.mp4")[0]
        return pd.to_numeric(extracted, errors="coerce").astype("Int64")
    if "video_relpath" in df.columns:
        extracted = df["video_relpath"].astype(str).str.extract(r"_v(\d+)(?:_raw)?\.mp4")[0]
        return pd.to_numeric(extracted, errors="coerce").astype("Int64")
    raise ValueError("Gemini CSV must contain variant_index, video_file, or video_relpath.")


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------
def binary_metrics(pred: pd.Series, gt: pd.Series) -> dict:
    valid = pd.DataFrame({"pred": pred, "gt": gt}).dropna()
    if len(valid) == 0:
        return {
            "n": 0,
            "match": 0,
            "accuracy": np.nan,
            "balanced_accuracy": np.nan,
            "precision": np.nan,
            "positive_recall": np.nan,
            "negative_recall": np.nan,
            "f1": np.nan,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
            "human_pos": 0,
            "human_neg": 0,
            "pred_pos": 0,
            "pred_neg": 0,
            "always_no_acc": np.nan,
            "always_yes_acc": np.nan,
            "majority_baseline_acc": np.nan,
            "gain_over_majority": np.nan,
        }

    pred_i = valid["pred"].astype(int)
    gt_i = valid["gt"].astype(int)

    tp = int(((pred_i == 1) & (gt_i == 1)).sum())
    tn = int(((pred_i == 0) & (gt_i == 0)).sum())
    fp = int(((pred_i == 1) & (gt_i == 0)).sum())
    fn = int(((pred_i == 0) & (gt_i == 1)).sum())

    n = len(valid)
    match = int((pred_i == gt_i).sum())
    accuracy = safe_div(match, n)

    human_pos = int((gt_i == 1).sum())
    human_neg = int((gt_i == 0).sum())
    pred_pos = int((pred_i == 1).sum())
    pred_neg = int((pred_i == 0).sum())

    precision = safe_div(tp, tp + fp)
    positive_recall = safe_div(tp, tp + fn)
    negative_recall = safe_div(tn, tn + fp)
    balanced_accuracy = np.nanmean([positive_recall, negative_recall])
    if (
        not pd.isna(precision)
        and not pd.isna(positive_recall)
        and (precision + positive_recall) > 0
    ):
        f1 = 2 * precision * positive_recall / (precision + positive_recall)
    else:
        f1 = np.nan

    always_no_acc = safe_div(human_neg, n)
    always_yes_acc = safe_div(human_pos, n)
    majority_baseline_acc = np.nanmax([always_no_acc, always_yes_acc])
    gain_over_majority = accuracy - majority_baseline_acc

    return {
        "n": n,
        "match": match,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "f1": f1,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
        "human_pos": human_pos,
        "human_neg": human_neg,
        "pred_pos": pred_pos,
        "pred_neg": pred_neg,
        "always_no_acc": always_no_acc,
        "always_yes_acc": always_yes_acc,
        "majority_baseline_acc": majority_baseline_acc,
        "gain_over_majority": gain_over_majority,
    }


def error_type(human: float, pred: float) -> str:
    if pd.isna(human) or pd.isna(pred):
        return "NA"
    h = int(human)
    p = int(pred)
    if h == 1 and p == 1:
        return "TP"
    if h == 0 and p == 0:
        return "TN"
    if h == 0 and p == 1:
        return "FP"
    if h == 1 and p == 0:
        return "FN"
    return "NA"


def metrics_interpretation(m: dict) -> str:
    if m["n"] == 0:
        return "No valid samples."

    notes = []
    neg_rate = safe_div(m["human_neg"], m["n"])
    pos_rate = safe_div(m["human_pos"], m["n"])

    if neg_rate >= 0.65:
        notes.append(f"Human labels are negative-heavy ({m['human_neg']}/{m['n']} = {neg_rate:.1%}).")
    elif pos_rate >= 0.65:
        notes.append(f"Human labels are positive-heavy ({m['human_pos']}/{m['n']} = {pos_rate:.1%}).")
    else:
        notes.append("Human labels are not extremely imbalanced.")

    if not pd.isna(m["accuracy"]) and not pd.isna(m["majority_baseline_acc"]):
        if m["gain_over_majority"] <= 0.02:
            notes.append("Accuracy is close to the majority baseline; inspect balanced accuracy and FP/FN.")
        elif m["gain_over_majority"] >= 0.10:
            notes.append("Accuracy is clearly above the majority baseline.")

    if m["n"] > 0:
        if safe_div(m["pred_neg"], m["n"]) >= 0.80:
            notes.append(f"Predictions are mostly no ({m['pred_neg']}/{m['n']}).")
        elif safe_div(m["pred_pos"], m["n"]) >= 0.80:
            notes.append(f"Predictions are mostly yes ({m['pred_pos']}/{m['n']}).")

    if m["fp"] > 2 * max(m["fn"], 1):
        notes.append("Main error pattern: over-accepting human-negative cases as yes (FP-heavy).")
    elif m["fn"] > 2 * max(m["fp"], 1):
        notes.append("Main error pattern: over-rejecting human-positive cases as no (FN-heavy).")
    else:
        notes.append("FP and FN are relatively balanced.")

    return " ".join(notes)


# ---------------------------------------------------------------------
# Loading / normalization
# ---------------------------------------------------------------------
def available_axes(human: pd.DataFrame, method_frames: Dict[str, pd.DataFrame], strict: bool) -> Dict[str, dict]:
    active = {}
    for axis, info in AXES.items():
        human_ok = info["human_col"] in human.columns
        pred_ok_all = all(info["pred_col"] in df.columns for df in method_frames.values())
        if human_ok and pred_ok_all:
            active[axis] = info
        else:
            msg = (
                f"Skipping axis {axis}: human_col={info['human_col']!r} present={human_ok}, "
                f"pred_col={info['pred_col']!r} present_in_all_methods={pred_ok_all}."
            )
            if strict:
                raise ValueError(msg)
            print(f"[WARN] {msg}")
    if not active:
        raise ValueError("No comparable axes found. Check human and Gemini columns.")
    return active


def normalize_human(human: pd.DataFrame, active_axes: Dict[str, dict]) -> pd.DataFrame:
    required = ["item_id", "variant"]
    missing = [c for c in required if c not in human.columns]
    if missing:
        raise ValueError(f"Human CSV missing required columns: {missing}. Columns: {human.columns.tolist()}")

    out = human.copy()
    out["item_id"] = out["item_id"].astype(str).str.strip()
    out["variant_idx"] = infer_variant_idx_from_human_variant(out["variant"])

    for axis, info in active_axes.items():
        out[f"human_{axis}"] = out[info["human_col"]].map(to_binary)

    if set(CORE_AXES_FOR_OVERALL).issubset(active_axes.keys()):
        core_cols = [f"human_{a}" for a in CORE_AXES_FOR_OVERALL]
        out["human_overall_temporal_recomputed"] = np.where(out[core_cols].eq(1).all(axis=1), 1.0, 0.0)
    # if set(["A", "V", "AVB", "TC", "CC"]).issubset(active_axes.keys()):
    #     strict_cols = [f"human_{a}" for a in ["A", "V", "AVB", "TC", "CC"]]
    if set(["A", "V", "AVB", "TC_REL", "TC_COUNT", "CC"]).issubset(active_axes.keys()):
        strict_cols = [f"human_{a}" for a in ["A", "V", "AVB", "TC_REL", "TC_COUNT", "CC"]]
        out["human_overall_strict_with_CC_recomputed"] = np.where(out[strict_cols].eq(1).all(axis=1), 1.0, 0.0)

    return out


def validate_gemini(df: pd.DataFrame, method_name: str, active_axes: Optional[Dict[str, dict]] = None) -> None:
    # active_axes can be None on the first pass because we discover axes after loading all methods.
    required = ["item_id"]
    if "variant_index" not in df.columns and "video_file" not in df.columns and "video_relpath" not in df.columns:
        required.append("variant_index|video_file|video_relpath")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{method_name} CSV missing required columns: {missing}. Columns: {df.columns.tolist()}")

    if active_axes is not None:
        missing_pred = [info["pred_col"] for info in active_axes.values() if info["pred_col"] not in df.columns]
        if missing_pred:
            raise ValueError(f"{method_name} CSV missing pred columns: {missing_pred}. Columns: {df.columns.tolist()}")


def dedupe_gemini(gemini: pd.DataFrame, method_name: str) -> pd.DataFrame:
    out = gemini.copy()
    out["_original_row_order"] = np.arange(len(out))

    before = len(out)
    if "video_relpath" in out.columns:
        out = out.sort_values("_original_row_order").drop_duplicates(subset=["video_relpath"], keep="last")
    else:
        out = out.sort_values("_original_row_order").drop_duplicates(subset=["item_id", "variant_idx"], keep="last")
    after = len(out)
    if after < before:
        print(f"[WARN:{method_name}] Deduplicated rows: {before} -> {after}")
    return out


def normalize_gemini(gemini: pd.DataFrame, method_name: str, active_axes: Dict[str, dict]) -> pd.DataFrame:
    validate_gemini(gemini, method_name, active_axes)
    out = gemini.copy()
    out["item_id"] = out["item_id"].astype(str).str.strip()
    out["variant_idx"] = infer_variant_idx_from_gemini(out)
    out = dedupe_gemini(out, method_name)

    for axis, info in active_axes.items():
        out[f"pred_{axis}"] = out[info["pred_col"]].map(to_binary)

    if set(CORE_AXES_FOR_OVERALL).issubset(active_axes.keys()):
        core_cols = [f"pred_{a}" for a in CORE_AXES_FOR_OVERALL]
        out["pred_overall_temporal_recomputed"] = np.where(out[core_cols].eq(1).all(axis=1), 1.0, 0.0)
    # if set(["A", "V", "AVB", "TC", "CC"]).issubset(active_axes.keys()):
    #     strict_cols = [f"pred_{a}" for a in ["A", "V", "AVB", "TC", "CC"]]
    if set(["A", "V", "AVB", "TC_REL", "TC_COUNT", "CC"]).issubset(active_axes.keys()):
        strict_cols = [f"pred_{a}" for a in ["A", "V", "AVB", "TC_REL", "TC_COUNT", "CC"]]
        out["pred_overall_strict_with_CC_recomputed"] = np.where(out[strict_cols].eq(1).all(axis=1), 1.0, 0.0)

    out["method"] = method_name
    return out


def merge_one_method(human_norm: pd.DataFrame, gemini_norm: pd.DataFrame, method_name: str, active_axes: Dict[str, dict]) -> pd.DataFrame:
    df = human_norm.merge(
        gemini_norm,
        on=["item_id", "variant_idx"],
        how="inner",
        suffixes=("_human", ""),
    )

    print(f"[INFO:{method_name}] merged rows: {len(df)}")
    if len(df) == 0:
        raise RuntimeError(f"Merged dataframe is empty for {method_name}. Check item_id + variant matching.")

    if len(df) < len(human_norm):
        missing = human_norm.merge(
            gemini_norm[["item_id", "variant_idx"]],
            on=["item_id", "variant_idx"],
            how="left",
            indicator=True,
        )
        missing = missing[missing["_merge"] == "left_only"]
        print(f"[WARN:{method_name}] Human rows missing in method CSV: {len(missing)}")
        preview_cols = [c for c in ["video_id", "item_id", "variant", "variant_idx"] if c in missing.columns]
        print(missing[preview_cols].head(10).to_string(index=False))

    for axis in active_axes:
        df[f"{axis}_error_type"] = [
            error_type(h, p) for h, p in zip(df[f"human_{axis}"], df[f"pred_{axis}"])
        ]
        df[f"{axis}_match"] = df[f"human_{axis}"] == df[f"pred_{axis}"]

    df["method"] = method_name
    df["_example_key"] = df["item_id"].astype(str) + "__v" + df["variant_idx"].astype(str)
    return df


# ---------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------
def build_method_axis_summary(method_dfs: Dict[str, pd.DataFrame], active_axes: Dict[str, dict]) -> pd.DataFrame:
    rows = []
    for method, df in method_dfs.items():
        for axis, info in active_axes.items():
            m = binary_metrics(df[f"pred_{axis}"], df[f"human_{axis}"])
            rows.append({
                "method": method,
                "axis": axis,
                "axis_long_name": info["long_name"],
                **m,
                "interpretation": metrics_interpretation(m),
            })

        if "pred_overall_temporal_recomputed" in df.columns and "human_overall_temporal_recomputed" in df.columns:
            m = binary_metrics(df["pred_overall_temporal_recomputed"], df["human_overall_temporal_recomputed"])
            rows.append({
                "method": method,
                "axis": "Overall_temporal_A_V_AVB_TC",
                "axis_long_name": "Recomputed overall temporal success, excluding CC",
                **m,
                "interpretation": metrics_interpretation(m),
            })

        if "pred_overall_strict_with_CC_recomputed" in df.columns and "human_overall_strict_with_CC_recomputed" in df.columns:
            m = binary_metrics(df["pred_overall_strict_with_CC_recomputed"], df["human_overall_strict_with_CC_recomputed"])
            rows.append({
                "method": method,
                "axis": "Overall_strict_with_CC",
                "axis_long_name": "Recomputed strict overall success, including CC",
                **m,
                "interpretation": metrics_interpretation(m),
            })

    return pd.DataFrame(rows)


def build_method_ranking(summary: pd.DataFrame, active_axes: Dict[str, dict]) -> pd.DataFrame:
    axis_rows = summary[summary["axis"].isin(active_axes.keys())].copy()
    rows = []
    for method, sub in axis_rows.groupby("method"):
        # tc = sub[sub["axis"] == "TC"]
        tc = sub[sub["axis"] == "TC_REL"]
        tc_row = tc.iloc[0].to_dict() if not tc.empty else {}
        rows.append({
            "method": method,
            "n_axes": sub["axis"].nunique(),
            "macro_accuracy_all_axes": sub["accuracy"].mean(),
            "macro_balanced_accuracy_all_axes": sub["balanced_accuracy"].mean(),
            "macro_f1_all_axes": sub["f1"].mean(),
            "TC_accuracy": tc_row.get("accuracy", np.nan),
            "TC_balanced_accuracy": tc_row.get("balanced_accuracy", np.nan),
            "TC_f1": tc_row.get("f1", np.nan),
            "TC_fp": tc_row.get("fp", np.nan),
            "TC_fn": tc_row.get("fn", np.nan),
            "TC_tp": tc_row.get("tp", np.nan),
            "TC_tn": tc_row.get("tn", np.nan),
            "TC_gain_over_majority": tc_row.get("gain_over_majority", np.nan),
            "rank_key_note": "Sort primarily by TC_balanced_accuracy, then TC_accuracy, then macro_balanced_accuracy_all_axes.",
        })
    ranking = pd.DataFrame(rows)
    if not ranking.empty:
        ranking = ranking.sort_values(
            ["TC_balanced_accuracy", "TC_accuracy", "macro_balanced_accuracy_all_axes", "macro_accuracy_all_axes"],
            ascending=[False, False, False, False],
        )
        ranking["rank_TC_first"] = np.arange(1, len(ranking) + 1)
    return ranking


def build_row_level_long(method_dfs: Dict[str, pd.DataFrame], active_axes: Dict[str, dict], excerpt_chars: int) -> pd.DataFrame:
    rows = []
    for method, df in method_dfs.items():
        for _, r in df.iterrows():
            base = {
                "method": method,
                "video_id": r.get("video_id", ""),
                "item_id": r.get("item_id", ""),
                "variant": r.get("variant", ""),
                "variant_idx": r.get("variant_idx", ""),
                "video_relpath": r.get("video_relpath", ""),
                "video_file": r.get("video_file", ""),
                "modality_combination": r.get("modality_combination", ""),
                "temporal_type": r.get("temporal_type", ""),
                "human_failure_reason": r.get("Failure reason", ""),
                "observed_behavior_summary_excerpt": truncate_text(r.get("observed_behavior_summary", ""), excerpt_chars),
                "overall_reason_excerpt": truncate_text(r.get("overall_reason", ""), excerpt_chars),
                "pose_evidence_mode": r.get("pose_evidence_mode", ""),
                "audio_evidence_mode": r.get("audio_evidence_mode", ""),
                "media_fps": r.get("media_fps", ""),
            }
            for axis, info in active_axes.items():
                rows.append({
                    **base,
                    "axis": axis,
                    "human_label": r.get(f"human_{axis}", np.nan),
                    "gemini_label": r.get(f"pred_{axis}", np.nan),
                    "match": r.get(f"{axis}_match", False),
                    "error_type": r.get(f"{axis}_error_type", "NA"),
                    "gemini_raw_label": r.get(info["pred_col"], ""),
                    "gemini_reason_excerpt": truncate_text(r.get(info["reason_col"], ""), excerpt_chars),
                    "gemini_evidence_excerpt": truncate_text(r.get(info["evidence_col"], ""), excerpt_chars),
                })
    return pd.DataFrame(rows)


def prefix_for_wide(df: pd.DataFrame, method: str, active_axes: Dict[str, dict], include_text: bool, excerpt_chars: int) -> pd.DataFrame:
    keep = [
        "item_id",
        "variant_idx",
        "video_id",
        "variant",
        "Failure reason",
        "video_relpath",
        "video_file",
        "modality_combination",
        "temporal_type",
        "media_fps",
        "pose_evidence_mode",
        "audio_evidence_mode",
    ]
    for axis, info in active_axes.items():
        keep.extend([f"pred_{axis}", f"{axis}_match", f"{axis}_error_type", info["pred_col"]])
        if include_text:
            keep.extend([info["reason_col"], info["evidence_col"]])
    keep = [c for c in keep if c in df.columns]
    small = df[keep].copy()
    if include_text:
        for axis, info in active_axes.items():
            for col in [info["reason_col"], info["evidence_col"]]:
                if col in small.columns:
                    small[col] = small[col].map(lambda x: truncate_text(x, excerpt_chars))
    rename = {
        c: f"{method}__{c}"
        for c in small.columns
        if c not in ["item_id", "variant_idx", "video_id", "variant", "Failure reason"]
    }
    return small.rename(columns=rename)


def build_row_level_wide(human_norm: pd.DataFrame, method_dfs: Dict[str, pd.DataFrame], active_axes: Dict[str, dict], include_text: bool, excerpt_chars: int) -> pd.DataFrame:
    base_cols = ["video_id", "item_id", "variant", "variant_idx", "Failure reason"]
    base_cols = [c for c in base_cols if c in human_norm.columns]
    for axis in active_axes:
        base_cols.append(f"human_{axis}")
    if "human_overall_temporal_recomputed" in human_norm.columns:
        base_cols.append("human_overall_temporal_recomputed")
    if "human_overall_strict_with_CC_recomputed" in human_norm.columns:
        base_cols.append("human_overall_strict_with_CC_recomputed")

    wide = human_norm[base_cols].copy()
    for method, df in method_dfs.items():
        pref = prefix_for_wide(df, method, active_axes, include_text, excerpt_chars)
        overlap = [
            c for c in pref.columns
            if c in wide.columns and c not in ["item_id", "variant_idx"]
        ]
        if overlap:
            pref = pref.drop(columns=overlap)
        wide = wide.merge(pref, on=["item_id", "variant_idx"], how="left")
    return wide


def build_tc_breakdowns(method_dfs: Dict[str, pd.DataFrame], group_cols: List[str], min_group_n: int) -> pd.DataFrame:
    rows = []
    for method, df in method_dfs.items():
        existing_group_cols = [c for c in group_cols if c in df.columns]
        if not existing_group_cols:
            continue
        for keys, sub in df.groupby(existing_group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            # m = binary_metrics(sub["pred_TC"], sub["human_TC"])
            m = binary_metrics(sub["pred_TC_REL"], sub["human_TC_REL"])
            if m["n"] < min_group_n:
                continue
            row = {"method": method, **m, "interpretation": metrics_interpretation(m)}
            for col, value in zip(existing_group_cols, keys):
                row[col] = value
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Pairwise and TC disagreement analysis
# ---------------------------------------------------------------------
def pairwise_method_transitions(method_dfs: Dict[str, pd.DataFrame], active_axes: Dict[str, dict]) -> pd.DataFrame:
    rows = []
    for base_method, other_method in itertools.permutations(method_dfs.keys(), 2):
        base = method_dfs[base_method]
        other = method_dfs[other_method]

        common_cols = ["item_id", "variant_idx"]
        base_small = base[common_cols + [f"{a}_match" for a in active_axes] + [f"{a}_error_type" for a in active_axes]].copy()
        other_small = other[common_cols + [f"{a}_match" for a in active_axes] + [f"{a}_error_type" for a in active_axes]].copy()

        base_small = base_small.rename(columns={c: f"base__{c}" for c in base_small.columns if c not in common_cols})
        other_small = other_small.rename(columns={c: f"other__{c}" for c in other_small.columns if c not in common_cols})
        wide = base_small.merge(other_small, on=common_cols, how="inner")

        for axis in active_axes:
            base_match = wide[f"base__{axis}_match"].fillna(False).astype(bool)
            other_match = wide[f"other__{axis}_match"].fillna(False).astype(bool)

            improved = (~base_match & other_match)
            degraded = (base_match & ~other_match)
            both_correct = (base_match & other_match)
            both_wrong = (~base_match & ~other_match)

            rows.append({
                "base_method": base_method,
                "other_method": other_method,
                "axis": axis,
                "n_common": len(wide),
                "other_correct_base_wrong": int(improved.sum()),
                "other_wrong_base_correct": int(degraded.sum()),
                "both_correct": int(both_correct.sum()),
                "both_wrong": int(both_wrong.sum()),
                "net_gain_other_minus_base": int(improved.sum() - degraded.sum()),
                "base_accuracy_on_common": safe_div(int(base_match.sum()), len(wide)),
                "other_accuracy_on_common": safe_div(int(other_match.sum()), len(wide)),
            })

            for transition_name, mask in [
                ("FP_to_TN", (wide[f"base__{axis}_error_type"] == "FP") & (wide[f"other__{axis}_error_type"] == "TN")),
                ("FN_to_TP", (wide[f"base__{axis}_error_type"] == "FN") & (wide[f"other__{axis}_error_type"] == "TP")),
                ("TN_to_FP", (wide[f"base__{axis}_error_type"] == "TN") & (wide[f"other__{axis}_error_type"] == "FP")),
                ("TP_to_FN", (wide[f"base__{axis}_error_type"] == "TP") & (wide[f"other__{axis}_error_type"] == "FN")),
            ]:
                rows.append({
                    "base_method": base_method,
                    "other_method": other_method,
                    "axis": axis,
                    "transition_type_only": transition_name,
                    "n_common": len(wide),
                    "count": int(mask.sum()),
                    "net_gain_other_minus_base": np.nan,
                    "base_accuracy_on_common": np.nan,
                    "other_accuracy_on_common": np.nan,
                })
    return pd.DataFrame(rows)


def collect_method_predictions_for_axis(row: pd.Series, methods: Iterable[str], axis: str) -> Tuple[List[str], List[str], List[str]]:
    labels, correct, wrong = [], [], []
    for method in methods:
        pred_col = f"{method}__pred_{axis}"
        match_col = f"{method}__{axis}_match"
        if pred_col not in row.index or pd.isna(row[pred_col]):
            continue
        labels.append(f"{method}:{format_label(row[pred_col])}")
        if bool(row.get(match_col, False)):
            correct.append(method)
        else:
            wrong.append(method)
    return labels, correct, wrong


def classify_reason_keywords(text: str) -> List[str]:
    text_l = clean_text(text).lower()
    hits = []
    for category, keywords in REASON_KEYWORDS.items():
        if any(k.lower() in text_l for k in keywords):
            hits.append(category)
    return hits


def build_tc_method_disagreement_cases(wide: pd.DataFrame, methods: List[str], active_axes: Dict[str, dict], excerpt_chars: int) -> pd.DataFrame:
    # if "TC" not in active_axes:
    if "TC_REL" not in active_axes:
        return pd.DataFrame()

    rows = []
    # pred_cols = [f"{m}__pred_TC" for m in methods if f"{m}__pred_TC" in wide.columns]
    pred_cols = [f"{m}__pred_TC_REL" for m in methods if f"{m}__pred_TC_REL" in wide.columns]
    if not pred_cols:
        return pd.DataFrame()

    for _, r in wide.iterrows():
        preds = [r[c] for c in pred_cols if not pd.isna(r[c])]
        if len(set(preds)) <= 1:
            continue

        # labels, correct_methods, wrong_methods = collect_method_predictions_for_axis(r, methods, "TC")
        labels, correct_methods, wrong_methods = collect_method_predictions_for_axis(r, methods, "TC_REL")

        reason_blob_parts = []
        method_reason_excerpt = {}
        for m in methods:
            reason_col = f"{m}__temporal_constraint_satisfaction_reason"
            evidence_col = f"{m}__temporal_constraint_satisfaction_evidence"
            if reason_col in r.index:
                reason = truncate_text(r.get(reason_col, ""), excerpt_chars)
                method_reason_excerpt[f"{m}_TC_reason_excerpt"] = reason
                reason_blob_parts.append(reason)
            if evidence_col in r.index:
                evidence = truncate_text(r.get(evidence_col, ""), excerpt_chars)
                method_reason_excerpt[f"{m}_TC_evidence_excerpt"] = evidence
                reason_blob_parts.append(evidence)

        rows.append({
            "video_id": r.get("video_id", ""),
            "item_id": r.get("item_id", ""),
            "variant": r.get("variant", ""),
            "variant_idx": r.get("variant_idx", ""),
            # "human_TC": r.get("human_TC", np.nan),
            "human_TC_REL": r.get("human_TC_REL", np.nan),
            "method_predictions": " | ".join(labels),
            "n_correct_methods": len(correct_methods),
            "n_wrong_methods": len(wrong_methods),
            "correct_methods": ", ".join(correct_methods),
            "wrong_methods": ", ".join(wrong_methods),
            "temporal_type": first_available(r, [f"{m}__temporal_type" for m in methods]),
            "modality_combination": first_available(r, [f"{m}__modality_combination" for m in methods]),
            "human_failure_reason": r.get("Failure reason", ""),
            "reason_keyword_hits": ", ".join(classify_reason_keywords("\n".join(reason_blob_parts))),
            **method_reason_excerpt,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["n_correct_methods", "temporal_type", "modality_combination", "item_id", "variant_idx"])
    return out


def first_available(row: pd.Series, cols: List[str]) -> str:
    for c in cols:
        if c in row.index:
            val = clean_text(row.get(c, ""))
            if val:
                return val
    return ""


def build_tc_all_methods_wrong_cases(wide: pd.DataFrame, methods: List[str], excerpt_chars: int) -> pd.DataFrame:
    rows = []
    for _, r in wide.iterrows():
        valid = []
        wrong = []
        for method in methods:
            # match_col = f"{method}__TC_match"
            # pred_col = f"{method}__pred_TC"
            match_col = f"{method}__TC_REL_match"
            pred_col = f"{method}__pred_TC_REL"
            if match_col not in r.index or pred_col not in r.index or pd.isna(r.get(pred_col)):
                continue
            valid.append(method)
            if not bool(r.get(match_col)):
                wrong.append(method)
        if valid and len(valid) == len(wrong):
            rows.append({
                "video_id": r.get("video_id", ""),
                "item_id": r.get("item_id", ""),
                "variant": r.get("variant", ""),
                "variant_idx": r.get("variant_idx", ""),
                # "human_TC": r.get("human_TC", np.nan),
                "human_TC_REL": r.get("human_TC_REL", np.nan),
                "wrong_methods": ", ".join(wrong),
                "temporal_type": first_available(r, [f"{m}__temporal_type" for m in methods]),
                "modality_combination": first_available(r, [f"{m}__modality_combination" for m in methods]),
                "human_failure_reason": r.get("Failure reason", ""),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Qualitative examples
# ---------------------------------------------------------------------
def build_video_path_from_row(row: pd.Series, video_root: Optional[Path]) -> str:
    if video_root is None:
        return ""
    rel = clean_text(row.get("video_relpath", ""))
    if rel:
        return str(video_root / rel)
    item_id = clean_text(row.get("item_id", ""))
    variant_idx = row.get("variant_idx", "")
    if item_id and not pd.isna(variant_idx):
        try:
            return str(video_root / item_id / f"{item_id}_v{int(variant_idx)}_raw.mp4")
        except Exception:
            return ""
    return ""


def qualitative_quality_score(df: pd.DataFrame, axis: str, info: dict) -> pd.Series:
    reason = df.get(info["reason_col"], pd.Series("", index=df.index)).fillna("").astype(str)
    evidence = df.get(info["evidence_col"], pd.Series("", index=df.index)).fillna("").astype(str)
    observed = df.get("observed_behavior_summary", pd.Series("", index=df.index)).fillna("").astype(str)
    human_reason = df.get("Failure reason", pd.Series("", index=df.index)).fillna("").astype(str)
    # Prefer rich, interpretable examples; for TC, temporal_type/modality are especially useful.
    score = (
        reason.str.len().clip(upper=600)
        + evidence.str.len().clip(upper=800)
        + observed.str.len().clip(upper=300)
        + human_reason.str.len().clip(upper=200)
    )
    if axis in {"TC_REL", "TC_COUNT"}:
        score += df.get("temporal_type", pd.Series("", index=df.index)).fillna("").astype(str).str.len().clip(upper=100)
    return score


def select_qualitative_examples(method_dfs: Dict[str, pd.DataFrame], active_axes: Dict[str, dict], examples_per_type: int) -> List[Tuple[str, str, str, pd.Series]]:
    selections: List[Tuple[str, str, str, pd.Series]] = []
    for method, df in method_dfs.items():
        for axis, info in active_axes.items():
            selected_keys = set()
            for etype in ["TP", "TN", "FP", "FN"]:
                subset = df[df[f"{axis}_error_type"] == etype].copy()
                if subset.empty:
                    continue
                subset = subset[~subset["_example_key"].isin(selected_keys)].copy()
                if subset.empty:
                    continue
                subset["_quality_score"] = qualitative_quality_score(subset, axis, info)
                subset = subset.sort_values(["_quality_score", "item_id", "variant_idx"], ascending=[False, True, True])
                if examples_per_type > 0:
                    subset = subset.head(examples_per_type)
                for _, row in subset.iterrows():
                    selected_keys.add(row["_example_key"])
                    selections.append((method, axis, etype, row))
    return selections


def write_detail_file(row: pd.Series, method: str, axis: str, etype: str, info: dict, out_dir: Path, video_root: Optional[Path], max_chars: int) -> Path:
    detail_dir = out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(f"{method}_{axis}_{etype}_{row.get('item_id', 'item')}_v{row.get('variant_idx', 'x')}.txt")
    path = detail_dir / fname

    sections = [
        ("METHOD", method),
        ("AXIS", axis),
        ("ERROR_TYPE", etype),
        ("HUMAN_LABEL", format_label(row.get(f"human_{axis}", np.nan))),
        ("GEMINI_LABEL", format_label(row.get(f"pred_{axis}", np.nan))),
        ("VIDEO_ID", row.get("video_id", "")),
        ("ITEM_ID", row.get("item_id", "")),
        ("VARIANT", row.get("variant", "")),
        ("VARIANT_IDX", row.get("variant_idx", "")),
        ("VIDEO_RELPATH", row.get("video_relpath", "")),
        ("FULL_VIDEO_PATH", build_video_path_from_row(row, video_root)),
        ("MODALITY_COMBINATION", row.get("modality_combination", "")),
        ("TEMPORAL_TYPE", row.get("temporal_type", "")),
        ("HUMAN_FAILURE_REASON", row.get("Failure reason", "")),
        ("GEMINI_AXIS_RAW_LABEL", row.get(info["pred_col"], "")),
        ("GEMINI_AXIS_REASON", row.get(info["reason_col"], "")),
        ("GEMINI_AXIS_EVIDENCE", row.get(info["evidence_col"], "")),
        ("OBSERVED_BEHAVIOR_SUMMARY", row.get("observed_behavior_summary", "")),
        ("OVERALL_REASON", row.get("overall_reason", "")),
        ("POSE_EVIDENCE_MODE", row.get("pose_evidence_mode", "")),
        ("AUDIO_EVIDENCE_MODE", row.get("audio_evidence_mode", "")),
        ("MEDIA_FPS", row.get("media_fps", "")),
        ("USER_PROMPT_SENT_TO_GEMINI", row.get("user_prompt", "")),
        ("MEDIAPIPE_SUMMARY", row.get("mediapipe_summary", "")),
        ("AUDIO_EVIDENCE_SUMMARY", row.get("audio_evidence_summary", "")),
        ("RAW_GEMINI_OUTPUT", row.get("raw_output", "")),
    ]

    lines = []
    for title, value in sections:
        lines.extend(["=" * 100, str(title), "=" * 100, truncate_text(value, max_chars), ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_qualitative_outputs(
    method_dfs: Dict[str, pd.DataFrame],
    active_axes: Dict[str, dict],
    out_dir: Path,
    video_root: Optional[Path],
    examples_per_type: int,
    detail_max_chars: int,
    excerpt_chars: int,
) -> Tuple[pd.DataFrame, str]:
    selections = select_qualitative_examples(method_dfs, active_axes, examples_per_type)
    rows = []
    md_lines = [
        "# Qualitative examples",
        "",
        "TP/TN are agreements with human GT. FP/FN are disagreements.",
        "FP = Gemini yes / human no. FN = Gemini no / human yes.",
        "",
    ]

    for method, axis, etype, row in selections:
        info = active_axes[axis]
        detail_path = write_detail_file(row, method, axis, etype, info, out_dir, video_root, detail_max_chars)
        compact = {
            "method": method,
            "axis": axis,
            "error_type": etype,
            "human_label": format_label(row.get(f"human_{axis}", np.nan)),
            "gemini_label": format_label(row.get(f"pred_{axis}", np.nan)),
            "video_id": row.get("video_id", ""),
            "item_id": row.get("item_id", ""),
            "variant": row.get("variant", ""),
            "variant_idx": row.get("variant_idx", ""),
            "full_video_path": build_video_path_from_row(row, video_root),
            "modality_combination": row.get("modality_combination", ""),
            "temporal_type": row.get("temporal_type", ""),
            "human_failure_reason": row.get("Failure reason", ""),
            "gemini_reason_excerpt": truncate_text(row.get(info["reason_col"], ""), excerpt_chars),
            "gemini_evidence_excerpt": truncate_text(row.get(info["evidence_col"], ""), excerpt_chars),
            "observed_behavior_summary_excerpt": truncate_text(row.get("observed_behavior_summary", ""), excerpt_chars),
            "pose_evidence_mode": row.get("pose_evidence_mode", ""),
            "audio_evidence_mode": row.get("audio_evidence_mode", ""),
            "media_fps": row.get("media_fps", ""),
            "detail_file": str(detail_path),
        }
        rows.append(compact)

    qual = pd.DataFrame(rows)

    if not qual.empty:
        for method in qual["method"].drop_duplicates():
            md_lines.append(f"## {method}")
            md_lines.append("")
            for axis in qual[qual["method"] == method]["axis"].drop_duplicates():
                md_lines.append(f"### {axis}")
                md_lines.append("")
                sub = qual[(qual["method"] == method) & (qual["axis"] == axis)]
                for _, r in sub.iterrows():
                    md_lines.append(f"#### {r['error_type']} — {r['item_id']} v{r['variant_idx']}")
                    md_lines.append("")
                    md_lines.append(f"- Human: `{r['human_label']}` / Gemini: `{r['gemini_label']}`")
                    md_lines.append(f"- Temporal type: `{r['temporal_type']}`")
                    md_lines.append(f"- Modality: `{r['modality_combination']}`")
                    if r["human_failure_reason"]:
                        md_lines.append(f"- Human failure reason: {r['human_failure_reason']}")
                    md_lines.append(f"- Gemini reason: {r['gemini_reason_excerpt']}")
                    md_lines.append(f"- Gemini evidence: {r['gemini_evidence_excerpt']}")
                    md_lines.append(f"- Detail file: `{r['detail_file']}`")
                    md_lines.append("")
    else:
        md_lines.append("No qualitative examples selected.")

    return qual, "\n".join(md_lines)


def build_reason_keyword_summary(disagreement_cases: pd.DataFrame) -> pd.DataFrame:
    if disagreement_cases.empty or "reason_keyword_hits" not in disagreement_cases.columns:
        return pd.DataFrame()
    rows = []
    for _, r in disagreement_cases.iterrows():
        hits = [h.strip() for h in str(r.get("reason_keyword_hits", "")).split(",") if h.strip()]
        for h in hits:
            rows.append({
                "keyword_category": h,
                "temporal_type": r.get("temporal_type", ""),
                "modality_combination": r.get("modality_combination", ""),
                "item_id": r.get("item_id", ""),
                "variant_idx": r.get("variant_idx", ""),
                "correct_methods": r.get("correct_methods", ""),
                "wrong_methods": r.get("wrong_methods", ""),
            })
    if not rows:
        return pd.DataFrame()
    long = pd.DataFrame(rows)
    return (
        long.groupby(["keyword_category", "temporal_type"], dropna=False)
        .size()
        .reset_index(name="n_cases")
        .sort_values(["n_cases", "keyword_category"], ascending=[False, True])
    )


def write_markdown_report(out_dir: Path, ranking: pd.DataFrame, summary: pd.DataFrame, tc_breakdowns: Dict[str, pd.DataFrame], methods: List[str], active_axes: Dict[str, dict]) -> None:
    lines = [
        "# Gemini tool-option analysis",
        "",
        "This report treats the human labels as GT and compares each Gemini/tool setting against them.",
        "",
        "## Methods analyzed",
        "",
    ]
    for method in methods:
        lines.append(f"- `{method}`")
    lines.append("")

    lines.append("## Ranking, TC-first")
    lines.append("")
    if not ranking.empty:
        display_cols = [
            "rank_TC_first", "method", "TC_balanced_accuracy", "TC_accuracy", "TC_f1",
            "TC_fp", "TC_fn", "macro_balanced_accuracy_all_axes", "macro_accuracy_all_axes"
        ]
        display_cols = [c for c in display_cols if c in ranking.columns]
        lines.append(ranking[display_cols].pipe(df_to_markdown, index=False))
    else:
        lines.append("No ranking available.")
    lines.append("")

    lines.append("## Axis-level summary")
    lines.append("")
    if not summary.empty:
        show = summary[summary["axis"].isin(active_axes.keys())].copy()
        display_cols = ["method", "axis", "n", "accuracy", "balanced_accuracy", "precision", "positive_recall", "negative_recall", "f1", "tn", "fp", "fn", "tp"]
        display_cols = [c for c in display_cols if c in show.columns]
        lines.append(show[display_cols].pipe(df_to_markdown, index=False))
    lines.append("")

    lines.append("## TC breakdown notes")
    lines.append("")
    for name, df in tc_breakdowns.items():
        lines.append(f"### {name}")
        lines.append("")
        if df.empty:
            lines.append("No breakdown available.")
        else:
            display_cols = [c for c in ["method", "temporal_type", "modality_combination", "n", "accuracy", "balanced_accuracy", "fp", "fn", "tp", "tn"] if c in df.columns]
            preview = df.sort_values(["method", "accuracy"], ascending=[True, True]).head(30)
            lines.append(preview[display_cols].pipe(df_to_markdown, index=False))
            lines.append("")
            lines.append("Preview is sorted to surface weaker groups first. See the CSV files for the full table.")
        lines.append("")

    lines.append("## Recommended reading order")
    lines.append("")
    lines.append("1. `method_ranking.csv`: decide which method is best under a TC-first criterion.")
    lines.append("2. `tc_breakdown_by_temporal_type.csv`: check whether synchronization, order, count, or absolute timing drives differences.")
    lines.append("3. `tc_method_disagreement_cases.csv`: inspect cases where tool options disagree.")
    lines.append("4. `qualitative_examples.md` and `details/*.txt`: read model reasons/evidence for TP/TN/FP/FN examples.")
    lines.append("")

    (out_dir / "README_analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main() -> None:
    args = parse_args()
    methods = parse_method_specs(args.method)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Human GT: {args.human_path}")
    human_raw = pd.read_csv(args.human_path)
    print(f"[INFO] Human rows: {len(human_raw)}")

    raw_method_frames: Dict[str, pd.DataFrame] = {}
    for name, path in methods.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing CSV for method {name}: {path}")
        df = pd.read_csv(path)
        validate_gemini(df, name)
        raw_method_frames[name] = df
        print(f"[INFO:{name}] path={path}")
        print(f"[INFO:{name}] raw rows={len(df)}")

    active_axes = available_axes(human_raw, raw_method_frames, strict=args.strict)
    print(f"[INFO] Active axes: {list(active_axes.keys())}")

    human_norm = normalize_human(human_raw, active_axes)

    method_dfs: Dict[str, pd.DataFrame] = {}
    for name, raw_df in raw_method_frames.items():
        gem_norm = normalize_gemini(raw_df, name, active_axes)
        method_dfs[name] = merge_one_method(human_norm, gem_norm, name, active_axes)

    # 1) Main summaries
    method_axis_summary = build_method_axis_summary(method_dfs, active_axes)
    method_axis_summary_path = args.out_dir / "method_axis_summary.csv"
    method_axis_summary.to_csv(method_axis_summary_path, index=False)

    ranking = build_method_ranking(method_axis_summary, active_axes)
    ranking_path = args.out_dir / "method_ranking.csv"
    ranking.to_csv(ranking_path, index=False)

    # 2) Row-level outputs
    row_level_long = build_row_level_long(method_dfs, active_axes, args.excerpt_chars)
    row_level_long_path = args.out_dir / "row_level_long.csv"
    row_level_long.to_csv(row_level_long_path, index=False)

    row_level_wide = build_row_level_wide(human_norm, method_dfs, active_axes, args.include_wide_text, args.excerpt_chars)
    row_level_wide_path = args.out_dir / "row_level_wide_core.csv"
    row_level_wide.to_csv(row_level_wide_path, index=False)

    # 3) TC-focused breakdowns
    tc_breakdowns = {
        "by_temporal_type": build_tc_breakdowns(method_dfs, ["temporal_type"], args.min_group_n),
        "by_modality_combination": build_tc_breakdowns(method_dfs, ["modality_combination"], args.min_group_n),
        "by_temporal_type_x_modality_combination": build_tc_breakdowns(method_dfs, ["temporal_type", "modality_combination"], args.min_group_n),
    }
    tc_breakdown_paths = {}
    for name, df in tc_breakdowns.items():
        path = args.out_dir / f"tc_breakdown_{name}.csv"
        df.to_csv(path, index=False)
        tc_breakdown_paths[name] = path

    # 4) Pairwise method transitions
    transitions = pairwise_method_transitions(method_dfs, active_axes)
    transitions_path = args.out_dir / "pairwise_method_transitions.csv"
    transitions.to_csv(transitions_path, index=False)

    # 5) TC disagreements across methods
    methods_list = list(methods.keys())
    tc_disagreements = build_tc_method_disagreement_cases(row_level_wide, methods_list, active_axes, args.excerpt_chars)
    tc_disagreements_path = args.out_dir / "tc_method_disagreement_cases.csv"
    tc_disagreements.to_csv(tc_disagreements_path, index=False)

    tc_all_wrong = build_tc_all_methods_wrong_cases(row_level_wide, methods_list, args.excerpt_chars)
    tc_all_wrong_path = args.out_dir / "tc_all_methods_wrong_cases.csv"
    tc_all_wrong.to_csv(tc_all_wrong_path, index=False)

    reason_keyword_summary = build_reason_keyword_summary(tc_disagreements)
    reason_keyword_summary_path = args.out_dir / "tc_reason_keyword_summary.csv"
    reason_keyword_summary.to_csv(reason_keyword_summary_path, index=False)

    # 6) Qualitative examples
    qualitative, qualitative_md = build_qualitative_outputs(
        method_dfs=method_dfs,
        active_axes=active_axes,
        out_dir=args.out_dir,
        video_root=args.video_root,
        examples_per_type=args.examples_per_type,
        detail_max_chars=args.detail_max_chars,
        excerpt_chars=args.excerpt_chars,
    )
    qualitative_path = args.out_dir / "qualitative_examples.csv"
    qualitative.to_csv(qualitative_path, index=False)
    qualitative_md_path = args.out_dir / "qualitative_examples.md"
    qualitative_md_path.write_text(qualitative_md, encoding="utf-8")

    # 7) Markdown report
    write_markdown_report(args.out_dir, ranking, method_axis_summary, tc_breakdowns, methods_list, active_axes)

    print("\n========== SAVED ==========")
    for p in [
        method_axis_summary_path,
        ranking_path,
        row_level_long_path,
        row_level_wide_path,
        *tc_breakdown_paths.values(),
        transitions_path,
        tc_disagreements_path,
        tc_all_wrong_path,
        reason_keyword_summary_path,
        qualitative_path,
        qualitative_md_path,
        args.out_dir / "README_analysis_summary.md",
    ]:
        print(p)

    print("\n========== TC-FIRST RANKING ==========")
    if not ranking.empty:
        cols = [
            "rank_TC_first", "method", "TC_balanced_accuracy", "TC_accuracy", "TC_f1",
            "TC_fp", "TC_fn", "macro_balanced_accuracy_all_axes", "macro_accuracy_all_axes",
        ]
        cols = [c for c in cols if c in ranking.columns]
        print(ranking[cols].to_string(index=False))
    else:
        print("No ranking available.")


if __name__ == "__main__":
    main()
