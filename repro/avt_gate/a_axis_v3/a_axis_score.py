#!/usr/bin/env python3
"""Walkthrough and scoring stages of the corrected A-axis evaluation (called from run_a_axis_correction.py, which installs the write
guard and the paths). Labels for non-A axes and all four baselines are read from the stored runs and never changed."""
import collections, hashlib, json, math, os, time
from pathlib import Path
import numpy as np, pandas as pd
import a_event_gate as AG

METHODS = [("initial", "MLLM-only"), ("one_call", "MLLM + Tools"), ("b1", "Reconsideration"), ("always_shown", "Reconsideration + Tools"),
           ("avt", "AVT-Judge"), ("gate", "Gate-only")]
SOURCE_COL = {"initial": "initial", "one_call": "one_call", "b1": "b1", "always_shown": "always_shown"}
ALPH = ("a01", "a05", "a10")
LOWER_BETTER = {"false_alarm_rate", "false_alarm_count"}


def _b(x):
    return str(x) == "True"


# ------------------------------------------------------------------ shared: corrected labels for one alpha
def a_labels(R, F, t, idx, bad):
    """-> (records DataFrame for every A unit, dict (dataset,item) -> resolve() result)."""
    groups = R.opened_groups(F, t); res = {}
    for k, fam in groups.items():
        res[k] = R.resolve(k[0], k[1], fam, idx, bad)
    rows = []
    num = lambda v: float(v) if v not in ("", None) else float("nan")
    for x in F.sort_values(["dataset", "item", "event"]).itertuples():
        dec = dict(open=_b(getattr(x, f"open_{t}")), kind=x.kind, direction=getattr(x, f"direction_{t}") or None)
        rr = res.get((x.dataset, x.item)) if dec["open"] else None
        resp = rr["labels"].get(x.event) if rr else None
        av, av_src = AG.avt_judge_label(x.initial, dec, resp)
        go, go_src = AG.gate_only_label(x.initial, dec)
        gres = res.get((x.dataset, x.item))
        rows.append(dict(dataset=x.dataset, unit=x.unit, item=x.item, event=x.event, kind=x.kind, initial=x.initial, open=dec["open"],
                         branch=getattr(x, f"branch_{t}"), threshold=num(getattr(x, f"threshold_{t}")), operator=getattr(x, f"operator_{t}"),
                         gate_reason=getattr(x, f"reason_{t}"), flam_max=num(x.flam_max), flam_query=x.flam_query, target_text=x.target_text,
                         recognized=_b(x.recognized), heard_tokens=x.heard_tokens,
                         clip_request_opened_events=";".join(sorted(gres["labels"].keys())) if gres else "",
                         admitted_evidence=("Whisper transcript (own target recognised)" if dec["open"] and x.kind == "speech" else
                                            ("FLAM line of this event" if dec["open"] else "none")),
                         response_label_for_event=(gres["all_labels"].get(x.event, "") if gres else ""),
                         avt_judge=av, avt_judge_source=av_src, gate_only=go, gate_only_source=go_src,
                         user_md5=(gres["fp"].get("user_md5", "") if gres and gres.get("fp") else ""),
                         system_md5=(gres["fp"].get("system_md5", "") if gres and gres.get("fp") else ""),
                         schema_md5=(gres["fp"].get("schema_md5", "") if gres and gres.get("fp") else ""),
                         output_source=(gres.get("src", "") if gres else ""), request_action=(gres["action"] if gres else "no request (no event of the clip opened)")))
    return pd.DataFrame(rows), res


def load_all(R):
    U = R.universe()
    F = pd.read_csv(R.OUT / "a_event_features_openings.csv", keep_default_na=False, low_memory=False)
    S = pd.read_csv(R.SAN / "results/unit_predictions.csv", low_memory=False)
    L = pd.read_csv(R.SENS / "results/unit_labels_openings.csv", low_memory=False)
    return U, F, S, L


# ------------------------------------------------------------------ walkthrough
def stage_walkthrough(a, R):
    M = R.setup(); O, FB, G = M["O"], M["FB"], M["G"]
    from adapter import AXIS_FULL
    sel = json.load(open(R.OUT / "selected_example.json"))
    U, F, S, L = load_all(R)
    idx, bad = R.reuse_index(), R.bad_md5()
    lines = []
    W = lines.append

    def clip(ds, item, title, frozen_note):
        src = FB.EVSRC[ds]; it = FB.items_all()[FB.PSET[ds]][item]; meta = O.meta_for(src, item)
        u = U[(U.dataset == ds) & (U["item"] == item)]; f = F[(F.dataset == ds) & (F["item"] == item)]
        W(f"# {title}\n\n{frozen_note}\n")
        W(f"- **Dataset / group / batch:** {ds} / {u.group.iloc[0]} / {u.batch.iloc[0]}\n- **Item ID:** `{item}`\n- **Stage-1 / tool source tag:** `{src}`\n")
        W("**Full generation prompt (verbatim):**\n\n```text\n" + (meta.get("generated_prompt") or meta.get("prompt") or it.get("prompt", "")) + "\n```\n")
        W("**Requested events:**\n\n| event | id | modality | target / action | definition |\n|---|---|---|---|---|")
        for k, e in enumerate(it["events"]):
            W(f"| event_{k + 1} | {e['id']} | {e['modality']} | {e.get('text') or e.get('action', '')} | {e.get('definition', '').replace('|', '/')} |")
        W("\n**Temporal constraint:** `" + json.dumps(it.get("temporal_constraint", {})) + "`\n")
        # ---- Stage-1 (cached) for all five axes, raw per-event JSON including skips
        W("## 1. Cached initial (Stage-1, media-only) judgments, all five axes\n")
        W("Source: the same-day Stage-1 anchor table `obs_judge_1028.anchor_df` (the run that produced the MLLM-only labels). Raw per-event "
          "JSON, unedited; skip / gating entries are shown as stored.\n")
        try:
            row = O.anchor_df(src).loc[item]
            for ax in ("A", "V", "AVB", "TCC", "TCR"):
                full = AXIS_FULL[ax]
                if ax == "TCR":
                    W(f"**{ax}** (`{full}`): label `{row.get(full, '')}`; reason: {row.get(full + '_reason', '')}\n")
                else:
                    W(f"**{ax}** (`{full}_per_event`):\n\n```json\n{json.dumps(json.loads(row[full + '_per_event']), indent=1, ensure_ascii=False)}\n```\n")
        except Exception as e:
            W(f"(Stage-1 anchor row not available: {type(e).__name__} {e})\n")
        W("**Scored units of this clip (evaluation table; `initial_reason` holds the explicit skip / prerequisite reasons):**\n")
        W("| unit | axis | MLLM-only | initial_reason | scored |\n|---|---|---|---|---|")
        for r in u.sort_values(["axis", "event"]).itertuples():
            W(f"| {r.unit} | {r.axis} | {r.initial if isinstance(r.initial, str) else ''} | {str(r.initial_reason) if isinstance(r.initial_reason, str) else ''} | {r.scored_row1} |")
        # ---- tool outputs
        rec = G.evidence(src, item)
        W("\n## 2. Cached tool outputs\n\n**Whisper (complete cached record, unedited):**\n")
        W("```json\n" + json.dumps((rec or {}).get("whisper"), indent=1, ensure_ascii=False) + "\n```\n")
        h = AG.heard_tokens((rec or {}).get("whisper"))
        W("Segments used for matching (no_speech_prob < 0.5):\n")
        for s in ((rec or {}).get("whisper") or {}).get("segments", []):
            W(f"- [{s['start']:.2f}–{s['end']:.2f} s] no_speech_prob={s['no_speech_prob']!r} -> {'USED' if s['no_speech_prob'] < 0.5 else 'dropped'}: \"{s['text'].strip()}\" "
              f"-> tokens {AG.norm(s['text']) if s['no_speech_prob'] < 0.5 else '[]'}")
        W(f"\nRecognised token set: `{sorted(h) if h is not None else None}`\n")
        W("**FLAM (raw cached scores; first query of each sounding event):**\n")
        q1 = {z["event_id"]: z["queries"] for z in (rec or {}).get("events", [])}
        for ev, qs in sorted(q1.items()):
            for i, q in enumerate(qs):
                fr = rec["flam"].get(q, {})
                W(f"- {ev} query {i} `{q}`{' (used by the gate)' if i == 0 else ''}: max_score={fr.get('max_score')!r}; detections={json.dumps(fr.get('detections'))}")
        # ---- per-event decisions, request, response, final labels
        out = {}
        for t in ("a05", "a01", "a10"):
            recs, res = a_labels(R, f, t, idx, bad); out[t] = (recs, res)
        recs, res = out["a05"]
        W("\n## 3. Event-by-event gate decisions (corrected contract, alpha = .05)\n")
        W("| event | kind | initial A | rule | tool output | match / threshold | gate | admitted evidence |\n|---|---|---|---|---|---|---|---|")
        for r in recs.itertuples():
            if r.kind == "speech":
                tool = f"heard {sorted(set(r.heard_tokens.split()))}"; mt = f"target {AG.norm(r.target_text)} -> {'recognised' if r.recognized else 'not recognised'}"
                rule = "Whisper: open iff initial FAIL and own target recognised"
            else:
                tool = f"FLAM max {r.flam_max!r} (`{r.flam_query}`)"; mt = f"{r.operator} {r.threshold!r} ({r.branch})"
                rule = "FLAM frozen event rule"
            W(f"| {r.event} | {r.kind} | {r.initial} | {rule} | {tool} | {mt} | **{'OPEN' if r.open else 'closed'}** — {r.gate_reason} | {r.admitted_evidence} |")
        for t in ("a01", "a10"):
            rr = out[t][0]
            W(f"\nalpha = {t[1:]}: openings " + ", ".join(f"{r.event}={'OPEN' if r.open else 'closed'}" for r in rr.itertuples()))
        k = (ds, item)
        if k in res and res[k]["cc"] is not None:
            rq = res[k]; cc = rq["cc"]
            W("\n## 4. The exact corrected request (alpha = .05; text only)\n")
            W(f"- uid `{rq['uid']}`; opened events (grouped clip × A request): `{sorted(rq['labels'])}`")
            W(f"- fingerprint: user md5 `{rq['fp']['user_md5']}`, system md5 `{rq['fp']['system_md5']}`, schema md5 `{rq['fp']['schema_md5']}`")
            W(f"- model settings: `{rq['fp']['settings']}`; media: none")
            W(f"- output source: {rq['action']} — `{rq['src']}`\n")
            W("**System instructions:**\n\n```text\n" + cc["system"] + "\n```\n")
            W("**User content (contains the generation prompt, axis criteria, OBS_RULES, the Stage-1 judgments of all A events, and the "
              "admitted evidence):**\n\n```text\n" + cc["user"] + "\n```\n")
            W("**Requested output schema:**\n\n```json\n" + json.dumps(cc["schema"], indent=1) + "\n```\n")
            r0 = rq["rec"]
            W("## 5. Actual response\n")
            if r0 is not None:
                W(f"Record time {r0.get('time')}, model {r0.get('model')}, thinking {r0.get('thinking')}, usage {r0.get('usage')}.\n")
                W("**Raw response (verbatim):**\n\n```json\n" + str(r0.get("raw", "")) + "\n```\n")
                W("**Parsed per-event labels:** " + ", ".join(f"{e}={l}" for e, l in sorted(rq["all_labels"].items())) + "\n")
            else:
                W(f"No valid output ({rq['action']}).\n")
        else:
            W("\n## 4–5. Request / response\n\nNo A event of this clip opens under the corrected contract at alpha = .05, so **no corrected A request "
              "is made** and every A event keeps its initial label.\n")
        # ---- final labels + old vs corrected + GT
        Lc = L.set_index(["dataset", "unit"]); Sc = S.set_index(["dataset", "unit"])
        W("\n## 6. Final labels, old vs corrected, and GT (GT shown for auditing only; it is not part of any request)\n")
        W("| event | kind | initial | gate (a05) | response label for event | AVT-Judge corrected (provenance) | Gate-only corrected (provenance) | "
          "AVT-Judge old (source) | Gate-only old | GT |\n|---|---|---|---|---|---|---|---|---|---|")
        for r in recs.itertuples():
            o = Lc.loc[(ds, r.unit)]
            W(f"| {r.event} | {r.kind} | {r.initial} | {'OPEN' if r.open else 'closed'} | {r.response_label_for_event or '—'} | **{r.avt_judge}** ({r.avt_judge_source}) | "
              f"**{r.gate_only}** ({r.gate_only_source}) | {o.judge_a05} ({o.judge_a05_source}) | {o.gate_a05} | {Sc.loc[(ds, r.unit), 'gt']} |")
        closed_resp = recs[(~recs.open) & recs.response_label_for_event.isin(["yes", "no"])]
        W("\n**Closed events cannot be changed by the response.**")
        for r in closed_resp.itertuples():
            W(f"- {r.event} is closed; the grouped request also returned `{r.response_label_for_event}` for it; the accepted label is the initial "
              f"label `{r.avt_judge}` ({r.avt_judge_source}).")
        for r in recs[~recs.open].itertuples():
            flip = "no" if r.initial == "yes" else "yes"
            got = AG.avt_judge_label(r.initial, dict(open=False, kind=r.kind), flip)
            W(f"- Counterfactual on the production code path (`a_event_gate.avt_judge_label`): if the response had said `{flip}` for closed "
              f"{r.event}, the final label would be `{got[0]}` ({got[1]}).")
        W("\n**Other axes (unchanged outputs and eligibility):**\n\n| unit | axis | GT eligible | MLLM-only | AVT-Judge (stored = corrected pipeline) | Gate-only |\n|---|---|---|---|---|---|")
        for r in u[u.axis != "A"].sort_values(["axis", "event"]).itertuples():
            o = Lc.loc[(ds, r.unit)]
            W(f"| {r.unit} | {r.axis} | yes | {r.initial if isinstance(r.initial, str) else ''} | {o.judge_a05 if isinstance(o.judge_a05, str) else ''} | {o.gate_a05 if isinstance(o.gate_a05, str) else ''} |")
        W("\nNon-A labels are copied from the stored 11-10 run; A-axis corrected labels are never propagated into AVB / TC / TR eligibility, which is "
          "computed from GT and the MLLM-only (Stage-1) labels only.\n")
        return recs
    s = sel["selected"]
    note = (f"Selected and frozen at {sel['frozen_at']} before any corrected outcome was inspected. Rule: {sel['rule']} Branches covered: "
            + "; ".join(f"{k}: {'yes' if v else 'NO'}" for k, v in sel["branches"].items()) + ". Branches not shown by this clip are covered by the "
            "regression clip below and by the deterministic tests (tests/test_a_event_gate.py).")
    r1 = clip(s["dataset"], s["item"], f"Walkthrough: {s['dataset']} / {s['item']}", note)
    W("\n\n---\n")
    r2 = clip("220 LTX", "hello-then-crossed_arms-then-yes__order", "Regression clip: 220 LTX / hello-then-crossed_arms-then-yes__order",
              "Known audit case: event_1 ('hello', initial PASS) was revised to FAIL by the legacy clip-level original gate, which opened "
              "because the word 'yes' (event_3) was heard.")
    e1 = r2[r2.event == "event_1"].iloc[0]
    ok = (not e1.open) and e1.avt_judge == "yes" and e1.gate_only == "yes"
    W(f"\n**Regression check:** event_1 open={e1.open}, AVT-Judge={e1.avt_judge}, Gate-only={e1.gate_only} -> {'PASS' if ok else 'FAIL'}.")
    # the legacy original-gate record that produced the historical event_1 FAIL (clip-level gate; read only)
    AU = M["AU"]; uid = "g220ltx|hello-then-crossed_arms-then-yes__order|A"
    W("\n**Legacy record behind the historical label (original paper gate, clip-level A call):**\n")
    for st in ("G5", "G4"):
        old = AU.stage2_rec(st, uid)
        if old is None:
            W(f"- set {st}: no record"); continue
        l1, s1 = AU.s2_event(old, "A", "event_1")
        W(f"- set {st}: record time {old.get('time')}, user md5 `{old.get('user_md5')}`; event_1 label `{l1}` ({s1}).")
        W("\n```json\n" + str(old.get("raw", ""))[:3000] + "\n```\n")
    W("The legacy call was made for the whole clip because 'yes' (event_3's target) was heard; its event_1 label replaced the initial PASS. "
      "Under the corrected contract no A event of this clip opens (both speech events are initially PASS), so no request is made and "
      "event_1 keeps PASS.\n")
    (R.OUT / "walkthrough").mkdir(exist_ok=True)
    (R.OUT / "walkthrough/WALKTHROUGH.md").write_text("\n".join(lines) + "\n")
    pd.concat([r1.assign(clip="selected example"), r2.assign(clip="regression clip")]).to_csv(R.OUT / "walkthrough/walkthrough_events.csv", index=False)
    json.dump(dict(regression_event1_pass=bool(ok), selected=s), open(R.OUT / "walkthrough/walkthrough_checks.json", "w"), indent=1)
    print("regression check:", "PASS" if ok else "FAIL")


# ------------------------------------------------------------------ scoring
def stage_score(a, R):
    import score_handoff as SH
    OUT = R.OUT; T = OUT / "tables"; T.mkdir(exist_ok=True); (OUT / "predictions").mkdir(exist_ok=True)
    U, F, S, L = load_all(R)
    idx, bad = R.reuse_index(), R.bad_md5()
    P = S.copy()
    key = list(zip(P.dataset, P.unit)); Lk = L.set_index(["dataset", "unit"])
    chk = {}
    recs_all = []
    for t in ALPH:
        recs, res = a_labels(R, F, t, idx, bad); recs["alpha"] = t; recs_all.append(recs)
        rk = recs.set_index(["dataset", "unit"])
        av = [rk.avt_judge.get(k) if k in rk.index else Lk[f"judge_{t}"].get(k) for k in key]
        go = [rk.gate_only.get(k) if k in rk.index else Lk[f"gate_{t}"].get(k) for k in key]
        P[f"avt_{t}"] = [x if isinstance(x, str) else "" for x in av]; P[f"gate_{t}"] = [x if isinstance(x, str) else "" for x in go]
        P[f"old_avt_{t}"] = [x if isinstance(x, str) else "" for x in Lk[f"judge_{t}"].reindex(key)]
        P[f"old_gate_{t}"] = [x if isinstance(x, str) else "" for x in Lk[f"gate_{t}"].reindex(key)]
        for c in (f"avt_{t}", f"gate_{t}", f"old_avt_{t}", f"old_gate_{t}"):
            P[c + "_cat"] = ["answered" if v in ("yes", "no") else (ic if ic != "answered" else "technical missing / failed output") for v, ic in zip(P[c], P.initial_cat)]
        nA = P.axis != "A"
        chk[f"{t}: non-A AVT-Judge labels identical to stored"] = f"{int((P[nA][f'avt_{t}'] == P[nA][f'old_avt_{t}']).sum())} / {int(nA.sum())}"
        chk[f"{t}: non-A Gate-only labels identical to stored"] = f"{int((P[nA][f'gate_{t}'] == P[nA][f'old_gate_{t}']).sum())} / {int(nA.sum())}"
        A_ = recs
        chk[f"{t}: closed A events keep the initial label exactly (AVT-Judge / Gate-only)"] = (
            f"{int(((~A_.open) & (A_.avt_judge == A_.initial.where(A_.initial.isin(['yes', 'no']), ''))).sum())} / {int((~A_.open).sum())}; "
            f"{int(((~A_.open) & (A_.gate_only == A_.initial.where(A_.initial.isin(['yes', 'no']), ''))).sum())} / {int((~A_.open).sum())}")
        chk[f"{t}: opened speech events / opened with unanswered initial"] = f"{int((A_.open & (A_.kind == 'speech')).sum())} / {int((A_.open & ~A_.initial.isin(['yes', 'no'])).sum())}"
        chk[f"{t}: closed speech events whose AVT-Judge label differs from the initial label (legacy inheritance would show here)"] = int(
            (A_[(A_.kind == "speech") & (~A_.open)].avt_judge != A_[(A_.kind == "speech") & (~A_.open)].initial).sum())
        chk[f"{t}: opened A events with unresolved output"] = int((A_.open & (A_.avt_judge == "")).sum())
    REC = pd.concat(recs_all, ignore_index=True)
    REC.to_csv(OUT / "predictions/a_event_records_all_alphas.csv", index=False, float_format="%.17g")
    keep = ["dataset", "batch", "group", "axis", "a_kind", "unit", "item", "event", "gt", "initial_cat"] + [c for c, _ in METHODS[:4]] + \
           [f"{p}{m}_{t}{s}" for t in ALPH for p in ("", "old_") for m in ("avt", "gate") for s in ("", "_cat")] + [c + "_cat" for c, _ in METHODS[:4]]
    P[keep].to_csv(OUT / "predictions/unit_predictions_six_methods.csv", index=False)
    # ---- invariance / independence checks
    chk["GT / eligibility rows identical to stored (units, GT)"] = f"{int((P['gt'].values == L.set_index(['dataset', 'unit'])['gt'].reindex(key).values).sum())} / {len(P)}"
    M = R.setup(); import p12_calib_1108 as P12
    C = R.cfgs(); Uk = U.set_index(["dataset", "unit"])
    snd = F[F.kind == "sounding"]
    for t in ALPH:
        same = sum(bool(P12.open_rule(C[t], Uk.loc[(d, u)])[0]) == _b(o) for d, u, o in zip(snd.dataset, snd.unit, snd[f"open_{t}"]) if Uk.loc[(d, u)].scored_row1)
        chk[f"{t}: sounding openings == p12_calib_1108.open_rule (cached units)"] = f"{same} / {int(sum(Uk.loc[(d, u)].scored_row1 for d, u in zip(snd.dataset, snd.unit)))}"
    import sanjoy_controls as SC
    sp = F[F.kind == "speech"]
    chk["speech: gen_stage2_1030.norm vs sanjoy_controls.norm recognition agree"] = int(sum(
        bool(set(AG.norm(t)) & set(h.split())) == bool(set(SC.norm(t)) & set(SC.norm(" ".join(h.split())))) for t, h in zip(sp.target_text, sp.heard_tokens)))
    chk["speech: units"] = len(sp)
    # GT-independence: shuffle GT and recompute decisions and request md5s for the a05 openings
    F2 = F.copy()                       # the feature / opening table has no GT column; requests are built with gt={}
    chk["openings do not read GT (decision inputs contain no GT column)"] = "gt" not in [c.lower() for c in F.columns]
    r05 = REC[REC.alpha == "a05"]
    md5_before = dict(zip(zip(r05.dataset, r05.item), r05.user_md5))
    sample = list({k for k, v in md5_before.items() if v})[:25]
    import final_benchmark_1108 as FB
    same = 0
    for (d, it) in sample:
        fam = R.opened_groups(F2, "a05")[(d, it)]
        cc, _, _ = R.build_request(d, it, fam)
        same += R.md5s(cc["user"]) == md5_before[(d, it)]
    chk["requests rebuilt from the GT-free feature table identical to the scored requests (sample of opened clips)"] = f"{same} / {len(sample)}"
    chk["system md5 of corrected requests == stored reconsideration prompts (11-06..11-10)"] = bool((REC[REC.system_md5 != ""].system_md5 == R.SYSTEM_MD5_STORED).all())
    cut, mt = R.code_cutoff(); chk["reuse requires record time >= verified builder snapshot"] = cut; chk["builder code mtimes"] = mt
    json.dump(chk, open(OUT / "checks.json", "w"), indent=1, default=str)
    # ---- metrics
    T6 = P.copy(); T6["axis_view"] = T6.axis
    TA = T6[T6.axis == "A"].copy(); TA["axis_view"] = "A " + TA.a_kind; T6 = pd.concat([T6, TA], ignore_index=True)
    rows, mem, rev = [], [], []
    for t in ALPH:
        new_cols = [c for c, _ in METHODS[:4]] + [f"avt_{t}", f"gate_{t}"]
        old_cols = [c for c, _ in METHODS[:4]] + [f"old_avt_{t}", f"old_gate_{t}"]
        names = {c: n for c, n in METHODS}
        for (g, ax), q in T6.groupby(["group", "axis_view"]):
            cn = np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in new_cols]); co = np.logical_and.reduce([q[c].isin(["yes", "no"]) for c in old_cols])
            same = cn & co
            mem.append(dict(alpha=t, dataset=g, axis=ax, gt_eligible=len(q), common_old=int(co.sum()), common_corrected=int(cn.sum()),
                            only_old=int((co & ~cn).sum()), only_corrected=int((cn & ~co).sum()),
                            only_old_units=";".join(q[co & ~cn].unit), only_corrected_units=";".join(q[cn & ~co].unit)))
            for version, cols in (("corrected", new_cols), ("old", old_cols)):
                common = q[cn] if version == "corrected" else q[co]
                for c in cols:
                    m_name = names.get(c.replace("old_", "").split("_a")[0] if c.startswith(("avt", "gate", "old_")) else c, c)
                    if c.startswith(("avt", "old_avt")):
                        m_name = "AVT-Judge"
                    elif c.startswith(("gate", "old_gate")):
                        m_name = "Gate-only"
                    for view, h in ((f"common six-method ({version})", common), ("answered", q[q[c].isin(["yes", "no"])]),
                                    ("identical examples (old common ∩ corrected common)", q[same])):
                        mm, cm = SH.answered_metrics(h["gt"], h[c])
                        r = dict(alpha=t, version=version, dataset=g, axis=ax, method=m_name, view=view, answered=len(h), gt_eligible=len(q),
                                 coverage=len(h) / len(q) if len(q) else np.nan, **{f"cm_{k}": v for k, v in cm.items()})
                        r.update({k: v[0] for k, v in mm.items()}); r.update({k + "_undefined_reason": v[3] for k, v in mm.items()})
                        rows.append(r)
                    qq = q.copy()
                    mm, cm = SH.fixed_metrics(qq, c)
                    r = dict(alpha=t, version=version, dataset=g, axis=ax, method=m_name, view="fixed GT-eligible denominator", answered=cm["answered"],
                             gt_eligible=len(q), coverage=cm["answered"] / len(q) if len(q) else np.nan, **{f"cm_{k}": v for k, v in cm.items()})
                    r.update({k: v[0] for k, v in mm.items()}); r.update({k + "_undefined_reason": v[3] for k, v in mm.items()})
                    rows.append(r)
                    if m_name in ("AVT-Judge", "Gate-only"):
                        for view, h in ((f"common six-method ({version})", common), ("answered", q[q[c].isin(["yes", "no"]) & q.initial.isin(["yes", "no"])])):
                            ini, fin, y = h.initial, h[c], h["gt"]
                            rev.append(dict(alpha=t, version=version, dataset=g, axis=ax, method=m_name, view=view, units=len(h),
                                            corrections=int(((ini != y) & (fin == y)).sum()), harmful_revisions=int(((ini == y) & (fin != y)).sum()),
                                            net=int(((ini != y) & (fin == y)).sum() - ((ini == y) & (fin != y)).sum()), revised=int((ini != fin).sum()),
                                            PASS_to_FAIL=int(((ini == "yes") & (fin == "no")).sum()), FAIL_to_PASS=int(((ini == "no") & (fin == "yes")).sum())))
    R_ = pd.DataFrame(rows).drop_duplicates(["alpha", "version", "dataset", "axis", "method", "view"])
    R_.to_csv(T / "metrics_all_axes_all_views.csv", index=False, float_format="%.17g")
    R_[R_.axis.str.startswith("A")].to_csv(T / "metrics_A_all_views.csv", index=False, float_format="%.17g")
    pd.DataFrame(mem).to_csv(T / "common_membership_old_vs_corrected.csv", index=False)
    pd.DataFrame(rev).drop_duplicates().to_csv(T / "corrections_harmful_revisions.csv", index=False)
    # non-A metric invariance (corrected vs old, every view, every alpha)
    nonA = R_[~R_.axis.str.startswith("A")].copy()
    nonA["view_n"] = nonA.view.str.replace(r" \((old|corrected)\)$", "", regex=True)
    chk2 = json.load(open(OUT / "checks.json"))
    for mcol in ("accuracy", "balanced_accuracy", "macro_F1", "FAIL_recall", "false_alarm_rate", "answered"):
        piv = nonA.pivot_table(index=["alpha", "dataset", "axis", "method", "view_n"], columns="version", values=mcol, aggfunc="first", dropna=False)
        same = (piv.old == piv.corrected) | (piv.old.isna() & piv.corrected.isna())
        chk2[f"non-A metric cells identical old vs corrected: {mcol} (all views, alphas, methods; NaN == NaN)"] = f"{int(same.sum())} / {len(piv)}"
    json.dump(chk2, open(OUT / "checks.json", "w"), indent=1, default=str)
    tables(R_, pd.DataFrame(rev), P, U, R, T)
    cost(R)
    print(json.dumps(chk2, indent=1, default=str)[:4000])


# ------------------------------------------------------------------ tables
def fmt(v):
    return "--" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.3f}"


def rank_marks(vals, lower_better=False):
    """bold = best, underline = second distinct value; computed on unrounded values."""
    clean = sorted({v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))}, reverse=not lower_better)
    best = clean[0] if clean else None; second = clean[1] if len(clean) > 1 else None
    out = []
    for v in vals:
        s = fmt(v)
        if best is not None and v == best:
            s = r"\textbf{" + s + "}"
        elif second is not None and v == second:
            s = r"\underline{" + s + "}"
        out.append(s)
    return out


def tables(R_, REV, P, U, R, T):
    meths = [n for _, n in METHODS]
    metrics_ = [("accuracy", "Acc"), ("balanced_accuracy", "BAcc"), ("macro_F1", "mF1"), ("FAIL_recall", "FAIL R"), ("false_alarm_rate", "FA rate")]
    main_view = "common six-method (corrected)"
    for version, view, fname, title in (("corrected", "common six-method (corrected)", "main_A_corrected_common.tex", "corrected, six-method common examples"),
                                        ("old", "common six-method (old)", "main_A_old_common.tex", "historical (legacy speech gate), six-method common examples"),
                                        ("corrected", "answered", "appendix_A_corrected_answered.tex", "corrected, per-method answered examples"),
                                        ("corrected", "fixed GT-eligible denominator", "appendix_A_corrected_fixed.tex", "corrected, fixed GT-eligible denominator"),
                                        ("corrected", "identical examples (old common ∩ corrected common)", "appendix_A_corrected_identical.tex", "corrected, identical examples"),
                                        ("old", "identical examples (old common ∩ corrected common)", "appendix_A_old_identical.tex", "historical, identical examples")):
        q = R_[(R_.alpha == "a05") & (R_.version == version) & (R_.view == view)]
        lines = [f"% A axis, alpha = .05, {title}. Bold = best, underline = second distinct value (unrounded; FA rate lower is better).",
                 r"\begin{tabular}{llr" + "c" * len(meths) + "}", r"\toprule",
                 r"Dataset & A view & Metric & " + " & ".join(meths) + r" \\", r"\midrule"]
        for g in ("LTX", "MOVA", "P03-P09"):
            for ax in ("A", "A speech", "A sounding"):
                h = q[(q.dataset == g) & (q.axis == ax)].set_index("method")
                if not len(h):
                    continue
                n = int(h.answered.max())
                for k, lab in metrics_:
                    if view == "fixed GT-eligible denominator" and k == "macro_F1":
                        continue
                    vals = [h[k].get(m) if m in h.index else None for m in meths]
                    lines.append(f"{g} & {ax} (n={n}) & {lab} & " + " & ".join(rank_marks(vals, k in LOWER_BETTER)) + r" \\")
                lines.append(r"\midrule")
        lines[-1] = r"\bottomrule"; lines.append(r"\end{tabular}")
        (T / fname).write_text("\n".join(lines) + "\n")
    # sensitivity (AVT-Judge / Gate-only across alpha; corrected and old)
    q = R_[(R_.view.str.startswith("common six-method")) & R_.method.isin(["AVT-Judge", "Gate-only"])]
    lines = [r"% Alpha sensitivity, A axis (six-method common examples of each alpha). BAcc / FAIL recall; corrected (old in brackets).",
             r"\begin{tabular}{ll" + "c" * 6 + "}", r"\toprule", r"Dataset & A view & Judge 1\% & Judge 5\% & Judge 10\% & Gate 1\% & Gate 5\% & Gate 10\% \\", r"\midrule"]
    for g in ("LTX", "MOVA", "P03-P09"):
        for ax in ("A", "A speech", "A sounding"):
            cells = []
            for m in ("AVT-Judge", "Gate-only"):
                for t in ALPH:
                    def get(ver):
                        r = q[(q.dataset == g) & (q.axis == ax) & (q.method == m) & (q.alpha == t) & (q.version == ver)]
                        return r.iloc[0] if len(r) else None
                    c, o = get("corrected"), get("old")
                    cells.append("--" if c is None else f"{fmt(c.balanced_accuracy)} / {fmt(c.FAIL_recall)}" + ("" if o is None else f" [{fmt(o.balanced_accuracy)} / {fmt(o.FAIL_recall)}]"))
            if any(x != "--" for x in cells):
                lines.append(f"{g} & {ax} & " + " & ".join(cells) + r" \\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"; lines.append(r"\end{tabular}")
    (T / "sensitivity_A_alpha.tex").write_text("\n".join(lines) + "\n")
    # perturbation (P03-P09 A rows by perturbation type)
    try:
        import section6_1106 as S6
        A_ = pd.read_csv(R.setup()["FB"].OUT / "units_all_conditions.csv", low_memory=False)
        var = A_[A_.cond == "row1"].drop_duplicates(["dataset", "unit"]).set_index(["dataset", "unit"]).variant
        p = P[(P.group == "P03-P09") & (P.axis == "A")].copy()
        p["variant"] = [var.get((d, u)) for d, u in zip(p.dataset, p.unit)]
        p["k"] = [S6.kind(type("R", (), dict(axis=r.axis, variant=r.variant, item=r.item, y=r.gt))()) for r in p.itertuples()]
        rows = []
        for k, h0 in p.groupby("k"):
            for c, nm in [(c, n) for c, n in METHODS[:4]] + [(f"avt_{t}", f"AVT-Judge {t}") for t in ALPH] + [(f"gate_{t}", f"Gate-only {t}") for t in ALPH] + \
                         [(f"old_avt_{t}", f"AVT-Judge old {t}") for t in ALPH] + [(f"old_gate_{t}", f"Gate-only old {t}") for t in ALPH]:
                h = h0[h0[c].isin(["yes", "no"])]
                rows.append(dict(row_type=k, method=nm, N=len(h), predicted_FAIL=int((h[c] == "no").sum()), predicted_FAIL_share=(h[c] == "no").mean() if len(h) else np.nan,
                                 accuracy=(h[c] == h['gt']).mean() if len(h) else np.nan))
        pd.DataFrame(rows).to_csv(T / "perturbation_P03_P09_A.csv", index=False, float_format="%.17g")
    except Exception as e:
        (T / "perturbation_P03_P09_A.csv").write_text(f"unavailable: {type(e).__name__}: {e}\n")
    # revision summary
    rv = REV[(REV.alpha == "a05") & REV.view.str.startswith("common")]
    rv.pivot_table(index=["dataset", "axis", "method"], columns="version", values=["corrections", "harmful_revisions", "net"], aggfunc="first").to_csv(T / "revisions_old_vs_corrected_a05.csv")


def cost(R):
    us, n, unres, att = [], 0, [], 0
    for f in R.CALLS.glob("AE__*.json") if R.CALLS.exists() else []:
        d = json.load(open(f)); n += 1; att += len(d["attempts"]); us += [x.get("usage") or {} for x in d["attempts"]]
        if not any(x.get("complete") for x in d["attempts"]):
            unres.append(d["uid"])
    ti = sum(u.get("prompt_token_count") or 0 for u in us); to = sum((u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0) for u in us)
    P = pd.read_csv(R.OUT / "call_plan.csv").fillna("")
    json.dump(dict(requests_total_across_alphas=len(P), unique_requests=int(P.user_md5.nunique()),
                   unique_reused=int(P[P.action.str.startswith("reuse")].user_md5.nunique()), new_requests_called=n, attempts=att, unresolved=unres,
                   input_tokens=ti, output_tokens_incl_thinking=to, usd_list_price=round(ti / 1e6 * 1.5 + to / 1e6 * 7.5, 4),
                   price_basis="$1.50 / 1M input, $7.50 / 1M output incl. thinking (project list price; not checked against billing)",
                   gate_only_calls=0), open(R.OUT / "cost.json", "w"), indent=1)
