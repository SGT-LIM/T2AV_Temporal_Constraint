#!/usr/bin/env python3
"""Build video-level majority-vote GT for the min3 eval subset from the
dghadiya/t2av_eval_annotations JSON files.

    python build_gt_min3.py \
        --annotations /projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/annotations \
        --subsets /projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3 \
        --prompt-json /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/new_prompts/generated/relative_500_v5_fixed.json \
        --out-dir /projectnb/ivc-ml/youngsun/T2AV_data/gt_annotations/min3_gt

Outputs (in --out-dir):
  gt_video.csv   one row per (model, video): majority label per axis, n annotators,
                 unanimous flag per axis. Axes: A V AVB TCREL TCCNT CC
  gt_event.csv   one row per (model, video, annotator, event_key): raw per-event labels,
                 observed count, required count
  unmatched.txt  eval videos with < --min-annot annotations (should be empty for min3)
Tie rule: on a PASS/FAIL tie the votes of --tiebreak-drop annotators (default Adi) are
removed and the remaining votes recounted; still-tied videos stay TIE and are excluded
downstream. <axis>_tiebroken marks rows decided by this rule.
  count_unresolved.txt  count-constrained items whose required counts could not be read

Annotation JSON layout (one file = one annotator x one video):
  video_id = "<item>__<MODEL>"   (item = file stem for the old batch, item dir for the new batch)
  annotations.responses.events.<event_key>.{a,v,avb}.label = PASS|FAIL
  annotations.responses.events.<event_key>.tcCount.value  = "<int>"  (observed count;
        0 if the event failed A/V/AVB; expected 1 when the prompt gives no count)
  annotations.responses.video.{tcRel,cc}.label            = PASS|FAIL

Video-level A/V/AVB  = PASS iff every event that carries that axis is PASS.
Video-level TCCNT    = PASS iff, for every event with a parsable observed count,
                       observed == required (required from the prompt JSON, default 1).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

AXES_EVENT = {"a": "A", "v": "V", "avb": "AVB"}
AXES_VIDEO = {"tcRel": "TCREL", "cc": "CC"}
ALL_AXES = ["A", "V", "AVB", "TCREL", "TCCNT", "CC"]


def stem_key(video_file: str) -> str:
    """'help-with-thumbs_up__sync__v1_raw.mp4' -> 'help-with-thumbs_up__sync'"""
    return re.sub(r"_?_v\d+_raw\.mp4$", "", video_file)


# ---------------------------------------------------------------------------
# prompt JSON: required counts + event aliases
# ---------------------------------------------------------------------------
def required_counts(item: dict) -> tuple[dict, str]:
    """Return ({event_id: required_count}, source); default 1 per event."""
    ev_ids = [e["id"] for e in item.get("events", [])]
    req = {e: 1 for e in ev_ids}
    tc = item.get("temporal_constraint") or {}
    if not tc.get("count_constrained"):
        return req, "not_count_constrained"
    val = tc.get("value") or {}
    src = []
    if isinstance(val.get("count"), int):                      # one count for all (sync_count)
        for e in ev_ids:
            req[e] = val["count"]
        src.append("value.count")
    if isinstance(val.get("counts"), dict):                    # per-event dict
        for k, v in val["counts"].items():
            if isinstance(v, int):
                req[k] = v
        src.append("value.counts")
    for s in val.get("sequence") or []:                        # sequence entries with counts
        if isinstance(s, dict):
            eid = s.get("event") or s.get("id")
            if eid in req and isinstance(s.get("count"), int):
                req[eid] = s["count"]
                src.append("value.sequence[].count")
    for e in item.get("events", []):                           # events carrying their own count
        for k in ("count", "repeat", "repetitions"):
            if isinstance(e.get(k), int):
                req[e["id"]] = e[k]
                src.append(f"events[].{k}")
    if not src:                                                # item_id fallback '..._x2-then-..._x1'
        xs = re.findall(r"_x(\d+)", item.get("item_id", ""))
        if xs and len(xs) == len(ev_ids):
            for e, n in zip(ev_ids, xs):
                req[e] = int(n)
            src.append("item_id_xN")
    return req, ("+".join(sorted(set(src))) if src else "UNRESOLVED")


def event_aliases(item: dict) -> dict:
    """annotation event_key -> prompt event id (ids, action names, speech_<text>)."""
    al = {}
    for e in item.get("events", []):
        eid = e["id"]
        al[eid] = eid
        if e.get("action"):
            al.setdefault(e["action"], eid)
        if e.get("text"):
            al.setdefault(f"speech_{e['text']}", eid)
            al.setdefault(e["text"], eid)
    return al


def parse_count(v):
    try:
        return int(str(v).strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# annotations
# ---------------------------------------------------------------------------
def load_annotations(ann_dir: Path):
    by_video = defaultdict(list)
    n_files = 0
    for f in sorted(ann_dir.glob("*.json")):
        n_files += 1
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] unreadable {f.name}: {exc}")
            continue
        vid = d.get("video_id")
        resp = (d.get("annotations") or {}).get("responses") or {}
        events = resp.get("events") or {}
        video = resp.get("video") or {}

        rec = {"video_id": vid, "user": d.get("user", "?"), "file": f.name, "events": {}}
        for k, ax in AXES_VIDEO.items():
            lab = (video.get(k) or {}).get("label")
            rec[ax] = lab if lab in ("PASS", "FAIL") else None
        agg = {ax: [] for ax in AXES_EVENT.values()}
        for ek, ev in events.items():
            e = {}
            for k, ax in AXES_EVENT.items():
                lab = (ev.get(k) or {}).get("label")
                if lab in ("PASS", "FAIL"):
                    e[ax] = lab
                    agg[ax].append(lab)
            e["tcCount"] = (ev.get("tcCount") or {}).get("value")
            rec["events"][ek] = e
        for ax, labs in agg.items():
            rec[ax] = ("PASS" if all(l == "PASS" for l in labs) else "FAIL") if labs else None
        rec["TCCNT"] = None  # filled once the prompt item is known
        by_video[vid].append(rec)
    print(f"[INFO] {n_files} annotation files, {len(by_video)} distinct video_ids")
    return by_video


def tccnt_label(rec: dict, req: dict, aliases: dict):
    labs = []
    for ek, e in rec["events"].items():
        c = parse_count(e.get("tcCount"))
        pid = aliases.get(ek)
        e["required"] = req.get(pid) if pid else None
        e["prompt_event"] = pid
        if c is None or pid is None:
            continue
        labs.append(c == req.get(pid, 1))
    if not labs:
        return None
    return "PASS" if all(labs) else "FAIL"


def majority(pairs, tiebreak_drop=()):
    """pairs: [(user, label)]. Returns (label, n_labels, unanimous, tiebroken).
    On a PASS/FAIL tie, drop the votes of users in `tiebreak_drop` and recount once."""
    pairs = [(u, l) for u, l in pairs if l in ("PASS", "FAIL")]
    if not pairs:
        return None, 0, None, False
    c = Counter(l for _, l in pairs)
    top, n = c.most_common(1)[0]
    if len(c) == 2 and c["PASS"] == c["FAIL"]:
        kept = [(u, l) for u, l in pairs if u not in tiebreak_drop]
        if kept and len(kept) < len(pairs):
            c2 = Counter(l for _, l in kept)
            top2, n2 = c2.most_common(1)[0]
            if not (len(c2) == 2 and c2["PASS"] == c2["FAIL"]):
                return top2, len(pairs), False, True
        return "TIE", len(pairs), False, False
    return top, len(pairs), (n == len(pairs)), False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--subsets", type=Path, required=True, help="eval_subsets/min3 (contains LTX_2p3/, MOVA/)")
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--models", nargs="+", default=["LTX_2p3", "MOVA"])
    ap.add_argument("--min-annot", type=int, default=3)
    ap.add_argument("--tiebreak-drop", nargs="*", default=["Adi"],
                    help="On a PASS/FAIL tie, drop these annotators' votes and recount (default: Adi).")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    items = {i["item_id"]: i for i in json.loads(args.prompt_json.read_text(encoding="utf-8"))}
    print(f"[INFO] {len(items)} prompt items")
    by_video = load_annotations(args.annotations)

    rows, ev_rows, unmatched, no_item, unresolved = [], [], [], [], []
    src_counter = Counter()
    for model in args.models:
        vids = sorted((args.subsets / model).rglob("*.mp4"))
        print(f"[INFO] {model}: {len(vids)} eval videos")
        for v in vids:
            # two naming generations: old batch keys by file stem, new batch by item dir
            cands = [stem_key(v.name), v.parent.name]
            item_id = max(cands, key=lambda k: len(by_video.get(f"{k}__{model}", [])))
            key = f"{item_id}__{model}"
            recs = by_video.get(key, [])
            if len(recs) < args.min_annot:
                unmatched.append(f"{model}\t{v.name}\t{key}\tn_annot={len(recs)}")

            item = items.get(item_id) or items.get(stem_key(v.name)) or items.get(v.parent.name)
            if item is None:
                no_item.append(f"{model}\t{v.name}")
                req, aliases, src = {}, {}, "NO_ITEM"
            else:
                req, src = required_counts(item)
                aliases = event_aliases(item)
                if src == "UNRESOLVED":
                    unresolved.append(f"{item_id}\t{json.dumps((item.get('temporal_constraint') or {}).get('value'))}")
            src_counter[src] += 1
            for r in recs:
                r["TCCNT"] = tccnt_label(r, req, aliases)

            row = {"model": model, "video_file": v.name, "video_id": key, "item_id": item_id,
                   "item_dir": v.parent.name, "n_annot": len(recs),
                   "count_constrained": bool(((item or {}).get("temporal_constraint") or {}).get("count_constrained")),
                   "required_counts": json.dumps(req), "count_source": src,
                   "annotators": "|".join(sorted(r["user"] for r in recs))}
            for ax in ALL_AXES:
                lab, n, unan, tb = majority([(r["user"], r[ax]) for r in recs], tuple(args.tiebreak_drop))
                row[f"{ax}_gt"], row[f"{ax}_n"], row[f"{ax}_unanimous"], row[f"{ax}_tiebroken"] = lab, n, unan, tb
            rows.append(row)
            for r in recs:
                for ek, e in r["events"].items():
                    ev_rows.append({"model": model, "video_file": v.name, "video_id": key,
                                    "user": r["user"], "event_key": ek, "prompt_event": e.get("prompt_event"),
                                    "A": e.get("A"), "V": e.get("V"), "AVB": e.get("AVB"),
                                    "tcCount_observed": e.get("tcCount"), "tcCount_required": e.get("required")})

    gt = pd.DataFrame(rows)
    gt.to_csv(args.out_dir / "gt_video.csv", index=False)
    pd.DataFrame(ev_rows).to_csv(args.out_dir / "gt_event.csv", index=False)
    (args.out_dir / "unmatched.txt").write_text("\n".join(unmatched))
    (args.out_dir / "count_unresolved.txt").write_text("\n".join(unresolved))

    print(f"\n[INFO] wrote {len(gt)} video rows -> {args.out_dir/'gt_video.csv'}")
    print(f"[INFO] videos with < {args.min_annot} annotations: {len(unmatched)}")
    print(f"[INFO] videos with no prompt item found: {len(no_item)}")
    for x in no_item[:5]:
        print("       ", x)
    print(f"[INFO] required-count source: {dict(src_counter)}")
    if unresolved:
        print(f"[WARN] count_constrained items with UNRESOLVED required counts (defaulted to 1): {len(unresolved)} -> count_unresolved.txt")
        for x in unresolved[:3]:
            print("       ", x)
    print("[INFO] annotators per video:", gt.groupby("model").n_annot.value_counts().sort_index().to_dict())
    for ax in ALL_AXES:
        sub = gt[gt[f"{ax}_n"] > 0]
        print(f"[INFO] {ax:5s} labeled={len(sub):3d}  PASS={int((sub[f'{ax}_gt']=='PASS').sum()):3d} "
              f"FAIL={int((sub[f'{ax}_gt']=='FAIL').sum()):3d} TIE={int((sub[f'{ax}_gt']=='TIE').sum()):2d} "
              f"unanimous={int(sub[f'{ax}_unanimous'].fillna(False).astype(bool).sum()):3d} "
              f"tiebroken={int(sub[f'{ax}_tiebroken'].astype(bool).sum()):2d}")


if __name__ == "__main__":
    main()
