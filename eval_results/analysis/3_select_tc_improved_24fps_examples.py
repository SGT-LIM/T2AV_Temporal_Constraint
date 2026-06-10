#!/usr/bin/env python3
"""
Select qualitative TC examples that improved when using media_fps=24.

This compares two per-video Gemini evaluation CSVs against the same human GT:
  - baseline / non-24fps result CSV
  - 24fps result CSV

It extracts videos where TC was wrong in the baseline but correct at 24fps,
plus optional degraded cases. It saves:
  1) compact CSV of improved cases
  2) compact CSV of degraded cases
  3) group summary CSV
  4) Markdown summary
  5) per-example detail .txt files containing old/new reasons, evidence, prompt, etc.

Expected columns:
Human GT CSV:
  - item_id
  - variant   e.g. v1, v2, v3
  - TC        0/1, yes/no, true/false
  - optional: video_id, Failure reason, prompt

Gemini result CSVs:
  - item_id
  - variant_index
  - temporal_constraint_satisfaction
  - temporal_constraint_satisfaction_reason
  - temporal_constraint_satisfaction_evidence
  - optional: video_relpath, video_file, modality_combination, temporal_type,
              observed_behavior_summary, overall_reason, user_prompt, raw_output,
              media_fps, pose_evidence_mode, mediapipe_summary

Example:
python select_tc_improved_24fps_examples.py \
  --human-path /home/coder/T2V_Gen/Gemini/human_eval_GT/human_FIVE_axis_labels.csv \
  --baseline-path /home/coder/T2V_Gen/Gemini/eval_output_tool_focused_raw/results.csv \
  --fps24-path /home/coder/T2V_Gen/Gemini/eval_output_tool_focused_raw/results_Gemini24fps.csv \
  --video-root /home/coder/T2V_Gen/LTX-2/outputs \
  --out-dir /home/coder/T2V_Gen/Gemini/human_eval_GT/compare_results_focused_raw/analysis_tc_24fps_improvements
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional, List, Dict

import numpy as np
import pandas as pd

TC_INFO = {
    "human_col": "TC",
    "pred_col": "temporal_constraint_satisfaction",
    "reason_col": "temporal_constraint_satisfaction_reason",
    "evidence_col": "temporal_constraint_satisfaction_evidence",
}

LONG_COLUMNS = [
    "user_prompt",
    "mediapipe_summary",
    "raw_output",
    "observed_behavior_summary",
    "overall_reason",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--human-path", type=Path, required=True)
    p.add_argument("--baseline-path", type=Path, required=True, help="Per-video evaluation CSV for old/non-24fps setting")
    p.add_argument("--fps24-path", type=Path, required=True, help="Per-video evaluation CSV for media_fps=24 setting")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--video-root", type=Path, default=None)
    p.add_argument("--baseline-name", type=str, default="baseline")
    p.add_argument("--fps24-name", type=str, default="fps24")
    p.add_argument("--excerpt-chars", type=int, default=1800)
    p.add_argument("--detail-max-chars", type=int, default=60000)
    p.add_argument("--max-improved", type=int, default=0, help="0 = save all improved examples")
    p.add_argument("--max-degraded", type=int, default=0, help="0 = save all degraded examples")
    p.add_argument("--include-stable", action="store_true", help="Also save stable correct/wrong CSVs")
    return p.parse_args()


def to_binary(x) -> float:
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    if s in {"1", "y", "yes", "true", "t"}:
        return 1.0
    if s in {"0", "n", "no", "false", "f"}:
        return 0.0
    return np.nan


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def truncate_text(x, max_chars: int) -> str:
    text = clean_text(x)
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [TRUNCATED to {max_chars} chars]"


def safe_filename(text: str, max_len: int = 180) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(text))
    return text[:max_len].strip("_") or "example"


def infer_variant_idx_from_variant(x) -> pd.Series:
    s = x.astype(str).str.extract(r"(\d+)")[0]
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def infer_variant_idx_from_gemini(df: pd.DataFrame) -> pd.Series:
    if "variant_index" in df.columns:
        return pd.to_numeric(df["variant_index"], errors="coerce").astype("Int64")
    if "video_file" in df.columns:
        s = df["video_file"].astype(str).str.extract(r"_v(\d+)(?:_raw)?\.mp4")[0]
        return pd.to_numeric(s, errors="coerce").astype("Int64")
    if "video_relpath" in df.columns:
        s = df["video_relpath"].astype(str).str.extract(r"_v(\d+)(?:_raw)?\.mp4")[0]
        return pd.to_numeric(s, errors="coerce").astype("Int64")
    raise ValueError("Gemini CSV must contain variant_index, video_file, or video_relpath.")


def normalize_human(human: pd.DataFrame) -> pd.DataFrame:
    if "item_id" not in human.columns or "variant" not in human.columns or TC_INFO["human_col"] not in human.columns:
        raise ValueError(
            f"Human CSV must contain item_id, variant, and {TC_INFO['human_col']}. "
            f"Columns: {human.columns.tolist()}"
        )
    h = human.copy()
    h["item_id"] = h["item_id"].astype(str).str.strip()
    h["variant_idx"] = infer_variant_idx_from_variant(h["variant"])
    h["human_TC"] = h[TC_INFO["human_col"]].map(to_binary)
    return h


def validate_gemini(df: pd.DataFrame, name: str) -> None:
    required = ["item_id", TC_INFO["pred_col"], TC_INFO["reason_col"], TC_INFO["evidence_col"]]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name} CSV is missing required per-video columns: {missing}.\n"
            f"This script needs per-video result CSVs, not aggregate tc_detailed_analysis CSVs.\n"
            f"Columns found: {df.columns.tolist()}"
        )


def normalize_gemini(gemini: pd.DataFrame, name: str) -> pd.DataFrame:
    validate_gemini(gemini, name)
    g = gemini.copy()
    g["_original_row_order"] = np.arange(len(g))
    g["item_id"] = g["item_id"].astype(str).str.strip()
    g["variant_idx"] = infer_variant_idx_from_gemini(g)

    before = len(g)
    if "video_relpath" in g.columns:
        g = g.sort_values("_original_row_order").drop_duplicates(subset=["video_relpath"], keep="last")
    else:
        g = g.sort_values("_original_row_order").drop_duplicates(subset=["item_id", "variant_idx"], keep="last")
    after = len(g)
    if after < before:
        print(f"[WARN:{name}] Deduplicated rows: {before} -> {after}")

    g[f"pred_TC__{name}"] = g[TC_INFO["pred_col"]].map(to_binary)
    g[f"TC_reason__{name}"] = g[TC_INFO["reason_col"]].fillna("").astype(str)
    g[f"TC_evidence__{name}"] = g[TC_INFO["evidence_col"]].fillna("").astype(str)
    return g


def error_type(human: float, pred: float) -> str:
    if pd.isna(human) or pd.isna(pred):
        return "NA"
    if human == 1 and pred == 1:
        return "TP"
    if human == 0 and pred == 0:
        return "TN"
    if human == 0 and pred == 1:
        return "FP"
    if human == 1 and pred == 0:
        return "FN"
    return "NA"


def match_bool(human: float, pred: float) -> bool:
    if pd.isna(human) or pd.isna(pred):
        return False
    return bool(human == pred)


def prefix_columns(df: pd.DataFrame, name: str) -> pd.DataFrame:
    keep = [
        "item_id", "variant_idx", "video_relpath", "video_file", "label_name", "label_type",
        "modality_combination", "event_summary", "temporal_type", "overall_temporal_success",
        "overall_reason", "observed_behavior_summary", "model", "media_fps", "thinking_level",
        "pose_evidence_mode", "mediapipe_hint_used", "mediapipe_fps", "mediapipe_error",
        "mediapipe_summary", "user_prompt", "raw_output",
        TC_INFO["pred_col"], TC_INFO["reason_col"], TC_INFO["evidence_col"],
        f"pred_TC__{name}", f"TC_reason__{name}", f"TC_evidence__{name}",
    ]
    keep = [c for c in keep if c in df.columns]
    small = df[keep].copy()
    rename = {c: f"{name}__{c}" for c in small.columns if c not in ["item_id", "variant_idx"]}
    return small.rename(columns=rename)


def build_video_path(row: pd.Series, video_root: Optional[Path], fps24_name: str, baseline_name: str) -> str:
    if video_root is None:
        return ""
    rel = clean_text(row.get(f"{fps24_name}__video_relpath", "")) or clean_text(row.get(f"{baseline_name}__video_relpath", ""))
    if rel:
        return str(video_root / rel)
    item_id = clean_text(row.get("item_id", ""))
    variant_idx = row.get("variant_idx", "")
    if item_id and pd.notna(variant_idx):
        return str(video_root / item_id / f"{item_id}_v{int(variant_idx)}_raw.mp4")
    return ""


def transition_kind(base_err: str, fps24_err: str) -> str:
    if base_err == "FP" and fps24_err == "TN":
        return "improved_FP_to_TN"
    if base_err == "FN" and fps24_err == "TP":
        return "improved_FN_to_TP"
    if base_err == "TN" and fps24_err == "FP":
        return "degraded_TN_to_FP"
    if base_err == "TP" and fps24_err == "FN":
        return "degraded_TP_to_FN"
    if base_err in {"FP", "FN"} and fps24_err in {"TP", "TN"}:
        return "improved_other"
    if base_err in {"TP", "TN"} and fps24_err in {"FP", "FN"}:
        return "degraded_other"
    if base_err in {"TP", "TN"} and fps24_err in {"TP", "TN"}:
        return "stable_correct"
    if base_err in {"FP", "FN"} and fps24_err in {"FP", "FN"}:
        return "stable_wrong"
    return "NA"


def quality_score(df: pd.DataFrame, baseline_name: str, fps24_name: str) -> pd.Series:
    # Prefer examples with rich rationales and where 24fps reason/evidence differs from baseline.
    base_reason = df.get(f"{baseline_name}__TC_reason__{baseline_name}", pd.Series("", index=df.index)).fillna("").astype(str)
    fps_reason = df.get(f"{fps24_name}__TC_reason__{fps24_name}", pd.Series("", index=df.index)).fillna("").astype(str)
    base_ev = df.get(f"{baseline_name}__TC_evidence__{baseline_name}", pd.Series("", index=df.index)).fillna("").astype(str)
    fps_ev = df.get(f"{fps24_name}__TC_evidence__{fps24_name}", pd.Series("", index=df.index)).fillna("").astype(str)
    obs = df.get(f"{fps24_name}__observed_behavior_summary", pd.Series("", index=df.index)).fillna("").astype(str)
    diff_bonus = ((base_reason != fps_reason) | (base_ev != fps_ev)).astype(int) * 200
    return (
        fps_reason.str.len().clip(upper=700)
        + fps_ev.str.len().clip(upper=900)
        + obs.str.len().clip(upper=300)
        + diff_bonus
    )


def compact_row(row: pd.Series, baseline_name: str, fps24_name: str, detail_file: Path, video_root: Optional[Path], excerpt_chars: int) -> dict:
    base_pred = row.get(f"pred_TC__{baseline_name}", row.get(f"{baseline_name}__pred_TC__{baseline_name}", np.nan))
    fps_pred = row.get(f"pred_TC__{fps24_name}", row.get(f"{fps24_name}__pred_TC__{fps24_name}", np.nan))
    return {
        "transition_kind": row["transition_kind"],
        "item_id": row["item_id"],
        "variant_idx": row["variant_idx"],
        "video_id": row.get("video_id", ""),
        "variant": row.get("variant", ""),
        "full_video_path": build_video_path(row, video_root, fps24_name, baseline_name),
        "human_TC": row["human_TC"],
        "baseline_TC": base_pred,
        "fps24_TC": fps_pred,
        "baseline_error_type": row["baseline_error_type"],
        "fps24_error_type": row["fps24_error_type"],
        "modality_combination": clean_text(row.get(f"{fps24_name}__modality_combination", "")) or clean_text(row.get(f"{baseline_name}__modality_combination", "")),
        "temporal_type": clean_text(row.get(f"{fps24_name}__temporal_type", "")) or clean_text(row.get(f"{baseline_name}__temporal_type", "")),
        "human_failure_reason": clean_text(row.get("Failure reason", "")),
        "baseline_media_fps": clean_text(row.get(f"{baseline_name}__media_fps", "")),
        "fps24_media_fps": clean_text(row.get(f"{fps24_name}__media_fps", "")),
        "baseline_reason_excerpt": truncate_text(row.get(f"{baseline_name}__TC_reason__{baseline_name}", ""), excerpt_chars),
        "baseline_evidence_excerpt": truncate_text(row.get(f"{baseline_name}__TC_evidence__{baseline_name}", ""), excerpt_chars),
        "fps24_reason_excerpt": truncate_text(row.get(f"{fps24_name}__TC_reason__{fps24_name}", ""), excerpt_chars),
        "fps24_evidence_excerpt": truncate_text(row.get(f"{fps24_name}__TC_evidence__{fps24_name}", ""), excerpt_chars),
        "baseline_observed_excerpt": truncate_text(row.get(f"{baseline_name}__observed_behavior_summary", ""), excerpt_chars),
        "fps24_observed_excerpt": truncate_text(row.get(f"{fps24_name}__observed_behavior_summary", ""), excerpt_chars),
        "detail_file": str(detail_file),
    }


def write_detail(row: pd.Series, out_dir: Path, baseline_name: str, fps24_name: str, video_root: Optional[Path], max_chars: int) -> Path:
    detail_dir = out_dir / "details"
    detail_dir.mkdir(parents=True, exist_ok=True)
    fname = safe_filename(f"TC_{row['transition_kind']}_{row['item_id']}_v{row['variant_idx']}.txt")
    path = detail_dir / fname

    def g(col: str):
        return row.get(col, "")

    sections = [
        ("TRANSITION_KIND", row["transition_kind"]),
        ("ITEM_ID", row["item_id"]),
        ("VARIANT_IDX", row["variant_idx"]),
        ("FULL_VIDEO_PATH", build_video_path(row, video_root, fps24_name, baseline_name)),
        ("HUMAN_TC", row["human_TC"]),
        ("BASELINE_TC", row.get(f"{baseline_name}__pred_TC__{baseline_name}", "")),
        ("FPS24_TC", row.get(f"{fps24_name}__pred_TC__{fps24_name}", "")),
        ("BASELINE_ERROR_TYPE", row["baseline_error_type"]),
        ("FPS24_ERROR_TYPE", row["fps24_error_type"]),
        ("MODALITY_COMBINATION", clean_text(g(f"{fps24_name}__modality_combination")) or clean_text(g(f"{baseline_name}__modality_combination"))),
        ("TEMPORAL_TYPE", clean_text(g(f"{fps24_name}__temporal_type")) or clean_text(g(f"{baseline_name}__temporal_type"))),
        ("HUMAN_FAILURE_REASON", g("Failure reason")),
        ("BASELINE_MEDIA_FPS", g(f"{baseline_name}__media_fps")),
        ("FPS24_MEDIA_FPS", g(f"{fps24_name}__media_fps")),
        ("BASELINE_TC_LABEL_RAW", g(f"{baseline_name}__temporal_constraint_satisfaction")),
        ("BASELINE_TC_REASON", g(f"{baseline_name}__TC_reason__{baseline_name}")),
        ("BASELINE_TC_EVIDENCE", g(f"{baseline_name}__TC_evidence__{baseline_name}")),
        ("BASELINE_OBSERVED_BEHAVIOR_SUMMARY", g(f"{baseline_name}__observed_behavior_summary")),
        ("BASELINE_OVERALL_REASON", g(f"{baseline_name}__overall_reason")),
        ("FPS24_TC_LABEL_RAW", g(f"{fps24_name}__temporal_constraint_satisfaction")),
        ("FPS24_TC_REASON", g(f"{fps24_name}__TC_reason__{fps24_name}")),
        ("FPS24_TC_EVIDENCE", g(f"{fps24_name}__TC_evidence__{fps24_name}")),
        ("FPS24_OBSERVED_BEHAVIOR_SUMMARY", g(f"{fps24_name}__observed_behavior_summary")),
        ("FPS24_OVERALL_REASON", g(f"{fps24_name}__overall_reason")),
        ("USER_PROMPT_SENT_TO_GEMINI_FPS24", g(f"{fps24_name}__user_prompt")),
        ("USER_PROMPT_SENT_TO_GEMINI_BASELINE", g(f"{baseline_name}__user_prompt")),
        ("FPS24_RAW_OUTPUT", g(f"{fps24_name}__raw_output")),
        ("BASELINE_RAW_OUTPUT", g(f"{baseline_name}__raw_output")),
    ]
    lines = []
    for title, value in sections:
        lines += ["=" * 100, str(title), "=" * 100, truncate_text(value, max_chars), ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def markdown_summary(compact: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "# TC examples improved by 24fps",
        "",
        "Improved = baseline TC prediction was wrong against human GT, but 24fps TC prediction matches human GT.",
        "Degraded = baseline TC prediction matched human GT, but 24fps TC prediction became wrong.",
        "",
    ]
    for kind in ["improved_FN_to_TP", "improved_FP_to_TN", "improved_other", "degraded_TP_to_FN", "degraded_TN_to_FP", "degraded_other"]:
        sub = compact[compact["transition_kind"] == kind] if not compact.empty else pd.DataFrame()
        if sub.empty:
            continue
        lines.append(f"## {kind} ({len(sub)})")
        lines.append("")
        for _, r in sub.iterrows():
            lines.append(f"### {r['item_id']} v{r['variant_idx']} — {r['temporal_type']} / {r['modality_combination']}")
            lines.append("")
            lines.append(f"- Human TC: `{r['human_TC']}`")
            lines.append(f"- Baseline TC: `{r['baseline_TC']}` ({r['baseline_error_type']})")
            lines.append(f"- 24fps TC: `{r['fps24_TC']}` ({r['fps24_error_type']})")
            lines.append(f"- Video: `{r['full_video_path']}`")
            if r.get("human_failure_reason"):
                lines.append(f"- Human failure reason: {r['human_failure_reason']}")
            lines.append(f"- Baseline reason: {r['baseline_reason_excerpt']}")
            lines.append(f"- 24fps reason: {r['fps24_reason_excerpt']}")
            lines.append(f"- 24fps evidence: {r['fps24_evidence_excerpt']}")
            lines.append(f"- Detail file: `{r['detail_file']}`")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    human = pd.read_csv(args.human_path)
    baseline = pd.read_csv(args.baseline_path)
    fps24 = pd.read_csv(args.fps24_path)

    human = normalize_human(human)
    baseline = normalize_gemini(baseline, args.baseline_name)
    fps24 = normalize_gemini(fps24, args.fps24_name)

    base_small = prefix_columns(baseline, args.baseline_name)
    fps_small = prefix_columns(fps24, args.fps24_name)

    merged = human.merge(base_small, on=["item_id", "variant_idx"], how="inner")
    merged = merged.merge(fps_small, on=["item_id", "variant_idx"], how="inner")
    if merged.empty:
        raise RuntimeError("No overlapping rows after merging human, baseline, and 24fps CSVs. Check item_id/variant_idx.")

    merged["baseline_pred_TC"] = merged[f"{args.baseline_name}__pred_TC__{args.baseline_name}"]
    merged["fps24_pred_TC"] = merged[f"{args.fps24_name}__pred_TC__{args.fps24_name}"]
    merged["baseline_error_type"] = [error_type(h, p) for h, p in zip(merged["human_TC"], merged["baseline_pred_TC"])]
    merged["fps24_error_type"] = [error_type(h, p) for h, p in zip(merged["human_TC"], merged["fps24_pred_TC"])]
    merged["baseline_match"] = [match_bool(h, p) for h, p in zip(merged["human_TC"], merged["baseline_pred_TC"])]
    merged["fps24_match"] = [match_bool(h, p) for h, p in zip(merged["human_TC"], merged["fps24_pred_TC"])]
    merged["transition_kind"] = [transition_kind(b, f) for b, f in zip(merged["baseline_error_type"], merged["fps24_error_type"])]
    merged["quality_score"] = quality_score(merged, args.baseline_name, args.fps24_name)

    merged_path = args.out_dir / "tc_baseline_vs_24fps_all_merged.csv"
    merged.to_csv(merged_path, index=False)

    improved = merged[(merged["baseline_match"] == False) & (merged["fps24_match"] == True)].copy()  # noqa: E712
    degraded = merged[(merged["baseline_match"] == True) & (merged["fps24_match"] == False)].copy()  # noqa: E712
    stable_correct = merged[(merged["baseline_match"] == True) & (merged["fps24_match"] == True)].copy()  # noqa: E712
    stable_wrong = merged[(merged["baseline_match"] == False) & (merged["fps24_match"] == False)].copy()  # noqa: E712

    for df in [improved, degraded, stable_correct, stable_wrong]:
        if not df.empty:
            df.sort_values(["transition_kind", "quality_score", "item_id", "variant_idx"], ascending=[True, False, True, True], inplace=True)

    if args.max_improved and args.max_improved > 0:
        improved = improved.head(args.max_improved)
    if args.max_degraded and args.max_degraded > 0:
        degraded = degraded.head(args.max_degraded)

    compact_rows: List[Dict] = []
    for _, row in pd.concat([improved, degraded], ignore_index=True).iterrows():
        detail_path = write_detail(row, args.out_dir, args.baseline_name, args.fps24_name, args.video_root, args.detail_max_chars)
        compact_rows.append(compact_row(row, args.baseline_name, args.fps24_name, detail_path, args.video_root, args.excerpt_chars))

    compact = pd.DataFrame(compact_rows)
    compact_path = args.out_dir / "tc_24fps_improved_and_degraded_examples.csv"
    compact.to_csv(compact_path, index=False)
    markdown_summary(compact, args.out_dir / "tc_24fps_improved_and_degraded_examples.md")

    improved_path = args.out_dir / "tc_24fps_improved_examples.csv"
    degraded_path = args.out_dir / "tc_24fps_degraded_examples.csv"
    improved.to_csv(improved_path, index=False)
    degraded.to_csv(degraded_path, index=False)

    if args.include_stable:
        stable_correct.to_csv(args.out_dir / "tc_24fps_stable_correct.csv", index=False)
        stable_wrong.to_csv(args.out_dir / "tc_24fps_stable_wrong.csv", index=False)

    summary = []
    for name, df in [
        ("all", merged),
        ("improved", improved),
        ("degraded", degraded),
        ("stable_correct", stable_correct),
        ("stable_wrong", stable_wrong),
    ]:
        summary.append({"group": "overall", "value": name, "n": len(df)})
    for col in [f"{args.fps24_name}__temporal_type", f"{args.fps24_name}__modality_combination", "transition_kind"]:
        if col in merged.columns or col == "transition_kind":
            source = merged if col == "transition_kind" else merged.rename(columns={col: "tmp_col"})
            c = "transition_kind" if col == "transition_kind" else "tmp_col"
            for val, sub in source.groupby(c, dropna=False):
                summary.append({"group": col.replace(f"{args.fps24_name}__", ""), "value": val, "n": len(sub)})
    pd.DataFrame(summary).to_csv(args.out_dir / "tc_24fps_transition_summary.csv", index=False)

    print("\n[SAVED]")
    print(f"merged all rows: {merged_path}")
    print(f"compact examples: {compact_path}")
    print(f"improved full rows: {improved_path}")
    print(f"degraded full rows: {degraded_path}")
    print(f"markdown: {args.out_dir / 'tc_24fps_improved_and_degraded_examples.md'}")
    print(f"details dir: {args.out_dir / 'details'}")
    print("\n[COUNTS]")
    print(f"merged: {len(merged)}")
    print(f"improved: {len(improved)}")
    print(f"degraded: {len(degraded)}")
    print(f"stable_correct: {len(stable_correct)}")
    print(f"stable_wrong: {len(stable_wrong)}")
    print("\ntransition_kind counts:")
    print(merged["transition_kind"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
