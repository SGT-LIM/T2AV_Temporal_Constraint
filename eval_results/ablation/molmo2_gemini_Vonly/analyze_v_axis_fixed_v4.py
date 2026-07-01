#!/usr/bin/env python3
"""
Robust V-axis analysis for Gemini / Molmo2 outputs.

Fixes:
1) Supports row-level V-only CSVs:
   item_id,event_id,event_kind,visual_event_correctness
2) Supports item-level CSVs with visual_event_correctness_per_event
3) Supports item-level CSVs with raw_output JSON fallback
4) Uses item_id aliases ONLY for matching, not as extra samples.
   Therefore n = actual V-axis event instances, not duplicated alias rows.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# ===========================================================================
# DEFAULT CONFIG
# ===========================================================================
CONDITIONS = {
    "Gemini (Joint 5-axis Eval)": {
        "path": "/home/coder/T2AV/eval_results/gemini/Test_ltx_notool/results_8fps.csv",
    },
    "Gemini (V-only Eval, 24fps)": {
        "path": "/home/coder/T2AV/eval_results/gemini/Test_ltx_Vonly_Gemini/results_8fps.csv",
    },
    # If you saved the 8fps run elsewhere, either edit this path or pass:
    #   --add-condition "Gemini (V-only Eval, 8fps)=/path/to/results_8fps.csv"
    "Gemini (V-only Eval, 8fps)": {
        "path": "results_8fps.csv",
        "optional": True,
    },
    "Molmo2 (V-only Eval)": {
        "path": "/home/coder/T2AV/eval_results/gemini/Test_ltx_Vonly_Molmo2/results.csv",
    },
}

HUMAN_GT_FILES = [
    "/home/coder/T2AV/eval_results/human/Test_ltx_converted.csv",
]

OUT_DIR = Path("./analysis_results_vonly")

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


def norm_event_id(v):
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return ""
    m = re.search(r"event[_\s-]*(\d+)", s, flags=re.I)
    if m:
        return f"event_{int(m.group(1))}"
    if re.fullmatch(r"\d+", s):
        return f"event_{int(s)}"
    return s


def item_id_aliases(item_id: str) -> list[str]:
    """Aliases are used only for matching, never counted as separate samples."""
    s = str(item_id).strip()
    aliases = []
    if s:
        aliases.append(s)

    # Generated output folders often prepend an action-pair prefix:
    #   clap_palm__open_palm_clap_rel_ord_x
    # Human GT may use:
    #   open_palm_clap_rel_ord_x
    if "__" in s:
        aliases.append(s.split("__", 1)[1])

    # Occasionally video names include variant suffixes.
    s2 = re.sub(r"_v\d+_raw$", "", s)
    s2 = re.sub(r"_v\d+$", "", s2)
    if s2 and s2 != s:
        aliases.append(s2)
        if "__" in s2:
            aliases.append(s2.split("__", 1)[1])

    out, seen = [], set()
    for a in aliases:
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def make_alias_keys(item_id: str, event_id: str) -> list[str]:
    ev = norm_event_id(event_id)
    return [f"{a}|{ev}|V" for a in item_id_aliases(item_id)]


def parse_row_id(rid: str):
    m = re.match(r"^(.*?)__(\d+)(event_\d+|relation)__(.+)$", str(rid))
    if not m:
        return (np.nan, np.nan, np.nan)
    item_id, variant, ev, axis = m.groups()
    return item_id, norm_event_id(ev), axis


def balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray):
    recalls = []
    for c in ("yes", "no"):
        mask = y_true == c
        if int(mask.sum()) > 0:
            recalls.append(float((y_pred[mask] == c).mean()))
    if not recalls:
        return float("nan"), 0
    return float(np.mean(recalls)), len(recalls)


def read_csv_or_excel(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name="Annotation")
    raise ValueError(f"Unsupported file type: {path}")


def load_human(paths: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    alias_rows = []
    obs_i = 0

    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"[WARN] human GT not found, skipping: {path}")
            continue
        h = read_csv_or_excel(path)

        if "row_id" not in h.columns or "human_label" not in h.columns:
            print(f"[WARN] {path} missing row_id/human_label; columns={list(h.columns)}")
            continue

        for _, r in h.iterrows():
            item_id, ev, axis = parse_row_id(r["row_id"])
            if axis != "V":
                continue
            human = norm_label(r["human_label"])
            if pd.isna(human):
                continue

            obs_id = f"h{obs_i}"
            obs_i += 1
            rows.append({
                "human_obs_id": obs_id,
                "item_id_human": item_id,
                "event_id": ev,
                "human": human,
                "row_id": r["row_id"],
            })
            for key in make_alias_keys(item_id, ev):
                alias_rows.append({"human_obs_id": obs_id, "key": key})

    if not rows:
        sys.exit("[FATAL] no usable V-axis human GT rows found.")

    human = pd.DataFrame(rows).drop_duplicates(subset=["human_obs_id"])
    human_alias = pd.DataFrame(alias_rows).drop_duplicates(subset=["human_obs_id", "key"])
    return human, human_alias


def safe_json_loads(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if isinstance(x, dict):
        return x
    s = str(x).strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        return ast.literal_eval(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", s, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            try:
                return ast.literal_eval(m.group(0))
            except Exception:
                return None
    return None


def per_event_list_from_cell(cell):
    obj = safe_json_loads(cell)
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if "per_event" in obj and isinstance(obj["per_event"], list):
            return obj["per_event"]
        if "visual_event_correctness" in obj:
            inner = obj.get("visual_event_correctness")
            if isinstance(inner, dict) and isinstance(inner.get("per_event"), list):
                return inner["per_event"]
    return []


def infer_item_id_from_row(r):
    if "item_id" in r and pd.notna(r.get("item_id")):
        return str(r.get("item_id"))
    if "video_relpath" in r and pd.notna(r.get("video_relpath")):
        # parent directory is usually the item_id
        return Path(str(r.get("video_relpath"))).parent.name
    if "video_file" in r and pd.notna(r.get("video_file")):
        s = Path(str(r.get("video_file"))).stem
        s = re.sub(r"_v\d+_raw$", "", s)
        s = re.sub(r"_v\d+$", "", s)
        return s
    return ""


def load_predictions(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path)
    rows = []
    pred_i = 0

    def add_pred(item_id, ev, kind, label, reason="", evidence=""):
        nonlocal pred_i
        ev = norm_event_id(ev)
        pred = norm_label(label)
        if not item_id or not ev or pd.isna(pred):
            return
        rows.append({
            "pred_obs_id": f"p{pred_i}",
            "item_id_pred": str(item_id),
            "event_id": ev,
            "kind": str(kind) if kind is not None and not pd.isna(kind) else "",
            "pred": pred,
            "reason": reason,
            "evidence": evidence,
        })
        pred_i += 1

    cols = set(df.columns)

    # Case 1: already one row per event.
    if {"item_id", "event_id", "visual_event_correctness"}.issubset(cols):
        for _, r in df.iterrows():
            add_pred(
                r.get("item_id"),
                r.get("event_id"),
                r.get("event_kind", ""),
                r.get("visual_event_correctness"),
                r.get("visual_event_correctness_reason", ""),
                r.get("visual_event_correctness_evidence", ""),
            )

    # Case 2: long Gemini per-event format.
    elif {"item_id", "event_id", "axis", "label"}.issubset(cols):
        sub = df[df["axis"].astype(str) == "visual_event_correctness"]
        for _, r in sub.iterrows():
            add_pred(
                r.get("item_id"),
                r.get("event_id"),
                r.get("event_kind", ""),
                r.get("label"),
                r.get("reason", ""),
                r.get("evidence", ""),
            )

    # Case 3: item-level with per-event JSON-like column.
    elif "visual_event_correctness_per_event" in cols:
        for _, r in df.iterrows():
            item_id = infer_item_id_from_row(r)
            events = per_event_list_from_cell(r.get("visual_event_correctness_per_event"))
            for evr in events:
                add_pred(
                    item_id,
                    evr.get("event_id", ""),
                    evr.get("event_kind", ""),
                    evr.get("label", ""),
                    evr.get("reason", ""),
                    evr.get("evidence", ""),
                )

    # Case 4: item-level raw_output JSON fallback.
    elif "raw_output" in cols:
        for _, r in df.iterrows():
            item_id = infer_item_id_from_row(r)
            events = per_event_list_from_cell(r.get("raw_output"))
            for evr in events:
                add_pred(
                    item_id,
                    evr.get("event_id", ""),
                    evr.get("event_kind", ""),
                    evr.get("label", ""),
                    evr.get("reason", ""),
                    evr.get("evidence", ""),
                )

    else:
        raise ValueError(f"{path} has unsupported columns: {list(df.columns)}")

    pred = pd.DataFrame(rows).drop_duplicates(subset=["item_id_pred", "event_id"], keep="first")
    alias_rows = []
    for _, r in pred.iterrows():
        for key in make_alias_keys(r["item_id_pred"], r["event_id"]):
            alias_rows.append({"pred_obs_id": r["pred_obs_id"], "key": key})
    pred_alias = pd.DataFrame(alias_rows).drop_duplicates(subset=["pred_obs_id", "key"])

    print(f"[INFO] loaded predictions from {path}: raw_rows={len(df)}, event_rows={len(pred)}")
    if len(pred) == 0:
        print(f"[WARN] no usable predictions. columns={list(df.columns)}")
        if "visual_event_correctness" in df.columns:
            print("[DEBUG] visual_event_correctness value counts:")
            print(df["visual_event_correctness"].value_counts(dropna=False).to_string())

    return pred, pred_alias


def match_predictions(pred, pred_alias, human, human_alias, cond):
    if pred.empty:
        return pd.DataFrame()

    pairs = pred_alias.merge(human_alias, on="key", how="inner")
    if pairs.empty:
        print(f"[WARN] {cond}: no alias keys matched.")
        print(f"       pred key examples: {pred_alias['key'].head(5).tolist() if not pred_alias.empty else []}")
        print(f"       human key examples: {human_alias['key'].head(5).tolist() if not human_alias.empty else []}")
        return pd.DataFrame()

    # Alias keys can produce duplicate matches. Collapse to one true event match.
    pairs = pairs.drop_duplicates(subset=["pred_obs_id", "human_obs_id"])
    # If a prediction somehow matches multiple human rows, keep first and warn.
    dup_pred = pairs[pairs.duplicated("pred_obs_id", keep=False)]
    dup_human = pairs[pairs.duplicated("human_obs_id", keep=False)]
    if not dup_pred.empty or not dup_human.empty:
        print(f"[WARN] {cond}: duplicate alias matches found; collapsing to one-to-one.")
    pairs = pairs.drop_duplicates(subset=["pred_obs_id"], keep="first")
    pairs = pairs.drop_duplicates(subset=["human_obs_id"], keep="first")

    out = (
        pairs
        .merge(pred, on="pred_obs_id", how="left")
        .merge(human, on="human_obs_id", how="left")
    )
    out["condition"] = cond

    print(f"[INFO] {cond}: pred_events={len(pred)}, matched_events={len(out)}, human_events={len(human)}")

    if len(out) < len(human):
        missing = human[~human["human_obs_id"].isin(set(out["human_obs_id"]))]
        print(f"[WARN] {cond}: {len(missing)} human events unmatched.")
        print("       missing examples:", missing[["item_id_human", "event_id"]].head(5).to_dict("records"))

    return out


def summarize(merged: pd.DataFrame, cond: str):
    if merged.empty:
        return {
            "condition": cond, "balanced_accuracy": np.nan, "accuracy": np.nan,
            "n": 0, "n_yes_gt": 0, "n_no_gt": 0, "one_class": False,
        }, []

    yt = merged["human"].to_numpy()
    yp = merged["pred"].to_numpy()
    bacc, ncls = balanced_accuracy(yt, yp)
    summary = {
        "condition": cond,
        "balanced_accuracy": bacc,
        "accuracy": float((yt == yp).mean()),
        "n": int(len(merged)),
        "n_yes_gt": int((yt == "yes").sum()),
        "n_no_gt": int((yt == "no").sum()),
        "one_class": ncls == 1,
    }

    kind_rows = []
    kinds = KIND_ORDER + sorted(set(merged["kind"].dropna().astype(str)) - set(KIND_ORDER) - {""})
    for kind in kinds:
        sub = merged[merged["kind"] == kind]
        if sub.empty:
            continue
        yt2 = sub["human"].to_numpy()
        yp2 = sub["pred"].to_numpy()
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

    return summary, kind_rows


def parse_add_condition(s: str):
    if "=" not in s:
        raise argparse.ArgumentTypeError("Use NAME=/path/to/results.csv")
    name, path = s.split("=", 1)
    return name.strip(), path.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human-gt", action="append", default=None,
                    help="Human GT CSV/XLSX. Can be repeated. Defaults to Test_ltx_converted.csv.")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--add-condition", action="append", type=parse_add_condition, default=[],
                    help='Add/override condition as "Name=/path/to/results.csv"')
    ap.add_argument("--only", nargs="*", default=None,
                    help="Run only these condition names.")
    args = ap.parse_args()

    conditions = dict(CONDITIONS)
    for name, path in args.add_condition:
        conditions[name] = {"path": path}

    if args.only:
        conditions = {k: v for k, v in conditions.items() if k in set(args.only)}

    human_paths = args.human_gt if args.human_gt else HUMAN_GT_FILES
    human, human_alias = load_human(human_paths)
    print(f"[INFO] V-axis human GT event rows: {len(human)}")
    print(f"[INFO] V-axis human alias keys: {len(human_alias)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    kind_rows_all = []
    merged_all = []

    for cond, cfg in conditions.items():
        path = Path(cfg["path"])
        if not path.exists():
            if cfg.get("optional", False):
                print(f"[SKIP] optional condition file not found: {cond}: {path}")
                continue
            print(f"[WARN] condition file not found: {cond}: {path}")
            summary_rows.append({
                "condition": cond, "balanced_accuracy": np.nan, "accuracy": np.nan,
                "n": 0, "n_yes_gt": 0, "n_no_gt": 0, "one_class": False,
            })
            continue

        pred, pred_alias = load_predictions(path)
        merged = match_predictions(pred, pred_alias, human, human_alias, cond)
        summary, kind_rows = summarize(merged, cond)
        summary_rows.append(summary)
        kind_rows_all.extend(kind_rows)
        if not merged.empty:
            merged_all.append(merged)

    summary_df = pd.DataFrame(summary_rows)
    kind_df = pd.DataFrame(kind_rows_all)
    merged_df = pd.concat(merged_all, ignore_index=True) if merged_all else pd.DataFrame()

    summary_df.to_csv(args.out_dir / "v_axis_summary.csv", index=False)
    kind_df.to_csv(args.out_dir / "v_axis_by_event_kind.csv", index=False)
    merged_df.to_csv(args.out_dir / "v_axis_matched_predictions.csv", index=False)

    print("\n=== V-axis overall ===")
    cols = ["condition", "balanced_accuracy", "accuracy", "n", "n_yes_gt", "n_no_gt", "one_class"]
    print(summary_df[cols].to_string(index=False))

    if not kind_df.empty:
        print("\n=== V-axis by event kind ===")
        cols2 = ["condition", "kind", "balanced_accuracy", "accuracy", "n", "n_yes_gt", "n_no_gt", "one_class"]
        print(kind_df[cols2].to_string(index=False))

    print(f"\n[OK] wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()
