#!/usr/bin/env python3
"""Bidirectional evidence-admission gate pilot (11/06). Writes only to runs/obsval_1028/bidir_pilot_1106/.
Direction is set ONLY by the initial media-only label (never by GT):
  initial PASS -> FAIL branch: admit only reliable FAIL-supporting evidence;  initial FAIL -> PASS branch: admit only reliable PASS evidence.
Admitted evidence is sent to Gemini for reconsideration with the unchanged two-stage prompt (obs_judge_1028.build_call); the label is
never forced. Closed gate -> media-only label. The original gated pipeline (row 5) is kept as the baseline.
Axes: A (speech and sounding events), V, AVB. TC: completed pilot results preserved (gemini_pilot_1106), not re-run. TR: separate,
no evidence rule defined, not run.
GT is used only to sample (25 per initial label x GT cell) and to score.
  python gepa_stage2/bidir_pilot_1106.py plan        # no calls: sample, triggers, prompts, cache matches, call count
  python gepa_stage2/bidir_pilot_1106.py run         # new calls (only after the plan is approved)
  python gepa_stage2/bidir_pilot_1106.py score
"""
import argparse, collections, hashlib, json, os, sys, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
OUT = HERE / "runs/obsval_1028/bidir_pilot_1106"
R2 = HERE / "runs/obsval_1028/gate_redesign_round2"
CALLS = HERE / "runs/obsval_1028/calls/gen_tool_text"
SEED, PER_CELL = 20261109, 25
DS = {"220 LTX": ("g220ltx", "G"), "220 MOVA": ("g220mova", "G"), "149 LTX": ("g149", "G"), "2k_25 LTX": ("g2k25", "G"), "P03-P09": ("hm_p3p9", "H")}
GROUP_OF = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA", "P03-P09": "P03-P09"}
AXES = ("A", "V", "AVB")

# branch rules: (family, branch) -> (rule name in the round-2 grid, evidence description). Pre-specified, not chosen on held-out data.
RULES = {
    ("A speech", "FAIL"): ("absent, other speech kept",
                           "reliable absence: Whisper returned kept speech (no_speech_prob < .5) and the target word appears nowhere in the transcript, "
                           "at any confidence. Not admitted: low-confidence recognition (word present with p < .5), no transcript, only filtered speech."),
    ("A speech", "PASS"): ("heard, word p >= 0.5", "presence: the target word is in a kept segment with word probability >= .5"),
    ("A sound", "FAIL"): ("FLAM max < 0.5", "FLAM first-query whole-clip max score < .5 (the round-2 5% development rule)"),
    ("A sound", "PASS"): ("FLAM max >= 0.999", "FLAM first-query whole-clip max score >= .999"),
    ("V", "FAIL"): ("caption check contradicts", "explicit caption contradiction of the requested event (text-only caption check verdict 'contradicts'); "
                                                 "caption omission ('not_mentioned') is never admitted"),
    ("V", "PASS"): ("caption check describes", "explicit caption description of the requested event (verdict 'describes')"),
    ("AVB", "FAIL"): ("abs offset >= 1.8 s and p >= 0.1", "Synchformer reading with |offset| >= 1.8 s and p >= .1"),
    ("AVB", "PASS"): ("offset 0 and p(0) >= 0.5 on a localized window",
                      "Synchformer offset 0 with p(offset 0) >= .5 on an event-localized window (P03-P09: annotation action window; generated: "
                      "anchor time > 0 inside the FLAM/Whisper span)"),
}


def calib_table():
    G = pd.read_csv(R2 / "dev_rule_grid.csv")
    rows = []
    for (fam, br), (rule, desc) in RULES.items():
        for grp in ("P03-P09", "LTX", "MOVA"):
            q = G[(G.group == grp) & (G.family == fam) & (G.rule == rule)]
            if not len(q):
                rows.append(dict(axis_family=fam, branch=br, group=grp, rule=rule, status="not applicable (no such units)"))
                continue
            r = q.iloc[0]
            den, num = int(r.err_den), int(r.err_num)
            if den < 20:
                st = f"EXPLORATORY: insufficient support (risk denominator {den} < 20)"
            elif r.opened == 0:
                st = "EXPLORATORY: never opened on development data"
            elif num / den <= 0.05:
                st = "meets 5% on development data (point estimate)"
            else:
                st = f"EXPLORATORY: fails 5% (development {num}/{den} = {num / den:.3f})"
            rows.append(dict(axis_family=fam, branch=br, group=grp, rule=rule, risk_cell=("GT PASS / initial PASS" if br == "FAIL" else "GT FAIL / initial FAIL"),
                             dev_err=f"{num} / {den}", dev_err_ci=r.err_ci, dev_opened=int(r.opened), dev_eligible=int(r.eligible),
                             dev_corrected=f"{int(r.corrected)} / {int(r.correctable_den)}", status=st))
    return pd.DataFrame(rows)


def family_of(axis, f):
    if axis == "A":
        return None if f is None else f.get("family")
    return axis


def branch_open(f, fam, branch):
    import gate_round2_1106 as RD
    fn = {name: g for fam_, name, d, g in RD.grid()}
    rule = RULES.get((fam, branch), (None,))[0]
    if f is None or rule is None:
        return False
    try:
        return bool(fn[rule](f))
    except Exception:
        return False


def payload(ds, axis, item, fam_by_event):
    """admitted evidence text for one (dataset, item, axis) row, from the opened events of that row."""
    import gen_stage2_1030 as G, hd_stage2_1101 as H
    src, mod = DS[ds]
    M = G if mod == "G" else H
    if axis == "A":
        s = "hm_ma39" if ds == "P03-P09" else src
        if mod == "H":                                   # hd_stage2_1101.a_parts -> {event_id: (line, below T_flam)}, no Whisper (no speech)
            fl, wt = (M.a_parts(s, item) or {}), None
        else:
            wt, fl, _ = M.a_parts(s, item)
        lines = []
        if any(f == "A speech" for f in fam_by_event.values()) and wt:
            lines.append(wt)
        lines += [fl[e][0] for e, f in sorted(fam_by_event.items()) if f == "A sound" and e in fl]
        return ("Observation (tool output):\n" + "\n".join(lines)) if lines else None, s
    if axis == "V":
        return M.v_text(src, item), src
    if axis == "AVB":
        return (M.avb_text(src, item), src) if mod == "H" else (G.avb_text(src, item), src)
    return None, src


def stage_plan(a):
    import obs_judge_1028 as O
    OUT.mkdir(parents=True, exist_ok=True)
    for f in ("manifest.csv", "plan_units.csv", "call_plan.csv"):
        if (OUT / f).exists():
            sys.exit(f"{f} exists; not overwritten")
    U = pd.read_csv(HERE / "runs/obsval_1028/section6_1106/units_all.csv", low_memory=False)
    U = U[(U.group == U.dataset) & U.dataset.isin(list(DS)) & U.axis.isin(AXES)]
    S = pd.read_csv(HERE / "runs/obsval_1028/gate_pilot_1106/split.csv")
    piv = {c: U[U.cond == c].set_index(["dataset", "unit"]) for c in ("row1", "row4", "row5")}
    b = U[(U.cond == "row1") & (U.status == "scored") & U.gt_elig.astype(bool)].merge(S[["dataset", "item", "group", "portion"]].rename(columns={"group": "split_group"}),
                                                                                        on=["dataset", "item"])
    b = b[b.portion == "heldout"].rename(columns={"pred": "initial"})
    r5 = piv["row5"]
    b["old_gated"] = [r5.pred.get((d, u)) if r5.status.get((d, u)) == "scored" else "" for d, u in zip(b.dataset, b.unit)]
    b = b[b.old_gated.isin(["yes", "no"])]            # both pipelines must be comparable on the unit
    rng = np.random.default_rng(SEED)
    sel, comp = [], []
    for ax in AXES:
        for init in ("yes", "no"):
            for gt in ("yes", "no"):
                pool = b[(b.axis == ax) & (b.initial == init) & (b.gt_y == gt)]
                strata = {k: list(g.index) for k, g in pool.groupby("dataset")}
                for k in strata:
                    rng.shuffle(strata[k])
                take, need = [], min(PER_CELL, len(pool))
                while len(take) < need:
                    for k in sorted(strata):
                        if strata[k] and len(take) < need:
                            take.append(strata[k].pop())
                sel.append(pool.loc[take])
                comp.append(dict(axis=ax, initial=("PASS" if init == "yes" else "FAIL"), gt=("PASS" if gt == "yes" else "FAIL"), pool=len(pool), selected=len(take),
                                 shortage=PER_CELL - len(take), by_dataset=pool.loc[take].dataset.value_counts().to_dict().__repr__()))
    M = pd.concat(sel)[["axis", "dataset", "unit", "item", "event", "split_group", "gt_y", "initial", "old_gated"]].rename(columns={"gt_y": "gt"})
    r4 = piv["row4"]
    M["always_shown"] = [r4.pred.get((d, u)) if r4.status.get((d, u)) == "scored" else "" for d, u in zip(M.dataset, M.unit)]
    M.to_csv(OUT / "manifest.csv", index=False)
    C = pd.DataFrame(comp); C.to_csv(OUT / "sample_composition.csv", index=False)
    # triggers
    F = pd.read_csv(R2 / "unit_features.csv", low_memory=False).set_index(["dataset", "unit"])
    cal = calib_table(); cal.to_csv(OUT / "branch_calibration.csv", index=False)
    calst = {(r.axis_family, r.branch, r.group): r.status for r in cal.itertuples()}
    rows = []
    for m in M.itertuples():
        f = F.loc[(m.dataset, m.unit)] if (m.dataset, m.unit) in F.index else None
        if isinstance(f, pd.DataFrame):
            f = f.iloc[0]
        fam = family_of(m.axis, f)
        br = "FAIL" if m.initial == "yes" else "PASS"
        op = branch_open(f, fam, br)
        rows.append(dict(axis=m.axis, dataset=m.dataset, unit=m.unit, item=m.item, event=m.event, group=GROUP_OF[m.dataset], family=fam, branch=br,
                         evidence_available=f is not None, opened=op, rule=RULES.get((fam, br), ("",))[0] if fam else "",
                         calibration_status=calst.get((fam, br, GROUP_OF[m.dataset]), "no evidence") if fam else "no evidence"))
    P = pd.DataFrame(rows); P.to_csv(OUT / "plan_units.csv", index=False)
    # calls: one per (dataset, item, axis) with opened units; full-prompt match against cached calls
    cached = collections.defaultdict(list)
    for f in CALLS.glob("*.json"):
        name = f.stem
        st, uid = name.split("__", 1)
        cached[uid].append((st, f))
    calls = []
    (OUT / "prompts").mkdir(exist_ok=True)
    for (ds, item, ax), g in P[P.opened].groupby(["dataset", "item", "axis"]):
        fam_by_event = {e: fm for e, fm in zip(g.event, g.family) if isinstance(e, str)}
        text, src = payload(ds, ax, item, fam_by_event)
        uid = f"{src}|{item}|{ax}"
        if text is None:
            calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="missing payload")); continue
        r = dict(set="BD1", source=src, uid=uid, item_id=item, axis=ax, variant="pilot", gt={}, clip=item, cond="gen_tool_text", obs={"text": text})
        cc = O.build_call(r)
        if cc is None:
            calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), action="no stage-1 anchor (no call possible)")); continue
        md5 = hashlib.md5(cc["user"].encode()).hexdigest()
        match = ""
        for st, fp in cached.get(uid.replace("/", "_"), []):
            rec = json.load(open(fp))
            if rec.get("status") == "ok" and rec.get("user_md5") == md5 and rec.get("rules_md5") == O.OBS_RULES_MD5:
                match = st; break
        json.dump(dict(uid=uid, system=cc["system"], user=cc["user"], schema=cc["schema"], user_md5=md5),
                  open(OUT / "prompts" / f"{uid.replace('/', '_')}.json", "w"), indent=1)
        calls.append(dict(dataset=ds, item=item, axis=ax, uid=uid, n_units=len(g), branches="/".join(sorted(set(g.branch))), user_md5=md5,
                          cached_set=match, action="reuse cached (full prompt match)" if match else "new call"))
    CP = pd.DataFrame(calls); CP.to_csv(OUT / "call_plan.csv", index=False)
    print(C.to_string(index=False))
    print(P.groupby(["axis", "family", "branch", "opened"]).size().to_string())
    print(CP.groupby(["axis", "action"]).size().to_string() if len(CP) else "no calls")


def stage_run(a):
    import obs_judge_1028 as O
    CP = pd.read_csv(OUT / "call_plan.csv").fillna("")
    todo = CP[CP.action == "new call"]
    (OUT / "calls").mkdir(exist_ok=True)
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key); t0 = time.time(); n = collections.Counter()

    def one(c):
        f = OUT / "calls" / f"BD1__{c.uid.replace('/', '_')}.json"
        if f.exists():
            return "cached"
        p = json.load(open(OUT / "prompts" / f"{c.uid.replace('/', '_')}.json"))
        r = dict(uid=c.uid, obs={})
        try:
            parsed, raw = O.call(client, "gemini-3.6-flash", dict(system=p["system"], user=p["user"], media=None, schema=p["schema"]), r)
            rec = dict(status="ok", parsed=parsed, raw=raw, usage=r.get("_usage"), wall_s=r.get("_wall_s"), user_md5=p["user_md5"],
                       anchor=O.anchor_entries(DS[c.dataset][0] if c.axis != "A" or c.dataset != "P03-P09" else "hm_ma39", c.item, c.axis))
        except Exception as e:
            rec = dict(status="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-1500:])
        rec.update(uid=c.uid, model="gemini-3.6-flash", thinking="high", rules_md5=O.OBS_RULES_MD5, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(f, "w"), default=str)
        return rec["status"]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:
        for i, s_ in enumerate(ex.map(one, list(todo.itertuples()))):
            n[s_] += 1
    json.dump(dict(calls=dict(n), wall_s=round(time.time() - t0, 1), workers=4), open(OUT / "run_info.json", "w"), indent=1)
    print(dict(n), round(time.time() - t0, 1), "s")


def stage_score(a):
    import audit_1106 as AU
    M = pd.read_csv(OUT / "manifest.csv"); P = pd.read_csv(OUT / "plan_units.csv"); CP = pd.read_csv(OUT / "call_plan.csv").fillna("")
    X = P.merge(M[["dataset", "unit", "gt", "initial", "old_gated", "always_shown"]], on=["dataset", "unit"])
    lab, src = [], []
    for x in X.itertuples():
        if not x.opened:
            lab.append(x.initial); src.append("closed: media-only fallback"); continue
        c = CP[(CP.dataset == x.dataset) & (CP.item == x.item) & (CP.axis == x.axis)]
        rec = None
        if len(c):
            c = c.iloc[0]
            if c.action == "new call":
                f = OUT / "calls" / f"BD1__{c.uid.replace('/', '_')}.json"; rec = json.load(open(f)) if f.exists() else None
            elif str(c.action).startswith("reuse"):
                rec = AU.stage2_rec(c.cached_set, c.uid)
        rec = rec if rec and rec.get("status") == "ok" else None
        l, st = AU.s2_event(rec, x.axis, x.event if isinstance(x.event, str) else None)
        if st == "ok" and l in ("yes", "no"):
            lab.append(l); src.append("open: stage-2 label")
        else:
            lab.append(""); src.append(f"open: missing output ({st})")
    X["new_label"] = lab; X["label_source"] = src
    X.to_csv(OUT / "unit_results.csv", index=False)
    rows = []
    for keys, q in X.groupby(["axis", "family", "branch", "calibration_status"], dropna=False):
        for scope, s_ in (("opened units", q[q.opened]), ("full subset", q)):
            for ref in ("initial", "old_gated"):
                v = s_[s_.new_label.isin(["yes", "no"])]
                o, n_ = v[ref] == v["gt"], v.new_label == v["gt"]
                rows.append(dict(axis=keys[0], family=keys[1], branch=keys[2], status=keys[3], scope=scope, vs=("media only" if ref == "initial" else "original gate"),
                                 units=len(s_), opened=int(q.opened.sum()), W_R=int((~o & n_).sum()), R_W=int((o & ~n_).sum()),
                                 unchanged=int((v.new_label == v[ref]).sum()), missing=int((~s_.new_label.isin(["yes", "no"])).sum())))
    T = pd.DataFrame(rows); T.to_csv(OUT / "results_by_branch.csv", index=False)
    pd.set_option("display.width", 250); print(T[T.vs == "original gate"].to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["plan", "run", "score"]); a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
