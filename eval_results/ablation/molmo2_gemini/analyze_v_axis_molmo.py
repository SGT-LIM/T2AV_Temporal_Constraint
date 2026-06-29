#!/usr/bin/env python3
"""
V-axis-only analysis for Molmo2 / Gemini visual-event correctness outputs.

This script compares visual_event_correctness against human GT.

It supports two prediction formats:
1) Existing Gemini per-event CSV:
   columns include: item_id, event_id, event_kind, axis, label

2) Molmo2 V-only CSV:
   columns include:
   item_id, event_id, event_kind, visual_event_correctness
   visual_event_correctness_reason, visual_event_correctness_evidence

Human GT:
   row_id format:
     <item_id>__<variant><event_or_relation>__<axis>
   Example:
     Si_So_rel_ord_SiSo__01event_1__V
   Required columns: row_id, human_label
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ===========================================================================
# CONFIG
# ===========================================================================
CONDITIONS: dict[str, dict] = {
    # Existing Gemini V-only / no-tool run.
    # For a normal Gemini evaluator run, point `per_event` to results_per_event.csv.
    "NoTools": {
        "label": "Gemini / NoTools",
        "item": None,
        "per_event": "/home/coder/T2AV/eval_results/gemini/Test_ltx_Vonly_Gemini/results_per_event.csv",
        "format": "gemini_per_event",
    },

    # Molmo2 V-only result file. This is the results.csv you showed.
    "Molmo2": {
        "label": "Molmo2 V-only",
        "item": "/home/coder/T2AV/eval_results/gemini/Test_ltx_Vonly_Molmo2/results.csv",
        "per_event": None,
        "format": "molmo_vonly",
    },
}

HUMAN_GT_FILES: list[str] = [
    "/home/coder/T2AV/eval_results/human/Test_ltx_converted.csv",
]

OUT_DIR = Path("./analysis_results_vonly")

CONDITION_ORDER = ["NoTools", "Molmo2"]
KIND_ORDER = ["speech", "silent_action", "sounding_action"]

_YES = {"yes", "y", "true", "1", "pass", "correct"}
_NO = {"no", "n", "false", "0", "fail", "incorrect"}


def norm_label(v):
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
    m = re.match(r"^(.*?)__(\d+)(event_\d+|relation)__(.+)$", str(rid))
    if not m:
        return (np.nan, np.nan, np.nan)
    item_id, _variant, ev, suffix = m.groups()
    return item_id, ev, suffix


def item_id_aliases(item_id: str) -> list[str]:
    """Return conservative aliases for old compact IDs vs prefixed output IDs.

    Example:
      clap_palm__open_palm_clap_rel_ord_x
    gives:
      clap_palm__open_palm_clap_rel_ord_x
      open_palm_clap_rel_ord_x

    This avoids empty merges when generated-video folders have an action prefix
    but the GT row_id uses the compact prompt item id.
    """
    s = str(item_id).strip()
    aliases = [s]
    if "__" in s:
        aliases.append(s.split("__", 1)[1])
    # de-duplicate while preserving order
    out = []
    seen = set()
    for a in aliases:
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def make_keys(item_id: str, ev: str, axis_suffix: str = "V") -> list[str]:
    return [f"{alias}|{ev}|{axis_suffix}" for alias in item_id_aliases(item_id)]


def load_human(paths: list[str]) -> pd.DataFrame:
    rows = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"[WARN] human GT not found, skipping: {p}")
            continue

        if path.suffix.lower() == ".csv":
            h = pd.read_csv(path)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            h = pd.read_excel(path, sheet_name="Annotation")
        else:
            raise ValueError(f"Unsupported human GT file type: {p}")

        if "row_id" not in h.columns or "human_label" not in h.columns:
            print(f"[WARN] {p} missing row_id/human_label; columns={list(h.columns)}")
            continue

        for _, r in h.iterrows():
            item_id, ev, axis = parse_row_id(r["row_id"])
            if axis != "V":
                continue
            human = norm_label(r["human_label"])
            if pd.isna(human):
                continue
            for key in make_keys(item_id, ev, "V"):
                rows.append({"key": key, "item_id": item_id, "event_id": ev, "axis_suffix": "V", "human": human})

    if not rows:
        sys.exit("[FATAL] no usable V-axis human GT rows found.")
    out = pd.DataFrame(rows).drop_duplicates(subset=["key"], keep="first")
    return out


def load_gemini_per_event(per_event_csv: str) -> pd.DataFrame:
    pe = pd.read_csv(per_event_csv)
    rows = []
    for _, r in pe.iterrows():
        if str(r.get("axis", "")) != "visual_event_correctness":
            continue
        pred = norm_label(r.get("label"))
        if pd.isna(pred):
            continue
        item_id = r.get("item_id")
        ev = r.get("event_id")
        kind = str(r.get("event_kind", ""))
        for key in make_keys(item_id, ev, "V"):
            rows.append({"key": key, "item_id": item_id, "event_id": ev, "kind": kind, "pred": pred})
    return pd.DataFrame(rows).drop_duplicates(subset=["key"], keep="first")


def load_molmo_vonly(item_csv: str) -> pd.DataFrame:
    m = pd.read_csv(item_csv)
    required = {"item_id", "event_id", "event_kind", "visual_event_correctness"}
    missing = required - set(m.columns)
    if missing:
        raise ValueError(f"Molmo V-only CSV missing columns: {sorted(missing)}")

    rows = []
    for _, r in m.iterrows():
        pred = norm_label(r.get("visual_event_correctness"))
        if pd.isna(pred):
            continue
        item_id = r.get("item_id")
        ev = r.get("event_id")
        kind = str(r.get("event_kind", ""))
        for key in make_keys(item_id, ev, "V"):
            rows.append({"key": key, "item_id": item_id, "event_id": ev, "kind": kind, "pred": pred})
    return pd.DataFrame(rows).drop_duplicates(subset=["key"], keep="first")


def load_predictions(cfg: dict) -> pd.DataFrame:
    fmt = cfg.get("format")
    if fmt == "molmo_vonly":
        path = cfg.get("item")
        if not path or not Path(path).exists():
            print(f"[WARN] Molmo result not found: {path}")
            return pd.DataFrame()
        return load_molmo_vonly(path)

    if fmt == "gemini_per_event":
        path = cfg.get("per_event")
        if not path or not Path(path).exists():
            print(f"[WARN] Gemini per_event result not found: {path}")
            return pd.DataFrame()
        return load_gemini_per_event(path)

    raise ValueError(f"Unknown condition format: {fmt}")


def merged_predictions(cond: str, human: pd.DataFrame) -> pd.DataFrame:
    pred = load_predictions(CONDITIONS[cond])
    if pred.empty:
        return pred
    merged = pred.merge(human[["key", "human"]], on="key", how="inner")
    if merged.empty:
        print(f"[WARN] {cond}: predictions loaded but no keys matched human GT.")
        print(f"       example pred keys: {pred['key'].head(5).tolist()}")
        print(f"       example human keys: {human['key'].head(5).tolist()}")
    return merged


def summarize_condition(cond: str, human: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    merged = merged_predictions(cond, human)
    if merged.empty:
        return {
            "condition": cond,
            "label": CONDITIONS[cond]["label"],
            "balanced_accuracy": np.nan,
            "accuracy": np.nan,
            "n": 0,
            "n_yes_gt": 0,
            "n_no_gt": 0,
            "one_class": False,
        }, pd.DataFrame()

    yt = merged.human.to_numpy()
    yp = merged.pred.to_numpy()
    bacc, ncls = balanced_accuracy(yt, yp)
    summary = {
        "condition": cond,
        "label": CONDITIONS[cond]["label"],
        "balanced_accuracy": bacc,
        "accuracy": float((yt == yp).mean()),
        "n": int(len(merged)),
        "n_yes_gt": int((yt == "yes").sum()),
        "n_no_gt": int((yt == "no").sum()),
        "one_class": ncls == 1,
    }

    kind_rows = []
    for kind in KIND_ORDER:
        sub = merged[merged.kind == kind]
        if sub.empty:
            kind_rows.append({
                "condition": cond, "kind": kind, "balanced_accuracy": np.nan,
                "accuracy": np.nan, "n": 0, "n_yes_gt": 0, "n_no_gt": 0,
                "one_class": False,
            })
            continue
        yt2 = sub.human.to_numpy()
        yp2 = sub.pred.to_numpy()
        bacc2, ncls2 = balanced_accuracy(yt2, yp2)
        kind_rows.append({
            "condition": cond,
            "kind": kind,
            "balanced_accuracy": bacc2,
            "accuracy": float((yt2 == yp2).mean()),
            "n": int(len(sub)),
            "n_yes_gt": int((yt2 == "yes").sum()),
            "n_no_gt": int((yt2 == "no").sum()),
            "one_class": ncls2 == 1,
        })

    return summary, pd.DataFrame(kind_rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    human = load_human(HUMAN_GT_FILES)
    print(f"[INFO] V-axis human GT rows/aliases: {len(human)}")

    summaries = []
    kind_frames = []
    merged_frames = []

    for cond in [c for c in CONDITION_ORDER if c in CONDITIONS]:
        summary, kind_df = summarize_condition(cond, human)
        summaries.append(summary)
        if not kind_df.empty:
            kind_frames.append(kind_df)
        merged = merged_predictions(cond, human)
        if not merged.empty:
            merged = merged.assign(condition=cond)
            merged_frames.append(merged)

    summary_df = pd.DataFrame(summaries)
    kind_df = pd.concat(kind_frames, ignore_index=True) if kind_frames else pd.DataFrame()
    merged_df = pd.concat(merged_frames, ignore_index=True) if merged_frames else pd.DataFrame()

    summary_df.to_csv(OUT_DIR / "v_axis_summary.csv", index=False)
    kind_df.to_csv(OUT_DIR / "v_axis_by_event_kind.csv", index=False)
    merged_df.to_csv(OUT_DIR / "v_axis_matched_predictions.csv", index=False)

    print("\n=== V-axis overall ===")
    print(summary_df[["condition", "balanced_accuracy", "accuracy", "n", "n_yes_gt", "n_no_gt", "one_class"]].to_string(index=False))

    if not kind_df.empty:
        print("\n=== V-axis by event kind ===")
        print(kind_df[["condition", "kind", "balanced_accuracy", "accuracy", "n", "n_yes_gt", "n_no_gt", "one_class"]].to_string(index=False))

    print(f"\n[OK] wrote outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
