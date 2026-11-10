#!/usr/bin/env python3
"""AVB scoring fix (11/08), applied identically to every condition; no API / GPU calls; original files and reports untouched.
Problem: audit_1106.load_run marks a per-event AVB entry 'gated' (excluded) whenever its free-text reason matches rep_scoring.SKIP_RE
(precondition | not evaluable | not evaluated | skipped). Model-written reasons such as "Audio-Visual Binding is not evaluable" then
override an explicit AVB PASS / FAIL label even when the structured A / V prerequisites of that event are satisfied.
Fix (AVB only, row 1 and row 2 runs, all datasets): an AVB entry stays 'gated' only if its reason is the pipeline's precondition message
("Binding not evaluated. [Precondition failed ...") or the run's own A or V label of the event is not an ok PASS. If the event has an
explicit AVB label yes / no and A and V of the event are ok PASS, a SKIP_RE match in model text no longer excludes it. Fills ('treated
as failure'), missing entries and run errors are unchanged. Always shown / gated (stage-2 records) never used the AVB reason text and are
unchanged by construction; their judge prerequisites (A / V of row 1) are unchanged. Gate rules frozen.
Output: runs/obsval_1028/avb_skipfix_1108/ (corrected AVB units for all conditions, before / after exclusion counts and metrics).
  python gepa_stage2/avb_skipfix_1108.py
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
RUNS = HERE / "runs/obsval_1028"; OUT = RUNS / "avb_skipfix_1108"
PIPE_MSG = "Binding not evaluated. [Precondition failed"
FIXED = []


def patch():
    import audit_1106 as AU, rep_scoring as RS
    orig = AU.load_run

    def load_run_fixed(files):
        out = orig(files)
        fs = [f for f in files if "per_event" not in f]
        if not fs:
            return out
        d = pd.concat(pd.read_csv(f) for f in fs).drop_duplicates("item_id", keep="last")
        for r in d.to_dict("records"):
            ent = out.get(r["item_id"])
            if ent is None or ent["error"]:
                continue
            try:
                per = json.loads(r.get("audio_visual_binding_per_event") or "[]")
            except Exception:
                continue
            for e in per:
                eid = e.get("event_id"); rs = str(e.get("reason", "")); lab = str(e.get("label", "")).lower()
                if eid not in ent["AVB"] or ent["AVB"][eid][1] != "gated" or PIPE_MSG in rs:
                    continue
                if lab in ("yes", "no") and ent["A"].get(eid) == ("yes", "ok") and ent["V"].get(eid) == ("yes", "ok"):
                    ent["AVB"][eid] = (lab, "ok")
                    FIXED.append(dict(run=str(Path(fs[0]).parent.name), item=r["item_id"], event=eid, label=lab, reason=rs[:200]))
        return out
    AU.load_run = load_run_fixed
    return AU


def metrics(y, p):
    import bidir_full_1107 as BF
    return BF.metrics(y, p)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    AU = patch()
    import section6_1106 as S6
    D = AU.datasets()
    new = pd.DataFrame(S6.avb_events(D)); new["group"] = new.dataset
    new.to_csv(OUT / "avb_units_all_conditions_fixed.csv", index=False)
    pd.DataFrame(FIXED).drop_duplicates().to_csv(OUT / "restored_avb_entries.csv", index=False)
    old = pd.read_csv(RUNS / "section6_1106/units_all.csv", low_memory=False); old = old[(old.group == old.dataset) & (old.axis == "AVB")]
    cnt = []
    for nm, T in (("before (units_all)", old), ("after (fixed)", new)):
        for (d, c), q in T.groupby(["dataset", "cond"]):
            cnt.append(dict(version=nm, dataset=d, cond=c, gt_eligible=int(q.gt_elig.astype(bool).sum()), scored=int((q.status == "scored").sum()),
                            excluded_judge_prereq=int(q.reason.fillna("").str.contains("judge prereq").sum())))
    C = pd.DataFrame(cnt); C.to_csv(OUT / "exclusion_counts_before_after.csv", index=False)
    # metrics on the four-condition common subset (media only, one call, always shown, original gate), before and after
    COND = {"row1": "media only", "row2": "one call plus tools", "row4": "always shown", "row5": "original paper gate"}
    rows = []
    groups = {d: [d] for d in new.dataset.unique()}; groups["LTX (220 + 149 + 2k_25)"] = ["220 LTX", "149 LTX", "2k_25 LTX"]
    for nm, T in (("before", old), ("after", new)):
        piv = {c: T[(T.cond == c)].set_index(["dataset", "unit"]) for c in COND}
        for g, dss in groups.items():
            base = piv["row1"]; keys = [k for k in base.index if k[0] in dss]
            sc = {c: {k for k in keys if piv[c].status.get(k) == "scored"} for c in COND}
            common = sorted(set.intersection(*sc.values()))
            for scope, ks, conds in (("four-condition common subset", common, list(COND)),
                                     ("media / always shown / original gate common subset (one call excluded)", sorted(sc["row1"] & sc["row4"] & sc["row5"]), ["row1", "row4", "row5"])):
                for c in conds:
                    y = [piv[c].gt_y.get(k) for k in ks]; p = [piv[c].pred.get(k) for k in ks]
                    m = metrics(y, p)
                    rows.append(dict(version=nm, group=g, scope=scope, condition=COND[c], units=len(ks), scored_row1=len(sc["row1"]), scored_row2=len(sc["row2"]),
                                     acc=m.get("acc"), macro_F1=m.get("macro_F1"), bal_acc=m.get("bal_acc"), FAIL_R=m.get("FAIL_R"), FA=m.get("FA"), FA_count=m.get("FA_count")))
    R = pd.DataFrame(rows); R.to_csv(OUT / "metrics_before_after.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(len(pd.DataFrame(FIXED).drop_duplicates()), "AVB entries restored")
    print(C.pivot_table(index=["dataset", "cond"], columns="version", values="scored").to_string())
    print(R[R.scope.str.startswith("four")].to_string(index=False))


if __name__ == "__main__":
    main()
