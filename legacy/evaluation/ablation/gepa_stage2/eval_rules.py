#!/usr/bin/env python3
"""Held-out evaluation of rule blocks (seed vs GEPA best), same metrics as status/two_stage_results_2026-10-19.md.

Stage 2 (unchanged):
  python gepa_stage2/eval_rules.py --sources gepa_stage2/sources.json --manifest gepa_stage2/manifests/test.jsonl \
      --rules seed=gepa_stage2/runs/s0/seed_candidate.txt best=gepa_stage2/runs/s0/best_candidate.txt \
      --run-dir gepa_stage2/runs/s0 [--oneshot gepa_stage2/oneshot.json] [--workers 4]
Stage 1 (10/21; one axis per call, `default` = the axis module's own rules, i.e. the seed):
  python gepa_stage2/eval_rules.py --stage1 video --axis A --sources ... --manifest gepa_stage2/manifests/test.jsonl \
      --rules seed=default best=gepa_stage2/runs/s1video_A/best_candidate.txt --run-dir gepa_stage2/runs/s1video_A \
      --seed-run from-sources        # reference column = the existing video-only run (no re-run of seed needed)
  for --stage1 tools use --oneshot gepa_stage2/oneshot.json as the reference instead (and --seed-run from-oneshot).

Writes run_dir/heldout_test_<tag>.csv (one row per event) and prints:
  HD-EPIC : per axis x variant, item-level rate judged FAIL ("no")  -> detection for broken variants, false alarm for originals
  220     : per model x axis, event-level accuracy (plain, not balanced) and item-level accuracy
  columns : video-only (existing run) | one-shot (if given) | seed_run (if given) | each rules tag ; diff last - ref, paired bootstrap 95% CI
Also: how often the judged label differs from the existing video-only run, and whether the difference was right, per tag.
oneshot.json = {"hdepic": <results dir or all.csv>, "ltx": <csv>, "mova": <csv>}  (the W+F+caption one-shot runs).
"""
import argparse, json, re, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import Stage2Adapter, AXIS_FULL
import adapter as S2
import run_two_stage as TS

PRE = re.compile(r"precondition|not evaluable|not evaluated", re.I)
FAIL_VARIANTS = {"absent_sound", "hand_swap", "noun_swap", "audio_shift_early", "audio_shift_late", "order_swap", "count_off"}


def run_tag(adapter, component, rows, rules, tag, run_dir):
    out = Path(run_dir) / f"heldout_test_{tag}.csv"
    eb = adapter.evaluate(rows, {component: rules}, capture_traces=True)
    recs = []
    for row, rec in zip(rows, eb.outputs):
        o = rec["out"]
        for e, (p, g) in rec["per"].items():
            if e == "__item__" and "__item__" not in o["stage1"]:          # item-level GT: aggregate the stage-1 event labels
                l1 = [l for l in o["stage1"].values() if l in ("yes", "no")]
                s1 = "no" if "no" in l1 else ("yes" if l1 else "")
            else:
                s1 = o["stage1"].get(e, "")
            recs.append(dict(uid=row["uid"], source=row["source"], item_id=row["item_id"], axis=row["axis"], variant=row["variant"],
                             eval_only=row["eval_only"], event_id=e, gt=g, stage1=s1, pred=p, tag=tag))
    df = pd.DataFrame(recs); df.to_csv(out, index=False)
    print(f"[{tag}] {len(rows)} rows / {len(df)} events -> {out}", flush=True)
    return df


def oneshot_labels(path, axis_full):
    """(item_id, event_id) -> label from a one-shot run (dir with shard?.csv / all.csv, or a csv)."""
    import glob
    fs = [path] if path.endswith(".csv") else (sorted(glob.glob(f"{path}/shard?.csv")) or [f"{path}/all.csv"])
    df = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last")
    lut = {}
    for _, r in df.iterrows():
        lab = str(r.get(axis_full, "")).lower()
        if lab in ("yes", "no") and not PRE.search(str(r.get(axis_full + "_reason", ""))):
            lut[(r.item_id, "__item__")] = lab                # item-level (TCR, and item-level GT rows of any axis)
        try:
            for pe in json.loads(r[f"{axis_full}_per_event"]):
                if PRE.search(str(pe.get("reason", ""))):
                    continue
                if "label" in pe:
                    lut[(r.item_id, pe["event_id"])] = str(pe["label"]).lower()
        except Exception:
            pass
    return lut


def fill_from_runs(base, col, cfg):
    """cfg = {source: run dir or csv}; fills base[col] with that run's labels."""
    base[col] = ""
    for src, path in cfg.items():
        for ax, axf in AXIS_FULL.items():
            m = (base.source == src) & (base.axis == ax)
            if not m.any():
                continue
            lut = oneshot_labels(path, axf)
            base.loc[m, col] = [lut.get((i, e), lut.get((i, "__item__"), "")) for i, e in zip(base[m].item_id, base[m].event_id)]
    miss = (base[col] == "").sum()
    print(f"[{col}] labels found for {len(base) - miss}/{len(base)} events (missing = gated out or absent in that run)")


def item_table(df, col):
    """item-level label: 'no' if any judged event is 'no'. Returns per uid: judged_no (bool), correct (bool)."""
    g = df.groupby("uid")
    item_pred = g[col].apply(lambda s: "no" if (s == "no").any() else "yes")
    item_gt = g["gt"].apply(lambda s: "no" if (s == "no").any() else "yes")
    meta = g[["source", "axis", "variant", "eval_only"]].first()
    t = meta.assign(pred=item_pred, gt=item_gt)
    t["no"] = t.pred == "no"; t["ok"] = t.pred == t["gt"]
    return t


def boot_ci(a, b, n=5000, seed=0):
    """paired bootstrap of mean(b) - mean(a) over items."""
    rng = np.random.default_rng(seed); a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) == 0:
        return np.nan, (np.nan, np.nan)
    idx = rng.integers(0, len(a), (n, len(a)))
    d = (b[idx] - a[idx]).mean(1)
    return float((b - a).mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True); ap.add_argument("--manifest", required=True)
    ap.add_argument("--rules", nargs="+", required=True, help="tag=path ...  (first = reference for diffs, e.g. seed); stage 1: tag=default = axis module rules")
    ap.add_argument("--run-dir", required=True); ap.add_argument("--oneshot", default=None)
    ap.add_argument("--extra-heldout", nargs="*", default=[], help="tag=csv ... other heldout_test_*.csv (e.g. the orchestrator) to add as columns")
    ap.add_argument("--seed-run", default=None, help="json {source: run dir or csv} of an EXISTING run with the seed rules -> column seed_run, "
                                                     "reference for the diff. Stage 1: 'from-sources' (video-only run in sources.json) or 'from-oneshot'")
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--judge-model", default="gemini-3.1-pro-preview")
    ap.add_argument("--stage1", choices=["video", "tools"], default=None); ap.add_argument("--axis", default=None)
    a = ap.parse_args()
    if a.stage1 and not a.axis:
        sys.exit("--stage1 needs --axis")

    rows = [json.loads(l) for l in open(a.manifest)]
    if a.axis:
        rows = [r for r in rows if r["axis"] == a.axis]
    sources = json.load(open(a.sources))
    log = lambda s: print(s, flush=True)
    if a.stage1:
        from stage1_adapter import Stage1Adapter, COMPONENT
        adapter = Stage1Adapter(sources, a.run_dir, axis=a.axis, mode=a.stage1, model=a.judge_model, workers=a.workers,
                                max_chars=10 ** 6, log=log)
    else:
        COMPONENT = S2.COMPONENT
        adapter = Stage2Adapter(sources, a.run_dir, model=a.judge_model, workers=a.workers, max_chars=10 ** 6, log=log)
    tags = [t.split("=", 1) for t in a.rules]
    rules_text = lambda p: adapter.seed_rules if (p == "default" and a.stage1) else Path(p).read_text()
    dfs = {tag: run_tag(adapter, COMPONENT, rows, rules_text(p), tag, a.run_dir) for tag, p in tags}
    ref = tags[0][0]
    base = dfs[ref].copy()
    if a.seed_run:
        if a.seed_run == "from-sources":
            sr = {src: cfg["stage1"] for src, cfg in sources.items()}
        elif a.seed_run == "from-oneshot":
            sr = json.load(open(a.oneshot))
        else:
            sr = json.load(open(a.seed_run))
        fill_from_runs(base, "pred_seed_run", sr)
        ref = "seed_run"
    for tag, d in dfs.items():
        base[f"pred_{tag}"] = d.set_index(["uid", "event_id"]).loc[list(zip(base.uid, base.event_id)), "pred"].values
    base["pred_video_only"] = base.stage1
    cols = ["pred_video_only"]
    if a.oneshot:
        fill_from_runs(base, "pred_oneshot", json.load(open(a.oneshot)))
        cols.append("pred_oneshot")
    if a.seed_run:
        cols.append("pred_seed_run")
    cols += [f"pred_{t}" for t, _ in tags]
    for spec in a.extra_heldout:                      # e.g. orch_seed=runs/orch/heldout_test_orch_seed.csv
        tag, path = spec.split("=", 1)
        ex = pd.read_csv(path).drop_duplicates(["uid", "event_id"]).set_index(["uid", "event_id"])["pred"]
        base[f"pred_{tag}"] = [ex.get((u, e), "") for u, e in zip(base.uid, base.event_id)]
        cols.append(f"pred_{tag}")

    # ---------------- HD-EPIC: item-level FAIL rate per axis x variant
    hd = base[base.source == "hdepic"]
    if len(hd):
        print("\n== HD-EPIC: fraction of items judged FAIL (detection for broken variants; false alarm for original / eval_only)")
        tabs = {c: item_table(hd, c) for c in cols}
        keys = sorted(set(zip(hd.axis, hd.variant, hd.eval_only)))
        lines = []
        for ax, var, eo in keys:
            sel = lambda t: t[(t.axis == ax) & (t.variant == var) & (t.eval_only == eo)]
            n = len(sel(tabs[cols[0]]))
            vals = {c: sel(tabs[c])["no"].mean() for c in cols}
            d, ci = boot_ci(sel(tabs[f"pred_{ref}"])["no"], sel(tabs[cols[-1]])["no"])
            kind = "detect" if var in FAIL_VARIANTS else "false-alarm"
            lines.append(dict(axis=ax, variant=var + (" (eval only)" if eo else ""), kind=kind, n=n, **{c.replace("pred_", ""): round(v, 2) for c, v in vals.items()},
                              **{f"{cols[-1].replace('pred_', '')}-{ref}": f"{d:+.2f} [{ci[0]:+.2f},{ci[1]:+.2f}]"}))
        print(pd.DataFrame(lines).to_string(index=False))

    # ---------------- 220: per model x axis accuracy
    gen = base[base.source.isin(["ltx", "mova"])]
    if len(gen):
        print("\n== 220: accuracy vs human GT (event-level plain acc; item-level acc in parentheses)")
        lines = []
        for (src, ax), g in gen.groupby(["source", "axis"]):
            rec = dict(model=src, axis=ax, n_events=len(g), n_items=g.uid.nunique())
            for c in cols:
                ev = (g[c] == g["gt"]).mean()
                it = item_table(g, c).ok.mean()
                rec[c.replace("pred_", "")] = f"{ev:.2f} ({it:.2f})"
            ok_ref = (g[f"pred_{ref}"] == g["gt"]).groupby(g.uid).mean(); ok_best = (g[cols[-1]] == g["gt"]).groupby(g.uid).mean()
            d, ci = boot_ci(ok_ref.values, ok_best.values)
            rec[f"{cols[-1].replace('pred_', '')}-{ref}"] = f"{d:+.2f} [{ci[0]:+.2f},{ci[1]:+.2f}]"
            lines.append(rec)
        print(pd.DataFrame(lines).to_string(index=False))

    # ---------------- how much each tag differs from the existing video-only run
    what = "stage 2 vs stage 1" if not a.stage1 else "judged vs existing video-only run (rerun noise + rule effect)"
    print(f"\n== {what} (judged events): changed / of those correct after change")
    for tag, _ in tags:
        c = f"pred_{tag}"
        for src, g in base.groupby("source"):
            ch = g[g[c] != g.stage1]
            print(f"  {tag:6s} {src:6s} changed {len(ch):4d}/{len(g):4d} ({len(ch) / max(len(g), 1):.2f})  right after change {int((ch[c] == ch['gt']).sum()):4d}  wrong {int((ch[c] != ch['gt']).sum()):4d}")
    suffix = f"_{a.stage1}_{a.axis}" if a.stage1 else ""
    base.to_csv(Path(a.run_dir) / f"heldout_test_merged{suffix}.csv", index=False)
    print(f"\n-> {a.run_dir}/heldout_test_merged{suffix}.csv")


if __name__ == "__main__":
    main()
