"""
V-axis judge vs caption: does the caption help Gemini, and on which events?

Run from eval_results/:
    python v_judge_caption_join.py

Outputs -> eval_results/v_caption_join/
    table_a_condition_metrics.csv   acc / recall(present) / spec(absent) / pass_rate, per cond x model x kind, mean+-sd over reps
    table_b_by_mentioned.csv        baseline vs caption acc split by whether the caption mentioned the event
    table_c_transition.csv          baseline right/wrong x caption right/wrong, per kind (majority over reps)
    flips_rationale.csv             per-event dump of flipped events with baseline and caption reasons + keyword tags
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[3] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[0])  # legacy path roots, see legacy/README.md
import csv, sys, glob, os, re
from collections import defaultdict, Counter
import statistics as st

csv.field_size_limit(sys.maxsize)
os.chdir((_LEGACY_ROOT + "/eval_results"))
OUT = "v_caption_join"; os.makedirs(OUT, exist_ok=True)

MODELS = ["LTX_2p3", "MOVA"]

# ---- judge conditions (multi_agent). rep1 lives in the condition folder, rep2/3 in rep2/, rep3/.
# baseline rep1 file uses the old name agentic_pure_gemini.
CONDS = {
    "gemini_only":      ("multi_agent/baseline_min3", {1: "{M}_agentic_pure_gemini", 2: "{M}_agentic_baseline", 3: "{M}_agentic_baseline"}),
    "gemini_wf":        ("multi_agent/tools_wf_min3", {1: "{M}_agentic_whisper_flam", 2: "{M}_agentic_whisper_flam", 3: "{M}_agentic_whisper_flam"}),
    "cap_avocado":      ("multi_agent/caption_avocado_plain_v3_min3", "{M}_caption_avocado_plain_v3_min3"),
    "cap_salmonn":      ("multi_agent/caption_salmonn_plain_v3_min3", "{M}_caption_salmonn_plain_v3_min3"),
    "cap_qwen3vl":      ("multi_agent/caption_qwen3vl_plain_v3_min3", "{M}_caption_qwen3vl_plain_v3_min3"),
    "cap_qwen3vl_ts":   ("multi_agent/caption_qwen3vl_ts_v3_min3", "{M}_caption_qwen3vl_ts_v3_min3"),
    "cap_omni":         ("multi_agent/caption_omni_plain_v3_min3", "{M}_caption_omni_plain_v3_min3"),
    "cap_omni_ts":      ("multi_agent/caption_omni_ts_v3_min3", "{M}_caption_omni_ts_v3_min3"),
    "cap_gemini":       ("multi_agent/caption_gemini_v3_min3", "{M}_caption_gemini_v3"),
}
BASELINES = ["gemini_only", "gemini_wf"]   # compare captions against both; decide which is the fair control

# ---- caption_accuracy per_event.csv: GT categories + whether caption mentioned the event
CAPACC = "caption_accuracy/per_event.csv"
# columns: condition,model,item_id,video,event_key,event_id,kind,prim,label,gt_v_pass,gt_v_present,gt_v_absent,...,gemini_mentioned,...
COL_MODEL, COL_COND, COL_ITEM, COL_EVENT = "model", "condition", "item_id", "event_id"   # if judge per_event event_id != this, try "event_key"
COL_KIND, COL_PRESENT, COL_ABSENT, COL_MENTIONED = "kind", "gt_v_present", "gt_v_absent", "gemini_mentioned"

def truthy(x): return str(x).strip().lower() in ("1", "true", "yes", "y", "1.0")

# explicit map: caption_accuracy `condition` value -> judge cond key. Unmapped values are printed at startup.
CAPACC_COND_MAP = {
    "avocado_fps8_plain_v3": "cap_avocado",
    "salmonn_plain_v3": "cap_salmonn",
    "omni_fps8_plain_v3": "cap_omni",
    "omni_fps8_ts_v3": "cap_omni_ts",
    "qwen3vl_fps8_plain_v3": "cap_qwen3vl",
    "qwen3vl_fps8_v3": "cap_qwen3vl_ts",
}
def map_cond(c): return CAPACC_COND_MAP.get(c.strip().lower())

# ------------------------------------------------------------------ load GT + mentions
gt = {}                       # (model, item, event) -> (kind, present/absent)
mentioned = defaultdict(dict) # cond -> (model,item,event) -> bool
gt_all = {}                   # (model, item, event) -> human V pass (bool), all events incl. excluded
unmapped = Counter()
for r in csv.DictReader(open(CAPACC, newline="")):
    key = (r[COL_MODEL], r[COL_ITEM], r[COL_EVENT])
    if truthy(r[COL_PRESENT]): gt[key] = (r[COL_KIND].strip().lower(), "present")
    elif truthy(r[COL_ABSENT]): gt[key] = (r[COL_KIND].strip().lower(), "absent")
    # else excluded (unresolvable FAIL) -> skipped
    c = map_cond(r[COL_COND])
    if c: mentioned[c][key] = truthy(r[COL_MENTIONED])
    else: unmapped[r[COL_COND]] += 1
    # item-level GT uses every event (excluded ones too): human V PASS per event, from gt_v_pass
    gt_all.setdefault(key, truthy(r["gt_v_pass"]))
print(f"GT events: {len(gt)}  kinds: {Counter(k for k,_ in gt.values())}   all events (item-level GT): {len(gt_all)}")
if unmapped: print("UNMAPPED caption_accuracy conditions (fix map_cond):", dict(unmapped))
print("mention coverage per cond:", {c: len(v) for c, v in mentioned.items()})

# ------------------------------------------------------------------ load judge per_event, axis=V
def per_event_path(cond, model, rep):
    folder, name = CONDS[cond]
    fname = (name[rep] if isinstance(name, dict) else name).format(M=model)
    sub = "" if rep == 1 else f"rep{rep}/"
    cands = glob.glob(f"{folder}/{sub}{fname}*per_event*.csv")
    return cands[0] if cands else None

V_AXIS = "visual_event_correctness"

def kind_of(s):
    s = (s or "").lower()
    for k in ("speech", "silent", "sounding"):
        if k in s: return k
    return None

def event_num(eid):
    m = re.search(r"(\d+)$", eid or "")
    return int(m.group(1)) if m else 0

def load_judge(cond, model, rep):
    """(item, capacc_event_id) -> (label, reason, evidence).
    judge event_id is positional (event_1..); caption_accuracy event_id is kind-based
    (sounding_action, sounding_action_2 ...). Rebuild the kind-based id from event order + event_kind.
    Keep last valid row per key (resume duplicates)."""
    p = per_event_path(cond, model, rep)
    if not p: return None
    rows = [r for r in csv.DictReader(open(p, newline="")) if r.get("axis", "").strip() == V_AXIS]
    # positional -> kind-based id, per item
    kinds = defaultdict(dict)  # item -> {judge event_id: kind}
    for r in rows: kinds[r["item_id"]][r["event_id"]] = kind_of(r.get("event_kind"))
    remap = {}
    for item, ev in kinds.items():
        cnt = Counter()
        for eid in sorted(ev, key=event_num):
            k = ev[eid]
            if not k: continue
            cnt[k] += 1
            base = "speech" if k == "speech" else f"{k}_action"   # capacc ids: speech, speech_2, silent_action, sounding_action_2
            remap[(item, eid)] = base if cnt[k] == 1 else f"{base}_{cnt[k]}"
    out = {}
    for r in rows:
        lab = (r.get("label") or "").strip().lower()
        if lab not in ("pass", "fail", "yes", "no"): continue
        lab = "pass" if lab in ("pass", "yes") else "fail"
        key = (r["item_id"], remap.get((r["item_id"], r["event_id"]), r["event_id"]))
        out[key] = (lab, r.get("reason", ""), r.get("evidence", ""))
    return out

judge = {}  # (cond, model, rep) -> dict
for cond in CONDS:
    for m in MODELS:
        for rep in (1, 2, 3):
            d = load_judge(cond, m, rep)
            if d is None: print(f"  missing: {cond} {m} rep{rep}"); continue
            judge[(cond, m, rep)] = d

# join diagnostic
for m in MODELS:
    d = judge.get(("gemini_only", m, 2)) or judge.get(("gemini_only", m, 3))
    if not d: continue
    gk = {(i, e) for (mm, i, e) in gt if mm == m}
    print(f"join {m}: GT {len(gk)}  judge V rows {len(d)}  matched {len(gk & set(d))}")
    unmatched = sorted(gk - set(d))[:5]
    if unmatched: print("   GT keys not in judge (sample):", unmatched, "\n   judge keys sample:", sorted(d)[:5])

def correct(lab, cat): return (lab == "pass") == (cat == "present")

# ------------------------------------------------------------------ table A: per condition metrics, mean+-sd over reps
def metrics(rows):
    """rows: list of (lab, cat). returns acc, recall_present, spec_absent, pass_rate, n"""
    if not rows: return None
    n = len(rows)
    acc = sum(correct(l, c) for l, c in rows) / n
    pres = [l for l, c in rows if c == "present"]; absn = [l for l, c in rows if c == "absent"]
    rec = sum(l == "pass" for l in pres) / len(pres) if pres else float("nan")
    spec = sum(l == "fail" for l in absn) / len(absn) if absn else float("nan")
    pr = sum(l == "pass" for l, _ in rows) / n
    return acc, rec, spec, pr, n, len(pres), len(absn)

def fmt(vals):
    vals = [v for v in vals if v == v]
    if not vals: return ""
    return f"{st.mean(vals):.3f}±{st.pstdev(vals):.3f}" if len(vals) > 1 else f"{vals[0]:.3f}"

with open(f"{OUT}/table_a_condition_metrics.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "kind", "cond", "n_reps", "acc", "recall_present", "spec_absent", "pass_rate", "n_events", "n_present", "n_absent"])
    for m in MODELS:
        for kind in ["all", "speech", "silent", "sounding"]:
            for cond in CONDS:
                per_rep = []
                for rep in (1, 2, 3):
                    d = judge.get((cond, m, rep))
                    if not d: continue
                    rows = [(d[(i, e)][0], cat) for (mm, i, e), (k, cat) in gt.items()
                            if mm == m and (kind == "all" or k == kind) and (i, e) in d]
                    mt = metrics(rows)
                    if mt: per_rep.append(mt)
                if not per_rep: continue
                w.writerow([m, kind, cond, len(per_rep),
                            fmt([x[0] for x in per_rep]), fmt([x[1] for x in per_rep]),
                            fmt([x[2] for x in per_rep]), fmt([x[3] for x in per_rep]),
                            per_rep[0][4], per_rep[0][5], per_rep[0][6]])

# ------------------------------------------------------------------ majority label over reps (for B, C, flips)
def majority(cond, m):
    votes = defaultdict(list); reasons = defaultdict(list)
    for rep in (1, 2, 3):
        d = judge.get((cond, m, rep))
        if not d: continue
        for k, (lab, reason, ev) in d.items():
            votes[k].append(lab); reasons[k].append(f"[rep{rep}] {reason}")
    out = {}
    for k, v in votes.items():
        lab = "pass" if v.count("pass") > len(v) / 2 else "fail" if v.count("fail") > len(v) / 2 else "tie"
        out[k] = (lab, " || ".join(reasons[k]), v)
    return out

maj = {(c, m): majority(c, m) for c in CONDS for m in MODELS}

# ------------------------------------------------------------------ table B: acc split by caption mentioned the event
with open(f"{OUT}/table_b_by_mentioned.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "kind", "cap_cond", "mentioned", "n", "baseline_cond", "baseline_acc", "caption_acc", "delta",
                                   "baseline_pass_rate", "caption_pass_rate"])
    for m in MODELS:
        for cap in [c for c in CONDS if c.startswith("cap_") and c in mentioned]:
            for kind in ["all", "speech", "silent", "sounding"]:
                for men in (True, False):
                    for base in BASELINES:
                        keys = [(mm, i, e) for (mm, i, e), (k, cat) in gt.items()
                                if mm == m and (kind == "all" or k == kind)
                                and mentioned[cap].get((mm, i, e)) is men
                                and (i, e) in maj[(base, m)] and (i, e) in maj[(cap, m)]
                                and maj[(base, m)][(i, e)][0] != "tie" and maj[(cap, m)][(i, e)][0] != "tie"]
                        if not keys: continue
                        b = [correct(maj[(base, m)][(i, e)][0], gt[(mm, i, e)][1]) for mm, i, e in keys]
                        c = [correct(maj[(cap, m)][(i, e)][0], gt[(mm, i, e)][1]) for mm, i, e in keys]
                        bp = [maj[(base, m)][(i, e)][0] == "pass" for mm, i, e in keys]
                        cp = [maj[(cap, m)][(i, e)][0] == "pass" for mm, i, e in keys]
                        w.writerow([m, kind, cap, men, len(keys), base, f"{sum(b)/len(b):.3f}", f"{sum(c)/len(c):.3f}",
                                    f"{(sum(c)-sum(b))/len(b):+.3f}", f"{sum(bp)/len(bp):.3f}", f"{sum(cp)/len(cp):.3f}"])

# ------------------------------------------------------------------ table C: transition matrix + flips with rationale
TAGS = {
    "cites_caption":  r"\bcaption|described|transcript|tool (output|result)|according to the",
    "frames_direct":  r"\bframe|\bvisible|\bvisibly|\bcan be seen|\bshows?\b|\bobserv",
    "hand_side":      r"\bleft\b|\bright\b|\bwrong hand|\bside\b",
    "mouth":          r"\bmouth|\blip|\bspeak|\bsays?\b|\bsaying",
    "sound_words":    r"\bsound|\baudio|\bheard|\bnoise|\bslap sound|\bclap sound",
    "uncertain":      r"\bunclear|\bnot clear|\bcannot (be )?determin|\bambiguous|\bhard to",
}
def tag(text):
    t = text.lower()
    return ";".join(k for k, p in TAGS.items() if re.search(p, t))

trans = Counter()
with open(f"{OUT}/flips_rationale.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["model", "kind", "gt", "cap_cond", "baseline_cond", "item_id", "event_id", "event_label", "cap_mentioned",
                "baseline_label", "caption_label", "flip", "baseline_reason", "caption_reason", "baseline_tags", "caption_tags"])
    labels = {}
    for r in glob.glob("multi_agent/baseline_min3/*per_event*.csv"):
        for row in csv.DictReader(open(r, newline="")):
            labels[(row["item_id"], row["event_id"])] = row.get("event_label", "")
    for m in MODELS:
        for cap in [c for c in CONDS if c.startswith("cap_")]:
            for base in BASELINES:
                for (mm, i, e), (kind, cat) in gt.items():
                    if mm != m: continue
                    b = maj[(base, m)].get((i, e)); c = maj[(cap, m)].get((i, e))
                    if not b or not c or b[0] == "tie" or c[0] == "tie": continue
                    bc, cc = correct(b[0], cat), correct(c[0], cat)
                    trans[(m, kind, cap, base, bc, cc)] += 1
                    if bc != cc:
                        flip = "base_wrong->cap_right" if cc else "base_right->cap_wrong"
                        w.writerow([m, kind, cat, cap, base, i, e, labels.get((i, e), ""), mentioned.get(cap, {}).get((mm, i, e), ""),
                                    b[0], c[0], flip, b[1], c[1], tag(b[1]), tag(c[1])])

with open(f"{OUT}/table_c_transition.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "kind", "cap_cond", "baseline_cond", "both_right", "base_wrong_cap_right", "base_right_cap_wrong", "both_wrong", "net_gain"])
    keys = sorted({k[:4] for k in trans})
    for m, kind, cap, base in keys:
        g = lambda bc, cc: trans[(m, kind, cap, base, bc, cc)]
        w.writerow([m, kind, cap, base, g(True, True), g(False, True), g(True, False), g(False, False), g(False, True) - g(True, False)])

# ------------------------------------------------------------------ table D: item (video) level V, FAIL as positive class (reproduces slide numbers)
# human item FAIL = any event gt_v_pass False; judge item FAIL = any V event label fail (events joined only)
def item_gt(m):
    per = defaultdict(list)
    for (mm, i, e), p in gt_all.items():
        if mm == m: per[i].append(p)
    return {i: not all(v) for i, v in per.items()}   # True = FAIL

def item_judge(d, items):
    per = defaultdict(list)
    for (i, e), (lab, _, _) in d.items():
        if i in items: per[i].append(lab)
    return {i: any(l == "fail" for l in v) for i, v in per.items()}

def prf(gtf, jf):
    keys = [i for i in gtf if i in jf]
    tp = sum(gtf[i] and jf[i] for i in keys); fp = sum((not gtf[i]) and jf[i] for i in keys)
    fn = sum(gtf[i] and not jf[i] for i in keys); tn = len(keys) - tp - fp - fn
    acc = (tp + tn) / len(keys) if keys else float("nan")
    p = tp / (tp + fp) if tp + fp else float("nan"); r = tp / (tp + fn) if tp + fn else float("nan")
    return acc, p, r, len(keys), tp + fn

with open(f"{OUT}/table_d_item_level.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "cond", "n_reps", "acc", "precision_FAIL", "recall_FAIL", "n_items", "n_gt_fail"])
    for m in MODELS:
        gtf = item_gt(m)
        for cond in CONDS:
            per_rep = []
            for rep in (1, 2, 3):
                d = judge.get((cond, m, rep))
                if d: per_rep.append(prf(gtf, item_judge(d, gtf)))
            if not per_rep: continue
            w.writerow([m, cond, len(per_rep), fmt([x[0] for x in per_rep]), fmt([x[1] for x in per_rep]),
                        fmt([x[2] for x in per_rep]), per_rep[0][3], per_rep[0][4]])

# ------------------------------------------------------------------ table E: right for the right reason?
# among items where human FAIL and judge FAIL (majority over reps): compare the SET of failed events
#   exact    : judge FAIL events == human FAIL events
#   superset : judge caught all human FAIL events but also failed >=1 human-PASS event
#   partial  : judge caught some but not all human FAIL events (may include extra)
#   miss     : judge FAIL events share nothing with human FAIL events -> right verdict, wrong reason
# also: false_fail = items human PASS but judge FAIL
with open(f"{OUT}/table_e_reason_match.csv", "w", newline="") as f, \
     open(f"{OUT}/wrong_reason_items.csv", "w", newline="") as f2:
    w = csv.writer(f); w.writerow(["model", "cond", "both_fail", "exact", "superset", "partial", "miss", "miss_rate", "false_fail", "extra_fail_events_on_present"])
    w2 = csv.writer(f2); w2.writerow(["model", "cond", "item_id", "human_fail_events", "judge_fail_events", "category", "judge_reasons_on_wrong_events"])
    for m in MODELS:
        hfail = defaultdict(set); hall = defaultdict(set)
        for (mm, i, e), p in gt_all.items():
            if mm != m: continue
            hall[i].add(e)
            if not p: hfail[i].add(e)
        for cond in CONDS:
            mj = maj[(cond, m)]
            jfail = defaultdict(set); jitems = set()
            for (i, e), (lab, reason, _) in mj.items():
                jitems.add(i)
                if lab == "fail": jfail[i].add(e)
            cnt = Counter(); extra = 0
            for i in hall:
                if i not in jitems: continue
                hf, jf = hfail[i], jfail[i]
                if not hf and jf: cnt["false_fail"] += 1; continue
                if not hf or not jf: continue
                cnt["both_fail"] += 1
                extra += len(jf - hf)
                if jf == hf: cat = "exact"
                elif hf <= jf: cat = "superset"
                elif hf & jf: cat = "partial"
                else: cat = "miss"
                cnt[cat] += 1
                if cat in ("miss", "superset", "partial"):
                    wrong = sorted(jf - hf)
                    w2.writerow([m, cond, i, ";".join(sorted(hf)), ";".join(sorted(jf)), cat,
                                 " ## ".join(f"{e}: {mj[(i, e)][1]}" for e in wrong)])
            bf = cnt["both_fail"]
            w.writerow([m, cond, bf, cnt["exact"], cnt["superset"], cnt["partial"], cnt["miss"],
                        f"{cnt['miss']/bf:.3f}" if bf else "", cnt["false_fail"], extra])

print("done ->", OUT)
