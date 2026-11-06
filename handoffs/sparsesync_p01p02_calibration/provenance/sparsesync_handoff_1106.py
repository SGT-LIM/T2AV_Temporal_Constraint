#!/usr/bin/env python3
"""SparseSync handoff (11/06): the exact P01/P02 calibration set of the current Synchformer AVB gate. No model calls, no data changes;
reads the calibration inputs and writes only to T2AV_data/tools/sparsesync_handoff_1106/.
Sources (all read-only):
  item set     runs/obsval_1028/rows.jsonl, set "B", cond "anchor" (110 items) = sync_action_1030.py jobs("b110")
  items        real_av_pilot/items_hdepic_medium_with_clips_v2.json (clip window, media op, shift_s, annotation)
  videos       real_av/eval/hdepic_v3test_1028/medium/<item>/<item>_v1_raw.mp4 (link to the cut clip in real_av/hdepic/clips)
  windows      synchformer_action_1030/b110/records/<item>.json (per occurrence: action span and the Synchformer input window)
  calibration  runs/obsval_1028/scores_rows.csv, set B30, cond anchor, verdict present (95 rows) = gate_b110_v2_1030.rows_with_readings
  rule         synchformer_action_1030/PREREGISTERED_RULE.json
  python gepa_stage2/sparsesync_handoff_1106.py
"""
import hashlib, json, re
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path("/projectnb/ivc-ml/youngsun/T2AV_data")
PILOT = DATA / "real_av_pilot/items_hdepic_medium_with_clips_v2.json"
EV = DATA / "real_av/eval"
T_DIR = DATA / "tools/synchformer_action_1030"
OUT = DATA / "tools/sparsesync_handoff_1106"
CODE = [HERE / "gate_b110_v2_1030.py", HERE / "sync_action_1030.py", DATA / "real_av_pilot/make_clips.py"]
VAR = {"original": "original", "fail_audio_shift_early": "audio_shift_early", "fail_audio_shift_late": "audio_shift_late"}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)                        # new directory only; never overwrite
    rows = [json.loads(l) for l in open(HERE / "runs/obsval_1028/rows.jsonl")]
    B = {r["item_id"]: r for r in rows if r["set"] == "B" and r["cond"] == "anchor"}
    it = {x["item_id"]: x for x in json.load(open(PILOT))}
    sc = pd.read_csv(HERE / "runs/obsval_1028/scores_rows.csv")
    cal = sc[(sc["set"] == "B30") & (sc.cond == "anchor") & sc.pred.isin(["yes", "no"])].copy()
    cal["item_id"] = cal.uid.str.split("|").str[1]
    cal = cal.set_index("item_id")
    rule = json.load(open(T_DIR / "PREREGISTERED_RULE.json"))
    man, miss = [], []
    for iid in sorted(B):
        x, r = it[iid], B[iid]
        link = EV / "hdepic_v3test_1028/medium" / iid / f"{iid}_v1_raw.mp4"
        rec = json.load(open(T_DIR / "b110/records" / f"{iid}.json"))
        target = Path(rec.get("video_path", "")) if rec.get("video_path") else link.resolve()
        for p in (link, target):
            if not p.exists():
                miss.append(str(p))
        part = re.match(r"hdepic_(P\d\d)-", iid).group(1)
        assert part in ("P01", "P02"), iid                       # P03-P09 test data never enters the handoff
        evs = []
        for e in rec.get("events", []):
            evs.append(dict(event_id=e["event_id"], label=e.get("label"), kind=e.get("kind"), status=e.get("status"),
                            gt_avb=r["gt"].get(e["event_id"], "not in GT row"),
                            occurrences=[dict(action_span_s=o["span"], span_source=o.get("span_source"), input_window_s=o.get("clip"),
                                              cropped_to_input=o.get("cropped_to_input"),
                                              synchformer_offset_s=o.get("lag"), synchformer_prob=o.get("confidence"),
                                              synchformer_p_offset0=o.get("p_lag0")) for o in e.get("occurrences", [])]))
        shift = float(x["media"].get("shift_s", 0.0)) if x["media"]["op"] == "cut+audio_shift" else 0.0
        c = cal.loc[iid] if iid in cal.index else None
        man.append(dict(
            item_id=iid, participant=part, source_video_id=x["video_id"], source_clip_window_s=x["clip"],
            variant=VAR.get(x["variant"], x["variant"]), media_op=x["media"]["op"], audio_shift_s=shift,
            video_path=str(link), video_file=str(target), video_duration_s=rec.get("duration_sec"),
            gt_row=r["gt"], gt_avb_row="FAIL" if "no" in r["gt"].values() else "PASS",
            in_calibration=c is not None, calibration_role=None if c is None else ("T (originals)" if VAR.get(x["variant"]) == "original" else "P (shifted)"),
            media_only_anchor_verdict=None if c is None else c.pred,
            synchformer=dict(margin_s=rec.get("margin_sec"), mode=rec.get("mode"), ckpt=rec.get("ckpt_id"), tool_version=rec.get("tool_version")),
            binding_events=evs))
    with open(OUT / "manifest_p01p02_calibration.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    # flat per-occurrence table for convenience
    flat = [dict(item_id=m["item_id"], variant=m["variant"], audio_shift_s=m["audio_shift_s"], in_calibration=m["in_calibration"],
                 video_path=m["video_path"], event_id=e["event_id"], label=e["label"], gt_avb=e["gt_avb"], occ=k,
                 action_start_s=o["action_span_s"][0], action_end_s=o["action_span_s"][1],
                 input_start_s=(o["input_window_s"] or [None, None])[0], input_end_s=(o["input_window_s"] or [None, None])[1],
                 synchformer_offset_s=o["synchformer_offset_s"], synchformer_prob=o["synchformer_prob"])
            for m in man for e in m["binding_events"] for k, o in enumerate(e["occurrences"])]
    pd.DataFrame(flat).to_csv(OUT / "occurrences_p01p02_calibration.csv", index=False)
    M = pd.DataFrame(man)
    stats = dict(items=len(M), by_variant=M.variant.value_counts().to_dict(),
                 calibration_rows=int(M.in_calibration.sum()), calibration_by_variant=M[M.in_calibration].variant.value_counts().to_dict(),
                 shift_values_s=sorted(M.audio_shift_s.unique().tolist()), participants=sorted(M.participant.unique().tolist()),
                 occurrences=len(flat), missing_files=miss,
                 source_md5={str(p): md5(p) for p in [PILOT, T_DIR / "PREREGISTERED_RULE.json", HERE / "runs/obsval_1028/scores_rows.csv"] + CODE},
                 rule=rule)
    json.dump(stats, open(OUT / "checks.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k not in ("rule", "source_md5")}, indent=1))


if __name__ == "__main__":
    main()
