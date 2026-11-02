#!/usr/bin/env python3
"""HD-EPIC axis x variant matrix from the FULL existing runs (all 1,523 items, no API calls).
For each axis: which variants are positive (GT PASS) and which are the negative perturbation (GT FAIL) by design;
prints fraction judged FAIL per variant per run, plus acc / prec / rec / FAR per axis.

  python gepa_stage2/variant_matrix.py --runs \
      video=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_baseline \
      wf=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_tools_wf \
      wf_cap=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_tools_wf_avocado \
      two_stage=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_two_stage
Variant is parsed from item_id suffix (_pass, _A, _mute, _AVBearly, _AVBlate, _TCC, _TCR, _Vhand, _Vnoun).
GT by design (hierarchy-aware): own perturbation -> FAIL; variants that do not touch the axis -> PASS;
variants that break a parent axis -> skipped (precondition), shown as 'n/a'."""
import argparse, glob, json, re, sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import AXIS_FULL
from eval_rules import oneshot_labels

VAR_RE = re.compile(r"_(pass|A|mute|AVBearly|AVBlate|TCC|TCR|Vhand|Vnoun)$")
NAME = {"pass": "original", "A": "absent_sound", "mute": "mute", "AVBearly": "shift_early", "AVBlate": "shift_late",
        "TCC": "count_off", "TCR": "order_swap", "Vhand": "hand_swap", "Vnoun": "noun_swap"}
# GT by design per axis: FAIL variants, PASS variants, everything else = n/a (parent axis broken)
GT = {
    "A":   dict(fail={"absent_sound", "mute"}, pas={"original", "shift_early", "shift_late", "count_off", "order_swap", "hand_swap", "noun_swap"}),
    "V":   dict(fail={"hand_swap", "noun_swap"}, pas={"original", "absent_sound", "mute", "shift_early", "shift_late", "count_off", "order_swap"}),
    "AVB": dict(fail={"shift_early", "shift_late"}, pas={"original", "count_off", "order_swap"}),
    "TCR": dict(fail={"order_swap"}, pas={"original", "shift_early", "shift_late", "count_off"}),
    "TCC": dict(fail={"count_off"}, pas={"original", "shift_early", "shift_late", "order_swap"}),
}
ORDER = ["original", "absent_sound", "mute", "shift_early", "shift_late", "count_off", "order_swap", "hand_swap", "noun_swap"]


def load_items(run):
    fs = sorted(glob.glob(f"{run}/shard?.csv")) or [f"{run}/all.csv"]
    df = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last")
    return df.item_id.tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="tag=dir ...")
    a = ap.parse_args()
    runs = dict(r.split("=", 1) for r in a.runs)
    items = sorted(set().union(*[load_items(d) for d in runs.values()]))
    rows = []
    for ax, axf in AXIS_FULL.items():
        luts = {tag: oneshot_labels(d, axf) for tag, d in runs.items()}
        for iid in items:
            m = VAR_RE.search(iid)
            if not m:
                continue
            var = NAME[m.group(1)]
            gt = "no" if var in GT[ax]["fail"] else ("yes" if var in GT[ax]["pas"] else None)
            if gt is None:
                continue
            rec = dict(axis=ax, variant=var, gt=gt, item=iid)
            for tag, lut in luts.items():
                rec[tag] = lut.get((iid, "__item__"), "")      # item-level axis label; "" = skipped / missing
            rows.append(rec)
    df = pd.DataFrame(rows)
    tags = list(runs)
    pd.set_option("display.width", 250)

    print("== fraction judged FAIL per axis x variant  (GT FAIL rows -> recall, GT PASS rows -> false alarm).  n = items with a label in that run")
    for ax in AXIS_FULL:
        d = df[df.axis == ax]
        print(f"\n-- {ax}")
        lines = []
        for var in ORDER:
            g = d[d.variant == var]
            if not len(g):
                continue
            line = dict(variant=var, gt=g["gt"].iloc[0], n=len(g))
            for t in tags:
                gg = g[g[t].isin(["yes", "no"])]
                line[t] = f"{(gg[t] == 'no').mean():.2f} ({len(gg)})" if len(gg) else "-"
            lines.append(line)
        print(pd.DataFrame(lines).to_string(index=False))

    print("\n\n== per axis, FAIL positive, over all labeled rows: acc | prec | rec | FAR  [n, n FAIL]")
    for ax in AXIS_FULL:
        d = df[df.axis == ax]
        out = []
        for t in tags:
            g = d[d[t].isin(["yes", "no"])]
            y, p = g["gt"] == "no", g[t] == "no"
            tp, fp, fn, tn = (y & p).sum(), (~y & p).sum(), (y & ~p).sum(), (~y & ~p).sum()
            acc = (tp + tn) / len(g) if len(g) else float("nan")
            prec = tp / (tp + fp) if tp + fp else float("nan"); rec = tp / (tp + fn) if tp + fn else float("nan")
            far = fp / (fp + tn) if fp + tn else float("nan")
            out.append(f"{t} {acc:.2f}/{prec:.2f}/{rec:.2f}/{far:.2f} [{len(g)},{int(y.sum())}]")
        print(f"{ax:4s} " + "   ".join(out))
    df.to_csv("gepa_stage2/runs/variant_matrix.csv", index=False)
    print("\n-> gepa_stage2/runs/variant_matrix.csv")


if __name__ == "__main__":
    main()
