#!/usr/bin/env python3
"""Gate redesign pilot, cache only (11/06). No model, API or GPU runs; reads cached runs, tool records and stage-2 calls.

Split (fixed, written once to runs/obsval_1028/gate_pilot_1106/split.csv): groups = prompt item (generated; the LTX and MOVA videos of a
220 prompt share a group) or source recording (P03-P09, e.g. P03-20240216-084005; every clip cut from it shares a group). 30% of the
groups of each source (220, 149, 2k_25, P03-P09) go to "dev", the rest to "heldout", seed 20261107. No parameter below is tuned:
every threshold is fixed a priori (listed in PARAMS) or inherited from an existing pre-registered file.
All datasets here were inspected before (paper tables, audits); the held-out portion is held out from this pilot only.

Units and labels: the verified Section 6 units (section6_1106/units_all.csv): event-level A / V / AVB / TC, video-level TR, GT-eligible
and scored in media only (the initial judge label). Each candidate opens on a unit when its evidence condition holds and supports one
direction (PASS or FAIL).
  code rule:  the unit's label becomes the evidence direction;
  judge:      the cached stage-2 label, only where that call showed exactly the payload the candidate admits (V: caption = G4 / HG4 / K4 V;
              AVB: Synchformer lines = HG4 / G4 AVB; A: Whisper only = G4 / K4 A on items with no FLAM line). Otherwise "diagnostic".
  python gepa_stage2/gate_pilot_1106.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import collections, glob, json, re
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
import sys; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import audit_1106 as AU
import gen2k25_stage2_1104 as K
import gen_stage2_1030 as G
import tc_screen_1102 as TS

OUT = HERE / "runs/obsval_1028/gate_pilot_1106"
EV = Path((_tp.DATA + "/tools/gen_evidence_1030"))
SYA = Path((_tp.DATA + "/tools/synchformer_action_1030"))
CAPD = Path((_tp.DATA + "/real_av/eval/hdepic_main_1101_captions"))
VCAP = HERE / "runs/obsval_1028/calls/vcap_check"
SEED, DEV = 20261107, 0.30
PARAMS = dict(T_flam=json.load(open(EV / "flam_threshold.json"))["T_flam"], flam_detect=0.98, whisper_nospeech=0.5, whisper_word_prob=0.5,
              sync_T=1.8, sync_P=0.25, insync_p0=0.5, tr_order_margin_s=0.3, tr_sync_pass_s=0.5, tr_sync_fail_s=1.5)
DS = {"220 LTX": ("220", "LTX_2p3", "g220ltx"), "220 MOVA": ("220", "MOVA", "g220mova"), "149 LTX": ("149", "LTX_2p3", "g149"),
      "2k_25 LTX": ("gen2k25", "LTX_2p3", "g2k25"), "P03-P09": ("p3p9", "P03-P09", "hm_p3p9")}
GROUP_OF = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA", "P03-P09": "P03-P09"}
PROMPTS = {"220": HERE.parents[2] / "new_prompts/generated/relative_500_v5_fixed.json",
           "149": Path((_tp.DATA + "/gen_holdout_149_1030/prompts_gen149.json")),
           "gen2k25": Path((_tp.DATA + "/gen_prolific2k25_1104/prompts_gen2k25.json")),
           "p3p9": Path((_tp.DATA + "/real_av_holdout_p3p9_1028/prompts_hdepic_p3p9.json")),
           "ma39": Path((_tp.DATA + "/real_av_holdout_p3p9_1028/mute_anchor_1101/prompts.json"))}
COUNT_WORD = re.compile(r"\b(once|twice|thrice|(one|two|three|four|five|six|seven)\s+times|\d+\s+times)\b", re.I)
ORDER_WORD = re.compile(r"\b(then|after|afterwards|before|followed by|first|next|finally|subsequently)\b", re.I)
TIME_WORD = re.compile(r"\b\d+(\.\d+)?\s*(s|sec|secs|seconds)\b|\b\d{1,2}:\d{2}\b", re.I)


# ------------------------------------------------------------------ split
def group_id(ds, item):
    if ds == "P03-P09":
        m = re.match(r"hdepic_(P\d\d-\d{8}-\d{6})", item)
        return "p3p9:" + (m.group(1) if m else item)
    return f"{DS[ds][0]}:{item}"


def make_split(U):
    f = OUT / "split.csv"
    if f.exists():
        return pd.read_csv(f)
    g = U[["dataset", "item"]].drop_duplicates().assign(group=lambda t: [group_id(d, i) for d, i in zip(t.dataset, t["item"])])
    g["source"] = g.group.str.split(":").str[0]
    rng = np.random.default_rng(SEED)
    pick = {}
    for s, q in g.drop_duplicates("group").groupby("source"):
        grp = sorted(q.group)
        dev = set(rng.choice(grp, size=int(round(DEV * len(grp))), replace=False))
        pick.update({x: ("dev" if x in dev else "heldout") for x in grp})
    g["portion"] = g.group.map(pick)
    g.to_csv(f, index=False)
    return g


# ------------------------------------------------------------------ evidence readers
_ITEMS = {}


def item(src, iid):
    if src not in _ITEMS:
        _ITEMS[src] = {x["item_id"]: x for x in json.load(open(PROMPTS[src]))}
    return _ITEMS[src].get(iid)


def ev_rec(evd, model, iid):
    f = EV / evd / f"{model}__{iid}.json"
    return json.load(open(f)) if f.exists() else None


def whisper_evidence(rec, text):
    segs = [s for s in rec["whisper"].get("segments", []) if s["no_speech_prob"] < PARAMS["whisper_nospeech"]]
    words = [w for s in segs for w in s.get("words", [])]
    target = set(TS.norm(text))
    hit = [w for w in words if set(TS.norm(w["word"])) & target and w.get("probability", 0) >= PARAMS["whisper_word_prob"]]
    other = [w for w in words if not (set(TS.norm(w["word"])) & target) and w.get("probability", 0) >= PARAMS["whisper_word_prob"]]
    return dict(word_heard=bool(hit), other_confident_words=len(other), any_speech=bool(segs), n_hits=len(hit), hit_times=sorted(w["start"] for w in hit))


def flam_evidence(rec, eid):
    q = next((x["queries"][0] for x in rec.get("events", []) if x.get("event_id") == eid and x.get("queries")), None)
    if q is None or q not in rec["flam"]:
        return None
    f = rec["flam"][q]
    det = [d for d in f["detections"] if (d.get("peak_score") or 0) >= PARAMS["flam_detect"]]
    return dict(max_score=f["max_score"], detected=bool(det), n_det=len(det), times=sorted(d["peak_time"] for d in det))


def caption_text(ds, iid):
    if ds == "P03-P09":
        if not hasattr(caption_text, "hd"):
            caption_text.hd = {k.split("/")[0]: v["caption"] for k, v in json.load(open(CAPD / "p3p9.json")).items()}
        return caption_text.hd.get(iid)
    return G.caption(DS[ds][2], iid)


def vcap(uid):
    f = VCAP / f"{uid}.json"
    if not f.exists():
        return None
    return {e["event_id"]: e["verdict"] for e in (json.load(open(f)).get("parsed") or {}).get("per_event", [])}


# ------------------------------------------------------------------ candidates
def evidence_rows(U, D):
    """one row per (candidate, unit) where the candidate's evidence can be computed: open (bool), direction (yes / no)."""
    out = []
    add = lambda cand, u, opened, direction, judge=None, reuse=None, **kw: out.append(dict(candidate=cand, dataset=u.dataset, unit=u.unit, item=u.item,
                                                                                          y=u.gt_y, init=u.pred, opened=bool(opened), direction=direction,
                                                                                          judge=judge, reuse=reuse, **kw))
    syncgen = pd.read_csv(HERE / "runs/obsval_1028/flam_sync_audit_1106/events.csv")
    syncgen["dsname"] = syncgen.apply(lambda r: {"220": f"220 {'LTX' if r.model == 'LTX_2p3' else 'MOVA'}", "149": "149 LTX", "gen2k25": "2k_25 LTX"}[str(r.set)], axis=1)
    SG = syncgen.set_index(["dsname", "item_id", "event_id"])
    hd = pd.concat(pd.read_csv(f) for f in sorted((SYA / "holdout").glob("per_event_shard*.csv"))).set_index(["item_id", "event_id"])
    for u in U.itertuples():
        ds = u.dataset; s, model, src = DS[ds]
        e_id = u.event if isinstance(u.event, str) else ""
        # ---------------- A
        if u.axis == "A":
            if ds == "P03-P09":                                         # anchor-mute set: sounding events, FLAM only
                rec = json.load(open(EV / "ma39" / f"ma39__{u.item}.json")) if (EV / "ma39" / f"ma39__{u.item}.json").exists() else None
                fe = flam_evidence(rec, e_id) if rec else None
                if fe:
                    add("A1 FLAM detected -> PASS", u, fe["detected"], "yes")
                    add("A0 FLAM below T_flam -> FAIL (current A gate, absence alone)", u, fe["max_score"] < PARAMS["T_flam"], "no")
                continue
            it = item(s, u.item); idx = int(e_id.split("_")[1]) - 1; e = it["events"][idx]
            rec = ev_rec(s if s != "gen2k25" else "gen2k25", model, u.item)
            if rec is None:
                continue
            uid = f"{src}|{u.item}|A"
            wp, fl, present = G.a_parts(src, u.item)
            if e["modality"] == "speech":
                we = whisper_evidence(rec, e.get("text", ""))
                # cached stage-2 A call shows exactly the Whisper text when the item has no FLAM line
                st = D[ds]["s2av"][0]
                lab, ok = AU.s2_event(AU.stage2_rec(st, uid), "A", e_id)
                reuse = (not fl) and ok == "ok"
                add("A2 required word heard (p >= .5) -> PASS", u, we["word_heard"], "yes", lab if reuse else None, reuse)
                add("A3 word absent but other confident speech -> FAIL", u, (not we["word_heard"]) and we["other_confident_words"] > 0, "no", lab if reuse else None, reuse)
                add("A4 word absent (alone; reference only)", u, not we["word_heard"], "no", lab if reuse else None, reuse)
                add("A5 current gate: Whisper shown when any required word of the item is heard (PASS-leaning payload)", u, present, "yes",
                    None, False, note="payload, not a direction-coded rule")
            elif e["modality"] == "sounding_action":
                fe = flam_evidence(rec, e_id)
                if fe:
                    add("A1 FLAM detected -> PASS", u, fe["detected"], "yes")
                    add("A0 FLAM below T_flam -> FAIL (current A gate, absence alone)", u, fe["max_score"] < PARAMS["T_flam"], "no")
        # ---------------- V
        elif u.axis == "V":
            vc = vcap(f"{src}|{u.item}|V")
            if vc is None or e_id not in vc:
                continue
            j = U4.get((ds, u.unit))
            add("V1 caption check 'describes' -> PASS", u, vc[e_id] == "describes", "yes", j, j is not None)
            add("V2 caption check 'contradicts' -> FAIL (current V gate)", u, vc[e_id] == "contradicts", "no", j, j is not None)
        # ---------------- AVB
        elif u.axis == "AVB":
            if ds == "P03-P09":
                if (u.item, e_id) not in hd.index:
                    continue
                r = hd.loc[(u.item, e_id)]; r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                if r.status != "ok":
                    continue
                lab, ok = AU.s2_event(AU.stage2_rec("HG4", f"hm_p3p9|{u.item}|AVB"), "AVB", e_id)
                j = lab if ok == "ok" else None
                localized = r.method == "real_window_multi"
                add("B1 Synchformer |off| >= 1.8 s & p >= .25 -> FAIL (current rule, per event)", u,
                    abs(r.offset) >= PARAMS["sync_T"] - 1e-9 and r.prob >= PARAMS["sync_P"] - 1e-9, "no", j, j is not None)
                add("B2 in sync on a real-footage window (offset 0, p0 >= .5) -> PASS", u,
                    localized and r.offset == 0 and r.p_offset0 >= PARAMS["insync_p0"], "yes", j, j is not None)
            else:
                k = (ds, u.item, e_id)
                if k not in SG.index:
                    continue
                r = SG.loc[k]; r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                t = json.loads(r.used_span)[0][0] if isinstance(r.used_span, str) else None
                localized = r.used_source == "anchor_time" and t is not None and t > 0 and r.anchor_inside_intended == True
                st, uid = ("G4", f"{src}|{u.item}|AVB") if ds != "2k_25 LTX" else ("K4", f"g2k25|{u.item}|AVB")
                lab, ok = AU.s2_event(AU.stage2_rec(st, uid), "AVB", e_id)
                j = lab if ok == "ok" and st == "G4" else None          # K4 shows all four tools: not the same payload
                add("B1 Synchformer |off| >= 1.8 s & p >= .25 -> FAIL (current rule, per event)", u,
                    abs(r.lag) >= PARAMS["sync_T"] - 1e-9 and r.conf >= PARAMS["sync_P"] - 1e-9, "no", j, j is not None)
                add("B2 in sync on a localized window (anchor t > 0 inside the FLAM/Whisper span; offset 0, p0 >= .5) -> PASS", u,
                    localized and r.lag == 0 and r.p_lag0 >= PARAMS["insync_p0"], "yes", j, j is not None)
                add("B3 in sync, any window (zero offset alone; reference only)", u, r.lag == 0, "yes", j, j is not None)
        # ---------------- TC (generated)
        elif u.axis == "TCC" and ds != "P03-P09":
            it = item(s, u.item); idx = int(e_id.split("_")[1]) - 1; e = it["events"][idx]
            _, _, counts = TS.claims(it); req = counts.get(e["id"])
            rec = ev_rec(s, model, u.item)
            if rec is None or req is None or e["modality"] == "silent_action":
                continue
            if e["modality"] == "speech":
                n = whisper_evidence(rec, e.get("text", ""))["n_hits"]
            else:
                fe = flam_evidence(rec, e_id)
                if fe is None:
                    continue
                n = fe["n_det"] if fe["max_score"] >= PARAMS["T_flam"] else 0
            cap = caption_text(ds, u.item) or ""
            cr = TS.caption_read({"set": s, "model": model, "item_id": u.item, "video": ""}, e) if False else None
            explicit = COUNT_WORD.search(cap) is not None
            add("C1 tool count == required (>= 1 located) -> PASS", u, n == req and n >= 1, "yes")
            add("C2 tool count != required AND caption states a count -> FAIL", u, n != req and explicit, "no")
            add("C3 tool count != required (alone; reference only)", u, n != req, "no")
        # ---------------- TR (generated)
        elif u.axis == "TCR" and ds != "P03-P09":
            it = item(s, u.item); order, sync, _ = TS.claims(it)
            seq = order or sync
            ids = {x["id"]: (f"event_{i + 1}", x) for i, x in enumerate(it["events"])}
            if any(ids[x][1]["modality"] == "silent_action" for x in seq):
                add("R1 audio order / sync, all relation events located", u, False, "", note="silent event in relation: not localizable")
                continue
            rec = ev_rec(s, model, u.item)
            t = {}
            for x in seq:
                k, ev = ids[x]
                if ev["modality"] == "speech":
                    h = whisper_evidence(rec, ev.get("text", ""))["hit_times"]
                else:
                    fe = flam_evidence(rec, k); h = fe["times"] if fe and fe["max_score"] >= PARAMS["T_flam"] else []
                if h:
                    t[x] = h[0]
            if len(t) < len(seq):
                add("R1 audio order / sync, all relation events located", u, False, "", note="not all located")
                continue
            if order:
                inv = max(t[a] - t[b] for i, a in enumerate(seq) for b in seq[i + 1:])
                add("R2 audio order respected by >= .3 s -> PASS", u, inv <= -PARAMS["tr_order_margin_s"], "yes")
                add("R3 audio order inverted by >= .3 s -> FAIL", u, inv >= PARAMS["tr_order_margin_s"], "no")
            else:
                gap = max(abs(t[a] - t[b]) for i, a in enumerate(seq) for b in seq[i + 1:])
                add("R2 audio events within .5 s (sync) -> PASS", u, gap <= PARAMS["tr_sync_pass_s"], "yes")
                add("R3 audio events >= 1.5 s apart (sync) -> FAIL", u, gap >= PARAMS["tr_sync_fail_s"], "no")
    return pd.DataFrame(out)


U4 = {}


def summarize(E):
    rows = []
    for (cand, grp, por), q in E.groupby(["candidate", "group", "portion"]):
        op = q[q.opened]
        rec = dict(candidate=cand, group=grp, portion=por, eligible=len(q), elig_pass=int((q.y == "yes").sum()), elig_fail=int((q.y == "no").sum()),
                   opened=len(op), open_rate=round(len(op) / len(q), 3) if len(q) else None,
                   reliability=round(float((op.y == op.direction).mean()), 3) if len(op) and op.direction.iloc[0] in ("yes", "no") else None)
        for who, lab in (("code", op.direction), ("judge", op.judge)):
            if who == "judge":
                ok = op.reuse == True
                o, l = op[ok], op.judge[ok]
                rec["judge_reuse_n"] = int(ok.sum())
            else:
                o, l = op, lab
            if not len(o) or (who == "code" and o.direction.iloc[0] not in ("yes", "no")):
                continue
            F, P = o.y == "no", o.y == "yes"
            rec.update({f"{who}_fixed_miss": int((F & (o.init == "yes") & (l == "no")).sum()),
                        f"{who}_broke_catch": int((F & (o.init == "no") & (l == "yes")).sum()),
                        f"{who}_fixed_FA": int((P & (o.init == "no") & (l == "yes")).sum()),
                        f"{who}_added_FA": int((P & (o.init == "yes") & (l == "no")).sum())})
            rec[f"{who}_net"] = rec[f"{who}_fixed_miss"] + rec[f"{who}_fixed_FA"] - rec[f"{who}_broke_catch"] - rec[f"{who}_added_FA"]
        rows.append(rec)
    return pd.DataFrame(rows)


def caption_inventory(U, S):
    rows = []
    for ds in DS:
        q = U[(U.dataset == ds) & (U.axis.isin(["V", "TCC", "TCR"]))][["item"]].drop_duplicates()
        for iid in q["item"]:
            c = caption_text(ds, iid)
            if not c:
                rows.append(dict(dataset=ds, item=iid, caption=False)); continue
            rows.append(dict(dataset=ds, item=iid, caption=True, count_word=bool(COUNT_WORD.search(c)), order_word=bool(ORDER_WORD.search(c)),
                             timestamp=bool(TIME_WORD.search(c)), words=len(c.split())))
    C = pd.DataFrame(rows).merge(S[["dataset", "item", "portion"]], on=["dataset", "item"], how="left")
    return C


def main():
    OUT.mkdir(exist_ok=True)
    U = pd.read_csv(HERE / "runs/obsval_1028/section6_1106/units_all.csv", low_memory=False)
    U = U[(U.group == U.dataset) & U.dataset.isin(list(DS))]
    for r in U[(U.cond == "row4") & (U.axis == "V") & (U.status == "scored")].itertuples():
        U4[(r.dataset, r.unit)] = r.pred
    base = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)].copy()
    S = make_split(U)
    D = AU.datasets()
    E = evidence_rows(base, D)
    E = E.merge(S[["dataset", "item", "group", "portion"]].rename(columns={"group": "split_group"}), on=["dataset", "item"], how="left")
    E["group"] = E.dataset.map(GROUP_OF)
    E.to_csv(OUT / "evidence_units.csv", index=False)
    R = summarize(E); R.to_csv(OUT / "candidates.csv", index=False)
    C = caption_inventory(U, S); C.to_csv(OUT / "caption_inventory.csv", index=False)
    bal = base.merge(S[["dataset", "item", "portion"]], on=["dataset", "item"]).groupby(["portion", "dataset", "axis"]).agg(
        units=("unit", "size"), PASS=("gt_y", lambda s: int((s == "yes").sum())), FAIL=("gt_y", lambda s: int((s == "no").sum()))).reset_index()
    bal.to_csv(OUT / "split_balance.csv", index=False)
    sg = S.groupby(["source", "portion"]).group.nunique().unstack(fill_value=0)
    json.dump(dict(seed=SEED, dev_share=DEV, params=PARAMS, groups=sg.to_dict()), open(OUT / "pilot_config.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 400); pd.set_option("display.max_colwidth", 70)
    print(sg.to_string()); print(bal.to_string(index=False))
    print(R.to_string(index=False))
    print(C.groupby(["dataset"]).agg(items=("item", "size"), with_caption=("caption", "sum"), count_word=("count_word", "sum"),
                                     order_word=("order_word", "sum"), timestamp=("timestamp", "sum")).to_string())


if __name__ == "__main__":
    main()
