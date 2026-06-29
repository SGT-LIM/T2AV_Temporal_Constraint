#!/usr/bin/env python3
"""
make_grouped_review_html.py

Combine batch_eval_2.py outputs from multiple folders into grouped review HTMLs.

Designed for this folder layout:

analysis/
  ltx-2.3/
    disagreements.csv
    count_disagreements.csv
  mova/
    disagreements.csv
    count_disagreements.csv
  LTX-ICL/
    disagreements.csv
    count_disagreements.csv
  mova-ICL/
    disagreements.csv
    count_disagreements.csv

Example:

  python make_grouped_review_html.py \
    --analysis-dir /home/coder/T2AV/eval_results/analysis \
    --video-root /home/coder/T2AV/generation \
    --outdir review_pages

This creates:
  review_pages/non_icl_review.html
  review_pages/non_icl_review_items.csv
  review_pages/icl_review.html
  review_pages/icl_review_items.csv
  review_pages/all_review.html
  review_pages/all_review_items.csv
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_GROUPS = {
    "non_icl": ["ltx-2.3", "mova"],
    "icl": ["LTX-ICL", "mova-ICL"],
}

RUN_META = {
    "ltx-2.3": {"model": "LTX-2.3", "icl": "non-ICL"},
    "mova": {"model": "MOVA", "icl": "non-ICL"},
    "LTX-ICL": {"model": "LTX-2.3", "icl": "ICL"},
    "mova-ICL": {"model": "MOVA", "icl": "ICL"},
}


def norm_str(x: Any) -> str:
    if pd.isna(x):
        return ""
    return str(x).strip()


def yesno_direction(human_label: str, gem_label: str) -> str:
    h, g = norm_str(human_label).lower(), norm_str(gem_label).lower()
    if h == "yes" and g == "no":
        return "over-reject"
    if h == "no" and g == "yes":
        return "over-accept"
    return "other"


def count_direction(human_count: Any, gem_count: Any) -> str:
    h = pd.to_numeric(human_count, errors="coerce")
    g = pd.to_numeric(gem_count, errors="coerce")
    if pd.isna(h) or pd.isna(g):
        return "other"
    if g > h:
        return "over-count"
    if g < h:
        return "under-count"
    return "exact"


def failure_mode_yesno(row: pd.Series) -> str:
    axis = norm_str(row.get("axis"))
    direction = norm_str(row.get("direction"))
    event_kind = norm_str(row.get("event_kind"))

    if direction == "over-accept":
        return {
            "A": "ACCEPT_AUDIO_DISPUTED",
            "V": "ACCEPT_VISUAL_DISPUTED",
            "AVB": "ACCEPT_BINDING_DISPUTED",
            "TC-Relation": "ACCEPT_ORDER_DISPUTED",
        }.get(axis, "ACCEPT_DISPUTED")

    if direction == "over-reject":
        blob = (norm_str(row.get("reason")) + " " + norm_str(row.get("evidence"))).lower()
        if axis == "AVB" and ("precondition" in blob or "not evaluable" in blob or "missing" in blob):
            return "CASCADE_AVB_PRECOND"
        if axis == "TC-Relation" and ("missing" in blob or "never occurs" in blob or "does not occur" in blob):
            return "CASCADE_RELATION_MISSING"
        if axis == "A" and event_kind == "speech":
            return "MISS_SPEECH_AUDIO"
        if axis == "A":
            return "MISS_ACTION_SOUND"
        if axis == "V" and event_kind == "speech":
            return "MISS_LIP_MOTION"
        if axis == "V":
            return "MISS_VISIBLE_ACTION"
        return "MISS_OR_TOO_STRICT"

    return "OTHER"


def interpret_yesno(row: pd.Series) -> tuple[str, str, int, str]:
    axis = norm_str(row.get("axis"))
    direction = norm_str(row.get("direction"))
    fm = norm_str(row.get("failure_mode"))

    if direction == "over-accept":
        if axis == "TC-Relation":
            return "watch", "root", 3, "사람은 순서/관계가 틀렸다고 봤는데 Gemini는 맞다고 판단함 → 실제 이벤트 순서와 누락 여부를 직접 확인."
        if axis == "AVB":
            return "watch", "root", 3, "사람은 binding/sync가 틀렸다고 봤는데 Gemini는 맞다고 판단함 → 오디오-비디오 동기화 또는 구성요소 오류를 직접 확인."
        if axis == "V":
            return "watch", "root", 3, "사람은 시각 이벤트가 틀렸거나 없다고 봤는데 Gemini는 맞다고 판단함 → 손 방향/동작/포즈를 직접 확인."
        if axis == "A":
            return "watch", "root", 3, "사람은 오디오 이벤트가 틀렸거나 없다고 봤는데 Gemini는 맞다고 판단함 → 실제 소리/발화를 직접 확인."
        return "watch", "root", 3, "Gemini가 사람 GT의 no를 yes로 받아들인 케이스 → 직접 확인 필요."

    if fm.startswith("CASCADE"):
        return "trust", "cascade", 0, "A/V 구성요소 미검출에서 파생된 연쇄 오류로 보임 → 독립 오류라기보다 root miss의 결과로 기록."

    if direction == "over-reject":
        if axis == "A":
            return "trust", "root", 1, "사람은 오디오가 있다고 봤는데 Gemini가 못 들은 케이스 → Gemini의 miss로 자동 해석 가능."
        if axis == "V":
            return "trust", "root", 1, "사람은 시각 동작/입모양이 있다고 봤는데 Gemini가 못 본 케이스 → Gemini의 visual miss로 자동 해석 가능."
        if axis == "AVB":
            return "trust", "cascade", 0, "Gemini가 A/V 중 하나를 놓쳐 binding도 실패 처리한 것으로 보임 → 연쇄 오류로 기록."
        if axis == "TC-Relation":
            return "trust", "cascade", 0, "Gemini가 필요한 이벤트를 놓쳐 순서도 실패 처리한 것으로 보임 → 연쇄 오류로 기록."
        return "trust", "root", 1, "사람 yes, Gemini no → 대체로 Gemini miss/too-strict로 자동 해석 가능."

    return "spot", "root", 2, "분류가 애매한 불일치 → 빠르게 확인."


def interpret_count(row: pd.Series) -> tuple[str, str, int, str, str]:
    h = int(pd.to_numeric(row.get("human_count"), errors="coerce"))
    g = int(pd.to_numeric(row.get("gem_count"), errors="coerce"))
    diff = g - h
    blob = (norm_str(row.get("reason")) + " " + norm_str(row.get("evidence"))).lower()

    if diff > 0:
        return "watch", "root", 2, "OVERCOUNT", f"Gemini가 발생 횟수를 더 많게 셈 (사람 {h} → Gemini {g}) → 환각/잘못된 이벤트 인정 가능성이 있어 확인 필요."
    if diff < 0:
        if g == 0 and ("does not occur" in blob or "zero" in blob or "no " in blob or "missing" in blob):
            return "trust", "cascade", 0, "CASCADE_UNDERCOUNT_MISS", f"Gemini가 이벤트를 놓쳐 0/적게 센 케이스 (사람 {h} → Gemini {g}) → 미검출의 카운트 축 발현으로 기록."
        return "spot", "root", 2, "UNDERCOUNT", f"Gemini가 발생 횟수를 더 적게 셈 (사람 {h} → Gemini {g}) → 횟수만 빠르게 확인."
    return "trust", "none", 0, "EXACT", "count exact match"


def event_order(event_id: Any) -> int:
    import re
    m = re.search(r"event_(\d+)", norm_str(event_id))
    return int(m.group(1)) if m else 99


def load_one_run(run_dir: Path, run_name: str) -> pd.DataFrame:
    frames = []
    meta = RUN_META.get(run_name, {"model": run_name, "icl": "unknown"})

    dis_path = run_dir / "disagreements.csv"
    if dis_path.exists():
        d = pd.read_csv(dis_path)
        d["kind"] = "yesno"
        if "direction" not in d.columns:
            d["direction"] = d.apply(lambda r: yesno_direction(r.get("human_label"), r.get("gem_label")), axis=1)
        if "failure_mode" not in d.columns:
            d["failure_mode"] = d.apply(failure_mode_yesno, axis=1)
        interp = d.apply(interpret_yesno, axis=1, result_type="expand")
        d[["tier", "layer", "priority", "interpretation"]] = interp
        frames.append(d)

    cdis_path = run_dir / "count_disagreements.csv"
    if cdis_path.exists():
        c = pd.read_csv(cdis_path)
        c["kind"] = "count"
        c["axis"] = "TC-Count"
        c["human_label"] = c["human_count"].astype(str)
        c["gem_label"] = c["gem_count"].astype(str)
        if "direction" not in c.columns:
            c["direction"] = c.apply(lambda r: count_direction(r.get("human_count"), r.get("gem_count")), axis=1)
        interp = c.apply(interpret_count, axis=1, result_type="expand")
        c[["tier", "layer", "priority", "failure_mode", "interpretation"]] = interp
        frames.append(c)

    if not frames:
        print(f"[warn] no disagreement files found in {run_dir}")
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out["run"] = run_name
    out["model"] = meta["model"]
    out["icl"] = meta["icl"]
    return out


def finalize(df, ltx_root, mova_root, video_suffix, out_html, relative_video_paths):
    needed = [
        "run", "model", "icl", "condition", "item_id", "video_file", "event_id", "event_kind", "event_label",
        "question", "axis", "kind", "direction", "human_label", "gem_label",
        "human_count", "gem_count", "diff", "required_count",
        "reason", "evidence", "failure_mode", "interpretation", "tier", "layer", "priority",
    ]
    for c in needed:
        if c not in df.columns:
            df[c] = ""

    missing_video = df["video_file"].fillna("").astype(str).str.strip() == ""
    df.loc[missing_video, "video_file"] = df.loc[missing_video, "item_id"].astype(str) + video_suffix

    # if video_root:
    #     root = Path(video_root).expanduser()
    #     df["video_src"] = df["video_file"].map(lambda v: str((root / str(v)).resolve()))
    #     if relative_video_paths:
    #         out_dir = out_html.expanduser().resolve().parent
    #         df["video_src"] = df["video_src"].map(lambda p: os.path.relpath(p, out_dir))
    # else:
    #     df["video_src"] = ""
    def resolve_video_path(row):
        model = str(row["model"]).upper()
        fname = str(row["video_file"])

        if "LTX" in model:
            root = ltx_root
        else:
            root = mova_root

        if not root:
            return ""

        return str((Path(root).expanduser() / fname).resolve())


    df["video_src"] = df.apply(resolve_video_path, axis=1)

    if relative_video_paths:
        out_dir = out_html.expanduser().resolve().parent
        df["video_src"] = df["video_src"].map(
            lambda p: os.path.relpath(p, out_dir) if p else ""
        )

    df["event_order"] = df["event_id"].map(event_order)
    df["rid"] = [f"r{i+1}" for i in range(len(df))]

    tier_order = {"watch": 0, "spot": 1, "trust": 2}
    df["_tier_order"] = df["tier"].map(tier_order).fillna(9)
    df = df.sort_values(["_tier_order", "icl", "model", "video_file", "event_order", "axis"])
    return df.drop(columns=["_tier_order"]).reset_index(drop=True)


CSS = r"""
:root{--bg:#f4f5f7;--panel:#fff;--ink:#171923;--muted:#6b7280;--line:#e5e7eb;--watch:#dc2626;--spot:#d97706;--trust:#16a34a;--reject:#2563eb;--accept:#d97706;--over:#e11d48;--under:#0d9488;--mono:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;--sans:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.5}header{position:sticky;top:0;z-index:20;background:rgba(244,245,247,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}.wrap{max-width:1220px;margin:0 auto;padding:14px 20px}h1{font-size:18px;margin:0}.sub{color:var(--muted);font-size:12px}.filters{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;align-items:center}.chip,.btn{cursor:pointer;border:1px solid var(--line);background:white;border-radius:999px;padding:4px 10px;font-size:12px}.chip{font-family:var(--mono)}.chip.on{background:var(--ink);color:white;border-color:var(--ink)}.search{border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13px;width:230px}.toggle{color:var(--muted);font-size:12px}main{max-width:1220px;margin:0 auto;padding:20px 20px 80px}.summary{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}.box{background:white;border:1px solid var(--line);border-radius:12px;padding:12px 14px}.box .n{font-family:var(--mono);font-size:25px;font-weight:750}.box .lab{font-size:12px;color:var(--muted)}.box.watch .n{color:var(--watch)}.box.spot .n{color:var(--spot)}.box.trust .n{color:var(--trust)}.insight{background:white;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:16px}.video{background:white;border:1px solid var(--line);border-radius:12px;margin-bottom:16px;overflow:hidden}.vhead{display:flex;align-items:center;gap:10px;background:#fbfbfc;padding:12px 14px;border-bottom:1px solid var(--line);cursor:pointer}.vname{font-family:var(--mono);font-weight:700}.badge{font-family:var(--mono);font-size:11px;border:1px solid var(--line);border-radius:6px;padding:2px 7px;background:#fff}.vmeta{color:var(--muted);font-family:var(--mono);font-size:12px}.vbody{padding:12px 14px}.video.collapsed .vbody{display:none}video{width:100%;max-height:420px;background:#111;border-radius:10px;margin-bottom:12px}.card{display:grid;grid-template-columns:1fr 230px;border-top:1px solid var(--line)}.card:first-of-type{border-top:none}.main{padding:12px 0}.side{border-left:1px solid var(--line);padding:12px;background:#fcfcfd}.row{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-bottom:7px}.axis,.tier,.dir,.fm,.run{font-family:var(--mono);font-size:11px;border-radius:6px;padding:2px 7px}.axis{background:#111827;color:white}.run{background:#eef2ff;color:#3730a3}.tier{border:1px solid}.tier.watch{color:var(--watch);background:#fef2f2;border-color:#fecaca}.tier.spot{color:var(--spot);background:#fffbeb;border-color:#fde68a}.tier.trust{color:var(--trust);background:#f0fdf4;border-color:#bbf7d0}.dir{background:#f3f4f6}.fm{border:1px solid var(--line);color:var(--muted)}.verdict{font-family:var(--mono);font-size:12px}.human{color:#374151}.gem{font-weight:700}.over-accept .gem,.over-count .gem{color:var(--accept)}.over-reject .gem{color:var(--reject)}.under-count .gem{color:var(--under)}.event{font-weight:650}.q{color:var(--muted);font-size:12px}.interp{background:#f1f5f9;border-radius:8px;padding:8px 10px;margin:8px 0;font-size:13px}.lab{font-family:var(--mono);font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-top:8px}.txt{font-size:13px}.ev{font-family:var(--mono);background:#f8fafc;border-left:3px solid var(--line);padding:7px 9px;white-space:pre-wrap;border-radius:0 6px 6px 0}select,textarea{width:100%;border:1px solid var(--line);border-radius:8px;padding:7px;font-size:12px}textarea{min-height:68px;resize:vertical;margin-top:8px}.saved{font-family:var(--mono);font-size:11px;color:var(--trust);opacity:0}.saved.show{opacity:1}.empty{text-align:center;color:var(--muted);padding:50px}@media(max-width:850px){.summary{grid-template-columns:1fr 1fr}.card{grid-template-columns:1fr}.side{border-left:0;border-top:1px solid var(--line)}}
"""

JS = r"""
const DATA = __DATA__;
const state = {
  tiers: new Set(["watch","spot","trust"]),
  axes: new Set([...new Set(DATA.map(d => d.axis))]),
  models: new Set([...new Set(DATA.map(d => d.model))]),
  runs: new Set([...new Set(DATA.map(d => d.run))]),
  q: "", openOnly: false
};
const LS_KEY = "gemini_grouped_review_state_v1";
function esc(s){return String(s ?? "").replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function savedState(){try{return JSON.parse(localStorage.getItem(LS_KEY)||"{}")}catch(e){return {}}}
function setSaved(id,patch){const s=savedState();s[id]={...(s[id]||{}),...patch};localStorage.setItem(LS_KEY,JSON.stringify(s));}
function reviewed(d){const s=savedState()[d.rid];return !!(s&&(s.status||s.note));}
function makeChips(id,values,setName){const el=document.getElementById(id);el.innerHTML="";values.forEach(v=>{const c=document.createElement("span");c.className="chip on";c.textContent=v;c.onclick=()=>{const S=state[setName];S.has(v)?S.delete(v):S.add(v);c.classList.toggle("on",S.has(v));render();};el.appendChild(c);});}
function passFilter(d){if(!state.tiers.has(d.tier))return false;if(!state.axes.has(d.axis))return false;if(!state.models.has(d.model))return false;if(!state.runs.has(d.run))return false;if(state.openOnly&&reviewed(d))return false;const blob=[d.run,d.model,d.icl,d.video_file,d.item_id,d.axis,d.event_label,d.reason,d.evidence,d.failure_mode,d.interpretation].join(" ").toLowerCase();return !state.q||blob.includes(state.q.toLowerCase());}
function card(d){const s=savedState()[d.rid]||{},status=s.status||"",note=s.note||"";return `<div class="card ${reviewed(d)?'reviewed':''}" data-rid="${esc(d.rid)}"><div class="main"><div class="row ${esc(d.direction)}"><span class="run">${esc(d.model)} · ${esc(d.icl)}</span><span class="axis">${esc(d.axis)}</span><span class="tier ${esc(d.tier)}">${esc(d.tier)}</span><span class="dir">${esc(d.direction)}</span><span class="fm">${esc(d.failure_mode)}</span><span class="verdict"><span class="human">human=${esc(d.human_label)}</span> → <span class="gem">gemini=${esc(d.gem_label)}</span></span></div><div class="event">${esc(d.event_label||d.event_id||"(whole video)")}</div>${d.question?`<div class="q">${esc(d.question)}</div>`:""}<div class="interp">${esc(d.interpretation)}</div><div class="lab">Gemini reason</div><div class="txt">${esc(d.reason)}</div><div class="lab">Gemini evidence</div><div class="ev">${esc(d.evidence)}</div></div><div class="side"><div class="lab">Human review</div><select data-act="status"><option value="" ${status===""?"selected":""}>unreviewed</option><option value="confirm_gt" ${status==="confirm_gt"?"selected":""}>confirm human GT</option><option value="gemini_might_be_right" ${status==="gemini_might_be_right"?"selected":""}>Gemini might be right</option><option value="ambiguous" ${status==="ambiguous"?"selected":""}>ambiguous</option><option value="ignore_cascade" ${status==="ignore_cascade"?"selected":""}>ignore/cascade</option></select><textarea data-act="note" placeholder="note...">${esc(note)}</textarea><div class="saved">saved</div></div></div>`}
function render(){const filtered=DATA.filter(passFilter);const byKey={};filtered.forEach(d=>{const key=`${d.video_file}|||${d.model}|||${d.icl}`;(byKey[key] ||= []).push(d);});document.getElementById("shown").textContent=filtered.length;document.getElementById("empty").style.display=filtered.length?"none":"block";const list=document.getElementById("list");list.innerHTML=Object.entries(byKey).map(([key,arr])=>{const [v,model,icl]=key.split("|||");const src=arr.find(x=>x.video_src)?.video_src||"";return `<section class="video"><div class="vhead" onclick="this.parentElement.classList.toggle('collapsed')"><span class="vname">${esc(v)}</span><span class="badge">${esc(model)}</span><span class="badge">${esc(icl)}</span><span class="vmeta">${arr.length} disagreements</span></div><div class="vbody">${src?`<video controls preload="metadata" src="${esc(src)}"></video>`:""}${arr.map(card).join("")}</div></section>`}).join("");list.querySelectorAll("[data-act=status]").forEach(sel=>{sel.onchange=()=>{const rid=sel.closest(".card").dataset.rid;setSaved(rid,{status:sel.value});flash(sel);render();}});list.querySelectorAll("[data-act=note]").forEach(ta=>{ta.oninput=()=>{const rid=ta.closest(".card").dataset.rid;setSaved(rid,{note:ta.value});flash(ta);};});}
function flash(el){const s=el.closest(".side").querySelector(".saved");s.classList.add("show");setTimeout(()=>s.classList.remove("show"),700)}
function exportCSV(){const s=savedState();const rows=DATA.map(d=>({...d,review_status:s[d.rid]?.status||"",review_note:s[d.rid]?.note||""}));const cols=["rid","run","model","icl","video_file","item_id","event_id","axis","kind","direction","tier","layer","failure_mode","human_label","gem_label","reason","evidence","interpretation","review_status","review_note"];const csv=[cols.join(",")].concat(rows.map(r=>cols.map(c=>`"${String(r[c]??"").replace(/"/g,'""')}"`).join(","))).join("\n");const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="review_export.csv";a.click();URL.revokeObjectURL(a.href);}
document.addEventListener("DOMContentLoaded",()=>{document.getElementById("total").textContent=DATA.length;document.getElementById("shown").textContent=DATA.length;document.getElementById("nWatch").textContent=DATA.filter(d=>d.tier==="watch").length;document.getElementById("nSpot").textContent=DATA.filter(d=>d.tier==="spot").length;document.getElementById("nTrust").textContent=DATA.filter(d=>d.tier==="trust").length;document.getElementById("nLTX").textContent=DATA.filter(d=>d.model.includes("LTX")).length;document.getElementById("nMOVA").textContent=DATA.filter(d=>d.model.includes("MOVA")).length;makeChips("tierChips",["watch","spot","trust"],"tiers");makeChips("axisChips",[...new Set(DATA.map(d=>d.axis))].sort(),"axes");makeChips("modelChips",[...new Set(DATA.map(d=>d.model))].sort(),"models");makeChips("runChips",[...new Set(DATA.map(d=>d.run))].sort(),"runs");document.getElementById("search").oninput=e=>{state.q=e.target.value;render();};document.getElementById("openOnly").onchange=e=>{state.openOnly=e.target.checked;render();};document.getElementById("export").onclick=exportCSV;render();});
"""


def render_html(df: pd.DataFrame, title: str) -> str:
    data = df.replace({np.nan: ""}).to_dict(orient="records")
    data_json = json.dumps(data, ensure_ascii=False)
    js = JS.replace("__DATA__", data_json)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
<h1>{title}</h1>
<div class="sub">총 <b id="total"></b>건 · 현재 표시 <b id="shown"></b>건 · 리뷰 상태는 브라우저 localStorage에 저장됨</div>
<div class="filters">
<span>Tier:</span><span id="tierChips"></span>
<span>Axis:</span><span id="axisChips"></span>
<span>Model:</span><span id="modelChips"></span>
<span>Run:</span><span id="runChips"></span>
<input class="search" id="search" placeholder="video / reason / evidence 검색">
<label class="toggle"><input type="checkbox" id="openOnly"> 미검토만</label>
<button class="btn" id="export">리뷰 CSV 내보내기</button>
</div>
</div></header>
<main>
<div class="summary">
<div class="box watch"><div class="n" id="nWatch"></div><div class="lab">watch</div></div>
<div class="box spot"><div class="n" id="nSpot"></div><div class="lab">spot</div></div>
<div class="box trust"><div class="n" id="nTrust"></div><div class="lab">trust</div></div>
<div class="box"><div class="n" id="nLTX"></div><div class="lab">LTX items</div></div>
<div class="box"><div class="n" id="nMOVA"></div><div class="lab">MOVA items</div></div>
</div>
<div class="insight"><b>구성:</b> non-ICL = ltx-2.3 + mova, ICL = LTX-ICL + mova-ICL. 같은 페이지 안에서 Model/Run 필터로 나눠볼 수 있습니다.</div>
<div id="list"></div>
<div id="empty" class="empty" style="display:none">필터에 맞는 항목이 없습니다.</div>
</main>
<script>{js}</script>
</body></html>"""


def write_page(df, out_html, title, ltx_root, mova_root, video_suffix, relative_video_paths):
    out_html.parent.mkdir(parents=True, exist_ok=True)
    # df = finalize(df.copy(), video_root, video_suffix, out_html, relative_video_paths)
    df = finalize(
        df.copy(),
        ltx_root,
        mova_root,
        video_suffix,
        out_html,
        relative_video_paths
    )
    df.to_csv(out_html.with_name(out_html.stem + "_items.csv"), index=False)
    out_html.write_text(render_html(df, title), encoding="utf-8")
    print(f"[ok] {out_html} ({len(df)} items)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis-dir", default=".", help="Directory containing ltx-2.3, mova, LTX-ICL, mova-ICL folders")
    ap.add_argument("--outdir", default="review_pages")
    # ap.add_argument("--video-root", default="")
    ap.add_argument("--ltx-root", default="", help="Root dir for LTX videos")
    ap.add_argument("--mova-root", default="", help="Root dir for MOVA videos")
    ap.add_argument("--video-suffix", default="_v1_raw.mp4")
    ap.add_argument("--relative-video-paths", action="store_true")
    ap.add_argument("--only", choices=["non_icl", "icl", "all"], default="all")
    args = ap.parse_args()

    analysis_dir = Path(args.analysis_dir)
    outdir = Path(args.outdir)

    loaded = {}
    for run_name in sorted({r for runs in DEFAULT_GROUPS.values() for r in runs}):
        run_dir = analysis_dir / run_name
        df = load_one_run(run_dir, run_name)
        if not df.empty:
            loaded[run_name] = df

    if not loaded:
        raise SystemExit(f"No usable disagreement CSVs found under {analysis_dir}")

    if args.only in ("non_icl", "all"):
        runs = [r for r in DEFAULT_GROUPS["non_icl"] if r in loaded]
        if runs:
            df = pd.concat([loaded[r] for r in runs], ignore_index=True)
            write_page(df, outdir / "non_icl_review.html", "Gemini disagreement review · non-ICL", args.ltx_root, args.mova_root, args.video_suffix, args.relative_video_paths)

    if args.only in ("icl", "all"):
        runs = [r for r in DEFAULT_GROUPS["icl"] if r in loaded]
        if runs:
            df = pd.concat([loaded[r] for r in runs], ignore_index=True)
            write_page(df, outdir / "icl_review.html", "Gemini disagreement review · ICL", args.ltx_root, args.mova_root, args.video_suffix, args.relative_video_paths)

    if args.only == "all":
        df = pd.concat(list(loaded.values()), ignore_index=True)
        write_page(df, outdir / "all_review.html", "Gemini disagreement review · all runs", args.ltx_root, args.mova_root, args.video_suffix, args.relative_video_paths)


if __name__ == "__main__":
    main()
