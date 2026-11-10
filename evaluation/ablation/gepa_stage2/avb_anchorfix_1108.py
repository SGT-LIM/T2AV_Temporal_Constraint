#!/usr/bin/env python3
"""Complete the AVB skip-bug repair in the stage-2 anchor builder (11/08). Writes only to runs/obsval_1028/avb_anchorfix_1108/.
Code change (in-process patch of run_two_stage.stage1_lookup; run_two_stage.py on disk is NOT edited, so no other run is affected):
  axis audio_visual_binding only: an event whose stage-1 reason matches SKIP_RE is now kept in the anchor if (a) the reason is not the
  pipeline's precondition message ("Binding not evaluated. [Precondition failed"), (b) its AVB label is an explicit yes / no, and (c) the
  same stage-1 row's A and V per-event entries for that event are label 'yes' with reasons that neither match SKIP_RE nor the 'treated as
  failure' placeholder. Everything else (genuine prerequisite failures, placeholders, missing entries, other axes) is unchanged.
Gate rules, thresholds, model (gemini-3.6-flash, thinking high, temperature 0, seed 42), OBS_RULES and prompt instructions frozen.
Calls (from combined_fix_1108/missing_calls.csv): combined gate = bidir payload (bidir_full_1107.payload); original gate = the frozen row-5
  set text (HG4 / G4 / K4 rows in rows.jsonl); always shown = the frozen row-4 set text (HA4 / GA4 / K4 rows in rows.jsonl).
  Deduplicated by prompt md5; an existing call is reused only if its exact prompt matches AND it has an entry for the event; new outputs
  saved under calls/AF__<md5>.json.
  python gepa_stage2/avb_anchorfix_1108.py plan | run | score
"""
import argparse, collections, hashlib, json, os, re, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "avb_anchorfix_1108"
PIPE_MSG = "Binding not evaluated. [Precondition failed"
FILL = re.compile(r"treated as failure", re.I)
S2 = {"P03-P09": ("HA4", "hm_p3p9"), "220 LTX": ("GA4", "g220ltx"), "220 MOVA": ("GA4", "g220mova"), "149 LTX": ("GA4", "g149"), "2k_25 LTX": ("K4", "g2k25")}
S2AV = {"P03-P09": ("HG4", "hm_p3p9"), "220 LTX": ("G4", "g220ltx"), "220 MOVA": ("G4", "g220mova"), "149 LTX": ("G4", "g149"), "2k_25 LTX": ("K4", "g2k25")}
RESTORED = []


def patch():
    import run_two_stage as TS
    orig = TS.stage1_lookup
    AVB, A, V = "audio_visual_binding", "audio_event_correctness", "visual_event_correctness"

    def ok_pass(r, col, eid):
        try:
            for e in json.loads(r[f"{col}_per_event"]):
                if e.get("event_id") == eid:
                    rs = str(e.get("reason", ""))
                    return str(e.get("label", "")).lower() == "yes" and not TS.SKIP_RE.search(rs) and not FILL.search(rs)
        except Exception:
            return False
        return False

    def stage1_lookup_fixed(item_id, axis, only_ids):
        ent, miss = orig(item_id, axis, only_ids)
        if axis != AVB or TS.STAGE1 is None or item_id not in TS.STAGE1.index:
            return ent, miss
        r = TS.STAGE1.loc[item_id]
        try:
            pe = json.loads(r[f"{axis}_per_event"])
        except Exception:
            return ent, miss
        have = {e["event_id"] for e in ent}; add = {}
        for e in pe:
            rs = str(e.get("reason", "")); eid = e.get("event_id")
            if eid in have or not TS.SKIP_RE.search(rs) or PIPE_MSG in rs or FILL.search(rs):
                continue
            if str(e.get("label", "")).lower() in ("yes", "no") and ok_pass(r, A, eid) and ok_pass(r, V, eid):
                add[eid] = e; RESTORED.append(dict(item=item_id, event=eid))
        if not add:
            return ent, miss
        allgood = {x["event_id"]: x for x in ent}; allgood.update(add)
        order = [x["event_id"] for x in pe if x.get("event_id") in allgood]
        want = list(only_ids) if only_ids is not None else order
        return [allgood[i] for i in want if i in allgood], [i for i in want if i not in allgood]
    TS.stage1_lookup = stage1_lookup_fixed


def rows_text():
    t = {}
    for l in open(RUNS / "rows.jsonl"):
        r = json.loads(l)
        if r["cond"] == "gen_tool_text" and r["axis"] == "AVB":
            t[(r["set"], r["uid"])] = r
    return t


def stage_plan(a):
    import obs_judge_1028 as O, bidir_full_1107 as BF, audit_1106 as AU
    import gen2k25_stage2_1104  # noqa: F401
    OUT.mkdir(parents=True, exist_ok=True); patch()
    N = pd.read_csv(RUNS / "combined_fix_1108/missing_calls.csv"); RT = rows_text()
    U = pd.read_csv(RUNS / "combined_fix_1108/avb_combined_unit_results.csv", low_memory=False)
    idx = json.load(open(RUNS / "p12_calib_1108/reuse_index.json"))
    for d in (RUNS / "p12_calib_1108/calls", OUT / "calls"):
        for p in d.glob("*.json") if d.exists() else []:
            r = json.load(open(p))
            if r.get("status") == "ok" and r.get("user_md5"):
                idx.setdefault(r["user_md5"], str(p))
    (OUT / "prompts").mkdir(exist_ok=True); rows = []
    for x in N.itertuples():
        ds, item = x.dataset, x.item
        if x.method == "combined gate":
            text, src = BF.payload(ds, "AVB", item, {}); setname = "bidir payload"
        else:
            st, src = (S2 if x.method == "always shown" else S2AV)[ds]; setname = st
            text = RT[(st, f"{src}|{item}|AVB")]["obs"]["text"]
        uid = f"{src}|{item}|AVB"
        cc = O.build_call(dict(set="AF", source=src, uid=uid, item_id=item, axis="AVB", variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text}))
        evs = U[(U.dataset == ds) & (U["item"] == item)].event.tolist()
        if cc is None:
            rows.append(dict(method=x.method, dataset=ds, item=item, uid=uid, source_set=setname, events=";".join(evs), action="still no stage-1 anchor after the fix")); continue
        md5 = hashlib.md5(cc["user"].encode()).hexdigest(); anchor_ids = [e["event_id"] for e in cc["anchor"]]
        f = idx.get(md5); reuse = False
        if f:
            rec = json.load(open(f)); rec.setdefault("anchor", cc["anchor"])
            reuse = all(AU.s2_event(rec, "AVB", e)[1] == "ok" for e in evs if e in anchor_ids)
        json.dump(dict(uid=uid, item=item, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5), open(OUT / "prompts" / f"{md5}.json", "w"))
        rows.append(dict(method=x.method, dataset=ds, item=item, uid=uid, source_set=setname, events=";".join(evs), anchor_events=";".join(anchor_ids), user_md5=md5,
                         prompt_chars=len(cc["system"]) + len(cc["user"]), reuse_file=f if reuse else "", action="reuse (exact complete output)" if reuse else "new call"))
    P = pd.DataFrame(rows); P.to_csv(OUT / "call_plan.csv", index=False)
    pd.DataFrame(RESTORED).drop_duplicates().to_csv(OUT / "anchor_restored_events.csv", index=False)
    new = P[P.action == "new call"].drop_duplicates("user_md5"); b = json.load(open(RUNS / "bidir_full_1107/estimate_basis.json"))
    est = dict(planned=len(P), unique_new_calls=len(new), reused=int((P.action != "new call").sum()), still_no_anchor=int((P.action == "still no stage-1 anchor after the fix").sum()),
               est_usd_list=round(new.prompt_chars.sum() / b["chars_per_token"] / 1e6 * 1.5 + b["output_tokens_median"] * len(new) / 1e6 * 7.5, 2))
    json.dump(est, open(OUT / "estimate.json", "w"), indent=1)
    print(P.groupby(["method", "action"]).size().to_string()); print(est)


def stage_run(a):
    import obs_judge_1028 as O
    from google import genai
    patch()
    P = pd.read_csv(OUT / "call_plan.csv").fillna(""); todo = P[P.action == "new call"].drop_duplicates("user_md5"); (OUT / "calls").mkdir(exist_ok=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"]); t0 = time.time(); n = collections.Counter()

    def one(c):
        f = OUT / "calls" / f"AF__{c.user_md5}.json"
        if f.exists():
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.user_md5}.json")); r = dict(uid=c.uid, obs={})
        try:
            parsed, raw = O.call(client, "gemini-3.6-flash", dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
            rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"],
                       anchor=O.anchor_entries(c.uid.split("|")[0], c.item, "AVB"))
        except Exception as e:
            rec = dict(status="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        rec.update(uid=c.uid, model="gemini-3.6-flash", thinking="high", rules_md5=O.OBS_RULES_MD5, anchor_fix="avb_anchorfix_1108", time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(f, "w"), default=str); return rec["status"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s] += 1
            if i % 20 == 0 or i + 1 == len(todo):
                print(f"[anchorfix] {i + 1}/{len(todo)} {dict(n)} {time.time() - t0:.0f}s", flush=True)
            if s == "error":
                err = json.load(open(OUT / "calls" / f"AF__{list(todo.itertuples())[i].user_md5}.json")).get("error", "")
                if "429" in err or "spending cap" in err:
                    print("[anchorfix] STOP: 429 / spending cap on the second-project credential", flush=True); ex.shutdown(cancel_futures=True); break
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), workers=a.workers), open(OUT / "run_info.json", "w"), indent=1)


def stage_score(a):
    import audit_1106 as AU, bidir_full_1107 as BF
    P = pd.read_csv(OUT / "call_plan.csv").fillna("")
    recs = {}
    for r in P.itertuples():
        f = Path(r.reuse_file) if r.action.startswith("reuse") else OUT / "calls" / f"AF__{r.user_md5}.json"
        rec = json.load(open(f)) if r.user_md5 and f.exists() else None
        recs[(r.method, r.dataset, r.item)] = rec if rec and rec.get("status") == "ok" else None
    ALL = pd.read_csv(RUNS / "combined_fix_1108/all_axes_combined_unit_results.csv", low_memory=False)
    AV = pd.read_csv(RUNS / "combined_fix_1108/avb_combined_unit_results.csv", low_memory=False).set_index(["dataset", "unit"])
    before = ALL.copy(); filled = collections.Counter()
    for i, x in ALL[ALL.axis == "AVB"].iterrows():
        k = (x.dataset, x.unit)
        for col, mth in (("combined", "combined gate"), ("original_gate", "original paper gate"), ("always_shown", "always shown")):
            if x[col] in ("yes", "no"):
                continue
            if col == "combined" and not bool(AV.opened.get(k)):
                continue
            if col != "combined" and "stage-2" not in str(AV.get(col + "_reason", pd.Series()).get(k, "")):
                continue
            rec = recs.get((mth, x.dataset, x["item"]))
            l, st = AU.s2_event(rec, "AVB", x.event)
            if st == "ok" and l in ("yes", "no"):
                ALL.at[i, col] = l; filled[mth] += 1
    ALL.to_csv(OUT / "all_axes_unit_results_after_anchorfix.csv", index=False)
    pipes = [("initial", "media only"), ("one_call", "one call plus tools"), ("always_shown", "always shown"), ("original_gate", "original paper gate"), ("combined", "combined gate")]
    rows, pc, cov = [], [], []
    for ver, T in (("before", before), ("after", ALL)):
        for kk in (("dataset", "axis"), ("group", "axis")):
            for key, q in T.groupby(list(kk)):
                common = q[np.logical_and.reduce([q[c].isin(["yes", "no"]) for c, _ in pipes])]
                for col, nm in pipes:
                    m = BF.metrics(common["gt"], common[col])
                    rows.append(dict(version=ver, level="/".join(kk), key=" | ".join(map(str, key)), method=nm, eligible_row1=len(q), common_units=len(common),
                                     acc=m.get("acc"), macro_F1=m.get("macro_F1"), bal_acc=m.get("bal_acc"), FAIL_R=m.get("FAIL_R"), FA=m.get("FA"),
                                     FAIL_P=m.get("FAIL_P"), FAIL_F1=m.get("FAIL_F1"), PASS_P=m.get("PASS_P"), PASS_R=m.get("PASS_R"), PASS_F1=m.get("PASS_F1")))
                    cov.append(dict(version=ver, level="/".join(kk), key=" | ".join(map(str, key)), method=nm, scored=int(q[col].isin(["yes", "no"]).sum()), missing=int((~q[col].isin(["yes", "no"])).sum())))
                if ver == "after":
                    for ref, rn in pipes[:4]:
                        o_, n_ = common[ref] == common["gt"], common["combined"] == common["gt"]
                        pc.append(dict(level="/".join(kk), key=" | ".join(map(str, key)), vs=rn, common_units=len(common), corrections=int((~o_ & n_).sum()), corruptions=int((o_ & ~n_).sum())))
    pd.DataFrame(rows).to_csv(OUT / "metrics_before_after.csv", index=False); pd.DataFrame(pc).to_csv(OUT / "paired_changes_after.csv", index=False)
    pd.DataFrame(cov).to_csv(OUT / "coverage_before_after.csv", index=False)
    us = [json.load(open(f)).get("usage") or {} for f in (OUT / "calls").glob("AF__*.json")] if (OUT / "calls").exists() else []
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    json.dump(dict(new_calls=len(us), input_tokens=ti, output_tokens_incl_thinking=to, usd_list=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 3), filled_units=dict(filled)), open(OUT / "cost.json", "w"), indent=1)
    print(dict(filled))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["plan", "run", "score"]); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
