#!/usr/bin/env python3
"""Synchformer on the generated sets with the ANCHOR-TIME window (10/30). GPU, env t2av_eval_sync. No Gemini calls.

Same code, checkpoint and mode as sync_action_1030.py (t2av_multiagent synchformer-avb, 24-01-04T16-39-21, window_if_alone_multi,
margin 0.64 s). Each binding event's span is [t, t + 1 video frame] with t = the event's event_time_s from the row 1 anchor (media-only, flag
T2AV_EVENT_TIME_FIELD=1): the AVB call's value if AVB was called for the event, else the V call's value. No anchor time (null,
or the field missing) -> the whole clip, flagged span_source=whole_clip.
Per event: the least-in-sync occurrence (lowest p(offset 0)): offset, probability, p(offset 0).

  python gepa_stage2/sync_gen_1030.py run --set 220 --shard 0 --nshards 2     # -> <OUT>/<set>/records, per_event_shard<k>.csv
  python gepa_stage2/sync_gen_1030.py texts                                   # T_batch / P_batch, section texts for rows 2 / 2b / 4 / 5
Label-free batch thresholds (change i): per batch (220-LTX, 220-MOVA, 149), over the strongest binding-event reading of each video:
  T_batch = median + 2.44 * MAD(|offset|), P_batch = median + 2.44 * MAD(probability); 2.44 = 1.645 * 1.4826, nothing fitted.
The labeled T_tool = 1.8 s / P_tool = .25 (PREREGISTERED_RULE.json) is kept for comparison; |T_batch - T_tool| > 0.2 s is flagged.
"""
from t2av_eval import paths as _P
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, json, sys, traceback
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
pass  # (legacy sys.path insert removed); pass  # (legacy sys.path insert removed)
OUT = Path((str(_P.DATA) + "/tools/synchformer_gen_1030"))
RULE = Path((str(_P.DATA) + "/tools/synchformer_action_1030/PREREGISTERED_RULE.json"))
R1 = Path((str(_P.INPUTS / "eval_results/multi_agent/gen_row1_anchor_g36_1030")))
CLIP = 5.04


def anchor_times(prefix, iid):
    """{event_id: t} from the row 1 anchor raw_output (AVB value preferred over V). prefix: LTX_2p3 / MOVA (220) or gen149."""
    import glob
    fs = [f for f in sorted(glob.glob(str(R1 / f"{prefix}_shard*.csv"))) if not f.endswith("_per_event.csv")]
    if not hasattr(anchor_times, "_df"):
        anchor_times._df = {}
    if prefix not in anchor_times._df:
        anchor_times._df[prefix] = pd.concat(pd.read_csv(f) for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
    df = anchor_times._df[prefix]
    if iid not in df.index:
        return {}
    raw = json.loads(df.loc[iid, "raw_output"])
    t = {}
    for ax in ("visual_event_correctness", "audio_visual_binding"):     # AVB last -> wins
        try:
            for e in json.loads(raw.get(ax) or "{}").get("per_event", []):
                if e.get("event_time_s") is not None:
                    t[e["event_id"]] = float(e["event_time_s"])
        except (json.JSONDecodeError, AttributeError):
            pass
    return t


def stage_run(a):
    from t2av_eval.evidence.gen_evidence import videos
    from t2av_eval.evidence.synchformer_action import their_ss, SYNC_ROOT
    from t2av_eval.judge.media import core as NE
    SS = their_ss()
    J = videos(a.set)[a.shard::a.nshards]
    od = OUT / a.set
    (od / "records").mkdir(parents=True, exist_ok=True)
    per = []
    for k, (iid, model, vid, item) in enumerate(J):
        meta = NE.build_item_meta_map([item], modality_filter=None, item_overrides=None, relative_only=False)[iid]
        binding = [s for s in NE.build_scoring_events(meta) if s.get("has_binding")]
        if not binding:
            continue
        at = anchor_times(model if a.set == "220" else "gen149", iid)
        # anchor time t -> span [t, t + one video frame] (compute_sync_record drops zero-length spans), t clamped into the clip
        fr = 1.0 / SS.VFPS
        tt = lambda t: min(max(float(t), 0.0), CLIP - 2 * fr)
        spans = {s["event_id"]: (([(tt(at[s["event_id"]]), tt(at[s["event_id"]]) + fr)], "anchor_time") if s["event_id"] in at
                                 else ([(0.0, CLIP)], "whole_clip")) for s in binding}
        SS._locate_spans = lambda video_path, events, wk, fk, _sp=spans: {ev["event_id"]: _sp[ev["event_id"]] for ev in events}
        f = od / "records" / f"{model}__{iid}.json"
        if not f.exists():
            try:
                rec = SS.compute_sync_record(vid, [{"event_id": s["event_id"], "kind": s["kind"], "label": s["label"]} for s in binding],
                                             synchformer_root=str(SYNC_ROOT), device="cuda", margin_sec=0.64,
                                             whisper_kwargs={}, flam_kwargs={}, mode="window_if_alone_multi")
                rec["spans"] = {e: dict(span=v[0], source=v[1]) for e, v in spans.items()}
            except Exception as ex:
                rec = {"error": f"{type(ex).__name__}: {ex}", "tb": traceback.format_exc()[-1500:]}
            json.dump(rec, open(f, "w"), indent=1)
        rec = json.load(open(f))
        for s in binding:
            ev = next((x for x in rec.get("events", []) if x["event_id"] == s["event_id"]), {})
            occ = ev.get("occurrences", [])
            w = min(occ, key=lambda o: (o["p_lag0"], -abs(o["lag"]))) if occ else None
            per.append(dict(set=a.set, model=model, item_id=iid, event_id=s["event_id"], label=s["label"],
                            span_source=rec.get("spans", {}).get(s["event_id"], {}).get("source"),
                            status=ev.get("status", rec.get("error", "")), offset=None if w is None else w["lag"],
                            prob=None if w is None else w["confidence"], p_offset0=None if w is None else w["p_lag0"]))
        print(f"[sync-gen] {a.set} shard {a.shard}: {k + 1}/{len(J)} {model} {iid}", flush=True)
    pd.DataFrame(per).to_csv(od / f"per_event_shard{a.shard}.csv", index=False)


def mad_thr(x):
    x = np.asarray(x, float)
    med = float(np.median(x))
    return med + 2.44 * float(np.median(np.abs(x - med)))


def stage_texts(a):
    rule = json.load(open(RULE))
    pe = pd.concat(pd.read_csv(f) for s in ("220", "149") for f in sorted((OUT / s).glob("per_event_shard*.csv")))
    pe["batch"] = pe["set"].astype(str) + "-" + pe["model"]
    ok = pe[pe.status == "ok"].assign(absoff=lambda t: t.offset.abs())
    best = ok.sort_values(["absoff", "prob"], ascending=False).drop_duplicates(["batch", "item_id"])
    thr = {}
    for b, g in best.groupby("batch"):
        T, P = mad_thr(g.absoff), mad_thr(g.prob)
        thr[b] = dict(n_videos=len(g), T_batch=round(T, 3), P_batch=round(P, 3), T_tool=rule["T"], P_tool=rule["P"],
                      T_differs_gt_0p2=abs(T - rule["T"]) > 0.2,
                      fire_batch=int(((g.absoff >= T - 1e-9) & (g.prob >= P - 1e-9)).sum()),
                      fire_tool=int(((g.absoff >= rule["T"] - 1e-9) & (g.prob >= rule["P"] - 1e-9)).sum()))
    json.dump(thr, open(OUT / "batch_thresholds.json", "w"), indent=1)
    print(json.dumps(thr, indent=1))
    from t2av_eval.evidence.gen_evidence import videos
    sec, obs = {}, {}
    for s in ("220", "149"):
        for iid, model, vid, item in videos(s):
            g = pe[(pe["set"].astype(str) == s) & (pe.model == model) & (pe.item_id == iid)]
            if not len(g):
                continue
            multi = len(g) > 1
            lines = []
            for r in g.itertuples():
                pre = f"'{r.label}': " if multi else ""
                if r.status != "ok" or pd.isna(r.offset):
                    lines.append(f"{pre}Synchformer, window around the action: no reading")
                else:
                    lines.append(f"{pre}Synchformer, window around the action: most likely offset {float(r.offset):+.1f} s (positive = audio "
                                 f"later than video), probability {float(r.prob):.2f}; probability of zero offset {float(r.p_offset0):.2f}")
            sec[str(Path(vid).resolve())] = (
                "Synchformer audio-visual synchronization (raw offset estimate):\n"
                "- Synchformer estimates the offset between the audio track and the video in a short window around each binding "
                "event's visible action. Offsets are on a 0.2 s grid; probabilities are the model's own, not correctness labels.\n"
                + "\n".join(f"- {l}" for l in lines))
            obs[f"{s}|{model}|{iid}"] = "\n".join(lines)
    json.dump(sec, open(OUT / "sync_sections_oncall.json", "w"), indent=1)
    json.dump(obs, open(OUT / "sync_obs_lines.json", "w"), indent=1)
    print(f"sections {len(sec)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "texts"])
    ap.add_argument("--set", choices=["220", "149"], default="220")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
