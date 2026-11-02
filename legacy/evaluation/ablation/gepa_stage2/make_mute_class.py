#!/usr/bin/env python3
# Replaced by t2av_eval/data/mute_class.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""HD-EPIC "mute_class" audio variant (10/28). Data only, no judge calls.

For each (clip, class) pair, EVERY annotated interval of that HD-EPIC-Sounds class inside the 25 s clip is replaced by
background noise: 50 ms fades, fill = nearest 1 s segment within 3 s before/after the interval that has no non-ambient
annotated event and no Whisper speech (so the ambient state continues), looped and RMS-matched to the clean surrounding
audio; fallback = the quietest clean 1 s of the clip (fill_source=global). Never digital silence. All other audio untouched.
A sham clip gets the same replacement on 1-2 intervals with no non-ambient annotated sound and no speech (GT stays PASS).

Pair rules (user, 10/28):
  classes: open / close, footstep, water, stir / mix / whisk, cut / chop, slide object, scrub / scrape / scour / wipe
  exclude a pair if any replaced interval (incl. fade margins) overlaps another non-ambient annotated event or a Whisper
  speech segment; ambient classes (background, sizzling / boiling, kettle / mixer / appliance, hoover / fan) are ignored
  for exclusion and recorded as ambient_overlap. coverage (replaced s / clip s) <= 0.40. Intervals crossing the clip edge:
  in-clip part only. Caps: <= 2 classes per clip, <= 60 pairs per class (prefer clips with fewer pairs).

Stages (each writes into OUT, never touches existing clips / caches / manifests):
  python gepa_stage2/make_mute_class.py clips      # clip list from manifests_v3 (all splits) -> OUT/work/clips.json
  python gepa_stage2/make_mute_class.py whisper    # GPU: faster-whisper large-v3-turbo on originals -> OUT/work/whisper/
  python gepa_stage2/make_mute_class.py plan       # pairs, exclusions, caps, sham intervals -> OUT/work/plan.jsonl
  python gepa_stage2/make_mute_class.py render     # wav edit + mux (video stream copied) -> OUT/clips/
  python gepa_stage2/make_mute_class.py flam       # GPU: FLAM residual check (10 s windows, hop 5 s) -> OUT/work/flam/
  python gepa_stage2/make_mute_class.py items      # prompts.json, eval symlinks, manifest.jsonl, counts, listen_sample/
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import argparse, json, os, re, subprocess, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
H = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic")
EV = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
ANN = PILOT / "annotations/HD_EPIC_Sounds.csv"
OUT = H / "hdepic_mute_class_1028"
W = OUT / "work"
SR_ANN = 48000
CLIP_S = 25.0
CLASSES = ["open / close", "footstep", "water", "stir / mix / whisk", "cut / chop", "slide object", "scrub / scrape / scour / wipe"]
AMBIENT = {"background", "sizzling / boiling", "kettle / mixer / appliance", "hoover / fan"}
FADE = 0.05
NEAR = 3.0
FILL_LEN = 1.0
MAX_COV = 0.40
CAP_CLASSES_PER_CLIP = 2
CAP_PAIRS_PER_CLASS = 60
SPEECH_NSP = 0.5            # speech segment = Whisper segment with no_speech_prob < 0.5 (= has_speech rule of the pipeline)
FLAM_CKPT = "/projectnb/ivc-ml/youngsun/.hf_cache/openflam"
SEED = 1028


def slug(c):
    return re.sub(r"[^a-z0-9]+", "", c.split("/")[0].strip().lower().replace(" ", ""))[:12]


SLUG = {c: slug(c) for c in CLASSES}            # open, footstep, water, stir, cut, slideobject, scrub


# ------------------------------------------------------------------ helpers
def merge(iv, gap=0.0):
    iv = sorted([list(x) for x in iv])
    out = []
    for s, e in iv:
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def any_overlap(iv, others):
    return any(overlaps(iv, o) for o in others)


def read_audio(path):
    """float32 [n, ch] at 48 kHz from a video."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", "48000", "-f", "f32le", "-"],
                       check=True, capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2).copy()


def rms(x):
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0


# ------------------------------------------------------------------ stage: clips
def stage_clips(a):
    med = {x["item_id"]: x for x in json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))}
    mw = {(m["video"], int(round(m["t0"] * 1000))): m for m in json.load(open(PILOT / "annotations/move_windows_25s.json"))}
    pv2 = {x["item_id"]: x for x in json.load(open(EV / "hdepic_medium_prompts_v2.json"))}
    pmv = {x["item_id"]: x for x in json.load(open(EV / "hdepic_move_prompts.json"))}
    clips = {}
    for split in ("train", "val", "test"):
        for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{split}.jsonl"):
            m = json.loads(l)
            key = m["split_key"]
            if key in clips:
                continue
            if m["source"] in ("hdepic", "hdfoot"):
                pid = f"hdepic_{key}_pass"
                it = med[pid]
                vid, lo = it["video_id"], it["clip"][0]
                orig = H / "clips" / Path(it["clip_path"]).name          # file name rounds lo, item id truncates it
                prompt_item, kind = pv2[pid], "medium"
            elif m["source"] == "hdmove":
                pid = f"hdepicmove_{key}_pass"
                vid, suf = key.rsplit("_", 1)
                w = mw[(vid, int(suf))]
                lo = w["t0"]
                orig = H / "clips_move" / f"{key}_move.mp4"
                prompt_item, kind = pmv[pid], "move"
            else:
                continue
            assert orig.exists(), orig
            clips[key] = dict(key=key, kind=kind, split=split, video_id=vid, lo=lo, hi=lo + CLIP_S, orig=str(orig), pass_item=pid,
                              prompt_src=str(EV / ("hdepic_medium_prompts_v2.json" if kind == "medium" else "hdepic_move_prompts.json")))
    W.mkdir(parents=True, exist_ok=True)
    json.dump(list(clips.values()), open(W / "clips.json", "w"), indent=1)
    print(f"{len(clips)} clips: {Counter((c['kind'], c['split']) for c in clips.values())}")


def stem(c):
    """clip file stem without the variant suffix (same convention as clips/ and clips_move/)."""
    return Path(c["orig"]).stem.rsplit("_", 1)[0]


def load_clips():
    return json.load(open(W / "clips.json"))


# ------------------------------------------------------------------ stage: whisper
def stage_whisper(a):
    sys.path.insert(0, str(ABL / "Tool_Use"))
    import whisper_audio as WA
    d = W / "whisper"
    d.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(load_clips()):
        f = d / f"{c['key']}.json"
        if f.exists():
            continue
        ev = WA.extract_whisper_evidence(c["orig"], model_size="large-v3-turbo", device="cuda")
        json.dump(ev, open(f, "w"))
        if i % 20 == 0:
            print(f"[whisper] {i} {c['key']} has_speech={ev.get('has_speech')}", flush=True)


def speech_segments(key):
    ev = json.load(open(W / "whisper" / f"{key}.json"))
    return [(s["start"], s["end"]) for s in ev.get("segments", []) if s.get("no_speech_prob", 1) < SPEECH_NSP]


# ------------------------------------------------------------------ stage: plan
def clip_events(ann, c):
    g = ann[ann.video_id == c["video_id"]]
    t0 = g.start_sample / SR_ANN - c["lo"]
    t1 = g.stop_sample / SR_ANN - c["lo"]
    k = (t1 > 0) & (t0 < CLIP_S)
    return [dict(cls=cl, t0=max(0.0, a0), t1=min(CLIP_S, a1), edge=bool(a0 < 0 or a1 > CLIP_S))
            for cl, a0, a1 in zip(g["class"][k], t0[k], t1[k])]


def clean_mask(n, events, speech, sr=48000):
    """True where no non-ambient annotated event and no speech."""
    m = np.ones(n, bool)
    for e in events:
        if e["cls"] not in AMBIENT:
            m[int(e["t0"] * sr):int(np.ceil(e["t1"] * sr))] = False
    for s, e in speech:
        m[int(s * sr):int(np.ceil(e * sr))] = False
    return m


def pick_fill(iv, clean, x, sr=48000, step=0.05):
    """nearest clean FILL_LEN segment within NEAR s before / after iv; else the quietest clean FILL_LEN of the clip."""
    n, L = len(clean), int(FILL_LEN * sr)
    cs = np.concatenate([[0], np.cumsum(~clean)])
    is_clean = lambda a0: a0 >= 0 and a0 + L <= n and cs[a0 + L] - cs[a0] == 0
    s, e = iv
    best = None
    for k in range(int((NEAR - FILL_LEN) / step) + 1):
        d = k * step
        for a0 in (int((s - FADE - FILL_LEN - d) * sr), int((e + FADE + d) * sr)):     # before, after (never inside the fade)
            if is_clean(a0) and rms(x[a0:a0 + L]) > 1e-6:
                best = (a0, d)
                break
        if best:
            break
    if best:
        return best[0], "near", best[1]
    cands = [a0 for a0 in range(0, n - L, int(0.1 * sr)) if is_clean(a0) and rms(x[a0:a0 + L]) > 1e-6]
    if not cands:            # nothing clean at all: quietest 1 s that avoids the interval itself
        cands = [a0 for a0 in range(0, n - L, int(0.1 * sr)) if not overlaps((a0 / sr, a0 / sr + FILL_LEN), (s - FADE, e + FADE))
                 and rms(x[a0:a0 + L]) > 1e-6]
        src = "global_unclean"
    else:
        src = "global"
    a0 = min(cands, key=lambda a: rms(x[a:a + L]))
    return a0, src, None


def target_rms(iv, clean, x, sr=48000):
    """RMS of the clean audio within NEAR s around the interval (outside fades); else the 0.5 s next to it."""
    s, e = iv
    a, b = max(0, int((s - FADE - NEAR) * sr)), int((s - FADE) * sr)
    c, d = int((e + FADE) * sr), min(len(x), int((e + FADE + NEAR) * sr))
    seg = np.concatenate([x[a:b][clean[a:b]], x[c:d][clean[c:d]]])
    if len(seg) >= int(0.25 * sr):
        return rms(seg), "clean_surround"
    seg = np.concatenate([x[max(0, int((s - FADE - 0.5) * sr)):max(0, int((s - FADE) * sr))], x[c:min(len(x), c + int(0.5 * sr))]])
    return rms(seg), "adjacent"


def plan_replacements(ivs, events, speech, x):
    clean = clean_mask(len(x), events, speech)
    reps = []
    for iv in ivs:
        a0, src, dist = pick_fill(iv, clean, x)
        tr, tsrc = target_rms(iv, clean, x)
        fr = rms(x[a0:a0 + int(FILL_LEN * 48000)])
        gain = float(np.clip(tr / fr, 0.25, 4.0)) if fr > 0 and tr > 0 else 1.0
        reps.append(dict(iv=[round(iv[0], 3), round(iv[1], 3)], fill_start=round(a0 / 48000, 3), fill_source=src, fill_dist=dist,
                         target_rms=tr, fill_rms=fr, gain=gain, target_src=tsrc))
    return reps


def stage_plan(a):
    ann = pd.read_csv(ANN)
    rng = np.random.default_rng(SEED)
    cand, excl = [], []
    for c in load_clips():
        events = clip_events(ann, c)
        speech = speech_segments(c["key"])
        x = read_audio(c["orig"])
        dur = len(x) / 48000
        for cl in CLASSES:
            mine = [e for e in events if e["cls"] == cl]
            if not mine:
                continue
            ivs = merge([(e["t0"], e["t1"]) for e in mine])
            pad = [(s - FADE, e + FADE) for s, e in ivs]
            others = [e for e in events if e["cls"] != cl and e["cls"] not in AMBIENT]
            amb = sorted({e["cls"] for e in events if e["cls"] in AMBIENT and any_overlap((e["t0"], e["t1"]), pad)})
            rec = dict(key=c["key"], kind=c["kind"], split=c["split"], cls=cl, n_instances=len(mine), n_intervals=len(ivs),
                       replaced_seconds=round(sum(e - s for s, e in ivs), 3), edge=any(e["edge"] for e in mine))
            rec["coverage"] = round(rec["replaced_seconds"] / dur, 4)
            why = []
            hit = sorted({o["cls"] for o in others if any_overlap((o["t0"], o["t1"]), pad)})
            if hit:
                why.append("overlap:" + "|".join(hit))
            if any(overlaps(sp, p) for sp in speech for p in pad):
                why.append("speech")
            if rec["coverage"] > MAX_COV:
                why.append("coverage")
            if why:
                excl.append({**rec, "reason": ";".join(why)})
                continue
            rec["ambient_overlap"] = amb
            rec["intervals"] = [[round(s, 3), round(e, 3)] for s, e in ivs]
            rec["replace"] = plan_replacements(ivs, events, speech, x)
            # sham: same total replaced seconds; 1 interval if one interval (fallback: 2 halves), else 2 halves
            clean = clean_mask(len(x), events, speech)
            for lens in ([[rec["replaced_seconds"]]] if len(ivs) == 1 else []) + [[rec["replaced_seconds"] / 2] * 2]:
                sham, taken = [], [(s - FADE, e + FADE) for s, e in ivs]
                for L in lens:
                    opts = []
                    for s in np.arange(FADE + 0.05, dur - L - FADE - 0.05, 0.05):
                        p = (s - FADE, s + L + FADE)
                        if any_overlap(p, taken):
                            continue
                        if clean[int(p[0] * 48000):int(p[1] * 48000)].all():
                            opts.append(round(float(s), 3))
                    if not opts:
                        sham = None
                        break
                    s = float(rng.choice(opts))
                    sham.append((s, s + L))
                    taken.append((s - FADE - 0.5, s + L + FADE + 0.5))
                if sham is not None:
                    break
            if sham is None:
                rec["sham"] = None
            else:
                sham = sorted(sham)
                rec["sham"] = dict(intervals=[[round(s, 3), round(e, 3)] for s, e in sham],
                                   ambient_overlap=sorted({e["cls"] for e in events if e["cls"] in AMBIENT and
                                                           any(overlaps((e["t0"], e["t1"]), (s - FADE, t + FADE)) for s, t in sham)}),
                                   replace=plan_replacements(sham, events, speech, x))
            cand.append(rec)
        print(f"[plan] {c['key']}: speech {len(speech)} segs; kept {sum(r['key'] == c['key'] for r in cand)}", flush=True)

    # caps: <= 2 classes per clip (keep the classes with fewer candidate pairs overall), then <= 60 per class
    # (prefer clips with fewer kept pairs, then a fixed random order)
    removed = []
    ncls = Counter(r["cls"] for r in cand)
    by_clip = defaultdict(list)
    for r in cand:
        by_clip[r["key"]].append(r)
    kept = []
    for k, rs in by_clip.items():
        rs = sorted(rs, key=lambda r: (ncls[r["cls"]], r["cls"]))
        kept += rs[:CAP_CLASSES_PER_CLIP]
        removed += [{**_short(r), "cap": "classes_per_clip"} for r in rs[CAP_CLASSES_PER_CLIP:]]
    per_clip = Counter(r["key"] for r in kept)
    order = {k: v for k, v in zip(sorted(per_clip), rng.permutation(len(per_clip)))}
    final = []
    for cl in CLASSES:
        rs = sorted([r for r in kept if r["cls"] == cl], key=lambda r: (per_clip[r["key"]], order[r["key"]]))
        final += rs[:CAP_PAIRS_PER_CLASS]
        removed += [{**_short(r), "cap": "pairs_per_class"} for r in rs[CAP_PAIRS_PER_CLASS:]]
    with open(W / "plan.jsonl", "w") as f:
        for r in final:
            f.write(json.dumps(r) + "\n")
    pd.DataFrame(excl).to_csv(W / "excluded_pairs.csv", index=False)
    pd.DataFrame(removed).to_csv(W / "cap_removed.csv", index=False)
    t = pd.DataFrame([dict(cls=r["cls"], kind=r["kind"]) for r in cand]).value_counts().unstack(fill_value=0)
    print("\neligible before caps:\n", t)
    print("excluded:", Counter(e["reason"].split(":")[0] for e in excl))
    print("removed by caps:", Counter(r["cap"] for r in removed))
    print("final:", Counter(r["cls"] for r in final), "no sham:", sum(r["sham"] is None for r in final))


def _short(r):
    return {k: r[k] for k in ("key", "kind", "split", "cls", "n_instances", "replaced_seconds", "coverage")}


def load_plan():
    return [json.loads(l) for l in open(W / "plan.jsonl")]


# ------------------------------------------------------------------ stage: render
def apply(x, reps, sr=48000):
    y = x.copy()
    L, f = int(FILL_LEN * sr), int(FADE * sr)
    xf = int(0.01 * sr)
    for r in reps:
        s, e = int(r["iv"][0] * sr), int(np.ceil(r["iv"][1] * sr))
        a, b = max(0, s - f), min(len(x), e + f)
        n = b - a
        src = x[int(r["fill_start"] * sr):int(r["fill_start"] * sr) + L] * r["gain"]
        # loop the 1 s fill with 10 ms crossfades at the seams
        fill = src.copy()
        ramp = np.linspace(0, 1, xf)[:, None]
        while len(fill) < n:
            fill = np.concatenate([fill[:-xf], fill[-xf:] * (1 - ramp) + src[:xf] * ramp, src[xf:]])
        fill = fill[:n]
        w = np.ones(n)
        w[:s - a] = np.linspace(0, 1, s - a) if s - a > 0 else w[:0]      # original fades out, fill fades in
        w[n - (b - e):] = np.linspace(1, 0, b - e) if b - e > 0 else w[n:]
        y[a:b] = x[a:b] * (1 - w[:, None]) + fill * w[:, None]
        assert rms(y[s:e]) > 0, "digital silence"
    return y


def mux(orig, y, out):
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=W, delete=False) as t:
        wav = t.name
    try:
        import soundfile as sf
        sf.write(wav, np.clip(y, -1, 1), 48000, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(orig), "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", str(out)], check=True)
    finally:
        os.remove(wav)


def stage_render(a):
    (OUT / "clips").mkdir(parents=True, exist_ok=True)
    clips = {c["key"]: c for c in load_clips()}
    for i, r in enumerate(load_plan()):
        c = clips[r["key"]]
        x = read_audio(c["orig"])
        for var, reps in (("muteclass", r["replace"]), ("sham", (r["sham"] or {}).get("replace"))):
            if not reps:
                continue
            out = OUT / "clips" / f"{stem(c)}_{var}-{SLUG[r['cls']]}.mp4"
            if out.exists():
                continue
            mux(c["orig"], apply(x, reps), out)
        if i % 20 == 0:
            print(f"[render] {i} {r['key']} {r['cls']}", flush=True)


# ------------------------------------------------------------------ stage: flam
def stage_flam(a):
    sys.path.insert(0, str(ABL / "Tool_Use"))
    import flam_audio as FA
    d = W / "flam"
    d.mkdir(parents=True, exist_ok=True)
    jobs = set()
    clips = {c["key"]: c for c in load_clips()}
    for r in load_plan():
        q = r["cls"]
        jobs.add((clips[r["key"]]["orig"], q))
        for var in ("muteclass", "sham"):
            p = OUT / "clips" / f"{stem(clips[r['key']])}_{var}-{SLUG[r['cls']]}.mp4"
            if p.exists():
                jobs.add((str(p), q))
    for i, (p, q) in enumerate(sorted(jobs)):
        f = d / f"{Path(p).stem}__{SLUG[q]}.json"
        if f.exists():
            continue
        ev = FA.extract_flam_evidence(p, queries=[flam_query(q)], ckpt_path=FLAM_CKPT, device="cuda", max_duration_sec=10.0, hop_sec=5.0)
        qr = ev["queries"][0]
        json.dump(dict(video=p, cls=q, query=qr["query"], model_duration=ev["model_duration"], num_frames=ev["num_frames"],
                       frame_scores=qr["frame_scores"]), open(f, "w"))
        if i % 25 == 0:
            print(f"[flam] {i}/{len(jobs)} {Path(p).name}", flush=True)


def flam_query(cls):
    """FLAM text for a class: 'a <first alternative> sound' (e.g. 'open / close' -> 'an open / close sound')."""
    return {"open / close": "a door or drawer opening or closing", "footstep": "footsteps", "water": "running water from a tap",
            "stir / mix / whisk": "stirring or whisking in a bowl", "cut / chop": "chopping with a knife on a cutting board",
            "slide object": "an object sliding on a surface", "scrub / scrape / scour / wipe": "scrubbing or wiping a surface"}[cls]


def flam_scores(path, cls):
    f = W / "flam" / f"{Path(path).stem}__{SLUG[cls]}.json"
    if not f.exists():
        return None
    d = json.load(open(f))
    s = np.asarray(d["frame_scores"])
    t = (np.arange(len(s)) + 0.5) * d["model_duration"] / len(s)
    return t, s


def max_in(ts, ivs, inside=True):
    t, s = ts
    m = np.zeros(len(t), bool)
    for a, b in ivs:
        m |= (t >= a) & (t <= b)
    m = m if inside else ~m
    return float(s[m].max()) if m.any() else float("nan")


# ------------------------------------------------------------------ stage: items
def stage_items(a):
    sys.path.insert(0, str(ABL))
    import new_eval as NE
    clips = {c["key"]: c for c in load_clips()}
    prompts = {}
    for c in clips.values():
        if c["prompt_src"] not in prompts:
            prompts[c["prompt_src"]] = {x["item_id"]: x for x in json.load(open(c["prompt_src"]))}
    plan = load_plan()
    # FLAM residuals. class median on original clips = median over original clips of the max score inside the annotated intervals
    for r in plan:
        o = flam_scores(clips[r["key"]]["orig"], r["cls"])
        r["flam_orig_in"] = max_in(o, r["intervals"]) if o else float("nan")
    med = {cl: float(np.nanmedian([r["flam_orig_in"] for r in plan if r["cls"] == cl] or [np.nan])) for cl in CLASSES}
    items, rows = [], []
    for r in plan:
        c = clips[r["key"]]
        base = prompts[c["prompt_src"]][c["pass_item"]]
        prefix = "hdepic" if c["kind"] == "medium" else "hdepicmove"
        tag = SLUG[r["cls"]]
        for var in ("mute_class", "sham", "original"):
            if var == "sham" and r["sham"] is None:
                continue
            vid = {"mute_class": OUT / "clips" / f"{stem(c)}_muteclass-{tag}.mp4",
                   "sham": OUT / "clips" / f"{stem(c)}_sham-{tag}.mp4", "original": Path(c["orig"])}[var]
            iid = f"{prefix}_{r['key']}_mc{ {'mute_class': '', 'sham': 'sham', 'original': 'orig'}[var] }-{tag}"
            it = json.loads(json.dumps(base))
            it["item_id"] = iid
            it["canonical_item_id"] = f"real_hdepic_mute_class_{var}"
            it["variant"] = var
            it["a_fail_claim_v2"] = r["cls"]
            claim = {"id": "e_sound_claim", "modality": "sounding_action", "actor": "person_A", "action": f"a '{r['cls']}' sound",
                     "acting_body_part": "none", "target_body_part": "none", "target_sound": f"a '{r['cls']}' sound",
                     "definition": f"A '{r['cls']}' sound is audible at some point in the clip; its source does not need to be visible."}
            it["events"].append(claim)
            it.setdefault("content", {})["e_sound_claim"] = {k: v for k, v in claim.items() if k != "id"}
            tf = "generated_prompt" if "generated_prompt" in it else "prompt"
            it[tf] = it[tf].rstrip().rstrip(".") + f", and a '{r['cls']}' sound can be heard."
            items.append(it)
            # A GT: claim event; prompt events whose target_sound names this class are also FAIL on the mute_class clip
            gt = {}
            named = []
            for k, e in enumerate(it["events"]):
                if e.get("modality") != "sounding_action":
                    continue
                sid = f"event_{k + 1}"              # scoring id = prompt-event order (checked against build_scoring_events below)
                is_cls = f"'{r['cls']}'" in str(e.get("target_sound", ""))
                if is_cls and e["id"] != "e_sound_claim":
                    named.append(e["id"])
                gt[sid] = "no" if var == "mute_class" and is_cls else "yes"
            if c["kind"] == "move" and not gt:
                gt = {}
            ivs = r["intervals"] if var == "mute_class" else (r["sham"]["intervals"] if var == "sham" else r["intervals"])
            ts = flam_scores(vid, r["cls"])
            rin = max_in(ts, ivs) if ts else float("nan")
            rout = max_in(ts, r["intervals"] if var != "sham" else r["intervals"] + r["sham"]["intervals"], inside=False) if ts else float("nan")
            reps = r["replace"] if var == "mute_class" else (r["sham"]["replace"] if var == "sham" else [])
            rows.append(dict(
                uid=f"hdmc|{iid}|A", item_id=iid, clip=r["key"], kind=c["kind"], split=c["split"], cls=r["cls"], variant=var,
                n_instances=r["n_instances"], n_intervals=r["n_intervals"], replaced_seconds=r["replaced_seconds"] if var != "original" else 0.0,
                coverage=r["coverage"] if var != "original" else 0.0, edge=r["edge"],
                ambient_overlap=r["ambient_overlap"] if var != "sham" else r["sham"]["ambient_overlap"],
                fill_source=sorted({x["fill_source"] for x in reps}) if reps else [],
                residual_in=rin, residual_out=rout, class_median_orig=med[r["cls"]],
                residual_outside=bool(var == "mute_class" and rout == rout and rout > med[r["cls"]]),
                item_text=it[tf], gt=gt, prompt_named_class_events=named,
                window=ivs[0] if var != "original" else r["intervals"][0], intervals=ivs,
                video=str(vid), eval_video=str(OUT / "eval" / iid / f"{iid}_v1_raw.mp4"), orig_video=c["orig"]))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    for row in rows:
        ok = {x["event_id"] for x in NE.build_scoring_events(metas[row["item_id"]]) if x.get("has_audio")}
        assert set(row["gt"]) == ok, (row["item_id"], row["gt"], ok)
    json.dump(items, open(OUT / "prompts.json", "w"), indent=1)
    for row in rows:
        p = Path(row["eval_video"])
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.symlink_to(row["video"])
    with open(OUT / "manifest.jsonl", "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    df = pd.DataFrame(rows)
    m = df[df.variant == "mute_class"]
    tab = m.groupby("cls").agg(pairs=("clip", "size"), medium=("kind", lambda k: (k == "medium").sum()), move=("kind", lambda k: (k == "move").sum()),
                               test=("split", lambda s: (s == "test").sum()), val=("split", lambda s: (s == "val").sum()), train=("split", lambda s: (s == "train").sum()),
                               ambient=("ambient_overlap", lambda a: sum(bool(x) for x in a)),
                               fill_global=("fill_source", lambda a: sum(any(s.startswith("global") for s in x) for x in a)),
                               named=("prompt_named_class_events", lambda a: sum(bool(x) for x in a)),
                               median_instances=("n_instances", "median"), median_replaced_s=("replaced_seconds", "median"),
                               residual_outside=("residual_outside", "sum"))
    tab["class_median_orig"] = [med[c] for c in tab.index]
    tab["sham"] = df[df.variant == "sham"].groupby("cls").size().reindex(tab.index).fillna(0).astype(int)
    tab.to_csv(OUT / "class_counts.csv")
    print(tab.to_string())
    listen(df)


def listen(df):
    """5 mute_class clips per class (half with ambient_overlap where possible) + their sham and original."""
    d = OUT / "listen_sample"
    d.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    m = df[df.variant == "mute_class"]
    lines = []
    for cl in CLASSES:
        g = m[m.cls == cl]
        amb, non = g[g.ambient_overlap.map(bool)], g[~g.ambient_overlap.map(bool)]
        na = min(len(amb), 3 if len(non) < 2 else 2 + (cl in CLASSES[::2]))
        pick = list(amb.sample(min(na, len(amb)), random_state=SEED).index) + list(non.sample(min(5 - na, len(non)), random_state=SEED).index)
        if len(pick) < 5:
            rest = g.drop(pick)
            pick += list(rest.sample(min(5 - len(pick), len(rest)), random_state=SEED).index)
        for i in pick:
            r = m.loc[i]
            for var in ("mute_class", "sham", "original"):
                s = df[(df["clip"] == r["clip"]) & (df.cls == cl) & (df.variant == var)]
                if not len(s):
                    continue
                s = s.iloc[0]
                link = d / f"{SLUG[cl]}__{r['clip']}__{var}.mp4"
                if not link.exists():
                    link.symlink_to(s.video)
            lines.append(f"| {cl} | {r['clip']} | {'; '.join(r.ambient_overlap) or '-'} | {r.n_instances} | "
                         f"{', '.join(f'{a:.2f}-{b:.2f}' for a, b in r.intervals)} | {r.residual_in:.3f} / {r.residual_out:.3f} "
                         f"(median {r.class_median_orig:.3f}){' FLAG' if r.residual_outside else ''} |")
    (d / "README.md").write_text("# listen sample (mute_class / sham / original per row)\n\nfiles: <class>__<clip>__<variant>.mp4\n\n"
                                 "| class | clip | ambient_overlap | n | replaced intervals (s, clip time) | FLAM in / out |\n|---|---|---|---|---|---|\n"
                                 + "\n".join(lines) + "\n")
    print(f"-> {d} ({len(lines)} mute_class clips)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["clips", "whisper", "plan", "render", "flam", "items"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
