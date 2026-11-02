#!/usr/bin/env python3
"""Per-class table under the 11/01 anchor rule (build_items --anchor-mode eligible), whole videos P01-P09. No calls.
Pairs: build_items.find_anchors_eligible (clean-pair rule for every verb class and every non-ambient sound class; the three collision
classes excluded by the user are counted separately for reference). Loudness: make_mute_anchor.db_reimpl on the 25 s window the
builder would cut for the pair (start 5 s before the action; window_s 25), 16 kHz mono; turn-off tap (verb class 8, noun tap) on the
0.2 s before the water sound ends. Pass = dB >= 20.
  python gepa_stage2/eligible_class_table_1101.py   -> runs/obsval_1028/eligible_pairs_1101.csv, docs/event_inventory_1101.md section
"""
import importlib.util, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_mute_anchor as MA

PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
VID = {p: Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/videos") if p in ("P01", "P02") else
       Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/videos_P03_P09") for p in [f"P0{k}" for k in range(1, 10)]}
DOC = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/docs/event_inventory_1101.md")
SR, W, PAD = 16000, 25.0, 5.0


def main():
    spec = importlib.util.spec_from_file_location("build_items", PILOT / "build_items.py")
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    parts = [f"P0{k}" for k in range(1, 10)]
    s, n = B.load_hdepic(parts)
    excl = B.EXCLUDED_CLASSES
    B.EXCLUDED_CLASSES = set()                      # count the excluded classes too, flagged below
    anc = B.find_anchors_eligible(s, n)
    anc["participant"] = anc.video_id.str[:3]
    anc["excluded"] = anc["sound"].isin(excl)
    dbs = []
    for vid, g in anc.groupby("video_id", sort=False):
        f = VID[vid[:3]] / f"{vid}.mp4"
        if not f.exists():
            dbs += [(i, np.nan) for i in g.index]; continue
        r = subprocess.run(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(f), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True)
        y = np.frombuffer(r.stdout, np.float32).astype(np.float64)
        for i, a in g.iterrows():
            lo = max(0.0, a.a_st - PAD)
            seg = y[int(lo * SR): int((lo + W) * SR)]
            tap = a.vc == 8 and a.nc == B.TAP_NC
            dbs.append((i, round(float(MA.db_reimpl(seg, a.s_st - lo, min(a.s_en, lo + W) - lo, tap)), 2)))
        print(f"[eligible] {vid}: {len(g)} pairs", flush=True)
    anc["db"] = pd.Series(dict(dbs))
    anc["pass20"] = anc.db >= 20
    anc.to_csv(HERE / "runs/obsval_1028/eligible_pairs_1101.csv", index=False)
    T = anc.groupby(["sound", "participant"]).agg(n=("db", "size"), k=("pass20", "sum"))
    elig = anc[~anc.excluded]
    shown = elig.groupby("sound").pass20.sum()
    shown = shown[shown >= 1].sort_values(ascending=False).index
    L = ["", "## Per-class table under the 11/01 anchor rule (whole videos, P01–P09)", "",
         "**Rule** (`build_items.py --anchor-mode eligible`; script `gepa_stage2/eligible_class_table_1101.py`; pairs in `runs/obsval_1028/eligible_pairs_1101.csv`):",
         "- any non-ambient HD-EPIC-Sounds class paired with any narration action under the find_anchors clean-pair rule;",
         "- the collision classes metal-only, plastic-only and metal / plastic are excluded (user, 11/01);",
         "- loudness: make_mute_anchor.db_reimpl on the 25 s builder window (from 5 s before the action), with turn-off taps measured on the water stopping;",
         "- a pair passes at ≥ 20 dB.", "",
         "Classes with at least one passing pair. Each cell shows `pairs / pass`.", "",
         "| sound class | " + " | ".join(parts) + " | P01/P02 pass | P03–P09 pass | top verbs of passing pairs |", "|---|" + "---|" * len(parts) + "---|---|---|"]
    for c in shown:
        cells = [f"{int(T.loc[(c, p)].n)} / {int(T.loc[(c, p)].k)}" if (c, p) in T.index else "0" for p in parts]
        g = elig[elig["sound"] == c]
        a12 = int(g[g.participant.isin(["P01", "P02"])].pass20.sum()); a39 = int(g[~g.participant.isin(["P01", "P02"])].pass20.sum())
        verbs = ", ".join(f"{v} ({k})" for v, k in g[g.pass20].verb.value_counts().head(4).items())
        L.append(f"| {c} | " + " | ".join(cells) + f" | {a12} | {a39} | {verbs} |")
    zero = sorted(set(elig["sound"]) - set(shown))
    L += ["", f"Eligible classes with no passing pair ({len(zero)}): " + ", ".join(f"{c} ({int((elig['sound'] == c).sum())} pairs)" for c in zero), "",
          "Excluded collision classes, for reference (pairs / pass, all participants): " +
          ", ".join(f"{c} {int((anc['sound'] == c).sum())} / {int(anc[anc['sound'] == c].pass20.sum())}" for c in sorted(excl)), ""]
    for c in ("water", "beep"):
        g = elig[elig["sound"] == c]
        L.append(f"- {c}: {len(g)} pairs, {int(g.pass20.sum())} pass" + (" → drops out under the 20 dB rule." if int(g.pass20.sum()) == 0 else "."))
    DOC.write_text(DOC.read_text() + "\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
