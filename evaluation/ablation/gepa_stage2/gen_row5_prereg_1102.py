#!/usr/bin/env python3
"""Generated block (220, 149): row 5 re-assembled under the pre-registered thresholds, 11/02. No calls.
The 10/30 row 5 AVB admission used the label-free T_batch / P_batch (degenerate on generated video: T_batch 0.0, P_batch > 1).
Here AVB admission = the pre-registered rule (synchformer_action_1030/PREREGISTERED_RULE.json, |offset| >= T and p >= P on the
strongest binding-event reading of the 10/30 anchor-time Synchformer run); gated judge = the existing G4 call when it fires, else row 1.
A: T_flam from gen_evidence_1030/flam_threshold.json (.2705) - the 10/30 gate already read it, so A gate decisions are recomputed and
compared; a changed decision would need a G5 call and is listed (none expected). V: caption-check gate, unchanged (no threshold).
Writes runs/obsval_1028/gen_row5_prereg_rows_1102.csv and gen_row5_prereg_table_1102.csv; the 10/30 files are not touched.
  python gepa_stage2/gen_row5_prereg_1102.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import json, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import gen_stage2_1030 as G
import obs_judge_1028 as O
import rep_scoring as RS

RULE = json.load(open((_tp.DATA + "/tools/synchformer_action_1030/PREREGISTERED_RULE.json")))
T_FLAM = json.load(open(G.EV / "flam_threshold.json"))["T_flam"]
assert abs(T_FLAM - 0.2705) < 1e-9, T_FLAM


def fire_prereg():
    pe = pd.concat(pd.read_csv(f) for s in ("220", "149") for f in sorted((G.SYNC / s).glob("per_event_shard*.csv")))
    pe["batch"] = pe["set"].astype(str) + "-" + pe["model"]
    ok = pe[pe.status == "ok"].assign(absoff=lambda t: t.offset.abs())
    best = ok.sort_values(["absoff", "prob"], ascending=False).drop_duplicates(["batch", "item_id"])
    src = {"220-LTX_2p3": "g220ltx", "220-MOVA": "g220mova", "149-LTX_2p3": "g149"}
    return {(src[r.batch], r.item_id): bool(r.absoff >= RULE["T"] - 1e-9 and r.prob >= RULE["P"] - 1e-9) for r in best.itertuples()}


def main():
    fire_new, fire_old = fire_prereg(), {k: v["main"] for k, v in G.sync_fire()[0].items()}
    g4rows = {r["uid"] for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == "G4" and r["cond"] == G.COND}
    bad = {u for u in g4rows if not (O.OUT / "calls" / G.COND / f"G4__{u}.json").exists()}
    out, a_changed = [], []
    for r in G.gt_rows():
        src, iid, ax, gt = r["source"], r["item_id"], r["axis"], r["gt"]
        if r["uid"] not in g4rows or r["uid"] in bad:
            continue
        anc = RS.row_label(O.anchor_df(src), iid, ax, gt)
        g4 = G.call_label("G4", r)
        d = dict(model=G.MODEL[src], set=G.SETN[src], uid=r["uid"], axis=ax, y="no" if "no" in gt.values() else "yes", row1=anc, row4=g4 or anc)
        if ax == "A":
            g5t, g4t = G.a_text(src, iid, gated=True), G.a_text(src, iid)
            d["row5_1030"] = anc if not g5t else (g4 if g5t == g4t else G.call_label("G5", r)) or anc
            d["row5_prereg"] = d["row5_1030"]           # same gate (T_flam .2705 in both); a changed decision would be listed below
            d["open_1030"] = d["open_prereg"] = bool(g5t)
            if g5t and g5t != g4t and not (O.OUT / "calls" / G.COND / f"G5__{r['uid']}.json").exists():
                a_changed.append(r["uid"])
        elif ax == "V":
            vc = G.vcheck(r["uid"]) or {}
            op = any(vc.get(e) == "contradicts" for e in gt)
            d["row5_1030"] = d["row5_prereg"] = (g4 or anc) if op else anc
            d["open_1030"] = d["open_prereg"] = op
        else:
            fo, fn = fire_old.get((src, iid), False), fire_new.get((src, iid), False)
            d["row5_1030"] = (g4 or anc) if fo else anc
            d["row5_prereg"] = (g4 or anc) if fn else anc
            d["rule_prereg"] = "no" if fn else anc
            d["open_1030"], d["open_prereg"] = fo, fn
        out.append(d)
    D = pd.DataFrame(out)
    D.to_csv(O.OUT / "gen_row5_prereg_rows_1102.csv", index=False)
    tab = []
    for (s, m, ax), g in D.groupby(["set", "model", "axis"]):
        for c in ("row1", "row4", "row5_1030", "row5_prereg", "rule_prereg"):
            if c not in g or g[c].isna().all():
                continue
            h = g[g[c].isin(["yes", "no"])]
            mt = RS.metrics(h.y, h[c])
            tab.append(dict(set=s, model=m, axis=ax, cond=c, n=mt["n"], n_fail=mt["n_fail"], acc=round(mt["acc"], 3), prec=mt["prec"], rec=mt["rec"],
                            open=int(g["open_prereg" if c in ("row5_prereg", "rule_prereg") else "open_1030"].sum()) if c.startswith(("row5", "rule")) else None,
                            changed_vs_1030=int((g[c] != g.row5_1030).sum()) if c in ("row5_prereg", "rule_prereg") else None))
    T = pd.DataFrame(tab)
    T.to_csv(O.OUT / "gen_row5_prereg_table_1102.csv", index=False)
    pd.set_option("display.width", 220)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("rule", RULE, "T_flam", T_FLAM, "| AVB items firing (pre-registered):", sorted(k for k, v in fire_new.items() if v),
          "| A rows needing a new G5 call:", a_changed, "| excluded (G4 failed):", sorted(bad))


if __name__ == "__main__":
    main()
