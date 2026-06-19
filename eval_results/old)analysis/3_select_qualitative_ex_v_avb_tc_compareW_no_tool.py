#!/usr/bin/env python3
"""
Select qualitative examples for V / AVB / TC, including a no-tool baseline.

This script extends the previous raw/focused_raw qualitative selector by adding
`no_tool` results and an explicit transition analysis:

1. Per-method examples for each method in {no_tool, raw, focused_raw}:
   - 2 agreement examples, preferably one TP and one TN
   - 2 disagreement examples, preferably one FP and one FN

2. Pairwise transition examples vs no_tool for each tool method in {raw, focused_raw}:
   - improved: no_tool was wrong, tool method is correct
   - degraded: no_tool was correct, tool method is wrong

Definitions:
  - TP: human=1, model=1
  - TN: human=0, model=0
  - FP: human=0, model=1
  - FN: human=1, model=0
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd


DEFAULT_HUMAN_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/human_FIVE_axis_labels.csv"
)

DEFAULT_NO_TOOL_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/eval_outputs_without-Tool/new-axis_temporal_eval.csv"
)

DEFAULT_RAW_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/output_tool_raw/results.csv"
)

DEFAULT_FOCUSED_RAW_PATH = Path(
    "/home/coder/T2V_Gen/Gemini/output_tool_focused_raw/results.csv"
)

DEFAULT_OUT_DIR = Path(
    "/home/coder/T2V_Gen/Gemini/human_eval_GT/Analysis_comparison"
)

DEFAULT_VIDEO_ROOT = Path(
    "/home/coder/T2V_Gen/hf_datasets/T2AV_TemporalConstraint/LTX-2.3/3-seed42-dev_outputs-comb-temporal_reorganized"
)

AXES = {
    "V": {
        "human_col": "V",
        "pred_col": "visual_event_correctness",
        "reason_col": "visual_event_correctness_reason",
        "evidence_col": "visual_event_correctness_evidence",
    },
    "AVB": {
        "human_col": "AVB",
        "pred_col": "audio_visual_binding",
        "reason_col": "audio_visual_binding_reason",
        "evidence_col": "audio_visual_binding_evidence",
    },
    "TC": {
        "human_col": "TC",
        "pred_col": "temporal_constraint_satisfaction",
        "reason_col": "temporal_constraint_satisfaction_reason",
        "evidence_col": "temporal_constraint_satisfaction_evidence",
    },
}

LONG_COLUMNS = [
    "user_prompt",
    "mediapipe_summary",
    "raw_output",
    "observed_behavior_summary",
    "overall_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pick qualitative examples for V, AVB, and TC across no_tool/raw/focused_raw."
    )
    parser.add_argument("--human-path", type=Path, default=DEFAULT_HUMAN_PATH)
    parser.add_argument("--no-tool-path", type=Path, default=DEFAULT_NO_TOOL_PATH)
    parser.add_argument("--raw-path", type=Path, default=DEFAULT_RAW_PATH)
    parser.add_argument("--focused-raw-path", type=Path, default=DEFAULT_FOCUSED_RAW_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT)
    parser.add_argument(
        "--detail-max-chars",
        type=int,
        default=60000,
        help="Max characters per long field in per-example detail TXT. <=0 means no truncation.",
    )
    parser.add_argument(
        "--excerpt-chars",
        type=int,
        default=1500,
        help="Max characters for reason/evidence/MediaPipe excerpts in compact CSV/Markdown.",
    )
    parser.add_argument(
        "--max-transition-examples-per-type",
        type=int,
        default=0,
        help=(
            "Max transition examples to save per axis/transition type. "
            "0 means save all available examples. This affects improved_FP_to_TN, "
            "improved_FN_to_TP, degraded_TN_to_FP, and degraded_TP_to_FN."
        ),
    )
    parser.add_argument(
        "--max-transition-fallback-examples",
        type=int,
        default=0,
        help=(
            "Max fallback improved_any/degraded_any examples when typed examples are absent. "
            "0 means save all available fallback examples."
        ),
    )
    return parser.parse_args()


def to_binary(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s in {"1", "y", "yes", "true"}:
        return 1
    if s in {"0", "n", "no", "false"}:
        return 0
    return np.nan


def truncate_text(x, max_chars: int) -> str:
    if pd.isna(x):
        return ""
    text = str(x)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [TRUNCATED to {max_chars} chars]"


def safe_filename(text: str, max_len: int = 150) -> str:
    text = str(text)
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    return text[:max_len].strip("_") or "example"


def get_value(row: pd.Series, col: str, default=""):
    return row[col] if col in row.index else default


def normalize_keys(human: pd.DataFrame, gemini: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    human = human.copy()
    gemini = gemini.copy()

    human["item_id"] = human["item_id"].astype(str).str.strip()
    gemini["item_id"] = gemini["item_id"].astype(str).str.strip()

    human["variant_idx"] = (
        human["variant"].astype(str).str.extract(r"(\d+)")[0].astype("Int64")
    )

    gemini["variant_idx"] = pd.to_numeric(
        gemini["variant_index"], errors="coerce"
    ).astype("Int64")

    return human, gemini


def dedupe_gemini(gemini: pd.DataFrame, method_name: str) -> pd.DataFrame:
    gemini = gemini.copy()
    gemini["_original_row_order"] = np.arange(len(gemini))

    before = len(gemini)
    if "video_relpath" in gemini.columns:
        gemini = gemini.sort_values("_original_row_order").drop_duplicates(
            subset=["video_relpath"], keep="last"
        )
    else:
        gemini = gemini.sort_values("_original_row_order").drop_duplicates(
            subset=["item_id", "variant_index"], keep="last"
        )

    after = len(gemini)
    if after < before:
        print(f"[WARN:{method_name}] Deduplicated Gemini rows: {before} -> {after}")

    return gemini


def validate_gemini_cols(gemini: pd.DataFrame, method_name: str) -> None:
    required = ["item_id", "variant_index"]
    for axis, info in AXES.items():
        required.append(info["pred_col"])
    missing = [c for c in required if c not in gemini.columns]
    if missing:
        raise ValueError(
            f"Gemini CSV for {method_name} missing columns: {missing}. "
            f"Columns: {gemini.columns.tolist()}"
        )


def add_binary_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for axis, info in AXES.items():
        df[f"human_{axis}"] = df[info["human_col"]].map(to_binary)
        df[f"pred_{axis}"] = df[info["pred_col"]].map(to_binary)

        conditions = [
            (df[f"human_{axis}"] == 1) & (df[f"pred_{axis}"] == 1),
            (df[f"human_{axis}"] == 0) & (df[f"pred_{axis}"] == 0),
            (df[f"human_{axis}"] == 0) & (df[f"pred_{axis}"] == 1),
            (df[f"human_{axis}"] == 1) & (df[f"pred_{axis}"] == 0),
        ]
        df[f"{axis}_error_type"] = np.select(conditions, ["TP", "TN", "FP", "FN"], default="NA")
        df[f"{axis}_match"] = df[f"human_{axis}"] == df[f"pred_{axis}"]

    return df


def quality_score(candidates: pd.DataFrame, axis: str) -> pd.Series:
    """Prefer examples with more informative textual rationales/evidence."""
    info = AXES[axis]
    reason = candidates.get(info["reason_col"], pd.Series("", index=candidates.index)).fillna("").astype(str)
    evidence = candidates.get(info["evidence_col"], pd.Series("", index=candidates.index)).fillna("").astype(str)
    observed = candidates.get("observed_behavior_summary", pd.Series("", index=candidates.index)).fillna("").astype(str)
    mp = candidates.get("mediapipe_summary", pd.Series("", index=candidates.index)).fillna("").astype(str)

    return (
        reason.str.len().clip(upper=500)
        + evidence.str.len().clip(upper=700)
        + observed.str.len().clip(upper=300)
        + (mp.str.len() > 0).astype(int) * 100
    )


def select_one(candidates: pd.DataFrame, axis: str, already_selected: set) -> Optional[pd.Series]:
    if candidates.empty:
        return None

    candidates = candidates.copy()
    if "_example_key" in candidates.columns:
        candidates = candidates[~candidates["_example_key"].isin(already_selected)]
    if candidates.empty:
        return None

    candidates["_score"] = quality_score(candidates, axis)
    sort_cols = ["_score"]
    ascending = [False]
    if "video_id" in candidates.columns:
        sort_cols.append("video_id")
        ascending.append(True)
    else:
        sort_cols.append("_original_row_order")
        ascending.append(True)

    return candidates.sort_values(sort_cols, ascending=ascending).iloc[0]


def select_examples_for_axis(df: pd.DataFrame, axis: str) -> List[pd.Series]:
    """Select 2 matches and 2 mismatches for one method."""
    selected: List[pd.Series] = []
    selected_keys: set = set()

    def add(row: Optional[pd.Series], selection_kind: str):
        if row is None:
            return
        row = row.copy()
        row["_selection_kind"] = selection_kind
        key = row["_example_key"]
        if key in selected_keys:
            return
        selected_keys.add(key)
        selected.append(row)

    for error_type in ["TP", "TN"]:
        subset = df[df[f"{axis}_error_type"] == error_type]
        add(select_one(subset, axis, selected_keys), f"match_{error_type}")

    while sum(str(r["_selection_kind"]).startswith("match") for r in selected) < 2:
        subset = df[df[f"{axis}_error_type"].isin(["TP", "TN"])]
        row = select_one(subset, axis, selected_keys)
        if row is None:
            break
        add(row, f"match_{row[f'{axis}_error_type']}")

    for error_type in ["FP", "FN"]:
        subset = df[df[f"{axis}_error_type"] == error_type]
        add(select_one(subset, axis, selected_keys), f"mismatch_{error_type}")

    while sum(str(r["_selection_kind"]).startswith("mismatch") for r in selected) < 2:
        subset = df[df[f"{axis}_error_type"].isin(["FP", "FN"])]
        row = select_one(subset, axis, selected_keys)
        if row is None:
            break
        add(row, f"mismatch_{row[f'{axis}_error_type']}")

    return selected


def build_video_path(row: pd.Series, video_root: Path) -> str:
    video_relpath = str(get_value(row, "video_relpath", ""))
    if video_relpath and video_relpath != "nan":
        return str(video_root / video_relpath)
    item_id = str(get_value(row, "item_id", ""))
    variant_idx = get_value(row, "variant_idx", "")
    if item_id and pd.notna(variant_idx):
        return str(video_root / item_id / f"{item_id}_v{int(variant_idx)}_raw.mp4")
    return ""


def build_compact_row(row: pd.Series, method_name: str, axis: str, detail_path: Path, video_root: Path, excerpt_chars: int) -> dict:
    info = AXES[axis]
    return {
        "method": method_name,
        "axis": axis,
        "selection_kind": get_value(row, "_selection_kind", ""),
        "error_type": get_value(row, f"{axis}_error_type", ""),
        "human_label": get_value(row, f"human_{axis}", np.nan),
        "gemini_label": get_value(row, f"pred_{axis}", np.nan),
        "video_id": get_value(row, "video_id", ""),
        "item_id": get_value(row, "item_id", ""),
        "variant": get_value(row, "variant", ""),
        "variant_idx": get_value(row, "variant_idx", ""),
        "video_relpath": get_value(row, "video_relpath", ""),
        "full_video_path": build_video_path(row, video_root),
        "modality_combination": get_value(row, "modality_combination", ""),
        "temporal_type": get_value(row, "temporal_type", ""),
        "human_failure_reason": get_value(row, "Failure reason", ""),
        "gemini_axis_reason_excerpt": truncate_text(get_value(row, info["reason_col"], ""), excerpt_chars),
        "gemini_axis_evidence_excerpt": truncate_text(get_value(row, info["evidence_col"], ""), excerpt_chars),
        "observed_behavior_summary_excerpt": truncate_text(get_value(row, "observed_behavior_summary", ""), excerpt_chars),
        "overall_reason_excerpt": truncate_text(get_value(row, "overall_reason", ""), excerpt_chars),
        "pose_evidence_mode": get_value(row, "pose_evidence_mode", ""),
        "mediapipe_hint_used": get_value(row, "mediapipe_hint_used", ""),
        "mediapipe_error": get_value(row, "mediapipe_error", ""),
        "mediapipe_summary_excerpt": truncate_text(get_value(row, "mediapipe_summary", ""), excerpt_chars),
        "detail_file": str(detail_path),
    }


def write_detail_file(row: pd.Series, method_name: str, axis: str, detail_dir: Path, video_root: Path, max_chars: int) -> Path:
    info = AXES[axis]
    error_type = get_value(row, f"{axis}_error_type", "NA")
    item_id = get_value(row, "item_id", "unknown_item")
    variant = get_value(row, "variant", get_value(row, "variant_idx", "unknown_variant"))

    fname = safe_filename(f"{method_name}_{axis}_{get_value(row, '_selection_kind', '')}_{error_type}_{item_id}_{variant}.txt")
    path = detail_dir / fname

    sections = [
        ("METHOD", method_name),
        ("AXIS", axis),
        ("SELECTION_KIND", get_value(row, "_selection_kind", "")),
        ("ERROR_TYPE", error_type),
        ("HUMAN_LABEL", get_value(row, f"human_{axis}", np.nan)),
        ("GEMINI_LABEL", get_value(row, f"pred_{axis}", np.nan)),
        ("VIDEO_ID", get_value(row, "video_id", "")),
        ("ITEM_ID", get_value(row, "item_id", "")),
        ("VARIANT", get_value(row, "variant", "")),
        ("VIDEO_RELPATH", get_value(row, "video_relpath", "")),
        ("FULL_VIDEO_PATH", build_video_path(row, video_root)),
        ("MODALITY_COMBINATION", get_value(row, "modality_combination", "")),
        ("TEMPORAL_TYPE", get_value(row, "temporal_type", "")),
        ("HUMAN_FAILURE_REASON", get_value(row, "Failure reason", "")),
        ("GEMINI_AXIS_LABEL_RAW", get_value(row, info["pred_col"], "")),
        ("GEMINI_AXIS_REASON", get_value(row, info["reason_col"], "")),
        ("GEMINI_AXIS_EVIDENCE", get_value(row, info["evidence_col"], "")),
        ("OBSERVED_BEHAVIOR_SUMMARY", get_value(row, "observed_behavior_summary", "")),
        ("OVERALL_REASON", get_value(row, "overall_reason", "")),
        ("POSE_EVIDENCE_MODE", get_value(row, "pose_evidence_mode", "")),
        ("MEDIAPIPE_HINT_USED", get_value(row, "mediapipe_hint_used", "")),
        ("MEDIAPIPE_ERROR", get_value(row, "mediapipe_error", "")),
        ("USER_PROMPT_SENT_TO_GEMINI", get_value(row, "user_prompt", "")),
        ("MEDIAPIPE_SUMMARY", get_value(row, "mediapipe_summary", "")),
        ("RAW_GEMINI_OUTPUT", get_value(row, "raw_output", "")),
    ]

    lines = []
    for title, value in sections:
        lines.append("=" * 100)
        lines.append(str(title))
        lines.append("=" * 100)
        lines.append(truncate_text(value, max_chars))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_markdown_summary(rows: List[dict], out_path: Path, title: str) -> None:
    lines = [
        f"# {title}",
        "",
        "Each axis contains two agreement examples and two disagreement examples when available.",
        "FP = Gemini yes / human no; FN = Gemini no / human yes.",
        "",
    ]

    for axis in ["V", "AVB", "TC"]:
        lines.append(f"## {axis}")
        lines.append("")
        axis_rows = [r for r in rows if r["axis"] == axis]
        for r in axis_rows:
            lines.append(f"### {r['selection_kind']} ({r['error_type']}) — {r['item_id']} {r['variant']}")
            lines.append("")
            lines.append(f"- Human label: `{r['human_label']}`")
            lines.append(f"- Gemini label: `{r['gemini_label']}`")
            lines.append(f"- Video: `{r['full_video_path']}`")
            lines.append(f"- Modality: `{r['modality_combination']}`")
            lines.append(f"- Temporal type: `{r['temporal_type']}`")
            if r.get("human_failure_reason"):
                lines.append(f"- Human failure reason: {r['human_failure_reason']}")
            lines.append(f"- Gemini reason: {r['gemini_axis_reason_excerpt']}")
            lines.append(f"- Gemini evidence: {r['gemini_axis_evidence_excerpt']}")
            lines.append(f"- Detail file: `{r['detail_file']}`")
            lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def load_and_merge_method(method_name: str, gemini_path: Path, human: pd.DataFrame) -> pd.DataFrame:
    print(f"\n========== Loading {method_name} ==========")
    print(f"[INFO:{method_name}] Gemini path: {gemini_path}")
    if not gemini_path.exists():
        raise FileNotFoundError(f"Missing Gemini result CSV for {method_name}: {gemini_path}")

    gemini = pd.read_csv(gemini_path)
    validate_gemini_cols(gemini, method_name)
    print(f"[INFO:{method_name}] Gemini rows before dedupe: {len(gemini)}")
    gemini = dedupe_gemini(gemini, method_name)
    print(f"[INFO:{method_name}] Gemini rows after dedupe: {len(gemini)}")

    if "pose_evidence_mode" in gemini.columns:
        print(f"[INFO:{method_name}] pose_evidence_mode counts:")
        print(gemini["pose_evidence_mode"].value_counts(dropna=False).to_string())

    if "mediapipe_hint_used" in gemini.columns:
        print(f"[INFO:{method_name}] mediapipe_hint_used counts:")
        print(gemini["mediapipe_hint_used"].value_counts(dropna=False).to_string())

    if "mediapipe_error" in gemini.columns:
        bad = gemini[gemini["mediapipe_error"].fillna("").astype(str).str.len() > 0]
        print(f"[WARN:{method_name}] Rows with MediaPipe error: {len(bad)}")

    human_norm, gemini_norm = normalize_keys(human, gemini)
    df = human_norm.merge(
        gemini_norm,
        on=["item_id", "variant_idx"],
        how="inner",
        suffixes=("_human", "_gemini"),
    )
    print(f"[INFO:{method_name}] Merged rows: {len(df)}")
    if len(df) == 0:
        raise RuntimeError(f"Merged dataframe is empty for {method_name}. Check item_id + variant matching.")

    df = add_binary_columns(df)
    df["_example_key"] = df["item_id"].astype(str) + "__v" + df["variant_idx"].astype(str)
    df["method"] = method_name
    return df


def analyze_one_method(method_name: str, df: pd.DataFrame, out_dir: Path, video_root: Path, detail_max_chars: int, excerpt_chars: int) -> pd.DataFrame:
    print(f"\n========== Selecting per-method examples: {method_name} ==========")
    method_out_dir = out_dir / method_name
    detail_dir = method_out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    compact_rows: List[dict] = []
    for axis in ["V", "AVB", "TC"]:
        print(f"\n[INFO:{method_name}] Selecting examples for axis={axis}")
        print(df[f"{axis}_error_type"].value_counts(dropna=False).to_string())
        selected = select_examples_for_axis(df, axis)
        for row in selected:
            detail_path = write_detail_file(row, method_name, axis, detail_dir, video_root, detail_max_chars)
            compact_rows.append(build_compact_row(row, method_name, axis, detail_path, video_root, excerpt_chars))

    compact = pd.DataFrame(compact_rows)
    csv_path = method_out_dir / f"{method_name}_V_AVB_TC_qualitative_examples.csv"
    md_path = method_out_dir / f"{method_name}_V_AVB_TC_qualitative_examples.md"
    compact.to_csv(csv_path, index=False)
    write_markdown_summary(compact_rows, md_path, f"Qualitative examples: {method_name}")

    print(f"\n[SAVED:{method_name}] compact CSV: {csv_path}")
    print(f"[SAVED:{method_name}] markdown summary: {md_path}")
    print(f"[SAVED:{method_name}] detail files: {detail_dir}")
    return compact


def prefix_method_df(df: pd.DataFrame, method_name: str) -> pd.DataFrame:
    """Prepare a method dataframe for no_tool vs tool transition analysis."""
    keep = [
        "item_id", "variant_idx", "video_id", "variant", "Failure reason",
        "video_relpath", "modality_combination", "temporal_type", "observed_behavior_summary",
        "overall_reason", "pose_evidence_mode", "mediapipe_hint_used", "mediapipe_error",
        "user_prompt", "mediapipe_summary", "raw_output", "_example_key",
    ]
    for axis, info in AXES.items():
        keep.extend([
            f"human_{axis}", f"pred_{axis}", f"{axis}_error_type", f"{axis}_match",
            info["pred_col"], info["reason_col"], info["evidence_col"],
        ])
    keep = [c for c in keep if c in df.columns]
    small = df[keep].copy()
    rename = {c: f"{method_name}__{c}" for c in small.columns if c not in ["item_id", "variant_idx"]}
    return small.rename(columns=rename)


def transition_quality_score(candidates: pd.DataFrame, axis: str, method_name: str) -> pd.Series:
    info = AXES[axis]
    base_reason_col = f"no_tool__{info['reason_col']}"
    tool_reason_col = f"{method_name}__{info['reason_col']}"
    base_ev_col = f"no_tool__{info['evidence_col']}"
    tool_ev_col = f"{method_name}__{info['evidence_col']}"
    mp_col = f"{method_name}__mediapipe_summary"

    base_reason = candidates.get(base_reason_col, pd.Series("", index=candidates.index)).fillna("").astype(str)
    tool_reason = candidates.get(tool_reason_col, pd.Series("", index=candidates.index)).fillna("").astype(str)
    base_ev = candidates.get(base_ev_col, pd.Series("", index=candidates.index)).fillna("").astype(str)
    tool_ev = candidates.get(tool_ev_col, pd.Series("", index=candidates.index)).fillna("").astype(str)
    mp = candidates.get(mp_col, pd.Series("", index=candidates.index)).fillna("").astype(str)
    return (
        base_reason.str.len().clip(upper=400)
        + tool_reason.str.len().clip(upper=500)
        + base_ev.str.len().clip(upper=500)
        + tool_ev.str.len().clip(upper=700)
        + (mp.str.len() > 0).astype(int) * 100
    )


def select_transition_one(candidates: pd.DataFrame, axis: str, method_name: str, selected_keys: set) -> Optional[pd.Series]:
    rows = select_transition_many(candidates, axis, method_name, selected_keys, max_examples=1)
    return rows[0] if rows else None


def select_transition_many(
    candidates: pd.DataFrame,
    axis: str,
    method_name: str,
    selected_keys: set,
    max_examples: int = 0,
) -> List[pd.Series]:
    """Select multiple transition examples.

    max_examples <= 0 means keep all remaining candidates. The caller's selected_keys
    set is updated in-place, so the same video is not selected twice within an axis.
    """
    if candidates.empty:
        return []

    candidates = candidates.copy()
    key_col = f"{method_name}___example_key"
    if key_col in candidates.columns:
        candidates = candidates[~candidates[key_col].isin(selected_keys)]
    if candidates.empty:
        return []

    candidates["_transition_score"] = transition_quality_score(candidates, axis, method_name)
    sort_cols = ["_transition_score", "item_id", "variant_idx"]
    ascending = [False, True, True]
    ranked = candidates.sort_values(sort_cols, ascending=ascending)

    if max_examples and max_examples > 0:
        ranked = ranked.head(max_examples)

    rows: List[pd.Series] = []
    for _, row in ranked.iterrows():
        key = get_value(row, key_col, f"{row['item_id']}__v{row['variant_idx']}")
        if key in selected_keys:
            continue
        selected_keys.add(key)
        rows.append(row)
    return rows


def build_transition_compact_row(row: pd.Series, method_name: str, axis: str, transition_kind: str, detail_path: Path, video_root: Path, excerpt_chars: int) -> dict:
    info = AXES[axis]
    no_tool_reason = get_value(row, f"no_tool__{info['reason_col']}", "")
    tool_reason = get_value(row, f"{method_name}__{info['reason_col']}", "")
    no_tool_evidence = get_value(row, f"no_tool__{info['evidence_col']}", "")
    tool_evidence = get_value(row, f"{method_name}__{info['evidence_col']}", "")

    # Prefer tool video_relpath; no_tool may not have it depending on the old CSV.
    video_relpath = get_value(row, f"{method_name}__video_relpath", "") or get_value(row, "no_tool__video_relpath", "")
    temp_row = pd.Series({
        "video_relpath": video_relpath,
        "item_id": row["item_id"],
        "variant_idx": row["variant_idx"],
    })

    return {
        "comparison": f"{method_name}_vs_no_tool",
        "axis": axis,
        "transition_kind": transition_kind,
        "item_id": row["item_id"],
        "variant_idx": row["variant_idx"],
        "video_id": get_value(row, f"{method_name}__video_id", get_value(row, "no_tool__video_id", "")),
        "variant": get_value(row, f"{method_name}__variant", get_value(row, "no_tool__variant", "")),
        "full_video_path": build_video_path(temp_row, video_root),
        "human_label": get_value(row, f"{method_name}__human_{axis}", get_value(row, f"no_tool__human_{axis}", np.nan)),
        "no_tool_label": get_value(row, f"no_tool__pred_{axis}", np.nan),
        "tool_label": get_value(row, f"{method_name}__pred_{axis}", np.nan),
        "no_tool_error_type": get_value(row, f"no_tool__{axis}_error_type", ""),
        "tool_error_type": get_value(row, f"{method_name}__{axis}_error_type", ""),
        "modality_combination": get_value(row, f"{method_name}__modality_combination", get_value(row, "no_tool__modality_combination", "")),
        "temporal_type": get_value(row, f"{method_name}__temporal_type", get_value(row, "no_tool__temporal_type", "")),
        "human_failure_reason": get_value(row, f"{method_name}__Failure reason", get_value(row, "no_tool__Failure reason", "")),
        "no_tool_reason_excerpt": truncate_text(no_tool_reason, excerpt_chars),
        "no_tool_evidence_excerpt": truncate_text(no_tool_evidence, excerpt_chars),
        "tool_reason_excerpt": truncate_text(tool_reason, excerpt_chars),
        "tool_evidence_excerpt": truncate_text(tool_evidence, excerpt_chars),
        "tool_pose_evidence_mode": get_value(row, f"{method_name}__pose_evidence_mode", ""),
        "tool_mediapipe_hint_used": get_value(row, f"{method_name}__mediapipe_hint_used", ""),
        "tool_mediapipe_error": get_value(row, f"{method_name}__mediapipe_error", ""),
        "detail_file": str(detail_path),
    }


def write_transition_detail_file(row: pd.Series, method_name: str, axis: str, transition_kind: str, detail_dir: Path, video_root: Path, max_chars: int) -> Path:
    info = AXES[axis]
    item_id = row["item_id"]
    variant_idx = row["variant_idx"]
    fname = safe_filename(f"{method_name}_vs_no_tool_{axis}_{transition_kind}_{item_id}_v{variant_idx}.txt")
    path = detail_dir / fname

    video_relpath = get_value(row, f"{method_name}__video_relpath", "") or get_value(row, "no_tool__video_relpath", "")
    temp_row = pd.Series({"video_relpath": video_relpath, "item_id": item_id, "variant_idx": variant_idx})

    sections = [
        ("COMPARISON", f"{method_name} vs no_tool"),
        ("AXIS", axis),
        ("TRANSITION_KIND", transition_kind),
        ("ITEM_ID", item_id),
        ("VARIANT_IDX", variant_idx),
        ("FULL_VIDEO_PATH", build_video_path(temp_row, video_root)),
        ("HUMAN_LABEL", get_value(row, f"{method_name}__human_{axis}", get_value(row, f"no_tool__human_{axis}", np.nan))),
        ("NO_TOOL_LABEL", get_value(row, f"no_tool__pred_{axis}", np.nan)),
        ("TOOL_LABEL", get_value(row, f"{method_name}__pred_{axis}", np.nan)),
        ("NO_TOOL_ERROR_TYPE", get_value(row, f"no_tool__{axis}_error_type", "")),
        ("TOOL_ERROR_TYPE", get_value(row, f"{method_name}__{axis}_error_type", "")),
        ("MODALITY_COMBINATION", get_value(row, f"{method_name}__modality_combination", get_value(row, "no_tool__modality_combination", ""))),
        ("TEMPORAL_TYPE", get_value(row, f"{method_name}__temporal_type", get_value(row, "no_tool__temporal_type", ""))),
        ("HUMAN_FAILURE_REASON", get_value(row, f"{method_name}__Failure reason", get_value(row, "no_tool__Failure reason", ""))),
        ("NO_TOOL_AXIS_LABEL_RAW", get_value(row, f"no_tool__{info['pred_col']}", "")),
        ("NO_TOOL_AXIS_REASON", get_value(row, f"no_tool__{info['reason_col']}", "")),
        ("NO_TOOL_AXIS_EVIDENCE", get_value(row, f"no_tool__{info['evidence_col']}", "")),
        ("NO_TOOL_OBSERVED_BEHAVIOR_SUMMARY", get_value(row, "no_tool__observed_behavior_summary", "")),
        ("NO_TOOL_OVERALL_REASON", get_value(row, "no_tool__overall_reason", "")),
        ("TOOL_AXIS_LABEL_RAW", get_value(row, f"{method_name}__{info['pred_col']}", "")),
        ("TOOL_AXIS_REASON", get_value(row, f"{method_name}__{info['reason_col']}", "")),
        ("TOOL_AXIS_EVIDENCE", get_value(row, f"{method_name}__{info['evidence_col']}", "")),
        ("TOOL_OBSERVED_BEHAVIOR_SUMMARY", get_value(row, f"{method_name}__observed_behavior_summary", "")),
        ("TOOL_OVERALL_REASON", get_value(row, f"{method_name}__overall_reason", "")),
        ("TOOL_POSE_EVIDENCE_MODE", get_value(row, f"{method_name}__pose_evidence_mode", "")),
        ("TOOL_MEDIAPIPE_HINT_USED", get_value(row, f"{method_name}__mediapipe_hint_used", "")),
        ("TOOL_MEDIAPIPE_ERROR", get_value(row, f"{method_name}__mediapipe_error", "")),
        ("TOOL_USER_PROMPT_SENT_TO_GEMINI", get_value(row, f"{method_name}__user_prompt", "")),
        ("TOOL_MEDIAPIPE_SUMMARY", get_value(row, f"{method_name}__mediapipe_summary", "")),
        ("TOOL_RAW_GEMINI_OUTPUT", get_value(row, f"{method_name}__raw_output", "")),
    ]

    lines = []
    for title, value in sections:
        lines.append("=" * 100)
        lines.append(str(title))
        lines.append("=" * 100)
        lines.append(truncate_text(value, max_chars))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def analyze_transitions_vs_no_tool(
    no_tool_df: pd.DataFrame,
    method_name: str,
    method_df: pd.DataFrame,
    out_dir: Path,
    video_root: Path,
    detail_max_chars: int,
    excerpt_chars: int,
    max_transition_examples_per_type: int,
    max_transition_fallback_examples: int,
) -> pd.DataFrame:
    print(f"\n========== Transition analysis: {method_name} vs no_tool ==========")
    no_tool_small = prefix_method_df(no_tool_df, "no_tool")
    method_small = prefix_method_df(method_df, method_name)
    wide = no_tool_small.merge(method_small, on=["item_id", "variant_idx"], how="inner")
    print(f"[INFO:{method_name}_vs_no_tool] Common rows: {len(wide)}")

    transition_out_dir = out_dir / f"{method_name}_vs_no_tool"
    detail_dir = transition_out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)

    compact_rows: List[dict] = []
    all_selected_keys: set = set()

    for axis in ["V", "AVB", "TC"]:
        base_match = wide[f"no_tool__{axis}_match"]
        tool_match = wide[f"{method_name}__{axis}_match"]
        improved = wide[(base_match == False) & (tool_match == True)].copy()  # noqa: E712
        degraded = wide[(base_match == True) & (tool_match == False)].copy()  # noqa: E712

        print(f"\n[INFO:{method_name}_vs_no_tool] axis={axis}")
        print(f"  improved no_tool wrong -> {method_name} correct: {len(improved)}")
        print(f"  degraded no_tool correct -> {method_name} wrong: {len(degraded)}")

        # Prefer interpretable transition types.
        transition_specs = [
            ("improved_FP_to_TN", improved[(improved[f"no_tool__{axis}_error_type"] == "FP") & (improved[f"{method_name}__{axis}_error_type"] == "TN")]),
            ("improved_FN_to_TP", improved[(improved[f"no_tool__{axis}_error_type"] == "FN") & (improved[f"{method_name}__{axis}_error_type"] == "TP")]),
            ("degraded_TN_to_FP", degraded[(degraded[f"no_tool__{axis}_error_type"] == "TN") & (degraded[f"{method_name}__{axis}_error_type"] == "FP")]),
            ("degraded_TP_to_FN", degraded[(degraded[f"no_tool__{axis}_error_type"] == "TP") & (degraded[f"{method_name}__{axis}_error_type"] == "FN")]),
        ]

        selected_for_axis: List[tuple[str, pd.Series]] = []
        selected_keys: set = set()
        for transition_kind, subset in transition_specs:
            rows = select_transition_many(
                subset,
                axis,
                method_name,
                selected_keys,
                max_examples=max_transition_examples_per_type,
            )
            selected_for_axis.extend((transition_kind, row) for row in rows)

        # Ensure improved/degraded examples are still saved even if an unexpected
        # error-type combination appears. This fallback also saves multiple rows.
        if not any(k.startswith("improved") for k, _ in selected_for_axis):
            rows = select_transition_many(
                improved,
                axis,
                method_name,
                selected_keys,
                max_examples=max_transition_fallback_examples,
            )
            selected_for_axis.extend(("improved_any", row) for row in rows)
        if not any(k.startswith("degraded") for k, _ in selected_for_axis):
            rows = select_transition_many(
                degraded,
                axis,
                method_name,
                selected_keys,
                max_examples=max_transition_fallback_examples,
            )
            selected_for_axis.extend(("degraded_any", row) for row in rows)

        for transition_kind, row in selected_for_axis:
            global_key = (axis, transition_kind, row["item_id"], row["variant_idx"])
            if global_key in all_selected_keys:
                continue
            all_selected_keys.add(global_key)
            detail_path = write_transition_detail_file(row, method_name, axis, transition_kind, detail_dir, video_root, detail_max_chars)
            compact_rows.append(build_transition_compact_row(row, method_name, axis, transition_kind, detail_path, video_root, excerpt_chars))

    compact = pd.DataFrame(compact_rows)
    csv_path = transition_out_dir / f"{method_name}_vs_no_tool_V_AVB_TC_transitions.csv"
    md_path = transition_out_dir / f"{method_name}_vs_no_tool_V_AVB_TC_transitions.md"
    compact.to_csv(csv_path, index=False)
    write_transition_markdown(compact_rows, md_path, method_name)

    print(f"\n[SAVED:{method_name}_vs_no_tool] compact CSV: {csv_path}")
    print(f"[SAVED:{method_name}_vs_no_tool] markdown summary: {md_path}")
    print(f"[SAVED:{method_name}_vs_no_tool] detail files: {detail_dir}")
    return compact


def write_transition_markdown(rows: List[dict], out_path: Path, method_name: str) -> None:
    lines = [
        f"# Transition examples: {method_name} vs no_tool",
        "",
        "Improved = no_tool was wrong but the tool method matches human GT.",
        "Degraded = no_tool matched human GT but the tool method is wrong.",
        "",
    ]
    for axis in ["V", "AVB", "TC"]:
        lines.append(f"## {axis}")
        lines.append("")
        for r in [x for x in rows if x["axis"] == axis]:
            lines.append(f"### {r['transition_kind']} — {r['item_id']} v{r['variant_idx']}")
            lines.append("")
            lines.append(f"- Human label: `{r['human_label']}`")
            lines.append(f"- No-tool label: `{r['no_tool_label']}` ({r['no_tool_error_type']})")
            lines.append(f"- {method_name} label: `{r['tool_label']}` ({r['tool_error_type']})")
            lines.append(f"- Video: `{r['full_video_path']}`")
            lines.append(f"- Modality: `{r['modality_combination']}`")
            lines.append(f"- Temporal type: `{r['temporal_type']}`")
            if r.get("human_failure_reason"):
                lines.append(f"- Human failure reason: {r['human_failure_reason']}")
            lines.append(f"- No-tool reason: {r['no_tool_reason_excerpt']}")
            lines.append(f"- {method_name} reason: {r['tool_reason_excerpt']}")
            lines.append(f"- {method_name} evidence: {r['tool_evidence_excerpt']}")
            lines.append(f"- Detail file: `{r['detail_file']}`")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if not args.human_path.exists():
        raise FileNotFoundError(f"Missing human GT CSV: {args.human_path}")

    human = pd.read_csv(args.human_path)
    print(f"[INFO] Human rows: {len(human)}")
    print(f"[INFO] Output dir: {args.out_dir}")

    required_human_cols = ["video_id", "item_id", "variant", "V", "AVB", "TC"]
    for col in required_human_cols:
        if col not in human.columns:
            raise ValueError(f"Human CSV missing column: {col}. Columns: {human.columns.tolist()}")

    method_specs = [
        ("no_tool", args.no_tool_path),
        ("raw", args.raw_path),
        ("focused_raw", args.focused_raw_path),
    ]

    method_dfs = {}
    per_method_compacts = []
    for method_name, path in method_specs:
        df = load_and_merge_method(method_name, path, human)
        method_dfs[method_name] = df
        compact = analyze_one_method(
            method_name=method_name,
            df=df,
            out_dir=args.out_dir,
            video_root=args.video_root,
            detail_max_chars=args.detail_max_chars,
            excerpt_chars=args.excerpt_chars,
        )
        per_method_compacts.append(compact)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    combined_per_method = pd.concat(per_method_compacts, ignore_index=True)
    combined_per_method_path = args.out_dir / "combined_no_tool_raw_focused_raw_V_AVB_TC_qualitative_examples.csv"
    combined_per_method.to_csv(combined_per_method_path, index=False)
    print(f"\n[SAVED] combined per-method CSV: {combined_per_method_path}")

    transition_compacts = []
    for method_name in ["raw", "focused_raw"]:
        transition = analyze_transitions_vs_no_tool(
            no_tool_df=method_dfs["no_tool"],
            method_name=method_name,
            method_df=method_dfs[method_name],
            out_dir=args.out_dir,
            video_root=args.video_root,
            detail_max_chars=args.detail_max_chars,
            excerpt_chars=args.excerpt_chars,
            max_transition_examples_per_type=args.max_transition_examples_per_type,
            max_transition_fallback_examples=args.max_transition_fallback_examples,
        )
        transition_compacts.append(transition)

    combined_transition = pd.concat(transition_compacts, ignore_index=True)
    combined_transition_path = args.out_dir / "combined_raw_focused_raw_vs_no_tool_V_AVB_TC_transitions.csv"
    combined_transition.to_csv(combined_transition_path, index=False)
    print(f"[SAVED] combined transition CSV: {combined_transition_path}")


if __name__ == "__main__":
    main()
