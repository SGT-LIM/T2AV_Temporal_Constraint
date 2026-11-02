#!/usr/bin/env python3
"""Evidence-condition agreement analysis (V axis, event level), same inputs as oracle_bound.py.

    python agreement_analysis.py --manifest manifests/test.jsonl --source hdepic \
        --run nocap="/projectnb/.../results/hdepic_medium_multi_baseline/shard*.csv" \
        --run cap="/projectnb/.../results/hdepic_medium_multi_tools_wf_avocado/shard*.csv" \
        [--run wf="/projectnb/.../results/hdepic_medium_multi_tools_wf/shard*.csv"] \
        [--out agree_events.csv]

Reports, event level:
  1. per-condition acc / PASS-R / FAIL-R
  2. agree vs disagree split: n, share, acc per condition, majority vote (odd #runs), oracle
  3. same split within GT PASS and GT FAIL
  4. pairwise: inside disagreements, who is right
  5. selective prediction: abstain on disagree -> coverage and acc on the covered part
  6. video level: all events correct, per condition, for agree-only videos vs any-disagree videos
"""
import argparse, csv, glob, json, sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)


def load_run(pattern):
    out = {}
    for f in sorted(glob.glob(pattern)):
        with open(f, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pe = r.get("visual_event_correctness_per_event") or ""
                if not pe.startswith("["):
                    continue
                try:
                    lst = json.loads(pe)
                except json.JSONDecodeError:
                    continue
                out[r["video_relpath"]] = {e["event_id"]: ("PASS" if e.get("label") == "yes" else "FAIL") for e in lst}
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--source", default="hdepic")
    ap.add_argument("--run", action="append", required=True, help="name=glob pattern")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    names, runs = [], {}
    for spec in a.run:
        n, p = spec.split("=", 1)
        names.append(n)
        runs[n] = load_run(p)
    items = [json.loads(l) for l in a.manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [it for it in items if it["source"] == a.source]
    print(f"manifest videos ({a.source}): {len(items)} | " + " | ".join(f"{n}: {len(runs[n])} videos" for n in names))

    rows, missing = [], 0
    for it in items:
        rp = it["relpath"]
        preds = {n: runs[n].get(rp) for n in names}
        if any(v is None for v in preds.values()):
            missing += 1
            continue
        for eid, gt in it["gt"].items():
            if any(eid not in preds[n] for n in names):
                continue
            r = {"relpath": rp, "eid": eid, "gt": gt}
            for n in names:
                r[n] = preds[n][eid]
                r[n + "_ok"] = float(preds[n][eid] == gt)
            labs = [preds[n][eid] for n in names]
            r["agree"] = len(set(labs)) == 1
            r["oracle"] = max(r[n + "_ok"] for n in names)
            if len(names) % 2 == 1:
                v = "PASS" if labs.count("PASS") > len(labs) / 2 else "FAIL"
                r["vote"], r["vote_ok"] = v, float(v == gt)
            rows.append(r)
    if missing:
        print(f"[WARN] {missing} manifest videos missing in at least one run")
    n_all = len(rows)
    n_fail = sum(r["gt"] == "FAIL" for r in rows)
    print(f"events: {n_all}  GT PASS {n_all - n_fail} / FAIL {n_fail}\n")

    has_vote = len(names) % 2 == 1
    cols = [n + "_ok" for n in names] + (["vote_ok"] if has_vote else []) + ["oracle"]
    hdr = " ".join(f"{c.replace('_ok',''):>8}" for c in cols)

    print("== per-condition (event level) ==")
    print(f"{'':12} {'n':>5} " + hdr + "   PASS-R / FAIL-R")
    for n in names:
        pr = mean([r[n + "_ok"] for r in rows if r["gt"] == "PASS"])
        fr = mean([r[n + "_ok"] for r in rows if r["gt"] == "FAIL"])
        print(f"{n:12} {n_all:5d} {mean([r[n+'_ok'] for r in rows]):8.3f}" + " " * (9 * (len(cols) - 1)) + f"   {pr:.3f} / {fr:.3f}")

    def block(title, sub):
        if not sub:
            print(f"{title:22} {0:5d}"); return
        print(f"{title:22} {len(sub):5d} ({len(sub)/n_all:5.1%}) " + " ".join(f"{mean([r[c] for r in sub]):8.3f}" for c in cols))

    print(f"\n== agree vs disagree ==\n{'subset':22} {'n':>5} {'share':>7} " + hdr)
    ag = [r for r in rows if r["agree"]]; dg = [r for r in rows if not r["agree"]]
    block("agree", ag); block("disagree", dg)
    for g in ("PASS", "FAIL"):
        block(f"gt={g} / agree", [r for r in ag if r["gt"] == g])
        block(f"gt={g} / disagree", [r for r in dg if r["gt"] == g])

    print("\n== pairwise: among events where x != y, who is right ==")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x, y = names[i], names[j]
            d = [r for r in rows if r[x] != r[y]]
            df = [r for r in d if r["gt"] == "FAIL"]
            print(f"  {x} vs {y}: n={len(d)}  {x} right {sum(r[x+'_ok']==1 for r in d)}  {y} right {sum(r[y+'_ok']==1 for r in d)}"
                  f"   | gt=FAIL n={len(df)}: {x} right {sum(r[x+'_ok']==1 for r in df)}, {y} right {sum(r[y+'_ok']==1 for r in df)}")

    print("\n== selective prediction: abstain on disagreement ==")
    best_full = max(mean([r[n + "_ok"] for r in rows]) for n in names)
    print(f"  coverage {len(ag)/n_all:.3f}  acc on covered {mean([r[names[0]+'_ok'] for r in ag]):.3f}  "
          f"(best single condition on full set {best_full:.3f})")
    if dg:
        print(f"  abstained {len(dg)}: GT FAIL share {sum(r['gt']=='FAIL' for r in dg)/len(dg):.3f} "
              f"(vs {n_fail/n_all:.3f} overall) -> disagreements are {'enriched' if sum(r['gt']=='FAIL' for r in dg)/len(dg) > n_fail/n_all else 'not enriched'} for FAIL")

    print("\n== video level (all GT events correct) ==")
    by_v = defaultdict(list)
    for r in rows:
        by_v[r["relpath"]].append(r)
    v_ag = [v for v in by_v.values() if all(r["agree"] for r in v)]
    v_dg = [v for v in by_v.values() if not all(r["agree"] for r in v)]
    print(f"{'subset':22} {'n':>5} " + hdr)
    for title, vs in (("all videos", list(by_v.values())), ("all-events-agree", v_ag), ("any-disagree", v_dg)):
        if not vs:
            continue
        print(f"{title:22} {len(vs):5d} " + " ".join(f"{mean([float(all(r[c]==1.0 for r in v)) for v in vs]):8.3f}" for c in cols))

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nwrote {a.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
