#!/usr/bin/env python3
"""Synchformer with ACTION-WINDOW spans (10/30, rev 2). GPU, env t2av_eval_sync. No Gemini calls.

Same code, checkpoint and mode as sync_1030.py (t2av_multiagent synchformer-avb, 24-01-04T16-39-21, window_if_alone_multi,
margin 0.64 s), but every binding event's spans are its VISIBLE action occurrences from the annotation
([occurrence start, occurrence start + action duration]); no FLAM span is needed, so every event gets a reading.
Per event: the least-in-sync occurrence (lowest p(offset 0)): offset, probability, p(offset 0).

  python gepa_stage2/sync_action_1030.py --set b110 --shard 0 --nshards 2
  python gepa_stage2/sync_action_1030.py --set holdout --shard 1 --nshards 2
  -> T2AV_data/tools/synchformer_action_1030/<set>/records/<item_id>.json, per_event_shard<k>.csv
"""
from t2av_eval import paths as _P
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, importlib, importlib.util, json, sys, traceback
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
CLONE = Path("/projectnb/ivc-ml/youngsun/tmp/t2av_multiagent")
SYNC_ROOT = Path("/projectnb/ivc-ml/youngsun/tmp/Synchformer")
OUT = Path((str(_P.DATA) + "/tools/synchformer_action_1030"))
HO = Path((str(_P.DATA) + "/real_av_holdout_p3p9_1028"))
EV = Path((str(_P.DATA) + "/real_av/eval"))
PILOT = Path((str(_P.DATA) + "/real_av_pilot"))


def their_ss():
    pk = importlib.util.spec_from_file_location("their_tool_use", CLONE / "Tool_Use" / "__init__.py",
                                                submodule_search_locations=[str(CLONE / "Tool_Use")])
    sys.modules["their_tool_use"] = importlib.util.module_from_spec(pk)
    pk.loader.exec_module(sys.modules["their_tool_use"])
    return importlib.import_module("their_tool_use.synchformer_sync")


def jobs(which):
    """[(item_id, variant, video, items-json events, prompt item)]"""
    if which == "b110":
        rows = [json.loads(l) for l in open(_P.WORK / "obsval_1028/rows.jsonl")]
        B = {r["item_id"]: r["variant"] for r in rows if r["set"] == "B" and r["cond"] == "anchor"}
        it = {x["item_id"]: x for x in json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))}
        pr = {x["item_id"]: x for x in json.load(open(EV / "hdepic_medium_prompts.json"))}
        return [(i, v, str(next((EV / "hdepic_v3test_1028/medium").glob(f"{i}/{i}_v1_raw.mp4")).resolve()), it[i]["events"], pr[i])
                for i, v in sorted(B.items())]
    if which == "avbadd":   # 11/02 AVB additions (eligible-class windows that overlap no existing window), both groups
        A = EV / "hdepic_avbadd_1102"
        out = []
        for g in ("p12", "p3p9"):
            it = json.load(open(A / g / "items_avbadd_with_clips.json"))
            pr = {x["item_id"]: x for x in json.load(open(A / g / "prompts_avbadd.json"))}
            out += [(x["item_id"], x["variant"], str((A / g / "eval" / x["item_id"] / f"{x['item_id']}_v1_raw.mp4").resolve()), x["events"], pr[x["item_id"]])
                    for x in sorted(it, key=lambda x: x["item_id"]) if x["item_id"] in pr]
        return out
    if which == "p12all":   # 11/01 option (ii): AVB items of all P01/P02 windows (shift early / late + originals of shifted windows), minus b110
        done = {f.stem for f in (OUT / "b110" / "records").glob("*.json")}
        it = json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))
        pr = {x["item_id"]: x for x in json.load(open(EV / "hdepic_medium_prompts_v2.json"))}
        win = lambda x: (x["video_id"], tuple(x["clip"]))
        ws = {win(x) for x in it if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
        sel = [x for x in it if (x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late") or (x["variant"] == "original" and win(x) in ws))
               and x["item_id"] not in done and x["item_id"] in pr]
        V = EV / "hdepic_main_1101"
        vid = lambda i: str(next(p for p in (V / "p12all_new" / i / f"{i}_v1_raw.mp4", V / "hdepic_p12" / i / f"{i}_v1_raw.mp4") if p.exists()).resolve())
        return [(x["item_id"], x["variant"], vid(x["item_id"]), x["events"], pr[x["item_id"]]) for x in sorted(sel, key=lambda x: x["item_id"])]
    it = json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))
    pr = {x["item_id"]: x for x in json.load(open(HO / "prompts_hdepic_p3p9.json"))}
    win = lambda x: (x["video_id"], tuple(x["clip"]))
    ws = {win(x) for x in it if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
    sel = [x for x in it if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late") or (x["variant"] == "original" and win(x) in ws)]
    return [(x["item_id"], x["variant"], str((HO / "eval" / x["item_id"] / f"{x['item_id']}_v1_raw.mp4").resolve()), x["events"], pr[x["item_id"]])
            for x in sorted(sel, key=lambda x: x["item_id"])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["b110", "holdout", "p12all", "avbadd"], required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()
    pass  # (legacy sys.path insert removed)
    from t2av_eval.judge.media import core as NE
    SS = their_ss()
    J = jobs(a.set)[a.shard::a.nshards]
    od = OUT / a.set
    (od / "records").mkdir(parents=True, exist_ok=True)
    per = []
    for k, (iid, var, vid, ievents, pitem) in enumerate(J):
        meta = NE.build_item_meta_map([pitem], modality_filter=None, item_overrides=None, relative_only=False)[iid]
        binding = [s for s in NE.build_scoring_events(meta) if s.get("has_binding")]
        acts = {f"{e['verb']} {e['noun']}": e for e in ievents if e.get("kind") == "sounding"}
        spans = {}
        for s in binding:
            e = acts.get(s["label"])
            if e is None:
                spans[s["event_id"]] = ([], "visible action: no annotation match")
                continue
            d = e["t"][1] - e["t"][0]
            spans[s["event_id"]] = ([(o, o + d) for o in (e.get("occurrences") or [e["t"][0]])], "visible action (annotation)")
        SS._locate_spans = lambda video_path, events, wk, fk, _sp=spans: {ev["event_id"]: _sp.get(ev["event_id"], ([], "")) for ev in events}
        f = od / "records" / f"{iid}.json"
        if not f.exists():
            try:
                rec = SS.compute_sync_record(vid, [{"event_id": s["event_id"], "kind": s["kind"], "label": s["label"]} for s in binding],
                                             synchformer_root=str(SYNC_ROOT), device="cuda", margin_sec=0.64,
                                             whisper_kwargs={}, flam_kwargs={}, mode="window_if_alone_multi")
                rec["note"] = "spans = visible action occurrences from the annotation (no FLAM)"
            except Exception as ex:
                rec = {"error": f"{type(ex).__name__}: {ex}", "tb": traceback.format_exc()[-1500:]}
            json.dump(rec, open(f, "w"), indent=1)
        rec = json.load(open(f))
        for s in binding:
            ev = next((x for x in rec.get("events", []) if x["event_id"] == s["event_id"]), {})
            occ = ev.get("occurrences", [])
            w = min(occ, key=lambda o: (o["p_lag0"], -abs(o["lag"]))) if occ else None
            per.append(dict(item_id=iid, variant=var, event_id=s["event_id"], label=s["label"], status=ev.get("status", rec.get("error", "")),
                            offset=None if w is None else w["lag"], prob=None if w is None else w["confidence"],
                            p_offset0=None if w is None else w["p_lag0"], n_occ=len(occ), method=None if w is None else w["method"]))
        print(f"[sync-action] {a.set} shard {a.shard}: {k + 1}/{len(J)} {iid}", flush=True)
    pd.DataFrame(per).to_csv(od / f"per_event_shard{a.shard}.csv", index=False)


if __name__ == "__main__":
    main()
