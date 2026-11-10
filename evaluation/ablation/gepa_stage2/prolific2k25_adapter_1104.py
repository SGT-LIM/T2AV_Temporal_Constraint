#!/usr/bin/env python3
"""New Prolific batch (prolific_ltx_2k_25), 11/04 (user). No judge calls.
Input: HF dataset dghadiya/t2av_eval_annotations, experiments/prolific_ltx_2k_25/annotations/*.json
       -> T2AV_Temporal_Constraint/generation/prolific_2k_25/ (one file per rater per video; same schema as the 149 batch).
GT: the 149 adapter's rules (gen149_adapter_1030: lab / item_from / fleiss; per (item, event, axis) majority of PASS / FAIL, ties or < 2
    labels = no GT, unanimous flag, holdout_gen=true) on the items NOT in the 149 or the 220 (by item_id), extended to the relation
    types the 149 batch did not have (order_count, sync_count; mapped as in relative_500_v5_fixed.json, the 220 prompts):
    TCR (per video, tcRel) for every order / sync item; TCC per event for every count-constrained item (user 11/04): a rater's label
    for an event is PASS iff that rater's tcCount equals the event's expected count. One annotation per rater (the latest).
Output: T2AV_data/gen_prolific2k25_1104/ prompts_gen2k25.json, gt_gen2k25.jsonl, kappa.json, stats.json, README.md;
        videos/<item_id>/<item_id>_v1_raw.mp4 from HF dataset dghadiya/T2AV_TemporalConstraint prolific_2k/LTX_2p3/<item_id>.mp4.
  python gepa_stage2/prolific2k25_adapter_1104.py stats | build | videos      (HF_TOKEN in the environment for videos)
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, collections, glob, json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen149_adapter_1030 as A149

SRC = Path((_tp.WORKSPACE + "/generation/prolific_2k_25/experiments/prolific_ltx_2k_25/annotations"))
D = Path((_tp.DATA + "/gen_prolific2k25_1104"))
SRCTAG = "gen2k25"
TASK = {"order": "order", "order_count": "order", "count": "count", "synchronization": "sync", "sync_count": "sync"}
COUNTED = {"count", "order_count", "sync_count"}                      # count-constrained -> TCC row (per event)
RELATED = {"order", "order_count", "synchronization", "sync_count"}   # order / sync relation -> TCR row (tcRel)


def load():
    by = collections.defaultdict(list)
    for f in sorted(glob.glob(str(SRC / "*.json"))):
        d = json.load(open(f))
        by[d["annotations"]["item_id"]].append(d)
    return by


def known():
    s149 = {x["item_id"] for x in json.load(open(A149.D / "prompts_gen149.json"))}
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(HERE / f"manifests_v3/{s}.jsonl")]
    s220 = {m["item_id"] for m in man if m["source"] in ("ltx", "mova")}
    return s149, s220


def stats():
    by = load()
    s149, s220 = known()
    files = sum(len(v) for v in by.values())
    vids = {d["video_id"] for v in by.values() for d in v}
    models = collections.Counter(d["annotations"]["model"] for v in by.values() for d in v)
    roles = collections.Counter(d.get("annotation_role") for v in by.values() for d in v)
    nann = collections.Counter(len({d["user"] for d in v}) for v in by.values())
    dup = sum(len(v) - len({d["user"] for d in v}) for v in by.values())
    lab = collections.defaultdict(collections.Counter)
    for v in by.values():
        for d in v:
            r = d["annotations"]["responses"]
            for e in r.get("events", {}).values():
                for ax in ("a", "v", "avb"):
                    if ax in e:
                        lab[ax.upper()][str(e[ax].get("label", "")).upper() or "EMPTY"] += 1
                if "tcCount" in e:
                    lab["tcCount (raw value present)"]["yes" if str(e["tcCount"].get("value", "")).strip() else "no"] += 1
            if "tcRel" in r.get("video", {}):
                lab["TCR"][str(r["video"]["tcRel"].get("label", "")).upper() or "EMPTY"] += 1
    rel = collections.Counter(v[0]["annotations"]["temporal_constraint"]["relationType"] for v in by.values())
    out = dict(files=files, items=len(by), video_ids=len(vids), models=dict(models), annotation_role=dict(roles),
               annotators_per_item=dict(sorted(nann.items())), duplicate_rater_files=dup, relation_types=dict(rel),
               overlap_149=len(set(by) & s149), overlap_220=len(set(by) & s220), overlap_both=len(set(by) & s149 & s220),
               new_items=len(set(by) - s149 - s220), labels={k: dict(v) for k, v in lab.items()})
    D.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(D / "stats.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def item_from(a, subjects):
    """the 149 item_from with order_count / sync_count mapped as in relative_500_v5_fixed.json (the 220 prompts):
    order_count -> task order, sync_count -> task sync, both count-constrained."""
    it = A149.item_from(dict(a, temporal_constraint=dict(a["temporal_constraint"], relationType="order")), subjects)
    rt = a["temporal_constraint"]["relationType"]
    it["temporal_constraint"].update(relation_type=rt, task_type=TASK[rt], count_constrained=rt in COUNTED, value=a["temporal_constraint"]["value"])
    it["source"] = SRCTAG
    return it


def majority(ls):
    c = collections.Counter(ls)
    return c.most_common(1)[0][0] if len(ls) >= 2 and c.most_common(1)[0][1] * 2 > len(ls) else None


def build():
    subjects = json.load(open(A149.REL500))[0]["subjects"]
    by = load()
    s149, s220 = known()
    items, rows, kap_units, ndup = [], [], collections.defaultdict(list), 0
    for iid in sorted(set(by) - s149 - s220):
        last = {}
        for d in sorted(by[iid], key=lambda d: d.get("created_at", "")):
            ndup += d["user"] in last
            last[d["user"]] = d
        anns = [d["annotations"] for d in last.values()]
        a0 = anns[0]
        items.append(item_from(a0, subjects))
        eids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(a0["events"])}
        for ax in ("a", "v", "avb"):
            gt, unan = {}, True
            for e in a0["events"]:
                if not e["axes"].get(ax):
                    continue
                ls = [l for l in (A149.lab(x["responses"]["events"].get(e["id"], {}).get(ax)) for x in anns) if l]
                kap_units[ax.upper()].append(ls)
                m = majority(ls)
                if m:
                    gt[eids[e["id"]]] = m
                    unan &= len(set(ls)) == 1
            if gt:
                AX = {"a": "A", "v": "V", "avb": "AVB"}[ax]
                rows.append(dict(uid=f"{SRCTAG}|{iid}|{AX}", source=SRCTAG, item_id=iid, axis=AX, gt=gt, unanimous=unan, n_raters=len(anns), holdout_gen=True))
        rt = a0["temporal_constraint"]["relationType"]
        if rt in RELATED:
            ls = [l for l in (A149.lab(x["responses"]["video"].get("tcRel")) for x in anns) if l]
            kap_units["TCR"].append(ls)
            m = majority(ls)
            if m:
                rows.append(dict(uid=f"{SRCTAG}|{iid}|TCR", source=SRCTAG, item_id=iid, axis="TCR", gt={"__item__": m},
                                 unanimous=len(set(ls)) == 1, n_raters=len(anns), holdout_gen=True))
        if rt in COUNTED:
            # 11/04 (user): TC per event. The per-video version of this morning is kept as gt_gen2k25_tcvideo_1104.jsonl.
            exp = a0["temporal_constraint"]["expectedCounts"]
            gt, unan = {}, True
            for e, n in exp.items():
                ls = []
                for x in anns:
                    try:
                        ls.append("yes" if int(str(x["responses"]["events"][e]["tcCount"]["value"]).strip()) == int(n) else "no")
                    except (KeyError, ValueError, TypeError):
                        continue
                kap_units["TCC"].append(ls)
                m = majority(ls)
                if m and e in eids:
                    gt[eids[e]] = m
                    unan &= len(set(ls)) == 1
            if gt:
                rows.append(dict(uid=f"{SRCTAG}|{iid}|TCC", source=SRCTAG, item_id=iid, axis="TCC", gt=gt, unanimous=unan,
                                 n_raters=len(anns), holdout_gen=True))
    D.mkdir(parents=True, exist_ok=True)
    json.dump(items, open(D / "prompts_gen2k25.json", "w"), indent=1)
    with open(D / "gt_gen2k25.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    # Fleiss' kappa on the units with exactly 3 labels (the 149 function); units with 4-6 raters are left out of kappa only
    kap = {ax: dict(zip(("kappa", "units_with_3"), A149.fleiss(u))) for ax, u in kap_units.items()}
    json.dump(kap, open(D / "kappa.json", "w"), indent=1)
    c = collections.Counter((r["axis"], "FAIL" if "no" in r["gt"].values() else "PASS") for r in rows)
    print(f"items {len(items)} (duplicate rater files dropped: {ndup}), GT rows {len(rows)}")
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        print(f"  {ax:4s} rows {c[(ax, 'PASS')] + c[(ax, 'FAIL')]}: PASS {c[(ax, 'PASS')]}, FAIL {c[(ax, 'FAIL')]}, unanimous "
              f"{sum(1 for r in rows if r['axis'] == ax and r['unanimous'])} | kappa {kap.get(ax)}")
    sys.path.insert(0, str(HERE.parent))
    import new_eval as NE
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    bad = [r["uid"] for r in rows if r["axis"] in ("A", "V", "AVB", "TCC")
           and not set(r["gt"]) <= {s["event_id"] for s in NE.build_scoring_events(metas[r["item_id"]])}]
    print(f"items parsed by new_eval: {len(items)}; GT rows with event ids not in the scoring events: {len(bad)}")


def videos():
    from huggingface_hub import hf_hub_download
    items = json.load(open(D / "prompts_gen2k25.json"))
    miss = []
    for k, it in enumerate(items):
        iid = it["item_id"]
        out = D / "videos" / iid / f"{iid}_v1_raw.mp4"
        if out.exists():
            continue
        try:
            p = hf_hub_download("dghadiya/T2AV_TemporalConstraint", f"prolific_2k/LTX_2p3/{iid}.mp4", repo_type="dataset", local_dir=str(D / "hf_cache"))
        except Exception as e:
            miss.append((iid, type(e).__name__)); continue
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out)
        if k % 100 == 0:
            print(f"[videos] {k + 1}/{len(items)}", flush=True)
    json.dump(miss, open(D / "videos_missing.json", "w"), indent=1)
    print("videos:", len(list((D / "videos").glob("*/*.mp4"))), "missing:", len(miss))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["stats", "build", "videos"])
    globals()[ap.parse_args().stage]()
