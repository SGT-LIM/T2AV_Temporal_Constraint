#!/usr/bin/env python3
"""Observation-validation sets for pipeline v4 section 4 step 4 (10/28). Data and rendering only, no judge calls.

Panels (render_panel.py, pad 2 s, 7 frames) -> gepa_stage2/panels_1028/<variant>/<item_id>.png + panels_1028/manifest.jsonl
  avb_shift_early / avb_shift_late / avb_original : v3 test hdepic AVB rows; window = anchor event (GT AVB event):
        [min(visual start, sound start + shift_s), max(visual end, sound end + shift_s)]  (shift_s = 0 for originals)
  mute_class / mute_sham / mute_original          : hdepic_mute_class_1028 manifest; window = first replaced interval
        (mute_class and original: first replaced interval of the class; sham: first sham interval)
  tcr_order_swap / tcr_original                   : v3 test hdepic TCR rows; window = whole item span (all occurrences)
  tcc_count_off / tcc_original                    : v3 test hdmove TCC rows; window = whole item span (movement tracks)
Focus clips -> gepa_stage2/focus_1028/<mode>_centred/<variant>/<item_id>.mp4 + focus_1028/<mode>_centred/manifest.jsonl
  --focus-mode action (default, 10/28 rev 2): [action onset - 3, action end + 4] s for every variant, action = visible anchor event
        (items json t[0], t[1]; no end -> onset + 1 s). Sound times are not used for the window (GT leak); sound_inside only
        records afterwards whether the shifted GT sound falls in the cut (full / onset_only / offset_only / miss)
  --focus-mode sound (first version, kept for comparison):
  AVB shift + original rows: [onset - 1.5, onset + 1.5] s, audio and video, onset = GT sound onset of the anchor event in
  that clip (annotation sound_t[0] + shift_s). Re-encoded (libx264 crf 18, aac 128k) so the cut is frame exact.

  python gepa_stage2/obs_sets_1028.py list            # manifests only (no rendering)
  python gepa_stage2/obs_sets_1028.py sample          # 5 panels + 5 focus clips, symlinked into */sample/
  python gepa_stage2/obs_sets_1028.py all             # everything (after the layout check)
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"                  # SCC job has 4 cores (10/28: a run was killed at 5.4 cores); set before numpy/librosa import
FF_THREADS = ["-threads", "2"]            # every ffmpeg call: 2 threads for decode and encode
import argparse, json, re, subprocess, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_panel as RP

RA = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av")
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
MC = RA / "hdepic/hdepic_mute_class_1028/manifest.jsonl"
ASSOC = PILOT / "annotations/data/scene-and-object-movements/assoc_info.json"
PAN, FOC = HERE / "panels_1028", HERE / "focus_1028"
PAD, NFR, FOCUS_SOUND = 2.0, 7, 1.5
PRE_ACTION, POST_ACTION, NO_END = 3.0, 4.0, 1.0      # focus = [action onset - 3, action end + 4]; no end -> onset + 1
MODE = "action"


MUTE_PAD = 2.0


def action_window(ev):
    """[action onset - 3, action end + 4] of a visible items-json event (no end -> onset + 1 s)."""
    on = ev["t"][0]
    end = ev["t"][1] if len(ev.get("t") or []) > 1 and ev["t"][1] is not None else on + NO_END
    return [round(on - PRE_ACTION, 3), round(end + POST_ACTION, 3)]


def clip_file(rel):
    return str(RA / "hdepic" / Path(rel).parent.name / Path(rel).name)


def occ_span(ev):
    """[start, end] over all occurrences of one items-json event (occurrence start + first-occurrence duration)."""
    d = ev["t"][1] - ev["t"][0]
    occ = ev.get("occurrences") or [ev["t"][0]]
    return min(occ), max(o + d for o in occ)


def base(n):
    return re.sub(r"\d+$", "", n.strip().lower()).strip()


def build():
    man = [json.loads(l) for l in open(HERE / "manifests_v3/test.jsonl")]
    items = {x["item_id"]: x for x in json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))}
    rows, focus = [], []
    # ---- AVB shift + originals
    for m in man:
        if m["source"] != "hdepic" or m["axis"] != "AVB":
            continue
        it = items[m["item_id"]]
        shift = float(it.get("media", {}).get("shift_s", 0.0) or 0.0)
        keys = sorted(m["gt"], key=lambda k: int(k.split("_")[1]))
        ev = it["events"][int(keys[0].split("_")[1]) - 1]
        assert ev["kind"] == "sounding" and "sound_t" in ev, (m["item_id"], ev)
        s0, s1 = ev["sound_t"][0] + shift, ev["sound_t"][1] + shift
        var = {"original": "avb_original", "audio_shift_early": "avb_shift_early", "audio_shift_late": "avb_shift_late"}[m["variant"]]
        video = clip_file(it["clip_path"])
        rows.append(dict(variant=var, item_id=m["item_id"], uid=m["uid"], clip=m["split_key"], video=video, gt=m["gt"],
                         anchor_event=keys[0], all_gt_events=keys, shift_s=shift, visual_t=ev["t"], sound_t_shifted=[round(s0, 3), round(s1, 3)],
                         window=action_window(ev), pad=0.0,
                         window_rule="[action onset - 3, action end + 4] (visible anchor event; same rule as focus clips; no sound times)"))
        if MODE == "sound":
            on, src, fa, fb = s0, "GT: HD-EPIC-Sounds sound_t[0] + shift_s", s0 - FOCUS_SOUND, s0 + FOCUS_SOUND
        else:
            # one fixed action-based rule for every variant; sound times are NOT used (they would leak the GT)
            on = ev["t"][0]
            src = "GT visible action: items json event t[0] / t[1]"
            fa, fb = action_window(ev)
        inside = "full" if fa <= s0 and s1 <= fb else ("onset_only" if fa <= s0 <= fb else ("offset_only" if fa <= s1 <= fb else "miss"))
        focus.append(dict(variant=var, item_id=m["item_id"], uid=m["uid"], clip=m["split_key"], video=video, gt=m["gt"], anchor_event=keys[0],
                          shift_s=shift, focus_mode=MODE, onset=round(on, 3), onset_source=src, visual_t=ev["t"],
                          sound_t_shifted=[round(s0, 3), round(s1, 3)], sound_inside=inside, focus=[round(fa, 3), round(fb, 3)]))
    # ---- TCR order_swap + originals (whole item span)
    for m in man:
        if m["source"] != "hdepic" or m["axis"] != "TCR":
            continue
        it = items[m["item_id"]]
        sp = [occ_span(e) for e in it["events"]]
        rows.append(dict(variant={"order_swap": "tcr_order_swap", "original": "tcr_original"}[m["variant"]], item_id=m["item_id"], uid=m["uid"],
                         clip=m["split_key"], video=clip_file(it["clip_path"]), gt=m["gt"],
                         window=[round(min(s for s, _ in sp), 3), round(max(e for _, e in sp), 3)]))
    # ---- TCC count_off + originals on the movement set (whole item span from the movement tracks)
    gt = pd.read_csv(RA / "eval/hdepic_move_gt.csv").set_index("item_id")
    wins = {(w["video"], int(round(w["t0"] * 1000))): w for w in json.load(open(PILOT / "annotations/move_windows_25s.json"))}
    A = json.load(open(ASSOC))
    for m in man:
        if m["source"] != "hdmove":
            continue
        g = gt.loc[m["item_id"]]
        vid, suf = m["split_key"].rsplit("_", 1)
        w = wins[(vid, int(suf))]
        t0, t1 = float(w["t0"]), float(w["t0"]) + 25.0
        names = set(json.loads(g.move_starts_sec))
        segs = [t["time_segment"] for o in A[vid].values() if base(o["name"]) in names for t in o["tracks"]
                if t["time_segment"][0] >= t0 and t["time_segment"][1] <= t1]
        rows.append(dict(variant={"count_off": "tcc_count_off", "original": "tcc_original"}[m["variant"]], item_id=m["item_id"], uid=m["uid"],
                         clip=m["split_key"], video=g.clip_path, gt=m["gt"],
                         window=[round(min(s for s, _ in segs) - t0, 3), round(max(e for _, e in segs) - t0, 3)]))
    # ---- mute_class / sham / original
    if MC.exists():
        mc = [json.loads(l) for l in open(MC)]
        # ONE window per (clip, class), shared by mute_class / sham / original: first replaced interval of the class +- 2 s
        first = {(r["clip"], r["cls"]): r["intervals"][0] for r in mc if r["variant"] == "mute_class"}
        for r in mc:
            a0, b0 = first[(r["clip"], r["cls"])]
            rows.append(dict(variant={"mute_class": "mute_class", "sham": "mute_sham", "original": "mute_original"}[r["variant"]],
                             item_id=r["item_id"], uid=r["uid"], clip=r["clip"], video=r["video"], gt=r["gt"], cls=r["cls"],
                             window=[round(a0 - MUTE_PAD, 3), round(b0 + MUTE_PAD, 3)], pad=0.0, window_shared=True,
                             window_rule="[first replaced interval start - 2, end + 2] of the mute_class clip; same window for "
                                         "mute_class, sham and original of this (clip, class)"))
    else:
        print(f"[warn] {MC} not built yet: mute_class panels skipped")
    out = []
    for r in rows:
        r.setdefault("pad", PAD)
        r.setdefault("window_rule", "whole item span, pad 2 s")
        for mode in PANEL_MODES:                    # one panel per mode, both kept
            out.append({**r, "mode": mode, "panel": str(PAN / mode / r["variant"] / f"{r['item_id']}.png")})
    rows = out
    for f in focus:
        f["path"] = str(FOC / f"{MODE}_centred" / f["variant"] / f"{f['item_id']}.mp4")
    return rows, focus


def cut(video, a, b, out):
    dur = RP.probe_duration(video)
    a, b = max(0.0, a), min(dur, b)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-ss", f"{a:.3f}", "-i", str(video), *FF_THREADS, "-t", f"{b - a:.3f}", "-c:v", "libx264", "-crf", "18",
                    "-preset", "fast", "-c:a", "aac", "-b:a", "128k", str(out)], check=True)
    return [round(a, 3), round(b, 3)]


PANEL_MODES = ("panel_even", "panel_peak")
PEAK_RULE = ("audio-only onsets: local maxima of librosa onset_strength (norm. height >= 0.10, prominence >= 0.07), strongest first, >= 0.3 s apart, top 6; per peak frames at "
             "peak - 0.5 s and peak; thin line per peak on the waveform; < 2 peaks -> panel_even (fallback recorded)")
FRAME_RULE = ("auto (render_panel.layout): span <= 10 s one frame per 0.5 s, max 16, 1 row if <= 8 else 2 interleaved rows; "
              "span > 10 s one frame per 2 s, 2 interleaved rows if a frame would be < 150 px; width 1550-1800 px")


def set_frames(r):
    r["frame_rule"] = FRAME_RULE if r["mode"] == "panel_even" else PEAK_RULE


PREV = {}
for _m in ("panel_even", "panel_peak"):
    _f = HERE / "panels_1028" / _m / "sample" / "sample_manifest.jsonl"
    if _f.exists():
        for _r in map(json.loads, open(_f)):
            PREV[(_r["mode"], _r["variant"], _r["item_id"])] = _r


def do_panel(r):
    p = Path(r["panel"])
    p.parent.mkdir(parents=True, exist_ok=True)
    set_frames(r)
    if not p.exists():
        try:
            fn = RP.render if r["mode"] == "panel_even" else RP.render_peak
            r.update(fn(r["video"], r["window"][0], r["window"][1], str(p), r["pad"]))
        except Exception as e:                     # recorded, never silently dropped
            r["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    else:
        prev = PREV.get((r["mode"], r["variant"], r["item_id"]))
        if prev:                                   # rendered in the sample run: take its render details
            r.update({k: v for k, v in prev.items() if k not in r or k in ("span", "frame_times", "n_frames", "frame_rows",
                                                                                   "width_px", "frame_px", "frame_px_ok", "peaks", "n_peaks", "fallback")})
        else:                                      # rendered by the killed 10/28 run (no manifest written): recompute details
            try:
                r.update(RP.describe(r["video"], r["window"][0], r["window"][1], r["pad"],
                                     "peak" if r["mode"] == "panel_peak" else "even"))
                r["meta_recomputed"] = True
            except Exception as e:
                r["error"] = f"describe {type(e).__name__}: {str(e)[:300]}"
    return r


def do_focus(f):
    if not Path(f["path"]).exists():
        f["cut"] = cut(f["video"], f["focus"][0], f["focus"][1], f["path"])
    else:
        f["cut"] = [round(max(0.0, f["focus"][0]), 3), round(min(RP.probe_duration(f["video"]), f["focus"][1]), 3)]
    a, b = f["cut"]
    s0, s1 = f["sound_t_shifted"]
    f["sound_inside"] = "full" if a <= s0 and s1 <= b else ("onset_only" if a <= s0 <= b else ("offset_only" if a <= s1 <= b else "miss"))


def write(path, recs):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["list", "sample", "all"])
    ap.add_argument("--focus-mode", choices=["action", "sound"], default="action")
    ap.add_argument("--focus-only", action="store_true", help="sample/all: focus clips only, no panels")
    ap.add_argument("--workers", type=int, default=2, help="at most 2 (4-core SCC allocation)")
    a = ap.parse_args()
    global MODE
    MODE = a.focus_mode
    FD = FOC / f"{MODE}_centred"
    rows, focus = build()
    print(pd.Series([r["variant"] for r in rows]).value_counts().to_string())
    print("focus:", pd.Series([f["variant"] for f in focus]).value_counts().to_dict())
    if a.stage == "list":
        write(PAN / "manifest_planned.jsonl", rows); write(FD / "manifest_planned.jsonl", focus)
        return
    if a.stage == "sample":
        by = {}
        for r in rows:
            if r["mode"] == "panel_even":
                by.setdefault(r["variant"], []).append(r)
        early = by["avb_shift_early"][0]
        orig = next((r for r in by["avb_original"] if r["clip"] == early["clip"]), by["avb_original"][0])
        mc = by["mute_class"][0]
        trio = [next(r for r in by[v] if r["clip"] == mc["clip"] and r["cls"] == mc["cls"]) for v in ("mute_sham", "mute_original")]
        pick0 = [early, orig, by["avb_shift_late"][0], mc] + trio + [by["tcr_order_swap"][0], by["tcc_count_off"][0]]
        idx = {(r["variant"], r["item_id"], r["mode"]): r for r in rows}
        pick = {m: [idx[(r["variant"], r["item_id"], m)] for r in pick0] for m in PANEL_MODES}
        fb = {}
        for f in focus:
            fb.setdefault(f["variant"], []).append(f)
        fpick = fb["avb_shift_early"][:2] + fb["avb_shift_late"][:2] + [next((f for f in fb["avb_original"] if f["clip"] == early["clip"]), fb["avb_original"][0])]
        jobs = [] if a.focus_only else [(PAN / m, pick[m], "panel", do_panel) for m in PANEL_MODES]
        for d, recs, key, fn in jobs + [(FD, fpick, "path", do_focus)]:
            for r in recs:
                fn(r)
            s = d / "sample"
            s.mkdir(parents=True, exist_ok=True)
            for r in recs:
                link = s / f"{r['variant']}__{Path(r[key]).name}"
                if not link.exists():
                    link.symlink_to(r[key])
            write(s / "sample_manifest.jsonl", recs)
            print(f"-> {s}")
        return
    if not a.focus_only:
        from multiprocessing import Pool
        with Pool(min(a.workers, 2)) as pool:
            done = []
            for i, r in enumerate(pool.imap(do_panel, rows, chunksize=4)):
                done.append(r)
                if i % 50 == 0:
                    print(f"[panel] {i}/{len(rows)}", flush=True)
        rows = done
    for f in focus:
        do_focus(f)
    if not a.focus_only:
        if (PAN / "manifest.jsonl").exists():
            sys.exit(f"exists, not overwriting: {PAN / 'manifest.jsonl'}")
        write(PAN / "manifest.jsonl", rows)
    write(FD / "manifest.jsonl", focus)


if __name__ == "__main__":
    main()
