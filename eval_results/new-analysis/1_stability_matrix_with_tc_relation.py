#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오류 안정성(stability) 분석 — raw per_event CSV + item-level CSV + human GT(xlsx)에서 재계산.

단위 = (model, video_file, event, axis).  각 단위에서 9개 버전 중 몇 개가
human GT와 불일치하는지 세어 분류:
  stable_wrong   : 존재하는 모든 버전이 불일치 -> Gemini 고정 blind spot (손으로 읽을 작은 집합)
  tool_sensitive : 일부 버전만 불일치          -> tool on/off가 좌우 (heatmap)
  solved         : 전 버전 일치                -> 무시

스키마:
  GEMINI per_event.csv : video_file, item_id, event_id, axis, label(yes/no), event_kind, reason ...
    - A / V / AVB / TC-Count 를 읽음.
    - TC-Count 는 label 대신 count_correct 에 verdict 가 들어있을 수 있음.
  GEMINI item-level CSV : NoTools.csv, MediaPipe.csv, ..., NoTools-ICL.csv 등
    - TC-Relation 은 event-level 이 아니라 item-level 이므로 여기에서 추가로 읽음.
    - wide schema 와 long schema 를 둘 다 최대한 지원함.
  HUMAN xlsx 'Annotation' 시트(헤더 1행): video_file, row_id, axis, human_label(yes/no),
                                          event, hand_condition ...
  human event 는 row_id('..__01event_1__V')의 가운데 토큰에서 추출.
  TC-Relation 은 event='ITEM' 으로 맞춤.

실행: 맨 아래 CONFIG의 경로만 확인 후  ->  python stability_matrix_with_tc_relation.py
"""
import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------- 정규화 유틸 ---------------------------------
YES = {"yes","y","true","1","1.0","pass","passed","correct","present","match","success","t"}
NO  = {"no","n","false","0","0.0","fail","failed","incorrect","absent","mismatch","failure","f"}


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
        # gemini per_event 풀네임 표기
        "audio-event-correctness":"A", "visual-event-correctness":"V",
        "audio-visual-binding":"AVB", "temporal-count-satisfaction":"TC-Count",
    }.get(s, None)


def norm_event(v):
    """'01event_1' / 'event_1' / 1 -> 'event_1'. 숫자 없으면 원문."""
    if pd.isna(v) or str(v).strip()=="" : return "ITEM"
    mm = re.search(r"(\d+)\s*$", str(v))
    if mm: return f"event_{int(mm.group(1))}"
    mm2 = re.search(r"(\d+)", str(v))
    return f"event_{int(mm2.group(1))}" if mm2 else str(v).strip()


def col(df, *names):
    low = {c.lower().strip(): c for c in df.columns}
    for n in names:                       # exact (case-insensitive)
        if n.lower() in low: return low[n.lower()]
    for n in names:                       # contains
        for c in df.columns:
            if n.lower() in c.lower(): return c
    return None


def first_col_by_keywords(df, keyword_sets, exclude_keywords=None):
    """모든 keyword 를 포함하는 첫 column 찾기. ex) [["relation", "reason"], ["order", "reason"]]."""
    exclude_keywords = [x.lower().replace("-", "_") for x in (exclude_keywords or [])]
    cols = list(df.columns)
    lows = {c: c.lower().replace(" ", "_").replace("-", "_") for c in cols}
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


# ------------------------------- 로더 --------------------------------------
def load_gemini_per_event(model, version, path):
    df = pd.read_csv(path)
    vf, ev, ax, lb = col(df,"video_file"), col(df,"event_id"), col(df,"axis"), col(df,"label")
    ek, rs, cc = col(df,"event_kind"), col(df,"reason"), col(df,"count_correct")
    if vf is None or ax is None or lb is None:
        raise ValueError(f"per_event CSV 필수 컬럼 누락: {path}")

    axis = df[ax].map(canon_axis)
    verdict = df[lb].map(to01)
    # TC-Count 는 verdict 가 label 이 아니라 count_correct 에 들어있다(label=NaN)
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
    # TC-Relation 이 per_event 에 이미 들어있으면 남겨도 되지만, item-level CSV와 중복될 수 있다.
    # 나중에 drop_duplicates(first)로 정리된다.
    return out.drop(columns="_ev").loc[out["axis"].notna()]


def companion_item_candidates(per_event_path):
    """NoTools_per_event.csv -> NoTools.csv, NoTools_per_event-ICL.csv -> NoTools-ICL.csv 등."""
    d, b = os.path.split(per_event_path)
    stem, ext = os.path.splitext(b)
    candidates = []
    if "_per_event" in stem:
        candidates.append(os.path.join(d, stem.replace("_per_event", "") + ext))
    if "per_event" in stem:
        candidates.append(os.path.join(d, stem.replace("per_event", "") + ext))
    # 혹시 별도 명명된 파일을 쓰는 경우를 위한 fallback
    candidates.append(os.path.join(d, stem.replace("_per_event", "_item") + ext))
    # 중복 제거
    seen, out = set(), []
    for p in candidates:
        if p not in seen:
            out.append(p); seen.add(p)
    return out


def first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def load_gemini_tc_relation(model, version, per_event_path):
    """TC-Relation 을 companion item-level CSV에서 읽어 event='ITEM' 단위로 반환."""
    p = first_existing(companion_item_candidates(per_event_path))
    if p is None:
        return pd.DataFrame(columns=["model","video_file","axis","g","version","event_kind","reason","event"]), None

    df = pd.read_csv(p)
    vf = col(df, "video_file", "file", "filename")
    if vf is None:
        raise ValueError(f"item-level CSV에서 video_file 컬럼을 찾지 못함: {p}")

    # 1) long schema: axis + label/verdict 가 있는 경우
    ax = col(df, "axis")
    if ax is not None:
        axis = df[ax].map(canon_axis)
        rel = df[axis == "TC-Relation"].copy()
        if len(rel):
            lb = col(rel, "label", "verdict", "correct", "satisfied", "satisfaction", "value")
            rs = col(rel, "reason", "rationale", "explanation")
            if lb is None:
                raise ValueError(f"long schema TC-Relation row 는 찾았지만 label/verdict 컬럼 없음: {p}")
            out = pd.DataFrame({
                "model": model,
                "video_file": rel[vf].astype(str).str.strip(),
                "axis": "TC-Relation",
                "g": rel[lb].map(to01),
                "version": version,
                "event_kind": "item",
                "reason": rel[rs] if rs else "",
                "event": "ITEM",
            })
            return out, p

    # 2) wide schema: temporal_relation_satisfaction 같은 column 이 있는 경우
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
        # 명시적 fallback: contains col은 오탐 가능성이 있어 마지막에만 사용
        rel_col = col(df, "tc_relation", "temporal_relation_satisfaction", "temporal_order_satisfaction", "relation_satisfaction")
    if rel_col is None:
        return pd.DataFrame(columns=["model","video_file","axis","g","version","event_kind","reason","event"]), p

    reason_col = first_col_by_keywords(df, [
        ["tc", "relation", "reason"],
        ["temporal", "relation", "reason"],
        ["temporal", "order", "reason"],
        ["relation", "reason"],
        ["order", "reason"],
        ["tc", "rel", "reason"],
    ])

    out = pd.DataFrame({
        "model": model,
        "video_file": df[vf].astype(str).str.strip(),
        "axis": "TC-Relation",
        "g": df[rel_col].map(to01),
        "version": version,
        "event_kind": "item",
        "reason": df[reason_col] if reason_col else "",
        "event": "ITEM",
    })
    return out, p


def load_human(model, path, sheet):
    df = pd.read_excel(path, sheet_name=sheet)            # 헤더 = 첫 행
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


# ------------------------------ 메인 ---------------------------------------
KEY = ["model","video_file","event","axis"]


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
            if len(g_rel):
                gem_all.append(g_rel)

            if CFG["INSPECT"]:
                axes_msg = sorted(pd.concat([g_pe, g_rel], ignore_index=True).axis.dropna().unique()) if len(g_rel) else sorted(g_pe.axis.dropna().unique())
                rel_msg = f", TC-Relation from {os.path.basename(item_path)} n={len(g_rel)}" if len(g_rel) else ", TC-Relation n=0"
                print(f"--- [{short}] {version:8s} per_event_rows={len(g_pe)} axes={axes_msg}{rel_msg} "
                      f"g={pd.concat([g_pe, g_rel], ignore_index=True).g.value_counts(dropna=False).to_dict() if len(g_rel) else g_pe.g.value_counts(dropna=False).to_dict()}")

    if not gem_all:
        raise RuntimeError("Gemini 결과를 하나도 읽지 못했습니다. BASE/MODELS/VERSIONS 경로를 확인하세요.")
    if not hum_all:
        raise RuntimeError("Human GT를 하나도 읽지 못했습니다. HUMAN 경로를 확인하세요.")

    gem = pd.concat(gem_all, ignore_index=True)
    hum = pd.concat(hum_all, ignore_index=True)

    # rel 만, abs 제외 (video_file 기준)
    keep = lambda s: s.str.contains("_rel_", case=False, na=False) & ~s.str.contains("_abs_", case=False, na=False)
    gem, hum = gem[keep(gem.video_file)].copy(), hum[keep(hum.video_file)].copy()

    # 중복 (unit,version) 정리: human은 v1만 annotate → join이 v1로 한정하지만,
    # ICL 등에서 같은 v1 행이 여러 번 들어있으면 상충 verdict 가 생길 수 있음.
    dk = ["model","video_file","event","axis","version"]
    conflict = int((gem.groupby(dk)["g"].nunique(dropna=True) > 1).sum())
    if conflict:
        print(f"[warn] 같은 (unit,version)에 상충하는 gemini verdict {conflict}건 -> first 사용(데이터 점검 권장)")
    n0 = len(gem); gem = gem.drop_duplicates(dk, keep="first")
    if len(gem) != n0:
        print(f"[info] 중복 gemini 행 {n0-len(gem)}개 제거")

    if CFG["INSPECT"]:
        # join 진단: 키가 실제로 맞물리는지
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
    m = gem.merge(hum[KEY+["h","event_text","hand_condition"]], on=KEY, how="inner")
    m = m.dropna(subset=["g","h"])
    m["disagree"] = (m.g != m.h).astype(int)
    print(f"[join] 비교쌍={len(m)}  units={m[KEY].drop_duplicates().shape[0]}  axis별={m.axis.value_counts().to_dict()}")

    order = [v for v in CFG["VERSIONS"] if v in set(m.version)]
    mat = m.pivot_table(index=KEY, columns="version", values="disagree", aggfunc="first").reindex(columns=order)
    np_ = mat.notna().sum(1); nd_ = mat.sum(1, skipna=True)
    cls = pd.Series(np.where(np_==0,"no_data",
                    np.where(nd_==0,"solved",
                    np.where(nd_==np_,"stable_wrong","tool_sensitive"))), index=mat.index)
    # 단위 속성(event_kind, hand_condition, event_text) 붙이기
    attr = (m.sort_values("version").groupby(KEY)
              .agg(event_kind=("event_kind","first"),
                   hand_condition=("hand_condition","first"),
                   event_text=("event_text","first"),
                   human_label=("h","first"))).reset_index()
    out = mat.reset_index().assign(n_present=np_.values, n_disagree=nd_.values, **{"class":cls.values})
    out = out.merge(attr, on=KEY, how="left")
    out.to_csv(os.path.join(CFG["OUT"],"stability_matrix.csv"), index=False)

    stable = out[out["class"]=="stable_wrong"].sort_values(["model","axis","video_file","event"])
    stable.to_csv(os.path.join(CFG["OUT"],"stable_wrong_units.csv"), index=False)

    # stable_wrong 에 각 버전 reason 까지 붙인 "손으로 읽을" 파일
    sw_key = stable[KEY]
    g_sw = gem.merge(sw_key, on=KEY, how="inner")
    reasons = (g_sw.pivot_table(index=KEY, columns="version", values="reason", aggfunc="first")
                   .reindex(columns=order).reset_index())
    reasons = reasons.merge(attr, on=KEY, how="left")
    reasons.to_csv(os.path.join(CFG["OUT"],"stable_wrong_with_reasons.csv"), index=False)

    summary = (out.groupby(["model","axis","class"]).size().unstack(fill_value=0)
                  .reindex(columns=["solved","tool_sensitive","stable_wrong"], fill_value=0))
    summary.to_csv(os.path.join(CFG["OUT"],"class_summary_by_axis.csv"))
    print("\n[summary]\n", summary)
    print(f"\n[손으로 읽을 집합] stable_wrong {len(stable)} units / 전체 {len(out)} "
          f"-> stable_wrong_with_reasons.csv")

    # =============================== 플롯 ===============================
    AXES = ["A","V","AVB","TC-Relation","TC-Count"]
    pal = {"solved":"#cfd8dc","tool_sensitive":"#f4a259","stable_wrong":"#c1121f"}
    models = list(CFG["MODELS"])

    fig, axs = plt.subplots(1, len(models), figsize=(6*len(models),4.6), sharey=True, squeeze=False)
    for j, model in enumerate(models):
        ax = axs[0][j]; here = [a for a in AXES if (model,a) in summary.index]
        bottoms = np.zeros(len(here))
        for c in ["solved","tool_sensitive","stable_wrong"]:
            vals = [summary.loc[(model,a),c] for a in here]
            ax.bar(here, vals, bottom=bottoms, color=pal[c], label=c); bottoms += np.array(vals)
        ax.set_title(model); ax.spines[["top","right"]].set_visible(False)
        if j==0: ax.set_ylabel("# of units"); ax.legend(frameon=False)
    fig.suptitle("Error stability by axis  (red = wrong in ALL versions = fixed blind spot)")
    plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"],"stab1_class_by_axis.png"),dpi=200); plt.close()

    ts = out[out["class"]=="tool_sensitive"]
    if len(ts):
        H = ts[order].fillna(-1).values
        lab = (ts.model+" | "+ts.video_file.str.replace("_v1_raw.mp4","",regex=False)
               +" | "+ts.event+" | "+ts.axis).values
        fig, ax = plt.subplots(figsize=(1.1*len(order)+4, max(3,0.3*len(ts))))
        cmap = matplotlib.colors.ListedColormap(["#e9ecef","#dff0d8","#c1121f"])
        ax.imshow(H, aspect="auto", cmap=cmap, vmin=-1, vmax=1)
        ax.set_xticks(range(len(order))); ax.set_xticklabels(order, rotation=90)
        ax.set_yticks(range(len(ts))); ax.set_yticklabels(lab, fontsize=6)
        ax.set_title("tool_sensitive units (red=disagree, green=agree, grey=absent)")
        plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"],"stab2_tool_sensitive_heatmap.png"),dpi=200); plt.close()

    rate = (m.groupby(["model","version"])["disagree"].mean().mul(100)
              .unstack(0).reindex(order))
    ax = rate.plot(kind="bar", figsize=(11,4.6), color=["#2c6fbb","#e07b39"])
    ax.set_ylabel("disagreement w/ human GT (%)"); ax.set_xlabel("")
    ax.set_title("Per-version disagreement rate (recomputed from raw; includes TC-Relation)")
    ax.spines[["top","right"]].set_visible(False); ax.legend(frameon=False, title="model")
    plt.tight_layout(); plt.savefig(os.path.join(CFG["OUT"],"stab3_disagreement_rate.png"),dpi=200); plt.close()

    print("\n[done] ->", CFG["OUT"])
    for f in ["stability_matrix.csv","stable_wrong_units.csv","stable_wrong_with_reasons.csv",
              "class_summary_by_axis.csv","stab1_class_by_axis.png",
              "stab2_tool_sensitive_heatmap.png","stab3_disagreement_rate.png"]:
        print("   -", f)


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
        HUMAN = {   # <-- 실제 경로 확인
            "LTX":  "/home/coder/T2AV/eval_results/human/YS_eval_annotation_ltx.xlsx",
            "MOVA": "/home/coder/T2AV/eval_results/human/YS_eval_annotation_mova.xlsx",
        },
        HUMAN_SHEET = "Annotation",
        INSPECT = False,    # 처음엔 True(진단만) -> 교집합 확인 후 False
        OUT = "/home/coder/T2AV/eval_results/new-analysis/stability",
    )
    run(CFG)
