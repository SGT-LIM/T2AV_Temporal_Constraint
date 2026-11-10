#!/usr/bin/env python3
"""TC / TR prerequisite scope in the reported runs (cached outputs only; writes $T2AV_OUT_DIR/<tag>).

Counts, per dataset, the TC events and TR videos that were scored (media-only, condition row1) although ANOTHER event of the same
item failed its A or V (in GT, or in the media-only judge output), and checks that no scored TR video has any event failing.
For examples it reads the raw media-only run row (agentic harness output) to show the target event's count entry and the other event's
A / V labels.
  python repro/avt_gate/audit/tc_tr_prereq.py --tag tc_tr_prereq
"""
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "evaluation/ablation/gepa_stage2"), str(REPO / "evaluation/ablation")]
sys.path.append(str(REPO))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="tc_tr_prereq"); a = ap.parse_args()
    import t2av_paths as tp
    out = tp.out_dir(a.tag)
    if out.exists():
        sys.exit(f"{out} exists")
    out.mkdir(parents=True)
    import pandas as pd
    import final_benchmark_1108 as FB
    A = pd.read_csv(FB.OUT / "units_all_conditions.csv", low_memory=False)
    r1 = A[A.cond == "row1"].copy()
    av = r1[r1.axis.isin(["A", "V"])]
    gt_fail = av[av.gt_y == "no"].groupby(["dataset", "item"]).event.apply(set).to_dict()
    judge_fail = av[(av.status == "scored") & (av.pred == "no")].groupby(["dataset", "item"]).event.apply(set).to_dict()
    grp = {"220 LTX": "LTX", "149 LTX": "LTX", "2k_25 LTX": "LTX", "220 MOVA": "MOVA", "MOVA390": "MOVA", "P03-P09": "P03-P09"}
    rows, ex = [], []
    tc = r1[(r1.axis == "TCC") & (r1.status == "scored")]
    for r in tc.itertuples():
        k = (r.dataset, r.item); ev = r.event
        og = sorted(gt_fail.get(k, set()) - {ev}); oj = sorted(judge_fail.get(k, set()) - {ev})
        rows.append(dict(dataset=r.dataset, group=grp[r.dataset], axis="TCC", unit=r.unit, item=r.item, event=ev, gt=r.gt_y, pred=r.pred,
                         other_event_gt_AV_fail=";".join(og), other_event_judge_AV_fail=";".join(oj)))
    tr = r1[(r1.axis == "TCR") & (r1.status == "scored")]
    for r in tr.itertuples():
        k = (r.dataset, r.item)
        rows.append(dict(dataset=r.dataset, group=grp[r.dataset], axis="TCR", unit=r.unit, item=r.item, event="video", gt=r.gt_y, pred=r.pred,
                         other_event_gt_AV_fail=";".join(sorted(gt_fail.get(k, set()))), other_event_judge_AV_fail=";".join(sorted(judge_fail.get(k, set())))))
    R = pd.DataFrame(rows); R.to_csv(out / "scored_tc_tr_units.csv", index=False)
    S = R.groupby(["group", "dataset", "axis"]).apply(lambda q: pd.Series(dict(scored=len(q), with_other_event_GT_AV_fail=int((q.other_event_gt_AV_fail != "").sum()),
                                                                                with_other_event_judge_AV_fail=int((q.other_event_judge_AV_fail != "").sum())))).reset_index()
    S.to_csv(out / "summary.csv", index=False)
    # excluded TR videos: reasons (any event failing excludes the whole video)
    trx = r1[(r1.axis == "TCR") & (r1.status != "scored") & r1.gt_elig.astype(bool)].groupby(["dataset", "reason"]).size().rename("units").reset_index()
    trx.to_csv(out / "tr_excluded_reasons.csv", index=False)
    tcx = r1[(r1.axis == "TCC") & (r1.status != "scored") & r1.gt_elig.astype(bool)].groupby(["dataset", "reason"]).size().rename("units").reset_index()
    tcx.to_csv(out / "tc_excluded_reasons.csv", index=False)
    # examples: raw media-only harness row (target event count entry; other events' A / V labels)
    import audit_1106 as AU
    D = AU.datasets()
    try:
        import final_cov_1108 as FC
        ds390, _, _ = FC.mova390_ds(); D["MOVA390"] = ds390
    except Exception:
        pass
    raw = {}
    for name in D:
        run = D[name]["r1"]; raw[name] = run
    for g in ("LTX", "MOVA"):
        q = R[(R.group == g) & (R.axis == "TCC") & (R.other_event_judge_AV_fail != "") & (R.other_event_gt_AV_fail != "")]
        for r in q.head(3).itertuples():
            ent = raw.get(r.dataset, {}).get(r.item, {})
            ex.append(dict(group=g, dataset=r.dataset, item=r.item, target_event=r.event, gt_TC=r.gt, media_only_TC=r.pred,
                           target_event_judge_A=str(ent.get("A", {}).get(r.event)), target_event_judge_V=str(ent.get("V", {}).get(r.event)),
                           target_event_judge_TCC=str(ent.get("TCC", {}).get(r.event)),
                           other_events_GT_AV_fail=r.other_event_gt_AV_fail, other_events_judge_A=str({e: ent.get("A", {}).get(e) for e in r.other_event_judge_AV_fail.split(";")}),
                           other_events_judge_V=str({e: ent.get("V", {}).get(e) for e in r.other_event_judge_AV_fail.split(";")})))
    pd.DataFrame(ex).to_csv(out / "examples.csv", index=False)
    json.dump(dict(summary=S.to_dict("records"), tr_scored_with_any_failing_event=int(((R.axis == "TCR") & ((R.other_event_gt_AV_fail != "") | (R.other_event_judge_AV_fail != ""))).sum())),
              open(out / "summary.json", "w"), indent=1, default=str)
    print(S.to_string(index=False)); print("TR scored with any failing event:", int(((R.axis == "TCR") & ((R.other_event_gt_AV_fail != "") | (R.other_event_judge_AV_fail != ""))).sum()))
    print(pd.DataFrame(ex).to_string(index=False)[:3000])


if __name__ == "__main__":
    main()
