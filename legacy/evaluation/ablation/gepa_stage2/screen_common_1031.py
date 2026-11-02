#!/usr/bin/env python3
# Replaced by t2av_eval/gate/reliability.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Shared rows / thresholds / report for the tool screening (CLAP, ImageBind, VQAScore, Qwen 3-sample), 10/31. No judge calls.

Sets:
  p1p2   calibration: manifests_v3 HD-EPIC-family rows, all splits (hdepic v2 prompts, hdfoot old prompts, hdmove prompts)
  p3p9   HD-EPIC P03-P09 rows built with the v3 rules (A: _A + originals; V: hand / noun swap + originals; AVB: shifts + originals
         of shifted windows; TCR: order_swap + originals with neighbouring events >= 1.0 s apart; TCC: count_off + originals)
  220    manifests_v3 ltx / mova rows;  149  gt_gen149.jsonl (majority)
Row events: HD-EPIC (p1p2, p3p9) -> every event of the axis (A: has_audio, V: all, AVB: has_binding), as in the v3 GT where every
axis event carries a label; generated -> the GT event ids. Row score = the weakest event; the tool calls the row FAIL when the
score is on the FAIL side of the threshold.
Threshold: on p1p2 PASS rows of the axis, the value that flags 5% of them (false-alarm rate .05), written with a timestamp to
T2AV_data/tools/screen_1031/<tool>/thresholds.json BEFORE any other set is scored; applied unchanged to p3p9, 220, 149.
Report per tool, axis, set and model: open rate, precision when open (agreement with the human majority), recall on human-FAIL rows,
and media-only recall on the same rows (220 / 149: row 1 of 10/30; p3p9 AVB: the 10/30 holdout anchor; others: not yet available).
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import glob, json, os, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ABL))
OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/screen_1031")
E = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
G149 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030")
MIN3 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3")
REL500 = Path((_LEGACY_ROOT + "/new_prompts/generated/relative_500_v5_fixed.json"))
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/items_hdepic_medium_with_clips_v2.json")
PROMPTS_P12 = {"hdepic": E / "hdepic_medium_prompts_v2.json", "hdfoot": E / "hdepic_medium_prompts.json", "hdmove": E / "hdepic_move_prompts.json"}
FA = 0.05


def _video_index():
    idx = {}
    for d in glob.glob(str(E / "hdepic_*")):
        for f in glob.glob(d + "/*/*_v1_raw.mp4"):
            idx.setdefault(Path(f).parent.name, f)
    return idx


def _metas(items):
    import new_eval as NE
    return NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)


def _axis_events(meta, axis):
    import new_eval as NE
    ev = NE.build_scoring_events(meta)
    if axis == "A":
        return [s for s in ev if s.get("has_audio")]
    if axis == "AVB":
        return [s for s in ev if s.get("has_binding")]
    return ev


def rows(which):
    """list of dict(set, model, item_id, axis, y, video, item, events [scoring events], windows {event_id: (t0, t1)})"""
    out = []
    if which == "p1p2":
        idx = _video_index()
        P = {s: {x["item_id"]: x for x in json.load(open(f))} for s, f in PROMPTS_P12.items()}
        M = {s: _metas(list(P[s].values())) for s in P}
        win = {x["item_id"]: x for x in json.load(open(PILOT))}
        man = [json.loads(l) for s in ("train", "val", "test") for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{s}.jsonl")]
        for m in man:
            if m["source"] not in P or m["item_id"] not in idx:
                continue
            meta = M[m["source"]][m["item_id"]]
            out.append(dict(set="p1p2", model=m["source"], item_id=m["item_id"], axis=m["axis"], y="no" if "no" in m["gt"].values() else "yes",
                            video=idx[m["item_id"]], item=P[m["source"]][m["item_id"]], events=_axis_events(meta, m["axis"]),
                            windows=_hd_windows(win.get(m["item_id"]), meta)))
    elif which == "p3p9":
        import filters
        it = {x["item_id"]: x for x in json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))}
        P = {x["item_id"]: x for x in json.load(open(HO / "prompts_hdepic_p3p9.json"))}
        M = _metas(list(P.values()))
        gt = pd.read_csv(HO / "gt_hdepic_p3p9.csv").set_index("item_id")
        col = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
               "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
        wkey = lambda x: (x["video_id"], tuple(x["clip"]))
        shifted = {wkey(x) for x in it.values() if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
        AX = {"fail_absent_sound": ["A"], "fail_hand_swap": ["V"], "fail_noun_swap": ["V"], "fail_audio_shift_early": ["AVB"],
              "fail_audio_shift_late": ["AVB"], "fail_order_swap": ["TCR"], "fail_count_off": ["TCC"], "original": ["A", "V", "AVB", "TCR", "TCC"]}
        for iid, x in sorted(it.items()):
            for ax in AX.get(x["variant"], []):
                if ax == "AVB" and x["variant"] == "original" and wkey(x) not in shifted:
                    continue
                if ax == "TCR" and not filters.min_gap(x["sequence"]) >= 1.0:
                    continue
                meta = M[iid]
                out.append(dict(set="p3p9", model=x["video_id"][:3], item_id=iid, axis=ax, y="no" if gt.loc[iid, col[ax]] == "FAIL" else "yes",
                                video=str(HO / "eval" / iid / f"{iid}_v1_raw.mp4"), item=P[iid], events=_axis_events(meta, ax),
                                windows=_hd_windows(x, meta)))
    else:
        if which == "220":
            P = {x["item_id"]: x for x in json.load(open(REL500))}
            man = [json.loads(l) for s in ("train", "val", "test") for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{s}.jsonl")]
            src = [({"ltx": "LTX_2p3", "mova": "MOVA"}[m["source"]], m) for m in man if m["source"] in ("ltx", "mova")]
            vid = lambda model, iid: str(sorted((MIN3 / model / iid).glob("*.mp4"))[0].resolve())
        else:
            P = {x["item_id"]: x for x in json.load(open(G149 / "prompts_gen149.json"))}
            src = [("LTX_2p3", json.loads(l)) for l in open(G149 / "gt_gen149.jsonl")]
            vid = lambda model, iid: str((G149 / "videos" / iid / f"{iid}_v1_raw.mp4").resolve())
        M = _metas(list(P.values()))
        times = _row1_times(which)
        for model, m in src:
            meta = M[m["item_id"]]
            evs = [s for s in _axis_events(meta, m["axis"]) if s["event_id"] in m["gt"]] if m["axis"] in ("A", "V", "AVB") else _axis_events(meta, "V")
            t = times.get((model, m["item_id"]), {})
            out.append(dict(set=which, model=model, item_id=m["item_id"], axis=m["axis"], y="no" if "no" in m["gt"].values() else "yes",
                            video=vid(model, m["item_id"]), item=P[m["item_id"]], events=evs,
                            windows={e: (max(0.0, v - 0.5), v + 0.5) for e, v in t.items()}))
    return out


def _hd_windows(x, meta):
    """{event_id: (t0, t1)} from the item's annotated event times (HD-EPIC), matched to scoring events by order of non-speech events."""
    if not x:
        return {}
    ev = [e for e in x.get("events", []) if "t" in e]
    sc = _axis_events(meta, "V")
    return {s["event_id"]: (float(e["t"][0]), float(e["t"][1])) for s, e in zip(sc, ev)}


def _row1_times(which):
    """{(model, item_id): {event_id: t}} from the 10/30 row 1 anchor (event_time_s; AVB over V)."""
    R1 = Path((_LEGACY_ROOT + "/eval_results/multi_agent/gen_row1_anchor_g36_1030"))
    pre = {"220": [("LTX_2p3", "LTX_2p3"), ("MOVA", "MOVA")], "149": [("gen149", "LTX_2p3")]}[which]
    out = {}
    for p, model in pre:
        for f in sorted(R1.glob(f"{p}_shard*.csv")):
            if f.name.endswith("_per_event.csv"):
                continue
            for r in pd.read_csv(f).itertuples():
                raw = json.loads(r.raw_output)
                t = {}
                for ax in ("visual_event_correctness", "audio_visual_binding"):
                    try:
                        for e in json.loads(raw.get(ax) or "{}").get("per_event", []):
                            if e.get("event_time_s") is not None:
                                t[e["event_id"]] = float(e["event_time_s"])
                    except (json.JSONDecodeError, AttributeError):
                        pass
                out[(model, r.item_id)] = t
    return out


def write_threshold(tool, axis, scores_pass, low_is_fail=True, note=""):
    """5% false alarm on p1p2 PASS rows; written before any other set is scored."""
    d = OUT / tool
    d.mkdir(parents=True, exist_ok=True)
    f = d / "thresholds.json"
    th = json.load(open(f)) if f.exists() else {}
    if axis in th:
        return th[axis]["threshold"]
    s = np.asarray([x for x in scores_pass if x is not None and not np.isnan(x)], float)
    thr = float(np.quantile(s, FA)) if low_is_fail else float(np.quantile(s, 1 - FA))
    th[axis] = dict(threshold=thr, low_is_fail=low_is_fail, n_pass=int(len(s)), fa_target=FA,
                    fa_on_p1p2=float(np.mean(s < thr) if low_is_fail else np.mean(s > thr)), note=note,
                    written=time.strftime("%Y-%m-%dT%H:%M:%S"), other_sets_scored=False)
    json.dump(th, open(f, "w"), indent=1)
    return thr


def media_only():
    """{(set, model, item_id, axis): label} for the media-only reference available tonight."""
    ref = {}
    f = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028/gen_rows_scored_1030.csv"
    if f.exists():
        d = pd.read_csv(f)
        for r in d[d.row == "row1"].itertuples():
            s, m, iid, ax = r.uid.split("|")
            ref[(s, m, iid, ax)] = r.pred
    f = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028/holdout_rule_rows_1030.csv"
    if f.exists():
        for r in pd.read_csv(f).itertuples():
            ref[("p3p9", r.participant, r.item_id, "AVB")] = r.anchor
    return ref


def report(tool, scored):
    """scored: DataFrame with set, model, item_id, axis, y, tool_fail (bool or NaN when no score)."""
    ref = media_only()
    scored = scored.assign(set=scored["set"].astype(str), model=scored["model"].astype(str))   # csv reads 220 / 149 as ints
    out = []
    for (s, m, ax), g in scored.groupby(["set", "model", "axis"]):
        h = g[g.tool_fail.notna()]
        if not len(h):
            continue
        tf = h.tool_fail.astype(bool)
        fail = h.y == "no"
        mo = h.apply(lambda r: ref.get((r["set"], r["model"], r["item_id"], r["axis"]), ""), axis=1)
        mf = h[fail & mo.isin(["yes", "no"])]
        out.append(dict(tool=tool, set=s, model=m, axis=ax, n=len(h), n_fail=int(fail.sum()), open_rate=round(tf.mean(), 3),
                        precision_open=round((fail & tf).sum() / tf.sum(), 3) if tf.sum() else None,
                        recall=round((fail & tf).sum() / fail.sum(), 3) if fail.sum() else None,
                        n_fail_with_media_only=len(mf),
                        tool_recall_same=round(float(mf.tool_fail.astype(bool).mean()), 3) if len(mf) else None,
                        media_only_recall_same=round(float((mo[mf.index] == "no").mean()), 3) if len(mf) else None))
    t = pd.DataFrame(out)
    t.to_csv(OUT / tool / "report.csv", index=False)
    print(t.to_string(index=False))
    return t


def dump(which):
    """rows/<set>.json for the tools whose envs lack new_eval (ImageBind, VQAScore): event ids, windows, definitions."""
    d = OUT / "rows"
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for r in rows(which):
        defs = {f"event_{k + 1}": e.get("definition", "") for k, e in enumerate(r["item"]["events"])}
        out.append(dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis=r["axis"], y=r["y"], video=r["video"],
                        events=[s["event_id"] for s in r["events"]], windows={k: list(v) for k, v in r["windows"].items()},
                        definitions={s["event_id"]: defs.get(s["event_id"], s.get("label", "")) for s in r["events"]},
                        actions=sorted({e["action"] for e in r["item"]["events"] if e.get("modality") != "speech" and e.get("action")})))
    json.dump(out, open(d / f"{which}.json", "w"))
    return len(out)
