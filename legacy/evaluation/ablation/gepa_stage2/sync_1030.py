#!/usr/bin/env python3
"""Synchformer per-event offsets for the 110 set-B rows (10/30). GPU, env t2av_eval_sync. No Gemini calls.

Code: SGT-LIM/t2av_multiagent branch synchformer-avb (read-only clone), Tool_Use/synchformer_sync.compute_sync_record;
Synchformer repo + checkpoint 24-01-04T16-39-21 (AudioSet; md5 54037d2...) under /projectnb/ivc-ml/youngsun/tmp/Synchformer.
Mode window_if_alone_multi, margin 0.64 s (defaults of that repo).
One change: the span lookup's FLAM is OUR Tool_Use/flam_audio.extract_flam_evidence with hop_sec=5 (full 25 s clip, as the
HD-EPIC pipeline runs it); the clone's FLAM has no hop and reads only the first 10 s. Other FLAM settings = that repo's defaults.
Events = the item's binding events (has_binding), not chosen by GT. Per event the stored reading is the occurrence with the
lowest p(offset 0) (that repo's per_event_fields rule): offset, probability of that offset, p(offset 0).

  python gepa_stage2/sync_1030.py      # -> T2AV_data/tools/synchformer_1030/{records/<item_id>.json, per_event.csv}
"""
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import json, sys, traceback
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
CLONE = Path("/projectnb/ivc-ml/youngsun/tmp/t2av_multiagent")
SYNC_ROOT = Path("/projectnb/ivc-ml/youngsun/tmp/Synchformer")
OUT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_1030")
FLAM_CKPT = "/projectnb/ivc-ml/youngsun/.hf_cache/openflam"
FLAM_KW = dict(model_name="v1-base", device="cuda", ckpt_path=FLAM_CKPT, method="unbiased", max_duration_sec=10.0, threshold=0.98,
               min_duration_sec=0.05, merge_gap_sec=0.10, median_filter_size=3, top_k=5, hop_sec=5.0)
WHISPER_KW = dict(model_size="large-v3-turbo", device="cuda", compute_type="float16", language="en", max_segments=200)


def main():
    sys.path.insert(0, str(ABL))
    import new_eval as NE
    # their Tool_Use package under its own name (our repo also has a Tool_Use package)
    import importlib.util
    pk = importlib.util.spec_from_file_location("their_tool_use", CLONE / "Tool_Use" / "__init__.py",
                                                submodule_search_locations=[str(CLONE / "Tool_Use")])
    sys.modules["their_tool_use"] = importlib.util.module_from_spec(pk)
    pk.loader.exec_module(sys.modules["their_tool_use"])
    import importlib
    THEIR_FLAM = importlib.import_module("their_tool_use.flam_audio")
    SS = importlib.import_module("their_tool_use.synchformer_sync")
    sys.path.insert(0, str(ABL / "Tool_Use"))
    spec_path = ABL / "Tool_Use" / "flam_audio.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("our_flam_audio", spec_path)
    OUR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(OUR)
    THEIR_FLAM.extract_flam_evidence = OUR.extract_flam_evidence     # hop_sec support; _locate_spans imports it at call time

    rows = [json.loads(l) for l in open(HERE / "runs/obsval_1028/rows.jsonl")]
    B = {r["item_id"]: r for r in rows if r["set"] == "B" and r["cond"] == "anchor"}
    items = json.load(open("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_prompts_v2.json"))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    (OUT / "records").mkdir(parents=True, exist_ok=True)
    per = []
    for k, (iid, r) in enumerate(sorted(B.items())):
        f = OUT / "records" / f"{iid}.json"
        vid = next(Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_v3test_1028/medium").glob(f"{iid}/{iid}_v1_raw.mp4"))
        events = [{"event_id": s["event_id"], "kind": s["kind"], "label": s["label"]}
                  for s in NE.build_scoring_events(metas[iid]) if s.get("has_binding")]
        if not f.exists():
            try:
                rec = SS.compute_sync_record(str(vid.resolve()), events, synchformer_root=str(SYNC_ROOT), device="cuda", margin_sec=0.64,
                                             whisper_kwargs=WHISPER_KW, flam_kwargs=FLAM_KW, mode="window_if_alone_multi")
                rec["note"] = "span lookup FLAM = T2AV_Temporal_Constraint Tool_Use/flam_audio with hop_sec=5 (full clip)"
            except Exception as e:
                rec = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-1500:]}
            json.dump(rec, open(f, "w"), indent=1)
        rec = json.load(open(f))
        for e in events:
            fields = SS.per_event_fields(rec if "events" in rec else None, e["event_id"])
            ev = next((x for x in rec.get("events", []) if x["event_id"] == e["event_id"]), {})
            occ = ev.get("occurrences", [])
            w = min(occ, key=lambda o: (o["p_lag0"], -abs(o["lag"]))) if occ else None
            per.append(dict(item_id=iid, variant=r["variant"], event_id=e["event_id"], label=e["label"], status=ev.get("status", rec.get("error", "")),
                            offset=None if w is None else w["lag"], prob=None if w is None else w["confidence"],
                            p_offset0=None if w is None else w["p_lag0"], n_occ=len(occ),
                            span=None if w is None else w["span"], spans_all=[o["span"] for o in occ], method=None if w is None else w["method"]))
        print(f"[sync] {k + 1}/{len(B)} {iid}: " + "; ".join(f"{p['event_id']} {p['status']} {p['offset']}" for p in per if p["item_id"] == iid), flush=True)
    pd.DataFrame(per).to_csv(OUT / "per_event.csv", index=False)


if __name__ == "__main__":
    main()
