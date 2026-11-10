#!/usr/bin/env python3
"""Final evaluation coverage (11/08): remaining missing / failed stage-2 outputs on the existing datasets, and both gated conditions on
MOVA390 (prolific_mova_390 @ 650fe5ae). Writes only to runs/obsval_1028/final_cov_1108/. No original output, cache, GT or prompt file is
modified (rows.jsonl and calls/gen_tool_text are read only; new outputs go to final_cov_1108/calls/).
Corrected scorer and anchor builder everywhere: avb_skipfix_1108.patch (audit_1106.load_run) and avb_anchorfix_1108.patch
(run_two_stage.stage1_lookup), both in-process.
Frozen combined configuration (p12_calib_1108/frozen_p12_config.json, unchanged): A speech = original paper Whisper gate (row 5 label);
A sound FLAM max < .3724 (initial PASS) / >= .9897 (initial FAIL); V caption check contradicts / describes; AVB |offset| >= 1.2 s and
conf >= .1278 (initial PASS) / |offset| <= 0.2 s and conf >= .3221 (initial FAIL); TC / TR closed. Nothing is selected on MOVA / LTX / P03-P09.
Original paper gate (MOVA390, as the 2k_25 batch, gen2k25_stage2_1104 / section6_1106): A = Whisper-word / FLAM-below-T_flam text gate
(gated text == always-shown text -> M4 call; differs -> new M5 call); V = caption check contradicts -> M4 call; AVB = pre-registered
Synchformer rule (|offset| >= 1.8 s, p >= .25, strongest reading) -> M4 call; TC / TR closed.
MOVA390 inputs (nothing regenerated): row 1 / row 2 runs, M4 always-shown calls, Whisper + FLAM records, AVoCaDO captions, Synchformer
per-event readings (mova390_pipeline_1108.py). New: caption checks (from the existing captions), M5 calls, combined-gate calls, M4 AVB calls
whose anchor changes under the anchor fix (used only for events the original M4 call lacks, as avb_anchorfix_1108 did for the other sets).
Calls: gemini-3.6-flash, thinking high, temperature 0, seed 42, OBS_RULES md5 556c2b2e...; deduplicated by prompt md5; an existing output is
reused only if status ok, same prompt md5 / rules / model / thinking and it has an entry for every needed event. Up to 3 attempts per prompt
in this run; an output that is empty, unparsable or lacks the needed events after 3 attempts is recorded as unresolved (never filled).
Any billing / spending-cap error stops the run (HOLD file); keys are never rotated.
  python gepa_stage2/final_cov_1108.py audit | plan | run | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, copy, glob, hashlib, json, os, re, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "final_cov_1108"; CALLS = OUT / "calls"
DSN, SRC = "MOVA390", "m390"
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA (old 220)", "P03-P09": "P03-P09", DSN: "MOVA390"}
MODEL, MAXTRY = "gemini-3.6-flash", 3
BILL = re.compile(r"spending cap|billing|exceeded its monthly", re.I)
PIPES = [("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("original_gate", "original paper gate"), ("combined", "combined gate")]
_M = {}


# ------------------------------------------------------------------ setup (in-process patches only)
def new_rec(key):
    """latest attempt record of a planned prompt key (file calls/<key>.json holds the attempt list)."""
    f = CALLS / f"{key}.json"
    if not f.exists():
        return None
    att = json.load(open(f))["attempts"]
    good = [a for a in att if a.get("status") == "ok" and a.get("complete")]
    return good[-1] if good else None


def merge(orig, extra):
    """original record plus per-event entries of extra for events the original lacks (per-event fallback, avb_anchorfix_1108 rule)."""
    if extra is None:
        return orig
    if orig is None:
        return extra
    m = copy.deepcopy(orig); p = m.setdefault("parsed", {}) or {}
    if "per_event" in (extra.get("parsed") or {}):
        have = {e.get("event_id") for e in p.get("per_event", []) if str(e.get("label", "")).lower() in ("yes", "no") or e.get("observed_count") is not None}
        p["per_event"] = [e for e in p.get("per_event", []) if e.get("event_id") in have] + \
                         [e for e in extra["parsed"]["per_event"] if e.get("event_id") not in have]
        ids = {a.get("event_id") for a in m.get("anchor", [])}
        m["anchor"] = m.get("anchor", []) + [a for a in extra.get("anchor", []) if a.get("event_id") not in ids]
    elif str(p.get("label", "")).lower() not in ("yes", "no"):
        m["parsed"] = extra.get("parsed")
    m["parsed"] = p if "per_event" in (extra.get("parsed") or {}) else m["parsed"]
    return m


def setup():
    if _M:
        return _M
    import avb_skipfix_1108 as SF, avb_anchorfix_1108 as AF
    AU = SF.patch(); AF.patch()
    import mova390_pipeline_1108 as MP
    GE, O, G = MP.register()
    import bidir_pilot_1106 as BP, bidir_full_1107 as BF, gate_pilot_1106 as GPI, section6_1106 as S6, p12_calib_1108 as P12
    BP.DS[DSN] = (SRC, "G"); S6.SRC[DSN] = SRC; S6.A5[SRC] = "M5"
    obs = json.load(open(MP.SYO / "sync_obs_lines_mova390.json"))
    orig_payload = BF.payload

    def payload(ds, ax, item, fam):
        if ds == DSN and ax == "AVB":                    # same adapter as the 2k_25 AVB payload (gen_stage2_1030.avb_text format)
            t = obs.get(item)
            return (None if t is None else "Observation (tool output):\n" + t), SRC
        return orig_payload(ds, ax, item, fam)
    BF.payload = payload
    orig_vcheck = G.vcheck

    def vcheck(uid):
        v = orig_vcheck(uid)
        if v is None:
            r = new_rec(f"VC__{uid}")
            v = None if r is None else {e["event_id"]: e["verdict"] for e in (r.get("parsed") or {}).get("per_event", [])}
        return v
    G.vcheck = vcheck; GPI.vcap = vcheck
    orig_s2 = AU.stage2_rec
    sub = json.load(open(OUT / "substitutions.json")) if (OUT / "substitutions.json").exists() else {}

    def stage2_rec(set_name, uid):
        k = f"{set_name}__{uid}"
        if set_name == "M5":
            return new_rec(sub[k]) if k in sub else None
        rec = orig_s2(set_name, uid)
        return merge(rec, new_rec(sub[k])) if k in sub else rec
    AU.stage2_rec = stage2_rec
    _M.update(AU=AU, O=O, G=G, BP=BP, BF=BF, GPI=GPI, S6=S6, P12=P12, MP=MP, SUB=sub)
    return _M


def mova390_ds():
    M = setup(); AU, MP = M["AU"], M["MP"]
    items = MP.items(); gt = [json.loads(l) for l in open(MP.D / "gt_mova390.jsonl")]
    gtA, gtV, gtB = {}, {}, {}
    for m in gt:
        for ax, dct in (("A", gtA), ("V", gtV), ("AVB", gtB)):
            if m["axis"] == ax:
                for e, v in m["gt"].items():
                    dct[(m["item_id"], e)] = v
    tc = pd.DataFrame([dict(uid=f"{SRC}|{m['item_id']}|TCC|{e}", y=v) for m in gt if m["axis"] == "TCC" for e, v in m["gt"].items()])
    rule = json.load(open((_tp.DATA + "/tools/synchformer_action_1030/PREREGISTERED_RULE.json")))
    pe = pd.concat(pd.read_csv(f) for f in sorted(MP.SYO.glob("per_event_shard*.csv")))
    ok = pe[pe.status == "ok"].assign(a=lambda t: t.offset.abs())
    best = ok.sort_values(["a", "prob"], ascending=False).drop_duplicates("item_id")
    fire = {r.item_id: bool(r.a >= rule["T"] - 1e-9 and r.prob >= rule["P"] - 1e-9) for r in best.itertuples()}
    ds = dict(items=items, rows=[dict(m, source=SRC, variant="MOVA") for m in gt], gtA=gtA, gtV=gtV, gtB=gtB, tc=tc,
              r1=AU.load_run(sorted(glob.glob(str(MP.R1 / "mova390_shard*.csv")))), r2=AU.load_run(sorted(glob.glob(str(MP.R2 / "mova390_shard*.csv")))),
              s2=("M4", SRC), s2av=("M4", SRC), fires=lambda iid: fire.get(iid, False), hd=False)
    return ds, gt, ok


def mova390_units(ds, gt):
    """all MOVA390 units x four baseline conditions, with the section6_1106 / audit_1106 rules."""
    M = setup(); AU, S6 = M["AU"], M["S6"]
    S6.av_rows = lambda D: [(DSN, dict(uid=f"{SRC}|{m['item_id']}|{m['axis']}", item_id=m["item_id"], axis=m["axis"], gt=m["gt"], variant="MOVA", part=""))
                            for m in gt if m["axis"] in ("A", "V")]
    D = {DSN: ds}
    U = pd.DataFrame(S6.av_events(D) + S6.avb_events(D))
    rows = []
    for u in AU.units(DSN, ds):
        if u["axis"] not in ("TCR", "TCC"):
            continue
        el = AU.gt_eligible(ds, u); y = AU.gt_label(ds, u) if el else ""
        for c in S6.CONDS:
            lu = AU.label_unit(ds, u, c) if el else dict(status="excluded", reason="GT prerequisite not met / not applicable")
            ev = u["uid"].split("|")[2] if u["axis"] == "TCC" else "video"
            rows.append(dict(dataset=DSN, axis=u["axis"], unit=u["uid"], item=u["item"], event=ev, cond=c, gt_elig=el, gt_y=y, status=lu["status"],
                             reason=lu.get("reason", ""), y=lu.get("y", ""), pred=lu.get("pred", ""), gate_open=False if c == "row5" else None, variant=""))
    return pd.concat([U, pd.DataFrame(rows)], ignore_index=True)


# ------------------------------------------------------------------ audit
def classify(reason):
    r = str(reason)
    if r in ("", "nan"):
        return ""
    if "prereq FAIL" in r or "GT prereq" in r or "not applicable" in r or "GT label missing" in r or "no prompt item" in r or "GT prerequisite" in r:
        return "valid exclusion (prerequisite / GT)"
    if r in ("API / run error", "item missing from run"):
        return "missing or failed call"
    if r in ("no stage-2 call", "gate open, no stage-2 call", "gate undetermined (no caption check)"):
        return "missing or failed call"
    if r in ("no stage-2 entry", "no direct output (fill / invalid)", "no direct output", "judge prereq not output (fill)"):
        return "output without a usable label (fill / malformed)"
    return "other: " + r


def stage_audit(a):
    OUT.mkdir(parents=True, exist_ok=True)
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[U.group == U.dataset]
    F = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False)
    U = pd.concat([U[U.axis != "AVB"], F], ignore_index=True)
    ds, gt, _ = mova390_ds(); N = mova390_units(ds, gt); N.to_csv(OUT / "mova390_units_before.csv", index=False)
    U = pd.concat([U, N], ignore_index=True)
    U["class"] = U.reason.map(classify)
    X = U[U.status != "scored"].groupby(["dataset", "axis", "cond", "class", "reason"]).size().rename("units").reset_index()
    X.to_csv(OUT / "audit_unscored_by_reason.csv", index=False)
    # MOVA390 baseline verification
    MP = setup()["MP"]
    def run_stats(R):
        d = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(str(R / "mova390_shard*.csv"))) if "per_event" not in f)
        return dict(rows=len(d), unique_items=int(d.item_id.nunique()), errors=int(d.overall_reason.astype(str).str.startswith("ERROR").sum()))
    st = collections.Counter((p.split("|")[-1][:-5], json.load(open(p))["status"]) for p in glob.glob(str(RUNS / "calls/gen_tool_text/M4__*.json")))
    rows4 = sum(1 for l in open(RUNS / "rows.jsonl") if '"set": "M4"' in l and '"gen_tool_text"' in l)
    V = dict(items=len(MP.items()), row1=run_stats(MP.R1), row2=run_stats(MP.R2), M4_rows=rows4, M4_records={f"{k[0]}|{k[1]}": v for k, v in sorted(st.items())})
    json.dump(V, open(OUT / "mova390_baseline_verification.json", "w"), indent=1)
    print(json.dumps(V, indent=1))
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
    print(X[~X["class"].str.startswith("valid")].to_string(index=False))


# ------------------------------------------------------------------ plan
def rows_index():
    t = {}
    for l in open(RUNS / "rows.jsonl"):
        r = json.loads(l)
        if r["cond"] == "gen_tool_text":
            t[(r["set"], r["uid"])] = r
    return t


def reuse_index(O):
    idx = dict(json.load(open(RUNS / "p12_calib_1108/reuse_index.json")))
    for d in (RUNS / "p12_calib_1108/calls", RUNS / "avb_anchorfix_1108/calls"):
        for p in d.glob("*.json"):
            r = json.load(open(p))
            if r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5:
                idx.setdefault(r["user_md5"], str(p))
    for p in glob.glob(str(RUNS / "calls/gen_tool_text/M4__*.json")):
        r = json.load(open(p))
        if r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5 and r.get("model") == MODEL and r.get("thinking") == "high":
            idx.setdefault(r["user_md5"], p)
    return idx


def complete(rec, axis, need):
    """True if rec (status ok) has a usable entry for every needed event (None = TR single label)."""
    if rec is None or rec.get("status") != "ok":
        return False
    AU = setup()["AU"]
    rec = dict(rec); rec.setdefault("anchor", [])
    return all(AU.s2_event(rec, axis, e)[1] == "ok" for e in (need or [None]))


def vcheck_call(G, O, r, items):
    c = G.caption(SRC, r["item_id"])
    if c is None:
        return None
    evs = items[r["item_id"]]["events"]; ids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(evs)}
    lines = [f"- {ids[e['id']]}: {e['definition']}" for e in evs if ids[e["id"]] in r["gt"]]
    user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() +
            "\n\nTarget visual events:\n" + "\n".join(lines) +
            "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
            "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
            "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
            "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
    return dict(system=G.VCHK_SYSTEM, user=user, schema=G.VCHK_SCHEMA)


def stage_plan(a):
    M = setup(); AU, O, G, S6, P12, BF, MP = (M[k] for k in ("AU", "O", "G", "S6", "P12", "BF", "MP"))
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "prompts").mkdir(exist_ok=True)
    RI, idx = rows_index(), reuse_index(O)
    plan = []                                                       # one row per (purpose, unit group); prompts deduplicated by md5

    def add(purpose, dataset, item, axis, uid, cc, need, sub_key=None, kind="stage2"):
        md5 = hashlib.md5(cc["user"].encode()).hexdigest()
        key = ("VC__" + uid) if kind == "vcheck" else f"FC__{md5}"
        f = idx.get(md5) if kind == "stage2" else None
        reuse = False
        if f:
            rec = json.load(open(f)); rec.setdefault("anchor", cc.get("anchor", []))
            reuse = complete(rec, axis, need)
        if not reuse:
            json.dump(dict(uid=uid, item=item, axis=axis, kind=kind, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5,
                           anchor=cc.get("anchor", []), need=need), open(OUT / "prompts" / f"{key.replace('/', '_')}.json", "w"))
        plan.append(dict(purpose=purpose, dataset=dataset, item=item, axis=axis, uid=uid, need=";".join(e or "" for e in (need or [])), user_md5=md5, key=key,
                         sub_key=sub_key or "", prompt_chars=len(cc["system"]) + len(cc["user"]), reuse_file=f if reuse else "",
                         action="reuse (exact complete output)" if reuse else "new call"))

    # (1) existing datasets: A / V stage-2 outputs that are missing, failed or lack the needed events (row 4 = s2av set, row 5 = gate set)
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[(U.group == U.dataset) & U.axis.isin(["A", "V"])]
    base = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)][["dataset", "unit"]]
    D = AU.datasets()
    bad = U[U.cond.isin(["row4", "row5"]) & (U.status != "scored")].merge(base, on=["dataset", "unit"])
    bad = bad[bad.reason.map(classify) != "valid exclusion (prerequisite / GT)"]
    for (dsn, item, ax), g in bad.groupby(["dataset", "item", "axis"]):
        if dsn == "P03-P09" and ax == "A":
            continue                                                # P03-P09 A = anchor-mute set; no gap there
        ds = D[dsn]; src = ds["s2"][1]; uid = f"{src}|{item}|{ax}"
        for c, q in g.groupby("cond"):
            st = ds["s2av"][0]
            if c == "row5" and ax == "A":
                op, same = S6.a_gate(S6.SRC[dsn], item); st = st if same else S6.A5[S6.SRC[dsn]]
            r = RI.get((st, uid))
            if r is None:
                plan.append(dict(purpose=f"retry existing {c}", dataset=dsn, item=item, axis=ax, uid=uid, action=f"no row for {st} (cannot rebuild)")); continue
            cc = O.build_call(r)
            add(f"retry existing {c} ({st})", dsn, item, ax, uid, cc, sorted(set(q.event)), sub_key=f"{st}__{uid}")
    # (2) MOVA390 caption checks (V rows; original gate and combined gate both need them)
    items = MP.items(); gt = [json.loads(l) for l in open(MP.D / "gt_mova390.jsonl")]
    for m in gt:
        if m["axis"] != "V":
            continue
        uid = f"{SRC}|{m['item_id']}|V"
        if G.vcheck(uid) is not None:
            continue
        cc = vcheck_call(G, O, m, items)
        if cc:
            add("MOVA390 caption check", DSN, m["item_id"], "V", uid, cc, None, kind="vcheck")
    # (3) MOVA390 original gate A: gated text differs from the always-shown text -> new M5 call (text = gated tool text)
    for m in gt:
        if m["axis"] != "A":
            continue
        iid = m["item_id"]; g5, g4 = G.a_text(SRC, iid, gated=True), G.a_text(SRC, iid)
        if g5 and g5 != g4:
            uid = f"{SRC}|{iid}|A"
            r = dict(set="M5", source=SRC, uid=uid, item_id=iid, axis="A", variant="MOVA", gt=m["gt"], clip=iid, cond="gen_tool_text", obs={"text": g5})
            cc = O.build_call(r)
            if cc is None:
                plan.append(dict(purpose="MOVA390 original gate A (M5)", dataset=DSN, item=iid, axis="A", uid=uid, action="no stage-1 anchor")); continue
            add("MOVA390 original gate A (M5)", DSN, iid, "A", uid, cc, [e["event_id"] for e in cc["anchor"]], sub_key=f"M5__{uid}")
    # (4) MOVA390 M4 AVB rows whose anchor changes under the anchor fix (fallback for events the original M4 call lacks)
    for (st, uid), r in RI.items():
        if st != "M4" or r["axis"] != "AVB":
            continue
        cc = O.build_call(r)
        if cc is None:
            continue
        old = AU.stage2_rec("M4", uid)
        lack = [e["event_id"] for e in cc["anchor"] if AU.s2_event(old, "AVB", e["event_id"])[1] != "ok"]
        if lack:
            add("MOVA390 always shown / original gate AVB (anchor fix)", DSN, r["item_id"], "AVB", uid, cc, lack, sub_key=f"M4__{uid}")
    # (5) MOVA390 combined gate: open units -> bidirectional payload (A: opened sound events; V: caption; AVB: Synchformer lines)
    ds, gt_, ok = mova390_ds(); X = combined_units(ds, gt_, ok)
    for (item, ax), g in X[X.opened].groupby(["item", "axis"]):
        text, s_ = BF.payload(DSN, ax, item, {e: ("A sound" if ax == "A" else ax) for e in g.event})
        uid = f"{s_}|{item}|{ax}"
        if text is None:
            plan.append(dict(purpose="MOVA390 combined gate", dataset=DSN, item=item, axis=ax, uid=uid, action="missing payload")); continue
        cc = O.build_call(dict(set="PC", source=s_, uid=uid, item_id=item, axis=ax, variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text}))
        if cc is None:
            plan.append(dict(purpose="MOVA390 combined gate", dataset=DSN, item=item, axis=ax, uid=uid, action="no stage-1 anchor")); continue
        add("MOVA390 combined gate", DSN, item, ax, uid, cc, sorted(set(g.event)))
    P = pd.DataFrame(plan); P.to_csv(OUT / "call_plan.csv", index=False)
    sub = {r.sub_key: (Path(r.reuse_file).stem if False else r.key) for r in P.itertuples() if isinstance(r.sub_key, str) and r.sub_key and r.action == "new call"}
    json.dump(sub, open(OUT / "substitutions.json", "w"), indent=1)
    b = json.load(open(RUNS / "bidir_full_1107/estimate_basis.json")); new = P[P.action == "new call"].drop_duplicates("key")
    est = dict(planned=len(P), unique_new_calls=len(new), reused=int((P.action == "reuse (exact complete output)").sum()),
               by_purpose=P.groupby(["purpose", "action"]).size().rename("n").reset_index().to_dict("records"),
               est_usd_list=round(new.prompt_chars.sum() / b["chars_per_token"] / 1e6 * 1.5 + b["output_tokens_median"] * len(new) / 1e6 * 7.5, 2))
    json.dump(est, open(OUT / "estimate.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250); print(P.groupby(["purpose", "action"]).size().to_string()); print("unique new calls", len(new), "est usd", est["est_usd_list"])


def combined_units(ds, gt, ok):
    """MOVA390 row-1-eligible units with frozen-config features and opening decision (A speech = original gate, inherited)."""
    M = setup(); G, GPI, P12 = M["G"], M["GPI"], M["P12"]
    cfg = json.load(open(RUNS / "p12_calib_1108/frozen_p12_config.json"))["config"]
    N = mova390_units(ds, gt)
    b = N[(N.cond == "row1") & (N.status == "scored") & N.gt_elig.astype(bool)].rename(columns={"pred": "initial", "gt_y": "gt"}).copy()
    items = ds["items"]; sy = ok.drop_duplicates(["item_id", "event_id"]).set_index(["item_id", "event_id"])
    fam, fl, vc, off, prob = [], [], [], [], []
    for r in b.itertuples():
        f = x = y = o = p = None
        if r.axis == "A":
            e = items[r.item]["events"][int(r.event.split("_")[1]) - 1]
            f = {"speech": "A speech", "sounding_action": "A sound"}.get(e["modality"])
            rec = G.evidence(SRC, r.item)
            fe = GPI.flam_evidence(rec, r.event) if (rec and f == "A sound") else None
            x = fe["max_score"] if fe else None
        elif r.axis == "V":
            f = "V"; v = G.vcheck(f"{SRC}|{r.item}|V"); y = v.get(r.event) if v else None
        elif r.axis == "AVB":
            f = "AVB"
            if (r.item, r.event) in sy.index:
                o, p = abs(float(sy.offset.get((r.item, r.event)))), float(sy.prob.get((r.item, r.event)))
        fam.append(f); fl.append(x); vc.append(y); off.append(o); prob.append(p)
    b["family"], b["flam_max"], b["vcap"], b["off"], b["prob"] = fam, fl, vc, off, prob
    res = [P12.open_rule(cfg, r) for r in b.itertuples()]
    b["opened"] = [x[0] for x in res]; b["branch_key"] = [x[1] for x in res]; b["fallback"] = [x[2] for x in res]
    b["branch"] = np.where(b.initial == "yes", "FAIL", "PASS")
    return b


# ------------------------------------------------------------------ run
def stage_run(a):
    M = setup(); O = M["O"]
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    import threading
    P = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = P[P.action == "new call"].drop_duplicates("key")
    CALLS.mkdir(exist_ok=True)
    if (OUT / "HOLD").exists():
        sys.exit("HOLD file present; not running")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); stop = threading.Event(); n = collections.Counter(); t0 = time.time()
    AU = M["AU"]

    def done(c):
        f = CALLS / f"{c.key.replace('/', '_')}.json"
        if not f.exists():
            return False, []
        att = json.load(open(f))["attempts"]
        return any(x.get("complete") for x in att) or len(att) >= MAXTRY, att

    def one(c):
        if stop.is_set():
            return "skipped (hold)"
        fin, att = done(c)
        if fin:
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.key.replace('/', '_')}.json"))
        while len(att) < MAXTRY and not stop.is_set():
            r = dict(uid=c.uid, obs={})
            try:
                parsed, raw = O.call(client, MODEL, dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
                rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], anchor=p["anchor"])
                if p["kind"] == "vcheck":
                    got = {e.get("event_id"): e.get("verdict") for e in (parsed or {}).get("per_event", [])}
                    want = [l.split(":")[0][2:] for l in p["user"].split("Target visual events:\n")[1].split("\n\n")[0].split("\n")]
                    rec["complete"] = all(got.get(w) in ("describes", "contradicts", "not_mentioned") for w in want)
                else:
                    rec["complete"] = complete(rec, p["axis"], [e or None for e in p["need"]] if p["need"] else None)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                rec = dict(status="error", error=msg[:2000], complete=False, usage=r.get("_usage"))
                if BILL.search(msg):
                    stop.set(); (OUT / "HOLD").write_text(f"HOLD {time.strftime('%Y-%m-%dT%H:%M:%S')}: billing / spending-cap error on {c.uid}; no key rotation\n")
            rec.update(uid=c.uid, model=MODEL, thinking="high", rules_md5=O.OBS_RULES_MD5, attempt=len(att) + 1, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
            att.append(rec)
            json.dump(dict(key=c.key, uid=c.uid, attempts=att), open(CALLS / f"{c.key.replace('/', '_')}.json", "w"), default=str)
            if rec.get("complete") or (rec["status"] == "error" and BILL.search(rec.get("error", ""))):
                break
        return "ok" if att and att[-1].get("complete") else ("hold" if stop.is_set() else "unresolved")
    vc = todo[todo.key.str.startswith("VC__")]; rest = todo[~todo.key.str.startswith("VC__")]
    for name, part in (("caption checks + other", pd.concat([vc, rest])),):
        with ThreadPoolExecutor(a.workers) as ex:
            for i, s in enumerate(ex.map(one, list(part.itertuples()))):
                n[s] += 1
                if i % 25 == 0 or i + 1 == len(part):
                    print(f"[final_cov] {i + 1}/{len(part)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), workers=a.workers, hold=stop.is_set(), time=time.strftime("%Y-%m-%dT%H:%M:%S")),
              open(OUT / f"run_info_{time.strftime('%H%M%S')}.json", "w"), indent=1)
    print("[DONE]", dict(n), "HOLD" if stop.is_set() else "")


# ------------------------------------------------------------------ score
def plan_rec(P, purpose, item, axis):
    """complete output for a planned (purpose, item, axis): reused file or the new call's last complete attempt."""
    q = P[(P.purpose == purpose) & (P["item"] == item) & (P.axis == axis)]
    for r in q.itertuples():
        if r.action.startswith("reuse") and r.reuse_file:
            rec = json.load(open(r.reuse_file)); return rec if rec.get("status") == "ok" else None
        if r.action == "new call":
            return new_rec(r.key)
    return None


def existing_units(M):
    """existing datasets after avb_anchorfix_1108, with A / V row 4 / row 5 / combined gaps refilled from the retries of this run."""
    AU, S6, BF = M["AU"], M["S6"], M["BF"]
    ALL = pd.read_csv(RUNS / "avb_anchorfix_1108/all_axes_unit_results_after_anchorfix.csv", low_memory=False)
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[U.group == U.dataset]
    E = pd.read_csv(RUNS / "p12_calib_1108/eval_unit_results.csv", low_memory=False).set_index(["dataset", "unit"])
    C = pd.read_csv(RUNS / "p12_combo_1108/combined_unit_results.csv", low_memory=False).set_index(["dataset", "unit"])
    AVB = pd.read_csv(RUNS / "combined_fix_1108/avb_combined_unit_results.csv", low_memory=False).set_index(["dataset", "unit"])
    FX = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False)
    G5 = pd.concat([U[(U.cond == "row5") & (U.axis != "AVB")], FX[FX.cond == "row5"]]).drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"])
    before = ALL.copy()
    NEW = pd.DataFrame(S6.av_events(AU.datasets())).drop_duplicates(["dataset", "unit", "cond"]).set_index(["dataset", "unit", "cond"])
    CP = pd.read_csv(RUNS / "p12_calib_1108/call_plan.csv").fillna("")
    for i, x in ALL[ALL.axis.isin(["A", "V"])].iterrows():
        for col, c in (("always_shown", "row4"), ("original_gate", "row5")):
            if x[col] not in ("yes", "no"):
                k = (x.dataset, x.unit, c)
                if k in NEW.index and NEW.status.get(k) == "scored":
                    ALL.at[i, col] = NEW.pred.get(k)
    fam = [C.family.get((d, u)) if (d, u) in C.index else None for d, u in zip(ALL.dataset, ALL.unit)]
    ALL["family"] = fam
    for i, x in ALL[ALL.axis.isin(["A", "V"]) & ~ALL.combined.isin(["yes", "no"])].iterrows():
        if x.family == "A speech":
            ALL.at[i, "combined"] = x.original_gate if x.original_gate in ("yes", "no") else ""; continue
        cp = CP[(CP.dataset == x.dataset) & (CP["item"] == x["item"]) & (CP.axis == x.axis)]
        rec = new_rec(f"FC__{cp.user_md5.iloc[0]}") if len(cp) and cp.user_md5.iloc[0] else None
        l, st = AU.s2_event(rec, x.axis, x.event)
        if st == "ok" and l in ("yes", "no"):
            ALL.at[i, "combined"] = l; ALL.at[i, "combined_source"] = "open: retried call (final_cov_1108)"
    # gate-opening flags and branches
    ALL["comb_opened"] = [bool(AVB.opened.get((d, u))) if a == "AVB" else (bool(G5.gate_open.get((d, u))) if f == "A speech" else bool(E.opened.get((d, u))) if (d, u) in E.index else False)
                          for d, u, a, f in zip(ALL.dataset, ALL.unit, ALL.axis, ALL.family)]
    ALL["orig_opened"] = [False if a in ("TCC", "TCR") else bool(G5.gate_open.get((d, u)) == True) for d, u, a in zip(ALL.dataset, ALL.unit, ALL.axis)]
    changed = int(((before.always_shown != ALL.always_shown) | (before.original_gate != ALL.original_gate) | (before.combined != ALL.combined)).sum())
    return ALL, changed


def mova390_table(M, P):
    AU, BF, O = M["AU"], M["BF"], M["O"]
    ds, gt, ok = mova390_ds()
    orig_rows = M["S6"].av_rows
    N = mova390_units(ds, gt); M["S6"].av_rows = orig_rows
    X = combined_units(ds, gt, ok)
    piv = {c: N[N.cond == c].drop_duplicates("unit").set_index("unit") for c in ("row2", "row4", "row5")}
    for c, nm in (("row2", "one_call"), ("row4", "always_shown"), ("row5", "original_gate")):
        X[nm] = [piv[c].pred.get(u) if piv[c].status.get(u) == "scored" else "" for u in X.unit]
        X[nm + "_reason"] = [piv[c].reason.get(u) if piv[c].status.get(u) != "scored" else "" for u in X.unit]
    X["orig_opened"] = [bool(piv["row5"].gate_open.get(u) == True) for u in X.unit]
    lab, src = [], []
    for x in X.to_dict("records"):
        if x["family"] == "A speech":
            lab.append(x["original_gate"]); src.append("A speech: original paper gate (inherited)"); continue
        if not x["opened"]:
            lab.append(x["initial"]); src.append("closed: media-only label" + (f" ({x['fallback']})" if x["fallback"] else "")); continue
        rec = plan_rec(P, "MOVA390 combined gate", x["item"], x["axis"])
        l, st = AU.s2_event(rec, x["axis"], x["event"])
        ok_ = st == "ok" and l in ("yes", "no")
        lab.append(l if ok_ else ""); src.append("open: stage-2 label" if ok_ else f"open: unresolved ({st})")
    X["combined"] = lab; X["combined_source"] = src
    X["comb_opened"] = [bool(o) or (f == "A speech" and oo) for o, f, oo in zip(X.opened, X.family, X.orig_opened)]
    X["group"] = "MOVA390"; X["portion"] = "all"
    return X, N


def stage_score(a):
    import bidir_full_1107 as BFm
    M = setup(); P = pd.read_csv(OUT / "call_plan.csv").fillna("")
    EX, changed = existing_units(M)
    X, N = mova390_table(M, P); N.to_csv(OUT / "mova390_units_all_conditions.csv", index=False)
    cols = ["dataset", "group", "axis", "unit", "item", "event", "portion", "gt", "initial", "one_call", "always_shown", "original_gate", "combined",
            "family", "comb_opened", "orig_opened", "combined_source"]
    ALL = pd.concat([EX[cols], X[cols]], ignore_index=True)
    ALL["branch"] = np.where(ALL.initial == "yes", "initial PASS (FAIL-evidence branch)", "initial FAIL (PASS-evidence branch)")
    ALL.to_csv(OUT / "all_units_five_methods.csv", index=False)
    pooled = ALL[ALL.group.isin(["MOVA (old 220)", "MOVA390"])].assign(group="MOVA pooled (old 220 + MOVA390)")
    T = pd.concat([ALL, pooled], ignore_index=True)
    rows, pc, cov, br = [], [], [], []
    for kk in (("dataset", "axis"), ("group", "axis")):
        for key, q in T.groupby(list(kk)):
            if kk[0] == "dataset" and key[0] not in GROUP:
                continue
            q = q.drop_duplicates(["dataset", "unit"])
            common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c, _ in PIPES])]
            for col, nm in PIPES:
                m = BFm.metrics(common["gt"], common[col])
                rows.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), method=nm, eligible_row1=len(q), common_units=len(common),
                                 n_FAIL=int((common["gt"] == "no").sum()), n_PASS=int((common["gt"] == "yes").sum()),
                                 **{k: m.get(k) for k in ("acc", "macro_F1", "bal_acc", "FAIL_R", "FA", "FAIL_P", "FAIL_F1", "PASS_P", "PASS_R", "PASS_F1")}))
                cov.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), method=nm, eligible_row1=len(q), scored=int(q[col].isin(["yes", "no"]).sum()),
                                missing=int((~q[col].isin(["yes", "no"])).sum())))
            for ref, rn in PIPES[:4]:
                o_, n_ = common[ref] == common["gt"], common["combined"] == common["gt"]
                pc.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), vs=rn, common_units=len(common), corrections=int((~o_ & n_).sum()), corruptions=int((o_ & ~n_).sum())))
            for g, col, opc in (("original paper gate", "original_gate", "orig_opened"), ("combined gate", "combined", "comb_opened")):
                for b, h in q.groupby("branch"):
                    op = h[h[opc].astype(bool)]; sc = op[op[col].isin(["yes", "no"])]
                    br.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), gate=g, branch=b, units=len(h), opened=len(op), opened_scored=len(sc),
                                   opened_unresolved=len(op) - len(sc), label_changed=int((sc[col] != sc.initial).sum()),
                                   corrections=int(((sc.initial != sc["gt"]) & (sc[col] == sc["gt"])).sum()), corruptions=int(((sc.initial == sc["gt"]) & (sc[col] != sc["gt"])).sum()),
                                   opened_GT_FAIL=int((op["gt"] == "no").sum()), opened_GT_PASS=int((op["gt"] == "yes").sum())))
    pd.DataFrame(rows).to_csv(OUT / "metrics_five_methods.csv", index=False); pd.DataFrame(pc).to_csv(OUT / "paired_changes.csv", index=False)
    pd.DataFrame(cov).to_csv(OUT / "coverage.csv", index=False); pd.DataFrame(br).to_csv(OUT / "gate_openings_by_branch.csv", index=False)
    # exclusion counts upstream of the row-1 universe (all GT units), MOVA390 from this run, others from section6 / skipfix
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[U.group == U.dataset]
    FX = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False)
    U = pd.concat([U[U.axis != "AVB"], FX, N], ignore_index=True)
    U["class"] = U.reason.map(classify)
    EXC = U.groupby(["dataset", "axis", "cond", "status", "class"]).size().rename("units").reset_index(); EXC.to_csv(OUT / "exclusion_counts.csv", index=False)
    # unresolved outputs and cost
    unres, us = [], []
    for f in CALLS.glob("*.json"):
        d = json.load(open(f)); att = d["attempts"]
        us += [x.get("usage") or {} for x in att]
        if not any(x.get("complete") for x in att):
            unres.append(dict(key=d["key"], uid=d["uid"], attempts=len(att), last_status=att[-1].get("status"), last_error=str(att[-1].get("error", ""))[:200],
                              last_raw=str(att[-1].get("raw", ""))[:200]))
    pd.DataFrame(unres).to_csv(OUT / "unresolved_outputs.csv", index=False)
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    json.dump(dict(prompts=len(list(CALLS.glob("*.json"))), attempts=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3),
                   unresolved=len(unres), existing_units_changed_by_retries=changed), open(OUT / "cost.json", "w"), indent=1)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
    R = pd.DataFrame(rows); print(R[R.level == "group/axis"][["key", "method", "common_units", "acc", "macro_F1", "bal_acc", "FAIL_R", "FA"]].to_string(index=False))
    print(json.load(open(OUT / "cost.json")))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["audit", "plan", "run", "score"]); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
