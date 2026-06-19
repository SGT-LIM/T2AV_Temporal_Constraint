"""Shared loaders for the from-scratch T2AV metric recomputation.

Restricted strictly to the 20 relative-prompt ("_rel_") items per model.
CC is never scored against human GT (no human labels exist for CC).
"""
import re
import numpy as np
import pandas as pd
import openpyxl

ROOT = "/home/coder/T2AV/eval_results"
HUMAN = {
    "LTX": f"{ROOT}/human/YS_eval_annotation_ltx.xlsx",
    "MOVA": f"{ROOT}/human/YS_eval_annotation_mova.xlsx",
}
GEMINI_DIR = {
    "LTX": f"{ROOT}/gemini/LTX-2.3",
    "MOVA": f"{ROOT}/gemini/MOVA",
}
GEMINI_ICL_DIR = {
    "LTX": f"{ROOT}/gemini/LTX-ICL",
    "MOVA": f"{ROOT}/gemini/MOVA-ICL",
}

SETTINGS = ["NoTools", "MediaPipe", "Whisper", "CLAP",
            "MediaPipe_Whisper", "MediaPipe_CLAP", "Whisper_CLAP", "AllTools"]

YESNO_AXIS_MAP = {
    "audio_event_correctness": "A",
    "visual_event_correctness": "V",
    "audio_visual_binding": "AVB",
}
AXES_ORDER = ["A", "V", "AVB", "TC-Relation", "TC-Count"]


def load_human(model):
    wb = openpyxl.load_workbook(HUMAN[model], data_only=True)
    ws = wb["Annotation"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    df = pd.DataFrame(rows[1:], columns=header)
    df = df.dropna(subset=["human_label"]).copy()
    df["item_id"] = df["row_id"].str.extract(r"^(.*?)__")[0]
    df["event_id"] = df["row_id"].str.extract(r"(event_\d+)")[0]
    df["human_label"] = df["human_label"].astype(str).str.strip().str.lower()

    def kind(s):
        s = str(s).lower()
        for k in ("silent action", "sounding action", "speech"):
            if k in s:
                return k.replace(" ", "_")
        return "relation"
    df["event_kind"] = df["event"].map(kind)
    df["model"] = model
    return df


def canonical_items(model):
    """The 20 relative-prompt item_ids for this model, taken from human GT (authoritative)."""
    h = load_human(model)
    items = sorted(h["item_id"].dropna().unique())
    assert len(items) == 20, f"{model}: expected 20 canonical items, got {len(items)}: {items}"
    assert all("_abs_" not in i for i in items), f"{model}: an 'abs' item leaked into canonical set: {items}"
    return set(items)


def load_gemini_setting(model, setting, icl=False):
    """Return (per_event_df, per_item_df) restricted to the 20 canonical rel items."""
    base = GEMINI_ICL_DIR[model] if icl else GEMINI_DIR[model]
    pe = pd.read_csv(f"{base}/{setting}_per_event.csv")
    pi = pd.read_csv(f"{base}/{setting}.csv")
    items = canonical_items(model)
    dropped_pe = sorted(set(pe["item_id"]) - items)
    dropped_pi = sorted(set(pi["item_id"]) - items)
    pe = pe[pe["item_id"].isin(items)].copy()
    pi = pi[pi["item_id"].isin(items)].copy()
    missing = items - set(pi["item_id"])
    return pe, pi, dropped_pe, dropped_pi, missing


def gemini_yesno_predictions(pe_df):
    """A / V / AVB per-event yes/no predictions (AVB already precondition-gated upstream)."""
    g = pe_df[pe_df["axis"].isin(YESNO_AXIS_MAP)].copy()
    g["axis"] = g["axis"].map(YESNO_AXIS_MAP)
    g["pred_label"] = g["label"].astype(str).str.strip().str.lower()
    return g[["item_id", "event_id", "axis", "event_kind", "event_label", "pred_label", "reason", "evidence"]]


def gemini_tccount_predictions(pe_df):
    """TC-Count per-event yes/no, derived as count_correct AND preconditions_ok (matches harness logic)."""
    g = pe_df[pe_df["axis"] == "temporal_count_satisfaction"].copy()
    g["count_correct"] = g["count_correct"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])
    g["preconditions_ok"] = g["preconditions_ok"].astype(str).str.strip().str.lower().isin(["true", "1", "1.0"])
    g["pred_label"] = np.where(g["count_correct"] & g["preconditions_ok"], "yes", "no")
    g["axis"] = "TC-Count"
    return g[["item_id", "event_id", "axis", "event_kind", "event_label", "pred_label",
              "observed_count", "required_count", "reason", "evidence"]]


def gemini_relation_predictions(pi_df):
    g = pi_df[["item_id", "temporal_relation_satisfaction",
               "temporal_relation_satisfaction_reason", "temporal_relation_satisfaction_evidence"]].copy()
    g["axis"] = "TC-Relation"
    g["event_id"] = np.nan
    g["event_kind"] = "relation"
    g["event_label"] = "relation"
    g["pred_label"] = g["temporal_relation_satisfaction"].astype(str).str.strip().str.lower()
    g = g.rename(columns={"temporal_relation_satisfaction_reason": "reason",
                           "temporal_relation_satisfaction_evidence": "evidence"})
    return g[["item_id", "event_id", "axis", "event_kind", "event_label", "pred_label", "reason", "evidence"]]


def build_predictions(pe_df, pi_df):
    parts = [gemini_yesno_predictions(pe_df), gemini_tccount_predictions(pe_df), gemini_relation_predictions(pi_df)]
    return pd.concat(parts, ignore_index=True)


def merge_human_pred(human_df, pred_df):
    h_yn = human_df[human_df["axis"].isin(["A", "V", "AVB", "TC-Count"])]
    m1 = h_yn.merge(pred_df.drop(columns=["event_kind", "event_label"], errors="ignore"),
                     on=["item_id", "event_id", "axis"], how="left", suffixes=("", "_g"))
    h_rel = human_df[human_df["axis"] == "TC-Relation"]
    m2 = h_rel.merge(pred_df[pred_df["axis"] == "TC-Relation"].drop(columns=["event_id", "event_kind", "event_label"]),
                      on=["item_id", "axis"], how="left", suffixes=("", "_g"))
    m = pd.concat([m1, m2], ignore_index=True)
    m["match"] = m["human_label"] == m["pred_label"]
    return m


def confusion_metrics(df, label_col="pred_label"):
    d = df.dropna(subset=[label_col])
    yt, yp = d["human_label"], d[label_col]
    tp = int(((yt == "yes") & (yp == "yes")).sum())
    fn = int(((yt == "yes") & (yp == "no")).sum())
    tn = int(((yt == "no") & (yp == "no")).sum())
    fp = int(((yt == "no") & (yp == "yes")).sum())
    n = len(d)
    n_pos, n_neg = tp + fn, tn + fp
    accuracy = (tp + tn) / n if n else np.nan
    recall = tp / n_pos if n_pos else np.nan          # = positive_recall = sensitivity
    specificity = tn / n_neg if n_neg else np.nan       # = negative_recall
    precision = tp / (tp + fp) if (tp + fp) else np.nan
    f1 = (2 * precision * recall / (precision + recall)
          if (precision and recall and not np.isnan(precision) and not np.isnan(recall) and (precision + recall) > 0)
          else np.nan)
    bacc = np.mean([recall, specificity]) if (n_pos and n_neg) else np.nan
    n_unmatched = int(df[label_col].isna().sum())
    return dict(n=n, n_pos=n_pos, n_neg=n_neg, TP=tp, FP=fp, TN=tn, FN=fn,
                accuracy=accuracy, balanced_accuracy=bacc, precision=precision,
                recall=recall, specificity=specificity, f1=f1, n_unmatched=n_unmatched)


def metrics_by_axis(merged_df):
    rows = []
    for ax in AXES_ORDER:
        sub = merged_df[merged_df["axis"] == ax]
        if len(sub) == 0:
            continue
        rows.append({"axis": ax, **confusion_metrics(sub)})
    overall = confusion_metrics(merged_df)
    rows.append({"axis": "OVERALL", **overall})
    per_axis = pd.DataFrame([r for r in rows if r["axis"] != "OVERALL"])
    macro = {"axis": "MACRO",
             "accuracy": per_axis["accuracy"].mean(),
             "balanced_accuracy": per_axis["balanced_accuracy"].mean(),
             "precision": per_axis["precision"].mean(),
             "recall": per_axis["recall"].mean(),
             "f1": per_axis["f1"].mean()}
    rows.append(macro)
    return pd.DataFrame(rows)
