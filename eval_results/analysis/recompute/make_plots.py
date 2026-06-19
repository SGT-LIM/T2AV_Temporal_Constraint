import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

os.makedirs("plots", exist_ok=True)

AXES = ["A", "V", "AVB", "TC-Relation", "TC-Count"]
SETTINGS = ["NoTools", "MediaPipe", "Whisper", "CLAP",
            "MediaPipe_Whisper", "MediaPipe_CLAP", "Whisper_CLAP", "AllTools"]
MODEL_COLORS = {"LTX": "#2E7DAA", "MOVA": "#D9622B"}

m = pd.read_csv("stage2_metrics_full.csv")
icl = pd.read_csv("stage3_icl_metrics.csv")

# ---------------------------------------------------------------------------
# Plot 1: per-axis bar chart (NoTools baseline, both models, accuracy + bacc)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
base = m[(m.setting == "NoTools") & (m.axis.isin(AXES))]

for ax, metric, title in zip(axes, ["accuracy", "balanced_accuracy"], ["Accuracy", "Balanced Accuracy"]):
    x = np.arange(len(AXES))
    width = 0.35
    for i, model in enumerate(["LTX", "MOVA"]):
        sub = base[base.model == model].set_index("axis").reindex(AXES)
        vals = sub[metric].values
        bars = ax.bar(x + (i - 0.5) * width, vals, width, label=model, color=MODEL_COLORS[model])
        for xpos, v in zip(x + (i - 0.5) * width, vals):
            if not np.isnan(v):
                ax.text(xpos, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(AXES, rotation=20, ha="right")
    ax.set_title(f"{title} per axis (NoTools)")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.5, color="gray", linewidth=0.7, linestyle="--")
    ax.grid(axis="y", alpha=0.3)

axes[0].set_ylabel("Score")
axes[0].legend(title="Model")
fig.suptitle("Per-Axis Performance vs. Human GT (NoTools baseline, 20 rel-prompt items/model)", y=1.02)
fig.tight_layout()
fig.savefig("plots/01_per_axis_bar_chart.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("saved plots/01_per_axis_bar_chart.png")

# ---------------------------------------------------------------------------
# Plot 2: tool comparison (OVERALL bacc + accuracy, all 8 settings, both models)
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
overall = m[m.axis == "OVERALL"]

for ax, metric, title in zip(axes, ["balanced_accuracy", "accuracy"], ["OVERALL Balanced Accuracy", "OVERALL Accuracy"]):
    x = np.arange(len(SETTINGS))
    width = 0.35
    for i, model in enumerate(["LTX", "MOVA"]):
        sub = overall[overall.model == model].set_index("setting").reindex(SETTINGS)
        vals = sub[metric].values
        bars = ax.bar(x + (i - 0.5) * width, vals, width, label=model, color=MODEL_COLORS[model])
        for xpos, v in zip(x + (i - 0.5) * width, vals):
            if not np.isnan(v):
                ax.text(xpos, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_title(title)
    ax.set_ylim(0, 1.0)
    ax.grid(axis="y", alpha=0.3)
    ax.axhline(0.5, color="gray", linewidth=0.7, linestyle="--")

axes[0].legend(title="Model")
axes[1].set_xticks(x)
axes[1].set_xticklabels(SETTINGS, rotation=30, ha="right")
fig.suptitle("Tool-Setting Comparison: OVERALL Score vs. Human GT (8 settings, both models)", y=1.0)
fig.tight_layout()
fig.savefig("plots/02_tool_comparison.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("saved plots/02_tool_comparison.png")

# Per-axis x per-setting heatmap-style grouped bars (one figure per model) — supplementary detail
for model in ["LTX", "MOVA"]:
    fig, ax = plt.subplots(figsize=(13, 5))
    sub_all = m[(m.model == model) & (m.axis.isin(AXES))]
    x = np.arange(len(SETTINGS))
    width = 0.15
    cmap = plt.get_cmap("tab10")
    for j, axis_name in enumerate(AXES):
        sub = sub_all[sub_all.axis == axis_name].set_index("setting").reindex(SETTINGS)
        vals = sub["balanced_accuracy"].values
        ax.bar(x + (j - 2) * width, vals, width, label=axis_name, color=cmap(j))
    ax.set_xticks(x)
    ax.set_xticklabels(SETTINGS, rotation=30, ha="right")
    ax.set_ylabel("Balanced accuracy")
    ax.set_ylim(0, 1.05)
    ax.set_title(f"{model}: Balanced Accuracy per Axis across Tool Settings")
    ax.legend(title="Axis", ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"plots/02b_tool_comparison_by_axis_{model}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved plots/02b_tool_comparison_by_axis_{model}.png")

# ---------------------------------------------------------------------------
# Plot 3: ICL before/after, per axis, per model
# ---------------------------------------------------------------------------
fig, axes2 = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
icl_axes = AXES + ["OVERALL"]

for ax, model in zip(axes2, ["LTX", "MOVA"]):
    x = np.arange(len(icl_axes))
    width = 0.35
    for i, (icl_flag, label) in enumerate([(False, "Zero-shot (NoTools)"), (True, "ICL (1-shot)")]):
        sub = icl[(icl.model == model) & (icl.icl == icl_flag)].set_index("axis").reindex(icl_axes)
        vals = sub["balanced_accuracy"].values
        bars = ax.bar(x + (i - 0.5) * width, vals, width, label=label,
                       color="#999999" if not icl_flag else "#2E7DAA")
        for xpos, v in zip(x + (i - 0.5) * width, vals):
            if not np.isnan(v):
                ax.text(xpos, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(icl_axes, rotation=20, ha="right")
    ax.set_title(f"{model}: ICL vs Zero-shot (Balanced Accuracy)")
    ax.set_ylim(0, 1.05)
    ax.axhline(0.5, color="gray", linewidth=0.7, linestyle="--")
    ax.grid(axis="y", alpha=0.3)

axes2[0].set_ylabel("Balanced accuracy")
axes2[0].legend()
fig.suptitle("In-Context-Learning Effect: Zero-shot vs. 1-shot NoTools", y=1.03)
fig.tight_layout()
fig.savefig("plots/03_icl_before_after.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("saved plots/03_icl_before_after.png")

print("\nAll plots written to analysis/recompute/plots/")
