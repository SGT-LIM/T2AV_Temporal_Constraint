import re
import numpy as np
import pandas as pd

# ======================
# PATHS
# ======================
HUMAN = "/home/coder/T2AV/eval_results/human/Test_ltx_converted.csv"

CONDITIONS = {
    "No Tools": "/home/coder/T2AV/eval_results/gemini/Test_ltx_notool/results_per_event.csv",
    "Mediapipe": "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results_per_event.csv",
    "Mediapipe_Input": "/home/coder/T2AV/eval_results/gemini/Test_ltx_mediapipe/results_use_mediapipe_as_inputvideo/results_per_event.csv",
}

AXIS_MAP = {
    "audio_event_correctness": "A",
    "visual_event_correctness": "V",
    "audio_visual_binding": "AVB",
    "temporal_count_satisfaction": "TC-Count",
}

KIND_ORDER = ["speech", "silent_action", "sounding_action"]
AXIS_ORDER = ["A", "V", "AVB", "TC-Count"]

YES = {"yes", "y", "true", "1", "pass", "correct"}
NO = {"no", "n", "false", "0", "fail", "incorrect"}

# ======================
# HELPERS
# ======================
def norm_label(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, bool):
        return "yes" if v else "no"
    s = str(v).strip().lower()
    if s in YES:
        return "yes"
    if s in NO:
        return "no"
    return np.nan

def balanced_accuracy(y_true, y_pred):
    recalls = []
    for c in ["yes", "no"]:
        mask = (y_true == c)
        if mask.sum() == 0:
            continue
        recalls.append((y_pred[mask] == c).mean())
    return np.mean(recalls)

def parse_row_id(rid):
    # item__01event_1__A
    m = re.match(r"^(.*?)__(\d+)(event_\d+|relation)__(.+)$", str(rid))
    if not m:
        return (None, None, None)
    item_id, _, ev, axis = m.groups()
    return item_id, ev, axis

# ======================
# LOAD HUMAN GT
# ======================
human = pd.read_csv(HUMAN)

parsed = human["row_id"].apply(parse_row_id)
human["item_id"] = [x[0] for x in parsed]
human["event_id"] = [x[1] for x in parsed]
human["axis"] = [x[2] for x in parsed]
human["gt"] = human["human_label"].map(norm_label)

human["key"] = (
    human["item_id"] + "|" +
    human["event_id"] + "|" +
    human["axis"]
)

human = human[["key", "gt"]].dropna()

# ======================
# ANALYZE EACH CONDITION
# ======================
records = []

for cond_name, path in CONDITIONS.items():
    df = pd.read_csv(path)

    df["axis_short"] = df["axis"].map(AXIS_MAP)

    def pred_from_row(r):
        if r["axis_short"] == "TC-Count":
            return norm_label(r["count_correct"])
        return norm_label(r["label"])

    df["pred"] = df.apply(pred_from_row, axis=1)

    df["key"] = (
        df["item_id"].astype(str) + "|" +
        df["event_id"].astype(str) + "|" +
        df["axis_short"].astype(str)
    )

    merged = df.merge(human, on="key", how="inner")

    for kind in KIND_ORDER:
        for axis in AXIS_ORDER:
            sub = merged[
                (merged["event_kind"] == kind) &
                (merged["axis_short"] == axis)
            ]

            if len(sub) == 0:
                continue

            ba = balanced_accuracy(
                sub["gt"].to_numpy(),
                sub["pred"].to_numpy()
            )

            records.append({
                "event_kind": kind,
                "axis": axis,
                "condition": cond_name,
                "balanced_accuracy": ba
            })

result = pd.DataFrame(records)

# ======================
# TABLE
# ======================
pivot = result.pivot_table(
    index=["event_kind", "axis"],
    columns="condition",
    values="balanced_accuracy"
)

print(pivot.round(2))
pivot.to_csv("per_event_kind_axis_balanced_accuracy.csv")