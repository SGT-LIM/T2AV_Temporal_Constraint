import pandas as pd
from common import *

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)

all_rows = []
all_merged = {}
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    for setting in SETTINGS:
        pe, pi, dpe, dpi, missing = load_gemini_setting(model, setting)
        if missing:
            print(f"[WARN] {model}/{setting}: missing canonical items {missing}")
        pred = build_predictions(pe, pi)
        merged = merge_human_pred(human, pred)
        all_merged[(model, setting)] = merged
        mt = metrics_by_axis(merged)
        mt.insert(0, "setting", setting)
        mt.insert(0, "model", model)
        all_rows.append(mt)

metrics = pd.concat(all_rows, ignore_index=True)
metrics.to_csv("stage2_metrics_full.csv", index=False)

print("=== OVERALL + MACRO per model x setting ===")
print(metrics[metrics["axis"].isin(["OVERALL", "MACRO"])]
      [["model", "setting", "axis", "n", "accuracy", "balanced_accuracy", "precision", "recall", "f1"]]
      .round(3).to_string(index=False))

print("\n=== Per-axis (NoTools only) ===")
print(metrics[(metrics["setting"] == "NoTools") & (metrics["axis"] != "MACRO")]
      [["model", "axis", "n", "accuracy", "balanced_accuracy", "precision", "recall", "f1", "TP", "FP", "TN", "FN"]]
      .round(3).to_string(index=False))
