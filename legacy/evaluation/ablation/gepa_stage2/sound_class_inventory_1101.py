#!/usr/bin/env python3
"""Every HD-EPIC-Sounds class that co-occurs with a narration action inside the evaluation windows, P01-P09 (11/01). No calls.

build_items.py (P01/P02 and P03-P09) pairs sounds with actions only through the fixed table ANCHOR_VC (close -> open / close,
cut -> cut / chop, press -> beep, turn-off tap -> water); every other class is never considered. This inventory applies the
SAME clean-pair rule as build_items.find_anchors to every verb class and every non-ambient sound class:
  exactly one segment of that class overlaps the action (+-0.15 s); the segment is < 5 s (longer = background, as load_hdepic);
  it overlaps no other narration; it starts before the action ends (+0.15 s).
Pairs are kept when action and sound lie inside one of the 577 windows (P01/P02: 194 windows of items_hdepic_medium_with_clips_v2;
P03-P09: 383 holdout windows); a pair in two overlapping windows counts once.
Loudness: the re-implementation (RMS of the 0.2 s after the sound onset / median 50 ms frame RMS of the window clip, 16 kHz mono),
which reads about 3-4 dB below the stored 10/08 values on P01/P02; >= 20 dB and >= 16 dB are both reported.
  python gepa_stage2/sound_class_inventory_1101.py   -> runs/obsval_1028/sound_class_pairs_1101.csv, appended to docs/event_inventory_1101.md
"""
import json, subprocess, sys
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
DOC = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/docs/event_inventory_1101.md")
AMBIENT = {"background", "sizzling / boiling", "kettle / mixer / appliance", "hoover / fan"}
TOL, MAXS = 0.15, 5.0
ANCHOR = {"open / close", "cut / chop", "beep", "water"}


def bi():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_items", PILOT / "build_items.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def audio16(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def db(y, s0):
    sr, w, fr = 16000, int(0.2 * 16000), int(0.05 * 16000)
    seg = y[int(s0 * sr): int(s0 * sr) + w]
    F = np.sqrt(np.array([np.mean(y[i:i + fr] ** 2) for i in range(0, len(y) - fr, fr)]))
    return 20 * np.log10(max(np.sqrt(np.mean(seg ** 2)) if len(seg) else 0, 1e-12) / max(np.median(F), 1e-12))


def main():
    B = bi()
    s, n = B.load_hdepic([f"P0{k}" for k in range(1, 10)])
    s = s[~s["class"].isin(AMBIENT)]
    wins = []
    for x in json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json")):
        if x["variant"] == "original":
            wins.append(dict(video_id=x["video_id"], lo=float(x["clip"][0]), hi=float(x["clip"][1]),
                             clip=str((PILOT / x["clip_path"]).resolve()) if not str(x["clip_path"]).startswith("/") else x["clip_path"]))
    for x in json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json")):
        if x["variant"] == "original":
            wins.append(dict(video_id=x["video_id"], lo=float(x["clip"][0]), hi=float(x["clip"][1]), clip=x["clip_path"]))
    W = pd.DataFrame(wins).drop_duplicates(["video_id", "lo"])
    rows = []
    for vid, wg in W.groupby("video_id"):
        g = n[n.video_id == vid]; sg = s[s.video_id == vid]
        st, en, cl = sg.st.values, sg.en.values, sg["class"].values
        nst, nen = g.start_timestamp.values, g.end_timestamp.values
        for r in g.itertuples():
            idx = np.where((st < r.end_timestamp + TOL) & (en > r.start_timestamp - TOL))[0]
            for c in set(cl[idx]):
                hit = [i for i in idx if cl[i] == c]
                if len(hit) != 1:
                    continue
                i = hit[0]
                if ((nst < en[i]) & (nen > st[i])).sum() != 1 or st[i] > r.end_timestamp + TOL:
                    continue
                inw = wg[(wg.lo <= r.start_timestamp) & (r.end_timestamp <= wg.hi) & (wg.lo <= st[i]) & (st[i] < wg.hi)]
                if not len(inw):
                    continue
                w = inw.iloc[0]
                rows.append(dict(participant=vid[:3], video_id=vid, nid=r.unique_narration_id, verb=r.verb, vc=int(r.vc), noun=r.noun,
                                 sound=c, s_rel=float(st[i] - w["lo"]), clip=w["clip"], anchor_class=c in ANCHOR))
    D = pd.DataFrame(rows).drop_duplicates(["video_id", "nid", "sound"])
    cache = {}
    dbs = []
    for c, s0 in zip(D["clip"], D["s_rel"]):                  # D["clip"], not D.clip (the DataFrame.clip method)
        if c not in cache:
            cache.clear(); cache[c] = audio16(c)
        dbs.append(round(float(db(cache[c], s0)), 2))
    D["db"] = dbs
    D.to_csv(HERE / "runs/obsval_1028/sound_class_pairs_1101.csv", index=False)
    parts = [f"P0{k}" for k in range(1, 10)]
    T = D.assign(p20=D.db >= 20, p16=D.db >= 16).groupby(["sound", "participant"]).agg(n=("db", "size"), n20=("p20", "sum"), n16=("p16", "sum"))
    L = ["", "## Sound classes co-occurring with a narration action inside the windows (all classes, P01–P09; 11/01)", "",
         "**Fixed 4-class table.** `build_items.py` pairs sounds with actions only through `ANCHOR_VC`: close → open / close, cut → cut / chop, press → beep, turn-off tap → water.",
         "- The P03–P09 build used the same script, so it inherited that table.",
         "- Every other class is never considered. It is filtered out by construction, not for lack of instances.", "",
         "**Rule used here.** The `find_anchors` clean-pair rule, applied to every verb class and every non-ambient sound class (script `gepa_stage2/sound_class_inventory_1101.py`, pairs in `runs/obsval_1028/sound_class_pairs_1101.csv`):",
         "- exactly one segment of the class overlaps the action (±0.15 s);",
         "- the segment is shorter than 5 s;",
         "- it overlaps no other narration;",
         "- it starts before the action ends.", "",
         "**Scope.** Pairs inside the 577 windows: P01/P02 194, P03–P09 383.", "",
         "**Loudness.** The re-implementation, which reads about 3–4 dB below the stored P01/P02 values. Each cell shows `pairs / ≥ 20 dB / ≥ 16 dB`.", "",
         "| sound class | anchor class now | " + " | ".join(parts) + " | P01/P02 ≥ 20 dB | P03–P09 ≥ 20 dB | top verbs |",
         "|---|---|" + "---|" * len(parts) + "---|---|---|"]
    order = D.groupby("sound").size().sort_values(ascending=False).index
    for c in order:
        cells = []
        for p in parts:
            if (c, p) in T.index:
                t = T.loc[(c, p)]; cells.append(f"{int(t.n)} / {int(t.n20)} / {int(t.n16)}")
            else:
                cells.append("0")
        g = D[D.sound == c]
        a = int(((g.db >= 20) & g.participant.isin(["P01", "P02"])).sum()); b = int(((g.db >= 20) & ~g.participant.isin(["P01", "P02"])).sum())
        verbs = ", ".join(f"{v} ({k})" for v, k in g.verb.value_counts().head(4).items())
        L.append(f"| {c} | {'yes' if c in ANCHOR else 'no'} | " + " | ".join(cells) + f" | {a} | {b} | {verbs} |")
    DOC.write_text(DOC.read_text() + "\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
