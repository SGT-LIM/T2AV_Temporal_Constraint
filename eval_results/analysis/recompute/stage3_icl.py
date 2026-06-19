import pandas as pd
from common import *

pd.set_option("display.width", 220)

rows = []
merged_store = {}
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    for icl in [False, True]:
        pe, pi, dpe, dpi, missing = load_gemini_setting(model, "NoTools", icl=icl)
        pred = build_predictions(pe, pi)
        merged = merge_human_pred(human, pred)
        merged_store[(model, icl)] = merged
        mt = metrics_by_axis(merged)
        mt.insert(0, "icl", icl)
        mt.insert(0, "model", model)
        rows.append(mt)

m = pd.concat(rows, ignore_index=True)
m.to_csv("stage3_icl_metrics.csv", index=False)
print(m[m.axis != "MACRO"][["model", "icl", "axis", "n", "accuracy", "balanced_accuracy", "precision", "recall", "f1", "TP", "FP", "TN", "FN"]]
      .round(3).to_string(index=False))

# Items that flip from correct->incorrect or incorrect->correct between zero-shot and ICL
print("\n=== Flip analysis (NoTools zero-shot vs ICL), per axis ===")
for model in ["LTX", "MOVA"]:
    z = merged_store[(model, False)].copy()
    i = merged_store[(model, True)].copy()
    key = ["item_id", "event_id", "axis"]
    z2 = z.set_index(key)[["human_label", "pred_label"]].rename(columns={"pred_label": "zs_pred"})
    i2 = i.set_index(key)[["pred_label"]].rename(columns={"pred_label": "icl_pred"})
    j = z2.join(i2, how="inner")
    j["zs_correct"] = j["human_label"] == j["zs_pred"]
    j["icl_correct"] = j["human_label"] == j["icl_pred"]
    fixed = j[(~j.zs_correct) & (j.icl_correct)]
    broken = j[(j.zs_correct) & (~j.icl_correct)]
    print(f"{model}: fixed by ICL = {len(fixed)}, broken by ICL = {len(broken)}")
    print(" fixed by axis:", fixed.reset_index().groupby("axis").size().to_dict())
    print(" broken by axis:", broken.reset_index().groupby("axis").size().to_dict())
