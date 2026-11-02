#!/usr/bin/env python3
# Replaced by t2av_eval/data/mute_anchor.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""HD-EPIC "mute_anchor" variant (10/28). Data only, no judge calls.

Anchors = clean action-sound pairs from real_av_pilot/build_items.py (find_anchors, imported, not copied): verb class
close (4, open / close), cut / slice / chop (7, cut / chop), press (21, beep), turn-off tap (8 with noun class tap, water).
An anchor is used when it lies inside a v3 medium clip AND is an occurrence of a sounding event of that clip's PASS prompt.

Loudness: "dB above the clip median" = 20 log10(rms_ratio) of the 10/08 anchor-audibility analysis
(real_av_pilot/analysis/anchor_audibility/scores_db.csv, column db_margin; window_tiers 'clear' = db_min >= 20).
That analysis' script is not on disk. Stored values are used where they exist (matched by clip, event, sound onset);
otherwise (turn-off tap, P03-P09) a re-implementation is used and marked db_source=reimpl:
  RMS of the 0.2 s after the sound onset / median 50 ms frame RMS of the clip (16 kHz mono)
  (reproduces the stored values to a median 1.2 dB, corr 0.93 on 60 stored anchors; not exact)
  turn-off tap: the moment that matters is the water STOPPING, so the 0.2 s window is the last 0.2 s before the sound end.
Keep anchors with dB >= 20.

mute_anchor clip: only that anchor's paired sound segment [s_st, s_en] (in-clip part) is replaced with background fill
(make_mute_class: nearest clean 1 s within 3 s, else quietest clean 1 s; looped, RMS-matched, 50 ms fades). Everything
else is unchanged. Item = the clip's PASS item unchanged (no added clause); A GT of the anchor's prompt event = FAIL, all
other sounding events PASS. Sham: the same replacement on one equal-length interval with no non-ambient annotated
sound and no speech (GT unchanged, PASS). Original = positive. Other annotated sounds overlapping the muted segment are
recorded (overlap_other), not used to exclude.

  python gepa_stage2/make_mute_anchor.py anchors      # v3 anchors + dB -> work/anchors.csv
  python gepa_stage2/make_mute_anchor.py build        # clips, items, manifest, listen_sample_v3
  python gepa_stage2/make_mute_anchor.py p3p9         # anchor counts P03-P09 (no audio on SCC -> no dB)
  python gepa_stage2/make_mute_anchor.py build_p3p9   # 11/01: the same construction on the P03-P09 holdout clips
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, importlib.util, json, subprocess, sys
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import make_mute_class as M

PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
SCORES = PILOT / "analysis/anchor_audibility/scores_db.csv"
OUT = M.H / "hdepic_mute_anchor_1028"
W = OUT / "work"
DB_MIN = 20.0
ACLASS = {4: "close", 7: "cut / slice / chop", 21: "press", 8: "turn-off tap"}
SLUG = {"close": "close", "cut / slice / chop": "cut", "press": "press", "turn-off tap": "tapoff"}
REIMPL_WIN, REIMPL_FRAME, REIMPL_SR = 0.2, 0.05, 16000
MAX_COV = 0.40


def bi():
    spec = importlib.util.spec_from_file_location("build_items", PILOT / "build_items.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def audio16(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(path), "-threads", "2", "-vn", "-ac", "1", "-ar", str(REIMPL_SR),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def db_reimpl(y, s0, s1, tap):
    n = int(REIMPL_FRAME * REIMPL_SR)
    F = np.sqrt((y[: len(y) // n * n].reshape(-1, n) ** 2).mean(1))
    a, b = (s1 - REIMPL_WIN, s1) if tap else (s0, s0 + REIMPL_WIN)
    seg = y[max(0, int(a * REIMPL_SR)):int(b * REIMPL_SR)]
    return 20 * np.log10(max(np.sqrt(np.mean(seg ** 2)), 1e-12) / max(np.median(F), 1e-12))


def stage_anchors(a):
    B = bi()
    s, n = B.load_hdepic(["P01", "P02"])
    anc = B.find_anchors(s, n)
    anc = anc[anc.vc.isin(ACLASS)]
    items = {x["item_id"]: x for x in json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))}
    stored = pd.read_csv(SCORES)
    rows = []
    for c in M.load_clips():
        if c["kind"] != "medium":
            continue
        lo, hi = c["lo"], c["hi"]
        it = items[c["pass_item"]]
        g = anc[(anc.video_id == c["video_id"]) & (anc.a_st >= lo) & (anc.a_en <= hi) & (anc.s_st >= lo) & (anc.s_en <= hi + 5)]
        y = None
        for r in g.itertuples():
            # the prompt event this anchor is an occurrence of (same verb / noun, an occurrence start within 0.6 s)
            ev_idx = occ = None
            for k, e in enumerate(it["events"]):
                if e["kind"] != "sounding" or e["verb"] != r.verb or e["noun"] != r.noun:
                    continue
                for j, o in enumerate(e.get("occurrences") or [e["t"][0]]):
                    if abs((r.a_st - lo) - o) < 0.6:
                        ev_idx, occ = k, j
            s0, s1 = r.s_st - lo, min(r.s_en, hi) - lo
            rec = dict(clip=c["key"], split=c["split"], video_id=c["video_id"], nid=r.nid, aclass=ACLASS[r.vc], verb=r.verb, noun=r.noun,
                       a0=round(r.a_st - lo, 3), a1=round(r.a_en - lo, 3), s0=round(s0, 3), s1=round(s1, 3), sound=r.sound,
                       in_prompt=ev_idx is not None, event_idx=ev_idx, occ=occ)
            win = f"hdepic_{c['key']}"
            st = stored[(stored["window"] == win) & ((stored["t_sound"] - s0).abs() < 0.06)] if ev_idx is not None else stored.iloc[:0]
            if len(st):
                rec.update(db=float(st.db_margin.iloc[0]), db_source="stored_1008")
            else:
                y = audio16(c["orig"]) if y is None else y
                rec.update(db=round(float(db_reimpl(y, s0, s1, r.vc == 8)), 2), db_source="reimpl")
            rows.append(rec)
        print(f"[anchors] {c['key']}: {len(g)}", flush=True)
    W.mkdir(parents=True, exist_ok=True)
    d = pd.DataFrame(rows)
    d.to_csv(W / "anchors.csv", index=False)
    d["pass20"] = d.db >= DB_MIN
    print(d.groupby("aclass").agg(clean_pairs=("clip", "size"), in_prompt=("in_prompt", "sum"),
                                 pass20=("pass20", lambda x: int((x & d.loc[x.index, "in_prompt"]).sum())),
                                 reimpl=("db_source", lambda x: int((x == "reimpl").sum()))).to_string())


def stage_build(a):
    d = pd.read_csv(W / "anchors.csv")
    d = d[d.in_prompt & (d.db >= DB_MIN)].copy()
    ann = pd.read_csv(M.ANN)
    clips = {c["key"]: c for c in M.load_clips()}
    items = {x["item_id"]: x for x in json.load(open(M.EV / "hdepic_medium_prompts_v2.json"))}
    rng = np.random.default_rng(M.SEED)
    (OUT / "clips").mkdir(parents=True, exist_ok=True)
    man, prom, skipped = [], [], []
    for r in d.itertuples():
        c = clips[r.clip]
        x = M.read_audio(c["orig"])
        dur = len(x) / 48000
        events = M.clip_events(ann, c)
        speech = M.speech_segments(c["key"])
        iv = (max(0.0, r.s0), min(dur, r.s1))
        cov = (iv[1] - iv[0]) / dur
        if cov > MAX_COV:
            skipped.append(dict(clip=r.clip, nid=r.nid, aclass=r.aclass, reason=f"coverage {cov:.2f}"))
            continue
        pad = (iv[0] - M.FADE, iv[1] + M.FADE)
        overlap = sorted({e["cls"] for e in events if e["cls"] not in M.AMBIENT and e["cls"] != r.sound and M.overlaps((e["t0"], e["t1"]), pad)})
        amb = sorted({e["cls"] for e in events if e["cls"] in M.AMBIENT and M.overlaps((e["t0"], e["t1"]), pad)})
        reps = M.plan_replacements([iv], events, speech, x)
        # sham: one equal-length clean interval (no non-ambient annotated sound, no speech), away from the muted segment
        clean = M.clean_mask(len(x), events, speech)
        L = iv[1] - iv[0]
        opts = [round(float(s), 3) for s in np.arange(M.FADE + 0.05, dur - L - M.FADE - 0.05, 0.05)
                if not M.overlaps((s - M.FADE - 0.5, s + L + M.FADE + 0.5), pad) and clean[int((s - M.FADE) * 48000):int((s + L + M.FADE) * 48000)].all()]
        sham = None
        if opts:
            s = float(rng.choice(opts))
            sham = dict(interval=[round(s, 3), round(s + L, 3)], replace=M.plan_replacements([(s, s + L)], events, speech, x))
        stem = M.stem(c)
        tag = f"{SLUG[r.aclass]}-n{str(r.nid).split('_')[-1]}"
        out = {"mute_anchor": OUT / "clips" / f"{stem}_muteanchor-{tag}.mp4", "sham": OUT / "clips" / f"{stem}_shamanchor-{tag}.mp4"}
        if not out["mute_anchor"].exists():
            M.mux(c["orig"], M.apply(x, reps), out["mute_anchor"])
        if sham and not out["sham"].exists():
            M.mux(c["orig"], M.apply(x, sham["replace"]), out["sham"])
        base = items[c["pass_item"]]
        anchor_eid = f"event_{int(r.event_idx) + 1}"
        for var in ("mute_anchor", "sham", "original"):
            if var == "sham" and sham is None:
                continue
            iid = f"hdepic_{r.clip}_ma{ {'mute_anchor': '', 'sham': 'sham', 'original': 'orig'}[var] }-{tag}"
            it = json.loads(json.dumps(base))
            it.update(item_id=iid, canonical_item_id=f"real_hdepic_mute_anchor_{var}", variant=var)
            gt = {f"event_{k + 1}": ("no" if var == "mute_anchor" and f"event_{k + 1}" == anchor_eid else "yes")
                  for k, e in enumerate(it["events"]) if e.get("modality") == "sounding_action"}
            vid = out[var] if var != "original" else Path(c["orig"])
            ev = OUT / "eval" / iid / f"{iid}_v1_raw.mp4"
            ev.parent.mkdir(parents=True, exist_ok=True)
            if not ev.exists():
                ev.symlink_to(vid)
            prom.append(it)
            man.append(dict(uid=f"hdma|{iid}|A", item_id=iid, clip=r.clip, split=r.split, aclass=r.aclass, verb=r.verb, noun=r.noun,
                            nid=r.nid, variant=var, anchor_event=anchor_eid, occ=int(r.occ), db=r.db, db_source=r.db_source,
                            action=[r.a0, r.a1], sound=[round(iv[0], 3), round(iv[1], 3)], replaced_seconds=round(L, 3) if var != "original" else 0.0,
                            window=[round(iv[0], 3), round(iv[1], 3)] if var != "sham" else sham["interval"],
                            fill_source=[q["fill_source"] for q in (reps if var == "mute_anchor" else (sham["replace"] if var == "sham" else []))],
                            overlap_other=overlap, ambient_overlap=amb, gt=gt, item_text=it.get("generated_prompt"),
                            video=str(vid), eval_video=str(ev), orig_video=c["orig"]))
        print(f"[build] {r.clip} {r.aclass} {r.verb} {r.noun} db {r.db:.1f}", flush=True)
    import new_eval as NE
    metas = NE.build_item_meta_map(prom, modality_filter=None, item_overrides=None, relative_only=False)
    for m in man:
        ok = {x["event_id"] for x in NE.build_scoring_events(metas[m["item_id"]]) if x.get("has_audio")}
        assert set(m["gt"]) == ok, (m["item_id"], m["gt"], ok)
    json.dump(prom, open(OUT / "prompts.json", "w"), indent=1)
    with open(OUT / "manifest.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    pd.DataFrame(skipped).to_csv(W / "skipped.csv", index=False)
    mf = pd.DataFrame(man)
    print(mf.groupby(["aclass", "variant"]).size().unstack(fill_value=0).to_string())
    print("skipped:", Counter(s["reason"].split()[0] for s in skipped))
    # listen_sample_v3: 3 triples per anchor class
    ls = OUT / "listen_sample_v3"
    ls.mkdir(exist_ok=True)
    lines = ["# listen_sample_v3: mute_anchor / sham / original", "",
             "| anchor class | clip | action (s) | muted sound segment (s) | dB | item text |", "|---|---|---|---|---|---|"]
    mu = mf[mf.variant == "mute_anchor"]
    for ac in ACLASS.values():
        g = mu[mu.aclass == ac]
        g = g[g.item_id.map(lambda i: ((mf.variant == "sham") & (mf.item_id == i.replace("_ma-", "_masham-"))).any())] if len(g) > 3 else g
        for _, r in g.sample(min(3, len(g)), random_state=M.SEED).iterrows():
            for var in ("mute_anchor", "sham", "original"):
                q = mf[(mf["clip"] == r["clip"]) & (mf.nid == r["nid"]) & (mf.variant == var)]
                if len(q):
                    link = ls / f"{SLUG[ac]}__{r['clip']}__{var}.mp4"
                    if not link.exists():
                        link.symlink_to(q.iloc[0]["video"])
            lines.append(f"| {ac} | {r['clip']} | {r['action'][0]:.2f}-{r['action'][1]:.2f} | {r['sound'][0]:.2f}-{r['sound'][1]:.2f} | "
                         f"{r['db']:.1f} | {r['item_text']} |")
    (ls / "README.md").write_text("\n".join(lines) + "\n")
    print(f"-> {ls}: {len(list(ls.glob('*.mp4')))} clips")


def stage_p3p9(a):
    B = bi()
    parts = [f"P0{i}" for i in range(3, 10)]
    s, n = B.load_hdepic(parts)
    anc = B.find_anchors(s, n)
    anc = anc[anc.vc.isin(ACLASS)]
    anc["aclass"] = anc.vc.map(ACLASS)
    anc["part"] = anc.video_id.str[:3]
    t = anc.groupby(["part", "aclass"]).size().unstack(fill_value=0)
    t["total"] = t.sum(1)
    print(t.to_string())
    W.mkdir(parents=True, exist_ok=True)
    anc.to_csv(W / "anchors_P03_P09.csv", index=False)
    # same counts for P01-P02 over whole videos, for comparison with the v3 subset
    s2, n2 = B.load_hdepic(["P01", "P02"])
    a2 = B.find_anchors(s2, n2)
    a2 = a2[a2.vc.isin(ACLASS)]
    a2["aclass"] = a2.vc.map(ACLASS)
    a2["part"] = a2.video_id.str[:3]
    print(a2.groupby(["part", "aclass"]).size().unstack(fill_value=0).to_string())




def stage_build_p3p9(a):
    """11/01: the same mute_anchor construction on the P03-P09 holdout clips (automatic only, user 11/01).
    Anchors: real_av_holdout_p3p9_1028/anchors_db.csv (build_items.find_anchors inside the holdout windows, loudness = the
    re-implementation, which reads about 4 dB LOW against the stored 10/08 values: a 20 dB cut here is stricter than on P01/P02).
    Kept: the anchor is an occurrence of a sounding event of the window's PASS prompt (same verb / noun, an occurrence start
    within 0.6 s, as stage_anchors) and dB >= 20. Speech segments: Whisper segments with no_speech_prob < 0.5 from the 11/01
    gen_evidence hdA record of the window's PASS item. Output: real_av_holdout_p3p9_1028/mute_anchor_1101/."""
    HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
    OUTP = HO / "mute_anchor_1101"
    EVD = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/gen_evidence_1030/hdA")
    d = pd.read_csv(HO / "anchors_db.csv")
    d = d[d.aclass.isin(ACLASS.values())].copy()
    items = {x["item_id"]: x for x in json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))}
    prompts = {x["item_id"]: x for x in json.load(open(HO / "prompts_hdepic_p3p9.json"))}
    ann = pd.read_csv(M.ANN)
    rng = np.random.default_rng(M.SEED)
    (OUTP / "clips").mkdir(parents=True, exist_ok=True)
    man, prom, skipped, counts = [], [], [], []
    for r in d.itertuples():
        key = f"{r.video_id}_{int(round(r.lo * 100)):07d}"
        pid = f"hdepic_{key}_pass"
        it = items.get(pid)
        if it is None:
            skipped.append(dict(key=key, nid=r.nid, aclass=r.aclass, reason="no window item")); continue
        ev_idx = occ = None
        for k, e in enumerate(it["events"]):
            if e["kind"] != "sounding" or e["verb"] != r.verb or e["noun"] != r.noun:
                continue
            for j, o in enumerate(e.get("occurrences") or [e["t"][0]]):
                if abs(r.a0 - o) < 0.6:
                    ev_idx, occ = k, j
        counts.append(dict(participant=r.video_id[:3], aclass=r.aclass, in_prompt=ev_idx is not None, db=r.db))
        if ev_idx is None or r.db < DB_MIN:
            continue
        orig = it["clip_path"]
        c = dict(key=key, video_id=r.video_id, lo=float(r.lo), hi=float(r.hi), orig=orig)
        x = M.read_audio(orig)
        dur = len(x) / 48000
        events = M.clip_events(ann, c)
        recf = EVD / f"p3p9__{pid}.json"
        rec = json.load(open(recf)) if recf.exists() else {"whisper": {"segments": []}}
        speech = [(sg["start"], sg["end"]) for sg in rec["whisper"]["segments"] if sg.get("no_speech_prob", 1) < M.SPEECH_NSP]
        iv = (max(0.0, float(r.s0)), min(dur, float(r.s1)))
        cov = (iv[1] - iv[0]) / dur
        if cov > MAX_COV:
            skipped.append(dict(key=key, nid=r.nid, aclass=r.aclass, reason=f"coverage {cov:.2f}")); continue
        pad = (iv[0] - M.FADE, iv[1] + M.FADE)
        sound_cls = {"close": "open / close", "cut / slice / chop": "cut / chop", "press": "beep", "turn-off tap": "water"}[r.aclass]
        overlap = sorted({e["cls"] for e in events if e["cls"] not in M.AMBIENT and e["cls"] != sound_cls and M.overlaps((e["t0"], e["t1"]), pad)})
        amb = sorted({e["cls"] for e in events if e["cls"] in M.AMBIENT and M.overlaps((e["t0"], e["t1"]), pad)})
        reps = M.plan_replacements([iv], events, speech, x)
        clean = M.clean_mask(len(x), events, speech)
        L = iv[1] - iv[0]
        opts = [round(float(t), 3) for t in np.arange(M.FADE + 0.05, dur - L - M.FADE - 0.05, 0.05)
                if not M.overlaps((t - M.FADE - 0.5, t + L + M.FADE + 0.5), pad) and clean[int((t - M.FADE) * 48000):int((t + L + M.FADE) * 48000)].all()]
        sham = None
        if opts:
            t = float(rng.choice(opts))
            sham = dict(interval=[round(t, 3), round(t + L, 3)], replace=M.plan_replacements([(t, t + L)], events, speech, x))
        tag = f"{SLUG[r.aclass]}-n{str(r.nid).split('-')[-1]}"
        out = {"mute_anchor": OUTP / "clips" / f"{key}_muteanchor-{tag}.mp4", "sham": OUTP / "clips" / f"{key}_shamanchor-{tag}.mp4"}
        if not out["mute_anchor"].exists():
            M.mux(orig, M.apply(x, reps), out["mute_anchor"])
        if sham and not out["sham"].exists():
            M.mux(orig, M.apply(x, sham["replace"]), out["sham"])
        base = prompts[pid]
        anchor_eid = f"event_{int(ev_idx) + 1}"
        for var in ("mute_anchor", "sham", "original"):
            if var == "sham" and sham is None:
                continue
            iid = f"hdepic_{key}_ma{ {'mute_anchor': '', 'sham': 'sham', 'original': 'orig'}[var] }-{tag}"
            itp = json.loads(json.dumps(base))
            itp.update(item_id=iid, canonical_item_id=f"real_hdepic_mute_anchor_{var}", variant=var)
            gt = {f"event_{k + 1}": ("no" if var == "mute_anchor" and f"event_{k + 1}" == anchor_eid else "yes")
                  for k, e in enumerate(itp["events"]) if e.get("modality") == "sounding_action"}
            vid = out[var] if var != "original" else Path(orig)
            evp = OUTP / "eval" / iid / f"{iid}_v1_raw.mp4"
            evp.parent.mkdir(parents=True, exist_ok=True)
            if not evp.exists():
                evp.symlink_to(vid)
            prom.append(itp)
            man.append(dict(uid=f"hdma39|{iid}|A", item_id=iid, clip=key, participant=r.video_id[:3], aclass=r.aclass, verb=r.verb, noun=r.noun,
                            nid=r.nid, variant=var, anchor_event=anchor_eid, occ=int(occ), db=float(r.db), db_source="reimpl (reads ~4 dB low)",
                            action=[float(r.a0)], sound=[round(iv[0], 3), round(iv[1], 3)], replaced_seconds=round(L, 3) if var != "original" else 0.0,
                            window=[round(iv[0], 3), round(iv[1], 3)] if var != "sham" else sham["interval"],
                            fill_source=[q["fill_source"] for q in (reps if var == "mute_anchor" else (sham["replace"] if var == "sham" else []))],
                            overlap_other=overlap, ambient_overlap=amb, gt=gt, item_text=itp.get("generated_prompt") or itp.get("prompt"),
                            video=str(vid), eval_video=str(evp), orig_video=orig))
        print(f"[build_p3p9] {key} {r.aclass} {r.verb} {r.noun} db {r.db:.1f}", flush=True)
    import new_eval as NE
    metas = NE.build_item_meta_map(prom, modality_filter=None, item_overrides=None, relative_only=False)
    for m in man:
        okids = {x["event_id"] for x in NE.build_scoring_events(metas[m["item_id"]]) if x.get("has_audio")}
        assert set(m["gt"]) == okids, (m["item_id"], m["gt"], okids)
    json.dump(prom, open(OUTP / "prompts.json", "w"), indent=1)
    with open(OUTP / "manifest.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    (OUTP / "work").mkdir(exist_ok=True)
    pd.DataFrame(skipped).to_csv(OUTP / "work" / "skipped.csv", index=False)
    cd = pd.DataFrame(counts)
    cd["pass20"] = cd.in_prompt & (cd.db >= DB_MIN)
    cd["pass16"] = cd.in_prompt & (cd.db >= DB_MIN - 4)
    tab = cd.groupby(["participant", "aclass"]).agg(clean_pairs=("db", "size"), in_prompt=("in_prompt", "sum"), pass20=("pass20", "sum"), pass16=("pass16", "sum"))
    tab.to_csv(OUTP / "work" / "counts.csv")
    mf = pd.DataFrame(man)
    print(tab.to_string())
    print(mf.groupby(["participant", "variant"]).size().unstack(fill_value=0).to_string())
    print("skipped:", Counter(s_["reason"].split()[0] for s_ in skipped))
    ls = OUTP / "listen_sample"
    ls.mkdir(exist_ok=True)
    mu = mf[mf.variant == "mute_anchor"].copy()
    mu["has_sham"] = mu.item_id.map(lambda i: ((mf.variant == "sham") & (mf.item_id == i.replace("_ma-", "_masham-"))).any())
    pick = pd.concat([g.sample(min(2, len(g)), random_state=M.SEED) for _, g in mu[mu.has_sham].groupby("participant")])
    pick = pick.sample(min(10, len(pick)), random_state=M.SEED).sort_values(["participant", "clip"])
    lines = ["# P03-P09 mute_anchor listening sample (11/01): mute_anchor / sham / original", "",
             "| # | participant | class | clip | action start (s) | muted sound segment (s) | dB (reimpl) | files |", "|---|---|---|---|---|---|---|---|"]
    for k, (_, r) in enumerate(pick.iterrows(), 1):
        names = []
        for var in ("mute_anchor", "sham", "original"):
            q = mf[(mf["clip"] == r["clip"]) & (mf.nid == r["nid"]) & (mf.variant == var)]
            if len(q):
                link = ls / f"{k:02d}_{SLUG[r['aclass']]}__{r['clip']}__{var}.mp4"
                if not link.exists():
                    link.symlink_to(q.iloc[0]["video"])
                names.append(link.name)
        lines.append(f"| {k} | {r['participant']} | {r['aclass']} | {r['clip']} | {r['action'][0]:.2f} | {r['sound'][0]:.2f}-{r['sound'][1]:.2f} | {r['db']:.1f} | {', '.join(names)} |")
    (ls / "README.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


# ------------------------------------------------------------------ 10/28 fill check rebuild
def flam_fill_choice(x, clean, iv, query, scorer, sr=48000, step=0.1):
    """lowest-FLAM clean 1 s fill segment within 3 s before/after iv (clip-wide clean candidates if none within 3 s)."""
    L, s, e = int(M.FILL_LEN * sr), iv[0], iv[1]
    cs = np.concatenate([[0], np.cumsum(~clean)])
    ok = lambda a0: a0 >= 0 and a0 + L <= len(x) and cs[a0 + L] - cs[a0] == 0 and M.rms(x[a0:a0 + L]) > 1e-6
    near = [a0 for k in range(int((M.NEAR - M.FILL_LEN) / step) + 1) for a0 in
            (int((s - M.FADE - M.FILL_LEN - k * step) * sr), int((e + M.FADE + k * step) * sr)) if ok(a0)]
    cand, src = (near, "near_minflam") if near else ([a0 for a0 in range(0, len(x) - L, int(step * sr)) if ok(a0)
                                                      and not M.overlaps((a0 / sr, a0 / sr + 1), (s - M.FADE, e + M.FADE))], "global_minflam")
    sc = [scorer(x[a0:a0 + L].mean(1), query) for a0 in cand]
    i = int(np.argmin(sc))
    return cand[i], src, float(sc[i]), len(cand)


def stage_rebuild_fill(a):
    import soundfile as sf, tempfile
    sys.path.insert(0, str(HERE.parent / "Tool_Use"))
    import flam_audio as FA
    from obs_judge_1028 import FLAM_QUERY
    chk = pd.read_csv(W / "fill_check.csv")
    redo = chk[chk.fill_1s >= 0.98]
    man = [json.loads(l) for l in open(OUT / "manifest.jsonl")]
    ann = pd.read_csv(M.ANN)
    clips = {c["key"]: c for c in M.load_clips()}
    tmp = W / "fill_check"
    def scorer(y, q):
        f = tmp / "_cand.wav"
        sf.write(f, y, 48000)
        return FA.extract_flam_evidence(str(f), queries=[q], ckpt_path="/projectnb/ivc-ml/youngsun/.hf_cache/openflam", device="cuda",
                                        max_duration_sec=10.0, hop_sec=0.0)["queries"][0]["max_score"]
    old = W / "_superseded_fillcheck"
    old.mkdir(exist_ok=True)
    log = []
    for r in redo.itertuples():
        mu = next(m for m in man if m["item_id"] == r.item_id)
        sh = next((m for m in man if m["variant"] == "sham" and m["clip"] == mu["clip"] and m["nid"] == mu["nid"]), None)
        c = clips[mu["clip"]]
        x = M.read_audio(c["orig"])
        events, speech = M.clip_events(ann, c), M.speech_segments(c["key"])
        clean = M.clean_mask(len(x), events, speech)
        q = FLAM_QUERY[{"close": "open / close", "cut / slice / chop": "cut / chop"}[mu["aclass"]]]
        for m in [mu] + ([sh] if sh else []):
            iv = tuple(m["sound"]) if m["variant"] == "mute_anchor" else tuple(m["window"])
            a0, src, score, ncand = flam_fill_choice(x, clean, iv, q, scorer)
            rep = M.plan_replacements([iv], events, speech, x)[0]          # keeps target RMS / gain rule
            fr = M.rms(x[a0:a0 + int(M.FILL_LEN * 48000)])
            rep.update(fill_start=round(a0 / 48000, 3), fill_source=src, fill_dist=None, fill_rms=fr,
                       gain=float(np.clip(rep["target_rms"] / fr, 0.25, 4.0)) if fr > 0 else 1.0)
            v = Path(m["video"])
            if v.exists():
                v.rename(old / v.name)
            M.mux(c["orig"], M.apply(x, [rep]), v)
            m.update(fill_source=[src], fill_flam=round(score, 3), fill_candidates=ncand, rebuilt_1028="fill_check: old fill source FLAM >= 0.98")
            log.append(dict(item_id=m["item_id"], variant=m["variant"], fill_start=rep["fill_start"], fill_source=src, fill_flam=round(score, 3),
                            n_candidates=ncand, old_fill_1s=r.fill_1s if m["variant"] == "mute_anchor" else None))
            print(f"[rebuild] {m['item_id']} {src} fill {rep['fill_start']:.2f} flam {score:.3f} ({ncand} cand)", flush=True)
    with open(OUT / "manifest.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    pd.DataFrame(log).to_csv(W / "fill_rebuild.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["anchors", "build", "p3p9", "rebuild_fill", "build_p3p9"])
    globals()[f"stage_{ap.parse_args().stage}"](None)
