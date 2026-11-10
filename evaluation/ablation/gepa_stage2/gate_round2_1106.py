#!/usr/bin/env python3
"""Gate redesign round 2 (11/06), cache only (the GPU diagnostic is sync_diag_round2_1106.py). No API / judge calls.
  (1) Whisper evidence per speech A event split into: heard / discarded by word confidence / discarded by the segment filter /
      absent with other speech / no transcript; compared with the existing A gate (item-level "required word in kept segments").
  (2) Event-linked caption evidence: the caption's mention of the target event and a count stated next to that mention; caption
      mention order for TR; fused with the audio (Whisper / FLAM) count and order. Unresolved extraction = unavailable.
  (3) Direction-specific admission calibration on the fixed development split (gate_pilot_1106/split.csv):
        FAIL-direction rule: erroneous admission = opened among GT PASS & initial PASS units / all such units;
        PASS-direction rule: erroneous admission = opened among GT FAIL & initial FAIL units / all such units.
      Targets 1 %, 5 %, 10 %. Among the predefined grid of each family, the rule with the most correctable openings whose development
      point estimate is <= target and whose denominator is >= 20 is selected; otherwise "not calibratable". Exact Clopper-Pearson 95 %
      intervals are reported. Selected rules are written to selected_rules.json (frozen) BEFORE the held-out portion is scored.
      All datasets were inspected earlier (paper tables, audits): the held-out portion is held out from this calibration only.
Units: verified Section 6 units, GT-eligible and scored in media only (initial label = media-only label).
  python gepa_stage2/gate_round2_1106.py      -> runs/obsval_1028/gate_redesign_round2/
"""
import json, re, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import beta

HERE = Path(__file__).resolve().parent
import sys; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import gate_pilot_1106 as GPI
import audit_1106 as AU
import gen_stage2_1030 as G
import tc_screen_1102 as TS

OUT = HERE / "runs/obsval_1028/gate_redesign_round2"
TARGETS = (0.01, 0.05, 0.10)
MIN_DEN = 20
GROUP_OF = GPI.GROUP_OF
NUMW = {"once": 1, "twice": 2, "thrice": 3, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "single": 1, "double": 2, "triple": 3}
STOP = {"the", "a", "an", "left", "right", "hand", "hands", "pose", "sign", "x1", "x2", "x3"}


def cp(k, n):
    if n == 0:
        return (None, None)
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return (round(float(lo), 4), round(float(hi), 4))


def stem(w):
    return TS.stem(w)


# ------------------------------------------------------------------ (1) Whisper categories
def whisper_category(rec, text):
    target = set(TS.norm(text))
    segs = rec["whisper"].get("segments", [])
    if not segs:
        return "no transcript", None
    kept = [s for s in segs if s["no_speech_prob"] < 0.5]
    best = None
    for s in segs:
        for w in s.get("words", []):
            if set(TS.norm(w["word"])) & target:
                p = w.get("probability", 0)
                k = (s["no_speech_prob"] < 0.5, p)
                best = max(best, k) if best else k
    if best is None:
        return ("absent, other speech kept" if kept else "absent, only filtered speech"), None
    if not best[0]:
        return "discarded by segment filter (no_speech_prob >= .5)", best[1]
    if best[1] < 0.5:
        return "discarded by word confidence (p < .5)", best[1]
    return "heard (kept segment, p >= .5)", best[1]


# ------------------------------------------------------------------ (2) event-linked caption evidence
def event_terms(e):
    if e["modality"] == "speech":
        return [w for w in TS.norm(e.get("text", "")) if w not in STOP][:1], "speech"
    toks = [t for t in re.split(r"[_\s]+", (e.get("action") or "").lower()) if t and t not in STOP]
    return [stem(t) for t in toks[:2]], "action"


def caption_mentions(cap, e):
    """token positions where the caption names the event (speech: the spoken word; action: the head verb / noun stem)."""
    toks = TS.norm(cap); st = [stem(t) for t in toks]
    terms, kind = event_terms(e)
    if not terms:
        return toks, []
    if kind == "speech":
        pos = [i for i, t in enumerate(toks) if t == terms[0]]
    else:
        pos = [i for i, t in enumerate(st) if t == terms[0] or (len(terms) > 1 and t == terms[1] and i > 0 and st[i - 1] == terms[0])]
    return toks, pos


def caption_count(cap, e):
    """count stated next to a mention of this event (within 6 tokens after, or the number word right before); None if mentioned
    without a count; 'unavailable' if the event is not mentioned."""
    if not cap:
        return "unavailable", "no caption"
    toks, pos = caption_mentions(cap, e)
    if not pos:
        return "unavailable", "event not mentioned"
    for i in pos:
        prev = toks[i - 1] if i > 0 else ""
        if prev in NUMW and prev not in ("one", "single") or prev.isdigit():
            return (int(prev) if prev.isdigit() else NUMW[prev]), "number before mention"
        nxt = toks[i + 1: i + 7]
        for k, w in enumerate(nxt):
            if w in ("once", "twice", "thrice"):
                return NUMW[w], "count word after mention"
            if (w in NUMW or w.isdigit()) and k + 1 < len(nxt) and nxt[k + 1] in ("times", "time"):
                return (int(w) if w.isdigit() else NUMW[w]), "N times after mention"
    if len(pos) >= 2:
        return "unavailable", "mentioned repeatedly without a stated count"
    return "unavailable", "mentioned once without a stated count"


def audio_count(rec, k, e):
    if e["modality"] == "speech":
        return GPI.whisper_evidence(rec, e.get("text", ""))["n_hits"]
    if e["modality"] == "sounding_action":
        fe = GPI.flam_evidence(rec, k)
        if fe is None:
            return None
        return fe["n_det"] if fe["max_score"] >= GPI.PARAMS["T_flam"] else 0
    return None


# ------------------------------------------------------------------ evidence table (one row per unit, all features)
def features(U, D, U4):
    syncgen = pd.read_csv(HERE / "runs/obsval_1028/flam_sync_audit_1106/events.csv")
    syncgen["dsname"] = syncgen.apply(lambda r: {"220": f"220 {'LTX' if r.model == 'LTX_2p3' else 'MOVA'}", "149": "149 LTX", "gen2k25": "2k_25 LTX"}[str(r.set)], axis=1)
    SG = syncgen.set_index(["dsname", "item_id", "event_id"])
    hd = pd.concat(pd.read_csv(f) for f in sorted((GPI.SYA / "holdout").glob("per_event_shard*.csv"))).set_index(["item_id", "event_id"])
    rows = []
    for u in U.itertuples():
        ds = u.dataset; s, model, src = GPI.DS[ds]
        e_id = u.event if isinstance(u.event, str) else ""
        base = dict(dataset=ds, group=GROUP_OF[ds], unit=u.unit, item=u.item, axis=u.axis, y=u.gt_y, init=u.pred)
        if u.axis == "A":
            if ds == "P03-P09":
                f = GPI.EV / "ma39" / f"ma39__{u.item}.json"
                fe = GPI.flam_evidence(json.load(open(f)), e_id) if f.exists() else None
                if fe:
                    rows.append(dict(base, family="A sound", flam_max=fe["max_score"]))
                continue
            it = GPI.item(s, u.item); e = it["events"][int(e_id.split("_")[1]) - 1]
            rec = GPI.ev_rec(s, model, u.item)
            if rec is None:
                continue
            wp, fl, present = G.a_parts(src, u.item)
            lab, ok = AU.s2_event(AU.stage2_rec(D[ds]["s2av"][0], f"{src}|{u.item}|A"), "A", e_id)
            judge = lab if (not fl and ok == "ok") else None
            if e["modality"] == "speech":
                cat, p = whisper_category(rec, e.get("text", ""))
                rows.append(dict(base, family="A speech", whisper_cat=cat, word_p=p, existing_gate_shows_whisper=bool(present), judge=judge))
            elif e["modality"] == "sounding_action":
                fe = GPI.flam_evidence(rec, e_id)
                if fe:
                    rows.append(dict(base, family="A sound", flam_max=fe["max_score"]))
        elif u.axis == "V":
            vc = GPI.vcap(f"{src}|{u.item}|V")
            if vc and e_id in vc:
                rows.append(dict(base, family="V", vcap=vc[e_id], judge=U4.get((ds, u.unit))))
        elif u.axis == "AVB":
            if ds == "P03-P09":
                if (u.item, e_id) not in hd.index:
                    continue
                r = hd.loc[(u.item, e_id)]; r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                if r.status != "ok":
                    continue
                lab, ok = AU.s2_event(AU.stage2_rec("HG4", f"hm_p3p9|{u.item}|AVB"), "AVB", e_id)
                rows.append(dict(base, family="AVB", off=abs(r.offset), prob=r.prob, p0=r.p_offset0, localized=r.method == "real_window_multi",
                                 judge=lab if ok == "ok" else None))
            else:
                k = (ds, u.item, e_id)
                if k not in SG.index:
                    continue
                r = SG.loc[k]; r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
                t = json.loads(r.used_span)[0][0] if isinstance(r.used_span, str) else None
                st, uid = ("G4", f"{src}|{u.item}|AVB") if ds != "2k_25 LTX" else ("K4", f"g2k25|{u.item}|AVB")
                lab, ok = AU.s2_event(AU.stage2_rec(st, uid), "AVB", e_id)
                rows.append(dict(base, family="AVB", off=abs(r.lag), prob=r.conf, p0=r.p_lag0,
                                 localized=bool(r.used_source == "anchor_time" and t and t > 0 and r.anchor_inside_intended == True),
                                 judge=lab if ok == "ok" and st == "G4" else None))
        elif u.axis == "TCC" and ds != "P03-P09":
            it = GPI.item(s, u.item); idx = int(e_id.split("_")[1]) - 1; e = it["events"][idx]
            _, _, counts = TS.claims(it); req = counts.get(e["id"])
            if req is None:
                continue
            rec = GPI.ev_rec(s, model, u.item)
            ac = audio_count(rec, e_id, e) if rec else None
            cc, why = caption_count(GPI.caption_text(ds, u.item), e)
            rows.append(dict(base, family="TC", required=req, audio_count=ac, caption_count=cc if cc != "unavailable" else None, caption_why=why,
                             modality=e["modality"]))
        elif u.axis == "TCR" and ds != "P03-P09":
            it = GPI.item(s, u.item); order, sync, _ = TS.claims(it)
            seq = order or sync
            ids = {x["id"]: (f"event_{i + 1}", x) for i, x in enumerate(it["events"])}
            cap = GPI.caption_text(ds, u.item) or ""
            first = {}
            for x in seq:
                _, pos = caption_mentions(cap, ids[x][1]) if cap else ([], [])
                if pos:
                    first[x] = pos[0]
            cap_state = "unavailable: not all relation events mentioned" if len(first) < len(seq) else (
                "unavailable: sync has no caption timing" if sync and not order else
                ("consistent" if all(first[a] < first[b] for i, a in enumerate(seq) for b in seq[i + 1:]) else "inverted"))
            rec = GPI.ev_rec(s, model, u.item); t = {}
            for x in seq:
                k, ev = ids[x]
                if ev["modality"] == "silent_action" or rec is None:
                    continue
                if ev["modality"] == "speech":
                    h = GPI.whisper_evidence(rec, ev.get("text", ""))["hit_times"]
                else:
                    fe = GPI.flam_evidence(rec, k); h = fe["times"] if fe and fe["max_score"] >= GPI.PARAMS["T_flam"] else []
                if h:
                    t[x] = h[0]
            audio_state = "unavailable: silent event in relation" if any(ids[x][1]["modality"] == "silent_action" for x in seq) else (
                "unavailable: not all located" if len(t) < len(seq) else (
                    ("consistent" if max(t[a] - t[b] for i, a in enumerate(seq) for b in seq[i + 1:]) <= -0.3 else
                     "inverted" if max(t[a] - t[b] for i, a in enumerate(seq) for b in seq[i + 1:]) >= 0.3 else "ambiguous (< .3 s)") if order else
                    ("consistent" if max(abs(t[a] - t[b]) for i, a in enumerate(seq) for b in seq[i + 1:]) <= 0.5 else
                     "inverted" if max(abs(t[a] - t[b]) for i, a in enumerate(seq) for b in seq[i + 1:]) >= 1.5 else "ambiguous")))
            rows.append(dict(base, family="TR", kind="order" if order else "sync", caption_state=cap_state, audio_state=audio_state))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ rule grid: (family, rule name, direction, function row -> bool)
def grid():
    R = []
    cats = ["absent, other speech kept", "absent, only filtered speech", "no transcript", "discarded by segment filter (no_speech_prob >= .5)",
            "discarded by word confidence (p < .5)"]
    R.append(("A speech", "absent, other speech kept", "no", lambda r: r.whisper_cat == cats[0]))
    R.append(("A speech", "absent (any: other speech, filtered speech or no transcript)", "no", lambda r: r.whisper_cat in cats[:3]))
    R.append(("A speech", "absent or discarded by a filter", "no", lambda r: r.whisper_cat in cats))
    R.append(("A speech", "existing gate does NOT show Whisper (no required word in kept segments)", "no", lambda r: not r.existing_gate_shows_whisper))
    for p in (0.3, 0.5, 0.7, 0.9):
        R.append(("A speech", f"heard, word p >= {p}", "yes", lambda r, p=p: r.word_p is not None and not pd.isna(r.word_p) and r.whisper_cat.startswith(("heard", "discarded by word")) and r.word_p >= p))
    R.append(("A speech", "existing gate shows Whisper (required word in kept segments)", "yes", lambda r: bool(r.existing_gate_shows_whisper)))
    for tau in (0.02, 0.05, 0.1, 0.2, 0.2705, 0.5):
        R.append(("A sound", f"FLAM max < {tau}", "no", lambda r, tau=tau: r.flam_max < tau))
    for tau in (0.98, 0.99, 0.995, 0.999):
        R.append(("A sound", f"FLAM max >= {tau}", "yes", lambda r, tau=tau: r.flam_max >= tau))
    R.append(("V", "caption check describes", "yes", lambda r: r.vcap == "describes"))
    R.append(("V", "caption check contradicts", "no", lambda r: r.vcap == "contradicts"))
    for T in (0.6, 1.0, 1.4, 1.8):
        for P in (0.1, 0.25, 0.5):
            R.append(("AVB", f"abs offset >= {T} s and p >= {P}", "no", lambda r, T=T, P=P: r.off >= T - 1e-9 and r.prob >= P - 1e-9))
    for q in (0.5, 0.7, 0.9, 0.95):
        R.append(("AVB", f"offset 0 and p(0) >= {q} on a localized window", "yes", lambda r, q=q: bool(r.localized) and r.off == 0 and r.p0 >= q))
    R.append(("TC", "caption count (event-linked) != required", "no", lambda r: r.caption_count is not None and not pd.isna(r.caption_count) and r.caption_count != r.required))
    R.append(("TC", "caption count (event-linked) == required", "yes", lambda r: r.caption_count is not None and not pd.isna(r.caption_count) and r.caption_count == r.required))
    R.append(("TC", "audio count != required and caption count != required", "no",
              lambda r: not pd.isna(r.audio_count) and not pd.isna(r.caption_count) and r.audio_count != r.required and r.caption_count != r.required))
    R.append(("TC", "audio count == required and caption count == required", "yes",
              lambda r: not pd.isna(r.audio_count) and not pd.isna(r.caption_count) and r.audio_count == r.required and r.caption_count == r.required))
    R.append(("TC", "audio count != required (>= 1 located or FLAM below T_flam)", "no", lambda r: not pd.isna(r.audio_count) and r.audio_count != r.required))
    R.append(("TC", "audio count == required (>= 1 located)", "yes", lambda r: not pd.isna(r.audio_count) and r.audio_count == r.required and r.audio_count >= 1))
    R.append(("TR", "caption mention order consistent", "yes", lambda r: r.caption_state == "consistent"))
    R.append(("TR", "caption mention order inverted", "no", lambda r: r.caption_state == "inverted"))
    R.append(("TR", "caption and audio both consistent", "yes", lambda r: r.caption_state == "consistent" and r.audio_state == "consistent"))
    R.append(("TR", "caption and audio both inverted", "no", lambda r: r.caption_state == "inverted" and r.audio_state == "inverted"))
    return R


def evaluate(F, fam, name, d, fn):
    q = F[F.family == fam]
    if not len(q):
        return None
    op = q.apply(fn, axis=1).astype(bool)
    other = "yes" if d == "no" else "no"
    risk = (q.y == other) & (q.init == other)                 # FAIL rule: GT PASS & init PASS; PASS rule: GT FAIL & init FAIL
    corr = (q.y == d) & (q.init == other)                     # correctable: GT = evidence direction, initial wrong
    n_risk, k_risk = int(risk.sum()), int((op & risk).sum())
    J = q.judge if "judge" in q else pd.Series([None] * len(q), index=q.index)
    jo = op & J.notna()
    jl = J[jo]
    return dict(eligible=len(q), elig_pass=int((q.y == "yes").sum()), elig_fail=int((q.y == "no").sum()), opened=int(op.sum()),
                coverage=round(float(op.mean()), 4), err_den=n_risk, err_num=k_risk, err_rate=round(k_risk / n_risk, 4) if n_risk else None,
                err_ci=cp(k_risk, n_risk), correctable_den=int(corr.sum()), corrected=int((op & corr).sum()),
                opened_correct=int((op & (q.y == d)).sum()),
                code_fixed=int((op & corr).sum()), code_corrupted=k_risk,
                judge_units=int(jo.sum()),
                judge_fixed=int(((q.y[jo] == d) & (q.init[jo] == other) & (jl == d)).sum()) if jo.any() else None,
                judge_corrupted=int(((q.y[jo] == other) & (q.init[jo] == other) & (jl == d)).sum()) if jo.any() else None,
                judge_broke_other=int(((q.y[jo] == q.init[jo]) & (jl != q.init[jo])).sum()) if jo.any() else None)


def main():
    OUT.mkdir(exist_ok=True)
    U = pd.read_csv(HERE / "runs/obsval_1028/section6_1106/units_all.csv", low_memory=False)
    U = U[(U.group == U.dataset) & U.dataset.isin(list(GPI.DS))]
    U4 = {(r.dataset, r.unit): r.pred for r in U[(U.cond == "row4") & (U.axis == "V") & (U.status == "scored")].itertuples()}
    base = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)].copy()
    S = pd.read_csv(HERE / "runs/obsval_1028/gate_pilot_1106/split.csv")
    D = AU.datasets()
    F = features(base, D, U4).merge(S[["dataset", "item", "portion"]], on=["dataset", "item"], how="left")
    F.to_csv(OUT / "unit_features.csv", index=False)
    # (1) Whisper categories against the existing A gate
    W = F[F.family == "A speech"]
    W.groupby(["group", "portion", "whisper_cat", "existing_gate_shows_whisper"]).agg(
        units=("unit", "size"), gt_fail=("y", lambda s: int((s == "no").sum())), init_fail=("init", lambda s: int((s == "no").sum()))).reset_index().to_csv(OUT / "whisper_categories.csv", index=False)
    # (2) caption extraction status
    F[F.family == "TC"].groupby(["group", "portion", "caption_why"]).size().rename("events").reset_index().to_csv(OUT / "tc_caption_extraction.csv", index=False)
    F[F.family == "TR"].groupby(["group", "portion", "kind", "caption_state", "audio_state"]).size().rename("videos").reset_index().to_csv(OUT / "tr_evidence_states.csv", index=False)
    # (3) calibration on dev
    R = grid()
    dev = []
    for grp in ("P03-P09", "LTX", "MOVA"):
        Fd = F[(F.group == grp) & (F.portion == "dev")]
        for fam, name, d, fn in R:
            ev = evaluate(Fd, fam, name, d, fn)
            if ev:
                dev.append(dict(group=grp, family=fam, rule=name, direction="FAIL" if d == "no" else "PASS", **ev))
    DV = pd.DataFrame(dev); DV.to_csv(OUT / "dev_rule_grid.csv", index=False)
    sel = []
    for (grp, fam, direc), q in DV.groupby(["group", "family", "direction"]):
        for tgt in TARGETS:
            ok = q[(q.err_den >= MIN_DEN) & (q.err_rate.fillna(1) <= tgt) & (q.opened > 0)]
            if not len(ok):
                why = "not calibratable: risk denominator < 20" if (q.err_den < MIN_DEN).all() else "no rule meets the target with any opening"
                sel.append(dict(group=grp, family=fam, direction=direc, target=tgt, rule=None, status=why, dev_err_den=int(q.err_den.max())))
                continue
            b = ok.sort_values(["corrected", "opened"], ascending=False).iloc[0]
            sel.append(dict(group=grp, family=fam, direction=direc, target=tgt, rule=b.rule, status="selected", dev_err_num=int(b.err_num), dev_err_den=int(b.err_den),
                            dev_err_rate=b.err_rate, dev_err_ci=b.err_ci, dev_ci_upper_within_target=bool(b.err_ci[1] is not None and b.err_ci[1] <= tgt),
                            dev_corrected=int(b.corrected), dev_correctable=int(b.correctable_den), dev_opened=int(b.opened), dev_eligible=int(b.eligible)))
    SEL = pd.DataFrame(sel)
    frozen = dict(written=time.strftime("%Y-%m-%dT%H:%M:%S"), split="runs/obsval_1028/gate_pilot_1106/split.csv (dev portion only)", targets=TARGETS,
                  min_risk_denominator=MIN_DEN, selection="most corrections among rules with dev erroneous-admission point estimate <= target",
                  heldout_scored=False, rules=SEL.to_dict("records"))
    json.dump(frozen, open(OUT / "selected_rules.json", "w"), indent=1, default=str)      # frozen before the held-out portion is read
    # held-out evaluation of the frozen rules
    fz = json.load(open(OUT / "selected_rules.json"))
    rules = {name: (fam, d, fn) for fam, name, d, fn in R}
    ho = []
    for r in fz["rules"]:
        if r["status"] != "selected":
            continue
        fam, d, fn = rules[r["rule"]]
        Fh = F[(F.group == r["group"]) & (F.portion == "heldout")]
        ev = evaluate(Fh, fam, r["rule"], d, fn)
        if ev:
            ho.append(dict(group=r["group"], family=fam, direction=r["direction"], target=r["target"], rule=r["rule"], **ev,
                           heldout_err_within_target=bool(ev["err_rate"] is not None and ev["err_rate"] <= r["target"])))
    HO = pd.DataFrame(ho); HO.to_csv(OUT / "heldout_frozen_rules.csv", index=False)
    SEL.to_csv(OUT / "selected_rules.csv", index=False)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 60)
    print(pd.read_csv(OUT / "whisper_categories.csv").to_string(index=False))
    print(pd.read_csv(OUT / "tc_caption_extraction.csv").to_string(index=False))
    print(pd.read_csv(OUT / "tr_evidence_states.csv").to_string(index=False))
    print(SEL.to_string(index=False)); print(HO.to_string(index=False))


if __name__ == "__main__":
    main()
