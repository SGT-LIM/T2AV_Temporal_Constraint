#!/usr/bin/env python3
"""Generated holdout: 149 LTX-2.3 videos, 3 Prolific raters each (10/30). No judge calls.

Input: generation/149videos.zip -> T2AV_data/gen_holdout_149_1030/raw/prolific_ltx_2k_50/annotations/*.json (one per rater per video).
Each annotation embeds the item (prompt, events, temporal_constraint with expectedCounts); there is no separate prompt file.
Output (T2AV_data/gen_holdout_149_1030/):
  prompts_gen149.json      items in the relative_500 schema (prompt text and event definitions copied verbatim)
  gt_gen149.jsonl          GT rows (manifest format): uid, source=gen149, item_id, axis, gt {event_k|__item__: yes/no},
                           unanimous, n_raters, holdout_gen=true
  kappa.json, README.md
  videos/<item_id>/<item_id>_v1_raw.mp4   from HF dataset dghadiya/T2AV_TemporalConstraint, prolific_2k/LTX_2p3/<item_id>.mp4
GT rules: per (item, event, axis) the majority of the 3 PASS/FAIL labels (N/A or missing labels not counted; a tie or <2 labels =
no GT for that event). A / V / AVB rows: the events whose `axes` flag is true. TCR: video-level tcRel majority (order and
synchronization items). TCC: count items only (as in the 220 GT); a rater's count label is PASS iff every event's tcCount equals
expectedCounts; then the majority. A row is unanimous when every GT event of the row had 3 identical labels.
Fleiss' kappa per axis over the rated units (2 categories, 3 raters).

  python gepa_stage2/gen149_adapter_1030.py build      # items, GT, kappa (no network)
  python gepa_stage2/gen149_adapter_1030.py videos     # download the 149 videos (huggingface_hub)
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import argparse, collections, glob, json, re, shutil
from pathlib import Path

D = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030")
A = D / "raw/prolific_ltx_2k_50/annotations"
REL500 = Path((_LEGACY_ROOT + "/new_prompts/generated/relative_500_v5_fixed.json"))
TASK = {"order": "order", "count": "count", "synchronization": "sync"}
MODLAB = {"speech": "Speech", "silent_action": "Action (silent)", "sounding_action": "Action (sounding)"}


def lab(x):
    s = str((x or {}).get("label", "")).strip().upper()
    return "yes" if s == "PASS" else ("no" if s == "FAIL" else None)


def convert_event(e):
    out = {"id": e["id"], "modality": e["modality"], "actor": e.get("actor", "person_A"), "definition": e["definition"]}
    body = e["label"].split(":", 1)[1].strip()
    if e["modality"] == "speech":
        m = re.search(r'say\s+"([^"]+)"', body)
        out["text"] = m.group(1) if m else body
    else:
        m = re.match(r"([A-Za-z0-9_]+)\s*(?:\(([^)]*)\))?", body)
        out["action"] = m.group(1)
        extra = (m.group(2) or "").lower()
        side = re.search(r"\b(left|right)\b", extra)
        part = re.search(r"\b(hand|head|foot|arm|body)\b", extra)
        if side:
            out["body_side"] = side.group(1)
        if part:
            out["body_part"] = part.group(1)
    return out


def item_from(a, subjects):
    tc = a["temporal_constraint"]
    rt = tc["relationType"]
    evs = [convert_event(e) for e in a["events"]]
    return {"item_id": a["item_id"], "canonical_item_id": a.get("canonical_id"),
            "modality_combination": " + ".join(dict.fromkeys(MODLAB.get(e["modality"], e["modality"]) for e in evs)),
            "subjects": subjects, "events": evs,
            "temporal_constraint": {"relation_type": rt, "task_type": TASK[rt], "count_constrained": rt == "count", "n_events": len(evs),
                                    "timing_type": tc.get("timingType", "relative"), "value": tc["value"]},
            "scene_hint": a.get("scene_hint"), "camera_hint": a.get("camera_hint"), "generated_prompt": a["prompt"],
            "source": "gen149", "holdout_gen": True}


def fleiss(units):
    """units: list of label lists (each 3 labels in {yes,no}). Fleiss' kappa, 2 categories."""
    units = [u for u in units if len(u) == 3]
    if not units:
        return None, 0
    n, N = 3, len(units)
    P_i = [(sum(u.count(c) ** 2 for c in ("yes", "no")) - n) / (n * (n - 1)) for u in units]
    p = {c: sum(u.count(c) for u in units) / (N * n) for c in ("yes", "no")}
    Pbar, Pe = sum(P_i) / N, sum(v ** 2 for v in p.values())
    return (round((Pbar - Pe) / (1 - Pe), 3) if Pe < 1 else None), N


def build():
    subjects = json.load(open(REL500))[0]["subjects"]
    by = collections.defaultdict(list)
    for f in sorted(glob.glob(str(A / "*.json"))):
        d = json.load(open(f))
        by[d["annotations"]["item_id"]].append(d["annotations"])
    items, rows, kap_units = [], [], collections.defaultdict(list)
    for iid, anns in sorted(by.items()):
        a0 = anns[0]
        items.append(item_from(a0, subjects))
        eids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(a0["events"])}
        for ax in ("a", "v", "avb"):
            gt, unan = {}, True
            for e in a0["events"]:
                if not e["axes"].get(ax):
                    continue
                ls = [lab(x["responses"]["events"].get(e["id"], {}).get(ax)) for x in anns]
                ls = [l for l in ls if l]
                kap_units[ax.upper()].append(ls)
                c = collections.Counter(ls)
                if len(ls) >= 2 and c.most_common(1)[0][1] * 2 > len(ls):
                    gt[eids[e["id"]]] = c.most_common(1)[0][0]
                    unan &= len(set(ls)) == 1 and len(ls) == 3
            if gt:
                rows.append(dict(uid=f"gen149|{iid}|{ {'a': 'A', 'v': 'V', 'avb': 'AVB'}[ax] }", source="gen149", item_id=iid,
                                 axis={"a": "A", "v": "V", "avb": "AVB"}[ax], gt=gt, unanimous=unan, n_raters=len(anns), holdout_gen=True))
        rt = a0["temporal_constraint"]["relationType"]
        if rt in ("order", "synchronization"):
            ls = [lab(x["responses"]["video"].get("tcRel")) for x in anns]
            ls = [l for l in ls if l]
            kap_units["TCR"].append(ls)
            c = collections.Counter(ls)
            if len(ls) >= 2 and c.most_common(1)[0][1] * 2 > len(ls):
                rows.append(dict(uid=f"gen149|{iid}|TCR", source="gen149", item_id=iid, axis="TCR", gt={"__item__": c.most_common(1)[0][0]},
                                 unanimous=len(set(ls)) == 1 and len(ls) == 3, n_raters=len(anns), holdout_gen=True))
        if rt == "count":
            exp = a0["temporal_constraint"]["expectedCounts"]
            ls = []
            for x in anns:
                try:
                    ok = all(int(str(x["responses"]["events"][e]["tcCount"]["value"]).strip()) == int(n) for e, n in exp.items())
                    ls.append("yes" if ok else "no")
                except (KeyError, ValueError, TypeError):
                    continue
            kap_units["TCC"].append(ls)
            c = collections.Counter(ls)
            if len(ls) >= 2 and c.most_common(1)[0][1] * 2 > len(ls):
                rows.append(dict(uid=f"gen149|{iid}|TCC", source="gen149", item_id=iid, axis="TCC", gt={"__item__": c.most_common(1)[0][0]},
                                 unanimous=len(set(ls)) == 1 and len(ls) == 3, n_raters=len(anns), holdout_gen=True))
    json.dump(items, open(D / "prompts_gen149.json", "w"), indent=1)
    with open(D / "gt_gen149.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    kap = {ax: dict(zip(("kappa", "units"), fleiss(u))) for ax, u in kap_units.items()}
    json.dump(kap, open(D / "kappa.json", "w"), indent=1)
    # summary
    c = collections.Counter((r["axis"], "FAIL" if "no" in r["gt"].values() else "PASS", "unanimous" if r["unanimous"] else "majority_only") for r in rows)
    print(f"items {len(items)}, GT rows {len(rows)}")
    for ax in ("A", "V", "AVB", "TCR", "TCC"):
        print(f"  {ax:4s} " + "  ".join(f"{lab_}:{c[(ax, lab_, u)]}/{c[(ax, lab_, 'majority_only')] if False else ''}" for lab_ in () for u in ()) +
              f"PASS unanimous {c[(ax, 'PASS', 'unanimous')]}, PASS majority-only {c[(ax, 'PASS', 'majority_only')]}, "
              f"FAIL unanimous {c[(ax, 'FAIL', 'unanimous')]}, FAIL majority-only {c[(ax, 'FAIL', 'majority_only')]} | kappa {kap.get(ax)}")
    # check the converted items parse in the pipeline
    import sys
    sys.path.insert(0, _LEGACY_CODE)
    import new_eval as NE
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    bad = []
    for r in rows:
        if r["axis"] in ("A", "V", "AVB"):
            ok = {s["event_id"] for s in NE.build_scoring_events(metas[r["item_id"]])}
            if not set(r["gt"]) <= ok:
                bad.append(r["uid"])
    print(f"items parsed by new_eval: {len(metas)}; GT rows with event ids not in the scoring events: {len(bad)}")


def videos():
    from huggingface_hub import hf_hub_download
    items = json.load(open(D / "prompts_gen149.json"))
    for k, it in enumerate(items):
        iid = it["item_id"]
        out = D / "videos" / iid / f"{iid}_v1_raw.mp4"
        if out.exists():
            continue
        p = hf_hub_download("dghadiya/T2AV_TemporalConstraint", f"prolific_2k/LTX_2p3/{iid}.mp4", repo_type="dataset",
                            local_dir=str(D / "hf_cache"))
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, out)
        if k % 25 == 0:
            print(f"[videos] {k + 1}/{len(items)}", flush=True)
    print("videos:", len(list((D / "videos").glob("*/*.mp4"))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build", "videos"])
    globals()[ap.parse_args().stage]()
