#!/usr/bin/env python3
"""HD-EPIC main table, stage 2 (rows 4, 5 and framing), 11/01. Text-only KEEP/REVISE calls through obs_judge_1028 (same OBS_RULES,
stage-1 block and call settings as B30 / HO30 / G4: gemini-3.6-flash, thinking high, temperature 0, seed 42).
Stage 1 = the 11/01 HD-EPIC row 1 anchor (results/hdepic_main_row1_anchor_g36_1101).

GT rows (axes A, V, AVB; TCR / TCC get no tool, decided 10/30):
  P01/P02  manifests_v3/test.jsonl rows of source hdepic (A, V, AVB, v2 prompts) and hdfoot (A, old prompts)
  P03-P09  the v3 rules (make_gt_v3) on the holdout items: A = _A (claim event no) + originals; V = hand / noun swap (broken event no;
           noun swap falls back to broken_event_idx because the holdout prompts carry no v_fail_object_v2) + originals;
           AVB = shift early / late (every binding event no) + the originals of the shifted windows.
Sources (obs_judge ANCHOR / PROMPTS): hm_hdepic, hm_hdfoot, hm_p3p9. Sets: HG4 (row 4), HG5 (row 5 new calls), HFRb / HFRc (framing).
Observation texts (all "Observation (tool output):"):
  A    one FLAM line per sounding event (first pipeline query, whole clip, hop 5, threshold .98) from the 11/01 hdA records
       (gen_evidence_1030 audio --set hdA); HD-EPIC has no speech events, so no Whisper line.
  V    the AVoCaDO caption (fps 2, plain): P01/P02 avocado_fps2_plain_v3_hdepic_items.json, P03-P09 the A100 clip captions (11/01).
  AVB  the Synchformer action-window lines (synchformer_action_1030, pre-registered mode), as in HO30.
Row 5 admission: A: a FLAM line only for an event whose first-query max score < T_flam (.2705); V: the text-only caption check says
  the caption contradicts a GT event (lemma heuristic scored as a variant); AVB: the pre-registered rule (|offset| >= 1.8 s and
  p >= .25 on the strongest binding-event reading), code-rule and gated-judge variants. A row-5 call with the row-4 text reuses
  the HG4 call (user decision 11/01). Framing b / c: AVB rows where the rule fires (sentence with 1.8 s / .25 from
  framing_config_1030.json) and V rows whose caption does not mention a GT event (descriptive sentence, no number).
  python gepa_stage2/hd_stage2_1101.py rows4 [--axes V,AVB]   # A once the hdA records exist
  python gepa_stage2/hd_stage2_1101.py vcheck --workers 6
  python gepa_stage2/hd_stage2_1101.py rows5 | framing | groups | score
  python gepa_stage2/obs_judge_1028.py run --set HG4|HG5|HFRb|HFRc --cond gen_tool_text --workers 12
"""
import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
from t2av_eval import paths as _P
from t2av_eval.gate import preregistered as PR
import argparse, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
pass  # (legacy sys.path insert removed); pass  # (legacy sys.path insert removed)
import obs_judge_1028 as O
import gen_stage2_1030 as G

E = Path((str(_P.DATA) + "/real_av/eval"))
V = E / "hdepic_main_1101"
HO = Path((str(_P.DATA) + "/real_av_holdout_p3p9_1028"))
EVD = Path((str(_P.DATA) + "/tools/gen_evidence_1030"))
SYA = Path((str(_P.DATA) + "/tools/synchformer_action_1030"))
CAPD = E / "hdepic_main_1101_captions"
SETDIR = {"hm_hdepic": "hdepic_p12", "hm_hdfoot": "hdfoot_p12", "hm_p3p9": "p3p9", "hm_ma": "ma", "hm_p12new": "p12all_new", "hm_ma39": "ma39",
          "hm_avbadd12": "avbadd_p12", "hm_avbadd39": "avbadd_p3p9"}
AVBADD = Path((str(_P.DATA) + "/real_av/eval/hdepic_avbadd_1102"))
# 11/01 option (ii): P01/P02 = all 194 windows under the P03-P09 rules (hm_hdepic test items + hm_p12new). hdfoot (old prompts,
# absent footstep) is not part of those rules and is reported as its own group from now on (it was inside P01P02 A before).
GROUP = {"hm_hdepic": "P01P02", "hm_hdfoot": "P01P02-hdfoot", "hm_p3p9": "P03P09", "hm_ma": "P01P02-ma", "hm_p12new": "P01P02", "hm_ma39": "P03P09-ma",
         "hm_avbadd12": "P01P02-avbadd", "hm_avbadd39": "P03P09-avbadd"}
PILOT_ITEMS = Path((str(_P.DATA) + "/real_av_pilot/items_hdepic_medium_with_clips_v2.json"))
MA = Path((str(_P.DATA) + "/real_av/hdepic/hdepic_mute_anchor_1028"))
MA_DIR = {"hm_ma": MA, "hm_ma39": Path((str(_P.DATA) + "/real_av_holdout_p3p9_1028/mute_anchor_1101"))}
MA_SETS_BY = {"hm_ma": {"row4": "HMA4", "row5": "HMA5"}, "hm_ma39": {"row4": "HMB4", "row5": "HMB5"}}
MA_SETS = MA_SETS_BY["hm_ma"]
COND = G.COND
SETS = {"row4": "HG4", "row5": "HG5", "frb": "HFRb", "frc": "HFRc"}
RULE = None        # loaded on first use from config/recipe_v4.yaml (t2av_eval.gate.preregistered); tests may set it


def rule():
    global RULE
    if RULE is None:
        RULE = PR.avb_rule()
    return RULE


def gt_rows():
    from t2av_eval.judge.media import core as NE
    from make_gt_v3 import ids_for, struct_for_prompt_event
    out = []
    man = [json.loads(l) for l in open(_P.INPUTS / "evaluation/ablation/gepa_stage2/manifests_v3/test.jsonl")]
    for m in man:
        if (m["source"] == "hdepic" and m["axis"] in ("A", "V", "AVB")) or (m["source"] == "hdfoot" and m["axis"] == "A"):
            src = "hm_" + m["source"]
            out.append(dict(source=src, item_id=m["item_id"], axis=m["axis"], gt=m["gt"], variant=m["variant"]))
    out += v3_rows(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json", HO / "prompts_hdepic_p3p9.json", HO / "gt_hdepic_p3p9.csv", "hm_p3p9")
    for src, g in (("hm_avbadd12", "p12"), ("hm_avbadd39", "p3p9")):          # 11/02 AVB additions (AVB rows only)
        if (AVBADD / g / "prompts_avbadd.json").exists():
            out += [r for r in v3_rows(AVBADD / g / "items_avbadd_with_clips.json", AVBADD / g / "prompts_avbadd.json", AVBADD / g / "gt_avbadd.csv", src)
                    if r["axis"] == "AVB"]
    newdir = V / "p12all_new"
    if newdir.exists():
        out += v3_rows(PILOT_ITEMS, E / "hdepic_medium_prompts_v2.json", E / "hdepic_medium_gt.csv", "hm_p12new", keep=set(__import__("os").listdir(newdir)))
    for r in out:
        r["uid"] = f"{r['source']}|{r['item_id']}|{r['axis']}"
    return out


def v3_rows(items_json, prompts_json, gt_csv, source, keep=None):
    """v3 GT rules on one item set (P03-P09 holdout, or the P01/P02 items outside the v3 test). Noun swap: the prompt's
    v_fail_object_v2 event when present (as make_gt_v3), else broken_event_idx."""
    from t2av_eval.judge.media import core as NE
    from make_gt_v3 import ids_for, struct_for_prompt_event
    out = []
    it = {x["item_id"]: x for x in json.load(open(items_json))}
    P = {x["item_id"]: x for x in json.load(open(prompts_json))}
    it = {k: v for k, v in it.items() if k in P and (keep is None or k in keep)}
    metas = NE.build_item_meta_map([P[k] for k in it], modality_filter=None, item_overrides=None, relative_only=False)
    gtc = pd.read_csv(gt_csv).drop_duplicates("item_id", keep="last").set_index("item_id")
    allit = json.load(open(items_json))
    wkey = lambda x: (x["video_id"], tuple(x["clip"]))
    shifted = {wkey(x) for x in allit if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
    for iid, x in sorted(it.items()):
        var, meta = x["variant"], metas[iid]
        structs = NE.build_scoring_events(meta)
        all_ids = [s_["event_id"] for s_ in structs]
        g = gtc.loc[iid]
        broken = None
        if pd.notna(g.get("broken_event_idx")) and str(g.get("broken_event_idx")) != "":
            k = int(float(g["broken_event_idx"]))
            broken = all_ids[k] if 0 <= k < len(all_ids) else None
        rows = []
        a_ids = ids_for("A", structs)
        if var == "fail_absent_sound":
            claim = struct_for_prompt_event(structs, meta["events"], "e_sound_claim")
            if claim in a_ids:
                rows.append(("A", "absent_sound", {e: ("no" if e == claim else "yes") for e in a_ids}))
        elif var == "original":
            if a_ids:
                rows.append(("A", "original", {e: "yes" for e in a_ids}))
            rows.append(("V", "original", {e: "yes" for e in all_ids}))
            if wkey(x) in shifted:
                rows.append(("AVB", "original", {e: "yes" for e in ids_for("AVB", structs)}))
        elif var == "fail_noun_swap":
            v2 = P[iid].get("v_fail_object_v2")
            b = struct_for_prompt_event(structs, meta["events"], v2["event"]) if v2 else broken
            if b:
                rows.append(("V", "noun_swap", {e: ("no" if e == b else "yes") for e in all_ids}))
        elif var == "fail_hand_swap" and broken:
            rows.append(("V", "hand_swap", {e: ("no" if e == broken else "yes") for e in all_ids}))
        elif var in ("fail_audio_shift_early", "fail_audio_shift_late"):
            rows.append(("AVB", var.replace("fail_", ""), {e: "no" for e in ids_for("AVB", structs)}))
        for ax, v, gt in rows:
            if gt:
                out.append(dict(source=source, item_id=iid, axis=ax, gt=gt, variant=v))
    return out


def a_parts(src, iid):
    f = {"hm_ma": EVD / "ma" / f"ma__{iid}.json", "hm_ma39": EVD / "ma39" / f"ma39__{iid}.json",
         "hm_p12new": EVD / "p12A" / f"p12all__{iid}.json"}.get(src, EVD / "hdA" / f"{SETDIR[src]}__{iid}.json")
    if not f.exists():
        return None
    rec = json.load(open(f))
    T = json.load(open(EVD / "flam_threshold.json"))["T_flam"]
    out = {}
    for e in rec.get("events", []):
        if not e["queries"]:
            continue
        q = e["queries"][0]
        fl = rec["flam"].get(q)
        if fl is None:
            continue
        if fl["detections"]:
            d = max(fl["detections"], key=lambda d: d.get("peak_score") or 0)
            line = (f"FLAM (open-vocabulary audio-text detector, whole clip audio): queried '{q}' -> detected, score peak at "
                    f"{d['peak_time']:.2f} s (detection threshold 0.98; scores are uncalibrated)")
        else:
            line = (f"FLAM (open-vocabulary audio-text detector, whole clip audio): queried '{q}' -> not detected (max frame score "
                    f"{fl['max_score']:.3f}; detection threshold 0.98; scores are uncalibrated)")
        out[e["event_id"]] = (line, fl["max_score"] < T)
    return out


def a_text(src, iid, gated=False):
    p = a_parts(src, iid)
    if p is None:
        return None
    lines = [l for l, below in p.values() if not gated or below]
    return "Observation (tool output):\n" + "\n".join(lines) if lines else ""


_CAP = {}


def caption(src, iid):
    if src not in _CAP:
        f = CAPD / f"{SETDIR[src]}.json"
        _CAP[src] = json.load(open(f)) if f.exists() else {}
    c = _CAP[src].get(f"{iid}/{iid}_v1_raw.mp4")
    return c["caption"] if c else None


def v_text(src, iid):
    c = caption(src, iid)
    return None if c is None else ("Observation (tool output):\nDense caption written by a separate captioning model (AVoCaDO) that "
                                   "watched and listened to the same clip without seeing the prompt:\n" + c.strip())


_PE = None


def sync_pe():
    global _PE
    if _PE is None:
        _PE = pd.concat(pd.read_csv(f) for d in ("b110", "holdout", "p12all", "avbadd") for f in sorted((SYA / d).glob("per_event_shard*.csv")))
    return _PE


def avb_text(src, iid):
    g = sync_pe()
    g = g[g.item_id == iid]
    if not len(g):
        return None
    multi = len(g) > 1
    lines = []
    for r in g.itertuples():
        pre = f"'{r.label}': " if multi else ""
        lines.append(f"{pre}Synchformer, window around the action: no reading" if r.status != "ok" or pd.isna(r.offset) else
                     f"{pre}Synchformer, window around the action: most likely offset {float(r.offset):+.1f} s (positive = audio later than "
                     f"video), probability {float(r.prob):.2f}; probability of zero offset {float(r.p_offset0):.2f}")
    return "Observation (tool output):\n" + "\n".join(lines)


def fires(iid):
    g = sync_pe()
    g = g[(g.item_id == iid) & (g.status == "ok")].assign(a=lambda t: t.offset.abs())
    if not len(g):
        return False
    w = g.sort_values(["a", "prob"], ascending=False).iloc[0]
    return bool(w.a >= rule()["T"] - 1e-9 and w.prob >= rule()["P"] - 1e-9)


def stage_rows4(a):
    axes = a.axes.split(",")
    keep = [r for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == SETS["row4"] and r["axis"] not in axes]
    new, miss = [], {}
    for r in gt_rows():
        if r["axis"] not in axes:
            continue
        t = {"A": a_text, "V": v_text, "AVB": avb_text}[r["axis"]](r["source"], r["item_id"])
        if not t:
            miss[(r["source"], r["axis"])] = miss.get((r["source"], r["axis"]), 0) + 1
            continue
        new += G.row(SETS["row4"], r, t)
    G.add_rows(SETS["row4"], keep + new)
    print(f"{SETS['row4']} rows ({','.join(axes)}): {len(new) // 2}; no tool text: {miss}")


def stage_vcheck(a):
    """text-only caption-vs-event check, the 10/30 prompt and schema (gen_stage2_1030.VCHK_*), cache calls/vcap_check/<uid>.json."""
    from google import genai
    import os, hashlib
    from concurrent.futures import ThreadPoolExecutor
    cache = O.OUT / "calls" / "vcap_check"
    cache.mkdir(parents=True, exist_ok=True)
    todo = []
    for r in gt_rows():
        if r["axis"] != "V" or (cache / f"{r['uid']}.json").exists():
            continue
        c = caption(r["source"], r["item_id"])
        if c is None:
            continue
        meta_items = _prompt_items(r["source"])
        evs = meta_items[r["item_id"]]["events"]
        lines = [f"- event_{k + 1}: {e['definition']}" for k, e in enumerate(evs) if f"event_{k + 1}" in r["gt"]]
        user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() +
                "\n\nTarget visual events:\n" + "\n".join(lines) +
                "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
                "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
                "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
                "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
        todo.append((r, dict(system=G.VCHK_SYSTEM, user=user, media=None, schema=G.VCHK_SCHEMA, anchor=[])))
    print(f"[vcap_check] to do {len(todo)}", flush=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def one(x):
        r, c = x
        try:
            parsed, raw = O.call(client, a.model, c, {"obs": {}})
        except Exception as e:
            return f"error {type(e).__name__}"
        json.dump(dict(status="ok", parsed=parsed, raw=raw, user=c["user"], user_md5=hashlib.md5(c["user"].encode()).hexdigest(),
                       uid=r["uid"], model=a.model, thinking="high", time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(cache / f"{r['uid']}.json", "w"))
        return "ok"

    n = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, todo)):
            n[s] = n.get(s, 0) + 1
            if i % 50 == 0:
                print(f"[vcap_check] {i + 1}/{len(todo)} {n}", flush=True)
    print(f"[DONE] vcap_check: {n}", flush=True)


_PI = {}


def _prompt_items(src):
    if src not in _PI:
        _PI[src] = {x["item_id"]: x for x in json.load(open(O.PROMPTS[src]))}
    return _PI[src]


def stage_rows5(a):
    new = []
    for r in gt_rows():
        if r["axis"] != "A":
            continue
        g4, g5 = a_text(r["source"], r["item_id"]), a_text(r["source"], r["item_id"], gated=True)
        if g4 is None:
            continue
        if g5 and g5 != g4:
            new += G.row(SETS["row5"], r, g5)
    G.add_rows(SETS["row5"], new)
    print(f"{SETS['row5']} rows (A, gated text differs from HG4): {len(new) // 2}")


def stage_framing(a):
    S = G.framing_sentences()
    rb, rc, log = [], [], []
    for r in gt_rows():
        if r["axis"] == "AVB" and fires(r["item_id"]):
            t = avb_text(r["source"], r["item_id"])
        elif r["axis"] == "V":
            vc = G.vcheck(r["uid"]) or {}
            if not any(vc.get(e) == "not_mentioned" for e in r["gt"]):
                continue
            t = v_text(r["source"], r["item_id"])
        else:
            continue
        if not t:
            continue
        b, c = S[r["axis"]]
        rb += G.row(SETS["frb"], r, t + "\n\nNote: " + b)
        rc += G.row(SETS["frc"], r, t + "\n\nNote: " + c)
        log.append(dict(uid=r["uid"], axis=r["axis"], b=b, c=c))
    G.add_rows(SETS["frb"], rb); G.add_rows(SETS["frc"], rc)
    json.dump(log, open(O.OUT / "hd_framing_sentences_1101.json", "w"), indent=1)
    print(f"framing rows: {len(rb) // 2} (AVB {sum(x['axis'] == 'AVB' for x in log)}, V {sum(x['axis'] == 'V' for x in log)})")


def admitted(r):
    src, iid, ax = r["source"], r["item_id"], r["axis"]
    if ax == "A":
        g5, g4 = a_text(src, iid, gated=True), a_text(src, iid)
        return None if g4 is None else ("closed" if not g5 else ("open_reused" if g5 == g4 else "open_new_call"))
    if ax == "V":
        vc = G.vcheck(r["uid"])
        return None if vc is None else ("open_reused" if any(vc.get(e) == "contradicts" for e in r["gt"]) else "closed")
    return "open_reused" if fires(iid) else "closed"


def stage_groups(a):
    t = pd.DataFrame([dict(group=GROUP[r["source"]], axis=r["axis"], g=admitted(r) or "pending") for r in gt_rows()])
    t = t.groupby(["group", "axis", "g"]).size().unstack(fill_value=0)
    t.to_csv(O.OUT / "hd_stage2_groups_1101.csv")
    print(t.to_string())


def call_label(set_name, r):
    f = O.OUT / "calls" / COND / f"{set_name}__{r['uid']}.json"
    if not f.exists():
        return ""
    rec = json.load(open(f))
    return O.obs_label(rec, r["axis"], r["gt"]) if rec["status"] == "ok" else ""


def stage_score(a):
    from t2av_eval.scoring import lookup as RS
    g4uids = {r["uid"] for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == SETS["row4"] and r["cond"] == COND}
    out = []
    for r in gt_rows():
        if r["uid"] not in g4uids:
            continue
        src, iid, ax, gt = r["source"], r["item_id"], r["axis"], r["gt"]
        anc = RS.row_label(O.anchor_df(src), iid, ax, gt)
        g4 = call_label(SETS["row4"], r)
        adm = admitted(r)
        d = dict(group=GROUP[src], source=src, uid=r["uid"], axis=ax, variant=r["variant"], y="no" if "no" in gt.values() else "yes",
                 row1=anc, row4=g4, admitted=adm)
        if ax == "A":
            d["row5"] = anc if adm == "closed" else (g4 if adm == "open_reused" else call_label(SETS["row5"], r))
        elif ax == "V":
            d["row5"] = g4 if adm == "open_reused" else anc
        else:
            d["row5"] = g4 if adm == "open_reused" else anc
            d["row5_rule"] = "no" if adm == "open_reused" else anc
        for k, s in (("FRb", SETS["frb"]), ("FRc", SETS["frc"])):
            d[k] = call_label(s, r)
        out.append(d)
    D = pd.DataFrame(out)
    bad = D[D.row4 == ""].uid.tolist()
    if bad:
        print(f"excluded (HG4 call missing / failed): {len(bad)}")
    D = D[D.row4 != ""]
    D.to_csv(O.OUT / "hd_stage2_rows_1101.csv", index=False)
    tab = []
    for (grp, ax, part), g in D.assign(part=np.where(D.variant == "original", "original", "variant")).groupby(["group", "axis", "part"]):
        for c in [c for c in ("row1", "row4", "row5", "row5_rule") if c in g]:
            h = g[g[c].isin(["yes", "no"])]
            if len(h):
                m = RS.metrics(h.y, h[c])
                tab.append(dict(group=grp, axis=ax, part=part, cond=c, n=m["n"], n_fail=m["n_fail"], acc=m["acc"], prec=m["prec"], rec=m["rec"]))
    T = pd.DataFrame(tab)
    T.to_csv(O.OUT / "hd_stage2_table_1101.csv", index=False)
    pd.set_option("display.width", 200)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


def ma_rows(src="hm_ma"):
    """11/01 (user): mute_anchor A rows. hm_ma = P01/P02 10/28 set (78 / 72 / 78); hm_ma39 = P03-P09 11/01 set (40 / 38 / 40)."""
    out = []
    for m in map(json.loads, open(MA_DIR[src] / "manifest.jsonl")):
        out.append(dict(source=src, item_id=m["item_id"], axis="A", gt=m["gt"], variant=m["variant"], uid=f"{src}|{m['item_id']}|A",
                        split=m.get("split", m.get("participant", "")), aclass=m["aclass"]))
    return out


def stage_ma_rows(a):
    src = a.src; sets = MA_SETS_BY[src]
    """HMA4 (row 4: all FLAM lines) and HMA5 (row 5: only lines below T_flam, rows whose gated text differs from HMA4)."""
    r4, r5, miss = [], [], 0
    for r in ma_rows(src):
        t4, t5 = a_text(src, r["item_id"]), a_text(src, r["item_id"], gated=True)
        if not t4:
            miss += 1; continue
        r4 += G.row(sets["row4"], r, t4)
        if t5 and t5 != t4:
            r5 += G.row(sets["row5"], r, t5)
    G.add_rows(sets["row4"], r4); G.add_rows(sets["row5"], r5)
    print(f"{sets['row4']} rows {len(r4) // 2}, {sets['row5']} rows {len(r5) // 2}, no FLAM text {miss}")


def stage_ma_score(a):
    from t2av_eval.scoring import lookup as RS
    src = a.src; sets = MA_SETS_BY[src]; tag = "" if src == "hm_ma" else "_" + src
    out = []
    for r in ma_rows(src):
        anc = RS.row_label(O.anchor_df(src), r["item_id"], "A", r["gt"])
        g4 = call_label(sets["row4"], r)
        t4, t5 = a_text(src, r["item_id"]), a_text(src, r["item_id"], gated=True)
        adm = "closed" if not t5 else ("open_reused" if t5 == t4 else "open_new_call")
        r5 = anc if adm == "closed" else (g4 if adm == "open_reused" else call_label(sets["row5"], r))
        out.append(dict(uid=r["uid"], variant=r["variant"], split=r["split"], aclass=r["aclass"], y="no" if "no" in r["gt"].values() else "yes",
                        row1=anc, row4=g4, row5=r5, admitted=adm))
    D = pd.DataFrame(out)
    D.to_csv(O.OUT / f"hd_ma_rows{tag}_1101.csv", index=False)
    print("row 5 groups:", D.admitted.value_counts().to_dict())
    tab = []
    for c in ("row1", "row4", "row5"):
        h = D[D[c].isin(["yes", "no"])]
        m = RS.metrics(h.y, h[c])
        per = {v: round(float((g[c] == g.y).mean()), 3) for v, g in h.groupby("variant")}
        tab.append(dict(cond=c, n=m["n"], n_fail=m["n_fail"], acc=round(m["acc"], 3), prec=round(m["prec"], 3), rec=round(m["rec"], 3),
                        FA_orig=round(float((h[h.variant == "original"][c] == "no").mean()), 3),
                        FA_sham=round(float((h[h.variant == "sham"][c] == "no").mean()), 3), **{f"acc_{k}": v for k, v in per.items()}))
    T = pd.DataFrame(tab); T.to_csv(O.OUT / f"hd_ma_table{tag}_1101.csv", index=False)
    print(T.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["rows4", "vcheck", "rows5", "framing", "groups", "score", "ma_rows", "ma_score"])
    ap.add_argument("--axes", default="A,V,AVB")
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--src", default="hm_ma", choices=["hm_ma", "hm_ma39"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
