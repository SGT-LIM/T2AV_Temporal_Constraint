#!/usr/bin/env python3
"""
Batch-evaluate MANY Gemini conditions against one human GT.

Layout: per condition, a pair of files in --indir
    <COND>_per_event*.csv   (per-event: A / V / AVB / TC-Count)
    <COND>*.csv             (per-item : TC-Relation)
Trailing download junk like " (3)" / "__3_" is stripped automatically.

Two comparison modes:
  * yes/no axes  (A, V, AVB, TC-Relation)  -> accuracy / balanced accuracy
  * TC-Count     (numeric)                 -> compare observed counts directly:
        exact-match rate, MAE, signed bias (gemini - human; + = Gemini over-counts)

Outputs (in --outdir):
  metrics_long.csv             condition x {A,V,AVB,TC-Relation,OVERALL,MACRO}
  bacc_heatmap.png             condition x axis balanced accuracy
  agreement_by_eventkind.csv   yes/no axes: condition x axis x event_kind agreement
  eventkind_heatmap.png
  disagreements.csv            yes/no mismatches (human_label vs gem_label + reason)
  count_metrics.csv            condition x event_kind: exact_match, MAE, signed_bias
  count_eventkind_heatmap.png  count exact-match rate (event_kind x condition)
  count_disagreements.csv      count mismatches: human_count vs gemini_count + diff
"""

import argparse, glob, os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

YESNO_AXIS_MAP = {
    "audio_event_correctness":  "A",
    "visual_event_correctness": "V",
    "audio_visual_binding":     "AVB",
}
COUNT_GEMINI_AXIS = "temporal_count_satisfaction"
RELATION_HUMAN_AXIS, RELATION_GEMINI_COL = "TC-Relation", "temporal_relation_satisfaction"
YESNO_AXES = ["A", "V", "AVB", "TC-Relation"]
POS, NEG = "yes", "no"


# ------------------------------------------------------------------ loaders
def load_human(xlsx_path):
    h = pd.read_excel(xlsx_path, sheet_name="Annotation").dropna(subset=["human_label"]).copy()
    h["item_id"] = h["row_id"].str.extract(r"^(.*?)__")[0]
    h["event_id"] = h["row_id"].str.extract(r"(event_\d+)")[0]
    h["human_label"] = h["human_label"].astype(str).str.strip().str.lower()
    def kind(s):
        s = str(s).lower()
        for k in ("silent action", "sounding action", "speech"):
            if k in s: return k.replace(" ", "_")
        return "relation"
    h["event_kind_h"] = h["event"].map(kind)
    return h


def load_gemini_yesno(csv_path):
    g = pd.read_csv(csv_path)
    g = g[g["axis"].isin(YESNO_AXIS_MAP)].copy()
    g["axis"] = g["axis"].map(YESNO_AXIS_MAP)
    g["gem_label"] = g["label"].astype(str).str.strip().str.lower()
    cols = ["item_id", "event_id", "axis", "event_kind", "event_label",
            "gem_label", "reason", "evidence"]
    return g[[c for c in cols if c in g.columns]]


def load_gemini_count(csv_path):
    g = pd.read_csv(csv_path)
    g = g[g["axis"] == COUNT_GEMINI_AXIS].copy()
    keep = ["item_id", "event_id", "event_kind", "event_label",
            "observed_count", "required_count", "reason", "evidence"]
    g = g[[c for c in keep if c in g.columns]].rename(
        columns={"observed_count": "gem_count", "reason": "reason", "evidence": "evidence"})
    return g


def load_gemini_relation(csv_path):
    gi = pd.read_csv(csv_path)
    if RELATION_GEMINI_COL not in gi.columns:
        return None
    rel = gi[["item_id", RELATION_GEMINI_COL]].copy()
    rel["axis"] = RELATION_HUMAN_AXIS
    rel["event_id"] = np.nan
    rel["event_kind"] = "relation"
    rel["event_label"] = "relation"
    rel = rel.rename(columns={RELATION_GEMINI_COL: "gem_label"})
    rel["gem_label"] = rel["gem_label"].astype(str).str.strip().str.lower()
    for src, dst in [("temporal_relation_satisfaction_reason", "reason"),
                     ("temporal_relation_satisfaction_evidence", "evidence")]:
        rel[dst] = gi[src] if src in gi.columns else ""
    return rel


# ------------------------------------------------------------------ merges
def merge_yesno(human, gem_yesno, gem_rel):
    he = human[human["axis"].isin(["A", "V", "AVB"])]
    m1 = he.merge(gem_yesno, on=["item_id", "event_id", "axis"], how="left", suffixes=("", "_g"))
    parts = [m1]
    if gem_rel is not None:
        hr = human[human["axis"] == RELATION_HUMAN_AXIS]
        m2 = hr.merge(gem_rel.drop(columns=["event_id"]), on=["item_id", "axis"],
                      how="left", suffixes=("", "_g"))
        parts.append(m2)
    m = pd.concat(parts, ignore_index=True)
    m["event_kind"] = m["event_kind"].fillna(m["event_kind_h"])
    m["match"] = m["human_label"] == m["gem_label"]
    return m


def merge_count(human, gem_count):
    hc = human[human["axis"] == "TC-Count"].copy()
    hc = hc.rename(columns={"human_observed_count": "human_count"})
    m = hc.merge(gem_count, on=["item_id", "event_id"], how="left", suffixes=("", "_g"))
    m["event_kind"] = m["event_kind"].fillna(m["event_kind_h"])
    m = m.dropna(subset=["human_count", "gem_count"])
    m["human_count"] = m["human_count"].astype(int)
    m["gem_count"] = m["gem_count"].astype(int)
    m["exact"] = m["human_count"] == m["gem_count"]
    m["diff"] = m["gem_count"] - m["human_count"]   # + = Gemini over-counts
    return m


# ------------------------------------------------------------------ metrics
def metrics_for(df):
    d = df.dropna(subset=["gem_label"])
    yt, yp = d["human_label"], d["gem_label"]
    tp = int(((yt == POS) & (yp == POS)).sum()); fn = int(((yt == POS) & (yp == NEG)).sum())
    tn = int(((yt == NEG) & (yp == NEG)).sum()); fp = int(((yt == NEG) & (yp == POS)).sum())
    n = len(d); n_pos, n_neg = tp + fn, tn + fp
    acc = (tp + tn) / n if n else np.nan
    pr = tp / n_pos if n_pos else np.nan
    nr = tn / n_neg if n_neg else np.nan
    bacc = np.mean([pr, nr]) if (n_pos and n_neg) else np.nan
    return dict(n=n, n_pos=n_pos, n_neg=n_neg, TP=tp, FN=fn, TN=tn, FP=fp,
                accuracy=acc, balanced_accuracy=bacc,
                positive_recall=pr, negative_recall=nr,
                n_unmatched=int(df["gem_label"].isna().sum()))


def metrics_table(m, cond):
    rows = [{"condition": cond, "axis": ax, **metrics_for(m[m["axis"] == ax])}
            for ax in YESNO_AXES if (m["axis"] == ax).any()]
    rows.append({"condition": cond, "axis": "OVERALL", **metrics_for(m)})
    per = pd.DataFrame([r for r in rows if r["axis"] in YESNO_AXES])
    rows.append({"condition": cond, "axis": "MACRO",
                 "accuracy": per["accuracy"].mean(),
                 "balanced_accuracy": per["balanced_accuracy"].mean()})
    return pd.DataFrame(rows)


def eventkind_agreement(m, cond):
    d = m.dropna(subset=["gem_label"])
    return pd.DataFrame([
        dict(condition=cond, axis=ax, event_kind=ek, n=len(s),
             n_disagree=int((~s["match"]).sum()), agreement_rate=s["match"].mean())
        for (ax, ek), s in d.groupby(["axis", "event_kind"])])


def count_metrics(mc, cond):
    def block(s, ek):
        return dict(condition=cond, event_kind=ek, n=len(s),
                    exact_match_rate=s["exact"].mean(),
                    MAE=s["diff"].abs().mean(),
                    signed_bias=s["diff"].mean())   # + = Gemini over-counts
    rows = [block(mc, "ALL")]
    for ek, s in mc.groupby("event_kind"):
        rows.append(block(s, ek))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ misc
def discover_conditions(indir):
    def cond_name(stem):
        c = stem.replace("_per_event", "")
        return re.sub(r"[\s_]*\(?\d+\)?[\s_]*$", "", c)
    conds = {}
    for p in sorted(glob.glob(os.path.join(indir, "*.csv"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        slot = "per_event" if "_per_event" in stem else "per_item"
        conds.setdefault(cond_name(stem), {}).setdefault(slot, p)
    return conds


def heatmap(df, index, col, val, title, out_png, order=None, fmt="{:.2f}"):
    piv = df.pivot_table(index=index, columns=col, values=val, aggfunc="mean")
    if order: piv = piv.reindex(columns=[c for c in order if c in piv.columns])
    fig, ax = plt.subplots(figsize=(1.4 + 1.1*len(piv.columns), 1.0 + .5*len(piv.index)))
    im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(piv.index)));   ax.set_yticklabels(piv.index)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v): ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=9)
    ax.set_title(title); fig.colorbar(im, ax=ax, fraction=.046, pad=.04)
    fig.tight_layout(); fig.savefig(out_png, dpi=150); plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default=".")
    ap.add_argument("--human", default="human_eval_annotation_ltx.xlsx")
    ap.add_argument("--outdir", default="batch_results")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    human = load_human(args.human)
    conds = discover_conditions(args.indir)
    if not conds: raise SystemExit(f"No CSVs in {args.indir}")

    M, EK, DIS, CM, CDIS = [], [], [], [], []
    for cond, f in conds.items():
        pe = f.get("per_event")
        if pe is None: print(f"[skip] {cond}: no per_event"); continue
        gem_rel = load_gemini_relation(f["per_item"]) if f.get("per_item") else None

        m = merge_yesno(human, load_gemini_yesno(pe), gem_rel); m["condition"] = cond
        mc = merge_count(human, load_gemini_count(pe)); mc["condition"] = cond

        M.append(metrics_table(m, cond))
        EK.append(eventkind_agreement(m, cond))
        DIS.append(m[(~m["match"]) & m["gem_label"].notna()])
        CM.append(count_metrics(mc, cond))
        CDIS.append(mc[~mc["exact"]])
        print(f"[ok] {cond}: yes/no {len(m)}r ({int((~m['match']).sum())} diff) | "
              f"count {len(mc)}r ({int((~mc['exact']).sum())} mismatch)"
              f"{'' if gem_rel is not None else '  (no relation file)'}")

    metrics = pd.concat(M, ignore_index=True)
    ek = pd.concat(EK, ignore_index=True)
    cm = pd.concat(CM, ignore_index=True)

    dcols = ["condition", "video_file", "item_id", "event_id", "event_kind",
             "event_label", "axis", "human_label", "gem_label", "reason", "evidence", "notes"]
    dis = pd.concat(DIS, ignore_index=True)
    dis = dis[[c for c in dcols if c in dis.columns]].sort_values(["condition", "event_kind", "axis"])

    ccols = ["condition", "video_file", "item_id", "event_id", "event_kind", "event_label",
             "human_count", "gem_count", "diff", "required_count", "reason", "evidence", "notes"]
    cdis = pd.concat(CDIS, ignore_index=True)
    cdis = cdis[[c for c in ccols if c in cdis.columns]].sort_values(
        ["condition", "event_kind", "diff"])

    metrics.to_csv(f"{args.outdir}/metrics_long.csv", index=False)
    ek.to_csv(f"{args.outdir}/agreement_by_eventkind.csv", index=False)
    dis.to_csv(f"{args.outdir}/disagreements.csv", index=False)
    cm.to_csv(f"{args.outdir}/count_metrics.csv", index=False)
    cdis.to_csv(f"{args.outdir}/count_disagreements.csv", index=False)

    heatmap(metrics[metrics["axis"].isin(YESNO_AXES)], "condition", "axis",
            "balanced_accuracy", "Balanced accuracy (condition x axis)",
            f"{args.outdir}/bacc_heatmap.png", order=YESNO_AXES)
    heatmap(ek, "event_kind", "axis", "agreement_rate",
            "yes/no agreement (event_kind x axis)",
            f"{args.outdir}/eventkind_heatmap.png", order=YESNO_AXES)
    heatmap(cm[cm["event_kind"] != "ALL"], "event_kind", "condition",
            "exact_match_rate", "TC-Count exact-match rate (event_kind x condition)",
            f"{args.outdir}/count_eventkind_heatmap.png")

    pd.set_option("display.width", 170)
    print("\n=== yes/no summary per condition ===")
    print(metrics[metrics["axis"].isin(["OVERALL", "MACRO"])]
          [["condition", "axis", "n", "accuracy", "balanced_accuracy"]].round(3).to_string(index=False))
    print("\n=== TC-Count numeric summary ===")
    print(cm.round(3).to_string(index=False))
    print(f"\nSaved -> {args.outdir}/")


if __name__ == "__main__":
    main()
