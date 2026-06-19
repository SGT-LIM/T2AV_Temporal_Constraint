import pandas as pd
from common import *

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 160)

# Errors introduced by a tool that NoTools got right (i.e. tool-specific damage)
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    pe0, pi0, *_ = load_gemini_setting(model, "NoTools")
    pred0 = build_predictions(pe0, pi0)
    base = merge_human_pred(human, pred0).set_index(["item_id", "event_id", "axis"])[["human_label", "pred_label"]]
    base = base.rename(columns={"pred_label": "notools_pred"})
    for setting in ["CLAP", "MediaPipe", "Whisper"]:
        pe, pi, *_ = load_gemini_setting(model, setting)
        pred = build_predictions(pe, pi)
        m = merge_human_pred(human, pred)
        j = m.set_index(["item_id", "event_id", "axis"])[["pred_label", "reason", "evidence", "event_kind"]].join(base, how="inner")
        j["notools_correct"] = j["human_label"] == j["notools_pred"]
        j["tool_correct"] = j["human_label"] == j["pred_label"]
        newly_broken = j[(j.notools_correct) & (~j.tool_correct)]
        print(f"--- {model}/{setting}: {len(newly_broken)} rows newly WRONG vs NoTools (NoTools was right) ---")
        print(newly_broken.reset_index().groupby(["axis", "event_kind"]).size())
    print()

print("\n##### Sample CLAP-introduced errors with evidence text #####")
for model in ["LTX", "MOVA"]:
    human = load_human(model)
    pe0, pi0, *_ = load_gemini_setting(model, "NoTools")
    pred0 = build_predictions(pe0, pi0)
    base = merge_human_pred(human, pred0).set_index(["item_id", "event_id", "axis"])[["human_label", "pred_label"]].rename(columns={"pred_label": "notools_pred"})
    pe, pi, *_ = load_gemini_setting(model, "CLAP")
    pred = build_predictions(pe, pi)
    m = merge_human_pred(human, pred)
    j = m.set_index(["item_id", "event_id", "axis"])[["pred_label", "reason", "evidence"]].join(base, how="inner")
    j["notools_correct"] = j["human_label"] == j["notools_pred"]
    j["tool_correct"] = j["human_label"] == j["pred_label"]
    newly_broken = j[(j.notools_correct) & (~j.tool_correct) & (j.index.get_level_values("axis") == "A")]
    print(f"--- {model} ---")
    print(newly_broken.reset_index()[["item_id", "event_id", "human_label", "pred_label", "reason"]].head(6).to_string(index=False))
    print()
