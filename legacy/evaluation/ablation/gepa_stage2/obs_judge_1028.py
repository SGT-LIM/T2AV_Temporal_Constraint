#!/usr/bin/env python3
"""Observation validation (pipeline v4 §4 step 4), 10/28. Two-stage KEEP/REVISE judge with ONE observation per call.

Every observation call gets: the item criteria for one axis, the SAME-DAY media-only anchor verdicts and reasons (all
non-gated anchor events of that axis; never the GT ids or labels), and ONE observation. It answers per event with
"KEEP:" / "REVISE:" reasons in the axis' normal schema. Media observations (audio-only, focus clip) are the only media in
the call (no original clip); text and panel observations come without any video. Nothing from GT enters a prompt; GT is
used only in `score`.

Sets / conditions (user spec 10/28):
  A  mute_class set, chosen classes, variants mute_class / sham / original, axis A:
       anchor (run_agentic_eval --axes a, media-only), audio_only, flam_text, panel_even, panel_peak
       + anchor only on the originals of the excluded classes
  B  hdepic AVB shift_early / shift_late / original (110 rows): anchor (full same-day run), focus, panel_even, panel_peak
       (Synchformer: no wrapper in the repo -> skipped)
  C  hdepic TCR order_swap + originals, hdmove TCC count_off + originals: anchor (full same-day run), panel_even, panel_peak
  D  V-only modality ablation: muted video, media-only V (run_agentic_eval --axes v), vs the same-day anchor V

  python gepa_stage2/obs_judge_1028.py rows --classes "open / close|footstep"   # rows.jsonl (needs anchors for B/C to exist only at run time)
  python gepa_stage2/obs_judge_1028.py prep                                     # audio wavs, muted videos, mute eval subset
  python gepa_stage2/obs_judge_1028.py run --cond audio_only --workers 6 [--dry-run 3]
  python gepa_stage2/obs_judge_1028.py score
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
FF_THREADS = ["-threads", "2"]
import argparse, hashlib, json, subprocess, sys, threading, time, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
sys.path.insert(0, str(ABL)); sys.path.insert(0, str(HERE))
DAY = "1028"
RA = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av")
EV = RA / "eval"
RES = EV / "results"
R220 = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent")
MC = RA / "hdepic/hdepic_mute_class_1028"
OBS = RA / "eval/obsval_1028"                       # new dir for this task's inputs (wavs, muted videos, subsets)
OUT = HERE / "runs/obsval_1028"                     # rows, call cache, scores
# same-day media-only anchors (launched by launch_obsval_1028.sh)
ANCHOR = {
    "hdepic": [RES / "hdepic_medium_multi_baseline_g36_obsval_1028", RES / "hdepic_regen_multi_baseline_g36_obsval_1028"],
    "hdmove": [RES / "hdepic_move_multi_baseline_g36_obsval_1028"],
    "ltx": [R220 / "baseline_min3_g36_obsval_1028/LTX_2p3.csv"], "mova": [R220 / "baseline_min3_g36_obsval_1028/MOVA.csv"],
    "hdmc": [RES / "hdepic_mute_class_A_baseline_g36_obsval_1028"],
    "hdma": [RES / "hdepic_mute_anchor_A_baseline_g36_obsval_1028"],
    "hdma29": [RES / "hdepic_mute_anchor_A_baseline_g36_obsval_1029"],      # anchor_1029 (set A3)
    "hdepic30": [RES / "hdepic_medium_BC_baseline_g36_obsval_1030"],         # 10/30 anchor, sets B30 / C30 TCR
    "hdmove30": [RES / "hdepic_move_TCC_baseline_g36_obsval_1030"],          # 10/30 anchor, set C30 TCC
    "hdho": [RES / "hdepic_holdout_p3p9_AVB_baseline_g36_1030" / f"shard{k}.csv" for k in range(12)],             # 10/30 HOLDOUT anchor, set HO30 (gated judge)
    # 10/30 generated block: row 1 media-only anchor (event_time_s flag), explicit shard files (rows 4 / 5 / framing)
    "g220ltx": [R220 / "gen_row1_anchor_g36_1030" / f"LTX_2p3_shard{k}.csv" for k in range(5)],
    "g220mova": [R220 / "gen_row1_anchor_g36_1030" / f"MOVA_shard{k}.csv" for k in range(5)],
    "g149": [R220 / "gen_row1_anchor_g36_1030" / f"gen149_shard{k}.csv" for k in range(7)],
    # 11/01 HD-EPIC main table: row 1 media-only anchor of 11/01 (rows 4 / 5 / framing, hd_stage2_1101.py)
    "hm_hdepic": [RES / "hdepic_main_row1_anchor_g36_1101" / f"hdepic_p12_shard{k}.csv" for k in range(3)],
    "hm_hdfoot": [RES / "hdepic_main_row1_anchor_g36_1101" / "hdfoot_p12_shard0.csv"],
    "hm_p3p9": [RES / "hdepic_main_row1_anchor_g36_1101" / f"p3p9_shard{k}.csv" for k in range(24)],
    "hm_ma": [RES / "hdepic_main_ma_row1_A_g36_1101" / f"shard{k}.csv" for k in range(4)],   # 11/01 mute_anchor A (P01/P02)
    "hm_p12new": [RES / "hdepic_main_row1_p12all_g36_1101" / f"shard{k}.csv" for k in range(12)],   # 11/01 option (ii) P01/P02 items
    "hm_ma39": [RES / "hdepic_main_ma39_row1_A_g36_1101" / f"shard{k}.csv" for k in range(3)],      # 11/01 P03-P09 mute_anchor A
    "hm_avbadd12": [RES / "hdepic_avbadd_row1_anchor_g36_1102" / f"p12_shard{k}.csv" for k in range(3)],     # 11/02 AVB additions
    "hm_avbadd39": [RES / "hdepic_avbadd_row1_anchor_g36_1102" / f"p3p9_shard{k}.csv" for k in range(8)],
}
MUTED = {   # D: muted-video V runs
    "hdepic": [RES / "hdepic_medium_V_muted_g36_obsval_1028", RES / "hdepic_regen_V_muted_g36_obsval_1028"],
    "ltx": [R220 / "V_muted_min3_g36_obsval_1028/LTX_2p3.csv"], "mova": [R220 / "V_muted_min3_g36_obsval_1028/MOVA.csv"],
}
MA = RA / "hdepic/hdepic_mute_anchor_1028"
PROMPTS = {"hdepic": EV / "hdepic_medium_prompts_v2.json", "hdmove": EV / "hdepic_move_prompts.json", "hdmc": MC / "prompts.json",
           "hdma": MA / "prompts.json", "hdma29": MA / "prompts.json",
           "hdepic30": EV / "hdepic_medium_prompts.json", "hdmove30": EV / "hdepic_move_prompts.json",
           "hdho": Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/prompts_hdepic_p3p9.json"),
           "g220ltx": Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/new_prompts/generated/relative_500_v5_fixed.json"),
           "g220mova": Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/new_prompts/generated/relative_500_v5_fixed.json"),
           "g149": Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/prompts_gen149.json"),
           "hm_hdepic": EV / "hdepic_medium_prompts_v2.json", "hm_hdfoot": EV / "hdepic_medium_prompts.json",
           "hm_p3p9": Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/prompts_hdepic_p3p9.json"),
           "hm_ma": Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/hdepic_mute_anchor_1028/prompts.json"),
           "hm_p12new": EV / "hdepic_medium_prompts_v2.json",
           "hm_ma39": Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/mute_anchor_1101/prompts.json"),
           "hm_avbadd12": EV / "hdepic_avbadd_1102" / "p12" / "prompts_avbadd.json",
           "hm_avbadd39": EV / "hdepic_avbadd_1102" / "p3p9" / "prompts_avbadd.json"}
QWEN = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/qwen_timestamps_1030")
SYNC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_1030")
MC_OPTION_A = {"close": "a door, drawer or cupboard closing", "cut / slice / chop": "a knife cutting"}
MC_SCHEMA = {"type": "object", "properties": {"choice": {"type": "string", "enum": ["a", "b", "c", "d", "e"]},
                                              "reason": {"type": "string"}}, "required": ["choice", "reason"]}
ANCHOR_SOUND = {"close": "open / close", "cut / slice / chop": "cut / chop"}     # mute_anchor class -> HD-EPIC-Sounds class
COND_BY_SET = {"A": ["audio_only", "flam_text", "panel_even", "panel_peak"], "B": ["focus", "panel_even", "panel_peak"],
               "C": ["panel_even", "panel_peak"]}
FLAM_THR = 0.98                                      # pipeline default --flam-threshold
FLAM_QUERY = {"open / close": "a door or drawer opening or closing", "footstep": "footsteps", "water": "running water from a tap",
              "stir / mix / whisk": "stirring or whisking in a bowl", "cut / chop": "chopping with a knife on a cutting board",
              "slide object": "an object sliding on a surface", "scrub / scrape / scour / wipe": "scrubbing or wiping a surface"}
SLUG = {"open / close": "open", "footstep": "footstep", "water": "water", "stir / mix / whisk": "stir", "cut / chop": "cut",
        "slide object": "slideobject", "scrub / scrape / scour / wipe": "scrub"}

OBS_RULES = """
TWO-STAGE PROTOCOL (read carefully):
- A first judge already evaluated this axis from the full video with its audio. Its judgment is shown below under "Stage 1 (media only)".
- You now receive ONE additional observation of the same clip, described under "Observation". You do NOT see the original video in this call.
- The observation is approximate and can be incomplete or misleading. Your job is to COMPARE stage 1 with the observation, not to re-judge from scratch.
- KEEP the stage-1 answer unless the observation gives specific evidence (a sound you hear or do not hear, a timestamped onset, a visible action at a given time, a detector result) that directly contradicts what stage 1 concluded.
- An observation that is ambiguous, does not cover the event, or merely agrees with stage 1 is NOT by itself a reason to change stage 1.
- Answer for every event listed under stage 1, with the same event ids. Start each reason with "KEEP:" or "REVISE:" followed by the comparison you made."""
OBS_RULES_MD5 = hashlib.md5(OBS_RULES.encode()).hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p)]


def wjl(p, recs):
    """atomic: readers starting while this runs see either the old or the new file, never a partial one"""
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + f".tmp{os.getpid()}")
    with open(tmp, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    os.replace(tmp, p)


# ------------------------------------------------------------------ rows
def stage_rows(a):
    classes = [c.strip() for c in a.classes.split("|") if c.strip()]
    bad = [c for c in classes if c not in SLUG]
    if bad:
        sys.exit(f"unknown classes {bad}; choose from {list(SLUG)}")
    pan = {(r["mode"], r["variant"], r["item_id"]): r for r in jl(HERE / "panels_1028/manifest.jsonl")}
    foc = {r["item_id"]: r for r in jl(HERE / "focus_1028/action_centred/manifest.jsonl")}
    rows = []
    # A
    vmap = {"mute_class": "mute_class", "sham": "mute_sham", "original": "mute_original"}
    for r in jl(MC / "manifest.jsonl"):
        inc = r["cls"] in classes
        if not inc and r["variant"] != "original":
            continue
        base = dict(set="A", source="hdmc", uid=r["uid"], item_id=r["item_id"], axis="A", variant=r["variant"], cls=r["cls"],
                    class_included=inc, gt=r["gt"], video=r["video"], clip=r["clip"])
        rows.append({**base, "cond": "anchor"})
        if not inc:
            continue
        rows.append({**base, "cond": "audio_only", "obs": {"wav": str(OBS / "audio" / f"{Path(r['video']).stem}.wav")}})
        rows.append({**base, "cond": "flam_text", "obs": {"flam_json": str(MC / "work/flam" / f"{Path(r['video']).stem}__{SLUG[r['cls']]}.json"),
                                                          "query": FLAM_QUERY[r["cls"]]}})
        for m in ("panel_even", "panel_peak"):
            p = pan[(m, vmap[r["variant"]], r["item_id"])]
            rows.append({**base, "cond": m, "obs": {"png": p["panel"], "span": p["span"], "peaks": p.get("peaks"), "fallback": p.get("fallback")}})
    # B / C from the v3 test manifest
    for m in jl(HERE / "manifests_v3/test.jsonl"):
        if m["source"] == "hdepic" and m["axis"] == "AVB":
            st, pv = "B", {"original": "avb_original", "audio_shift_early": "avb_shift_early", "audio_shift_late": "avb_shift_late"}[m["variant"]]
        elif (m["source"] == "hdepic" and m["axis"] == "TCR") or (m["source"] == "hdmove" and m["axis"] == "TCC"):
            st = "C"
            pv = {"TCR": {"order_swap": "tcr_order_swap", "original": "tcr_original"},
                  "TCC": {"count_off": "tcc_count_off", "original": "tcc_original"}}[m["axis"]][m["variant"]]
        else:
            continue
        base = dict(set=st, source=m["source"], uid=m["uid"], item_id=m["item_id"], axis=m["axis"], variant=m["variant"], gt=m["gt"], clip=m["split_key"])
        rows.append({**base, "cond": "anchor"})
        for c in COND_BY_SET[st]:
            if c == "focus":
                f = foc[m["item_id"]]
                rows.append({**base, "cond": c, "obs": {"mp4": f["path"], "cut": f["cut"]}})
            else:
                p = pan[(c, pv, m["item_id"])]
                rows.append({**base, "cond": c, "obs": {"png": p["panel"], "span": p["span"], "peaks": p.get("peaks"), "fallback": p.get("fallback")}})
    # D: V rows (scored from the muted run vs the anchor; no observation call)
    for m in jl(HERE / "manifests_v3/test.jsonl"):
        if m["axis"] == "V" and m["source"] in ("hdepic", "ltx", "mova"):
            base = dict(set="D", source=m["source"], uid=m["uid"], item_id=m["item_id"], axis="V", variant=m["variant"], gt=m["gt"],
                        clip=m.get("split_key"))
            rows += [{**base, "cond": "anchor"}, {**base, "cond": "muted_video"}]
    wjl(OUT / "rows.jsonl", rows)
    json.dump(dict(classes=classes, built=time.strftime("%Y-%m-%d %H:%M")), open(OUT / "rows_meta.json", "w"))
    t = pd.DataFrame(rows).groupby(["set", "cond"]).size()
    print(t.to_string())
    nobs = sum(1 for r in rows if r["cond"] not in ("anchor", "muted_video"))
    print(f"observation calls: {nobs}")


# ------------------------------------------------------------------ set A2: mute_anchor (10/28 evening)
def a2_rows():
    """mute_anchor / sham / original rows (axis A). Panel window = the anchor's paired sound segment +- 2 s, the SAME window for
    the three variants of one anchor (taken from the mute_anchor row)."""
    man = jl(MA / "manifest.jsonl")
    win = {(r["clip"], r["nid"]): [round(r["sound"][0] - 2.0, 3), round(r["sound"][1] + 2.0, 3)] for r in man if r["variant"] == "mute_anchor"}
    pdir = HERE / "panels_1028"
    rows = []
    for r in man:
        cls = ANCHOR_SOUND[r["aclass"]]
        stem = Path(r["video"]).stem
        base = dict(set="A2", source="hdma", uid=r["uid"], item_id=r["item_id"], axis="A", variant=r["variant"], cls=cls,
                    aclass=r["aclass"], gt=r["gt"], video=r["video"], clip=r["clip"], window=win[(r["clip"], r["nid"])])
        rows.append({**base, "cond": "anchor"})
        rows.append({**base, "cond": "audio_only", "obs": {"wav": str(OBS / "audio" / f"{stem}.wav")}})
        rows.append({**base, "cond": "flam_text", "obs": {"flam_json": str(MA / "work/flam" / f"{stem}__{SLUG[cls]}.json"), "query": FLAM_QUERY[cls]}})
        for m in ("panel_even", "panel_peak"):
            rows.append({**base, "cond": m, "obs": {"png": str(pdir / m / f"ma_{r['variant']}" / f"{r['item_id']}.png")}})
    return rows


def stage_rows_a2(a):
    rows = [r for r in jl(OUT / "rows.jsonl") if r["set"] != "A2"] + a2_rows()
    wjl(OUT / "rows.jsonl", rows)
    print(pd.DataFrame([r for r in rows if r["set"] == "A2"]).groupby(["variant", "cond"]).size().unstack().to_string())


def _panel(r):
    import render_panel as RP
    p = Path(r["obs"]["png"])
    p.parent.mkdir(parents=True, exist_ok=True)
    fn = RP.render if r["cond"] == "panel_even" else RP.render_peak
    info = fn(r["video"], r["window"][0], r["window"][1], str(p), 0.0) if not p.exists() else \
        RP.describe(r["video"], r["window"][0], r["window"][1], 0.0, "even" if r["cond"] == "panel_even" else "peak")
    return r["uid"], r["cond"], info


def stage_prep_a2(a):
    rows = [r for r in jl(OUT / "rows.jsonl") if r["set"] == "A2"]
    (OBS / "audio").mkdir(parents=True, exist_ok=True)
    for r in rows:                                    # 16 kHz mono wavs (audio-only observation)
        if r["cond"] == "audio_only" and not Path(r["obs"]["wav"]).exists():
            subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-i", r["video"], *FF_THREADS, "-vn", "-ac", "1", "-ar", "16000",
                            "-acodec", "pcm_s16le", r["obs"]["wav"]], check=True)
    from multiprocessing import Pool                  # panels, 2 workers (4-core job)
    with Pool(2) as pool:
        info = pool.map(_panel, [r for r in rows if r["cond"] in ("panel_even", "panel_peak")])
    meta = {(u, c): i for u, c, i in info}
    for r in rows:
        if r["cond"] in ("panel_even", "panel_peak"):
            i = meta[(r["uid"], r["cond"])]
            r["obs"].update(span=i["span"], peaks=i.get("peaks"), fallback=i.get("fallback"))
    allrows = [r for r in jl(OUT / "rows.jsonl") if r["set"] != "A2"] + rows
    wjl(OUT / "rows.jsonl", allrows)
    wjl(HERE / "panels_1028" / "manifest_mute_anchor.jsonl", [dict(uid=u, cond=c, **i) for u, c, i in info])
    # FLAM over the whole clip, class query, 10 s windows hop 5 s (same wrapper and settings as the mute_class residual check)
    sys.path.insert(0, str(ABL / "Tool_Use"))
    import flam_audio as FA
    d = MA / "work/flam"
    d.mkdir(parents=True, exist_ok=True)
    for r in rows:
        if r["cond"] != "flam_text" or Path(r["obs"]["flam_json"]).exists():
            continue
        ev = FA.extract_flam_evidence(r["video"], queries=[r["obs"]["query"]], ckpt_path="/projectnb/ivc-ml/youngsun/.hf_cache/openflam",
                                      device="cuda", max_duration_sec=10.0, hop_sec=5.0)
        q = ev["queries"][0]
        json.dump(dict(video=r["video"], cls=r["cls"], query=q["query"], model_duration=ev["model_duration"], num_frames=ev["num_frames"],
                       frame_scores=q["frame_scores"]), open(r["obs"]["flam_json"], "w"))
    n = pd.DataFrame([dict(cond=c, fb=(i.get("fallback") or "")) for (u, c), i in meta.items()])
    print("panels:", n.groupby("cond").size().to_dict(), "| panel_peak fallbacks:", int((n.fb == "panel_even").sum()))


def stage_prep_a2_window(a):
    """flam_text_window: FLAM with the anchor class query on the anchor's sound segment +- 1 s only (= panel window shrunk by 1 s
    each side), cut from each row's own clip. Records query, window and max score; adds rows cond=flam_text_window."""
    sys.path.insert(0, str(ABL / "Tool_Use"))
    import flam_audio as FA
    import render_panel as RP
    allrows = jl(OUT / "rows.jsonl")
    base = [r for r in allrows if r["set"] == "A2" and r["cond"] == "anchor"]
    d = MA / "work/flam_window"
    d.mkdir(parents=True, exist_ok=True)
    new = []
    for r in base:
        dur = RP.probe_duration(r["video"])
        w = [round(max(0.0, r["window"][0] + 1.0), 3), round(min(dur, r["window"][1] - 1.0), 3)]
        js = d / f"{r['item_id']}.json"
        if not js.exists():
            wav = d / f"{r['item_id']}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", *FF_THREADS, "-ss", f"{w[0]:.3f}", "-t", f"{w[1] - w[0]:.3f}", "-i", r["video"],
                            *FF_THREADS, "-vn", "-ac", "1", "-ar", "48000", "-acodec", "pcm_s16le", str(wav)], check=True)
            ev = FA.extract_flam_evidence(str(wav), queries=[FLAM_QUERY[r["cls"]]], ckpt_path="/projectnb/ivc-ml/youngsun/.hf_cache/openflam",
                                          device="cuda", max_duration_sec=10.0, hop_sec=0.0)
            q = ev["queries"][0]
            json.dump(dict(video=r["video"], query=q["query"], window=w, max_score=q["max_score"], audio_duration=ev["audio_duration"],
                           frame_scores=q["frame_scores"]), open(js, "w"))
        new.append({**{k: v for k, v in r.items() if k != "cond"}, "cond": "flam_text_window",
                    "obs": {"flam_json": str(js), "query": FLAM_QUERY[r["cls"]], "flam_window": w}})
    allrows = [r for r in allrows if not (r["set"] == "A2" and r["cond"] == "flam_text_window")] + new
    wjl(OUT / "rows.jsonl", allrows)
    print(f"flam_text_window rows: {len(new)}")


# ------------------------------------------------------------------ set A3 (10/29): same 228 A2 rows, scored against anchor_1029
def stage_rows_a3(a):
    allrows = [r for r in jl(OUT / "rows.jsonl") if r["set"] != "A3"]
    a2 = {(r["uid"], r["cond"]): r for r in allrows if r["set"] == "A2"}
    man = {m["uid"]: m for m in jl(MA / "manifest.jsonl")}
    d = OBS / "a3_windows"
    new = []
    for (uid, cond), r in a2.items():
        if cond != "anchor":
            continue
        m = man[uid]
        base = {**{k: v for k, v in r.items() if k not in ("cond", "obs")}, "set": "A3", "source": "hdma29",
                "anchor_event": m["anchor_event"], "action_text": f"{m['verb']} {m['noun']}"}
        w = r["window"]
        new.append({**base, "cond": "anchor"})
        new.append({**base, "cond": "audio_window", "obs": {"wav": str(d / f"{r['item_id']}.wav"), "cut": w}})
        new.append({**base, "cond": "clip_window", "obs": {"mp4": str(d / f"{r['item_id']}.mp4"), "cut": w}})
        new.append({**base, "cond": "clip_window_mc", "obs": {"mp4": str(d / f"{r['item_id']}.mp4"), "cut": w,
                                                            "option_a": MC_OPTION_A[r["aclass"]]}})
        new.append({**base, "cond": "panel_even_1029", "obs": dict(a2[(uid, "panel_even")]["obs"])})
    wjl(OUT / "rows.jsonl", allrows + new)
    print(pd.DataFrame(new).groupby(["variant", "cond"]).size().unstack().to_string())


def stage_prep_a3(a):
    import render_panel as RP
    rows = [r for r in jl(OUT / "rows.jsonl") if r["set"] == "A3" and r["cond"] == "anchor"]
    d = OBS / "a3_windows"
    d.mkdir(parents=True, exist_ok=True)
    for r in rows:
        dur = RP.probe_duration(r["video"])
        a0, b0 = max(0.0, r["window"][0]), min(dur, r["window"][1])
        wav, mp4 = d / f"{r['item_id']}.wav", d / f"{r['item_id']}.mp4"
        if not wav.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-ss", f"{a0:.3f}", "-t", f"{b0 - a0:.3f}", "-i", r["video"], *FF_THREADS,
                            "-vn", "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le", str(wav)], check=True)
        if not mp4.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-ss", f"{a0:.3f}", "-i", r["video"], *FF_THREADS, "-t", f"{b0 - a0:.3f}",
                            "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "128k", str(mp4)], check=True)
    # actual cut bounds (clamped to the clip) into the rows
    allrows = jl(OUT / "rows.jsonl")
    for r in allrows:
        if r["set"] == "A3" and r["cond"] in ("audio_window", "clip_window", "clip_window_mc"):
            dur = RP.probe_duration(r["video"])
            r["obs"]["cut"] = [round(max(0.0, r["window"][0]), 3), round(min(dur, r["window"][1]), 3)]
    wjl(OUT / "rows.jsonl", allrows)
    print(f"prep_a3: {len(list(d.glob('*.wav')))} wavs, {len(list(d.glob('*.mp4')))} mp4s")


# ------------------------------------------------------------------ sets B30 / C30 (10/30): tool texts, against the 10/30 anchors
def _fmt(x):
    return f"{x:.2f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def _spans(sp):
    return " and ".join(f"{_fmt(float(a))}-{_fmt(float(b))} s" for a, b in sp)


def _qwen(path, actions):
    import importlib.util
    spec = importlib.util.spec_from_file_location("parse_qwen", QWEN / "qwen_timestamps_share" / "parse_qwen.py")
    PQ = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PQ)
    r = json.load(open(path))
    sp, err = PQ.parse(r["reply"], r["actions"])
    return (None, err) if err else ({a: sp.get(a, []) for a in actions}, "")


def texts_b(item_id, meta_events, sync_rows, peaks=None):
    """synchformer_text / qwen_ts_text for one B item; binding events of the prompt (never GT-selected).
    Sound time = FLAM's per-frame score peak inside each detection (flam_peaks.json; the Synchformer records keep only spans)."""
    snd = [e for e in meta_events if e.get("modality") == "sounding_action"]
    multi = len(snd) > 1
    qsp, qerr = _qwen(QWEN / "qwen_timestamps_share/hdepic" / f"{item_id}.json", [e["action"] for e in snd])
    st, qt = [], []
    for e in snd:
        pre = f"'{e['action']}': " if multi else ""
        sr = sync_rows.get(e["action"])
        if sr is None or pd.isna(sr["offset"]):
            st.append(f"{pre}Synchformer, window around the action: no reading (no sound detected for this event)")
        else:
            st.append(f"{pre}Synchformer, window around the action: most likely offset {float(sr['offset']):+.1f} s (positive = audio later "
                      f"than video), probability {float(sr['prob']):.2f}; probability of zero offset {float(sr['p_offset0']):.2f}")
        q = None if qsp is None else qsp.get(e["action"], [])
        act = (f"Frame-only timing model: the action '{e['action']}' occurs at {_spans(q)}." if q else
               f"Frame-only timing model: the action '{e['action']}' was not found.")
        pk = sorted(d["peak_time"] for d in (peaks or {}).get(e["action"], []) if d.get("peak_time") is not None)
        if pk:
            line = act + f" Detected sound for this event (FLAM, full clip): score peak at {', '.join(_fmt(x) + ' s' for x in pk)}."
        else:
            line = act + " Detected sound for this event (FLAM, full clip): none detected."
        if q and pk:
            a0 = float(q[0][0])
            near = min(pk, key=lambda x: abs(x - a0))
            line += f"\nsound peak minus action start = {near - a0:+.2f} s"
        qt.append(line)
    return "\n".join(st), "\n".join(qt), qerr


def text_c(path, events, tcc=False):
    acts = [e["action"] for e in events if e.get("modality") != "speech"]
    qsp, err = _qwen(path, sorted(set(acts)))
    if qsp is None:
        return None, err
    parts = []
    for a in acts:                                     # prompt order
        sp = qsp.get(a, [])
        t = f"'{a}' at {_spans(sp)}" if sp else f"'{a}' not found"
        if tcc:
            t += f" (occurrences found: {len(sp)})"
        parts.append(t)
    return "Frame-only timing model: " + "; ".join(parts), ""


def stage_rows_bc30(a):
    """--part BTCR (sets B30 + C30 TCR) or TCC (set C30 TCC, after the Qwen move pass)."""
    allrows = jl(OUT / "rows.jsonl")
    old = [r for r in allrows if r["set"] in ("B", "C") and r["cond"] == "anchor"]
    if a.part == "BTCR":
        keep = [r for r in allrows if not (r["set"] in ("B30",) or (r["set"] == "C30" and r["axis"] == "TCR"))]
        pv1 = {x["item_id"]: x for x in json.load(open(PROMPTS["hdepic30"]))}
        sync = pd.read_csv(SYNC / "per_event.csv")
        peaks_all = json.load(open(SYNC / "flam_peaks.json"))                # required: per-frame FLAM peak times
        new = []
        for r in old:
            if r["set"] == "B":
                it = pv1[r["item_id"]]
                sr = {x["label"]: x for x in sync[sync.item_id == r["item_id"]].to_dict("records")}
                st, qt, qerr = texts_b(r["item_id"], it["events"], sr, peaks_all.get(r["item_id"], {}))
                base = {**{k: v for k, v in r.items() if k not in ("cond", "obs")}, "set": "B30", "source": "hdepic30"}
                new += [{**base, "cond": "anchor"},
                        {**base, "cond": "synchformer_text", "obs": {"text": "Observation (tool output):\n" + st}},
                        {**base, "cond": "qwen_ts_text", "obs": {"text": "Observation (tool output):\n" + qt, "qwen_error": qerr}},
                        {**base, "cond": "qwen_plus_synchformer_text", "obs": {"text": "Observation (tool output):\n" + st + "\n" + qt, "qwen_error": qerr}}]
            elif r["set"] == "C" and r["axis"] == "TCR":
                it = pv1[r["item_id"]]
                t, err = text_c(QWEN / "qwen_timestamps_share/hdepic" / f"{r['item_id']}.json", it["events"])
                base = {**{k: v for k, v in r.items() if k not in ("cond", "obs")}, "set": "C30", "source": "hdepic30"}
                new += [{**base, "cond": "anchor"},
                        {**base, "cond": "qwen_ts_text", "obs": {"text": "Observation (tool output):\n" + (t or f"Frame-only timing model: no usable output ({err})"), "qwen_error": err}}]
    else:
        keep = [r for r in allrows if r["set"] != "C30T"]          # own set name: no overlap with the running C30 (TCR) observation run
        pm = {x["item_id"]: x for x in json.load(open(PROMPTS["hdmove30"]))}
        new = []
        for r in old:
            if r["set"] == "C" and r["axis"] == "TCC":
                t, err = text_c(QWEN / "move_1030/hdepicmove" / f"{r['item_id']}.json", pm[r["item_id"]]["events"], tcc=True)
                base = {**{k: v for k, v in r.items() if k not in ("cond", "obs")}, "set": "C30T", "source": "hdmove30"}
                new += [{**base, "cond": "anchor"},
                        {**base, "cond": "qwen_ts_text", "obs": {"text": "Observation (tool output):\n" + (t or f"Frame-only timing model: no usable output ({err})"), "qwen_error": err}}]
    wjl(OUT / "rows.jsonl", keep + new)
    print(pd.DataFrame(new).groupby(["set", "axis", "variant", "cond"]).size().unstack().to_string())


# ------------------------------------------------------------------ prep (no API)
def stage_prep(a):
    rows = jl(OUT / "rows.jsonl")
    if a.set not in (None, "A"):
        rows_a = []
    else:
        rows_a = rows
    # audio-only wavs (16 kHz mono, same as the audio_only media mode)
    (OBS / "audio").mkdir(parents=True, exist_ok=True)
    for r in rows_a:
        if r["cond"] == "audio_only" and not Path(r["obs"]["wav"]).exists():
            subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-i", r["video"], *FF_THREADS, "-vn", "-ac", "1", "-ar", "16000",
                            "-acodec", "pcm_s16le", r["obs"]["wav"]], check=True)
    # mute_class subset dir for the A anchor: chosen classes (3 variants) + excluded classes (originals only)
    sub = OBS / "mute_eval_subset"
    sub.mkdir(parents=True, exist_ok=True)
    for r in rows_a:
        if r["set"] == "A" and r["cond"] == "anchor":
            d = sub / r["item_id"]
            d.mkdir(parents=True, exist_ok=True)
            link = d / f"{r['item_id']}_v1_raw.mp4"
            if not link.exists():
                link.symlink_to(MC / "eval" / r["item_id"] / f"{r['item_id']}_v1_raw.mp4")
    # D: muted copies (video stream copied, audio removed) of every V-row video, in the outputs-dir layout
    srcdirs = {"hdepic": [EV / "hdepic_v3test_1028/medium", EV / "hdepic_v3test_1028/regen"],
               "ltx": [Path("/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3_test1027/LTX_2p3")],
               "mova": [Path("/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3_test1027/MOVA")]}
    n = 0
    for src, dirs in (srcdirs.items() if a.set in (None, "D") else []):
        want = {r["item_id"] for r in rows if r["set"] == "D" and r["source"] == src}
        for d in dirs:
            for f in sorted(d.rglob("*.mp4")):
                rel = f.relative_to(d)
                if src == "hdepic" and rel.parts[0] not in want:
                    continue
                out = OBS / "muted" / (d.name if src == "hdepic" else d.name) / rel
                if out.exists():
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["ffmpeg", "-v", "error", "-n", *FF_THREADS, "-i", str(f.resolve()), *FF_THREADS, "-map", "0:v:0", "-c:v", "copy",
                                "-an", str(out)], check=True)
                n += 1
    print(f"prep done: muted videos written {n}; subset items {len(list(sub.iterdir()))}")


# ------------------------------------------------------------------ run
_LOCK = threading.Lock()
_META, _ANCH = {}, {}


def meta_for(source, item_id):
    import new_eval as NE
    with _LOCK:
        if source not in _META:
            items = json.load(open(PROMPTS[source]))
            _META[source] = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    return _META[source][item_id]


def anchor_df(source):
    import rep_scoring as RS
    with _LOCK:
        if source not in _ANCH:
            _ANCH[source] = RS.load([str(p) for p in ANCHOR[source]])
    return _ANCH[source]


def anchor_entries(source, item_id, axis):
    """same-day anchor per-event entries (all non-gated events of this axis; GT ids are NOT used)."""
    import run_two_stage as TS
    from adapter import AXIS_FULL
    df = anchor_df(source)
    with _LOCK:
        TS.STAGE1 = df
        ent, _ = TS.stage1_lookup(item_id, AXIS_FULL[axis], None)
    return ent


def criteria_text(meta, axis):
    from adapter import CRITERIA
    if axis in ("TCR", "TCC"):
        return CRITERIA[axis](meta["events"], meta.get("temporal_constraint") or meta.get("constraint"))
    return CRITERIA[axis](meta["events"])


def obs_block(r):
    c, o = r["cond"], r["obs"]
    if "text" in o:                                    # B30 / C30 tool texts, built at rows time
        return o["text"], None
    c = "panel_even" if c == "panel_even_1029" else c
    if c == "audio_only":
        return ("Observation (audio only): the attached audio is the complete soundtrack of the same clip with the picture removed.", "wav")
    if c == "flam_text":
        d = json.load(open(o["flam_json"]))
        mx = float(np.max(d["frame_scores"]))
        return (f"Observation (sound-event detector text): FLAM, an open-vocabulary audio-text detector, was run over the whole clip audio "
                f"(10 s windows, 5 s hop).\nqueried: '{o['query']}' -> {'detected' if mx >= FLAM_THR else 'not detected'} "
                f"(max frame score {mx:.3f}; detection threshold {FLAM_THR:.2f}; scores are uncalibrated)", None)
    if c == "audio_window":
        a, b = o["cut"]
        return (f"Observation (audio only): the attached audio is the soundtrack of the same clip from {a:.2f} s to {b:.2f} s "
                f"(clip time; audio time 0 = clip time {a:.2f} s), with the picture removed.", "wav")
    if c == "clip_window":
        a, b = o["cut"]
        return (f"Observation (video excerpt): the attached video is an excerpt of the same clip with its audio, from {a:.2f} s to "
                f"{b:.2f} s of the original clip (excerpt time 0 = clip time {a:.2f} s).", "mp4")
    if c == "clip_window_mc":
        a, b = o["cut"]
        return (f"Observation (video excerpt): the attached video is an excerpt of the same clip with its audio, from {a:.2f} s to "
                f"{b:.2f} s of the original clip (excerpt time 0 = clip time {a:.2f} s).", "mp4")
    if c == "flam_text_window":
        d = json.load(open(o["flam_json"]))
        mx = float(d["max_score"])
        a, b = o["flam_window"]
        return (f"Observation (sound-event detector text): FLAM, an open-vocabulary audio-text detector, was run ONLY on the clip "
                f"audio from {a:.2f} s to {b:.2f} s (clip time).\nqueried: '{o['query']}' -> {'detected' if mx >= FLAM_THR else 'not detected'} "
                f"(max frame score {mx:.3f}; detection threshold {FLAM_THR:.2f}; scores are uncalibrated)", None)
    if c in ("panel_even", "panel_peak"):
        a, b = o["span"]
        s = (f"Observation (image): the attached image shows the clip's mono audio waveform from {a:.2f} s to {b:.2f} s (clip time; "
             "seconds on the axis) and video frames from the same span; each frame is labelled with its clip time in seconds.")
        if c == "panel_peak" and not o.get("fallback"):
            s += (" Thin vertical lines on the waveform mark the strongest audio onsets in this span; for each marked onset two frames "
                  "are shown side by side: 0.5 s before the onset and at the onset.")
        else:
            s += " The frames are evenly spaced across the span."
        return s, "png"
    if c == "focus":
        a, b = o["cut"]
        return (f"Observation (video excerpt): the attached video is an excerpt of the same clip with its audio, from {a:.2f} s to "
                f"{b:.2f} s of the original clip (excerpt time 0 = clip time {a:.2f} s).", "mp4")
    raise ValueError(c)


def build_call(r):
    import new_eval as NE
    import run_two_stage as TS
    from adapter import AXIS_FULL
    meta = meta_for(r["source"], r["item_id"])
    axis = AXIS_FULL[r["axis"]]
    ent = anchor_entries(r["source"], r["item_id"], r["axis"])
    if not ent:
        return None
    ob, media = obs_block(r)
    if r["cond"] == "clip_window_mc":
        q = (f"Question about the action '{r['action_text']}' ({r['anchor_event']}): In this segment, which sound do you hear at the moment "
             f"of the action?\n(a) {r['obs']['option_a']}\n(b) footsteps\n(c) running water\n(d) speech\n(e) none of these\n"
             "Answer with one letter in 'choice' and give a short reason. Choosing (a) means KEEP the stage-1 judgment of this event; "
             "any other choice means REVISE it.")
        text = meta.get("generated_prompt") or meta.get("prompt") or ""
        user = "\n\n".join([f"Prompt of the clip being evaluated:\n{text}", criteria_text(meta, r["axis"]),
                             TS.fmt_block(axis, ent), ob, q])
        system = NE.build_system_prompt("none", "none", "none", single_axis=True)
        return dict(system=system, user=user, media=media, schema=MC_SCHEMA, anchor=ent)
    text = meta.get("generated_prompt") or meta.get("prompt") or meta.get("text") or ""
    user = "\n\n".join([f"Prompt of the clip being evaluated:\n{text}", criteria_text(meta, r["axis"]), OBS_RULES.strip(),
                         TS.fmt_block(axis, ent), ob])
    system = NE.build_system_prompt("none", "none", "none", single_axis=True)
    return dict(system=system, user=user, media=media, schema=TS.SCHEMA[axis], anchor=ent)


def call(client, model, c, r):
    from google.genai import types
    from google.genai import errors as ge
    import new_eval as NE
    parts = []
    if c["media"] == "wav":
        parts.append(types.Part.from_bytes(data=Path(r["obs"]["wav"]).read_bytes(), mime_type="audio/wav"))
    elif c["media"] == "png":
        parts.append(types.Part.from_bytes(data=Path(r["obs"]["png"]).read_bytes(), mime_type="image/png"))
    elif c["media"] == "mp4":
        up = NE.upload_and_wait(client, r["obs"]["mp4"])
        parts.append(types.Part(file_data=types.FileData(file_uri=up.uri, mime_type=up.mime_type), video_metadata=types.VideoMetadata(fps=24)))
    parts.append(c["user"])
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=c["schema"], system_instruction=c["system"],
                                      temperature=0.0, seed=42, thinking_config=types.ThinkingConfig(thinking_level="high"))
    for i, d in enumerate([30, 60, 120, None]):
        try:
            resp = client.models.generate_content(model=model, contents=parts, config=cfg)
            break
        except (ge.ServerError, ge.ClientError) as e:
            if d is None or not (isinstance(e, ge.ServerError) or getattr(e, "code", None) in (429, 500, 503)):
                raise
            print(f"    [RETRY {i + 1}] {type(e).__name__} {getattr(e, 'code', None)}; sleep {d}s", flush=True)
            time.sleep(d)
    raw = resp.text or ""
    return NE.parse_model_json(raw), raw


def stage_run(a):
    rows = [r for r in jl(OUT / "rows.jsonl") if r["cond"] == a.cond and (not a.set or r["set"] == a.set)]
    cache = OUT / "calls" / a.cond
    cache.mkdir(parents=True, exist_ok=True)
    todo = [r for r in rows if not (cache / f"{r['set']}__{r['uid'].replace('/', '_')}.json").exists()]
    print(f"[{a.cond}] rows {len(rows)}, to do {len(todo)}; model {a.model}, thinking high, rules md5 {OBS_RULES_MD5}", flush=True)
    if a.dry_run:
        for r in todo[: a.dry_run]:
            c = build_call(r)
            print("=" * 100, "\n", r["uid"], r["cond"], "media:", c and c["media"])
            print(c["user"] if c else "(no anchor entries: row skipped)")
        return
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key)

    def one(r):
        f = cache / f"{r['set']}__{r['uid'].replace('/', '_')}.json"
        try:
            c = build_call(r)
            if c is None:
                rec = dict(status="no_anchor")
            else:
                parsed, raw = call(client, a.model, c, r)
                rec = dict(status="ok", parsed=parsed, raw=raw, anchor=c["anchor"], media=c["media"],
                           user_md5=hashlib.md5(c["user"].encode()).hexdigest())
        except Exception as e:
            rec = dict(status="error", error=f"{type(e).__name__}: {e}", tb=traceback.format_exc()[-2000:])
        rec.update(uid=r["uid"], set=r["set"], cond=r["cond"], model=a.model, thinking="high", rules_md5=OBS_RULES_MD5,
                   time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        if rec["status"] != "error":                 # errors are not cached, so a rerun retries them
            json.dump(rec, open(f, "w"))
        return rec["status"]

    from concurrent.futures import ThreadPoolExecutor
    n = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, todo)):
            n[s] = n.get(s, 0) + 1
            if i % 25 == 0:
                print(f"[{a.cond}] {i + 1}/{len(todo)} {n}", flush=True)
    print(f"[DONE] {a.cond}: {n}", flush=True)


# ------------------------------------------------------------------ score
def obs_label(rec, axis, gt, anchor_event=None):
    """row label from an observation call: same rule as the anchor (GT ids, KEEP/REVISE output labels, gated text dropped).
    clip_window_mc: choice (a) = KEEP (anchor labels), any other choice = REVISE = the anchor event's label flipped."""
    import rep_scoring as RS
    p = rec.get("parsed") or {}
    if rec.get("cond") == "clip_window_mc":
        flip = {"yes": "no", "no": "yes"}
        labs = {e["event_id"]: str(e.get("label", "")).lower() for e in rec.get("anchor", []) if "event_id" in e}
        if str(p.get("choice", "")).lower() != "a" and anchor_event in labs:
            labs[anchor_event] = flip.get(labs[anchor_event], labs[anchor_event])
        want = [e for e in gt if e != "__item__"]
        ls = [labs[e] for e in want if labs.get(e) in ("yes", "no")]
        return "no" if "no" in ls else ("yes" if ls else "")
    if axis == "TCR":
        lab = str(p.get("label", "")).strip().lower()
        return lab if lab in ("yes", "no") and not RS.SKIP_RE.search(str(p.get("reason", ""))) else ""
    want = [e for e in gt if e != "__item__"] or None
    labs = []
    for e in p.get("per_event", []):
        if want is not None and e.get("event_id") not in want:
            continue
        if axis == "TCC":
            oc = e.get("observed_count")
            rc = next((x.get("required_count") for x in rec.get("anchor", []) if x.get("event_id") == e.get("event_id")), None)
            if oc is None or rc is None:
                continue
            try:
                labs.append("yes" if int(oc) == int(rc) else "no")
            except (TypeError, ValueError):
                continue
        else:
            lab = str(e.get("label", "")).strip().lower()
            if lab in ("yes", "no"):
                labs.append(lab)
    return "no" if "no" in labs else ("yes" if labs else "")


def stage_score(a):
    import rep_scoring as RS
    rows = jl(OUT / "rows.jsonl")
    lab = {}
    for src in ANCHOR:
        try:
            df = RS.load([str(p) for p in ANCHOR[src]])
        except SystemExit:
            print(f"[warn] anchor missing for {src}"); continue
        for r in rows:
            if r["source"] == src and r["cond"] == "anchor":
                lab[(r["set"], r["uid"], "anchor")] = RS.row_label(df, r["item_id"], r["axis"], r["gt"])
    for src in MUTED:
        try:
            df = RS.load([str(p) for p in MUTED[src]])
        except SystemExit:
            print(f"[warn] muted run missing for {src}"); continue
        for r in rows:
            if r["source"] == src and r["cond"] == "muted_video":
                lab[(r["set"], r["uid"], "muted_video")] = RS.row_label(df, r["item_id"], r["axis"], r["gt"])
    for r in rows:
        if r["cond"] in ("anchor", "muted_video"):
            continue
        f = OUT / "calls" / r["cond"] / f"{r['set']}__{r['uid'].replace('/', '_')}.json"
        if f.exists():
            rec = json.load(open(f))
            lab[(r["set"], r["uid"], r["cond"])] = obs_label(rec, r["axis"], r["gt"], r.get("anchor_event")) if rec["status"] == "ok" else ""
    d = pd.DataFrame([dict(set=r["set"], source=r["source"], uid=r["uid"], axis=r["axis"], variant=r["variant"], cls=r.get("cls"),
                           cond=r["cond"], y="no" if "no" in r["gt"].values() else "yes", pred=lab.get((r["set"], r["uid"], r["cond"]), ""))
                      for r in rows])
    anc = d[d.cond == "anchor"].set_index(["set", "uid"]).pred
    d["anchor"] = [anc.get((s, u), "") for s, u in zip(d["set"], d.uid)]
    d.to_csv(OUT / "scores_rows.csv", index=False)
    out = []
    keys = ["set", "source", "axis", "variant", "cond"]
    for k, g in d.groupby(keys):
        g = g[g.pred.isin(["yes", "no"]) & g.anchor.isin(["yes", "no"])]
        if not len(g):
            continue
        m = RS.metrics(g.y, g.pred)
        ra, rb = g.anchor == g.y, g.pred == g.y
        out.append(dict(zip(keys, k), n=m["n"], n_fail=m["n_fail"], acc=m["acc"], prec=m["prec"], rec=m["rec"],
                        FA=((g.pred == "no") & (g.y == "yes")).sum() / max(1, (g.y == "yes").sum()),
                        fixed=int((~ra & rb).sum()), broken=int((ra & ~rb).sum()), both_wrong=int((~ra & ~rb).sum()),
                        revised=int((g.pred != g.anchor).sum())))
    t = pd.DataFrame(out)
    t.to_csv(OUT / "scores_table.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["rows", "prep", "run", "score", "rows_a2", "prep_a2", "prep_a2_window", "rows_a3", "prep_a3", "rows_bc30"])
    ap.add_argument("--classes", default="")
    ap.add_argument("--cond", default=None)
    ap.add_argument("--set", default=None)
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", type=int, default=0)
    ap.add_argument("--part", default="BTCR", choices=["BTCR", "TCC"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
