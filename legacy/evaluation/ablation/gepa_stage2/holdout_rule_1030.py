#!/usr/bin/env python3
"""P03-P09 HOLDOUT confirmation of the pre-registered AVB rule (10/30).

  python gepa_stage2/holdout_rule_1030.py rule     # code rule on the same-day holdout anchor; no judge calls
  python gepa_stage2/holdout_rule_1030.py rows     # set HO30 rows for the gated judge (synchformer_text only where the rule fires)
  python gepa_stage2/holdout_rule_1030.py score    # gated judge: fired rows take the judge's KEEP/REVISE verdict, others keep the anchor

Rule (PREREGISTERED_RULE.json, written 11:12 before any holdout result): AVB -> FAIL if the strongest binding-event Synchformer
reading (action-window mode) has |offset| >= T and p >= P, else keep the media-only anchor verdict.
GT: AVB shift_early / shift_late items = FAIL on every binding event; their originals = PASS (the variant construction).
Holdout criterion (pre-registered): broken originals <= round(0.05 * n originals with an anchor verdict).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import rep_scoring as RS

HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
ANC = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_holdout_p3p9_AVB_baseline_g36_1030")
SY = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030")
OUT = HERE / "runs/obsval_1028"
VAR = {"fail_audio_shift_early": "shift_early", "fail_audio_shift_late": "shift_late", "original": "original"}


def rows():
    import new_eval as NE
    items = json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))
    win = lambda x: (x["video_id"], tuple(x["clip"]))
    ws = {win(x) for x in items if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
    sel = [x for x in items if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late") or (x["variant"] == "original" and win(x) in ws)]
    pr = json.load(open(HO / "prompts_hdepic_p3p9.json"))
    metas = NE.build_item_meta_map(pr, modality_filter=None, item_overrides=None, relative_only=False)
    anc = RS.load([str(p) for p in sorted(ANC.glob("shard*.csv")) if not p.name.endswith("_per_event.csv")])
    out = []
    for x in sel:
        bind = [s["event_id"] for s in NE.build_scoring_events(metas[x["item_id"]]) if s.get("has_binding")]
        g = "yes" if x["variant"] == "original" else "no"
        gt = {e: g for e in bind}
        out.append(dict(uid=f"hdho|{x['item_id']}|AVB", item_id=x["item_id"], variant=VAR[x["variant"]], y=g, gt=gt,
                        participant=x["video_id"][:3], anchor=RS.row_label(anc, x["item_id"], "AVB", gt)))
    d = pd.DataFrame(out)
    pe = pd.concat(pd.read_csv(f) for f in sorted((SY / "holdout").glob("per_event_shard*.csv")))
    ok = pe[pe.status == "ok"].assign(absoff=lambda t: t.offset.abs())
    best = ok.sort_values(["absoff", "prob"], ascending=False).drop_duplicates("item_id").set_index("item_id")
    d = d.join(best[["offset", "absoff", "prob"]], on="item_id")
    return d, pe


def stage_rule(a):
    rule = json.load(open(SY / "PREREGISTERED_RULE.json"))
    T, P = rule["T"], rule["P"]
    d, pe = rows()
    print(f"pre-registered rule: T={T} s, P={P} (written {rule['written']}, holdout_results_seen={rule['holdout_results_seen']})")
    print(f"holdout rows {len(d)}; anchor verdict present {int(d.anchor.isin(['yes', 'no']).sum())}; Synchformer reading present "
          f"{int(d.absoff.notna().sum())}; per-event statuses {pe.status.value_counts().to_dict()}")
    d = d[d.anchor.isin(["yes", "no"])].copy()
    d["fire"] = (d.absoff >= T - 1e-9) & (d.prob >= P - 1e-9)
    d["rule"] = np.where(d.fire, "no", d.anchor)
    tab = []
    for v, g in d.groupby("variant"):
        ra, rb = g.anchor == g.y, g.rule == g.y
        tab.append(dict(variant=v, n=len(g), fired=int(g.fire.sum()), anchor_acc=round(ra.mean(), 3), rule_acc=round(rb.mean(), 3),
                        fixed=int((~ra & rb).sum()), broken=int((ra & ~rb).sum()),
                        FA_anchor=round((g.anchor == "no").mean(), 3) if v == "original" else None,
                        FA_rule=round((g.rule == "no").mean(), 3) if v == "original" else None))
    t = pd.DataFrame(tab)
    print(t.to_string(index=False))
    o = d[d.variant == "original"]
    broken = int(((o.anchor == o.y) & (o.rule != o.y)).sum())
    allowed = int(round(0.05 * len(o)))
    print(f"\nHOLDOUT CRITERION: broken originals {broken} vs allowed {allowed} of {len(o)} -> {'PASS' if broken <= allowed else 'FAIL'}")
    per = d.groupby(["participant", "variant"]).apply(lambda g: pd.Series(dict(n=len(g), fixed=int(((g.anchor != g.y) & (g.rule == g.y)).sum()),
                                                                               broken=int(((g.anchor == g.y) & (g.rule != g.y)).sum())))).unstack()
    print("\nper participant:\n" + per.to_string())
    d.to_csv(OUT / "holdout_rule_rows_1030.csv", index=False)
    t.to_csv(OUT / "holdout_rule_table_1030.csv", index=False)
    json.dump(dict(T=T, P=P, broken_orig=broken, allowed=allowed, n_orig=int(len(o)), passed=broken <= allowed, table=tab),
              open(OUT / "holdout_rule_result_1030.json", "w"), indent=1)


def stage_rows(a):
    """HO30 rows for the gated judge: only rows where the rule fires; synchformer_text with all binding-event readings."""
    sys.path.insert(0, str(HERE))
    import obs_judge_1028 as O
    d = pd.read_csv(OUT / "holdout_rule_rows_1030.csv")
    pe = pd.concat(pd.read_csv(f) for f in sorted((SY / "holdout").glob("per_event_shard*.csv")))
    pr = {x["item_id"]: x for x in json.load(open(HO / "prompts_hdepic_p3p9.json"))}
    allrows = [r for r in O.jl(O.OUT / "rows.jsonl") if r["set"] != "HO30"]
    new = []
    for r in d[d.fire].itertuples():
        snd = [e for e in pr[r.item_id]["events"] if e.get("modality") == "sounding_action"]
        multi = len(snd) > 1
        lines = []
        for e in snd:
            x = pe[(pe.item_id == r.item_id) & (pe.label == e["action"])]
            pre = f"'{e['action']}': " if multi else ""
            if not len(x) or pd.isna(x.offset.iloc[0]):
                lines.append(f"{pre}Synchformer, window around the action: no reading")
            else:
                x = x.iloc[0]
                lines.append(f"{pre}Synchformer, window around the action: most likely offset {float(x.offset):+.1f} s (positive = audio later "
                             f"than video), probability {float(x.prob):.2f}; probability of zero offset {float(x.p_offset0):.2f}")
        gt = json.loads(r.gt.replace("'", '"')) if isinstance(r.gt, str) else r.gt
        base = dict(set="HO30", source="hdho", uid=r.uid, item_id=r.item_id, axis="AVB", variant=r.variant, gt=gt, clip=r.item_id)
        new += [{**base, "cond": "anchor"}, {**base, "cond": "synchformer_text", "obs": {"text": "Observation (tool output):\n" + "\n".join(lines)}}]
    O.wjl(O.OUT / "rows.jsonl", allrows + new)
    print(f"HO30 gated-judge rows: {len(new) // 2} (rule fired)")


def stage_score(a):
    d = pd.read_csv(OUT / "holdout_rule_rows_1030.csv")
    calls = {}
    for f in (OUT / "calls/synchformer_text").glob("HO30__*.json"):
        rec = json.load(open(f))
        calls[rec["uid"]] = rec
    sys.path.insert(0, str(HERE))
    import obs_judge_1028 as O
    lab = []
    for r in d.itertuples():
        if not r.fire:
            lab.append(r.anchor)
            continue
        rec = calls.get(r.uid)
        gt = json.loads(r.gt.replace("'", '"'))
        lab.append(O.obs_label(rec, "AVB", gt) if rec and rec["status"] == "ok" else "")
    d["judge"] = lab
    tab = []
    for v, g in d.groupby("variant"):
        g = g[g.judge.isin(["yes", "no"])]
        ra, rj, rr = g.anchor == g.y, g.judge == g.y, g.rule == g.y
        tab.append(dict(variant=v, n=len(g), fired=int(g.fire.sum()), anchor_acc=round(ra.mean(), 3), rule_acc=round(rr.mean(), 3),
                        judge_acc=round(rj.mean(), 3), judge_fixed=int((~ra & rj).sum()), judge_broken=int((ra & ~rj).sum()),
                        judge_vs_rule_differ=int((g.judge != g.rule).sum()),
                        FA_judge=round((g.judge == "no").mean(), 3) if v == "original" else None))
    print(pd.DataFrame(tab).to_string(index=False))
    d.to_csv(OUT / "holdout_rule_rows_judge_1030.csv", index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["rule", "rows", "score"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
