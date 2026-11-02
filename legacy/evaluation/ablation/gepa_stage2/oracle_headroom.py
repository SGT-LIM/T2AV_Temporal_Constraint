#!/usr/bin/env python3
"""No API calls. Oracle selection headroom between the media-only anchor and another condition on the SAME rows.
Per (source, axis): both right / only anchor right / only cond right / both wrong. oracle acc = 1 - both_wrong/n.
  only_cond_right  = what a perfect selector could gain (split: FAIL fixed = recall gain, PASS fixed = precision gain)
  only_anchor_right = what the cond breaks
Noise floor: the same table between two media-only runs, all scored with rep_scoring.row_label (10/28: rep2 vs rep3 same day;
rep1 vs rep2 across days). Refuses to overwrite --out.
  python gepa_stage2/oracle_headroom.py
  python gepa_stage2/oracle_headroom.py --one-call-hd results/hdepic_medium_multi_tools_wf_hop5_g36
"""
import argparse, glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rep_scoring as RS

HELD = "gepa_stage2/runs/v3_test/heldout_v3.csv"
R = "/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent"
V220, T220 = f"{R}/baseline_min3_g36_1027", f"{R}/tools_min3_g36_1027"
COL = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding",
       "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
MODEL = {"ltx": "LTX_2p3", "mova": "MOVA"}
PARENTS = {"AVB": ("A", "V"), "TCR": ("A", "V", "AVB"), "TCC": ("A", "V")}

def lab(x):
    s = str(x).strip().lower()
    return "no" if s in ("no", "fail", "false") else ("yes" if s in ("yes", "pass", "true") else "")

def find_csv(d, pattern="*"):
    best = None
    for f in sorted(glob.glob(f"{d}/**/{pattern}.csv", recursive=True)):
        try: df = pd.read_csv(f, engine="python")
        except Exception: continue
        if "item_id" not in df.columns or not all(c in df.columns for c in COL.values()): continue
        if best is None or len(df) > len(best[1]): best = (f, df)
    if best is None:
        print(f"[warn] no usable csv under {d}"); return None
    print(f"  <- {best[0]} ({len(best[1])} rows)")
    return best[1].drop_duplicates("item_id", keep="last").set_index("item_id")

def col_from_run(base, run_by_src, gate_parents):
    out = []
    for _, r in base.iterrows():
        df = run_by_src.get(r.source)
        if df is None or r.item_id not in df.index: out.append(""); continue
        v = lab(df.loc[r.item_id, COL[r.axis]])
        if gate_parents and r.axis in PARENTS and any(lab(df.loc[r.item_id, COL[p]]) == "no" for p in PARENTS[r.axis]):
            v = ""
        out.append(v)
    return out

def pair_table(base, a, b, title):
    rows = []
    for (src, ax), g in base.groupby(["source", "axis"]):
        g = g[g[a].isin(["yes", "no"]) & g[b].isin(["yes", "no"])]
        if not len(g): continue
        ra, rb, fail = g[a] == g.y, g[b] == g.y, g.y == "no"
        n = len(g)
        rows.append(dict(source=src, axis=ax, n=n, n_fail=int(fail.sum()),
                         acc_a=ra.mean(), acc_b=rb.mean(), oracle=1 - (~ra & ~rb).sum() / n,
                         only_b=int((~ra & rb).sum()), only_b_FAIL=int((~ra & rb & fail).sum()), only_b_PASS=int((~ra & rb & ~fail).sum()),
                         only_a=int((ra & ~rb).sum()), only_a_FAIL=int((ra & ~rb & fail).sum()), only_a_PASS=int((ra & ~rb & ~fail).sum()),
                         both_wrong=int((~ra & ~rb).sum())))
    t = pd.DataFrame(rows)
    print(f"\n== {title}   (a = {a}, b = {b})")
    print("   oracle - acc_a = headroom if a selector were perfect; only_b = rows only b gets right (FAIL/PASS split); only_a = rows b breaks")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--held", default=HELD)
    ap.add_argument("--one-call-hd", default=None, help="HD-EPIC one-call run dir (csv with item_id + axis columns)")
    ap.add_argument("--hd-video-rep2", nargs="+", default=None, help="HD-EPIC media-only rep2 run dirs (medium / regen / move, matched by name); default = the 10/28 rep2 dirs")
    ap.add_argument("--out", default="gepa_stage2/runs/v3_test/oracle_headroom_1028.csv")
    a = ap.parse_args()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)

    h = pd.read_csv(a.held)
    tags = list(h.tag.unique()); print("tags:", tags)
    base = h[h.tag == tags[0]][["uid", "source", "axis", "y", "stage1"]].rename(columns={"stage1": "anchor"}).copy()
    base["item_id"] = base.uid.str.split("|").str[1]
    for t in tags:
        base["two_stage_seed" if t == tags[0] else f"gepa_{t}"] = base.uid.map(h[h.tag == t].set_index("uid").pred)
    base = base[base.anchor.isin(["yes", "no"])]

    tables = []
    tables.append(pair_table(base, "anchor", "two_stage_seed", "anchor vs two-stage seed (all tools, KEEP-first)"))
    for c in [c for c in base.columns if c.startswith("gepa_")]:
        tables.append(pair_table(base, "anchor", c, f"anchor vs {c}"))

    # 10/28: every media-only / one-call run is scored with ONE rule (rep_scoring.row_label = heldout stage1 rule:
    # GT events only, gated events dropped). The 10/27 version read item-level columns for the reruns (gated = FAIL),
    # which made the 220 AVB / TCR noise floor and drift look large. rep1 = the anchor csvs recomputed with that rule
    # (differs from the stored heldout stage1 column only where that column filled gated events by fresh stage-1 calls).
    runs = dict(RS.RUNS)
    if a.hd_video_rep2:
        dirs = {k: [d for d in a.hd_video_rep2 if k in Path(d).name] for k in ("medium", "regen", "move")}
        runs["rep2"] = {**runs["rep2"], "hdepic": dirs["medium"] + dirs["regen"], "hdfoot": dirs["medium"], "hdmove": dirs["move"]}
        print("HD-EPIC rep2 dirs:", dirs)
    man = [json.loads(l) for l in open(RS.MAN)]
    sc = RS.score_rows(man, {k: runs[k] for k in ("rep1", "rep2", "rep3", "d1027", "oc1027")}).set_index("uid")
    base = base.join(sc[["rep1", "rep2", "rep3", "d1027", "oc1027"]], on="uid")

    b220 = base[base.source.isin(MODEL)]
    tables.append(pair_table(b220, "rep1", "d1027", "220 two-day: media-only 10/16 (rep1) vs media-only 10/27, same rule"))
    tables.append(pair_table(b220, "rep2", "rep3", "220 NOISE FLOOR same day: media-only rep2 vs rep3 (10/28)"))
    tables.append(pair_table(b220, "rep1", "rep2", "220: media-only 10/16 (rep1) vs rep2 10/28"))
    tables.append(pair_table(b220, "d1027", "oc1027", "220 same day: media-only 10/27 vs one call 10/27, same rule"))

    bhd = base[~base.source.isin(MODEL)]
    tables.append(pair_table(bhd, "rep1", "rep2", "HD-EPIC: media-only rep1 (10/16, 10/25) vs rep2 (10/28)"))
    tables.append(pair_table(bhd, "rep2", "rep3", "HD-EPIC NOISE FLOOR same day: media-only rep2 vs rep3 (10/28)"))
    if a.one_call_hd:
        print("\nHD-EPIC one call:"); df = find_csv(a.one_call_hd)
        if df is not None:
            bhd = bhd.copy()
            bhd["onecall_hd"] = col_from_run(bhd, {s: df for s in bhd.source.unique()}, gate_parents=True)
            tables.append(pair_table(bhd, "anchor", "onecall_hd", "HD-EPIC: anchor vs one call (item-level columns, old rule)"))

    if Path(a.out).exists():
        sys.exit(f"exists, not overwriting: {a.out}")
    pd.concat(tables, keys=range(len(tables))).to_csv(a.out); print(f"\n-> {a.out}")

if __name__ == "__main__":
    main()
