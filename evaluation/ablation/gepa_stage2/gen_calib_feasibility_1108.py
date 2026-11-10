#!/usr/bin/env python3
"""Feasibility audit (11/08): can the human-annotated generated datasets (LTX = 220 + 149 + 2k_25, old MOVA = 220 MOVA, MOVA390) support a
separate gate-calibration experiment? FEASIBILITY DIAGNOSTICS ONLY: no rule is selected, frozen or deployed; the current P01/P02-only gates
are unchanged; no API / GPU call. Reads existing outputs only; writes only runs/obsval_1028/gen_calib_feasibility_1108/.
Inputs: final_cov_1108/all_units_five_methods.csv (row-1-eligible universe, initial = media-only label), section6_1106/units_all.csv +
avb_skipfix_1108 (GT / prerequisite exclusions of the existing sets), final_cov_1108/mova390_units_all_conditions.csv (MOVA390),
gen_evidence_1030 records (Whisper words + FLAM), calls/vcap_check + final_cov_1108 VC calls (caption check), flam_sync_audit_1106 and
synchformer_gen_1030/mova390 (Synchformer), prompt files (event types, canonical ids), audio_evidence_cache (one-call Whisper sections).
Branches (direction = initial label only): FAIL-evidence branch acts on initial PASS (risk cell = GT PASS, useful cell = GT FAIL);
PASS-evidence branch acts on initial FAIL (risk cell = GT FAIL, useful cell = GT PASS).
  python gepa_stage2/gen_calib_feasibility_1108.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import collections, glob, hashlib, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "gen_calib_feasibility_1108"
EV = Path((_tp.DATA + "/tools/gen_evidence_1030"))
GEN = ("220 LTX", "149 LTX", "2k_25 LTX", "220 MOVA", "MOVA390")
GROUP = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA (old 220)", "MOVA390": "MOVA390"}
GEN_OF = {"LTX": "LTX", "MOVA (old 220)": "MOVA", "MOVA390": "MOVA"}
PROMPTS = {"220": HERE.parents[2] / "new_prompts/generated/relative_500_v5_fixed.json",
           "149": Path((_tp.DATA + "/gen_holdout_149_1030/prompts_gen149.json")),
           "gen2k25": Path((_tp.DATA + "/gen_prolific2k25_1104/prompts_gen2k25.json")),
           "mova390": Path((_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json"))}
DS = {"220 LTX": ("220", "LTX_2p3", "g220ltx"), "220 MOVA": ("220", "MOVA", "g220mova"), "149 LTX": ("149", "LTX_2p3", "g149"),
      "2k_25 LTX": ("gen2k25", "LTX_2p3", "g2k25"), "MOVA390": ("mova390", "MOVA", "m390")}
MIN_RISK, MIN_USEFUL = 20, 10
SEED = "gen_calib_split_1108"


def norm(t):                                      # tc_screen_1102.norm (the tokenizer the existing Whisper categories use)
    return re.findall(r"[a-z']+", (t or "").lower())


def items():
    return {k: {x["item_id"]: x for x in json.load(open(f))} for k, f in PROMPTS.items()}


# ------------------------------------------------------------------ units (all GT units, exclusions, initial label)
def gt_units():
    U = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); U = U[(U.group == U.dataset) & U.dataset.isin(GEN)]
    F = pd.read_csv(RUNS / "avb_skipfix_1108/avb_units_all_conditions_fixed.csv", low_memory=False); F = F[F.dataset.isin(GEN)]
    N = pd.read_csv(RUNS / "final_cov_1108/mova390_units_all_conditions.csv", low_memory=False)
    U = pd.concat([U[U.axis != "AVB"], F, N], ignore_index=True)
    U = U[(U.cond == "row1") & U.axis.isin(["A", "V", "AVB", "TCC", "TCR"])].drop_duplicates(["dataset", "unit"])
    return U


def event_type(it, axis, ev):
    if axis == "TCR":
        return it["temporal_constraint"].get("task_type") or "relation"
    if not isinstance(ev, str) or not ev.startswith("event_"):
        return "item"
    e = it["events"][int(ev.split("_")[1]) - 1]
    return e.get("modality", "?")


# ------------------------------------------------------------------ prompt groups (union of item id, canonical id, action base)
def prompt_groups(IT):
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x

    def union(a, b):
        par[find(a)] = find(b)
    for s, d in IT.items():
        for iid, x in d.items():
            union(f"id:{iid}", f"canon:{x.get('canonical_item_id') or iid}")
    canon = {f"id:{iid}": find(f"id:{iid}") for d in IT.values() for iid in d}
    for s, d in IT.items():
        for iid in d:
            union(f"id:{iid}", f"base:{iid.split('__')[0]}")
    coarse = {k: find(k) for k in canon}
    return {k[3:]: v for k, v in canon.items()}, {k[3:]: v for k, v in coarse.items()}


# ------------------------------------------------------------------ features
def ev_rec(setn, model, iid):
    f = EV / setn / f"{model}__{iid}.json"
    return json.load(open(f)) if f.exists() else None


def flam_max(rec, eid):
    q = next((x["queries"][0] for x in rec.get("events", []) if x.get("event_id") == eid and x.get("queries")), None)
    return None if q is None or q not in rec.get("flam", {}) else rec["flam"][q]["max_score"]


def whisper_target(rec, text):
    """target-word presence features; a missing word has NO probability (never 0). Absence is a categorical state only."""
    target = set(norm(text)); segs = rec.get("whisper", {}).get("segments", [])
    hits, other, miss_p = [], [], 0
    for s in segs:
        for w in s.get("words", []):
            p = w.get("probability")
            miss_p += p is None
            (hits if set(norm(w["word"])) & target else other).append((p, s["no_speech_prob"], w["word"]))
    hp = [p for p, _, _ in hits if p is not None]; hk = [p for p, ns, _ in hits if p is not None and ns < 0.5]
    kept = [s for s in segs if s["no_speech_prob"] < 0.5]
    if not segs:
        state = "no transcript (no segment)"
    elif not hits:
        state = "target absent; other speech in kept segment" if kept else "target absent; only no_speech>=.5 segments"
    elif not hk:
        state = "target present only in no_speech>=.5 segment"
    else:
        state = "target present in kept segment"
    return dict(wh_state=state, wh_n_segments=len(segs), wh_n_target_hits=len(hits), wh_p_target_max=max(hp) if hp else np.nan,
                wh_p_target_max_kept=max(hk) if hk else np.nan, wh_min_nsp=min((s["no_speech_prob"] for s in segs), default=np.nan),
                wh_n_other_words=len(other), wh_missing_word_prob=miss_p)


def vcap(src, iid):
    f = RUNS / "calls/vcap_check" / f"{src}|{iid}|V.json"
    if f.exists():
        return {e["event_id"]: e["verdict"] for e in (json.load(open(f)).get("parsed") or {}).get("per_event", [])}
    f = RUNS / "final_cov_1108/calls" / f"VC__{src}|{iid}|V.json"
    if f.exists():
        att = [a for a in json.load(open(f))["attempts"] if a.get("complete")]
        return {e["event_id"]: e["verdict"] for e in (att[-1].get("parsed") or {}).get("per_event", [])} if att else None
    return None


def sync_table():
    s = pd.read_csv(RUNS / "flam_sync_audit_1106/events.csv")
    s["dataset"] = s.apply(lambda r: {"220": f"220 {'LTX' if r.model == 'LTX_2p3' else 'MOVA'}", "149": "149 LTX", "gen2k25": "2k_25 LTX"}[str(r.set)], axis=1)
    s = s[s.lag.notna()].assign(off=lambda t: t.lag.abs(), prob=lambda t: t.conf)[["dataset", "item_id", "event_id", "off", "prob"]]
    m = pd.concat(pd.read_csv(f) for f in sorted(Path((_tp.DATA + "/tools/synchformer_gen_1030/mova390")).glob("per_event_shard*.csv")))
    m = m[m.status == "ok"].assign(dataset="MOVA390", off=lambda t: t.offset.abs())[["dataset", "item_id", "event_id", "off", "prob"]]
    return pd.concat([s, m]).drop_duplicates(["dataset", "item_id", "event_id"]).set_index(["dataset", "item_id", "event_id"])


def onecall_avg_logprob_coverage(IT):
    """the one-call audio-evidence cache (separate Whisper run: language=en, compute float16) prints avg_logprob per segment (2 decimals)."""
    want = {(m, i) for k, d in IT.items() for i in d for m in ("LTX_2p3", "MOVA")}
    n = collections.Counter()
    for f in glob.glob((_tp.DATA + "/audio_evidence_cache/*.json")):
        try:
            r = json.load(open(f))
        except Exception:
            continue
        sec, v = r.get("section") or "", str(r.get("video", ""))
        m = "MOVA" if "/MOVA/" in v or "MOVA__" in v else ("LTX_2p3" if "LTX" in v else "other")
        n[(m, "files")] += 1; n[(m, "with avg_logprob")] += "avg_logprob=" in sec
    return {f"{a}|{b}": c for (a, b), c in n.items()}


# ------------------------------------------------------------------ main
def curve(q, score, direction, thresholds, branch_init):
    """empirical admission counts per threshold among the branch's units (initial = branch_init)."""
    h = q[(q.initial == branch_init) & q[score].notna()]
    risk_y, use_y = ("yes", "no") if branch_init == "yes" else ("no", "yes")
    R, Uu = h[h["gt"] == risk_y], h[h["gt"] == use_y]
    out = []
    for t in thresholds:
        ar = (R[score] < t) if direction == "lt" else (R[score] >= t); au = (Uu[score] < t) if direction == "lt" else (Uu[score] >= t)
        out.append(dict(threshold=t, n_risk=len(R), false_admissions=int(ar.sum()), false_admission_rate=round(ar.mean(), 4) if len(R) else None,
                        n_useful=len(Uu), useful_admissions=int(au.sum()), useful_admission_rate=round(au.mean(), 4) if len(Uu) else None))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IT = items(); canon, coarse = prompt_groups(IT)
    setkey = {"220 LTX": "220", "220 MOVA": "220", "149 LTX": "149", "2k_25 LTX": "gen2k25", "MOVA390": "mova390"}
    U = gt_units()
    U["event_type"] = [event_type(IT[setkey[d]][i], a, e) if i in IT[setkey[d]] else "?" for d, i, a, e in zip(U.dataset, U["item"], U.axis, U.event)]
    U["group"] = U.dataset.map(GROUP); U["prompt_group"] = U["item"].map(coarse); U["canonical_group"] = U["item"].map(canon)
    U["gt_label"] = U.gt_y.where(U.gt_y.isin(["yes", "no"]), "")
    def excl(r):
        if r.status == "scored":
            return "row-1 scored (universe)"
        s = str(r.reason)
        return ("GT label missing / tie" if "GT label missing" in s or "undetermined" in s else "GT prerequisite failure" if "GT prereq" in s or "GT prerequisite" in s
                else "judge (media-only) prerequisite failure" if "judge prereq" in s else "not applicable" if "not applicable" in s else "other: " + s)
    U["universe_status"] = U.apply(excl, axis=1)
    U.to_csv(OUT / "gt_units_generated.csv", index=False)
    # (1) inventory
    inv = []
    for (g, d, ax, et), q in list(U.groupby(["group", "dataset", "axis", "event_type"])) + [((g, "ALL " + g, ax, et), q) for (g, ax, et), q in U.groupby(["group", "axis", "event_type"])]:
        sc = q[q.status == "scored"]
        row = dict(group=g, dataset=d, axis=ax, event_type=et, gt_units=len(q), videos=q["item"].nunique(), prompt_groups=q.prompt_group.nunique(),
                   gt_PASS_all=int((q.gt_y == "yes").sum()), gt_FAIL_all=int((q.gt_y == "no").sum()), gt_missing_or_tie=int((~q.gt_y.isin(["yes", "no"])).sum()))
        row.update({k: int((q.universe_status == k).sum()) for k in ("GT label missing / tie", "GT prerequisite failure", "judge (media-only) prerequisite failure", "not applicable")})
        row.update(universe=len(sc), initPASS_gtPASS=int(((sc.pred == "yes") & (sc.gt_y == "yes")).sum()), initPASS_gtFAIL=int(((sc.pred == "yes") & (sc.gt_y == "no")).sum()),
                   initFAIL_gtPASS=int(((sc.pred == "no") & (sc.gt_y == "yes")).sum()), initFAIL_gtFAIL=int(((sc.pred == "no") & (sc.gt_y == "no")).sum()))
        inv.append(row)
    INV = pd.DataFrame(inv); INV.to_csv(OUT / "inventory_by_dataset_eventtype_axis.csv", index=False)
    vid = U.groupby("dataset").agg(videos=("item", "nunique"), prompt_groups=("prompt_group", "nunique"), canonical_groups=("canonical_group", "nunique")).reset_index()
    vid.to_csv(OUT / "videos_and_prompt_groups.csv", index=False)
    # shared prompts across generators
    sets = {d: set(U[U.dataset == d]["item"]) for d in GEN}; pg = {d: set(U[U.dataset == d].prompt_group) for d in GEN}
    sh = [dict(a=a, b=b, shared_item_ids=len(sets[a] & sets[b]), shared_prompt_groups=len(pg[a] & pg[b])) for i, a in enumerate(GEN) for b in GEN[i + 1:]]
    pd.DataFrame(sh).to_csv(OUT / "shared_prompts_across_sets.csv", index=False)
    # (2) features on the universe
    X = U[U.status == "scored"].rename(columns={"pred": "initial", "gt_y": "gt"}).copy()
    X = X[X.axis.isin(["A", "V", "AVB"])]
    SY = sync_table(); feats = []
    for r in X.itertuples():
        setn, model, src = DS[r.dataset]; it = IT[setkey[r.dataset]].get(r.item); f = dict()
        if r.axis == "A":
            rec = ev_rec(setn, model, r.item); e = it["events"][int(r.event.split("_")[1]) - 1]
            f["family"] = {"speech": "A speech", "sounding_action": "A sound"}.get(e["modality"], "A other")
            f["tool_record"] = rec is not None
            if rec is not None and f["family"] == "A sound":
                f["flam_max"] = flam_max(rec, r.event)
            if rec is not None and f["family"] == "A speech":
                f.update(whisper_target(rec, e.get("text", "")))
        elif r.axis == "V":
            v = vcap(src, r.item); f["family"] = "V"; f["vcap"] = (v or {}).get(r.event) if v is not None else None; f["tool_record"] = v is not None
        else:
            f["family"] = "AVB"; k = (r.dataset, r.item, r.event)
            f["off"], f["prob"] = (float(SY.off.get(k)), float(SY.prob.get(k))) if k in SY.index else (np.nan, np.nan); f["tool_record"] = k in SY.index
        feats.append(f)
    X = pd.concat([X.reset_index(drop=True), pd.DataFrame(feats)], axis=1)
    X.to_csv(OUT / "unit_features_generated.csv", index=False)
    score_col = {"A speech": "wh_p_target_max", "A sound": "flam_max", "V": "vcap", "AVB": "off"}
    miss = X.groupby(["group", "dataset", "family"]).apply(lambda q: pd.Series(dict(units=len(q), tool_record_missing=int((~q.tool_record.astype(bool)).sum()),
                                                                                   score_missing=int(q[score_col.get(q.name[2], "family")].isna().sum()) if q.name[2] in score_col else None))).reset_index()
    miss.to_csv(OUT / "missing_tool_scores.csv", index=False)
    # (3) support per branch, per group and generator family
    sup = []
    for lvl, key in (("group", "group"), ("dataset", "dataset"), ("generator", None)):
        X["_k"] = X[key] if key else X.group.map(GEN_OF)
        for (k, fam), q in X.groupby(["_k", "family"]):
            for br, ini, ry, uy in (("FAIL-evidence (initial PASS)", "yes", "yes", "no"), ("PASS-evidence (initial FAIL)", "no", "no", "yes")):
                h = q[q.initial == ini]; nr, nu = int((h["gt"] == ry).sum()), int((h["gt"] == uy).sum())
                sup.append(dict(level=lvl, key=k, family=fam, branch=br, units=len(h), risk_initially_correct=nr, useful_initially_wrong=nu,
                                videos=h["item"].nunique(), prompt_groups=h.prompt_group.nunique(),
                                sparse=("risk<20 " if nr < MIN_RISK else "") + ("useful<10" if nu < MIN_USEFUL else "")))
    SUP = pd.DataFrame(sup); SUP.to_csv(OUT / "branch_support.csv", index=False)
    # (4) candidate splits (prompt-group-disjoint across generators)
    def h(gid, salt=""):
        return int(hashlib.md5((SEED + salt + str(gid)).encode()).hexdigest(), 16) % 1000 / 1000
    X["fold50"] = np.where([h(g) < 0.5 for g in X.prompt_group], "calibration", "test")
    X["fold3"] = ["k%d" % (int(h(g, "k3") * 3)) for g in X.prompt_group]
    ltx_groups = set(X[X.group == "LTX"].prompt_group)
    X["cross"] = np.where(X.group == "LTX", "calibration (LTX)", np.where(X.prompt_group.isin(ltx_groups), "dropped (MOVA prompt group also in LTX)", "test (MOVA, LTX-disjoint groups)"))
    spl = []
    for scheme in ("fold50", "fold3", "cross"):
        for (gen, fam, fold), q in X.groupby([X.group.map(GEN_OF), "family", scheme]):
            for br, ini, ry, uy in (("FAIL-evidence", "yes", "yes", "no"), ("PASS-evidence", "no", "no", "yes")):
                hq = q[q.initial == ini]
                spl.append(dict(scheme=scheme, generator=gen, family=fam, fold=fold, branch=br, risk=int((hq["gt"] == ry).sum()), useful=int((hq["gt"] == uy).sum()),
                                prompt_groups=hq.prompt_group.nunique(), videos=hq["item"].nunique()))
    SPL = pd.DataFrame(spl); SPL.to_csv(OUT / "split_support.csv", index=False)
    X.drop(columns=["_k"]).to_csv(OUT / "unit_features_generated.csv", index=False)
    pd.DataFrame(dict(prompt_group=sorted(set(X.prompt_group)))).assign(fold50=lambda t: np.where([h(g) < 0.5 for g in t.prompt_group], "calibration", "test"),
                                                                         fold3=lambda t: ["k%d" % int(h(g, "k3") * 3) for g in t.prompt_group]).to_csv(OUT / "candidate_split_assignment.csv", index=False)
    # (5) score distributions, ties, curves (pooled feasibility diagnostics; NOT calibration)
    dist, ties, cur = [], [], []
    for (gen, fam), q in X.groupby([X.group.map(GEN_OF), "family"]):
        for sc in [c for c in ("wh_p_target_max", "wh_p_target_max_kept", "flam_max", "off", "prob") if c in q and q[c].notna().any()]:
            v = q[sc].dropna()
            vc = v.round(6).value_counts()
            ties.append(dict(generator=gen, family=fam, score=sc, available=len(v), missing=int(q[sc].isna().sum()), distinct=int(v.nunique()),
                             most_common_value=float(vc.index[0]), mass_at_most_common=round(vc.iloc[0] / len(v), 3), units_in_tied_values=int(vc[vc > 1].sum())))
            for (ini, gt_), w in q.groupby(["initial", "gt"]):
                x = w[sc].dropna()
                if len(x):
                    dist.append(dict(generator=gen, family=fam, score=sc, initial=ini, gt=gt_, n=len(x), **{f"q{int(p * 100)}": round(float(x.quantile(p)), 4) for p in (0, .1, .25, .5, .75, .9, 1)}))
    for fam, sc, dirs in (("A speech", "wh_p_target_max", (("PASS-evidence", "no", "ge"),)), ("A speech", "wh_p_target_max_kept", (("PASS-evidence", "no", "ge"),)),
                          ("A sound", "flam_max", (("FAIL-evidence", "yes", "lt"), ("PASS-evidence", "no", "ge"))),
                          ("AVB", "off", (("FAIL-evidence", "yes", "ge"), ("PASS-evidence", "no", "lt")))):
        for gen, q in X[X.family == fam].groupby(X.group.map(GEN_OF)):
            v = np.unique(q[sc].dropna().round(6))
            for br, ini, d in dirs:
                ths = list(v) + ([float(v.max()) + 1e-6] if d == "lt" and len(v) else [])
                for c in curve(q, sc, d, ths, ini):
                    cur.append(dict(generator=gen, family=fam, score=sc, branch=br, rule=f"{sc} {'<' if d == 'lt' else '>='} t", **c))
    # AVB with confidence floor (the frozen family), conf thresholds at observed quantiles
    for gen, q in X[X.family == "AVB"].groupby(X.group.map(GEN_OF)):
        for P in (0.0, 0.1278, 0.25, 0.3221, 0.5, 0.75):
            qq = q.assign(score_pass=np.where(q.prob >= P, q.off, np.nan), score_fail=np.where(q.prob >= P, q.off, np.nan))
            for c in curve(qq, "score_pass", "lt", [0.0001, 0.2001, 0.4001], "no"):
                cur.append(dict(generator=gen, family="AVB", score=f"off | conf>={P}", branch="PASS-evidence", rule=f"off <= t and conf >= {P}", **c))
            for c in curve(qq, "score_fail", "ge", [0.6, 1.0, 1.2, 1.8], "yes"):
                cur.append(dict(generator=gen, family="AVB", score=f"off | conf>={P}", branch="FAIL-evidence", rule=f"off >= t and conf >= {P}", **c))
    # categorical rules: V caption check, Whisper absence / presence states
    cat = []
    for (gen, fam), q in X.groupby([X.group.map(GEN_OF), "family"]):
        col = "vcap" if fam == "V" else ("wh_state" if fam == "A speech" else None)
        if col is None:
            continue
        for br, ini, ry, uy in (("FAIL-evidence", "yes", "yes", "no"), ("PASS-evidence", "no", "no", "yes")):
            hq = q[q.initial == ini]
            for val, w in hq.groupby(hq[col].fillna("(missing)")):
                cat.append(dict(generator=gen, family=fam, branch=br, state=val, units=len(w), risk_in_state=int((w["gt"] == ry).sum()), useful_in_state=int((w["gt"] == uy).sum()),
                                n_risk_branch=int((hq["gt"] == ry).sum()), n_useful_branch=int((hq["gt"] == uy).sum())))
    pd.DataFrame(dist).to_csv(OUT / "score_distributions.csv", index=False); pd.DataFrame(ties).to_csv(OUT / "score_coverage_ties.csv", index=False)
    pd.DataFrame(cur).to_csv(OUT / "feasibility_admission_curves.csv", index=False); pd.DataFrame(cat).to_csv(OUT / "categorical_state_admissions.csv", index=False)
    # (6) Whisper implementation facts from the caches
    wf = collections.Counter()
    for s in ("220", "149", "gen2k25", "mova390"):
        for f in glob.glob(str(EV / s / "*.json")):
            r = json.load(open(f)); w = r.get("whisper", {})
            wf[(s, "records")] += 1; wf[(s, "no segment")] += not w.get("segments")
            for sg in w.get("segments", []):
                wf[(s, "segments")] += 1; wf[(s, "segments with avg_logprob")] += "avg_logprob" in sg; wf[(s, "segments no_speech>=.5")] += sg["no_speech_prob"] >= 0.5
                for x in sg.get("words", []):
                    wf[(s, "words")] += 1; wf[(s, "words without probability")] += x.get("probability") is None; wf[(s, "words p<.5")] += (x.get("probability") or 0) < 0.5
    W = {f"{a}|{b}": c for (a, b), c in wf.items()}; W["one-call cache (separate run)"] = onecall_avg_logprob_coverage(IT)
    json.dump(W, open(OUT / "whisper_cache_facts.json", "w"), indent=1)
    print(INV[INV.dataset.str.startswith("ALL")].to_string(index=False)[:6000])
    print(SUP[SUP.level == "generator"].to_string(index=False))
    print(json.dumps(W, indent=1)[:2500])


if __name__ == "__main__":
    main()
