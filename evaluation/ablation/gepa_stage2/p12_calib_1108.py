#!/usr/bin/env python3
"""Corrected gate calibration protocol (11/08): select every new gate rule / threshold on HD-EPIC P01/P02 ONLY; evaluate the frozen
configuration unchanged on P03-P09, LTX (220 + 149 + 2k_25) and old MOVA (220). Writes only to runs/obsval_1028/p12_calib_1108/.
GT, paper tables, MOVA390 work and every earlier output are untouched. Earlier LTX- / P03-P09-selected variants stay EXPLORATORY.
Calibration units (P01/P02, all sources with GT; original and perturbed items):
  A sound  hm_ma (mute anchor + original; shams and the 6 past-end windows excluded, as the paper), hm_hdepic and hm_p12new (absent sound +
           original), hm_hdfoot (absent footstep, old prompts); feature = FLAM first-query whole-clip max (gen_evidence_1030 ma / hdA / p12A)
  A speech none (HD-EPIC has no speech events)  -> UNSUPPORTED
  V        hm_hdepic, hm_p12new (hand swap, noun swap, original), hm_oldnoun12 (old-rule noun swap); feature = caption check verdict (vcap_check)
  AVB      hm_hdepic, hm_p12new, hm_avbadd12 (audio shift early / late, original); feature = Synchformer action-window reading
           (synchformer_action_1030 p12all, avbadd, b110; |offset|, confidence of the reported offset, p(0))
  initial label = the source's row 1 anchor run (obs_judge_1028.ANCHOR), event status 'ok' only.
Frozen families (direction = initial label only) and constraint (empirical, no formal guarantee):
  A sound   FAIL evidence: flam_max < t;  PASS evidence: flam_max >= t
  AVB       FAIL evidence: |off| >= T and conf >= P;  PASS evidence: |off| <= S and conf >= Q
  V (fixed candidates, validated only)  FAIL evidence: verdict contradicts;  PASS evidence: verdict describes
  A speech (fixed candidates)  absence FAIL / heard p >= .5 PASS -> no P01/P02 units
  feasible: risk denominator (initially correct units) >= 20 and erroneous admission <= .05. Selection: maximise admission among initially
  incorrect units; ties -> lower erroneous admission; then conservative order (FLAM FAIL: smaller t; FLAM PASS: larger t; AVB FAIL: larger T
  then larger P; AVB PASS: smaller S then larger Q). Thresholds are observed calibration values; equal admission sets are merged.
  Status: INSUFFICIENT SUPPORT (risk denominator < 20 or no initially incorrect unit) / NO USEFUL FEASIBLE RULE / FAILS CRITERION (fixed rule)
  / USABLE EMPIRICAL CANDIDATE (selected) or MEETS CRITERION (fixed rule). Unsupported / failing branches -> media-only label at evaluation.
Evaluation: section6_1106 units (row 1 scored, GT-eligible) of P03-P09, 220 LTX, 149 LTX, 2k_25 LTX, 220 MOVA, both split portions;
  features from gate_redesign_round2/unit_features.csv; stage 2 = bidir_pilot_1106.payload (A: opened sound events only; V: caption block;
  AVB: Synchformer lines) + obs_judge_1028.build_call, gemini-3.6-flash, thinking high, temperature 0, seed 42; exact-prompt reuse.
  python gepa_stage2/p12_calib_1108.py build | select | plan | run | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, glob, hashlib, json, os, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "p12_calib_1108"
EV = Path((_tp.DATA + "/tools/gen_evidence_1030"))
SYA = Path((_tp.DATA + "/tools/synchformer_action_1030"))
ALPHA, MIN_N = 0.05, 20
EVAL_DS = ("P03-P09", "220 LTX", "149 LTX", "2k_25 LTX", "220 MOVA")
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA (old 220)", "P03-P09": "P03-P09"}


def cp(k, n):
    from scipy.stats import beta
    if not n:
        return (None, None)
    return (round(0.0 if k == 0 else float(beta.ppf(.025, k, n - k + 1)), 4), round(1.0 if k == n else float(beta.ppf(.975, k + 1, n - k)), 4))


# ------------------------------------------------------------------ calibration units
def sync_table():
    parts = []
    for pri, d in enumerate(("p12all", "avbadd", "b110")):
        for f in sorted(glob.glob(str(SYA / d / "per_event_shard*.csv"))):
            parts.append(pd.read_csv(f).assign(cache=d, pri=pri))
    t = pd.concat(parts); t = t[t.item_id.str.contains(r"hdepic_P0[12]-")]
    return t.sort_values("pri").drop_duplicates(["item_id", "event_id"]).set_index(["item_id", "event_id"])


def flam_rec(source, iid):
    cands = {"hm_ma": [EV / "ma" / f"ma__{iid}.json"], "hm_hdepic": [EV / "hdA" / f"hdepic_p12__{iid}.json"],
             "hm_hdfoot": [EV / "hdA" / f"hdfoot_p12__{iid}.json"], "hm_p12new": [EV / "p12A" / f"p12all__{iid}.json"]}[source]
    for f in cands:
        if f.exists():
            return json.load(open(f)), str(f)
    return None, ""


def stage_build(a):
    import obs_judge_1028 as O, audit_1106 as AU, hd_stage2_1101 as H, gate_pilot_1106 as GPI
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {s: AU.load_run([str(p) for p in O.ANCHOR[s]]) for s in ("hm_ma", "hm_hdepic", "hm_p12new", "hm_hdfoot", "hm_oldnoun12", "hm_avbadd12")}
    rows = []
    def init_of(src, iid, ax, eid):
        e = runs[src].get(iid)
        if e is None:
            return "", "item missing from row 1 run"
        if e["error"]:
            return "", "row 1 API / run error"
        lab, st = e[ax].get(eid, ("", "missing"))
        return (lab, "") if (st == "ok" and lab in ("yes", "no")) else ("", f"row 1 event status {st}")
    # A: mute anchor (P01/P02)
    for m in map(json.loads, open(H.MA_DIR["hm_ma"] / "manifest.jsonl")):
        if m["variant"] == "sham" or any(w in m["item_id"] for w in H.PASTEND_WINDOWS):
            continue
        rec, path = flam_rec("hm_ma", m["item_id"])
        for eid, y in m["gt"].items():
            fe = GPI.flam_evidence(rec, eid) if rec else None
            lab, why = init_of("hm_ma", m["item_id"], "A", eid)
            rows.append(dict(source="hm_ma", axis="A", family="A sound", item=m["item_id"], event=eid, variant=m["variant"], gt=y, initial=lab,
                             flam_max=fe["max_score"] if fe else np.nan, tool_path=path, missing=";".join(x for x in (why, "" if fe else "no FLAM reading") if x)))
    # A / V / AVB rows of the v3 P01/P02 sources
    st = sync_table()
    for r in H.gt_rows():
        src, ax, iid = r["source"], r["axis"], r["item_id"]
        if src not in ("hm_hdepic", "hm_p12new", "hm_hdfoot", "hm_oldnoun12", "hm_avbadd12"):
            continue
        for eid, y in r["gt"].items():
            if y not in ("yes", "no"):
                continue
            lab, why = init_of(src, iid, ax, eid)
            d = dict(source=src, axis=ax, item=iid, event=eid, variant=r.get("variant"), gt=y, initial=lab)
            if ax == "A":
                rec, path = flam_rec(src, iid); fe = GPI.flam_evidence(rec, eid) if rec else None
                rows.append(dict(d, family="A sound", flam_max=fe["max_score"] if fe else np.nan, tool_path=path,
                                 missing=";".join(x for x in (why, "" if fe else ("no FLAM record" if rec is None else "event has no FLAM query (not sounding)")) if x)))
            elif ax == "V":
                vc = GPI.vcap(f"{src}|{iid}|V") or {}
                rows.append(dict(d, family="V", vcap=vc.get(eid, ""), tool_path=f"calls/vcap_check/{src}|{iid}|V.json" if vc else "",
                                 missing=";".join(x for x in (why, "" if vc.get(eid) else "no caption-check verdict") if x)))
            elif ax == "AVB":
                k = (iid, eid); s = st.loc[k] if k in st.index else None
                ok = s is not None and s.status == "ok" and pd.notna(s.offset)
                rows.append(dict(d, family="AVB", off=abs(float(s.offset)) if ok else np.nan, prob=float(s.prob) if ok else np.nan,
                                 p0=float(s.p_offset0) if ok else np.nan, sync_cache=s.cache if s is not None else "",
                                 missing=";".join(x for x in (why, "" if ok else ("no Synchformer record" if s is None else f"Synchformer status {s.status}")) if x)))
    U = pd.DataFrame(rows); U["usable"] = U.missing.fillna("") == ""
    U.to_csv(OUT / "p12_calibration_units.csv", index=False)
    inv = U.assign(has_initial=U.initial.isin(["yes", "no"])).groupby(["axis", "family", "source", "variant"]).agg(
        gt_units=("item", "size"), with_initial=("has_initial", "sum"), usable=("usable", "sum")).reset_index()
    inv.to_csv(OUT / "p12_inventory.csv", index=False)
    miss = U[~U.usable].assign(reason=U.missing.str.replace(r"status \w+", "status X", regex=True)).groupby(["axis", "source", "reason"]).size().reset_index(name="units")
    miss.to_csv(OUT / "p12_missing_records.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(inv.to_string(index=False)); print(miss.to_string(index=False))


# ------------------------------------------------------------------ selection on P01/P02
def fam_rows(U, fam_axis, init):
    q = U[(U.family == fam_axis) & U.usable & (U.initial == init)]
    return q, q["gt"] == q["initial"]


def stat_row(name, m, risk):
    kr, nr, ku, nu = int((m & risk).sum()), int(risk.sum()), int((m & ~risk).sum()), int((~risk).sum())
    return dict(rule=name, opened=int(m.sum()), k_risk=kr, n_risk=nr, risk_rate=round(kr / nr, 4) if nr else None, risk_cp95=cp(kr, nr),
                k_use=ku, n_use=nu, use_rate=round(ku / nu, 4) if nu else None, use_cp95=cp(ku, nu))


def select_family(q, risk, fam):
    cands = []
    if fam == "A_FAIL":
        vals = sorted(q.flam_max.unique())
        for t in vals + [np.inf]:
            cands.append((("t", float(t)), q.flam_max < t, (t,)))                     # conservative: smaller t first
    elif fam == "A_PASS":
        for t in sorted(q.flam_max.unique(), reverse=True):
            cands.append((("t", float(t)), q.flam_max >= t, (-t,)))                   # conservative: larger t first
    elif fam == "AVB_FAIL":
        for T in sorted(q.off.unique(), reverse=True):
            for P in sorted(q.prob.unique(), reverse=True):
                cands.append((("T", float(T), "P", float(P)), (q.off >= T) & (q.prob >= P), (-T, -P)))
    elif fam == "AVB_PASS":
        for S in sorted(q.off.unique()):
            for P in sorted(q.prob.unique(), reverse=True):
                cands.append((("S", float(S), "Q", float(P)), (q.off <= S) & (q.prob >= P), (S, -P)))
    seen, sets = set(), []
    for par, m, order in cands:
        key = tuple(np.flatnonzero(m.values))
        if key in seen:
            continue
        seen.add(key); s = stat_row(str(par), m, risk); s.update(params=par, order=order); sets.append(s)
    S = pd.DataFrame(sets)
    n_r, n_u = int(risk.sum()), int((~risk).sum())
    if n_r < MIN_N or n_u == 0:
        return S, dict(status=f"INSUFFICIENT SUPPORT (risk denominator {n_r}, initially incorrect {n_u})", n_risk=n_r, n_use=n_u)
    F = S[S.risk_rate <= ALPHA].copy()
    F = F.sort_values(["use_rate", "risk_rate", "order"], ascending=[False, True, True])
    b = F.iloc[0]
    st = "USABLE EMPIRICAL CANDIDATE" if b.k_use > 0 else "NO USEFUL FEASIBLE RULE"
    return S, dict(status=st, params=b.params, **{k: b[k] for k in ("opened", "k_risk", "n_risk", "risk_rate", "risk_cp95", "k_use", "n_use", "use_rate", "use_cp95")},
                   distinct_sets=len(S), feasible_sets=len(F))


def stage_select(a):
    if (OUT / "frozen_p12_config.json").exists():
        sys.exit("frozen_p12_config.json exists; not overwritten")
    U = pd.read_csv(OUT / "p12_calibration_units.csv", low_memory=False)
    out, allsets = {}, []
    for fam, ax, init in (("A_FAIL", "A sound", "yes"), ("A_PASS", "A sound", "no"), ("AVB_FAIL", "AVB", "yes"), ("AVB_PASS", "AVB", "no")):
        q, risk = fam_rows(U, ax, init)
        S, sel = select_family(q, risk, fam); out[fam] = sel
        allsets.append(S.assign(family=fam))
        for nm, m in (("always open", pd.Series(True, index=q.index)), ("always closed", pd.Series(False, index=q.index))):
            out[f"{fam} diagnostic: {nm}"] = stat_row(nm, m, risk)
    for fam, init, verdict in (("V_FAIL", "yes", "contradicts"), ("V_PASS", "no", "describes")):
        q, risk = fam_rows(U, "V", init); s = stat_row(f"verdict {verdict}", q.vcap == verdict, risk)
        s["status"] = (f"INSUFFICIENT SUPPORT (risk denominator {s['n_risk']}, initially incorrect {s['n_use']})" if s["n_risk"] < MIN_N or s["n_use"] == 0
                       else ("MEETS CRITERION" if s["risk_rate"] <= ALPHA else f"FAILS CRITERION ({s['k_risk']}/{s['n_risk']} = {s['risk_rate']})"))
        out[fam] = s
    for fam in ("A_SPEECH_FAIL (Whisper absence)", "A_SPEECH_PASS (word heard, p >= .5)"):
        out[fam] = dict(status="UNSUPPORTED: no P01/P02 speech events (HD-EPIC has no speech); branch falls back to media only", n_risk=0, n_use=0)
    pd.concat(allsets).to_csv(OUT / "p12_enumerated_admission_sets.csv", index=False)
    cfg = {}
    for fam, s in out.items():
        if "diagnostic" in fam:
            continue
        use = s["status"].startswith(("USABLE", "MEETS"))
        cfg[fam] = dict(active=use, params=s.get("params"), status=s["status"], fallback=None if use else "media-only label")
    json.dump(dict(written=time.strftime("%Y-%m-%dT%H:%M:%S"), calibration="HD-EPIC P01/P02 only", config=cfg, selection=out, procedure=__doc__,
                   script_md5=hashlib.md5(open(__file__).read().encode()).hexdigest(), evaluation_rows_read=False), open(OUT / "frozen_p12_config.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(pd.DataFrame([dict(family=k, **{kk: v for kk, v in s.items() if kk not in ("order",)}) for k, s in out.items()]).to_string(index=False))


# ------------------------------------------------------------------ evaluation
def eval_units():
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False)
    U = U[(U.group == U.dataset) & U.dataset.isin(EVAL_DS) & U.axis.isin(["A", "V", "AVB", "TCC", "TCR"])]
    piv = {c: U[U.cond == c].set_index(["dataset", "unit"]) for c in ("row2", "row4", "row5")}
    b = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)].rename(columns={"pred": "initial", "gt_y": "gt"})
    S = pd.read_csv(RUNS / "gate_pilot_1106/split.csv"); b = b.merge(S[["dataset", "item", "portion"]], on=["dataset", "item"], how="left")
    for c, nm in (("row2", "one_call"), ("row4", "always_shown"), ("row5", "original_gate")):
        b[nm] = [piv[c].pred.get((d, u)) if piv[c].status.get((d, u)) == "scored" else "" for d, u in zip(b.dataset, b.unit)]
    F = pd.read_csv(RUNS / "gate_redesign_round2/unit_features.csv", low_memory=False).drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"])
    for c in ("family", "flam_max", "vcap", "off", "prob", "p0"):
        b[c] = [F[c].get((d, u)) if c in F else None for d, u in zip(b.dataset, b.unit)]
    b["branch"] = np.where(b.initial == "yes", "FAIL", "PASS"); b["group"] = b.dataset.map(GROUP)
    return b


def open_rule(cfg, r):
    """-> (opened, branch_key, fallback_reason)"""
    if r.axis in ("TCC", "TCR"):
        return False, "TC/TR (no gate)", ""
    init = r.initial
    if r.axis == "A":
        if r.family == "A speech":
            k = "A_SPEECH_FAIL (Whisper absence)" if init == "yes" else "A_SPEECH_PASS (word heard, p >= .5)"
            return False, k, "unsupported on P01/P02 -> media only"
        if r.family != "A sound" or pd.isna(r.flam_max):
            return False, "A (no FLAM feature)", "no feature -> media only"
        k = "A_FAIL" if init == "yes" else "A_PASS"; c = cfg[k]
        if not c["active"]:
            return False, k, f"{c['status']} -> media only"
        t = c["params"][1]
        return (bool(r.flam_max < t) if init == "yes" else bool(r.flam_max >= t)), k, ""
    if r.axis == "V":
        k = "V_FAIL" if init == "yes" else "V_PASS"; c = cfg[k]
        if not c["active"]:
            return False, k, f"{c['status']} -> media only"
        return (r.vcap == ("contradicts" if init == "yes" else "describes")), k, ""
    if r.axis == "AVB":
        k = "AVB_FAIL" if init == "yes" else "AVB_PASS"; c = cfg[k]
        if pd.isna(r.off):
            return False, k, "no Synchformer feature -> media only"
        if not c["active"]:
            return False, k, f"{c['status']} -> media only"
        p = c["params"]
        return (bool(r.off >= p[1] and r.prob >= p[3]) if init == "yes" else bool(r.off <= p[1] and r.prob >= p[3])), k, ""
    return False, "", ""


def reuse_index():
    f = OUT / "reuse_index.json"
    if f.exists():
        return json.load(open(f))
    import obs_judge_1028 as O
    idx = dict(json.load(open(RUNS / "av_full_1107/reuse_index.json")))
    for d in (RUNS / "av_full_1107/calls", RUNS / "a_sound_ltx_exp_1107/calls", RUNS / "flam3_1108/calls", RUNS / "bidir_full_1107/calls", OUT / "calls"):
        for p in d.glob("*.json"):
            r = json.load(open(p))
            if r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5 and r.get("model") == "gemini-3.6-flash" and r.get("thinking") == "high":
                idx.setdefault(r["user_md5"], str(p))
    json.dump(idx, open(f, "w")); return idx


def payload(ds, ax, item, events):
    import bidir_full_1107 as BF
    return BF.payload(ds, ax, item, {e: ("A sound" if ax == "A" else ax) for e in events})


def stage_plan(a):
    import obs_judge_1028 as O
    import gen2k25_stage2_1104  # noqa: F401
    fz = json.load(open(OUT / "frozen_p12_config.json")); cfg = fz["config"]
    M = eval_units(); res = [open_rule(cfg, r) for r in M.itertuples()]
    M["opened"] = [x[0] for x in res]; M["branch_key"] = [x[1] for x in res]; M["fallback"] = [x[2] for x in res]
    M.to_csv(OUT / "eval_manifest.csv", index=False)
    idx = reuse_index(); (OUT / "prompts").mkdir(exist_ok=True); rows = []
    for (ds, item, ax), g in M[M.opened].groupby(["dataset", "item", "axis"]):
        text, src = payload(ds, ax, item, list(g.event)); uid = f"{src}|{item}|{ax}"
        if text is None:
            rows.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="missing payload")); continue
        cc = O.build_call(dict(set="PC", source=src, uid=uid, item_id=item, axis=ax, variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text}))
        if cc is None:
            rows.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="no stage-1 anchor")); continue
        md5 = hashlib.md5(cc["user"].encode()).hexdigest()
        json.dump(dict(uid=uid, item=item, axis=ax, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5), open(OUT / "prompts" / f"{md5}.json", "w"))
        rows.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), user_md5=md5, prompt_chars=len(cc["system"]) + len(cc["user"]),
                         reuse_file=idx.get(md5, ""), action="reuse (exact prompt match)" if md5 in idx else "new call"))
    CP = pd.DataFrame(rows); CP.to_csv(OUT / "call_plan.csv", index=False)
    b = json.load(open(RUNS / "bidir_full_1107/estimate_basis.json")); new = CP[CP.action == "new call"].drop_duplicates("user_md5")
    est = dict(calls=len(CP), reused=int((CP.action == "reuse (exact prompt match)").sum()), new_calls=len(new), missing_payload=int((CP.action == "missing payload").sum()),
               no_anchor=int((CP.action == "no stage-1 anchor").sum()),
               est_usd_list=round(new.prompt_chars.sum() / b["chars_per_token"] / 1e6 * 1.5 + b["output_tokens_median"] * len(new) / 1e6 * 7.5, 2) if len(new) else 0)
    json.dump(est, open(OUT / "estimate.json", "w"), indent=1)
    print(M.groupby(["dataset", "axis", "branch_key"]).opened.agg(["sum", "size"]).to_string()); print(CP.groupby(["dataset", "axis", "action"]).size().to_string()); print(est)


def stage_run(a):
    import obs_judge_1028 as O
    from google import genai
    CP = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = CP[CP.action == "new call"].drop_duplicates("user_md5"); (OUT / "calls").mkdir(exist_ok=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"]); t0 = time.time(); n = collections.Counter()

    def one(c):
        f = OUT / "calls" / f"PC__{c.user_md5}.json"
        if f.exists():
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.user_md5}.json")); r = dict(uid=c.uid, obs={})
        try:
            parsed, raw = O.call(client, "gemini-3.6-flash", dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
            rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], anchor=O.anchor_entries(c.uid.split("|")[0], c.item, c.axis))
        except Exception as e:
            rec = dict(status="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        rec.update(uid=c.uid, model="gemini-3.6-flash", thinking="high", rules_md5=O.OBS_RULES_MD5, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(f, "w"), default=str); return rec["status"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 25 == 0 or i + 1 == len(todo):
                print(f"[p12] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), workers=a.workers), open(OUT / "run_info.json", "w"), indent=1)


def stage_score(a):
    import audit_1106 as AU, obs_judge_1028 as O, bidir_full_1107 as BF
    M = pd.read_csv(OUT / "eval_manifest.csv", low_memory=False); CP = pd.read_csv(OUT / "call_plan.csv").fillna("")
    cmap = {(r.dataset, r.item, r.axis): r for r in CP.itertuples()}; lab, src = [], []
    for x in M.to_dict("records"):
        if not x["opened"]:
            lab.append(x["initial"]); src.append("closed: media-only label" + (f" ({x['fallback']})" if isinstance(x["fallback"], str) and x["fallback"] else "")); continue
        c = cmap.get((x["dataset"], x["item"], x["axis"])); rec = None
        if c is not None and c.action in ("new call", "reuse (exact prompt match)"):
            f = Path(c.reuse_file) if c.action.startswith("reuse") else OUT / "calls" / f"PC__{c.user_md5}.json"
            rec = json.load(open(f)) if f.exists() else None
            if rec is not None and "anchor" not in rec:
                rec["anchor"] = O.anchor_entries(c.uid.split("|")[0], x["item"], x["axis"])
        rec = rec if rec and rec.get("status") == "ok" else None
        l, st = AU.s2_event(rec, x["axis"], None if x["axis"] == "TCR" else x["event"]); ok = st == "ok" and l in ("yes", "no")
        lab.append(l if ok else ""); src.append(("open: reused call" if c.action.startswith("reuse") else "open: new call") if ok else f"open: missing ({st}; {getattr(c, 'action', 'no call')})")
    M["p12_config"] = lab; M["label_source"] = src; M.to_csv(OUT / "eval_unit_results.csv", index=False)
    pipes = [("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("original_gate", "original paper gate"), ("p12_config", "P01/P02-calibrated gate")]
    rows, pc = [], []
    for kk in (("dataset", "axis"), ("group", "axis"), ("dataset", "portion", "axis")):
        for key, q in M.groupby(list(kk)):
            common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c, _ in pipes])]
            for sc, D in (("identical common units", common), ("condition-specific", q)):
                for col, nm in pipes:
                    h = D[D[col].isin(["yes", "no"])]
                    rows.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), scope=sc, pipeline=nm, eligible=len(D), excluded_missing=len(D) - len(h),
                                     opened=int(D.opened.sum()) if col == "p12_config" else None, **BF.metrics(h["gt"], h[col])))
            for ref, rn in pipes[:4]:
                o_, n_ = common[ref] == common["gt"], common["p12_config"] == common["gt"]; op = common.opened.astype(bool)
                pc.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), vs=rn, common_units=len(common), opened=int(op.sum()),
                               corrections_opened=int((~o_ & n_ & op).sum()), corruptions_opened=int((o_ & ~n_ & op).sum()),
                               corrections_closed=int((~o_ & n_ & ~op).sum()), corruptions_closed=int((o_ & ~n_ & ~op).sum())))
    pd.DataFrame(rows).to_csv(OUT / "eval_metrics.csv", index=False); pd.DataFrame(pc).to_csv(OUT / "eval_paired_changes.csv", index=False)
    cov = M.groupby(["dataset", "axis", "branch_key"]).agg(units=("unit", "size"), opened=("opened", "sum"),
                                                          fallback_media_only=("fallback", lambda s: int(s.fillna("").astype(str).str.len().gt(0).sum())),
                                                          missing_output=("p12_config", lambda s: int((s == "").sum()))).reset_index()
    cov.to_csv(OUT / "eval_coverage.csv", index=False)
    us = [json.load(open(f)).get("usage") or {} for f in (OUT / "calls").glob("PC__*.json")] if (OUT / "calls").exists() else []
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    json.dump(dict(new_calls=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3)), open(OUT / "cost.json", "w"), indent=1)
    print(M.label_source.str.replace(r"\(.*", "", regex=True).value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["build", "select", "plan", "run", "score"]); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
