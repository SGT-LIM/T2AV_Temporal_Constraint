import pandas as pd
from common import *

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 160)

def show(df, cols, n=15):
    print(df[cols].head(n).to_string(index=False))
    print(f"... n={len(df)} total\n")

# ---------------------------------------------------------------------
# 1) Hand-laterality disagreements on V / AVB for sounding_action events
# ---------------------------------------------------------------------
print("##### 1. Hand-laterality-flavoured V/AVB disagreements (NoTools) #####")
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    pe, pi, dpe, dpi, missing = load_gemini_setting(model, "NoTools")
    pred = build_predictions(pe, pi)
    merged = merge_human_pred(human, pred)
    sub = merged[(merged.axis.isin(["V", "AVB"])) & (merged.event_kind == "sounding_action") & (~merged.match)]
    sub = sub.copy()
    sub["mentions_hand"] = sub["reason"].astype(str).str.lower().str.contains("hand|side|left|right") | sub["evidence"].astype(str).str.lower().str.contains("hand|side|left|right")
    print(f"--- {model}: {len(sub)} V/AVB disagreements on sounding_action, {sub['mentions_hand'].sum()} mention hand/side/left/right ---")
    show(sub, ["item_id", "event_id", "axis", "human_label", "pred_label", "reason"], n=8)

# ---------------------------------------------------------------------
# 2) AVB false positives (gemini says yes, human says no) across all settings
# ---------------------------------------------------------------------
print("##### 2. AVB false positives (gemini=yes, human=no), all settings pooled #####")
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    fps = []
    for setting in SETTINGS:
        pe, pi, dpe, dpi, missing = load_gemini_setting(model, setting)
        pred = build_predictions(pe, pi)
        merged = merge_human_pred(human, pred)
        sub = merged[(merged.axis == "AVB") & (merged.human_label == "no") & (merged.pred_label == "yes")].copy()
        sub["setting"] = setting
        fps.append(sub)
    fps = pd.concat(fps, ignore_index=True)
    print(f"--- {model}: {len(fps)} AVB false-positive rows across 8 settings ---")
    print(fps.groupby(["item_id", "event_id"]).size().sort_values(ascending=False).head(10))
    show(fps.drop_duplicates(["item_id", "event_id"]), ["item_id", "event_id", "setting", "reason"], n=6)

# ---------------------------------------------------------------------
# 3) TC-Count failure patterns: signed bias direction by event_kind (NoTools)
# ---------------------------------------------------------------------
print("##### 3. TC-Count observed-vs-required mismatches (NoTools) #####")
for model in ["LTX", "MOVA"]:
    pe, pi, dpe, dpi, missing = load_gemini_setting(model, "NoTools")
    g = gemini_tccount_predictions(pe)
    mism = g[g["observed_count"] != g["required_count"]]
    print(f"--- {model}: {len(mism)}/{len(g)} events with observed != required ---")
    print(mism.groupby("event_kind").size())
    show(mism, ["item_id", "event_id", "event_kind", "event_label", "observed_count", "required_count"], n=10)

print("\nDone.")
