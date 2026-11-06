#!/usr/bin/env python3
"""Portable tools for the P01/P02 AVB-gate calibration set.

  # 1. reproduce the current Synchformer gate (T = 1.8 s, P = .25) from this folder alone
  python tools/calibrate_thresholds.py reproduce
  # 2. check that local videos are the calibration videos (existence; --sha256 also checks content)
  python tools/calibrate_thresholds.py verify --video-root /path/to/T2AV_TemporalConstraint_HDEPIC [--sha256]
  # 3. derive T / P for another sync model (e.g. SparseSync) from a CSV with one reading per event occurrence:
  #    columns item_id, event_id, occurrence, offset_s, prob, p_offset0   (same windows as event_windows.csv)
  python tools/calibrate_thresholds.py derive --readings sparsesync_readings.csv --grid 0.2

The video root can also be given with the environment variable T2AV_HDEPIC_VIDEO_ROOT. It must contain the Hugging Face dataset
layout videos/<item_id>/<item_id>_v1_raw.mp4.
"""
import argparse, hashlib, json, os, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent.parent


def item_readings(occ):
    """per event: occurrence with the lowest p(offset 0) (ties: larger |offset|); per item: event with the largest |offset|
    (ties: higher probability). Same as provenance/gate_b110_v2_1030.py + sync_action_1030.py."""
    occ = occ.assign(absoff=occ.offset_s.abs())
    ev = occ.sort_values(["p_offset0", "absoff"], ascending=[True, False]).drop_duplicates(["item_id", "event_id"])
    return ev.sort_values(["absoff", "prob"], ascending=False).drop_duplicates("item_id").set_index("item_id")


def derive(readings, grid):
    mem = pd.read_csv(HERE / "calibration_membership.csv").set_index("item_id")
    cal = mem[mem.in_calibration]
    r = item_readings(readings)
    a = cal.join(r[["absoff", "prob"]], how="left")
    if a.absoff.isna().any():
        print(f"warning: {int(a.absoff.isna().sum())} calibration items have no reading", file=sys.stderr)
    orig, shf = a[a.variant == "original"], a[a.variant != "original"]
    T_raw = float(orig.absoff.quantile(0.95))
    T = round(round(T_raw / grid) * grid, 2)
    sel = shf[shf.absoff > T + 1e-9]
    P_raw = float(sel.prob.quantile(0.05)) if len(sel) else float("nan")
    P = round(P_raw, 2)
    fire = (a.absoff >= T - 1e-9) & (a.prob >= P - 1e-9)
    anchor_ok = a.media_only_anchor_verdict == a.gt_avb_row.map({"PASS": "yes", "FAIL": "no"})
    broken_orig = int((anchor_ok & fire & (a.variant == "original")).sum())
    return dict(n_originals=len(orig), n_shifted=len(shf), T_raw=T_raw, T=T, n_shifted_above_T=len(sel), P_raw=P_raw, P=P,
                fired=int(fire.sum()), broken_originals=broken_orig, allowed_broken=int(round(0.05 * len(orig))),
                gate_ok=broken_orig <= int(round(0.05 * len(orig))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["reproduce", "verify", "derive"])
    ap.add_argument("--video-root", default=os.environ.get("T2AV_HDEPIC_VIDEO_ROOT"))
    ap.add_argument("--sha256", action="store_true")
    ap.add_argument("--readings")
    ap.add_argument("--grid", type=float, default=0.2)
    a = ap.parse_args()
    if a.cmd == "reproduce":
        w = pd.read_csv(HERE / "event_windows.csv").rename(columns={"synchformer_offset_s": "offset_s", "synchformer_prob": "prob",
                                                                    "synchformer_p_offset0": "p_offset0"})
        print(json.dumps(derive(w, 0.2), indent=1))
    elif a.cmd == "derive":
        print(json.dumps(derive(pd.read_csv(a.readings), a.grid), indent=1))
    else:
        if not a.video_root:
            sys.exit("give --video-root or set T2AV_HDEPIC_VIDEO_ROOT")
        bad = 0
        for m in map(json.loads, open(HERE / "manifest.jsonl")):
            p = Path(a.video_root) / m["video_relpath"]
            if not p.exists():
                print("missing", p); bad += 1; continue
            if a.sha256:
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for b in iter(lambda: f.read(1 << 20), b""):
                        h.update(b)
                if h.hexdigest() != m["video_sha256"]:
                    print("sha256 differs", p); bad += 1
        print("all 110 videos OK" if not bad else f"{bad} problems")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
