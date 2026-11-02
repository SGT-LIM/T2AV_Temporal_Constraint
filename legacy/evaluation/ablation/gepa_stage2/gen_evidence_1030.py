#!/usr/bin/env python3
"""Tool evidence for the generated sets (220 = min3 LTX_2p3 + MOVA, 149 = gen_holdout_149_1030), 10/30. GPU, env t2av_eval. No Gemini calls.

  python gepa_stage2/gen_evidence_1030.py threshold        # FLAM "no detection" threshold from P01/P02 originals (recorded first)
  python gepa_stage2/gen_evidence_1030.py audio --set 220   # Whisper (words) + FLAM (event queries) per video
  python gepa_stage2/gen_evidence_1030.py audio --set 149
  python gepa_stage2/gen_evidence_1030.py cache --set 149   # run_agentic_eval audio cache (rows 2 / 2b / 3)

Whisper: Tool_Use/whisper_audio (faster-whisper large-v3-turbo, word timestamps), speech segment = no_speech_prob < 0.5.
FLAM: Tool_Use/flam_audio, queries = the pipeline's own per-event queries (_queries_for_label of each sounding event), whole clip
(10 s windows, hop 5 s), threshold 0.98; per query: max frame score and detections with FLAM's per-frame peak time / score.
Threshold: over the sounding events of the P01/P02 v3 ORIGINAL clips (sound present by construction), each event's whole-clip
max FLAM score for its first query; T_flam = 5th percentile. Written to T2AV_data/tools/gen_evidence_1030/flam_threshold.json with
a timestamp before any generated-set result exists.
Out: T2AV_data/tools/gen_evidence_1030/<set>/<item_id>.json
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
sys.path.insert(0, str(ABL)); sys.path.insert(0, str(ABL / "Tool_Use")); sys.path.insert(0, str(HERE))
OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/gen_evidence_1030")
FLAM_KW = dict(model_name="v1-base", device="cuda", ckpt_path="/projectnb/ivc-ml/youngsun/.hf_cache/openflam", method="unbiased",
               max_duration_sec=10.0, threshold=0.98, min_duration_sec=0.05, merge_gap_sec=0.10, median_filter_size=3, top_k=5, hop_sec=5.0)
REL500 = Path((_LEGACY_ROOT + "/new_prompts/generated/relative_500_v5_fixed.json"))
MIN3 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3")
G149 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030")


HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")


def videos(which):
    """[(item_id, model, video_path, prompt item)]"""
    if which == "avbadd":   # 11/02 AVB additions: run_agentic_eval audio cache (hop 5) for row 2
        A = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_avbadd_1102")
        out = []
        for g in ("p12", "p3p9"):
            P = {x["item_id"]: x for x in json.load(open(A / g / "prompts_avbadd.json"))}
            out += [(i, g, str(A / g / "eval" / i / f"{i}_v1_raw.mp4"), P[i]) for i in sorted(P)]
        return out
    if which == "p12A":     # 11/01 option (ii): A-row items (originals + _A) of the P01/P02 windows not in the v3 test
        E = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
        V = E / "hdepic_main_1101" / "p12all_new"
        P = {x["item_id"]: x for x in json.load(open(E / "hdepic_medium_prompts_v2.json"))}
        ids = sorted(i for i in os.listdir(V) if i.endswith("_pass") or i.endswith("_A"))
        return [(i, "p12all", str(V / i / f"{i}_v1_raw.mp4"), P[i]) for i in ids]
    if which in ("ma", "ma39"):  # 11/01: mute_anchor sets (P01/P02 10/28: 228 rows; P03-P09 11/01: 118 rows), rows 4 / 5 A records
        M = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/hdepic_mute_anchor_1028") if which == "ma" else \
            Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028/mute_anchor_1101")
        P = {x["item_id"]: x for x in json.load(open(M / "prompts.json"))}
        man = [json.loads(l) for l in open(M / "manifest.jsonl")]
        return [(m["item_id"], which, m["eval_video"], P[m["item_id"]]) for m in sorted(man, key=lambda m: m["item_id"])]
    if which in ("hdmove", "hdA"):
        # 11/01 HD-EPIC main table. hdmove: the 142 P01/P02 movement-set test items (hop-5 audio cache, row 2).
        # hdA: the HD-EPIC A-row items (P01/P02 v3-test hdepic + hdfoot A rows; P03-P09 fail_absent_sound + originals), for the
        # row 4 / 5 Whisper + FLAM records. "model" = the prompt set, because hdfoot reuses hdepic item ids with other prompts.
        E = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
        V = E / "hdepic_main_1101"
        PJ = {"hdepic_p12": E / "hdepic_medium_prompts_v2.json", "hdfoot_p12": E / "hdepic_medium_prompts.json",
              "hdmove_p12": E / "hdepic_move_prompts.json", "p3p9": HO / "prompts_hdepic_p3p9.json"}
        man = [json.loads(l) for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "manifests_v3/test.jsonl")]
        want = {}
        if which == "hdmove":
            want["hdmove_p12"] = {m["item_id"] for m in man if m["source"] == "hdmove"}
        else:
            for src in ("hdepic", "hdfoot"):
                want[f"{src}_p12"] = {m["item_id"] for m in man if m["source"] == src and m["axis"] == "A"}
            it = json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))
            want["p3p9"] = {x["item_id"] for x in it if x["variant"] in ("fail_absent_sound", "original")}
        out = []
        for st, ids in want.items():
            P = {x["item_id"]: x for x in json.load(open(PJ[st]))}
            out += [(i, st, str(V / st / i / f"{i}_v1_raw.mp4"), P[i]) for i in sorted(ids)]
        return out
    if which == "p3p9":     # 10/31 HD-EPIC main table: every P03-P09 item except fail_mute (count_off included)
        P = {x["item_id"]: x for x in json.load(open(HO / "prompts_hdepic_p3p9.json"))}
        it = json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))
        return [(x["item_id"], "hdepic", str(HO / "eval" / x["item_id"] / f"{x['item_id']}_v1_raw.mp4"), P[x["item_id"]])
                for x in sorted(it, key=lambda x: x["item_id"]) if x["variant"] != "fail_mute"]
    if which == "220":
        P = {x["item_id"]: x for x in json.load(open(REL500))}
        out = []
        for m in ("LTX_2p3", "MOVA"):
            for d in sorted((MIN3 / m).iterdir()):
                if d.is_dir() and d.name in P:
                    v = sorted(d.glob("*.mp4"))
                    if v:
                        out.append((d.name, m, str(v[0].resolve()), P[d.name]))
        return out
    P = {x["item_id"]: x for x in json.load(open(G149 / "prompts_gen149.json"))}
    return [(i, "LTX_2p3", str((G149 / "videos" / i / f"{i}_v1_raw.mp4").resolve()), P[i]) for i in sorted(P)]


def flam_queries(item):
    import new_eval as NE
    import flam_audio as FA
    meta = NE.build_item_meta_map([item], modality_filter=None, item_overrides=None, relative_only=False)[item["item_id"]]
    ev = []
    for s in NE.build_scoring_events(meta):
        if s["kind"] == "sounding_action":
            ev.append((s["event_id"], s["label"], FA._queries_for_label("sounding_action", s["label"])))
    return ev, [s for s in NE.build_scoring_events(meta) if s["kind"] == "speech"]


def stage_audio(a):
    import whisper_audio as WA
    import flam_audio as FA
    od = OUT / a.set
    od.mkdir(parents=True, exist_ok=True)
    V = videos(a.set)[a.shard::a.nshards]
    for k, (iid, model, vid, item) in enumerate(V):
        f = od / f"{model}__{iid}.json"
        if f.exists():
            continue
        snd, speech = flam_queries(item)
        rec = dict(item_id=iid, model=model, video=vid)
        w = WA.extract_whisper_evidence(vid, model_size="large-v3-turbo", device="cuda", word_timestamps=True) if speech or True else {}
        rec["whisper"] = dict(segments=[dict(start=s["start"], end=s["end"], text=s["text"], no_speech_prob=s["no_speech_prob"],
                                             words=s.get("words", [])) for s in w.get("segments", [])], has_speech=w.get("has_speech"))
        queries = sorted({q for _, _, qs in snd for q in qs})
        fl = {}
        if queries:
            ev = FA.extract_flam_evidence(vid, queries=queries, **FLAM_KW)
            for q in ev["queries"]:
                fl[q["query"]] = dict(max_score=q["max_score"], detections=[dict(start=d["start"], end=d["end"], peak_time=d["peak_time"],
                                                                                 peak_score=d.get("peak_score")) for d in q["detections"]])
            rec["flam_model_duration"] = ev["model_duration"]
        rec["flam"] = fl
        rec["events"] = [dict(event_id=e, label=l, queries=qs) for e, l, qs in snd]
        json.dump(rec, open(f, "w"), indent=1)
        if k % 20 == 0:
            print(f"[audio] {a.set} {k + 1}/{len(V)} {model} {iid}", flush=True)


def stage_cache(a):
    """Warm the run_agentic_eval audio-evidence cache (whisper_flam, run_agentic_eval defaults = tools_min3_g36_1027 settings)
    so rows 2 / 2b / 3 can run with T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 on a login node. Same cache key as the runs."""
    import new_eval as NE
    import run_agentic_eval as R
    hop = ["--flam-hop-sec", "5"] if a.set in ("p3p9", "hdmove", "hdA", "p12A", "ma", "ma39", "avbadd") else []          # HD-EPIC 25 s clips: hop 5 as hdepic_medium_multi_tools_wf_hop5_g36
    args = R.build_arg_parser().parse_args(["--prompt-json", "x", "--outputs-dir", "x", "--output-csv", "x",
                                            "--audio-evidence-mode", "whisper_flam", "--flam-ckpt-path", FLAM_KW["ckpt_path"]] + hop)
    keep = [k for k in vars(args) if k.startswith(("whisper_", "clap_", "flam_"))] + ["audio_evidence_mode"]
    kw = {k: getattr(args, k) for k in keep}
    V = videos(a.set)[a.shard::a.nshards]
    n_hit = n_new = n_err = n_skip = 0
    for k, (iid, model, vid, item) in enumerate(V):
        meta = NE.build_item_meta_map([item], modality_filter=None, item_overrides=None, relative_only=False)[iid]
        f = NE._AUDIO_EVIDENCE_CACHE_DIR / f"{NE._audio_evidence_cache_key(vid, meta, kw)}.json"
        if f.exists():
            n_hit += 1
            continue
        sec, err = NE.build_audio_evidence_section(video_path=vid, item_meta=meta, **kw)
        # 11/01: items without a sounding action (the movement set) get a valid Whisper section plus the note "OpenFLAM skipped:
        # no non-speech sounding-action events". new_eval only caches error-free results, so a cache-only run would show no audio
        # evidence at all, while a live run shows this section with a warning. Store section + note, as a live run would use them.
        if sec and err.strip().startswith("OpenFLAM skipped: no non-speech sounding-action events"):
            f.write_text(json.dumps({"section": sec, "error": err, "video": str(Path(vid).resolve()), "item_id": iid,
                                     "note": "flam skipped, no sounding action; stored by gen_evidence_1030 cache stage 11/01"}))
            n_new += 1
            n_skip += 1
            continue
        n_new += bool(sec and not err)
        n_err += bool(err)
        if err:
            print(f"[cache] ERROR {iid}: {err}", flush=True)
        if k % 20 == 0:
            print(f"[cache] {a.set} {k + 1}/{len(V)}", flush=True)
    print(f"[cache] done {a.set}: hit {n_hit}, new {n_new} (of them flam-skipped, no sounding action: {n_skip}), errors {n_err}", flush=True)


def stage_threshold(a):
    import flam_audio as FA
    import new_eval as NE
    f = OUT / "flam_threshold.json"
    if f.exists():
        sys.exit(f"exists, not overwriting: {f}")
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{s}.jsonl")]
    keys = sorted({m["split_key"] for m in man if m["source"] == "hdepic" and m["variant"] == "original"})
    P = {x["item_id"]: x for x in json.load(open("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_prompts_v2.json"))}
    vals = []
    for k, key in enumerate(keys):
        iid = f"hdepic_{key}_pass"
        vid = next(Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval").glob(f"hdepic_medium_shard*/{iid}/{iid}_v1_raw.mp4"))
        meta = NE.build_item_meta_map([P[iid]], modality_filter=None, item_overrides=None, relative_only=False)[iid]
        snd = [s for s in NE.build_scoring_events(meta) if s["kind"] == "sounding_action"]
        if not snd:
            continue
        qs = {s["event_id"]: FA._queries_for_label("sounding_action", s["label"])[0] for s in snd}
        ev = FA.extract_flam_evidence(str(vid), queries=sorted(set(qs.values())), **FLAM_KW)
        mx = {q["query"]: q["max_score"] for q in ev["queries"]}
        vals += [dict(item_id=iid, event_id=e, query=q, max_score=mx[q]) for e, q in qs.items()]
        if k % 20 == 0:
            print(f"[threshold] {k + 1}/{len(keys)}", flush=True)
    s = np.array([v["max_score"] for v in vals])
    rec = dict(T_flam=round(float(np.percentile(s, 5)), 4), n_events=len(vals), n_clips=len(keys),
               quantiles={q: round(float(np.percentile(s, q)), 4) for q in (1, 5, 10, 25, 50)},
               definition="5th percentile of the whole-clip max FLAM score (first pipeline query per sounding event) over the "
                          "sounding events of the P01/P02 v3 original clips (sound present); FLAM settings as FLAM_KW",
               flam_kw={k: v for k, v in FLAM_KW.items() if k != "ckpt_path"}, written=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generated_set_results_seen=False)
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(rec, open(f, "w"), indent=1)
    json.dump(vals, open(OUT / "flam_threshold_events.json", "w"))
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["threshold", "audio", "cache"])
    ap.add_argument("--set", choices=["220", "149", "p3p9", "hdmove", "hdA", "ma", "p12A", "ma39", "avbadd"], default="220")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
