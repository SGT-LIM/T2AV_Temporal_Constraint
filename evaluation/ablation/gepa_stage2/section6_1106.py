#!/usr/bin/env python3
"""Section 6 verified results (user 11/06). No model / API calls; reads run CSVs, call caches and GT files only, writes only to
runs/obsval_1028/section6_1106/.
Protocol (independent per-axis revision design, no cross-axis propagation of stage-2 revisions):
  applicability   TR only for order / sync items; AVB only on audio events; TC per counted event; A / V have no prerequisite.
  GT prerequisite AVB: A and V of the event PASS in GT; TC: A, V, AVB (audio event) or V (silent event) PASS in GT; TR: every event.
  judge prereq    media only, always shown, gated: the shared media-only stage-1 labels; one call: the one-call run's own labels.
                  A judge-gated / inherited downstream label is excluded, never scored as FAIL.
  direct output   media only / one call: the run's per-event label (status ok); always shown: the stage-2 call of the axis
                  (A / V: G4 / HG4 / K4; AVB / TR / TC: GA4 / HA4 / K4); gated: stage-2 call of the axis when its gate opens
                  (A: FLAM / Whisper gate, G5 / K5 or the row-4 call when the gated text equals the full text; V: caption check
                  contradicts a GT event of the row, G4 / HG4 / K4; AVB: Synchformer rule, G4 / HG4 / K4), else the media-only label
                  (closed gate = unchanged). TR / TC have no gate (closed).
  missing outputs ("treated as failure" fills, no stage-2 call / entry, open gate without a call, API errors) are excluded and counted.
AVB / TR / TC units come from audit_1106 (runs/obsval_1028/audit_1106/units.csv); A / V units are built here.
  python gepa_stage2/audit_1106.py && python gepa_stage2/section6_1106.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import collections, json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import audit_1106 as AU
import gen_stage2_1030 as G
import gen2k25_stage2_1104 as K
import hd_stage2_1101 as H
import obs_judge_1028 as O
import rep_scoring as RS

OUT = O.OUT / "section6_1106"
CONDS = ("row1", "row2", "row4", "row5")
CNAME = {"row1": "media only", "row2": "one call", "row4": "always shown", "row5": "gated"}
SRC = {"220 LTX": "g220ltx", "220 MOVA": "g220mova", "149 LTX": "g149", "2k_25 LTX": "g2k25", "P03-P09": "hm_p3p9"}
A5 = {"g220ltx": "G5", "g220mova": "G5", "g149": "G5", "g2k25": "K5"}
MISSING = {"API / run error", "item missing from run", "no direct output (fill / invalid)", "no direct output", "no stage-2 call",
           "no stage-2 entry", "gate open, no stage-2 call", "gate undetermined (no caption check)", "judge prereq not output (fill)"}


# ------------------------------------------------------------------ event-level A / V / AVB units (11/06 b: Section 5 units)
MA_DIR = Path((_tp.DATA + "/real_av_holdout_p3p9_1028/mute_anchor_1101"))
MA_ONECALL = O.RES / "hdepic_ma39_onecall_A_g36_1105"
MISS_ST = {"item": "item missing from run", "error": "API / run error", "fill": "no direct output (fill / invalid)",
           "no_stage2": "no stage-2 call", "no_stage2_entry": "no stage-2 entry", "missing": "no direct output", "gated": "no direct output"}


def a_gate(src, iid):
    g5, g4 = G.a_text(src, iid, gated=True), G.a_text(src, iid)
    return bool(g5), bool(g5) and g5 == g4


def av_rows(D):
    """[(dataset, row dict(uid, item_id, axis, gt, variant, part))]"""
    out = []
    for r in G.gt_rows():
        if r["axis"] in ("A", "V"):
            name = {"g220ltx": "220 LTX", "g220mova": "220 MOVA", "g149": "149 LTX"}[r["source"]]
            out.append((name, dict(r, part="")))
    for r in K.gt_rows():                      # 2k_25 V: every GT event of the row, with or without a specified hand side (11/06 c)
        if r["axis"] in ("A", "V"):
            out.append(("2k_25 LTX", dict(r, part="")))
    for r in H.gt_rows():
        if r["source"] == "hm_p3p9" and r["axis"] == "V":
            out.append(("P03-P09", dict(r, part="")))
    return out


def ev(dataset, axis, iid, eid, cond, y, gt_elig, status, reason="", pred="", gate=None, variant="", part=""):
    return dict(dataset=dataset, axis=axis, unit=f"{iid}|{axis}|{eid}" + (f"|{part}" if part else ""), item=iid, event=eid, cond=cond,
                gt_elig=gt_elig, gt_y=y if gt_elig else "", status=status, reason=reason, y=y if status == "scored" else "",
                pred=pred if status == "scored" else "", gate_open=gate, variant=variant)


def av_events(D):
    """A / V per GT event. Direct output per event only (stage-1 run per-event entry with status ok, or the stage-2 call's entry);
    no row-level label is used."""
    out = []
    for name, r in av_rows(D):
        dsn = "2k_25 LTX" if name.startswith("2k_25") else name
        ds, src = D[dsn], SRC[dsn]
        iid, ax = r["item_id"], r["axis"]
        uid = f"{ds['s2'][1]}|{iid}|{ax}"
        # row-level gate (the pipeline opens or closes the gate per GT row)
        if ax == "A":
            op, same = a_gate(src, iid)
            g5set = (ds["s2av"][0] if same else A5[src]) if op else None
        else:
            vc = G.vcheck(uid)
            op = None if vc is None else any(vc.get(x) == "contradicts" for x in r.get("gate_gt", r["gt"]))
            g5set = ds["s2av"][0] if op else None
        rec4 = AU.stage2_rec(ds["s2av"][0], uid)
        rec5 = AU.stage2_rec(g5set, uid) if g5set else None
        for eid, y in r["gt"].items():
            if eid == "__item__":
                continue
            if y not in ("yes", "no"):
                for c in CONDS:
                    out.append(ev(name, ax, iid, eid, c, y, False, "excluded", "GT label missing (tie / no majority)", variant=r.get("variant", ""), part=r["part"]))
                continue
            for c in CONDS:
                if c in ("row1", "row2") or (c == "row5" and op is False):
                    e = (ds["r2"] if c == "row2" else ds["r1"]).get(iid)
                    lab, st = ("", "item") if e is None else (("", "error") if e["error"] else e[ax].get(eid, ("", "missing")))
                elif c == "row4":
                    lab, st = AU.s2_event(rec4, ax, eid)
                elif op is None:
                    lab, st = "", "gate undetermined"
                else:
                    lab, st = AU.s2_event(rec5, ax, eid)
                ok = lab in ("yes", "no") and st == "ok"
                rsn = "" if ok else ("gate undetermined (no caption check)" if st == "gate undetermined" else
                                     ("gate open, no stage-2 call" if c == "row5" and st == "no_stage2" else MISS_ST.get(st, "no direct output")))
                out.append(ev(name, ax, iid, eid, c, y, True, "scored" if ok else "excluded", rsn, lab, op if c == "row5" else None,
                              r.get("variant", ""), r["part"]))
    return out


def ma_events():
    """P03-P09 A = anchor-mute set hm_ma39 (mute_anchor + original; shams excluded), per GT event.
    media only: hdepic_main_ma39_row1_A_g36_1101; one call: hdepic_ma39_onecall_A_g36_1105; always shown: HMB4;
    gated: the FLAM gate decision of hd_ma_rows_hm_ma39_1101.csv (closed -> media only, open_reused -> HMB4, open_new_call -> HMB5)."""
    adm = pd.read_csv(O.OUT / "hd_ma_rows_hm_ma39_1101.csv").set_index("uid").admitted
    r1 = AU.load_run([str(p) for p in O.ANCHOR["hm_ma39"]])
    r2 = AU.load_run(sorted(str(f) for f in MA_ONECALL.glob("shard*.csv")))
    out = []
    for m in map(json.loads, open(MA_DIR / "manifest.jsonl")):
        if m["variant"] == "sham":
            continue
        iid = m["item_id"]; uid = f"hm_ma39|{iid}|A"; a = adm.get(uid, "closed")
        rec4 = AU.stage2_rec("HMB4", uid); rec5 = AU.stage2_rec("HMB5", uid) if a == "open_new_call" else rec4
        for eid, y in m["gt"].items():
            for c in CONDS:
                if c in ("row1", "row2") or (c == "row5" and a == "closed"):
                    e = (r2 if c == "row2" else r1).get(iid)
                    lab, st = ("", "item") if e is None else (("", "error") if e["error"] else e["A"].get(eid, ("", "missing")))
                else:
                    lab, st = AU.s2_event(rec4 if c == "row4" else rec5, "A", eid)
                ok = lab in ("yes", "no") and st == "ok"
                out.append(ev("P03-P09", "A", iid, eid, c, y, True, "scored" if ok else "excluded", "" if ok else MISS_ST.get(st, "no direct output"),
                              lab, (a != "closed") if c == "row5" else None, m["variant"]))
    return out


def avb_events(D):
    """AVB per audio event of each AVB GT row; same rules as audit_1106.label_unit, applied event by event."""
    out = []
    for name, ds in D.items():
        for u in AU.units(name, ds):
            if u["axis"] != "AVB":
                continue
            iid = u["item"]; item = ds["items"].get(iid)
            evs = {e: a for e, a, _ in AU.events_of(item)} if item else {}
            var = ("shift_early" if "_AVBearly" in iid else "shift_late" if "_AVBlate" in iid else "original") if ds["hd"] else ""
            fires = bool(ds["fires"](iid))
            recs = {c: AU.stage2_rec((ds["s2"] if c == "row4" else ds["s2av"])[0], f"{ds['s2'][1]}|{iid}|AVB") for c in ("row4", "row5")}
            for eid, y in u["gt"].items():
                if eid == "__item__":
                    continue
                base = ("no prompt item" if item is None else "GT label missing (tie / no majority)" if y not in ("yes", "no") or eid not in evs
                        else "not applicable (silent)" if not evs[eid] else "")
                if not base:
                    ok, base = AU.gt_ok(ds, iid, eid, True, "AV")
                for c in CONDS:
                    g5 = fires if c == "row5" else None
                    if base:
                        out.append(ev(name, "AVB", iid, eid, c, y, False, "excluded", base, gate=g5, variant=var)); continue
                    ok, rs = AU.judge_ok(ds["r2"] if c == "row2" else ds["r1"], iid, eid, True, "AV")
                    if not ok:
                        out.append(ev(name, "AVB", iid, eid, c, y, True, "excluded", rs, gate=g5, variant=var)); continue
                    if c == "row4" or (c == "row5" and fires):
                        lab, st = AU.s2_event(recs[c], "AVB", eid)
                        rsn = "gate open, no stage-2 call" if c == "row5" and st == "no_stage2" else MISS_ST.get(st, "no direct output")
                    else:
                        lab, st = (ds["r2"] if c == "row2" else ds["r1"])[iid]["AVB"].get(eid, ("", "missing"))
                        rsn = "judge prereq FAIL (gated)" if st == "gated" else MISS_ST.get(st, "no direct output")
                    ok = lab in ("yes", "no") and st == "ok"
                    out.append(ev(name, "AVB", iid, eid, c, y, True, "scored" if ok else "excluded", "" if ok else rsn, lab, g5, var))
    return out


# ------------------------------------------------------------------ metrics / tables
def met(q):
    q = q[q.status == "scored"]
    n = len(q); nf = int((q.y == "no").sum()); npass = n - nf
    tp = int(((q.pred == "no") & (q.y == "no")).sum()); fp = int(((q.pred == "no") & (q.y == "yes")).sum())
    fn, tn = nf - tp, npass - fp
    return dict(n=n, n_fail=nf, n_pass=npass, TP=tp, FN=fn, FP=fp, TN=tn, acc=(tp + tn) / n if n else None,
                prec=tp / (tp + fp) if tp + fp else None, rec=tp / nf if nf else None, FA=fp / npass if npass else None)


def f2(v):
    return "–" if v is None or pd.isna(v) else f"{v:.2f}".replace("0.", ".", 1) if v < 1 else f"{v:.2f}"


def cell(m):
    return "no scored unit" if not m["n"] else f"{f2(m['acc'])} / {f2(m['prec'])} / {f2(m['rec'])} / {f2(m['FA'])} ({m['n']}, {m['n_fail']})"


AXN = {"A": "A", "V": "V", "AVB": "AVB", "TCR": "TR", "TCC": "TC (per event)"}


def main_md(U, groups):
    o = ["| group | axis | media only | one call | always shown | gated |", "|---|---|---|---|---|---|"]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax)]
            if len(q):
                o.append(f"| {g} | {AXN[ax]} | " + " | ".join(cell(met(q[q.cond == c])) for c in CONDS) + " |")
    return "\n".join(o)


def ext(q):
    m = met(q)
    f = lambda p, r: 2 * p * r / (p + r) if p is not None and r is not None and p + r else None
    tn, fn = m["TN"], m["FN"]
    pp = tn / (tn + fn) if tn + fn else None; pr = tn / m["n_pass"] if m["n_pass"] else None
    ff, pf = f(m["prec"], m["rec"]), f(pp, pr)
    return dict(m, fail_f1=ff, pass_prec=pp, pass_rec=pr, pass_f1=pf,
                bal_acc=(m["rec"] + pr) / 2 if m["rec"] is not None and pr is not None else None,
                macro_f1=(ff + pf) / 2 if ff is not None and pf is not None else None)


def ext_md(U, groups, ax="V"):
    o = ["| group | condition | n (PASS / FAIL) | acc | FAIL prec | FAIL rec | FAIL F1 | PASS prec | PASS rec | PASS F1 | FA | balanced acc | macro-F1 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in groups:
        for c in CONDS:
            m = ext(U[(U.group == g) & (U.axis == ax) & (U.cond == c)])
            o.append(f"| {g} | {CNAME[c]} | {m['n']} ({m['n_pass']} / {m['n_fail']}) | " + " | ".join(
                f2(m[k]) for k in ("acc", "prec", "rec", "fail_f1", "pass_prec", "pass_rec", "pass_f1", "FA", "bal_acc", "macro_f1")) + " |")
    return "\n".join(o)


def counts_md(U, groups):
    o = ["| group | axis | units (events; TR: videos) | GT-eligible (PASS / FAIL) | " + " | ".join(f"{CNAME[c]} scored (PASS / FAIL)" for c in CONDS) + " |",
         "|---|---|---|---|" + "---|" * 4]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax)]
            if not len(q):
                continue
            q1 = q[q.cond == "row1"]; e = q1[q1.gt_elig.astype(bool)]
            s = []
            for c in CONDS:
                h = q[(q.cond == c) & (q.status == "scored")]
                s.append(f"{len(h)} ({int((h.y == 'yes').sum())} / {int((h.y == 'no').sum())})")
            o.append(f"| {g} | {AXN[ax]} | {len(q1)} | {len(e)} ({int((e.gt_y == 'yes').sum())} / {int((e.gt_y == 'no').sum())}) | " + " | ".join(s) + " |")
    return "\n".join(o)


def excl_md(U, groups):
    o = ["| group | axis | condition | exclusion reasons (count) |", "|---|---|---|---|"]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            for c in CONDS:
                q = U[(U.group == g) & (U.axis == ax) & (U.cond == c) & (U.status == "excluded")]
                if len(q):
                    o.append(f"| {g} | {AXN[ax]} | {CNAME[c]} | " + "; ".join(f"{k}{' [missing output]' if k in MISSING else ''} {v}"
                                                                          for k, v in q.reason.value_counts().items()) + " |")
    return "\n".join(o)


def conf_md(U, groups):
    o = ["| group | axis | condition | TP | FN | FP | TN |", "|---|---|---|---|---|---|---|"]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            for c in CONDS:
                q = U[(U.group == g) & (U.axis == ax) & (U.cond == c)]
                if len(q):
                    m = met(q)
                    o.append(f"| {g} | {AXN[ax]} | {CNAME[c]} | {m['TP']} | {m['FN']} | {m['FP']} | {m['TN']} |")
    return "\n".join(o)


def kind(r):
    if r.axis == "A":
        return "anchor mute (A)" if r.variant == "mute_anchor" else "originals, A (anchor-mute windows)"
    if r.axis == "V":
        return {"hand_swap": "hand swap (V)", "noun_swap": "noun swap (V)"}.get(r.variant, "originals, V")
    if r.axis == "AVB":
        return "early shift (AVB)" if "_AVBearly" in r.item else ("late shift (AVB)" if "_AVBlate" in r.item else "originals, AVB (shifted windows)")
    if r.axis == "TCR":
        return "order swap (TR)" if r.y == "no" else "originals, TR"
    return "count+1 event (TC)" if r.y == "no" else "PASS events (TC)"


ORDER = ["anchor mute (A)", "hand swap (V)", "noun swap (V)", "early shift (AVB)", "late shift (AVB)", "order swap (TR)", "count+1 event (TC)",
         "originals, A (anchor-mute windows)", "originals, V", "originals, AVB (shifted windows)", "originals, TR", "PASS events (TC)"]


def perturb_md(U):
    p = U[(U.group == "P03-P09") & (U.status == "scored")].copy()
    p["k"] = [kind(r) for r in p.itertuples()]
    o = ["| row type | media only | one call | always shown | gated |", "|---|---|---|---|---|"]
    for k in ORDER:
        q = p[p.k == k]
        o.append(f"| {k} | " + " | ".join((lambda h: f"{f2((h.pred == 'no').mean())} ({len(h)})" if len(h) else "no scored unit")(q[q.cond == c])
                                          for c in CONDS) + " |")
    return "\n".join(o)


def gate_md(U, groups):
    """gate admission (share of scored gated units whose gate opened; among GT PASS and GT FAIL) next to the final judge FA."""
    o = ["| group | axis | gated units scored | gate open: all | gate open: GT PASS | gate open: GT FAIL | final FA, media only | final FA, gated | FA among GT-PASS units with open gate |",
         "|---|---|---|---|---|---|---|---|---|"]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax) & (U.cond == "row5") & (U.status == "scored")]
            if not len(q):
                continue
            op = q.gate_open.fillna(False).astype(bool)
            pa, fa = q[q.y == "yes"], q[q.y == "no"]
            r = lambda a, b: f"{a} / {b} = {f2(a / b) if b else '–'}"
            m1 = met(U[(U.group == g) & (U.axis == ax) & (U.cond == "row1")]); m5 = met(q)
            po = pa[op[pa.index]]
            o.append(f"| {g} | {AXN[ax]} | {len(q)} | {r(int(op.sum()), len(q))} | {r(int(op[pa.index].sum()), len(pa))} | "
                     f"{r(int(op[fa.index].sum()), len(fa))} | {f2(m1['FA'])} | {f2(m5['FA'])} | "
                     f"{r(int((po.pred == 'no').sum()), len(po)) if len(po) else '–'} |")
    return "\n".join(o)


def revisions(U, groups):
    """always shown / gated vs media only on the same valid paired units (A / V / AVB / TC: the same event; TR: the same video),
    scored in both conditions."""
    out = []
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax)]
            if not len(q):
                continue
            b = q[q.cond == "row1"].set_index("unit")
            for c in ("row4", "row5"):
                x = q[q.cond == c].set_index("unit")
                s1 = b[b.status == "scored"]
                d = collections.Counter()
                for u, r in s1.iterrows():
                    if u not in x.index:
                        d["missing output"] += 1; continue
                    rx = x.loc[u]
                    if rx.status != "scored":
                        d["missing output" if rx.reason in MISSING else f"excluded: {rx.reason}"] += 1; continue
                    w0, w1 = r.pred != r.y, rx.pred != rx.y
                    d[{(True, False): "W->R", (False, True): "R->W", (True, True): "W->W", (False, False): "R->R"}[(w0, w1)]] += 1
                    if c == "row5" and rx.gate_open is not None and not pd.isna(rx.gate_open) and not bool(rx.gate_open):
                        d["closed gate (unchanged)"] += 1
                    if r.pred != rx.pred:
                        d["label changed"] += 1
                pw = d["W->R"] + d["W->W"]; pr = d["R->W"] + d["R->R"]; n = pw + pr
                out.append(dict(group=g, axis=AXN[ax], cond=CNAME[c], paired=n, **{k: d[k] for k in ("W->R", "R->W", "W->W", "R->R")},
                                closed_gate_unchanged=d["closed gate (unchanged)"] if c == "row5" else None, labels_changed=d["label changed"],
                                correction_rate=d["W->R"] / pw if pw else None, corruption_rate=d["R->W"] / pr if pr else None,
                                net_acc_change=(d["W->R"] - d["R->W"]) / n if n else None, missing_output=d["missing output"],
                                other_excluded="; ".join(f"{k[10:]} {v}" for k, v in d.items() if k.startswith("excluded: "))))
    return pd.DataFrame(out)


def rev_md(R):
    o = ["| group | axis | condition | paired units | W→R | R→W | W→W | R→R | closed gate (unchanged, inside R→R / W→W) | correction rate (W→R / initially wrong) | corruption rate (R→W / initially correct) | net acc change | missing output in this condition (unit scored in media only) |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in R.itertuples():
        o.append(f"| {r.group} | {r.axis} | {r.cond} | {r.paired} | {getattr(r, '_5')} | {getattr(r, '_6')} | {getattr(r, '_7')} | {getattr(r, '_8')} | "
                 f"{'' if r.closed_gate_unchanged is None or pd.isna(r.closed_gate_unchanged) else int(r.closed_gate_unchanged)} | "
                 f"{f2(r.correction_rate)} | {f2(r.corruption_rate)} | "
                 f"{'–' if r.net_acc_change is None or pd.isna(r.net_acc_change) else f'{r.net_acc_change:+.3f}'} | {r.missing_output} |")
    return "\n".join(o)


# ------------------------------------------------------------------ sensitivity (gate cutoffs 1 / 5 / 10 %, P03-P09)
def sens(U):
    """gate-cutoff sensitivity, per event (AVB: P03-P09 audio events; A: anchor-mute events). The cutoff only decides whether the gate
    opens (adm1 / adm5 / adm10 of sens_1105/rows_scored.csv, per GT row); an open gate uses the existing always-shown call (HG4 for AVB,
    HMB4 for A; sens_1105 made no new call), a closed gate keeps the media-only event label."""
    S = pd.read_csv(O.OUT / "sens_1105/rows_scored.csv")
    S["item"] = S.uid.str.split("|").str[1]
    out, chk = [], {}
    for ax, setn, s2 in (("A", "hm_ma39", "HMB4"), ("AVB", "hm_p3p9", "HG4")):
        b = U[(U.group == "P03-P09") & (U.axis == ax) & (U.cond == "row1")]
        adm = S[S.axis == ax].set_index("item")
        recs = {i: AU.stage2_rec(s2, f"{setn}|{i}|{ax}") for i in b["item"].unique()}
        g5 = U[(U.group == "P03-P09") & (U.axis == ax) & (U.cond == "row5")].set_index("unit")
        for tag, col in (("media only", None), ("1%", "adm1"), ("5%", "adm5"), ("10%", "adm10")):
            rows = []
            for r in b.itertuples():
                rs = r.reason if isinstance(r.reason, str) else ""
                if r.status != "scored" and rs not in MISSING:
                    continue                                   # judge / GT prerequisite exclusion: not a unit at any cutoff
                op = bool(adm[col].get(r.item, False)) if col else False
                if op:
                    lab, st = AU.s2_event(recs[r.item], ax, r.event)
                    ok = lab in ("yes", "no") and st == "ok"
                else:
                    lab, ok = r.pred, r.status == "scored"
                rows.append(dict(y=r.gt_y, pred=lab if ok else "", status="scored" if ok else "excluded", open=op))
            h = pd.DataFrame(rows); m = met(h); hs = h[h.status == "scored"]; pa = hs[hs.y == "yes"]; fa = hs[hs.y == "no"]
            if tag == "5%":
                chk[ax] = dict(events=len(hs), equal_to_gated_column=bool(m["n"] == met(g5)["n"] and m["FA"] == met(g5)["FA"] and m["acc"] == met(g5)["acc"]))
            out.append(dict(axis=ax, cutoff=tag, n=m["n"], n_fail=m["n_fail"], acc=m["acc"], prec=m["prec"], rec=m["rec"], FA=m["FA"],
                            missing=int((h.status != "scored").sum()),
                            gate_open_all=f"{int(hs.open.sum())} / {len(hs)}" if col else "–",
                            gate_open_pass=f"{int(pa.open.sum())} / {len(pa)} = {f2(pa.open.mean())}" if col else "–",
                            gate_open_fail=f"{int(fa.open.sum())} / {len(fa)}" if col else "–"))
    return pd.DataFrame(out), chk


def sens_md(T):
    o = ["| axis | cutoff | gate open (events) | gate open on GT-PASS events (admission rate) | gate open on GT-FAIL events | gated: acc / prec / rec / final FA (n events, n FAIL) | missing output |",
         "|---|---|---|---|---|---|---|"]
    for r in T.itertuples():
        o.append(f"| {'A, anchor mute' if r.axis == 'A' else r.axis} | {r.cutoff} | {r.gate_open_all} | {r.gate_open_pass} | {r.gate_open_fail} | "
                 f"{f2(r.acc)} / {f2(r.prec)} / {f2(r.rec)} / {f2(r.FA)} ({r.n}, {r.n_fail}) | {r.missing} |")
    return "\n".join(o)


def recon_md(U, groups):
    """GT accounting in one unit (events for A / V / AVB / TC, videos for TR): every unit has exactly one GT status."""
    o = ["| group | axis | units | not applicable | GT label missing (tie / no majority) | GT prerequisite FAIL | GT prerequisite undetermined | other | GT-eligible | check |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax) & (U.cond == "row1")]
            if not len(q):
                continue
            ne = q[~q.gt_elig.astype(bool)]
            na = int(ne.reason.str.startswith("not applicable").sum()); gm = int(ne.reason.str.startswith("GT label missing").sum())
            pf = int((ne.reason == "GT prereq FAIL").sum()); pu = int(ne.reason.str.startswith("GT prereq undetermined").sum())
            ot = len(ne) - na - gm - pf - pu; el = int(q.gt_elig.astype(bool).sum())
            o.append(f"| {g} | {AXN[ax]} | {len(q)} | {na} | {gm} | {pf} | {pu} | {ot} | {el} | {'ok' if na + gm + pf + pu + ot + el == len(q) else 'MISMATCH'} |")
    return "\n".join(o)


# ------------------------------------------------------------------ old vs new
def old_new(U, groups):
    Dold = pd.read_csv(O.OUT / "main_table_1105_rows.csv")
    P = pd.read_csv(O.OUT / "section6_1106_rowlevel/units_all.csv", low_memory=False)
    gm = {"LTX (220 + 149 + 2k_25)": "LTX", "MOVA (220)": "MOVA"}
    out = []
    for g in groups:
        for ax in ("A", "V", "AVB", "TCR", "TCC"):
            q = U[(U.group == g) & (U.axis == ax)]
            if not len(q):
                continue
            o = Dold[(Dold.group == gm.get(g, g)) & (Dold.axis == ax)]
            for c in CONDS:
                h = o[o[c].isin(["yes", "no"])]
                mo = met(h.assign(status="scored", pred=h[c])) if len(h) else dict(n=0)
                mn = met(q[q.cond == c])
                mp = met(P[(P.group == g) & (P.axis == ax) & (P.cond == c)])
                out.append(dict(group=g, axis=AXN[ax], cond=CNAME[c], old=cell(mo) if mo["n"] else "–", prev=cell(mp), new=cell(mn)))
    return pd.DataFrame(out)


def main():
    OUT.mkdir(exist_ok=True)
    D = AU.datasets()
    A = pd.read_csv(AU.OUT / "units.csv")
    A = A[A.axis.isin(["TCR", "TCC"])].copy()                     # TR per video, TC per counted event; A / V / AVB rebuilt per event
    A["variant"] = ""; A["event"] = A.unit.str.split("|").str[2].fillna("video")
    A["gate_open"] = pd.Series([None] * len(A), dtype=object)
    for name, ds in D.items():
        A.loc[(A.dataset == name) & (A.cond == "row5") & A.axis.isin(["TCR", "TCC"]), "gate_open"] = False
    U = pd.concat([A, pd.DataFrame(av_events(D) + ma_events() + avb_events(D))], ignore_index=True)
    U["group"] = U.dataset
    L = U[U.dataset.isin(["220 LTX", "149 LTX", "2k_25 LTX"])].assign(group="LTX (220 + 149 + 2k_25)")
    Mo = U[U.dataset == "220 MOVA"].assign(group="MOVA (220)")
    U = pd.concat([U, L, Mo], ignore_index=True)
    U.to_csv(OUT / "units_all.csv", index=False)
    MAIN = ["P03-P09", "LTX (220 + 149 + 2k_25)", "MOVA (220)"]
    SETS = ["220 LTX", "149 LTX", "2k_25 LTX", "220 MOVA"]
    R = revisions(U, MAIN + SETS); R.to_csv(OUT / "revisions.csv", index=False)
    ST, chk = sens(U); ST.to_csv(OUT / "sensitivity.csv", index=False)
    ON = old_new(U, MAIN + SETS); ON.to_csv(OUT / "old_vs_new.csv", index=False)
    # duplicate / overlap checks
    L1 = U[(U.group == "LTX (220 + 149 + 2k_25)") & (U.cond == "row1")]
    dup = int(U[(U.cond == "row1") & (U.group == U.dataset)].duplicated(["dataset", "axis", "unit"]).sum())
    over = {f"{a} & {b}": len(set(L1[L1.dataset == a]["item"]) & set(L1[L1.dataset == b]["item"]))
            for a, b in (("220 LTX", "149 LTX"), ("220 LTX", "2k_25 LTX"), ("149 LTX", "2k_25 LTX"))}
    v2k = U[(U.dataset == "2k_25 LTX") & (U.axis == "V") & (U.cond == "row1") & (U.group == U.dataset)]
    dup_v2k = int(v2k.duplicated(["item", "event"]).sum()); n_v2k = len(v2k)
    gtsame = {f"{g}|{ax}": len({frozenset(q[(q.cond == c) & q.gt_elig.astype(bool)].unit) for c in CONDS}) == 1
              for (g, ax), q in U.groupby(["group", "axis"])}
    pd.Series(dict(dup_units_ltx=dup, **over, gt_eligible_identical_all=all(gtsame.values()), **{f"sens_{k}": v for k, v in chk.items()})).to_csv(OUT / "checks.csv")
    T = dict(main=main_md(U, MAIN), sets=main_md(U, SETS), vext=ext_md(U, ["LTX (220 + 149 + 2k_25)", "220 LTX", "149 LTX", "2k_25 LTX", "P03-P09", "MOVA (220)"]),
             counts=counts_md(U, MAIN + SETS), excl=excl_md(U, MAIN + SETS), conf=conf_md(U, MAIN + SETS),
             perturb=perturb_md(U), gate=gate_md(U, MAIN + SETS), rev=rev_md(R), sens=sens_md(ST),
             oldnew="\n".join(["| group | axis | condition | old (main_table_1105, GT rows) | previous report (11/06, GT rows) | new (Section 5 units) |",
                                "|---|---|---|---|---|---|"] +
                              [f"| {r.group} | {r.axis} | {r.cond} | {r.old} | {r.prev} | {r.new} |" for r in ON.itertuples()]),
             recon=recon_md(U, MAIN + SETS),
             checks=dict(dup=dup, dup_v2k=dup_v2k, n_v2k=n_v2k, over=over, gtsame=all(gtsame.values()), sens=chk))
    json.dump(T, open(OUT / "tables.json", "w"), indent=1, default=str)
    for k, v in T.items():
        print(f"===== {k}\n{v if isinstance(v, str) else json.dumps(v, default=str)}")


if __name__ == "__main__":
    main()
