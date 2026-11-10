#!/usr/bin/env python3
"""Sanjoy control experiments (2026-11-08) on the final_benchmark_1108 scope.
  Direct gated decision (no Stage-2 MLLM): Direct-original, Direct-combined-v2.
  No-tool second pass (text-only Stage 2, tool evidence removed): B1-all, B2-original, B2-combined-v2.
Reference (read only): evaluation/ablation/gepa_stage2/runs/obsval_1028/final_benchmark_1108/ (unit_results_final.csv, calibration_v2,
tables) and the code that produced it (final_benchmark_1108.py, final_cov_1108.py, obs_judge_1028.py, ...). Nothing outside this
analysis directory is written. The FLAM+Synchformer-only ablation is excluded everywhere.
No-tool request = obs_judge_1028.build_call with the observation text replaced by overnight_1104.NOTOOL_TEXT (the project's existing
no-tool two-stage template, frozen 2026-11-04); system prompt, generation prompt, axis criteria, OBS_RULES, Stage-1 block, schema,
model settings and media (none) unchanged. One request per (source, item, axis) with the established Stage-1 anchor (all non-gated
Stage-1 events of that axis, corrected anchor builder) - identical for B1, B2-original and B2-combined-v2, so one call serves all three.
  python scripts/sanjoy_controls.py verify | freeze | plan | run | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, glob, hashlib, json, os, re, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path((_tp.WORKSPACE))
GS = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2"   # portable: code dir of this checkout
sys.path.insert(0, str(GS)); sys.path.insert(0, str(GS.parent))
REF = GS / "runs/obsval_1028/final_benchmark_1108"
OUT = _tp.out_dir("sanjoy_two_baselines_2026-11-08")   # portable: $T2AV_OUT_DIR/<name>
CALLS, PROMPTS = OUT / "calls", OUT / "prompts"
MODEL, MAXTRY = "gemini-3.6-flash", 3
BILL = re.compile(r"spending cap|billing|exceeded its monthly", re.I)
EVSRC = {"220 LTX": "g220ltx", "220 MOVA": "g220mova", "149 LTX": "g149", "2k_25 LTX": "g2k25", "MOVA390": "m390", "P03-P09": "hm_p3p9"}
METHODS = [("initial", "Media-only"), ("one_call", "One-call media+tools"), ("always_shown", "Two-stage always-shown"),
           ("original_gate", "Original gated two-stage"), ("combined", "Combined gated two-stage (v2)"),
           ("direct_orig", "Direct-original"), ("direct_comb", "Direct-combined-v2"),
           ("b1", "No-tool B1-all"), ("b2_orig", "No-tool B2-original"), ("b2_comb", "No-tool B2-combined-v2")]
FIVE = [m for m, _ in METHODS[:5]]
NAME = dict(METHODS)
HIST = [REF / "unit_results_final.csv", REF / "units_all_conditions.csv", REF / "calibration_v2/frozen_p12_config.json",
        GS / "runs/obsval_1028/p12_calib_1108/frozen_p12_config.json"] + sorted((REF / "tables").glob("*.csv"))
_M = {}


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def setup():
    if not _M:
        import final_benchmark_1108 as FB
        M = FB.setup(); _M.update(M); _M["FB"] = FB
    return _M


def load_units():
    U = pd.read_csv(REF / "unit_results_final.csv", low_memory=False)
    U["event_key"] = np.where(U.axis == "TCR", "", U.event.astype(str))
    return U


def metrics(y, p):
    import comprehensive_report_1108 as CR
    return CR.metrics(y, p)


# ------------------------------------------------------------------ verify
def stage_verify(a):
    (OUT / "provenance").mkdir(exist_ok=True)
    before = {str(p): md5f(p) for p in HIST}
    f = OUT / "provenance/historical_md5_before.json"
    if not f.exists():
        json.dump(before, open(f, "w"), indent=1)
    U = load_units()
    # five-method continuity table reproduced from the unit file with the same metric function
    T = U.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind; T = pd.concat([T, TA])
    ref = pd.read_csv(REF / "tables/continuity_five_method_common_subset.csv")
    refm = {"media only": "initial", "one call plus tools": "one_call", "always shown": "always_shown", "original paper gate": "original_gate",
            "combined gate (v2 frozen)": "combined"}
    rows, bad = [], 0
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        c5 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in FIVE])]
        for r in ref[(ref.group == g) & (ref.axis == ax) & ref.method.isin(list(refm))].itertuples():
            m = metrics(c5["gt"], c5[refm[r.method]])
            same = m["N"] == r.N and all((np.isnan(m[k]) and np.isnan(getattr(r, k))) or abs(m[k] - getattr(r, k)) < 1e-12
                                         for k in ("accuracy", "macro_F1", "balanced_accuracy", "FAIL_recall", "PASS_recall", "FA_rate"))
            bad += not same
            rows.append(dict(group=g, axis=ax, method=r.method, N_ref=r.N, N_new=m["N"], acc_ref=r.accuracy, acc_new=m["accuracy"], identical=same))
    pd.DataFrame(rows).to_csv(OUT / "provenance/five_method_reproduction.csv", index=False)
    # Stage-2 modality: every gated / always-shown record used is text only (media None) and prompts carry no media
    med = collections.Counter()
    for st in ("G4", "G5", "GA4", "HG4", "HG5", "HA4", "HMB4", "HMB5", "K4", "K5", "M4", "HN", "GN"):
        for p in glob.glob(str(GS / f"runs/obsval_1028/calls/gen_tool_text/{st}__*.json"))[:400]:
            r = json.load(open(p))
            if r.get("status") == "ok":
                med[(st, str(r.get("media")))] += 1
    for d in ("p12_calib_1108/calls", "avb_anchorfix_1108/calls"):
        for p in glob.glob(str(GS / f"runs/obsval_1028/{d}/*.json"))[:200]:
            r = json.load(open(p)); med[(d, "user prompt only (runner passes media=None)")] += 1
    json.dump(dict(five_method_mismatches=bad, five_method_rows=len(rows), stage2_media={f"{k[0]}|{k[1]}": v for k, v in med.items()},
                   note="obs_judge_1028.build_call: media from obs_block; text observations -> media None; p12 / AF / final_cov / final_benchmark runners call O.call with media=None"),
              open(OUT / "provenance/verification.json", "w"), indent=1)
    print("five-method continuity rows", len(rows), "mismatches", bad); print(dict(med))


# ------------------------------------------------------------------ freeze
def gate_configs():
    v2 = json.load(open(REF / "calibration_v2/frozen_p12_config.json"))["config"]
    rule = json.load(open((_tp.DATA + "/tools/synchformer_action_1030/PREREGISTERED_RULE.json")))
    tf = json.load(open((_tp.DATA + "/tools/gen_evidence_1030/flam_threshold.json")))["T_flam"]
    return v2, rule, tf


def stage_freeze(a):
    import overnight_1104 as ON, obs_judge_1028 as O
    v2, rule, tf = gate_configs()
    f = OUT / "config/frozen_config.json"
    if f.exists():
        print("frozen config exists; kept"); return
    cfg = dict(written=time.strftime("%Y-%m-%dT%H:%M:%S"), reference=str(REF), model=MODEL, thinking="high", temperature=0.0, seed=42,
               response_mime_type="application/json", schema="run_two_stage.SCHEMA[axis] (unchanged)", media="none (text only)",
               obs_rules_md5=O.OBS_RULES_MD5, notool_observation_text=ON.NOTOOL_TEXT, notool_template_source="overnight_1104.NOTOOL_TEXT (sets HN / GN, 2026-11-04)",
               request_grouping="one request per (source, item, axis); targets = obs_judge_1028.anchor_entries (all non-gated Stage-1 events, corrected anchor builder)",
               variants=dict(B1="every (dataset, item, axis) with >= 1 valid Stage-1 unit", B2_original="units with orig_opened; closed -> Stage 1",
                             B2_combined_v2="units with comb_opened (v2); A speech follows the original gate as in the combined gate; closed -> Stage 1"),
               label_policy="established Stage-2 extraction (audit_1106.s2_event: per-event label); failed / missing outputs -> missing (no fill)",
               original_gate=dict(A_sound=f"FLAM line admitted when FLAM max < T_flam = {tf} -> FAIL direction",
                                  A_speech="Whisper transcript admitted when a target word is heard (kept segments); event whose own target word is heard -> PASS direction; other speech events: ambiguous (retain)",
                                  V="row opens when any GT event's caption check says contradicts; contradicts -> FAIL direction; describes / not_mentioned: no directional rule (retain)",
                                  AVB=f"pre-registered rule (|offset| >= {rule['T']} s and p >= {rule['P']} on the strongest reading) -> AVB FAIL (row level, every binding event of the opened row; historical hd_stage2_1101 row5_rule)",
                                  TC_TR="closed (media only)"),
               combined_v2=dict(config=v2, mapping="opened initial PASS (FAIL-evidence branch) -> FAIL; opened initial FAIL (PASS-evidence branch) -> PASS; A speech -> original-gate direct mapping (inherited)"),
               excluded="FLAM+Synchformer-only ablation")
    json.dump(cfg, open(f, "w"), indent=1, default=str)
    (OUT / "config/notool_prompt_template.txt").write_text(
        "SYSTEM: new_eval.build_system_prompt('none','none','none', single_axis=True)  [identical to gated Stage 2]\n\nUSER (blocks joined by blank lines):\n"
        "1. Prompt of the clip being evaluated:\\n<generated prompt>\n2. <axis criteria, adapter.CRITERIA>\n3. OBS_RULES (unchanged, md5 " + O.OBS_RULES_MD5 + "):\n"
        + O.OBS_RULES.strip() + "\n4. <Stage 1 (media only) block, run_two_stage.fmt_block(axis, anchor entries)>\n5. " + ON.NOTOOL_TEXT + "\n\nSCHEMA: run_two_stage.SCHEMA[axis]\n")
    print("frozen")


# ------------------------------------------------------------------ plan
def requests(U):
    M = setup(); O = M["O"]
    s = U[U.scored_row1]
    out = []
    for (ds, item, ax), g in s.groupby(["dataset", "item", "axis"]):
        src = "hm_ma39" if (ds == "P03-P09" and ax == "A") else EVSRC[ds]
        import overnight_1104 as ON
        r = dict(set="NT", source=src, uid=f"{src}|{item}|{ax}", item_id=item, axis=ax, variant="control", gt={}, clip=item, cond="gen_tool_text", obs={"text": ON.NOTOOL_TEXT})
        cc = O.build_call(r)
        out.append((ds, item, ax, src, g, cc))
    return out


def stage_plan(a):
    M = setup(); O, FC = M["O"], M["FC"]
    U = load_units(); PROMPTS.mkdir(exist_ok=True)
    idx = {}
    for st in ("HN", "GN"):
        for p in glob.glob(str(GS / f"runs/obsval_1028/calls/gen_tool_text/{st}__*.json")):
            r = json.load(open(p))
            if r.get("status") == "ok" and r.get("user_md5") and r.get("rules_md5") == O.OBS_RULES_MD5 and r.get("model") == MODEL and r.get("thinking") == "high":
                idx[r["user_md5"]] = p
    rows = []
    for ds, item, ax, src, g, cc in requests(U):
        units = len(g); o1 = int(g.orig_opened.astype(bool).sum()); o2 = int(g.comb_opened.astype(bool).sum())
        if cc is None:
            rows.append(dict(dataset=ds, item=item, axis=ax, source=src, units=units, units_orig_open=o1, units_comb_open=o2, action="no stage-1 anchor")); continue
        md5 = hashlib.md5((cc["system"] + "\x00" + cc["user"] + "\x00" + json.dumps(cc["schema"], sort_keys=True)).encode()).hexdigest()
        umd5 = hashlib.md5(cc["user"].encode()).hexdigest()
        need = [e["event_id"] for e in cc["anchor"]] if ax != "TCR" else None
        reuse = ""
        if umd5 in idx:
            rec = json.load(open(idx[umd5])); rec.setdefault("anchor", cc["anchor"])
            if FC.complete(rec, ax, need):
                reuse = idx[umd5]
        key = f"NT__{md5}"
        if not reuse:
            json.dump(dict(uid=f"{src}|{item}|{ax}", item=item, axis=ax, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=umd5,
                           request_md5=md5, anchor=cc["anchor"], need=need), open(PROMPTS / f"{key}.json", "w"))
        rows.append(dict(dataset=ds, item=item, axis=ax, source=src, units=units, units_orig_open=o1, units_comb_open=o2, request_md5=md5, user_md5=umd5, key=key,
                         prompt_chars=len(cc["system"]) + len(cc["user"]), anchor_events=len(cc["anchor"]),
                         reuse_file=reuse, action="reuse (identical request, HN/GN cache)" if reuse else "new call",
                         slap_note="new no-tool request (not a coverage repair of the failing gated prompt)" if "slap-then-help-then-thumbs_up__order" in item and ds == "220 MOVA" and ax == "V" else ""))
    P = pd.DataFrame(rows); P.to_csv(OUT / "config/call_plan.csv", index=False)
    assert P.dropna(subset=["request_md5"]).request_md5.is_unique or True
    # usage-based cost estimate (HN / GN no-tool records)
    us = []
    for p in list(idx.values()):
        u = json.load(open(p)).get("usage") or {}
        if u.get("prompt_token_count"):
            us.append(u["prompt_token_count"] * 1.5e-6 + ((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)) * 7.5e-6)
    new = P[P.action == "new call"]
    q = np.percentile(us, [25, 50, 75]) if us else [np.nan] * 3
    summ = dict(units_valid_stage1=int(U.scored_row1.sum()),
                B1=dict(units=int(P.units.sum()), distinct_requests=int(P.request_md5.notna().sum())),
                B2_original=dict(units=int(P.units_orig_open.sum()), distinct_requests=int(((P.units_orig_open > 0) & P.request_md5.notna()).sum())),
                B2_combined_v2=dict(units=int(P.units_comb_open.sum()), distinct_requests=int(((P.units_comb_open > 0) & P.request_md5.notna()).sum())),
                distinct_requests_all_variants=int(P.request_md5.nunique()), reused_identical=int((P.action != "new call").sum() - (P.action == "no stage-1 anchor").sum()),
                new_calls=len(new), no_anchor=int((P.action == "no stage-1 anchor").sum()),
                est_usd_per_call_quartiles=[round(x, 5) for x in q], est_total_usd_median=round(len(new) * q[1], 2),
                est_total_usd_iqr=[round(len(new) * q[0], 2), round(len(new) * q[2], 2)], basis=f"{len(us)} HN/GN no-tool records (usage)",
                note="B1, B2-original and B2-combined-v2 requests are byte-identical per (source, item, axis); B2 units are a subset of B1 requests")
    json.dump(summ, open(OUT / "config/plan_summary.json", "w"), indent=1)
    print(json.dumps(summ, indent=1)); print(P.groupby(["dataset", "axis", "action"]).size().unstack(fill_value=0))


# ------------------------------------------------------------------ run
def stage_run(a):
    M = setup(); O, FC = M["O"], M["FC"]
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    import threading
    P = pd.read_csv(OUT / "config/call_plan.csv").fillna(""); todo = P[P.action == "new call"].drop_duplicates("key")
    CALLS.mkdir(exist_ok=True)
    if (OUT / "HOLD").exists():
        sys.exit("HOLD present")
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); stop = threading.Event(); n = collections.Counter(); t0 = time.time()

    def one(c):
        if stop.is_set():
            return "skipped (hold)"
        f = CALLS / f"{c.key}.json"
        att = json.load(open(f))["attempts"] if f.exists() else []
        if any(x.get("complete") for x in att) or len(att) >= MAXTRY:
            return "cached"
        p = json.load(open(PROMPTS / f"{c.key}.json"))
        while len(att) < MAXTRY and not stop.is_set():
            r = dict(uid=c.uid if hasattr(c, "uid") else p["uid"], obs={})
            try:
                parsed, raw = O.call(client, MODEL, dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
                rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"], request_md5=p["request_md5"], anchor=p["anchor"])
                rec["complete"] = FC.complete(rec, p["axis"], p["need"])
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                rec = dict(status="error", error=msg[:2000], complete=False, usage=r.get("_usage"), user_md5=p["user_md5"], request_md5=p["request_md5"])
                if BILL.search(msg):
                    stop.set(); (OUT / "HOLD").write_text(f"HOLD {time.strftime('%Y-%m-%dT%H:%M:%S')}: billing / spending-cap error; no key rotation\n")
            rec.update(uid=p["uid"], model=MODEL, thinking="high", rules_md5=O.OBS_RULES_MD5, attempt=len(att) + 1, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
            att.append(rec); json.dump(dict(key=c.key, uid=p["uid"], attempts=att), open(f, "w"), default=str)
            if rec.get("complete") or (rec["status"] == "error" and BILL.search(rec.get("error", ""))):
                break
        return "ok" if att and att[-1].get("complete") else ("hold" if stop.is_set() else "unresolved")
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 100 == 0 or i + 1 == len(todo):
                print(f"[sanjoy] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), hold=stop.is_set(), time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(OUT / f"provenance/run_info_{time.strftime('%H%M%S')}.json", "w"), indent=1)
    print("[DONE]", dict(n), "HOLD" if stop.is_set() else "")


# ------------------------------------------------------------------ direct decisions
def norm(t):
    return re.findall(r"[a-z']+", (t or "").lower())


def direct_labels(U):
    """returns direct_orig, direct_comb labels and per-unit reason codes (no MLLM)."""
    M = setup(); G = M["G"]; FB = M["FB"]
    import p12_calib_1108 as P12
    v2, rule, tf = gate_configs()
    IT = FB.items_all()
    heard_cache = {}

    def heard(ds, item, ev):
        k = (ds, item)
        if k not in heard_cache:
            rec = G.evidence(EVSRC[ds], item)
            segs = [s for s in (rec or {}).get("whisper", {}).get("segments", []) if s["no_speech_prob"] < 0.5]
            heard_cache[k] = {w for s in segs for w in norm(s["text"])}
        e = IT[FB.PSET[ds]][item]["events"][int(ev.split("_")[1]) - 1]
        return bool(set(norm(e.get("text", ""))) & heard_cache[k])
    do, dor, dc, dcr = [], [], [], []
    for r in U.itertuples():
        ini = r.initial
        if not r.scored_row1:
            do.append(""); dor.append("no valid Stage-1 label"); dc.append(""); dcr.append("no valid Stage-1 label"); continue
        # ---- original gate
        if r.axis in ("TCC", "TCR"):
            lab, why = ini, "closed (TC/TR: no gate)"
        elif not bool(r.orig_opened):
            lab, why = ini, "closed"
        elif r.axis == "A":
            if r.family == "A sound":
                if pd.notna(r.flam_max) and r.flam_max < tf:
                    lab, why = ("no", "open: FLAM < T_flam (FAIL dir) -> FAIL") if ini == "yes" else ("no", "open: FLAM < T_flam (FAIL dir) supports Stage 1")
                else:
                    lab, why = ini, "open: no admitted FLAM evidence for this event (unsupported, retained)"
            elif r.family == "A speech":
                if heard(r.dataset, r.item, r.event):
                    lab, why = ("yes", "open: target word heard (PASS dir) -> PASS") if ini == "no" else ("yes", "open: target word heard (PASS dir) supports Stage 1")
                else:
                    lab, why = ini, "open: Whisper admitted, target word not heard (ambiguous, retained)"
            else:
                lab, why = ini, "open: unknown A family (retained)"
        elif r.axis == "V":
            if r.vcap == "contradicts":
                lab, why = ("no", "open: caption contradicts (FAIL dir) -> FAIL") if ini == "yes" else ("no", "open: caption contradicts (FAIL dir) supports Stage 1")
            else:
                lab, why = ini, f"open: no directional verdict for this event ({r.vcap}) (unsupported, retained)"
        elif r.axis == "AVB":
            own = pd.notna(r.off) and r.off >= rule["T"] - 1e-9 and r.prob >= rule["P"] - 1e-9
            tag = "own reading meets rule" if own else "row-level rule, not this event's reading"
            lab, why = ("no", f"open: Synchformer rule AVB->FAIL ({tag}) -> FAIL") if ini == "yes" else ("no", f"open: Synchformer rule AVB->FAIL ({tag}) supports Stage 1")
        else:
            lab, why = ini, "closed"
        do.append(lab); dor.append(why)
        # ---- combined v2
        if r.axis in ("TCC", "TCR"):
            lab2, why2 = ini, "closed (TC/TR: no gate)"
        elif r.axis == "A" and r.family == "A speech":
            lab2, why2 = lab, "A speech: inherited original gate -> " + why
        else:
            op, bk, fb = P12.open_rule(v2, r)
            if not op:
                lab2, why2 = ini, "closed" + (f" ({fb})" if fb else "")
            else:
                lab2, why2 = ("no" if ini == "yes" else "yes"), f"open: {bk} -> {'FAIL' if ini == 'yes' else 'PASS'}"
        dc.append(lab2); dcr.append(why2)
    return do, dor, dc, dcr


# ------------------------------------------------------------------ score
def stage_score(a):
    M = setup(); AU = M["AU"]
    U = load_units()
    U["direct_orig"], U["direct_orig_why"], U["direct_comb"], U["direct_comb_why"] = direct_labels(U)
    # consistency: Direct-combined openings must equal the stored v2 openings (non-speech)
    chk = U[U.scored_row1 & U.axis.isin(["A", "V", "AVB"]) & (U.family != "A speech")]
    open_direct = chk.direct_comb_why.str.startswith("open")
    mism = int((open_direct != chk.comb_opened.astype(bool)).sum())
    P = pd.read_csv(OUT / "config/call_plan.csv").fillna("")
    recs = {}
    for r in P.itertuples():
        rec = None
        if r.action.startswith("reuse"):
            rec = json.load(open(r.reuse_file)); rec = rec if rec.get("status") == "ok" else None
        elif r.action == "new call" and (CALLS / f"{r.key}.json").exists():
            good = [x for x in json.load(open(CALLS / f"{r.key}.json"))["attempts"] if x.get("complete")]
            rec = good[-1] if good else None
        recs[(r.dataset, r["item"] if isinstance(r, dict) else r.item, r.axis)] = (rec, r.action)
    b1, b1why, keep_mis = [], [], 0
    for r in U.itertuples():
        if not r.scored_row1:
            b1.append(""); b1why.append("no valid Stage-1 label"); continue
        rec, act = recs.get((r.dataset, r.item, r.axis), (None, "no request"))
        l, st = AU.s2_event(rec, r.axis, None if r.axis == "TCR" else r.event)
        if st == "ok" and l in ("yes", "no"):
            b1.append(l); b1why.append("answered")
            if rec and r.axis != "TCR":
                for e in (rec.get("parsed") or {}).get("per_event", []):
                    if e.get("event_id") == r.event and str(e.get("reason", "")).startswith("KEEP") and l != r.initial:
                        keep_mis += 1
        else:
            b1.append(""); b1why.append(f"missing ({st}; {act})")
    U["b1"], U["b1_why"] = b1, b1why
    U["b2_orig"] = np.where(~U.scored_row1, "", np.where(U.orig_opened.astype(bool), U.b1, U.initial))
    U["b2_comb"] = np.where(~U.scored_row1, "", np.where(U.comb_opened.astype(bool), U.b1, U.initial))
    for c in ("direct_orig", "direct_comb", "b1", "b2_orig", "b2_comb"):
        U[c + "_cat"] = ["answered" if v in ("yes", "no") else (ic if ic != "answered" else "technical missing / failed output") for v, ic in zip(U[c], U.initial_cat)]
    keep = ["dataset", "batch", "group", "axis", "a_kind", "unit", "item", "event", "gt", "initial", "one_call", "always_shown", "original_gate", "combined",
            "direct_orig", "direct_orig_why", "direct_comb", "direct_comb_why", "b1", "b1_why", "b2_orig", "b2_comb", "orig_opened", "comb_opened", "family",
            "flam_max", "vcap", "off", "prob", "scored_row1"] + [c + "_cat" for c, _ in METHODS]
    U[keep].to_csv(OUT / "results/unit_predictions.csv", index=False)
    json.dump(dict(direct_comb_vs_stored_v2_openings_mismatch=mism, keep_reason_but_label_differs_from_stage1=keep_mis), open(OUT / "results/consistency_checks.json", "w"), indent=1)
    tables(U)
    print("v2 opening mismatches", mism, "KEEP/label mismatches", keep_mis)


def views(U):
    T = U.copy(); T["axis_view"] = T.axis
    TA = T[T.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind
    return pd.concat([T, TA], ignore_index=True)


def tables(U):
    T = views(U); cols = [m for m, _ in METHODS]; td = OUT / "tables"
    v1, v2, v3, v5, const, man = [], [], [], [], [], []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        c10 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in cols])]
        c5 = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in FIVE])]
        man += [dict(group=g, axis=ax, subset=s, dataset=d, unit=u) for s, h in (("ten-method common", c10), ("five-method common", c5)) for d, u in zip(h.dataset, h.unit)]
        for c in cols:
            b = dict(group=g, axis=ax, method=NAME[c]); val = q[q[c].isin(["yes", "no"])]
            v1.append(dict(b, view="1 per-method valid responses", coverage_of_gt_eligible=len(val) / len(q) if len(q) else np.nan, **metrics(val["gt"], val[c])))
            v2.append(dict(b, view="2 ten-method common subset", **metrics(c10["gt"], c10[c])))
            if c in FIVE:
                v5.append(dict(b, view="historical five-method common subset", **metrics(c5["gt"], c5[c])))
            cat = q[c + "_cat"]; ok = q[c].isin(["yes", "no"])
            v3.append(dict(b, view="3 fixed GT-eligible universe", gt_eligible=len(q), answered=int(ok.sum()), correct=int((ok & (q[c] == q["gt"])).sum()),
                           correct_over_gt_eligible=(ok & (q[c] == q["gt"])).sum() / len(q) if len(q) else np.nan, coverage=ok.mean() if len(q) else np.nan,
                           model_prerequisite_skip=int((cat == "model prerequisite skip").sum()), model_abstention=int((cat == "model abstention / no usable label").sum()),
                           technical_missing_failed=int((cat == "technical missing / failed output").sum())))
        for nm, h in (("ten-method common", c10), ("per-axis GT-eligible universe", q)):
            for lab, cn in (("yes", "constant-PASS"), ("no", "constant-FAIL")):
                const.append(dict(group=g, axis=ax, subset=nm, method=cn, **metrics(h["gt"], np.array([lab] * len(h)))))
    for nm, rows in (("view1_per_method_valid", v1), ("view2_ten_method_common", v2), ("view3_fixed_gt_eligible_universe", v3),
                     ("historical_five_method_common", v5), ("constant_baselines_diagnostic", const)):
        pd.DataFrame(rows).to_csv(td / f"{nm}.csv", index=False)
    pd.DataFrame(man).to_csv(OUT / "results/subset_manifests.csv", index=False)
    transitions(T); attribution(T); gate_open(T); direct_breakdown(U); examples(U); figures()


def trans_row(h, new, base="initial"):
    ini, fin, y = h[base], h[new], h["gt"]
    return dict(units=len(h), wrong_to_correct=int(((ini != y) & (fin == y)).sum()), correct_to_wrong=int(((ini == y) & (fin != y)).sum()),
                wrong_still_wrong=int(((ini != y) & (fin != y)).sum()), correct_still_correct=int(((ini == y) & (fin == y)).sum()),
                PASS_to_FAIL=int(((ini == "yes") & (fin == "no")).sum()), FAIL_to_PASS=int(((ini == "no") & (fin == "yes")).sum()),
                net_corrections=int(((ini != y) & (fin == y)).sum() - ((ini == y) & (fin != y)).sum()), revised=int((ini != fin).sum()))


def transitions(T):
    rows = []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        for c in ("always_shown", "original_gate", "combined", "direct_orig", "direct_comb", "b1", "b2_orig", "b2_comb", "one_call"):
            h = q[q.initial.isin(["yes", "no"]) & q[c].isin(["yes", "no"])]
            rows.append(dict(group=g, axis=ax, method=NAME[c], split="all", **trans_row(h, c)))
            for b, hb in h.groupby(np.where(h.initial == "yes", "initial PASS", "initial FAIL")):
                rows.append(dict(group=g, axis=ax, method=NAME[c], split=b, **trans_row(hb, c)))
            opc = {"original_gate": "orig_opened", "direct_orig": "orig_opened", "b2_orig": "orig_opened", "combined": "comb_opened", "direct_comb": "comb_opened", "b2_comb": "comb_opened"}.get(c)
            if opc:
                for nm, hb in (("gate open", h[h[opc].astype(bool)]), ("gate closed", h[~h[opc].astype(bool)])):
                    rows.append(dict(group=g, axis=ax, method=NAME[c], split=nm, **trans_row(hb, c)))
    pd.DataFrame(rows).to_csv(OUT / "tables/transitions_vs_stage1.csv", index=False)


def boot(h, a, b, n=2000, seed=20261108):
    """video-cluster bootstrap of accuracy(b) - accuracy(a) on matched units; clusters = (dataset, item)."""
    if not len(h):
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    cl = h.groupby(["dataset", "item"]).apply(lambda t: ((t[b] == t["gt"]).sum() - (t[a] == t["gt"]).sum(), len(t))).values
    d = np.array([x[0] for x in cl], float); m = np.array([x[1] for x in cl], float)
    est = d.sum() / m.sum(); bs = []
    for _ in range(n):
        i = rng.integers(0, len(d), len(d)); bs.append(d[i].sum() / m[i].sum())
    return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def attribution(T):
    comps = [("Q1", "direct_orig", "original_gate", "orig_opened"), ("Q1", "direct_comb", "combined", "comb_opened"),
             ("Q2", "b2_orig", "original_gate", "orig_opened"), ("Q2", "b2_comb", "combined", "comb_opened"),
             ("Q3", "initial", "b1", None), ("Q4", "always_shown", "original_gate", None), ("Q4", "always_shown", "combined", None)]
    rows = []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        for qn, a, b, opc in comps:
            m_ = q[q[a].isin(["yes", "no"]) & q[b].isin(["yes", "no"]) & q.initial.isin(["yes", "no"])]
            for nm, h in [("matched all", m_)] + ([("matched gate-open", m_[m_[opc].astype(bool)])] if opc else []):
                ca, cb = h[a] == h["gt"], h[b] == h["gt"]
                est, lo, hi = boot(h, a, b)
                ma, mb = metrics(h["gt"], h[a]), metrics(h["gt"], h[b])
                rows.append(dict(question=qn, group=g, axis=ax, comparison=f"{NAME[b]} vs {NAME[a]}", subset=nm, N=len(h), clusters=h.groupby(["dataset", "item"]).ngroups,
                                 acc_a=ma["accuracy"], acc_b=mb["accuracy"], bal_acc_a=ma["balanced_accuracy"], bal_acc_b=mb["balanced_accuracy"],
                                 FAIL_R_a=ma["FAIL_recall"], FAIL_R_b=mb["FAIL_recall"], both_correct=int((ca & cb).sum()), only_b_correct=int((~ca & cb).sum()),
                                 only_a_correct=int((ca & ~cb).sum()), both_wrong=int((~ca & ~cb).sum()), acc_diff_b_minus_a=est, ci95_lo=lo, ci95_hi=hi,
                                 N_gt_FAIL=int((h["gt"] == "no").sum())))
    pd.DataFrame(rows).to_csv(OUT / "tables/attribution_comparisons.csv", index=False)


def gate_open(T):
    rows = []
    for (g, ax), q in T.groupby(["group", "axis_view"]):
        for gate, opc, meths in (("original", "orig_opened", ("original_gate", "direct_orig", "b2_orig")), ("combined v2", "comb_opened", ("combined", "direct_comb", "b2_comb"))):
            h = q[q[opc].astype(bool) & q.initial.isin(["yes", "no"])]
            for c in ("initial",) + meths:
                hh = h[h[c].isin(["yes", "no"])]
                rows.append(dict(group=g, axis=ax, gate=gate, method=NAME[c], open_units=len(h), answered=len(hh), **{k: v for k, v in metrics(hh["gt"], hh[c]).items() if k in ("accuracy", "balanced_accuracy", "FAIL_recall", "PASS_recall", "FA_count", "N_gt_FAIL", "N_gt_PASS")}))
    pd.DataFrame(rows).to_csv(OUT / "tables/gate_open_analysis.csv", index=False)


def direct_breakdown(U):
    s = U[U.scored_row1].assign(a_kind=lambda t: t.a_kind.fillna(""))
    rows = []
    for meth, why in (("Direct-original", "direct_orig_why"), ("Direct-combined-v2", "direct_comb_why")):
        lab = "direct_orig" if meth == "Direct-original" else "direct_comb"
        x = s.assign(kind=s[why].str.replace(r" \([^)]*\)$", "", regex=True), branch=np.where(s.initial == "yes", "initial PASS", "initial FAIL"),
                     revised=s[lab] != s.initial, correct=s[lab] == s["gt"])
        for (g, ax, ak, br, k), h in x.groupby(["group", "axis", "a_kind", "branch", why]):
            rows.append(dict(method=meth, group=g, axis=ax, a_kind=ak, branch=br, rule_outcome=k, units=len(h), revised=int(h.revised.sum()),
                             revised_correct=int((h.revised & h.correct).sum()), revised_wrong=int((h.revised & ~h.correct).sum())))
    pd.DataFrame(rows).to_csv(OUT / "tables/direct_decision_breakdown.csv", index=False)


def examples(U):
    s = U[U.scored_row1 & U.axis.isin(["A", "V", "AVB"])]
    out = []
    for nm, cond in (("direct correct, gated wrong (combined)", (s.direct_comb == s["gt"]) & (s.combined != s["gt"]) & s.comb_opened.astype(bool)),
                     ("gated correct, direct wrong (combined)", (s.direct_comb != s["gt"]) & (s.combined == s["gt"]) & s.comb_opened.astype(bool)),
                     ("gated correct, no-tool wrong (combined open)", (s.combined == s["gt"]) & (s.b2_comb != s["gt"]) & s.b2_comb.isin(["yes", "no"]) & s.comb_opened.astype(bool)),
                     ("no-tool correct, gated wrong (combined open)", (s.combined != s["gt"]) & (s.b2_comb == s["gt"]) & s.comb_opened.astype(bool)),
                     ("B1 revision correct", (s.b1 != s.initial) & (s.b1 == s["gt"]) & s.b1.isin(["yes", "no"])),
                     ("B1 revision wrong", (s.b1 != s.initial) & (s.b1 != s["gt"]) & s.b1.isin(["yes", "no"]))):
        h = s[cond]
        for (g, ax), hh in h.groupby(["group", "axis"]):
            for r in hh.head(5).itertuples():
                out.append(dict(category=nm, group=g, dataset=r.dataset, axis=ax, unit=r.unit, item=r.item, event=r.event, a_kind=r.a_kind, gt=r.gt, stage1=r.initial,
                                flam_max=r.flam_max, caption_verdict=r.vcap, sync_abs_offset=r.off, sync_conf=r.prob, original_gate=r.original_gate, combined=r.combined,
                                direct_orig=r.direct_orig, direct_comb=r.direct_comb, direct_comb_rule=r.direct_comb_why, b1=r.b1, b2_orig=r.b2_orig, b2_comb=r.b2_comb))
    pd.DataFrame(out).to_csv(OUT / "examples/diagnostic_examples.csv", index=False)


def figures():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    V = pd.read_csv(OUT / "tables/view2_ten_method_common.csv")
    axes = ["A", "V", "AVB", "TCC", "TCR"]; groups = ["P03-P09", "LTX", "MOVA"]
    fig, ax = plt.subplots(len(groups), 1, figsize=(13, 10), sharey=True)
    for i, g in enumerate(groups):
        q = V[(V.group == g) & V.axis.isin(axes)]
        w = 0.08
        for j, (c, nm) in enumerate(METHODS):
            vals = [q[(q.axis == a) & (q.method == nm)].balanced_accuracy.mean() for a in axes]
            ax[i].bar(np.arange(len(axes)) + (j - 4.5) * w, vals, w, label=nm)
        ax[i].set_xticks(range(len(axes))); ax[i].set_xticklabels(axes); ax[i].set_title(f"{g}: balanced accuracy, ten-method common subset"); ax[i].set_ylim(0.3, 1)
    ax[0].legend(fontsize=7, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.45))
    fig.tight_layout(); fig.savefig(OUT / "figures/balanced_accuracy_ten_method_common.png", dpi=150); plt.close(fig)
    A = pd.read_csv(OUT / "tables/attribution_comparisons.csv")
    q = A[(A.subset == "matched all") & A.axis.isin(axes)]
    fig, ax = plt.subplots(1, 1, figsize=(13, 5))
    labels = [f"{r.question} {r.group} {r.axis}\n{r.comparison[:38]}" for r in q.itertuples()]
    ax.errorbar(range(len(q)), q.acc_diff_b_minus_a, yerr=[q.acc_diff_b_minus_a - q.ci95_lo, q.ci95_hi - q.acc_diff_b_minus_a], fmt="o", ms=3)
    ax.axhline(0, color="k", lw=0.5); ax.set_xticks(range(len(q))); ax.set_xticklabels(labels, rotation=90, fontsize=5); ax.set_ylabel("accuracy difference (video-cluster 95% CI)")
    fig.tight_layout(); fig.savefig(OUT / "figures/attribution_differences_ci.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["verify", "freeze", "plan", "run", "score"]); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
