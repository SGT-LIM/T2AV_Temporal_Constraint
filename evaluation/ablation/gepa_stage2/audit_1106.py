#!/usr/bin/env python3
"""Audit of the conditional evaluation rules (user 11/06). No calls; existing caches and result files are only read.
Rules audited (user):
  R1 only applicable units;  R2 an upper axis is scored only where its prerequisites are PASS in BOTH the GT and the judge's
  eligibility source;  R3 judge-gated / inherited downstream FAILs are excluded, never filled in as FAIL;  R5 prerequisite exclusion,
  API error, parse error / missing output and N/A are separate reasons.
Prerequisites (judge code, agentic_orchestrator.py:12-14, 49-57, 269-290; axis_binding.py:48-51):
  AVB per event: A = yes and V = yes.  TR per video: every A, V, AVB of the video = yes.  TC per event: audio-bearing events
  A, V, AVB = yes; silent events V = yes (A / AVB not applicable, not FAIL).  The same rules are applied to the GT.
Units: AVB per row (item; label = no if any kept event is no, as the tables), TR per video, TC per event (generated sets as in the
main table; P03-P09 rebuilt per event from the count_off override).
Eligibility source: media only = its own run; one call = its own run; always shown / gated = stage 1 (= the media-only run), as the
pipeline does. The output of a condition must be a direct judgment: a label written by the model for that unit (not a gating message,
not a "returned no ... entry; treated as failure" fill, not an error row); always shown / gated without a stage-2 call -> no direct output.
  python gepa_stage2/audit_1106.py   -> runs/obsval_1028/audit_1106/{accounting.csv, recount.csv, units.csv, revisions.csv}
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import collections, glob, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import obs_judge_1028 as O
import hd_stage2_1101 as H
import hd_rows_score_1101 as HR
import gen_rows_score_1030 as GR
import gen_stage2_1030 as G
import gen2k25_stage2_1104 as K
import gen_row5_prereg_1102 as GP
import rep_scoring as RS

OUT = O.OUT / "audit_1106"; OUT.mkdir(exist_ok=True)
import functools
_FP = functools.lru_cache(None)(GP.fire_prereg)
CALLS = O.OUT / "calls" / "gen_tool_text"
FILL = re.compile(r"treated as failure", re.I)
REL500 = {x["item_id"]: x for x in json.load(open((_tp.WORKSPACE + "/new_prompts/generated/relative_500_v5_fixed.json")))}
P149 = {x["item_id"]: x for x in json.load(open(GR.G149 / "prompts_gen149.json"))}
P2K = {x["item_id"]: x for x in json.load(open(K.D / "prompts_gen2k25.json"))}


# ------------------------------------------------------------------ run outputs
def load_run(files):
    fs = [f for f in files if "per_event" not in f]
    if not fs:
        return {}
    d = pd.concat(pd.read_csv(f) for f in fs).drop_duplicates("item_id", keep="last")
    out = {}
    for r in d.to_dict("records"):
        err = str(r.get("overall_reason", "")).startswith("ERROR")
        ent = dict(error=err)
        for ax, col in (("A", "audio_event_correctness"), ("V", "visual_event_correctness"), ("AVB", "audio_visual_binding"),
                        ("TCC", "temporal_count_satisfaction")):
            m = {}
            try:
                for e in json.loads(r.get(col + "_per_event") or "[]"):
                    rs = str(e.get("reason", ""))
                    if ax == "TCC":
                        oc, rc = e.get("observed_count"), e.get("required_count")
                        st = "gated" if RS.SKIP_RE.search(rs) else ("fill" if FILL.search(rs) else "ok")
                        try:
                            lab = "yes" if int(oc) == int(rc) else "no"
                        except (TypeError, ValueError):
                            lab, st = "", ("gated" if st == "gated" else "fill")
                    else:
                        lab = str(e.get("label", "")).lower()
                        st = "gated" if RS.SKIP_RE.search(rs) else ("fill" if FILL.search(rs) else "ok")
                    m[e["event_id"]] = (lab, st)
            except Exception:
                pass
            ent[ax] = m
        tr = str(r.get("temporal_relation_satisfaction", "")).lower(); trr = str(r.get("temporal_relation_satisfaction_reason", ""))
        ent["TCR"] = (tr, "gated" if RS.SKIP_RE.search(trr) else ("fill" if FILL.search(trr) or tr not in ("yes", "no") else "ok"))
        out[r["item_id"]] = ent
    return out


def stage2_rec(set_name, uid):
    f = CALLS / f"{set_name}__{uid}.json"
    if not f.exists():
        return None
    rec = json.load(open(f))
    return rec if rec.get("status") == "ok" else None


def s2_event(rec, axis, eid):
    if rec is None:
        return "", "no_stage2"
    p = rec.get("parsed") or {}
    if axis == "TCR":
        l = str(p.get("label", "")).lower()
        return (l, "ok") if l in ("yes", "no") else ("", "fill")
    req = {x.get("event_id"): x.get("required_count") for x in rec.get("anchor", [])}
    for e in p.get("per_event", []):
        if e.get("event_id") != eid:
            continue
        if axis == "TCC":
            try:
                return ("yes" if int(e.get("observed_count")) == int(req.get(eid)) else "no"), "ok"
            except (TypeError, ValueError):
                return "", "fill"
        l = str(e.get("label", "")).lower()
        return (l, "ok") if l in ("yes", "no") else ("", "fill")
    return "", "no_stage2_entry"


# ------------------------------------------------------------------ datasets
def events_of(item):
    """[(event_id, has_audio, has_binding)] in scoring order (audio-bearing = speech / sounding)."""
    out = []
    for k, e in enumerate(item["events"]):
        aud = e.get("modality") in ("speech", "sounding_action")
        out.append((f"event_{k + 1}", aud, aud))
    return out


def datasets():
    D = {}
    # ---- generated
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s}.jsonl")]
    allm = [json.loads(l) for l in open(HERE / "manifests_v3/all.jsonl")]
    gem = pd.read_csv((_tp.DATA + "/gt_annotations/min3_gt/gt_event_majority.csv"))
    tcpe = pd.read_csv(O.OUT / "tc_per_event_rows_1105.csv")
    for src, model, grp, pre, setn in (("ltx", "LTX_2p3", "220 LTX", "LTX_2p3", "g220ltx"), ("mova", "MOVA", "220 MOVA", "MOVA", "g220mova")):
        g = gem[gem.model == model]
        gtA, gtV, gtB = {}, {}, {}
        for r in g.itertuples():
            iid = r.video_id.replace(f"__{model}", "")
            it = REL500.get(iid)
            if not it:
                continue
            idx = {e["id"]: f"event_{k + 1}" for k, e in enumerate(it["events"])}
            eid = idx.get(r.prompt_event)
            if not eid:
                continue
            for dct, c in ((gtA, "A"), (gtV, "V"), (gtB, "AVB")):
                v = str(getattr(r, c)).upper()
                dct[(iid, eid)] = {"PASS": "yes", "FAIL": "no"}.get(v, "tie" if v == "TIE" else "")
        rows = [m for m in man if m["source"] == src]
        D[grp] = dict(items=REL500, rows=rows, gtA=gtA, gtV=gtV, gtB=gtB, tc=tcpe[tcpe.group == grp],
                      r1=load_run(sorted(glob.glob(str(GR.R / GR.RUNS["row1"] / f"{pre}_shard*.csv")))),
                      r2=load_run(sorted(glob.glob(str(GR.R / GR.RUNS["row2"] / f"{pre}_shard*.csv")))),
                      s2=("GA4", setn), s2av=("G4", setn), fires=lambda iid, s=setn: _FP().get((s, iid), False), hd=False)
    for grp, items, gtf, pre, setn, r1f, r2f, s2, s2av in (
            ("149 LTX", P149, GR.G149 / "gt_gen149.jsonl", "gen149", "g149", None, None, "GA4", "G4"),
            ("2k_25 LTX", P2K, K.D / "gt_gen2k25.jsonl", None, "g2k25", K.R1, K.R2, "K4", "K4")):
        gt = [json.loads(l) for l in open(gtf)]
        gtA, gtV, gtB = {}, {}, {}
        for m in gt:
            for ax, dct in (("A", gtA), ("V", gtV), ("AVB", gtB)):
                if m["axis"] == ax:
                    for e, v in m["gt"].items():
                        dct[(m["item_id"], e)] = v
        if pre:
            r1 = load_run(sorted(glob.glob(str(GR.R / GR.RUNS["row1"] / f"{pre}_shard*.csv"))))
            r2 = load_run(sorted(glob.glob(str(GR.R / GR.RUNS["row2"] / f"{pre}_shard*.csv"))))
            fires = lambda iid, s=setn: _FP().get((s, iid), False)
        else:
            r1 = load_run(sorted(glob.glob(str(r1f / "gen2k25_shard*.csv"))))
            r2 = load_run(sorted(glob.glob(str(r2f / "gen2k25_shard*.csv"))))
            fires = K.fires
        rows = [dict(m, source=setn) for m in gt]
        D[grp] = dict(items=items, rows=rows, gtA=gtA, gtV=gtV, gtB=gtB, tc=tcpe[tcpe.group == grp], r1=r1, r2=r2,
                      s2=(s2, setn), s2av=(s2av, setn), fires=fires, hd=False)
    # ---- HD-EPIC P03-P09 (GT prerequisites hold by construction: the perturbation breaks only the axis it targets)
    P = {x["item_id"]: x for x in json.load(open(H.HO / "prompts_hdepic_p3p9.json"))}
    rows = [r for r in H.gt_rows() if r["source"] == "hm_p3p9" and r["axis"] == "AVB"]
    rows += [dict(source="hm_p3p9", item_id=r["item_id"], axis=r["axis"], gt=r["gt"], variant=r["variant"])
             for r in HR.gt_all() if r["set"] == "p3p9" and r["axis"] in ("TCR", "TCC")]
    it = {x["item_id"]: x for x in json.load(open(H.HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))}
    D["P03-P09"] = dict(items=P, rows=rows, gtA=None, gtV=None, gtB=None, tc=None, hdit=it,
                        r1=load_run(sorted(glob.glob(str(O.RES / "hdepic_main_row1_anchor_g36_1101" / "p3p9_shard*.csv")))),
                        r2=load_run(sorted(glob.glob(str(O.RES / "hdepic_main_row2_onecall_sync_g36_1101" / "p3p9_shard*.csv")))),
                        s2=("HA4", "hm_p3p9"), s2av=("HG4", "hm_p3p9"), fires=H.fires, hd=True)
    return D


# ------------------------------------------------------------------ unit building
def gt_ok(ds, iid, eid, aud, need):
    """GT prerequisite of an event: need in {'AV', 'AVB'} -> (ok, reason)."""
    if ds["hd"]:
        return True, ""
    labs = []
    if aud:
        labs.append(ds["gtA"].get((iid, eid), ""))
    labs.append(ds["gtV"].get((iid, eid), ""))
    if need == "AVB" and aud:
        labs.append(ds["gtB"].get((iid, eid), ""))
    if any(l == "no" for l in labs):
        return False, "GT prereq FAIL"
    if any(l != "yes" for l in labs):
        return False, "GT prereq undetermined (tie / missing)"
    return True, ""


def judge_ok(run, iid, eid, aud, need):
    e = run.get(iid)
    if e is None:
        return False, "item missing from run"
    if e["error"]:
        return False, "API / run error"
    labs = []
    if aud:
        labs.append(e["A"].get(eid, ("", "missing")))
    labs.append(e["V"].get(eid, ("", "missing")))
    if need == "AVB" and aud:
        labs.append(e["AVB"].get(eid, ("", "missing")))
    if all(l == "yes" for l, _ in labs):
        return True, ""
    if any(st == "fill" for l, st in labs):
        return False, "judge prereq not output (fill)"
    return False, "judge prereq FAIL (gated)"


def units(ds_name, ds):
    """yield dict(unit, axis, events, y) for AVB rows, TR videos, TC events."""
    out = []
    for m in ds["rows"]:
        iid, ax = m["item_id"], m["axis"]
        if ax == "AVB":
            out.append(dict(uid=f"{iid}|AVB", item=iid, axis="AVB", gt=m["gt"]))
        elif ax == "TCR":
            out.append(dict(uid=f"{iid}|TCR", item=iid, axis="TCR", gt=m["gt"]))
        elif ax == "TCC" and ds["hd"]:
            x = ds["hdit"].get(iid, {})
            over = {f"event_{int(k) + 1}" for k in (x.get("count_override") or {})}
            for eid, aud, _ in events_of(ds["items"][iid]):
                y = "no" if eid in over else ("yes" if m["gt"].get("__item__") == "yes" or over else m["gt"].get("__item__"))
                out.append(dict(uid=f"{iid}|TCC|{eid}", item=iid, axis="TCC", gt={eid: y}))
    if ds["tc"] is not None:
        for r in ds["tc"].itertuples():
            parts = r.uid.split("|")
            out.append(dict(uid=f"{parts[1]}|TCC|{parts[3]}", item=parts[1], axis="TCC", gt={parts[3]: r.y}))
    return out


def gt_eligible(ds, u):
    """condition-independent: applicable and GT prerequisites PASS (TR: every event of the video; AVB / TC: at least one event)."""
    item = ds["items"].get(u["item"])
    if item is None:
        return False
    evs = {e: a for e, a, _ in events_of(item)}
    if u["axis"] == "TCR":
        if not ds["hd"] and item["temporal_constraint"].get("task_type") not in ("order", "sync"):
            return False
        return all(gt_ok(ds, u["item"], e, a, "AVB")[0] for e, a in evs.items())
    return any(y in ("yes", "no") and e in evs and not (u["axis"] == "AVB" and not evs[e])
               and gt_ok(ds, u["item"], e, evs[e], "AV" if u["axis"] == "AVB" else "AVB")[0] for e, y in u["gt"].items())


def gt_label(ds, u):
    """GT over the GT-eligible events of a unit ('' if none)."""
    item = ds["items"].get(u["item"])
    if item is None:
        return ""
    if u["axis"] == "TCR":
        return u["gt"].get("__item__", "") if gt_eligible(ds, u) else ""
    evs = {e: a for e, a, _ in events_of(item)}
    ys = [y for e, y in u["gt"].items() if y in ("yes", "no") and e in evs and not (u["axis"] == "AVB" and not evs[e])
          and gt_ok(ds, u["item"], e, evs[e], "AV" if u["axis"] == "AVB" else "AVB")[0]]
    return ("no" if "no" in ys else "yes") if ys else ""


def label_unit(ds, u, cond):
    """-> dict(status, reason, y, pred) under the audit rules for one condition."""
    iid, ax = u["item"], u["axis"]
    item = ds["items"].get(iid)
    if item is None:
        return dict(status="excluded", reason="no prompt item")
    evs = {e: (a, b) for e, a, b in events_of(item)}
    elig_run = ds["r2"] if cond == "row2" else ds["r1"]
    # always shown = the 11/05 all-four-tools call (GA4 / HA4 / K4); gated = the call the existing tables use when the gate fires
    # (G4 / HG4 / K4, gen_row5_prereg_1102.py:56-61, hd_stage2_1101.py:384-386)
    s2set, setn = ds["s2"] if cond == "row4" else ds["s2av"]
    rec = stage2_rec(s2set, f"{setn}|{iid}|{ax}") if cond in ("row4", "row5") else None
    use_s2 = cond == "row4" or (cond == "row5" and ax == "AVB" and ds["fires"](iid))
    if ax == "TCR":
        if (not ds["hd"]) and item["temporal_constraint"].get("task_type") not in ("order", "sync"):
            return dict(status="excluded", reason="not applicable (no relation)")
        if not ds["hd"]:
            for eid, (aud, _) in evs.items():
                ok, rs = gt_ok(ds, iid, eid, aud, "AVB")
                if not ok:
                    return dict(status="excluded", reason=rs)
        e = elig_run.get(iid)
        if e is None:
            return dict(status="excluded", reason="item missing from run")
        if e["error"]:
            return dict(status="excluded", reason="API / run error")
        if e["TCR"][1] == "gated":
            return dict(status="excluded", reason="judge prereq FAIL (gated)")
        # the one-call prompt lets the model write a TR "no" without a skip note when A / V / AVB failed (new_eval.py:1810-1816 only
        # rewrites a "yes"), so the judge prerequisite is checked on the labels, not on the reason text
        for eid, (aud, _) in evs.items():
            ok, rs = judge_ok(elig_run, iid, eid, aud, "AVB")
            if not ok:
                return dict(status="excluded", reason=rs if rs != "judge prereq FAIL (gated)" else "judge prereq FAIL (TR label not marked as skipped)")
        if use_s2:
            lab, st = s2_event(rec, "TCR", None)
        else:
            lab, st = e["TCR"]
        if lab not in ("yes", "no"):
            return dict(status="excluded", reason={"no_stage2": "no stage-2 call", "fill": "no direct output (fill / invalid)"}.get(st, "no direct output"))
        return dict(status="scored", reason="", y=u["gt"]["__item__"], pred=lab, events="video")
    kept_y, kept_p, kept_e, reasons = [], [], [], []
    for eid, y in u["gt"].items():
        if eid == "__item__" or y not in ("yes", "no") or eid not in evs:
            reasons.append("GT label missing"); continue
        aud = evs[eid][0]
        if ax == "AVB" and not aud:
            reasons.append("not applicable (silent)"); continue
        need = "AV" if ax == "AVB" else "AVB"
        ok, rs = gt_ok(ds, iid, eid, aud, need)
        if not ok:
            reasons.append(rs); continue
        ok, rs = judge_ok(elig_run, iid, eid, aud, need)
        if not ok:
            reasons.append(rs); continue
        if use_s2:
            lab, st = s2_event(rec, ax, eid)
            if lab not in ("yes", "no"):
                reasons.append({"no_stage2": "no stage-2 call", "no_stage2_entry": "no stage-2 entry", "fill": "no direct output (fill / invalid)"}[st]); continue
        else:
            out = (ds["r2"] if cond == "row2" else ds["r1"]).get(iid)
            lab, st = out[ax].get(eid, ("", "missing"))
            if st != "ok" or lab not in ("yes", "no"):
                reasons.append("no direct output (fill / invalid)" if st == "fill" else ("judge prereq FAIL (gated)" if st == "gated" else "no direct output")); continue
        kept_y.append(y); kept_p.append(lab); kept_e.append(eid)
    if not kept_y:
        return dict(status="excluded", reason=collections.Counter(reasons).most_common(1)[0][0] if reasons else "no events")
    return dict(status="scored", reason="", y="no" if "no" in kept_y else "yes", pred="no" if "no" in kept_p else "yes",
                events=";".join(kept_e))


def metrics(q):
    q = q[q.status == "scored"]
    if not len(q):
        return dict(n=0)
    tp = ((q.pred == "no") & (q.y == "no")).sum(); pf = (q.pred == "no").sum(); nf = (q.y == "no").sum(); np_ = (q.y == "yes").sum()
    return dict(n=len(q), n_fail=int(nf), acc=round(float((q.pred == q.y).mean()), 3), prec=round(tp / pf, 3) if pf else None,
                rec=round(tp / nf, 3) if nf else None, FA=round(float(((q.pred == "no") & (q.y == "yes")).sum() / np_), 3) if np_ else None)


def s2_av(ds, iid, ax, eid):
    """stage-2 per-event label of a prerequisite axis (A / V from G4 / HG4 / K4, AVB from the all-four call), '' if none."""
    st, setn = ds["s2av"] if ax in ("A", "V") else ds["s2"]
    lab, s = s2_event(stage2_rec(st, f"{setn}|{iid}|{ax}"), ax, eid)
    return lab if s == "ok" else ""


def revisions(D, U):
    """always shown (row4), per prerequisite event (AVB: audio events; TC: counted events; TR: every event of the video):
    stage-1 prerequisite vs the prerequisite after the stage-2 A / V / AVB revision. Eligibility in every existing table and in this
    audit = stage-1 labels. ds2 = the downstream stage-2 call has a direct label for that event (TR: for the video)."""
    out = []
    for name, ds in D.items():
        for u in units(name, ds):
            item = ds["items"].get(u["item"])
            e1 = ds["r1"].get(u["item"])
            if item is None or e1 is None or e1["error"]:
                continue
            evs = {e: a for e, a, _ in events_of(item)}
            eids = list(evs) if u["axis"] == "TCR" else [e for e in u["gt"] if e in evs]
            need = "AV" if u["axis"] == "AVB" else "AVB"
            s2set, setn = ds["s2"]
            rec = stage2_rec(s2set, f"{setn}|{u['item']}|{u['axis']}")
            for eid in eids:
                aud = evs[eid]
                if u["axis"] == "AVB" and not aud:
                    continue
                gok = gt_ok(ds, u["item"], eid, aud, need)[0]
                s1_ok, s2_ok, has = True, True, False
                for ax in (["A"] if aud else []) + ["V"] + (["AVB"] if need == "AVB" and aud else []):
                    l1 = e1[ax].get(eid, ("", ""))[0]
                    l2 = s2_av(ds, u["item"], ax, eid)
                    has |= bool(l2); s1_ok &= l1 == "yes"; s2_ok &= (l2 or l1) == "yes"
                case = "no stage-2 prerequisite label" if not has else \
                    {(True, True): "PASS kept", (False, False): "FAIL kept", (False, True): "FAIL -> PASS", (True, False): "PASS -> FAIL"}[(s1_ok, s2_ok)]
                ds2 = s2_event(rec, u["axis"], None if u["axis"] == "TCR" else eid)[1] == "ok"
                out.append(dict(dataset=name, axis=u["axis"], unit=u["uid"], event=eid, gt_prereq_ok=gok, case=case,
                                handling="scored with stage-1 eligibility" if s1_ok else "excluded (stage-1 gated)", downstream_s2_label=ds2))
    R = pd.DataFrame(out)
    R.to_csv(OUT / "revisions_events.csv", index=False)
    T = R.groupby(["dataset", "axis", "case", "gt_prereq_ok", "downstream_s2_label"]).size().rename("n").reset_index()
    T.to_csv(OUT / "revisions.csv", index=False)
    return T


def fills(D):
    """per-event 'treated as failure' fills in the stage-1 / one-call outputs; the existing row_label (rep_scoring.py:64-95) reads them as FAIL."""
    out = []
    for name, ds in D.items():
        for cond, run in (("row1", ds["r1"]), ("row2", ds["r2"])):
            c = collections.Counter()
            for iid, e in run.items():
                c["items"] += 1; c["API / run error"] += e["error"]
                for ax in ("A", "V", "AVB", "TCC"):
                    for lab, st in e[ax].values():
                        c[f"{ax} {st}"] += 1
                c[f"TCR {e['TCR'][1]}"] += 1
            out.append(dict(dataset=name, run=cond, **c))
    F = pd.DataFrame(out).fillna(0)
    F.to_csv(OUT / "fills.csv", index=False)
    return F


def compare_old(A, P):
    """existing main_table_1105_rows.csv cells next to the audit recount (same metric code as the existing table)."""
    D = pd.read_csv(O.OUT / "main_table_1105_rows.csv")
    new = pd.concat([A[["dataset", "axis", "cond", "n", "n_fail", "acc", "prec", "rec", "FA"]], P])
    gmap = {"LTX (pooled)": "LTX", "220 MOVA": "220 MOVA"}
    out = []
    for r in new.itertuples():
        q = D[(D.group == gmap.get(r.dataset, r.dataset)) & (D.axis == r.axis)]
        h = q[q[r.cond].isin(["yes", "no"])]
        tp = ((h[r.cond] == "no") & (h.y == "no")).sum(); pf = (h[r.cond] == "no").sum(); nf = (h.y == "no").sum(); np_ = (h.y == "yes").sum()
        out.append(dict(dataset=r.dataset, axis=r.axis, cond=r.cond, old_n=len(h), old_n_fail=int(nf),
                        old_acc=round(float((h[r.cond] == h.y).mean()), 3) if len(h) else None, old_prec=round(tp / pf, 3) if pf else None,
                        old_rec=round(tp / nf, 3) if nf else None, old_FA=round(float(((h[r.cond] == "no") & (h.y == "yes")).sum() / np_), 3) if np_ else None,
                        new_n=r.n, new_n_fail=r.n_fail, new_acc=r.acc, new_prec=r.prec, new_rec=r.rec, new_FA=r.FA))
    C = pd.DataFrame(out)
    C.to_csv(OUT / "compare_old_new.csv", index=False)
    return C


def main():
    D = datasets()
    rows = []
    for name, ds in D.items():
        for u in units(name, ds):
            ge = gt_eligible(ds, u); gy = gt_label(ds, u)
            for cond in ("row1", "row2", "row4", "row5"):
                r = label_unit(ds, u, cond)
                rows.append(dict(dataset=name, axis=u["axis"], unit=u["uid"], item=u["item"], cond=cond, gt_elig=ge, gt_y=gy, **r))
    U = pd.DataFrame(rows)
    U.to_csv(OUT / "units.csv", index=False)
    acc = []
    for (dsn, ax, cond), q in U.groupby(["dataset", "axis", "cond"]):
        c = collections.Counter(q[q.status == "excluded"].reason)
        gtok = q[q.gt_elig]
        acc.append(dict(dataset=dsn, axis=ax, cond=cond, units=len(q),
                        applicable=int((~q.reason.isin(["not applicable (no relation)", "not applicable (silent)", "no prompt item"])).sum()),
                        gt_eligible=len(gtok), scored=int((q.status == "scored").sum()),
                        gt_pass=int(((q.status == "scored") & (q.y == "yes")).sum()), gt_fail=int(((q.status == "scored") & (q.y == "no")).sum()),
                        **{f"excl: {k}": v for k, v in sorted(c.items())}, **metrics(q)))
    A = pd.DataFrame(acc).fillna(0)
    A.to_csv(OUT / "accounting.csv", index=False)
    # pooled LTX
    L = U[U.dataset.isin(["220 LTX", "149 LTX", "2k_25 LTX"])]
    pooled = [dict(dataset="LTX (pooled)", axis=ax, cond=cond, **metrics(q)) for (ax, cond), q in L.groupby(["axis", "cond"])]
    pd.DataFrame(pooled).to_csv(OUT / "recount_pooled_ltx.csv", index=False)
    assert not len(U[(U.status == "scored") & ~U.gt_elig]), "scored unit outside the GT-eligible set"
    compare_old(A, pd.DataFrame(pooled))
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
    print(A.to_string(index=False))
    print(pd.DataFrame(pooled).to_string(index=False))
    print(revisions(D, U).to_string(index=False))
    print(fills(D).to_string(index=False))


if __name__ == "__main__":
    main()
