#!/usr/bin/env python3
"""Set A redesign (10/28, after listening): audibility filter on the ORIGINAL clips, natural negatives, mute_class filter.
Data only, no judge calls, no audio editing.

Audibility of one interval (original clip, 48 kHz mono):
  bg   = background RMS of the clip = median of 50 ms frame RMS over frames with no non-ambient annotated event and no
         Whisper speech (ambient classes: background, sizzling / boiling, kettle / mixer / appliance, hoover / fan)
  db   = 20 log10(RMS inside the interval / bg)
  peak = a librosa onset_strength local maximum inside [start - 0.05, end + 0.05] (envelope normalised to the clip max,
         height >= 0.10, prominence >= 0.07; same detector as panel_peak)
  AUDIBLE   : db >= 6 and peak          INAUDIBLE : db < 3 and no peak          middle : everything else (dropped)

annot_inaudible items (A axis, ORIGINAL clip, no editing, no sham): PASS prompt + ", and a '<class>' sound can be heard.";
GT FAIL for the claim (and for a prompt event that names this class as its sound). Two candidate groups:
  annotated : the class has HD-EPIC-Sounds annotations in the clip and ALL of its in-clip intervals are INAUDIBLE
  visual    : the class has NO annotation in the clip, the prompt has a visible action whose typical sound is the class
              (verb map below), and the audio in ALL of that action's occurrence intervals is INAUDIBLE
Caps: <= 2 classes per clip (rarer classes first), <= 60 per class (clips with fewer pairs first, then seed 1028 order).
mute_class: keep pairs whose intervals are all AUDIBLE; drop a class with < 10 kept pairs.

  python gepa_stage2/audibility_1028.py intervals   # per-interval table + per-class AUDIBLE / middle / INAUDIBLE counts
  python gepa_stage2/audibility_1028.py build       # annot_inaudible items, mute_class filter, listen_sample_v2
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import make_mute_class as M

OUT = M.H / "hdepic_annot_inaudible_1028"
W = OUT / "work"
SR = 48000
FRAME = 0.05
AUD_DB, INAUD_DB, PEAK_TOL = 6.0, 3.0, 0.05
PEAK_MIN_REL, PEAK_PROM = 0.10, 0.07
CAP_PER_CLASS, CAP_PER_CLIP, MIN_MUTE = 60, 2, 10
SEED = 1028
TAPLIKE = re.compile(r"\btap\b|faucet", re.I)


def verb_class(verb, noun):
    """typical-sound class of a visible action (None if not one of the 7)."""
    v, n = verb.lower().strip(), (noun or "").lower()
    if v in ("open", "close", "open up") and re.search(r"fridge|cupboard|drawer|door|lid|freezer|oven|dishwasher|microwave", n):
        return "open / close"
    if v in ("cut", "slice", "chop", "cut off", "dice", "mince"):
        return "cut / chop"
    if v in ("stir", "mix", "whisk"):
        return "stir / mix / whisk"
    if (v in ("turn on", "turn off") and TAPLIKE.search(n)) or v in ("rinse", "wash"):
        return "water"
    if v in ("wipe", "scrub", "scrape", "scour") and "nose" not in n:
        return "scrub / scrape / scour / wipe"
    if v in ("slide", "push"):
        return "slide object"
    if v in ("walk", "step"):
        return "footstep"
    return None


def mono(path):
    x = M.read_audio(path)
    return x.mean(1)


def onset_peaks(y):
    import librosa
    from scipy.signal import find_peaks
    hop = 512
    env = librosa.onset.onset_strength(y=y.astype(np.float32), sr=SR, hop_length=hop)
    if not len(env) or env.max() <= 0:
        return np.array([])
    idx, _ = find_peaks(env / env.max(), height=PEAK_MIN_REL, prominence=PEAK_PROM)
    return idx * hop / SR


def bg_rms(y, events, speech):
    n = int(FRAME * SR)
    fr = y[: len(y) // n * n].reshape(-1, n)
    r = np.sqrt((fr.astype(np.float64) ** 2).mean(1))
    t = (np.arange(len(r)) + 0.5) * FRAME
    ok = np.ones(len(r), bool)
    for e in events:
        if e["cls"] not in M.AMBIENT:
            ok &= ~((t >= e["t0"]) & (t <= e["t1"]))
    for s, e in speech:
        ok &= ~((t >= s) & (t <= e))
    if ok.sum() >= 0.1 * len(r):
        return float(np.median(r[ok])), "non_event_median", float(ok.mean())
    return float(np.percentile(r, 20)), "p20_all_frames", float(ok.mean())


def judge(y, bg, peaks, s, e):
    seg = y[int(s * SR):int(np.ceil(e * SR))]
    rms = float(np.sqrt(np.mean(seg.astype(np.float64) ** 2))) if len(seg) else 0.0
    db = 20 * np.log10(max(rms, 1e-12) / max(bg, 1e-12))
    pk = bool(((peaks >= s - PEAK_TOL) & (peaks <= e + PEAK_TOL)).any())
    lab = "AUDIBLE" if db >= AUD_DB and pk else ("INAUDIBLE" if db < INAUD_DB and not pk else "middle")
    return dict(db=round(float(db), 2), peak=pk, audibility=lab)


def stage_intervals(a):
    ann = pd.read_csv(M.ANN)
    items = {x["item_id"]: x for x in json.load(open(M.PILOT / "items_hdepic_medium_with_clips_v2.json"))}
    rows = []
    for c in M.load_clips():
        y = mono(c["orig"])
        events = M.clip_events(ann, c)
        speech = M.speech_segments(c["key"])
        bg, bgsrc, frac = bg_rms(y, events, speech)
        peaks = onset_peaks(y)
        base = dict(clip=c["key"], kind=c["kind"], split=c["split"], bg_rms=bg, bg_source=bgsrc, bg_frame_frac=round(frac, 3))
        for e in events:                                       # annotated intervals of the 7 classes
            if e["cls"] in M.CLASSES:
                rows.append({**base, "group": "annotated", "cls": e["cls"], "t0": round(e["t0"], 3), "t1": round(e["t1"], 3),
                             "edge": e["edge"], **judge(y, bg, peaks, e["t0"], e["t1"])})
        if c["kind"] == "medium":                              # visible actions of the PASS prompt (medium items only)
            it = items[c["pass_item"]]
            for k, ev in enumerate(it["events"]):
                cl = verb_class(ev.get("verb", ""), ev.get("noun", ""))
                if cl is None:
                    continue
                d = ev["t"][1] - ev["t"][0]
                for o in (ev.get("occurrences") or [ev["t"][0]]):
                    rows.append({**base, "group": "visual", "cls": cl, "t0": round(o, 3), "t1": round(o + d, 3), "edge": False,
                                 "event_index": k, "verb": ev.get("verb"), "noun": ev.get("noun"), "event_kind": ev.get("kind"),
                                 **judge(y, bg, peaks, o, o + d)})
        print(f"[intervals] {c['key']} bg {bg:.5f} ({bgsrc}, {frac:.2f}) peaks {len(peaks)}", flush=True)
    W.mkdir(parents=True, exist_ok=True)
    d = pd.DataFrame(rows)
    d.to_csv(W / "intervals.csv", index=False)
    t = d[d.group == "annotated"].groupby(["cls", "audibility"]).size().unstack(fill_value=0)[["AUDIBLE", "middle", "INAUDIBLE"]]
    t["n"] = t.sum(1)
    print("\nannotated intervals in the original clips (all v3 clips):\n", t.to_string())
    print("\nvisual-action occurrence intervals:\n", d[d.group == "visual"].groupby(["cls", "audibility"]).size().unstack(fill_value=0).to_string())


def stage_build(a):
    d = pd.read_csv(W / "intervals.csv")
    clips = {c["key"]: c for c in M.load_clips()}
    rng = np.random.default_rng(SEED)
    # ---- candidates per (clip, class)
    cand = []
    ann = d[d.group == "annotated"].groupby(["clip", "cls"])
    annotated_keys = set(ann.groups)
    for (clip, cl), g in ann:
        if (g.audibility == "INAUDIBLE").all():
            cand.append(dict(clip=clip, cls=cl, group="annotated", sound_annotation=True, n_intervals=len(g),
                             intervals=g[["t0", "t1"]].values.round(3).tolist(), db=g.db.round(2).tolist()))
    vis = d[d.group == "visual"].groupby(["clip", "cls"])
    for (clip, cl), g in vis:
        if (clip, cl) in annotated_keys:                       # annotated classes are decided by their annotations
            continue
        if (g.audibility == "INAUDIBLE").all():
            cand.append(dict(clip=clip, cls=cl, group="visual", sound_annotation=False, n_intervals=len(g),
                             intervals=g[["t0", "t1"]].values.round(3).tolist(), db=g.db.round(2).tolist(),
                             actions=sorted(set(f"{v} {n}" for v, n in zip(g.verb, g.noun)))))
    for r in cand:
        r.update(kind=clips[r["clip"]]["kind"], split=clips[r["clip"]]["split"])
    print("annot_inaudible candidates before caps:\n", pd.DataFrame(cand).groupby(["cls", "group"]).size().unstack(fill_value=0).to_string())
    # ---- caps
    ncls = Counter(r["cls"] for r in cand)
    by_clip = defaultdict(list)
    for r in cand:
        by_clip[r["clip"]].append(r)
    kept, removed = [], []
    for k, rs in by_clip.items():
        rs = sorted(rs, key=lambda r: (ncls[r["cls"]], r["cls"]))
        kept += rs[:CAP_PER_CLIP]
        removed += [{**r, "cap": "classes_per_clip"} for r in rs[CAP_PER_CLIP:]]
    per_clip = Counter(r["clip"] for r in kept)
    order = dict(zip(sorted(per_clip), rng.permutation(len(per_clip))))
    final = []
    for cl in M.CLASSES:
        rs = sorted([r for r in kept if r["cls"] == cl], key=lambda r: (per_clip[r["clip"]], order[r["clip"]]))
        final += rs[:CAP_PER_CLASS]
        removed += [{**r, "cap": "pairs_per_class"} for r in rs[CAP_PER_CLASS:]]
    # ---- items (same construction as the v2 _A / hdfoot / mute_class items, on the ORIGINAL clip)
    prompts = {}
    items, man = [], []
    for r in final:
        c = clips[r["clip"]]
        if c["prompt_src"] not in prompts:
            prompts[c["prompt_src"]] = {x["item_id"]: x for x in json.load(open(c["prompt_src"]))}
        base = prompts[c["prompt_src"]][c["pass_item"]]
        prefix = "hdepic" if c["kind"] == "medium" else "hdepicmove"
        iid = f"{prefix}_{r['clip']}_inaud-{M.SLUG[r['cls']]}"
        it = json.loads(json.dumps(base))
        it.update(item_id=iid, canonical_item_id="real_hdepic_annot_inaudible", variant="annot_inaudible", a_fail_claim_v2=r["cls"])
        claim = {"id": "e_sound_claim", "modality": "sounding_action", "actor": "person_A", "action": f"a '{r['cls']}' sound",
                 "acting_body_part": "none", "target_body_part": "none", "target_sound": f"a '{r['cls']}' sound",
                 "definition": f"A '{r['cls']}' sound is audible at some point in the clip; its source does not need to be visible."}
        it["events"].append(claim)
        it.setdefault("content", {})["e_sound_claim"] = {k: v for k, v in claim.items() if k != "id"}
        tf = "generated_prompt" if "generated_prompt" in it else "prompt"
        it[tf] = it[tf].rstrip().rstrip(".") + f", and a '{r['cls']}' sound can be heard."
        gt, named = {}, []
        for k, e in enumerate(it["events"]):
            if e.get("modality") != "sounding_action":
                continue
            is_cls = f"'{r['cls']}'" in str(e.get("target_sound", ""))
            if is_cls and e["id"] != "e_sound_claim":
                named.append(e["id"])
            gt[f"event_{k + 1}"] = "no" if is_cls else "yes"
        items.append(it)
        ev = OUT / "eval" / iid / f"{iid}_v1_raw.mp4"
        ev.parent.mkdir(parents=True, exist_ok=True)
        if not ev.exists():
            ev.symlink_to(c["orig"])
        man.append(dict(uid=f"hdai|{iid}|A", item_id=iid, clip=r["clip"], kind=r["kind"], split=r["split"], cls=r["cls"],
                        variant="annot_inaudible", group=r["group"], sound_annotation=r["sound_annotation"], n_intervals=r["n_intervals"],
                        intervals=r["intervals"], db=r["db"], actions=r.get("actions"), prompt_named_class_events=named, gt=gt,
                        item_text=it[tf], window=r["intervals"][0], video=c["orig"], eval_video=str(ev)))
    # validate GT ids against the scoring events
    import new_eval as NE
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    for m in man:
        ok = {x["event_id"] for x in NE.build_scoring_events(metas[m["item_id"]]) if x.get("has_audio")}
        assert set(m["gt"]) == ok, (m["item_id"], m["gt"], ok)
    json.dump(items, open(OUT / "prompts.json", "w"), indent=1)
    M_ = OUT / "manifest.jsonl"
    with open(M_, "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    pd.DataFrame(removed).to_csv(W / "cap_removed.csv", index=False)
    tab = pd.DataFrame(man).groupby(["cls", "group"]).size().unstack(fill_value=0)
    print("\nannot_inaudible after caps:\n", tab.to_string())
    print("removed by caps:", Counter((r["cls"], r["cap"]) for r in removed))

    # ---- mute_class filter: keep pairs whose replaced intervals are all AUDIBLE
    mc = [json.loads(l) for l in open(M.OUT / "manifest.jsonl")]
    aud = d[d.group == "annotated"].set_index(["clip", "cls", "t0", "t1"]).audibility
    keep_pairs, stat = set(), []
    for r in mc:
        if r["variant"] != "mute_class":
            continue
        # replaced intervals are merged in-clip annotated intervals; take all annotations of the class in the clip
        labs = d[(d["group"] == "annotated") & (d["clip"] == r["clip"]) & (d["cls"] == r["cls"])].audibility
        all_aud = len(labs) > 0 and (labs == "AUDIBLE").all()
        stat.append(dict(cls=r["cls"], clip=r["clip"], all_audible=all_aud, n=len(labs), n_audible=int((labs == "AUDIBLE").sum()),
                         n_middle=int((labs == "middle").sum()), n_inaudible=int((labs == "INAUDIBLE").sum())))
        if all_aud:
            keep_pairs.add((r["clip"], r["cls"]))
    st = pd.DataFrame(stat)
    per = st.groupby("cls").all_audible.agg(["size", "sum"]).rename(columns={"size": "pairs", "sum": "all_audible"})
    per["kept_in_set"] = per.all_audible >= MIN_MUTE
    print("\nmute_class pairs with all intervals AUDIBLE:\n", per.to_string())
    surviving = set(per.index[per.kept_in_set])
    kept_rows = [r for r in mc if (r["clip"], r["cls"]) in keep_pairs and r["cls"] in surviving]
    with open(M.OUT / "manifest_audible_1028.jsonl", "w") as f:          # new file; manifest.jsonl is not touched
        for r in kept_rows:
            f.write(json.dumps({**r, "audibility_filter": "all intervals AUDIBLE"}) + "\n")
    st.to_csv(W / "mute_class_audibility.csv", index=False)
    per.to_csv(W / "mute_class_audibility_per_class.csv")
    # ---- listen_sample_v2
    ls = OUT / "listen_sample_v2"
    ls.mkdir(parents=True, exist_ok=True)
    lines = ["# listen_sample_v2", "", "## annot_inaudible (original clip; the item claims the sound can be heard; GT FAIL)", "",
             "| class | group | clip | intervals (s) | dB vs background | actions | item text |", "|---|---|---|---|---|---|---|"]
    mf = pd.DataFrame(man)
    for cl in M.CLASSES:
        g = mf[mf.cls == cl]
        ga, gv = g[g.group == "annotated"], g[g.group == "visual"]
        na = min(len(ga), 3 if len(gv) >= 2 else 5)
        pick = list(ga.sample(na, random_state=SEED).index) + list(gv.sample(min(5 - na, len(gv)), random_state=SEED).index)
        for i in pick:
            r = mf.loc[i]
            link = ls / f"inaudible__{M.SLUG[cl]}__{r['group']}__{r['clip']}.mp4"
            if not link.exists():
                link.symlink_to(r["video"])
            iv = ", ".join(f"{a:.2f}-{b:.2f}" for a, b in r["intervals"])
            acts = "; ".join(r["actions"]) if isinstance(r["actions"], list) else "-"
            lines.append(f"| {cl} | {r['group']} | {r['clip']} | {iv} | {', '.join(f'{x:.1f}' for x in r['db'])} | {acts} | {r['item_text']} |")
    lines += ["", "## mute_class (all intervals AUDIBLE): mute_class clip + original", "",
              "| class | clip | replaced intervals (s) | files |", "|---|---|---|---|"]
    kr = pd.DataFrame([r for r in kept_rows if r["variant"] == "mute_class"])
    for cl in sorted(surviving):
        g = kr[kr.cls == cl]
        for _, r in g.sample(min(3, len(g)), random_state=SEED).iterrows():
            for var, vid in (("mute_class", r["video"]), ("original", r["orig_video"])):
                link = ls / f"mute__{M.SLUG[cl]}__{r['clip']}__{var}.mp4"
                if not link.exists():
                    link.symlink_to(vid)
            lines.append(f"| {cl} | {r['clip']} | {', '.join(f'{a:.2f}-{b:.2f}' for a, b in r['intervals'])} | "
                         f"mute__{M.SLUG[cl]}__{r['clip']}__{{mute_class,original}}.mp4 |")
    (ls / "README.md").write_text("\n".join(lines) + "\n")
    print(f"-> {ls}: {len(list(ls.glob('*.mp4')))} clips")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["intervals", "build"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
