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
     - More defensible mode: induce a codebook from observed reasons, save it,
       then rerun with the frozen/manual codebook for reproducibility.
     - Optional Gemini LLM tagging if CFG["USE_LLM_TAXONOMY"] = True.

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
            ax.bar(x, here["fp_rate"].fillna(0).mul(100), label="FP / hallucinate")
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


# ------------------- tool-sensitive taxonomy / grounded codebook -------------
# IMPORTANT: The old version used a hand-written TAXONOMY_LABELS list directly.
# This version makes the taxonomy defensible by separating the process into:
#   (1) collect observed wrong tool-sensitive reasons,
#   (2) induce a codebook from those reasons OR load a frozen/manual codebook,
#   (3) tag reasons using the frozen codebook,
#   (4) write audit files with definitions, examples, evidence quotes, and confidence.
#
# Recommended workflow:
#   First run:  TAXONOMY_MODE="induced", USE_LLM_TAXONOMY=True
#               -> inspect taxonomy_codebook_induced.json and taxonomy_codebook_audit_examples.csv
#   Final run:  TAXONOMY_MODE="codebook", TAXONOMY_CODEBOOK_PATH=<approved json>
#               -> use the same frozen codebook for reproducible results.

DEFAULT_TAXONOMY_LABELS = [
    "laterality_left_right",
    "slap_contact_overacceptance",
    "speech_visual_or_mouth_motion",
    "timing_order_or_sync",
    "count_or_repetition",
    "audio_or_speech_content",
    "action_identity_or_visibility",
    "tool_artifact_or_uncertainty",
    "other_unclear",
]

DEFAULT_CODEBOOK = [
    {
        "label": "laterality_left_right",
        "display_name": "Left/right or side confusion",
        "definition": "The reason indicates confusion about left/right hand, actor-centered side, body side, thigh/leg side, or opposite-side mapping.",
        "include_when": "Mentions left, right, side, hand side, thigh/leg side, or actor/viewer orientation.",
        "exclude_when": "The reason only mentions a hand/action without a side-specific error.",
    },
    {
        "label": "slap_contact_overacceptance",
        "display_name": "Contact over-accepted as slap",
        "definition": "The reason treats ambiguous contact, hit, impact, or hand-body motion as a valid slap, or hallucinates a slap-like action.",
        "include_when": "Mentions slap/slapping/hit/strike/contact/impact/thigh in a way that explains an incorrect accept/reject judgment.",
        "exclude_when": "The reason is about count/order only and does not discuss whether a slap/contact occurred.",
    },
    {
        "label": "speech_visual_or_mouth_motion",
        "display_name": "Visible speech or mouth-motion judgment",
        "definition": "The reason concerns whether the mouth/lips/person visibly speaks, talks, or moves the mouth.",
        "include_when": "Mentions mouth, lips, visible speaking, talking, or visual speech behavior.",
        "exclude_when": "The reason only concerns transcript/audio content without visual speech behavior.",
    },
    {
        "label": "timing_order_or_sync",
        "display_name": "Timing, order, or synchrony",
        "definition": "The reason concerns before/after order, simultaneous/synchronized occurrence, onset alignment, or temporal relation.",
        "include_when": "Mentions before, after, order, sequence, sync, simultaneous, aligned, onset, timing, temporal relation.",
        "exclude_when": "The reason only says an event exists/does not exist with no temporal claim.",
    },
    {
        "label": "count_or_repetition",
        "display_name": "Count or repetition",
        "definition": "The reason concerns number of occurrences, once/twice/multiple times, or repeated actions.",
        "include_when": "Mentions count, once, twice, single, multiple, repeated, repetition, number of events.",
        "exclude_when": "The reason concerns temporal order but not the number of occurrences.",
    },
    {
        "label": "audio_or_speech_content",
        "display_name": "Audio or speech-content evidence",
        "definition": "The reason concerns whether sound/speech/audio content was present, heard, transcribed, or matched the requested phrase.",
        "include_when": "Mentions audio, sound, heard, transcript, speech content, spoken words, Whisper, CLAP, or cue from audio.",
        "exclude_when": "The reason only concerns mouth motion without audio content.",
    },
    {
        "label": "action_identity_or_visibility",
        "display_name": "Action identity or visual visibility",
        "definition": "The reason concerns whether the requested action/gesture/pose is visually present, clear, occluded, or correctly identified.",
        "include_when": "Mentions visible/visibility/gesture/action/pose/thumbs-up/raise/occluded/unclear as the reason for the judgment.",
        "exclude_when": "The reason is only about left/right side or timing without action identity/visibility.",
    },
    {
        "label": "tool_artifact_or_uncertainty",
        "display_name": "Tool artifact or uncertainty",
        "definition": "The reason explicitly attributes the judgment to tool outputs, landmarks, transcripts, CLAP/Whisper/MediaPipe, or expresses uncertainty/ambiguity.",
        "include_when": "Mentions MediaPipe, landmark, CLAP, Whisper, tool, confidence, uncertain, ambiguous, likely, appears.",
        "exclude_when": "The reason merely uses normal evidence without tool/uncertainty language.",
    },
    {
        "label": "other_unclear",
        "display_name": "Other or unclear",
        "definition": "The reason does not fit the approved codebook or is too vague to tag confidently.",
        "include_when": "Use when no specific label is supported by the reason text.",
        "exclude_when": "Do not use together with a specific label unless the reason is partially unclassifiable.",
    },
]


def _strip_json_fences(raw):
    """Remove common markdown fences, but keep the payload text."""
    raw = str(raw).strip()
    # If Gemini returned a fenced block, prefer the first fenced json block.
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _first_json_value(raw):
    """Parse the first JSON value in a messy model response.

    Gemini sometimes returns valid JSON followed by extra explanatory text, or
    multiple JSON snippets. json.loads() then raises "Extra data". For this
    analysis script, the safest behavior is to recover the first JSON object or
    array and ignore trailing text, while still failing on truly malformed JSON.
    """
    txt = _strip_json_fences(raw)
    # First try strict parsing.
    try:
        return json.loads(txt)
    except Exception:
        pass

    decoder = json.JSONDecoder()
    # Try raw_decode from every plausible JSON start position.
    starts = [m.start() for m in re.finditer(r"[\{\[]", txt)]
    last_err = None
    for st in starts:
        try:
            obj, _end = decoder.raw_decode(txt[st:])
            return obj
        except json.JSONDecodeError as e:
            last_err = e
            continue

    # Last-resort: balanced bracket extraction from first object/array.
    for st in starts:
        opener = txt[st]
        closer = "}" if opener == "{" else "]"
        depth = 0
        in_str = False
        esc = False
        for i in range(st, len(txt)):
            ch = txt[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = txt[st:i+1]
                        try:
                            return json.loads(candidate)
                        except Exception as e:
                            last_err = e
                            break
    if last_err:
        raise last_err
    raise json.JSONDecodeError("No JSON object or array found", txt, 0)


def safe_json_loads(raw):
    return _first_json_value(raw)


def coerce_tagging_json(obj):
    """Normalize Gemini tagging output to a dict with labels/confidence fields."""
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        if len(obj) == 1 and isinstance(obj[0], dict):
            return obj[0]
        if all(isinstance(x, str) for x in obj):
            return {"labels": obj, "confidence": 0.7, "evidence_quote": ""}
        for x in obj:
            if isinstance(x, dict):
                return x
    return {"labels": ["other_unclear"], "confidence": 0.0, "evidence_quote": ""}


def coerce_codebook_json(obj):
    """Normalize Gemini codebook output to a codebook list."""
    if isinstance(obj, dict):
        cb = obj.get("codebook", obj.get("labels", obj.get("categories", [])))
        return cb if isinstance(cb, list) else []
    if isinstance(obj, list):
        return obj
    return []


def gemini_json(prompt, cfg):
    """Call Gemini and parse JSON. This intentionally avoids hard dependence on a single SDK schema API."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai
    client = genai.Client()
    model = cfg.get("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        from google.genai import types
        cfg_kwargs = dict(temperature=0, response_mime_type="application/json")
        thinking_level = cfg.get("GEMINI_THINKING_LEVEL", "")
        if thinking_level:
            try:
                cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
            except Exception:
                pass
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(**cfg_kwargs),
        )
    except Exception:
        # Fallback for SDK variants.
        resp = client.models.generate_content(
            model=model,
            contents=prompt + "\n\nReturn JSON only.",
            config={"temperature": 0},
        )
    return safe_json_loads(resp.text)


def normalize_codebook(codebook):
    """Validate/normalize a codebook into a list of dicts with unique snake_case labels."""
    out = []
    seen = set()
    for item in codebook or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip().lower()
        label = re.sub(r"[^a-z0-9_]+", "_", label).strip("_")
        if not label or label in seen:
            continue
        seen.add(label)
        out.append({
            "label": label,
            "display_name": str(item.get("display_name", label)).strip() or label,
            "definition": str(item.get("definition", "")).strip(),
            "include_when": str(item.get("include_when", "")).strip(),
            "exclude_when": str(item.get("exclude_when", "")).strip(),
            "example_ids": item.get("example_ids", []),
            "rationale": str(item.get("rationale", "")).strip(),
        })
    if not any(x["label"] in {"other", "other_unclear", "unclear"} for x in out):
        out.append(DEFAULT_CODEBOOK[-1].copy())
    return out


def codebook_labels(codebook):
    return [x["label"] for x in codebook]


def codebook_as_text(codebook):
    lines = []
    for i, item in enumerate(codebook, 1):
        lines.append(
            f"{i}. {item['label']}\n"
            f"   definition: {item.get('definition','')}\n"
            f"   include_when: {item.get('include_when','')}\n"
            f"   exclude_when: {item.get('exclude_when','')}"
        )
    return "\n".join(lines)


def heuristic_reason_tags_with_codebook(text, codebook=None):
    """Fallback tagger. If an induced codebook is used, this only reliably handles default labels."""
    labels = set(codebook_labels(codebook or DEFAULT_CODEBOOK))
    s = str(text).lower()
    tags = []
    def add(x):
        if x in labels:
            tags.append(x)
    add_other = "other_unclear" if "other_unclear" in labels else ("other" if "other" in labels else list(labels)[-1])
    if re.search(r"\b(left|right|hand|thigh|leg|side|opposite)\b", s):
        add("laterality_left_right")
    if re.search(r"\b(slap|slapping|strike|strikes|hit|hits|contact|impact|thigh|leg)\b", s):
        add("slap_contact_overacceptance")
    if re.search(r"\b(mouth|lip|lips|speaking|talking|visual speech|mouth motion)\b", s):
        add("speech_visual_or_mouth_motion")
    if re.search(r"\b(before|after|order|sequence|sync|synchron|simultaneous|same time|aligned|onset|timing|temporal)\b", s):
        add("timing_order_or_sync")
    if re.search(r"\b(count|once|twice|three|repetition|repeated|number|single|multiple)\b", s):
        add("count_or_repetition")
    if re.search(r"\b(audio|sound|heard|hear|clap|whisper|transcript|spoken|speech content|voice|utterance|says|said)\b", s):
        add("audio_or_speech_content")
    if re.search(r"\b(visible|visibility|gesture|action|pose|thumb|thumbs|raise|raised|unclear|occluded|not clear)\b", s):
        add("action_identity_or_visibility")
    if re.search(r"\b(mediapipe|landmark|clap|whisper|tool|confidence|uncertain|ambiguous|likely|appears)\b", s):
        add("tool_artifact_or_uncertainty")
    return list(dict.fromkeys(tags)) or [add_other]


def build_taxonomy_discovery_sample(ts_wrong, cfg):
    """Balanced sample of observed wrong reasons for taxonomy induction."""
    max_rows = int(cfg.get("MAX_TAXONOMY_DISCOVERY_ROWS", 250))
    sample_parts = []
    group_cols = ["model", "axis", "error_type"]
    # Deterministic balanced sampling so the induced codebook is reproducible.
    for _, g in ts_wrong.sort_values(KEY + ["version"]).groupby(group_cols, observed=False):
        n = max(1, min(len(g), max_rows // max(1, ts_wrong.groupby(group_cols, observed=False).ngroups)))
        sample_parts.append(g.head(n))
    sample = pd.concat(sample_parts, ignore_index=True) if sample_parts else ts_wrong.head(max_rows).copy()
    if len(sample) > max_rows:
        sample = sample.head(max_rows)
    rows = []
    for i, r in enumerate(sample.itertuples(index=False), 1):
        rows.append({
            "id": f"R{i:04d}",
            "model": r.model,
            "axis": r.axis,
            "version": r.version,
            "error_type": r.error_type,
            "event": r.event,
            "event_text": str(getattr(r, "event_text", "")),
            "reason": str(getattr(r, "reason", "")),
        })
    return rows


def induce_taxonomy_codebook(ts_wrong, outdir, cfg):
    """Induce a taxonomy from observed reasons, or load/fallback to a predefined/manual codebook."""
    mode = str(cfg.get("TAXONOMY_MODE", "default")).lower().strip()
    codebook_path = cfg.get("TAXONOMY_CODEBOOK_PATH")
    if mode in {"codebook", "manual", "frozen"} and codebook_path:
        with open(codebook_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        codebook = obj.get("codebook", obj) if isinstance(obj, dict) else obj
        codebook = normalize_codebook(codebook)
        source = f"loaded:{codebook_path}"
    elif mode in {"induced", "discover", "llm_induced"} and cfg.get("USE_LLM_TAXONOMY", False):
        sample_rows = build_taxonomy_discovery_sample(ts_wrong, cfg)
        with open(os.path.join(outdir, "taxonomy_discovery_input.jsonl"), "w", encoding="utf-8") as f:
            for obj in sample_rows:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        prompt = f"""
You are creating a defensible qualitative codebook for error analysis.

Task:
- Read the observed wrong tool-sensitive failure reasons below.
- Induce 6 to 10 recurring failure-mode labels from the data itself.
- Do NOT simply reuse axis names such as A/V/AVB/TC as labels.
- Labels should describe semantic causes of failure, not metric categories.
- Prefer labels that are supported by multiple observed reasons.
- Include one catch-all label named other_unclear.
- For each label, provide a snake_case label, display_name, definition, include_when, exclude_when, rationale, and 3-8 example_ids from the provided rows.

Return strict JSON only:
{{"codebook": [{{"label":"...", "display_name":"...", "definition":"...", "include_when":"...", "exclude_when":"...", "rationale":"...", "example_ids":["R0001"]}}]}}

Observed reason rows:
{json.dumps(sample_rows, ensure_ascii=False, indent=2)}
""".strip()
        try:
            obj = gemini_json(prompt, cfg)
            codebook = normalize_codebook(coerce_codebook_json(obj))
            source = "llm_induced_from_observed_reasons"
        except Exception as e:
            if cfg.get("VERBOSE_LLM_ERRORS", False):
                print(f"[warn] taxonomy induction failed: {type(e).__name__}: {e}")
            if cfg.get("FAIL_ON_LLM_TAXONOMY_ERROR", False):
                raise
            codebook = normalize_codebook(DEFAULT_CODEBOOK)
            source = "fallback_default_codebook_after_failed_induction"
    else:
        codebook = normalize_codebook(DEFAULT_CODEBOOK)
        source = "default_predefined_codebook"

    payload = {
        "source": source,
        "note": "For publication/reporting, inspect this codebook and rerun with TAXONOMY_MODE='codebook' and TAXONOMY_CODEBOOK_PATH pointing to the approved frozen JSON.",
        "codebook": codebook,
    }
    with open(os.path.join(outdir, "taxonomy_codebook_used.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return codebook, source


def tag_reason_with_codebook(row_obj, codebook, cfg):
    """Tag one reason with the approved codebook; returns tags, confidence, evidence, method."""
    reason = str(row_obj.get("reason", ""))
    if not cfg.get("USE_LLM_TAXONOMY", False):
        tags = heuristic_reason_tags_with_codebook(reason, codebook)
        return tags, 0.50, "", "heuristic_codebook"

    prompt = f"""
Classify this wrong tool-sensitive failure reason using the frozen codebook.

Rules:
- Use only labels from the codebook.
- Select 1 to 3 labels.
- Choose labels only when supported by the reason text or metadata.
- Provide a short evidence quote from the reason whenever possible.
- Provide confidence from 0.0 to 1.0.
- If no label fits, use other_unclear.

Codebook:
{codebook_as_text(codebook)}

Metadata:
{json.dumps({k: row_obj.get(k, "") for k in ["model", "axis", "version", "error_type", "event", "event_text", "g", "h"]}, ensure_ascii=False)}

Failure reason:
{reason}

Return strict JSON only:
{{"labels": ["..."], "confidence": 0.0, "evidence_quote": "...", "short_reason": "..."}}
""".strip()
    labels_allowed = set(codebook_labels(codebook))
    try:
        obj = coerce_tagging_json(gemini_json(prompt, cfg))
        raw_labels = obj.get("labels", [])
        if isinstance(raw_labels, str):
            raw_labels = [raw_labels]
        labels = [str(x).strip() for x in raw_labels if str(x).strip() in labels_allowed]
        if not labels:
            labels = ["other_unclear" if "other_unclear" in labels_allowed else sorted(labels_allowed)[-1]]
        try:
            conf = float(obj.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        evidence = str(obj.get("evidence_quote", ""))[:300]
        return labels[:3], conf, evidence, "llm_gemini_codebook"
    except Exception as e:
        if cfg.get("VERBOSE_LLM_ERRORS", False):
            print(f"[warn] Gemini codebook tagging failed: {type(e).__name__}: {e}")
        if cfg.get("FAIL_ON_LLM_TAXONOMY_ERROR", False):
            raise
        tags = heuristic_reason_tags_with_codebook(reason, codebook)
        return tags, 0.50, "", "heuristic_after_llm_failure"




def coerce_batch_tagging_json(obj):
    """Normalize Gemini batch tagging output into a list of item dicts."""
    if isinstance(obj, dict):
        items = obj.get("items", obj.get("results", obj.get("tags", [])))
        if isinstance(items, list):
            return items
        if all(k in obj for k in ["id", "labels"]):
            return [obj]
    if isinstance(obj, list):
        return obj
    return []


def tag_reasons_with_codebook_batch(row_objs, codebook, cfg):
    """Tag multiple unique reason rows in one Gemini call."""
    if not cfg.get("USE_LLM_TAXONOMY", False):
        out = {}
        for row in row_objs:
            tags = heuristic_reason_tags_with_codebook(row.get("reason", ""), codebook)
            out[row["id"]] = (tags, 0.50, "", "heuristic_codebook")
        return out

    labels_allowed = set(codebook_labels(codebook))
    batch_payload = []
    for row in row_objs:
        batch_payload.append({
            "id": row.get("id", ""),
            "model": row.get("model", ""),
            "axis": row.get("axis", ""),
            "version": row.get("version", ""),
            "error_type": row.get("error_type", ""),
            "event": row.get("event", ""),
            "event_text": row.get("event_text", ""),
            "g": row.get("g", ""),
            "h": row.get("h", ""),
            "reason": row.get("reason", ""),
        })

    prompt = f"""
Classify each wrong tool-sensitive failure reason using the frozen codebook.

Rules:
- Use only labels from the codebook.
- For each item, select 1 to 3 labels.
- Choose labels only when supported by the reason text or metadata.
- Provide a short evidence quote from the reason whenever possible.
- Provide confidence from 0.0 to 1.0.
- If no label fits, use other_unclear.
- Return one result for every input id.

Codebook:
{codebook_as_text(codebook)}

Items:
{json.dumps(batch_payload, ensure_ascii=False, indent=2)}

Return strict JSON only in this schema:
{{"items": [{{"id":"...", "labels":["..."], "confidence":0.0, "evidence_quote":"...", "short_reason":"..."}}]}}
""".strip()

    try:
        obj = gemini_json(prompt, cfg)
        items = coerce_batch_tagging_json(obj)
        out = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("id", "")).strip()
            # Gemini sometimes returns a valid single-item classification but drops the id.
            # In that case, safely restore the only possible input id instead of failing.
            if not iid and len(row_objs) == 1:
                iid = row_objs[0]["id"]
            if not iid:
                continue
            raw_labels = item.get("labels", [])
            if isinstance(raw_labels, str):
                raw_labels = [raw_labels]
            labels = [str(x).strip() for x in raw_labels if str(x).strip() in labels_allowed]
            if not labels:
                labels = ["other_unclear" if "other_unclear" in labels_allowed else sorted(labels_allowed)[-1]]
            try:
                conf = float(item.get("confidence", 0.0))
            except Exception:
                conf = 0.0
            conf = max(0.0, min(1.0, conf))
            evidence = str(item.get("evidence_quote", ""))[:300]
            out[iid] = (labels[:3], conf, evidence, "llm_gemini_codebook_batch")

        missing = [row["id"] for row in row_objs if row["id"] not in out]
        if missing:
            # Pro models occasionally omit a subset of ids in a large batch even when JSON is valid.
            # Do not discard the successful ids. Retry only omitted ids with smaller batches;
            # if a single-id retry still omits the id, fail loudly in strict mode.
            if cfg.get("RETRY_OMITTED_IDS", True) and len(row_objs) > 1:
                depth = int(cfg.get("_BATCH_RETRY_DEPTH", 0))
                id_to_row = {row["id"]: row for row in row_objs}
                retry_rows = [id_to_row[mid] for mid in missing if mid in id_to_row]
                retry_size = 5 if depth == 0 else 1
                if cfg.get("VERBOSE_LLM_ERRORS", False):
                    print(f"[warn] Gemini omitted {len(missing)} ids; retrying omitted ids with batch_size={retry_size}")
                retry_cfg = dict(cfg)
                retry_cfg["_BATCH_RETRY_DEPTH"] = depth + 1
                for i in range(0, len(retry_rows), retry_size):
                    sub = retry_rows[i:i+retry_size]
                    out.update(tag_reasons_with_codebook_batch(sub, codebook, retry_cfg))
                still_missing = [row["id"] for row in row_objs if row["id"] not in out]
                if still_missing:
                    raise RuntimeError(f"Gemini batch tagging still omitted {len(still_missing)} ids after retry, e.g. {still_missing[:5]}")
            else:
                raise RuntimeError(f"Gemini batch tagging omitted {len(missing)} ids, e.g. {missing[:5]}")
        return out
    except Exception as e:
        if cfg.get("VERBOSE_LLM_ERRORS", False):
            print(f"[warn] Gemini batch codebook tagging failed: {type(e).__name__}: {e}")
        if cfg.get("FAIL_ON_LLM_TAXONOMY_ERROR", False):
            raise
        out = {}
        for row in row_objs:
            tags = heuristic_reason_tags_with_codebook(row.get("reason", ""), codebook)
            out[row["id"]] = (tags, 0.50, "", "heuristic_after_llm_failure")
        return out


def summarize_tool_sensitive_taxonomy(m, out, outdir, order, cfg):
    """Grounded taxonomy analysis for wrong reasons in tool-sensitive units, with dedup + batch LLM tagging."""
    ts_keys = out.loc[out["class"] == "tool_sensitive", KEY].drop_duplicates()
    if len(ts_keys) == 0:
        return pd.DataFrame(), pd.DataFrame()

    ts = m.merge(ts_keys, on=KEY, how="inner")
    ts_wrong = ts[ts["disagree"] == 1].copy()
    if len(ts_wrong) == 0:
        return pd.DataFrame(), pd.DataFrame()

    codebook, codebook_source = induce_taxonomy_codebook(ts_wrong, outdir, cfg)
    labels = codebook_labels(codebook)

    # Build row objects for all wrong tool-sensitive unit-version rows.
    all_row_objs = []
    for i, r in enumerate(ts_wrong.itertuples(index=False), 1):
        reason = str(getattr(r, "reason", ""))
        uid = hashlib.md5("||".join([r.model, r.video_file, r.event, r.axis, r.version]).encode()).hexdigest()[:12]
        row_obj = {
            "id": uid,
            "model": r.model,
            "video_file": r.video_file,
            "event": r.event,
            "axis": r.axis,
            "version": r.version,
            "g": float(r.g),
            "h": float(r.h),
            "error_type": r.error_type,
            "event_text": str(getattr(r, "event_text", "")),
            "reason": reason,
        }
        # Dedup key: same semantic evidence should receive the same taxonomy label.
        # Include axis/error_type/event_text because the same reason phrase can mean different things across axes.
        dedup_payload = {
            "axis": row_obj["axis"],
            "error_type": row_obj["error_type"],
            "event_text": row_obj["event_text"],
            "reason": row_obj["reason"],
        }
        row_obj["_tag_key"] = hashlib.md5(json.dumps(dedup_payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        all_row_objs.append(row_obj)

    # Tag only unique reason/context rows, then copy labels back to all rows.
    dedup_enabled = bool(cfg.get("TAXONOMY_DEDUP", True))
    unique_by_key = {}
    for row in all_row_objs:
        key = row["_tag_key"] if dedup_enabled else row["id"]
        if key not in unique_by_key:
            u = row.copy()
            u["id"] = key  # batch result id becomes the dedup key
            unique_by_key[key] = u
    unique_rows = list(unique_by_key.values())

    batch_size = int(cfg.get("TAXONOMY_TAGGING_BATCH_SIZE", 25))
    tag_cache = {}
    cache_path = os.path.join(outdir, "taxonomy_tag_cache.json")
    if cfg.get("TAXONOMY_USE_CACHE", True) and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                raw_cache = json.load(f)
            for k, v in raw_cache.items():
                tag_cache[k] = (v.get("labels", ["other_unclear"]), float(v.get("confidence", 0.0)), v.get("evidence_quote", ""), v.get("method", "cache"))
        except Exception:
            tag_cache = {}

    to_tag = [r for r in unique_rows if r["id"] not in tag_cache]
    print(f"[taxonomy] reason rows={len(all_row_objs)} unique_to_tag={len(unique_rows)} cache_hit={len(unique_rows)-len(to_tag)} batch_size={batch_size}")

    for st in range(0, len(to_tag), batch_size):
        batch = to_tag[st:st+batch_size]
        print(f"[taxonomy] tagging batch {st//batch_size + 1}/{(len(to_tag)+batch_size-1)//batch_size} (n={len(batch)})")
        batch_result = tag_reasons_with_codebook_batch(batch, codebook, cfg)
        tag_cache.update(batch_result)
        if cfg.get("TAXONOMY_USE_CACHE", True):
            serializable = {k: {"labels": v[0], "confidence": v[1], "evidence_quote": v[2], "method": v[3]} for k, v in tag_cache.items()}
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)

    rows = []
    prompt_rows = []
    for row_obj in all_row_objs:
        key = row_obj["_tag_key"] if dedup_enabled else row_obj["id"]
        tags, conf, evidence, method = tag_cache[key]
        clean_obj = {k: v for k, v in row_obj.items() if not k.startswith("_")}
        prompt_rows.append({**clean_obj, "codebook_labels": labels, "tag_key": key})
        rows.append({
            **clean_obj,
            "taxonomy_tags": ";".join(tags),
            "taxonomy_confidence": conf,
            "taxonomy_evidence_quote": evidence,
            "tagging_method": method,
            "codebook_source": codebook_source,
            "tag_key": key,
        })

    tagged = pd.DataFrame(rows)
    tagged.to_csv(os.path.join(outdir, "tool_sensitive_wrong_reasons_tagged.csv"), index=False)

    with open(os.path.join(outdir, "tool_sensitive_taxonomy_tagging_input.jsonl"), "w", encoding="utf-8") as f:
        for obj in prompt_rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    exploded = tagged.assign(taxonomy_tag=tagged["taxonomy_tags"].str.split(";")).explode("taxonomy_tag")

    # Reason-level summary: one wrong unit-version reason can contribute multiple labels.
    summary = (exploded.groupby(["model", "axis", "error_type", "taxonomy_tag"])
                      .size().reset_index(name="n_reason_labels")
                      .sort_values(["model", "axis", "error_type", "n_reason_labels"], ascending=[True, True, True, False]))
    summary.to_csv(os.path.join(outdir, "tool_sensitive_taxonomy_summary_reason_level.csv"), index=False)
    summary.to_csv(os.path.join(outdir, "tool_sensitive_taxonomy_summary.csv"), index=False)

    # Unique-unit summary: reduces repeated version-counting.
    unit_exploded = exploded.drop_duplicates(KEY + ["taxonomy_tag"])
    unit_summary = (unit_exploded.groupby(["model", "axis", "taxonomy_tag"])
                                 .size().reset_index(name="n_unique_units")
                                 .sort_values(["model", "axis", "n_unique_units"], ascending=[True, True, False]))
    unit_summary.to_csv(os.path.join(outdir, "tool_sensitive_taxonomy_summary_unique_units.csv"), index=False)

    # Confidence / audit summaries.
    conf_summary = (tagged.groupby(["model", "axis"])
                          .agg(n=("id", "size"),
                               mean_confidence=("taxonomy_confidence", "mean"),
                               low_confidence_n=("taxonomy_confidence", lambda x: int((x < 0.6).sum())))
                          .reset_index())
    conf_summary.to_csv(os.path.join(outdir, "taxonomy_confidence_summary.csv"), index=False)

    # Representative examples for auditing each label.
    ex_rows = []
    for tag, dm in exploded.sort_values("taxonomy_confidence", ascending=False).groupby("taxonomy_tag"):
        for rr in dm.head(int(cfg.get("TAXONOMY_EXAMPLES_PER_LABEL", 8))).itertuples(index=False):
            ex_rows.append({
                "taxonomy_tag": tag,
                "model": rr.model,
                "axis": rr.axis,
                "version": rr.version,
                "error_type": rr.error_type,
                "video_file": rr.video_file,
                "event": rr.event,
                "confidence": rr.taxonomy_confidence,
                "evidence_quote": rr.taxonomy_evidence_quote,
                "reason": rr.reason,
            })
    pd.DataFrame(ex_rows).to_csv(os.path.join(outdir, "taxonomy_codebook_audit_examples.csv"), index=False)

    coverage = {
        "n_wrong_tool_sensitive_reason_rows": int(len(tagged)),
        "n_unique_tool_sensitive_units_with_wrong_versions": int(tagged[KEY].drop_duplicates().shape[0]),
        "n_unique_tagged_reason_contexts": int(len(unique_rows)),
        "n_labels_in_codebook": int(len(labels)),
        "multi_label_rate": float((tagged["taxonomy_tags"].str.contains(";")).mean()),
        "other_unclear_reason_rows": int(exploded[exploded["taxonomy_tag"].isin(["other", "other_unclear", "unclear"])].shape[0]),
        "mean_confidence": float(tagged["taxonomy_confidence"].mean()),
        "codebook_source": codebook_source,
        "tagging_method_counts": tagged["tagging_method"].value_counts().to_dict(),
    }
    with open(os.path.join(outdir, "taxonomy_coverage_summary.json"), "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)

    # Plot top tags by model, reason-level count. Use the induced codebook order.
    for model, dm in exploded.groupby("model", observed=False):
        counts = dm["taxonomy_tag"].value_counts().reindex(labels).dropna()
        fig, ax = plt.subplots(figsize=(10.5, 4.4))
        ax.bar(counts.index, counts.values)
        ax.set_xticks(range(len(counts.index)))
        ax.set_xticklabels(counts.index, rotation=45, ha="right")
        ax.set_ylabel("# wrong tool-sensitive unit-version reason labels")
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
        print(f"   - deep1b_fp_fn_tool_sensitive_{model}.png")

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
        OUT = "/home/coder/T2AV/eval_results/new-analysis/stability_deep_gemini_strict",

        # Taxonomy tagging. Default is deterministic heuristic tagging.
        # For Gemini LLM tagging:
        #   pip install -U google-genai
        #   export GEMINI_API_KEY="YOUR_API_KEY"
        #   USE_LLM_TAXONOMY = True
        #   LLM_PROVIDER = "gemini"
        USE_LLM_TAXONOMY = True,
        TAXONOMY_MODE = "induced",
        TAXONOMY_CODEBOOK_PATH = "",
        FAIL_ON_LLM_TAXONOMY_ERROR = True,
        LLM_PROVIDER = "gemini",   # "gemini", "openai", or any other value for heuristic fallback
        GEMINI_MODEL = "gemini-3.1-pro-preview",
        OPENAI_MODEL = "gpt-4o-mini",
        GEMINI_THINKING_LEVEL = "low",
        TAXONOMY_DEDUP = True,
        TAXONOMY_TAGGING_BATCH_SIZE = 25,
        TAXONOMY_USE_CACHE = True,
        RETRY_OMITTED_IDS = True,
        MAX_TAXONOMY_DISCOVERY_ROWS = 120,
        VERBOSE_LLM_ERRORS = True,
    )
    run(CFG)
