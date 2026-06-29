#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep error-stability analysis for T2AV Gemini judge outputs.

Extends the stability matrix script with:
  1) FP/FN direction analysis by model × axis × version.
     - FP = Gemini pass(1) while human fail(0): hallucination / over-accept.
     - FN = Gemini fail(0) while human pass(1): omission / over-reject.
  2) Cascade collapse.
     - AVB / TC-Count errors are marked cascaded when upstream A/V/AVB is already wrong.
     - TC-Relation item-level errors can be collapsed to event-level upstream failures in the same video.
     - Outputs raw-vs-independent error counts.
  3) Tool-sensitive reason taxonomy tagging.
     - Default: deterministic keyword tagging.
     - Optional: OpenAI or Gemini LLM tagging if CFG["USE_LLM_TAXONOMY"] = True.
       Set CFG["LLM_PROVIDER"] to "openai" or "gemini".

Execution:
  Edit CONFIG at bottom, then:
    python stability_deep_analysis.py

Recommended first run:
  INSPECT=True to confirm TC-Relation joins correctly, then INSPECT=False.
"""
import os, re, json, hashlib
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------- normalization utils --------------------------
YES = {"yes","y","true","1","1.0","pass","passed","correct","present","match","success","t"}
NO  = {"no","n","false","0","0.0","fail","failed","incorrect","absent","mismatch","failure","f"}
AXES = ["A", "V", "AVB", "TC-Relation", "TC-Count"]
BASE_AXES = ["A", "V"]
DEPENDENT_AXES = ["AVB", "TC-Relation", "TC-Count"]
KEY = ["model", "video_file", "event", "axis"]
KEYV = ["model", "video_file", "event", "axis", "version"]


def to01(v):
    if pd.isna(v): return np.nan
    s = str(v).strip().lower()
    if s in YES: return 1.0
    if s in NO:  return 0.0
    return np.nan


def canon_axis(v):
    if pd.isna(v): return None
    s = re.sub(r"[\s_]", "-", str(v).strip().lower())
    return {
        "a":"A","audio":"A","a-axis":"A",
        "v":"V","visual":"V","v-axis":"V",
        "avb":"AVB","av-binding":"AVB","avbinding":"AVB","binding":"AVB","av":"AVB",
        "tc-relation":"TC-Relation","tc-relation-satisfaction":"TC-Relation",
        "tcrelation":"TC-Relation","tc-rel":"TC-Relation","tc-rel-satisfaction":"TC-Relation",
        "relation":"TC-Relation","relation-satisfaction":"TC-Relation","tcr":"TC-Relation",
        "temporal-relation":"TC-Relation","temporal-relation-satisfaction":"TC-Relation",
        "temporal-order":"TC-Relation","temporal-order-satisfaction":"TC-Relation",
        "tc-count":"TC-Count","tc-count-satisfaction":"TC-Count",
        "tccount":"TC-Count","tc-cnt":"TC-Count","count":"TC-Count","count-satisfaction":"TC-Count","tcc":"TC-Count",
        "audio-event-correctness":"A", "visual-event-correctness":"V",
        "audio-visual-binding":"AVB", "temporal-count-satisfaction":"TC-Count",
    }.get(s, None)


def norm_event(v):
    """'01event_1' / 'event_1' / 1 -> 'event_1'. No number -> original or ITEM."""
    if pd.isna(v) or str(v).strip() == "": return "ITEM"
    mm = re.search(r"(\d+)\s*$", str(v))
    if mm: return f"event_{int(mm.group(1))}"
    mm2 = re.search(r"(\d+)", str(v))
    return f"event_{int(mm2.group(1))}" if mm2 else str(v).strip()


def col(df, *names):
    low = {c.lower().strip(): c for c in df.columns}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    for n in names:
        for c in df.columns:
            if n.lower() in c.lower(): return c
    return None


def first_col_by_keywords(df, keyword_sets, exclude_keywords=None):
    exclude_keywords = [x.lower().replace("-", "_") for x in (exclude_keywords or [])]
    lows = {c: c.lower().replace(" ", "_").replace("-", "_") for c in df.columns}
    for keys in keyword_sets:
        keys = [k.lower().replace("-", "_") for k in keys]
        for c, lc in lows.items():
            if exclude_keywords and any(x in lc for x in exclude_keywords):
                continue
            if all(k in lc for k in keys):
                return c
    return None


def gem_event(ev_raw, axis):
    return "ITEM" if axis == "TC-Relation" else norm_event(ev_raw)


def human_event(row_id, axis):
    if axis == "TC-Relation": return "ITEM"
    parts = str(row_id).split("__")
    return norm_event(parts[1]) if len(parts) >= 2 else norm_event(row_id)


# -------------------------------- loaders -----------------------------------
def load_gemini_per_event(model, version, path):
    df = pd.read_csv(path)
    vf, ev, ax, lb = col(df,"video_file"), col(df,"event_id"), col(df,"axis"), col(df,"label")
    ek, rs, cc = col(df,"event_kind"), col(df,"reason"), col(df,"count_correct")
    if vf is None or ax is None or lb is None:
        raise ValueError(f"per_event CSV 필수 컬럼 누락: {path}")

    axis = df[ax].map(canon_axis)
    verdict = df[lb].map(to01)
    if cc is not None:
        cc01 = df[cc].map(to01)
        verdict = verdict.where(axis != "TC-Count", cc01)

    out = pd.DataFrame({
        "model": model,
        "video_file": df[vf].astype(str).str.strip(),
        "axis": axis,
        "g": verdict,
        "version": version,
        "event_kind": df[ek] if ek else "",
        "reason": df[rs] if rs else "",
        "_ev": df[ev].astype(str) if ev else "",
    })
    out["event"] = [gem_event(e,a) for e,a in zip(out["_ev"], out["axis"])]
    return out.drop(columns="_ev").loc[out["axis"].notna()]


def companion_item_candidates(per_event_path):
    """NoTools_per_event.csv -> NoTools.csv, NoTools_per_event-ICL.csv -> NoTools-ICL.csv."""
    d, b = os.path.split(per_event_path)
    stem, ext = os.path.splitext(b)
    candidates = []
    if "_per_event" in stem:
        candidates.append(os.path.join(d, stem.replace("_per_event", "") + ext))
    if "per_event" in stem:
        candidates.append(os.path.join(d, stem.replace("per_event", "") + ext))
    candidates.append(os.path.join(d, stem.replace("_per_event", "_item") + ext))
    seen, out = set(), []
    for p in candidates:
        if p not in seen:
            out.append(p); seen.add(p)
    return out


def first_existing(paths):
    for p in paths:
        if os.path.exists(p): return p
    return None


def load_gemini_tc_relation(model, version, per_event_path):
    """Read item-level TC-Relation from companion CSV and return event='ITEM'."""
    p = first_existing(companion_item_candidates(per_event_path))
    empty = pd.DataFrame(columns=["model","video_file","axis","g","version","event_kind","reason","event"])
    if p is None:
        return empty, None

    df = pd.read_csv(p)
    vf = col(df, "video_file", "file", "filename")
    if vf is None:
        raise ValueError(f"item-level CSV에서 video_file 컬럼을 찾지 못함: {p}")

    # long schema: rows include axis + label/verdict
    ax = col(df, "axis")
    if ax is not None:
        axis = df[ax].map(canon_axis)
        rel = df[axis == "TC-Relation"].copy()
        if len(rel):
            lb = col(rel, "label", "verdict", "correct", "satisfied", "satisfaction", "value")
            rs = col(rel, "reason", "rationale", "explanation")
            if lb is None:
                raise ValueError(f"long schema TC-Relation row 는 찾았지만 label/verdict 컬럼 없음: {p}")
            return pd.DataFrame({
                "model": model,
                "video_file": rel[vf].astype(str).str.strip(),
                "axis": "TC-Relation",
                "g": rel[lb].map(to01),
                "version": version,
                "event_kind": "item",
                "reason": rel[rs] if rs else "",
                "event": "ITEM",
            }), p

    # wide schema: temporal_relation_satisfaction / temporal_order_satisfaction column
    rel_col = first_col_by_keywords(df, [
        ["tc", "relation"],
        ["temporal", "relation"],
        ["temporal", "order"],
        ["relation", "satisfaction"],
        ["order", "satisfaction"],
        ["tc", "rel"],
        ["tcr"],
    ], exclude_keywords=["reason", "rationale", "explanation", "event_kind", "video_file", "item_id"])
    if rel_col is None:
        rel_col = col(df, "tc_relation", "temporal_relation_satisfaction", "temporal_order_satisfaction", "relation_satisfaction")
    if rel_col is None:
        return empty, p

    reason_col = first_col_by_keywords(df, [
        ["tc", "relation", "reason"],
        ["temporal", "relation", "reason"],
        ["temporal", "order", "reason"],
        ["relation", "reason"],
        ["order", "reason"],
        ["tc", "rel", "reason"],
    ])
    return pd.DataFrame({
        "model": model,
        "video_file": df[vf].astype(str).str.strip(),
        "axis": "TC-Relation",
        "g": df[rel_col].map(to01),
        "version": version,
        "event_kind": "item",
        "reason": df[reason_col] if reason_col else "",
        "event": "ITEM",
    }), p


def load_human(model, path, sheet):
    df = pd.read_excel(path, sheet_name=sheet)
    vf, ax, lb = col(df,"video_file"), col(df,"axis"), col(df,"human_label","label")
    rid, evt, hc = col(df,"row_id"), col(df,"event"), col(df,"hand_condition")
    if vf is None or ax is None or lb is None:
        raise ValueError(f"human GT 필수 컬럼 누락: {path}")
    out = pd.DataFrame({
        "model": model,
        "video_file": df[vf].astype(str).str.strip(),
        "axis": df[ax].map(canon_axis),
        "h": df[lb].map(to01),
        "event_text": df[evt] if evt else "",
        "hand_condition": df[hc] if hc else "",
        "_rid": df[rid].astype(str) if rid else "",
    })
    out["event"] = [human_event(r,a) for r,a in zip(out["_rid"], out["axis"])]
    return out.drop(columns="_rid").loc[out["axis"].notna()]


# --------------------------- deeper analysis helpers -------------------------
def add_error_direction(m):
    """Add error_type: correct / FP / FN / unknown."""
    m = m.copy()
    m["error_type"] = np.select(
        [m["g"] == m["h"], (m["g"] == 1) & (m["h"] == 0), (m["g"] == 0) & (m["h"] == 1)],
        ["correct", "FP", "FN"],
        default="unknown",
    )
    m["is_fp"] = (m["error_type"] == "FP").astype(int)
    m["is_fn"] = (m["error_type"] == "FN").astype(int)
    return m


def summarize_per_event_stats(m, outdir, order):
    """
    Raw counts (+ %) per axis, per event, and per specific event instance.

    Complements direction_counts_*.csv (which is axis × version only) by adding
    the EVENT dimension. Every table carries both raw numbers and rates:
      n        = # of gemini-vs-human comparison pairs
      agree    = g == h
      disagree = g != h   (== FP + FN)
      FP       = gemini pass(1) / human fail(0)  (over-accept / hallucination)
      FN       = gemini fail(0) / human pass(1)  (over-reject / omission)
      *_pct    = the corresponding rate over n, in %.

    Note on version aggregation: tables that do NOT split by version sum each
    unit across all tool configs present, so one human label compared under k
    configs contributes k pairs. That is the intended "how often does gemini
    disagree on this event across configs" view; use the *_version table for the
    per-config breakdown.
    """
    def build(group_cols, fname, sort_cols=None):
        g = (m.groupby(group_cols, observed=True)
               .agg(n=("disagree", "size"),
                    disagree=("disagree", "sum"),
                    FP=("is_fp", "sum"),
                    FN=("is_fn", "sum"))
               .reset_index())
        g["agree"] = g["n"] - g["disagree"]
        g["disagree_pct"] = (100 * g["disagree"] / g["n"]).round(1)
        g["fp_pct"] = (100 * g["FP"] / g["n"]).round(1)
        g["fn_pct"] = (100 * g["FN"] / g["n"]).round(1)
        lead = [c for c in ["model", "axis", "event", "video_file", "version"]
                if c in g.columns]
        g = g[lead + ["n", "agree", "disagree", "FP", "FN",
                      "disagree_pct", "fp_pct", "fn_pct"]]
        if "axis" in g.columns:
            g["axis"] = pd.Categorical(g["axis"], AXES, ordered=True)
        if "version" in g.columns:
            g["version"] = pd.Categorical(g["version"], order, ordered=True)
        # natural event ordering (event_1, event_2, ..., event_10) instead of lexical
        sort_cols = sort_cols or group_cols
        keys, drop_tmp = [], []
        for c in sort_cols:
            if c == "event":
                g["_evnum"] = pd.to_numeric(g["event"].str.extract(r"(\d+)")[0], errors="coerce")
                keys.append("_evnum"); drop_tmp.append("_evnum")
            else:
                keys.append(c)
        g = g.sort_values(keys).drop(columns=drop_tmp)
        g.to_csv(os.path.join(outdir, fname), index=False)
        return g

    by_axis = build(["model", "axis"],
                    "stats_by_axis.csv")
    by_axis_event = build(["model", "axis", "event"],
                          "stats_by_axis_event.csv")
    by_axis_event_ver = build(["model", "axis", "event", "version"],
                              "stats_by_axis_event_version.csv")
    by_instance = build(["model", "video_file", "event", "axis"],
                        "stats_by_video_event_axis.csv",
                        sort_cols=["model", "axis", "video_file", "event"])

    print("\n[per-event stats] 카운트+% 테이블:")
    print("   - stats_by_axis.csv               (model × axis)")
    print("   - stats_by_axis_event.csv         (model × axis × event)")
    print("   - stats_by_axis_event_version.csv (model × axis × event × version)")
    print("   - stats_by_video_event_axis.csv   (특정 이벤트 인스턴스: video × event × axis)")
    print("\n[stats_by_axis]\n", by_axis.to_string(index=False))
    return by_axis, by_axis_event, by_axis_event_ver, by_instance


def summarize_direction(m, outdir, order):
    """CSV + plots for FP/FN direction by model × axis × version and by stability class."""
    rows = []
    gb_cols = ["model", "axis", "version"]
    for keys, d in m.groupby(gb_cols):
        model, axis, version = keys
        n = len(d)
        fp = int((d.error_type == "FP").sum())
        fn = int((d.error_type == "FN").sum())
        corr = int((d.error_type == "correct").sum())
        rows.append({
            "model": model, "axis": axis, "version": version,
            "n": n, "correct": corr, "FP": fp, "FN": fn,
            "fp_rate": fp / n if n else np.nan,
            "fn_rate": fn / n if n else np.nan,
            "err_rate": (fp + fn) / n if n else np.nan,
            "fp_minus_fn_rate": (fp - fn) / n if n else np.nan,
        })
    direction = pd.DataFrame(rows)
    direction["axis"] = pd.Categorical(direction["axis"], AXES, ordered=True)
    direction["version"] = pd.Categorical(direction["version"], order, ordered=True)
    direction = direction.sort_values(["model", "axis", "version"])
    direction.to_csv(os.path.join(outdir, "direction_counts_by_axis_version.csv"), index=False)

    # model-level plots: positive FP, negative FN, one panel per axis
    for model, dm in direction.groupby("model", observed=False):
        fig, axs = plt.subplots(1, len(AXES), figsize=(3.2 * len(AXES), 4.1), sharey=True, squeeze=False)
        for i, axis in enumerate(AXES):
            ax = axs[0][i]
            here = dm[dm.axis.astype(str) == axis].set_index("version").reindex(order)
            x = np.arange(len(order))
            ax.bar(x, here["fp_rate"].fillna(0).mul(100), label="FP / over-accept")
            ax.bar(x, -here["fn_rate"].fillna(0).mul(100), label="FN / over-reject")
            ax.axhline(0, linewidth=0.8)
            ax.set_title(axis)
            ax.set_xticks(x)
            ax.set_xticklabels(order, rotation=90, fontsize=7)
            ax.spines[["top", "right"]].set_visible(False)
            if i == 0:
                ax.set_ylabel("% of units\n(+FP, -FN)")
                ax.legend(frameon=False, fontsize=8)
        fig.suptitle(f"FP/FN direction by axis × version — {model}")
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"deep1_fp_fn_by_axis_version_{model}.png"), dpi=200)
        plt.close()

    # same plot but in RAW COUNTS (+FP up, -FN down), with value labels on bars
    for model, dm in direction.groupby("model", observed=False):
        fig, axs = plt.subplots(1, len(AXES), figsize=(3.2 * len(AXES), 4.1), sharey=True, squeeze=False)
        for i, axis in enumerate(AXES):
            ax = axs[0][i]
            here = dm[dm.axis.astype(str) == axis].set_index("version").reindex(order)
            x = np.arange(len(order))
            fp = here["FP"].fillna(0).to_numpy()
            fn = here["FN"].fillna(0).to_numpy()
            ax.bar(x, fp, label="FP / over-accept")
            ax.bar(x, -fn, label="FN / over-reject")
            for xi, v in zip(x, fp):
                if v: ax.text(xi, v, str(int(v)), ha="center", va="bottom", fontsize=6)
            for xi, v in zip(x, fn):
                if v: ax.text(xi, -v, str(int(v)), ha="center", va="top", fontsize=6)
            ax.axhline(0, linewidth=0.8)
            ax.set_title(axis)
            ax.set_xticks(x)
            ax.set_xticklabels(order, rotation=90, fontsize=7)
            ax.spines[["top", "right"]].set_visible(False)
            if i == 0:
                ax.set_ylabel("# of units\n(+FP, -FN)")
                ax.legend(frameon=False, fontsize=8)
        fig.suptitle(f"FP/FN direction by axis × version (counts) — {model}")
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"deep1_fp_fn_by_axis_version_counts_{model}.png"), dpi=200)
        plt.close()

    if "class" in m.columns:
        cls_rows = []
        for keys, d in m.groupby(["model", "class", "axis", "version"]):
            model, cls, axis, version = keys
            n = len(d)
            fp = int((d.error_type == "FP").sum())
            fn = int((d.error_type == "FN").sum())
            cls_rows.append({
                "model": model, "class": cls, "axis": axis, "version": version,
                "n": n, "FP": fp, "FN": fn,
                "fp_rate": fp / n if n else np.nan,
                "fn_rate": fn / n if n else np.nan,
            })
        cls_dir = pd.DataFrame(cls_rows)
        cls_dir["axis"] = pd.Categorical(cls_dir["axis"], AXES, ordered=True)
        cls_dir["version"] = pd.Categorical(cls_dir["version"], order, ordered=True)
        cls_dir = cls_dir.sort_values(["model", "class", "axis", "version"])
        cls_dir.to_csv(os.path.join(outdir, "direction_counts_by_class_axis_version.csv"), index=False)

        # Tool-sensitive-only plot: directly tests whether tool-sensitive errors are FP or FN.
        ts = cls_dir[cls_dir["class"] == "tool_sensitive"]
        for model, dm in ts.groupby("model", observed=False):
            fig, axs = plt.subplots(1, len(AXES), figsize=(3.2 * len(AXES), 4.1), sharey=True, squeeze=False)
            for i, axis in enumerate(AXES):
                ax = axs[0][i]
                here = dm[dm.axis.astype(str) == axis].set_index("version").reindex(order)
                x = np.arange(len(order))
                ax.bar(x, here["fp_rate"].fillna(0).mul(100), label="FP")
                ax.bar(x, -here["fn_rate"].fillna(0).mul(100), label="FN")
                ax.axhline(0, linewidth=0.8)
                ax.set_title(axis)
                ax.set_xticks(x)
                ax.set_xticklabels(order, rotation=90, fontsize=7)
                ax.spines[["top", "right"]].set_visible(False)
                if i == 0:
                    ax.set_ylabel("% within tool-sensitive units\n(+FP, -FN)")
                    ax.legend(frameon=False, fontsize=8)
            fig.suptitle(f"FP/FN direction within tool-sensitive units — {model}")
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, f"deep1b_fp_fn_tool_sensitive_{model}.png"), dpi=200)
            plt.close()

        # tool-sensitive plot in RAW COUNTS, with value labels
        for model, dm in ts.groupby("model", observed=False):
            fig, axs = plt.subplots(1, len(AXES), figsize=(3.2 * len(AXES), 4.1), sharey=True, squeeze=False)
            for i, axis in enumerate(AXES):
                ax = axs[0][i]
                here = dm[dm.axis.astype(str) == axis].set_index("version").reindex(order)
                x = np.arange(len(order))
                fp = here["FP"].fillna(0).to_numpy()
                fn = here["FN"].fillna(0).to_numpy()
                ax.bar(x, fp, label="FP")
                ax.bar(x, -fn, label="FN")
                for xi, v in zip(x, fp):
                    if v: ax.text(xi, v, str(int(v)), ha="center", va="bottom", fontsize=6)
                for xi, v in zip(x, fn):
                    if v: ax.text(xi, -v, str(int(v)), ha="center", va="top", fontsize=6)
                ax.axhline(0, linewidth=0.8)
                ax.set_title(axis)
                ax.set_xticks(x)
                ax.set_xticklabels(order, rotation=90, fontsize=7)
                ax.spines[["top", "right"]].set_visible(False)
                if i == 0:
                    ax.set_ylabel("# within tool-sensitive units\n(+FP, -FN)")
                    ax.legend(frameon=False, fontsize=8)
            fig.suptitle(f"FP/FN direction within tool-sensitive units (counts) — {model}")
            plt.tight_layout()
            plt.savefig(os.path.join(outdir, f"deep1b_fp_fn_tool_sensitive_counts_{model}.png"), dpi=200)
            plt.close()

    return direction


def add_cascade_flags(m):
    """
    Mark each wrong row as independent or cascaded.

    Dependency policy:
      A, V: independent roots.
      AVB: cascaded if same event/version has wrong A or V.
      TC-Count: cascaded if same event/version has wrong A, V, or AVB.
      TC-Relation: cascaded if same video/version has any wrong A, V, or AVB in any event.
    """
    m = m.copy()
    wrong = m[m["disagree"] == 1].copy()
    same_event_wrong = defaultdict(set)
    video_wrong = defaultdict(set)
    for r in wrong.itertuples(index=False):
        same_event_wrong[(r.model, r.video_file, r.event, r.version)].add(r.axis)
        if r.event != "ITEM":
            video_wrong[(r.model, r.video_file, r.version)].add(r.axis)

    cascade_status, cascade_source, root_axis = [], [], []
    for r in m.itertuples(index=False):
        if r.disagree != 1:
            cascade_status.append("correct")
            cascade_source.append("")
            root_axis.append("")
            continue

        ev_key = (r.model, r.video_file, r.event, r.version)
        vid_key = (r.model, r.video_file, r.version)
        ev_wrong_axes = same_event_wrong.get(ev_key, set())
        vid_wrong_axes = video_wrong.get(vid_key, set())

        if r.axis in BASE_AXES:
            cascade_status.append("independent")
            cascade_source.append(r.axis)
            root_axis.append(r.axis)
        elif r.axis == "AVB":
            src = [a for a in ["A", "V"] if a in ev_wrong_axes]
            if src:
                cascade_status.append("cascaded")
                cascade_source.append("+".join(src))
                root_axis.append(src[0])
            else:
                cascade_status.append("independent")
                cascade_source.append("AVB")
                root_axis.append("AVB")
        elif r.axis == "TC-Count":
            src = [a for a in ["A", "V", "AVB"] if a in ev_wrong_axes]
            if src:
                cascade_status.append("cascaded")
                cascade_source.append("+".join(src))
                root_axis.append(src[0])
            else:
                cascade_status.append("independent")
                cascade_source.append("TC-Count")
                root_axis.append("TC-Count")
        elif r.axis == "TC-Relation":
            src = [a for a in ["A", "V", "AVB"] if a in vid_wrong_axes]
            if src:
                cascade_status.append("cascaded")
                cascade_source.append("video:" + "+".join(src))
                root_axis.append(src[0])
            else:
                cascade_status.append("independent")
                cascade_source.append("TC-Relation")
                root_axis.append("TC-Relation")
        else:
            cascade_status.append("independent")
            cascade_source.append(r.axis)
            root_axis.append(r.axis)

    m["cascade_status"] = cascade_status
    m["cascade_source"] = cascade_source
    m["root_axis"] = root_axis
    return m


def collapse_unit_stability(out):
    """Collapse stability rows at the unit level to avoid counting propagated errors as independent units."""
    out = out.copy()
    err = out[out["class"] != "solved"].copy()

    # class-aware indexes: stable_wrong only collapses to stable_wrong;
    # tool_sensitive collapses to any non-solved upstream.
    by_event = defaultdict(dict)   # (model, video, event) -> axis -> class
    by_video = defaultdict(dict)   # (model, video) -> axis -> class
    for _, r in err.iterrows():
        by_event[(r["model"], r["video_file"], r["event"])][r["axis"]] = r["class"]
        by_video[(r["model"], r["video_file"])][r["axis"]] = r["class"]

    statuses, sources = [], []
    for _, r in out.iterrows():
        cls = r["class"]
        if cls == "solved":
            statuses.append("solved")
            sources.append("")
            continue
        ev_axes = by_event.get((r["model"], r["video_file"], r["event"]), {})
        vid_axes = by_video.get((r["model"], r["video_file"]), {})

        def upstream_ok(up_cls):
            if cls == "stable_wrong":
                return up_cls == "stable_wrong"
            return up_cls in {"stable_wrong", "tool_sensitive"}

        src = []
        if r["axis"] == "AVB":
            src = [a for a in ["A", "V"] if a in ev_axes and upstream_ok(ev_axes[a])]
        elif r["axis"] == "TC-Count":
            src = [a for a in ["A", "V", "AVB"] if a in ev_axes and upstream_ok(ev_axes[a])]
        elif r["axis"] == "TC-Relation":
            src = [a for a in ["A", "V", "AVB"] if a in vid_axes and upstream_ok(vid_axes[a])]

        if src:
            statuses.append("cascaded_unit")
            sources.append("+".join(src))
        else:
            statuses.append("independent_unit")
            sources.append(r["axis"])

    out["collapse_status"] = statuses
    out["collapse_source"] = sources
    return out

def summarize_cascade(m_cascade, collapsed_units, outdir, order):
    m_cascade.to_csv(os.path.join(outdir, "cascade_per_version_errors.csv"), index=False)

    wrong = m_cascade[m_cascade.disagree == 1].copy()
    per_ver = (wrong.groupby(["model", "version", "cascade_status"])
                    .size().unstack(fill_value=0).reset_index())
    for c in ["independent", "cascaded"]:
        if c not in per_ver.columns: per_ver[c] = 0
    per_ver["raw_errors"] = per_ver["independent"] + per_ver["cascaded"]
    per_ver["collapse_ratio"] = np.where(per_ver["raw_errors"] > 0,
                                          per_ver["cascaded"] / per_ver["raw_errors"], np.nan)
    per_ver["version"] = pd.Categorical(per_ver["version"], order, ordered=True)
    per_ver = per_ver.sort_values(["model", "version"])
    per_ver.to_csv(os.path.join(outdir, "cascade_independent_error_count_by_version.csv"), index=False)

    by_axis = (wrong.groupby(["model", "axis", "version", "cascade_status"])
                    .size().unstack(fill_value=0).reset_index())
    for c in ["independent", "cascaded"]:
        if c not in by_axis.columns: by_axis[c] = 0
    by_axis["raw_errors"] = by_axis["independent"] + by_axis["cascaded"]
    by_axis["axis"] = pd.Categorical(by_axis["axis"], AXES, ordered=True)
    by_axis["version"] = pd.Categorical(by_axis["version"], order, ordered=True)
    by_axis = by_axis.sort_values(["model", "axis", "version"])
    by_axis.to_csv(os.path.join(outdir, "cascade_summary_by_axis_version.csv"), index=False)

    collapsed_units.to_csv(os.path.join(outdir, "collapsed_stability_matrix.csv"), index=False)
    unit_summary = (collapsed_units[collapsed_units["class"] != "solved"]
                    .groupby(["model", "class", "collapse_status"])
                    .size().unstack(fill_value=0))
    for c in ["independent_unit", "cascaded_unit"]:
        if c not in unit_summary.columns: unit_summary[c] = 0
    unit_summary["raw_non_solved_units"] = unit_summary["independent_unit"] + unit_summary["cascaded_unit"]
    unit_summary.to_csv(os.path.join(outdir, "collapsed_unit_summary_by_class.csv"))

    # Per-version raw vs independent plot
    for model, dm in per_ver.groupby("model", observed=False):
        dm = dm.set_index("version").reindex(order)
        x = np.arange(len(order))
        fig, ax = plt.subplots(figsize=(11, 4.2))
        ax.bar(x, dm["independent"].fillna(0), label="independent errors")
        ax.bar(x, dm["cascaded"].fillna(0), bottom=dm["independent"].fillna(0), label="cascaded errors")
        ax.set_xticks(x)
        ax.set_xticklabels(order, rotation=45, ha="right")
        ax.set_ylabel("# wrong units")
        ax.set_title(f"Raw errors decomposed into independent vs cascaded — {model}")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"deep2_cascade_raw_vs_independent_{model}.png"), dpi=200)
        plt.close()

    return per_ver, by_axis, unit_summary


TAXONOMY_LABELS = [
    "laterality_left_right",
    "slap_contact_hallucination",
    "mouth_or_speech_visual",
    "timing_order_sync",
    "count_repetition",
    "audio_detection_or_speech_content",
    "action_identity_or_visibility",
    "tool_artifact_or_uncertainty",
    "other",
]


def heuristic_reason_tags(text):
    s = str(text).lower()
    tags = []
    if re.search(r"\b(left|right|hand|thigh|leg|side|opposite)\b", s):
        tags.append("laterality_left_right")
    if re.search(r"\b(slap|slapping|strike|strikes|hit|hits|contact|impact|thigh|leg)\b", s):
        tags.append("slap_contact_hallucination")
    if re.search(r"\b(mouth|lip|lips|speaking|talking|speech|utterance|says|said|voice)\b", s):
        tags.append("mouth_or_speech_visual")
    if re.search(r"\b(before|after|order|sequence|sync|synchron|simultaneous|same time|aligned|onset|timing|temporal)\b", s):
        tags.append("timing_order_sync")
    if re.search(r"\b(count|once|twice|three|repetition|repeated|number|single|multiple)\b", s):
        tags.append("count_repetition")
    if re.search(r"\b(audio|sound|heard|hear|clap|whisper|transcript|spoken|speech content)\b", s):
        tags.append("audio_detection_or_speech_content")
    if re.search(r"\b(visible|visibility|gesture|action|pose|thumb|thumbs|raise|raised|unclear|occluded|not clear)\b", s):
        tags.append("action_identity_or_visibility")
    if re.search(r"\b(mediapipe|landmark|clap|whisper|tool|confidence|uncertain|ambiguous|likely|appears)\b", s):
        tags.append("tool_artifact_or_uncertainty")
    return tags or ["other"]


def taxonomy_prompt(text):
    return f"""
Classify the failure reason below into one or more labels from this fixed taxonomy:
{TAXONOMY_LABELS}

Definitions:
- laterality_left_right: left/right hand, side, thigh, actor-centered side confusion.
- slap_contact_hallucination: mere contact/hit/impact is over-accepted as a valid slap, or slap is hallucinated.
- mouth_or_speech_visual: visible speaking/mouth/lip motion judgment.
- timing_order_sync: temporal order, synchrony, onset, before/after mistakes.
- count_repetition: count, once/twice, repetition mistakes.
- audio_detection_or_speech_content: speech/audio content, sound presence, transcript/audio cue mistakes.
- action_identity_or_visibility: wrong action/gesture identity or visual visibility/occlusion.
- tool_artifact_or_uncertainty: tool-specific artifact or explicit uncertainty/ambiguous cue.
- other: none of the above.

Return strict JSON only: {{"labels": [..], "short_reason": "..."}}

Failure reason:
{text}
""".strip()


def parse_taxonomy_json(raw):
    """Parse an LLM JSON response and keep only allowed labels."""
    raw = str(raw).strip()
    # tolerate accidental fenced JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    parsed = json.loads(raw)
    labels = [x for x in parsed.get("labels", []) if x in TAXONOMY_LABELS]
    return labels or ["other"]


def llm_reason_tags(text, cfg):
    """Optional LLM tagging. Supports OpenAI or Gemini. Falls back to heuristic tags."""
    if not cfg.get("USE_LLM_TAXONOMY", False):
        return heuristic_reason_tags(text), "heuristic"

    provider = str(cfg.get("LLM_PROVIDER", "openai")).strip().lower()
    prompt = taxonomy_prompt(text)

    if provider == "gemini":
        if not os.environ.get("GEMINI_API_KEY"):
            return heuristic_reason_tags(text), "heuristic_no_gemini_api_key"
        try:
            from google import genai
            client = genai.Client()
            schema = {
                "type": "object",
                "properties": {
                    "labels": {
                        "type": "array",
                        "items": {"type": "string", "enum": TAXONOMY_LABELS},
                    },
                    "short_reason": {"type": "string"},
                },
                "required": ["labels", "short_reason"],
            }
            resp = client.models.generate_content(
                model=cfg.get("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config={
                    "temperature": 0,
                    "response_format": {
                        "text": {
                            "mime_type": "application/json",
                            "schema": schema,
                        }
                    },
                },
            )
            return parse_taxonomy_json(resp.text), "llm_gemini"
        except Exception as e:
            if cfg.get("VERBOSE_LLM_ERRORS", False):
                print(f"[warn] Gemini taxonomy failed: {type(e).__name__}: {e}")
            return heuristic_reason_tags(text), "heuristic_gemini_failed"

    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            return heuristic_reason_tags(text), "heuristic_no_openai_api_key"
        try:
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=cfg.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw = resp.choices[0].message.content.strip()
            return parse_taxonomy_json(raw), "llm_openai"
        except Exception as e:
            if cfg.get("VERBOSE_LLM_ERRORS", False):
                print(f"[warn] OpenAI taxonomy failed: {type(e).__name__}: {e}")
            return heuristic_reason_tags(text), "heuristic_openai_failed"

    return heuristic_reason_tags(text), f"heuristic_unknown_provider_{provider}"


def summarize_tool_sensitive_taxonomy(m, out, outdir, order, cfg):
    """Tag wrong reasons for tool-sensitive units and summarize taxonomy counts."""
    ts_keys = out.loc[out["class"] == "tool_sensitive", KEY].drop_duplicates()
    if len(ts_keys) == 0:
        return pd.DataFrame(), pd.DataFrame()

    ts = m.merge(ts_keys, on=KEY, how="inner")
    ts_wrong = ts[ts["disagree"] == 1].copy()
    rows = []
    prompt_rows = []
    for i, r in enumerate(ts_wrong.itertuples(index=False)):
        reason = str(getattr(r, "reason", ""))
        uid = hashlib.md5("||".join([r.model, r.video_file, r.event, r.axis, r.version]).encode()).hexdigest()[:12]
        tags, method = llm_reason_tags(reason, cfg)
        prompt_rows.append({
            "id": uid,
            "model": r.model,
            "video_file": r.video_file,
            "event": r.event,
            "axis": r.axis,
            "version": r.version,
            "error_type": r.error_type,
            "reason": reason,
            "taxonomy": TAXONOMY_LABELS,
        })
        rows.append({
            "id": uid,
            "model": r.model,
            "video_file": r.video_file,
            "event": r.event,
            "axis": r.axis,
            "version": r.version,
            "g": r.g,
            "h": r.h,
            "error_type": r.error_type,
            "reason": reason,
            "taxonomy_tags": ";".join(tags),
            "tagging_method": method,
        })

    tagged = pd.DataFrame(rows)
    tagged.to_csv(os.path.join(outdir, "tool_sensitive_wrong_reasons_tagged.csv"), index=False)

    # LLM-ready JSONL export for external batch tagging / manual inspection.
    with open(os.path.join(outdir, "tool_sensitive_taxonomy_prompts.jsonl"), "w", encoding="utf-8") as f:
        for obj in prompt_rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    exploded = tagged.assign(taxonomy_tag=tagged["taxonomy_tags"].str.split(";")).explode("taxonomy_tag")
    summary = (exploded.groupby(["model", "axis", "error_type", "taxonomy_tag"])
                      .size().reset_index(name="n")
                      .sort_values(["model", "axis", "error_type", "n"], ascending=[True, True, True, False]))
    summary.to_csv(os.path.join(outdir, "tool_sensitive_taxonomy_summary.csv"), index=False)

    # Plot top tags by model; keep simple, because full axis×tag can be large.
    for model, dm in exploded.groupby("model", observed=False):
        counts = dm["taxonomy_tag"].value_counts().reindex(TAXONOMY_LABELS).dropna()
        fig, ax = plt.subplots(figsize=(9.5, 4.2))
        ax.bar(counts.index, counts.values)
        ax.set_xticklabels(counts.index, rotation=45, ha="right")
        ax.set_ylabel("# wrong tool-sensitive unit-version reasons")
        ax.set_title(f"Tool-sensitive failure taxonomy — {model}")
        ax.spines[["top", "right"]].set_visible(False)
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"deep3_tool_sensitive_taxonomy_{model}.png"), dpi=200)
        plt.close()

    return tagged, summary


# -------------------------------- main ---------------------------------------
def run(CFG):
    os.makedirs(CFG["OUT"], exist_ok=True)
    gem_all, hum_all = [], []
    for short, sub in CFG["MODELS"].items():
        mdir = os.path.join(CFG["BASE"], sub)
        hp = CFG["HUMAN"][short]
        if not os.path.exists(hp):
            print(f"!! human GT 없음: {hp}"); continue
        h = load_human(short, hp, CFG["HUMAN_SHEET"]); hum_all.append(h)
        if CFG["INSPECT"]:
            print(f"\n=== [{short}] HUMAN rows={len(h)} axes={sorted(h.axis.dropna().unique())} "
                  f"label={h.h.value_counts(dropna=False).to_dict()}")
        for version, fname in CFG["VERSIONS"].items():
            p = os.path.join(mdir, fname)
            if not os.path.exists(p):
                print(f"   (skip) {short}/{version}: 없음 {fname}"); continue
            g_pe = load_gemini_per_event(short, version, p)
            gem_all.append(g_pe)
            g_rel, item_path = load_gemini_tc_relation(short, version, p)
            if len(g_rel): gem_all.append(g_rel)
            if CFG["INSPECT"]:
                g_tmp = pd.concat([g_pe, g_rel], ignore_index=True) if len(g_rel) else g_pe
                rel_msg = f", TC-Relation from {os.path.basename(item_path)} n={len(g_rel)}" if len(g_rel) else ", TC-Relation n=0"
                print(f"--- [{short}] {version:8s} per_event_rows={len(g_pe)} "
                      f"axes={sorted(g_tmp.axis.dropna().unique())}{rel_msg} "
                      f"g={g_tmp.g.value_counts(dropna=False).to_dict()}")

    if not gem_all:
        raise RuntimeError("Gemini 결과를 하나도 읽지 못했습니다. BASE/MODELS/VERSIONS 경로를 확인하세요.")
    if not hum_all:
        raise RuntimeError("Human GT를 하나도 읽지 못했습니다. HUMAN 경로를 확인하세요.")

    gem = pd.concat(gem_all, ignore_index=True)
    hum = pd.concat(hum_all, ignore_index=True)

    keep = lambda s: s.str.contains("_rel_", case=False, na=False) & ~s.str.contains("_abs_", case=False, na=False)
    gem, hum = gem[keep(gem.video_file)].copy(), hum[keep(hum.video_file)].copy()

    dk = ["model","video_file","event","axis","version"]
    conflict = int((gem.groupby(dk)["g"].nunique(dropna=True) > 1).sum())
    if conflict:
        print(f"[warn] 같은 (unit,version)에 상충하는 gemini verdict {conflict}건 -> first 사용(데이터 점검 권장)")
    n0 = len(gem); gem = gem.drop_duplicates(dk, keep="first")
    if len(gem) != n0:
        print(f"[info] 중복 gemini 행 {n0-len(gem)}개 제거")

    if CFG["INSPECT"]:
        gk = gem[KEY].drop_duplicates(); hk = hum[KEY].drop_duplicates()
        merged = gk.merge(hk, on=KEY, how="inner")
        print(f"\n[INSPECT] human units={len(hk)} axis별={hk.axis.value_counts().to_dict()}")
        print(f"[INSPECT] gemini units={len(gk)} axis별={gk.axis.value_counts().to_dict()}")
        print(f"[INSPECT] 비교 가능 교집합={len(merged)} axis별={merged.axis.value_counts().to_dict()}")
        only_g = gk.merge(hk, on=KEY, how="left", indicator=True).query('_merge=="left_only"')
        nonv1 = only_g[~only_g.video_file.str.contains("_v1_", case=False, na=False)]
        print(f"[INSPECT] 매칭 안 된 gemini 유닛 {len(only_g)}개 중 v1 이외(변종) = {len(nonv1)}개")
        v1_unmatched = only_g[only_g.video_file.str.contains("_v1_", case=False, na=False)]
        if len(v1_unmatched):
            print("[INSPECT] (주의) v1인데 매칭 안 된 유닛 — video_file/event/axis 포맷 점검 필요:")
            print(v1_unmatched.head(30).to_string(index=False))
        else:
            print("[INSPECT] v1 유닛은 전부 매칭됨 ✓  -> INSPECT=False 로 바꿔 본실행 OK")
        return

    # ---- merge & disagreement ----
    m = gem.merge(hum[KEY + ["h", "event_text", "hand_condition"]], on=KEY, how="inner")
    m = m.dropna(subset=["g", "h"])
    m["disagree"] = (m.g != m.h).astype(int)
    m = add_error_direction(m)
    print(f"[join] 비교쌍={len(m)}  units={m[KEY].drop_duplicates().shape[0]}  axis별={m.axis.value_counts().to_dict()}")

    order = [v for v in CFG["VERSIONS"] if v in set(m.version)]

    # =========================== stability matrix ===========================
    mat = m.pivot_table(index=KEY, columns="version", values="disagree", aggfunc="first").reindex(columns=order)
    np_ = mat.notna().sum(1); nd_ = mat.sum(1, skipna=True)
    cls = pd.Series(np.where(np_ == 0, "no_data",
                    np.where(nd_ == 0, "solved",
                    np.where(nd_ == np_, "stable_wrong", "tool_sensitive"))), index=mat.index)
    attr = (m.sort_values("version").groupby(KEY)
              .agg(event_kind=("event_kind", "first"),
                   hand_condition=("hand_condition", "first"),
                   event_text=("event_text", "first"),
                   human_label=("h", "first"))).reset_index()
    out = mat.reset_index().assign(n_present=np_.values, n_disagree=nd_.values, **{"class": cls.values})
    out = out.merge(attr, on=KEY, how="left")
    out.to_csv(os.path.join(CFG["OUT"], "stability_matrix.csv"), index=False)

    # Attach stability class back to merged rows for class-conditioned FP/FN analysis.
    m = m.merge(out[KEY + ["class", "n_present", "n_disagree"]], on=KEY, how="left")
    m.to_csv(os.path.join(CFG["OUT"], "merged_long_with_direction.csv"), index=False)

    stable = out[out["class"] == "stable_wrong"].sort_values(["model", "axis", "video_file", "event"])
    stable.to_csv(os.path.join(CFG["OUT"], "stable_wrong_units.csv"), index=False)

    sw_key = stable[KEY]
    g_sw = gem.merge(sw_key, on=KEY, how="inner")
    reasons = (g_sw.pivot_table(index=KEY, columns="version", values="reason", aggfunc="first")
                   .reindex(columns=order).reset_index())
    reasons = reasons.merge(attr, on=KEY, how="left")
    reasons.to_csv(os.path.join(CFG["OUT"], "stable_wrong_with_reasons.csv"), index=False)

    summary = (out.groupby(["model", "axis", "class"]).size().unstack(fill_value=0)
                  .reindex(columns=["solved", "tool_sensitive", "stable_wrong"], fill_value=0))
    summary.to_csv(os.path.join(CFG["OUT"], "class_summary_by_axis.csv"))
    print("\n[summary]\n", summary)
    print(f"\n[stable_wrong] {len(stable)} units / 전체 {len(out)} -> stable_wrong_with_reasons.csv")

    # ============================= original plots ===========================
    pal = {"solved":"#cfd8dc", "tool_sensitive":"#f4a259", "stable_wrong":"#c1121f"}
    models = list(CFG["MODELS"])

    fig, axs = plt.subplots(1, len(models), figsize=(6*len(models),4.6), sharey=True, squeeze=False)
    for j, model in enumerate(models):
        ax = axs[0][j]
        here = [a for a in AXES if (model, a) in summary.index]
        bottoms = np.zeros(len(here))
        for c in ["solved", "tool_sensitive", "stable_wrong"]:
            vals = [summary.loc[(model,a),c] for a in here]
            ax.bar(here, vals, bottom=bottoms, color=pal[c], label=c); bottoms += np.array(vals)
        ax.set_title(model); ax.spines[["top", "right"]].set_visible(False)
        if j == 0: ax.set_ylabel("# of units"); ax.legend(frameon=False)
    fig.suptitle("Error stability by axis  (red = wrong in ALL versions = fixed blind spot)")
    plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"], "stab1_class_by_axis.png"), dpi=200); plt.close()

    ts = out[out["class"] == "tool_sensitive"]
    if len(ts):
        H = ts[order].fillna(-1).values
        lab = (ts.model + " | " + ts.video_file.str.replace("_v1_raw.mp4", "", regex=False)
               + " | " + ts.event + " | " + ts.axis).values
        fig, ax = plt.subplots(figsize=(1.1*len(order)+4, max(3, 0.3*len(ts))))
        cmap = matplotlib.colors.ListedColormap(["#e9ecef", "#dff0d8", "#c1121f"])
        ax.imshow(H, aspect="auto", cmap=cmap, vmin=-1, vmax=1)
        ax.set_xticks(range(len(order))); ax.set_xticklabels(order, rotation=90)
        ax.set_yticks(range(len(ts))); ax.set_yticklabels(lab, fontsize=6)
        ax.set_title("tool_sensitive units (red=disagree, green=agree, grey=absent)")
        plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"], "stab2_tool_sensitive_heatmap.png"), dpi=200); plt.close()

    rate = (m.groupby(["model", "version"])["disagree"].mean().mul(100)
              .unstack(0).reindex(order))
    ax = rate.plot(kind="bar", figsize=(11,4.6), color=["#2c6fbb", "#e07b39"])
    ax.set_ylabel("disagreement w/ human GT (%)"); ax.set_xlabel("")
    ax.set_title("Per-version disagreement rate (recomputed from raw; includes TC-Relation)")
    ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False, title="model")
    plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"], "stab3_disagreement_rate.png"), dpi=200); plt.close()

    # ============================= deep analyses ============================
    direction = summarize_direction(m, CFG["OUT"], order)
    per_event_stats = summarize_per_event_stats(m, CFG["OUT"], order)

    m_cascade = add_cascade_flags(m)
    collapsed_units = collapse_unit_stability(out)
    cascade_ver, cascade_axis, unit_summary = summarize_cascade(m_cascade, collapsed_units, CFG["OUT"], order)

    tagged, taxonomy_summary = summarize_tool_sensitive_taxonomy(m, out, CFG["OUT"], order, CFG)

    print("\n[deep1] FP/FN direction outputs:")
    print("   - merged_long_with_direction.csv")
    print("   - direction_counts_by_axis_version.csv")
    print("   - direction_counts_by_class_axis_version.csv")
    for model in models:
        print(f"   - deep1_fp_fn_by_axis_version_{model}.png")
        print(f"   - deep1_fp_fn_by_axis_version_counts_{model}.png")
        print(f"   - deep1b_fp_fn_tool_sensitive_{model}.png")
        print(f"   - deep1b_fp_fn_tool_sensitive_counts_{model}.png")

    print("\n[deep2] cascade collapse outputs:")
    print("   - cascade_per_version_errors.csv")
    print("   - cascade_independent_error_count_by_version.csv")
    print("   - cascade_summary_by_axis_version.csv")
    print("   - collapsed_stability_matrix.csv")
    print("   - collapsed_unit_summary_by_class.csv")
    for model in models:
        print(f"   - deep2_cascade_raw_vs_independent_{model}.png")
    if not unit_summary.empty:
        print("\n[collapsed unit summary]\n", unit_summary)

    print("\n[deep3] taxonomy outputs:")
    print("   - tool_sensitive_wrong_reasons_tagged.csv")
    print("   - tool_sensitive_taxonomy_summary.csv")
    print("   - tool_sensitive_taxonomy_prompts.jsonl")
    for model in models:
        print(f"   - deep3_tool_sensitive_taxonomy_{model}.png")

    print("\n[done] ->", CFG["OUT"])


# ============================== CONFIG =====================================
if __name__ == "__main__":
    CFG = dict(
        BASE   = "/home/coder/T2AV/eval_results/gemini",
        MODELS = {"LTX":"LTX-2.3", "MOVA":"MOVA"},
        VERSIONS = {
            "NoTool":"NoTools_per_event.csv", "MediaPipe":"MediaPipe_per_event.csv",
            "Whisper":"Whisper_per_event.csv", "CLAP":"CLAP_per_event.csv",
            "M+W":"MediaPipe_Whisper_per_event.csv", "M+C":"MediaPipe_CLAP_per_event.csv",
            "W+C":"Whisper_CLAP_per_event.csv", "M+W+C":"AllTools_per_event.csv",
            "ICL":"NoTools_per_event-ICL.csv",
        },
        HUMAN = {
            "LTX":  "/home/coder/T2AV/eval_results/human/YS_eval_annotation_ltx.xlsx",
            "MOVA": "/home/coder/T2AV/eval_results/human/YS_eval_annotation_mova.xlsx",
        },
        HUMAN_SHEET = "Annotation",
        INSPECT = False,
        OUT = "/home/coder/T2AV/eval_results/new-analysis/stability_deep",

        # Taxonomy tagging. Default is deterministic heuristic tagging.
        # For Gemini LLM tagging:
        #   pip install -U google-genai
        #   export GEMINI_API_KEY="YOUR_API_KEY"
        #   USE_LLM_TAXONOMY = True
        #   LLM_PROVIDER = "gemini"
        USE_LLM_TAXONOMY = False,
        LLM_PROVIDER = "gemini",   # "gemini", "openai", or any other value for heuristic fallback
        GEMINI_MODEL = "gemini-3.1-pro",
        OPENAI_MODEL = "gpt-4o-mini",
        VERBOSE_LLM_ERRORS = True,
    )
    run(CFG)
