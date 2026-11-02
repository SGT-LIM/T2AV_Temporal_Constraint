#!/usr/bin/env python3
"""AVB human-FAIL rows on the generated sets: Synchformer readings and the material for a failure-type reading (10/30). No calls.

Rows: AVB GT-FAIL rows with a row 1 anchor verdict under the stage1_lookup rule (149: 51; 220-MOVA: 5; 220-LTX: 1).
Per row, over the GT-'no' binding events: the reading with the largest |offset| (ties: higher p) from synchformer_gen_1030
(anchor-time window), whether it passes the labeled rule (|offset| >= 1.8 s and p >= .25), the row 1 anchor's A / V / AVB per-event
labels and reasons, and (149 only) each rater's AVB / A / V label and rationale for the event.
  python gepa_stage2/avb_failure_types_1030.py   -> runs/obsval_1028/avb_failure_rows_1030.csv, prints a 10-row sample (149) + all 220
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import obs_judge_1028 as O
import rep_scoring as RS

SYNC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_gen_1030")
ANN = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/raw/prolific_ltx_2k_50/annotations")
RULE = json.load(open("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030/PREREGISTERED_RULE.json"))


def raters_149():
    by = {}
    for f in sorted(ANN.glob("*.json")):
        a = json.load(open(f))["annotations"]
        ids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(a["events"])}
        for eid, r in a["responses"]["events"].items():
            by.setdefault((a["item_id"], ids.get(eid, eid)), []).append(
                {ax: (r.get(ax, {}).get("label"), (r.get(ax, {}).get("rationale") or "").strip()) for ax in ("a", "v", "avb")})
    return by


def per_event(src, iid):
    df = O.anchor_df(src)
    r = df.loc[iid]
    out = {}
    for ax, col in (("A", "audio_event_correctness"), ("V", "visual_event_correctness"), ("AVB", "audio_visual_binding")):
        try:
            for e in json.loads(r[col + "_per_event"]):
                out.setdefault(e["event_id"], {})[ax] = (e.get("label"), str(e.get("reason", "")).strip())
        except Exception:
            pass
    return out


def main():
    pe = pd.concat(pd.read_csv(f) for s in ("220", "149") for f in sorted((SYNC / s).glob("per_event_shard*.csv")))
    pe["absoff"] = pe.offset.abs()
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{s}.jsonl")]
    gts = [("g220ltx", "220", "LTX_2p3", m) for m in man if m["source"] == "ltx" and m["axis"] == "AVB"]
    gts += [("g220mova", "220", "MOVA", m) for m in man if m["source"] == "mova" and m["axis"] == "AVB"]
    gts += [("g149", "149", "LTX_2p3", json.loads(l)) for l in open("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030/gt_gen149.jsonl")
            if json.loads(l)["axis"] == "AVB"]
    R = raters_149()
    rows = []
    for src, s, model, m in gts:
        if "no" not in m["gt"].values():
            continue
        anc = RS.row_label(O.anchor_df(src), m["item_id"], "AVB", m["gt"])
        if anc not in ("yes", "no"):
            continue
        fail_ev = [e for e, v in m["gt"].items() if v == "no"]
        g = pe[(pe["set"].astype(str) == s) & (pe.model == model) & (pe.item_id == m["item_id"]) & pe.event_id.isin(fail_ev)]
        g = g[g.status == "ok"].sort_values(["absoff", "prob"], ascending=False)
        w = g.iloc[0] if len(g) else None
        ev = per_event(src, m["item_id"])
        rows.append(dict(set=s, model=model, item_id=m["item_id"], anchor=anc, fail_events=",".join(fail_ev),
                         offset=None if w is None else w.offset, absoff=None if w is None else w.absoff, prob=None if w is None else w.prob,
                         p_offset0=None if w is None else w.p_offset0, span_source=None if w is None else w.span_source,
                         passes_rule=bool(w is not None and w.absoff >= RULE["T"] - 1e-9 and w.prob >= RULE["P"] - 1e-9),
                         anchor_events=json.dumps({e: ev.get(e, {}) for e in fail_ev}),
                         raters=json.dumps({e: R.get((m["item_id"], e), []) for e in fail_ev}) if s == "149" else ""))
    D = pd.DataFrame(rows)
    D.to_csv(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028/avb_failure_rows_1030.csv", index=False)
    for (s, model), g in D.groupby(["set", "model"]):
        print(f"\n== {s} {model}: {len(g)} GT-FAIL AVB rows with an anchor verdict; anchor says FAIL on {int((g.anchor == 'no').sum())}")
        print(f"   |offset| quantiles .5/.75/.9/max: {g.absoff.quantile([.5, .75, .9]).round(2).tolist()} / {g.absoff.max()}; "
              f"share 0: {(g.absoff == 0).mean():.2f}; p quantiles .25/.5/.75: {g.prob.quantile([.25, .5, .75]).round(2).tolist()}")
        print(f"   pass labeled rule ({RULE['T']} s / {RULE['P']}): {int(g.passes_rule.sum())}; offset values: "
              f"{g.offset.value_counts().sort_index().to_dict()}")
    show = pd.concat([D[D["set"] == "149"].sample(10, random_state=1030), D[D["set"] == "220"]])
    for r in show.itertuples():
        print("\n" + "=" * 110 + f"\n{r.set} {r.model} {r.item_id} | anchor AVB {r.anchor} | sync offset {r.offset} p {r.prob} p0 {r.p_offset0} ({r.span_source})")
        for e, d in json.loads(r.anchor_events).items():
            for ax in ("A", "V", "AVB"):
                if ax in d:
                    print(f"  anchor {e} {ax}: {d[ax][0]} | {d[ax][1][:260]}")
            if r.raters:
                for k, x in enumerate(json.loads(r.raters).get(e, [])):
                    print(f"  rater{k} {e}: A {x['a'][0]} V {x['v'][0]} AVB {x['avb'][0]}" +
                          "".join(f" | {ax} rationale: {x[ax][1][:200]}" for ax in ("avb", "a", "v") if x[ax][1]))


if __name__ == "__main__":
    main()
