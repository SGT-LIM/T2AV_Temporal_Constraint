#!/usr/bin/env python3
"""GT rows (item x axis) for GEPA v3 (2026-10-26). Same row format as make_gt.py, new data:
  hdepic : v2 prompts. A = new `_A` claim (claim event -> no) + originals; V = `_Vhand` / `_Vnoun` (swapped event -> no) + originals;
           AVB = shift early/late + originals (stage-1 judged); TCR = order_swap + originals, neighbouring events >= --tcr-gap s,
           stage-1 judged. No TCC (replaced by the movement set). `_A` items give NO V/AVB/TC rows (claim event is scored on V too).
  hdfoot : old prompts, only `_A` items whose claim is a footstep (clean GT, judge recall ~.2) -> A rows, source "hdfoot".
  move   : object-movement set, TCC item-level (names in move_names.csv exclude=1 dropped), stage-1 judged, source "hdmove".
  220    : reuse gepa_stage2/manifests/gt_{ltx,mova}.jsonl as they are.
Stage-1 dirs may be several (later ones override earlier rows by item_id).

  cd evaluation/ablation
  python gepa_stage2/make_gt_v3.py hdepic --prompt-json $E/hdepic_medium_prompts_v2.json --gt-csv $E/hdepic_medium_gt.csv \
      --stage1-dir $E/results/hdepic_medium_multi_baseline_g36 $E/results/hdepic_regen_multi_baseline_g36 \
      --drop-ids $E/regen_2026-10-25/dropped_items.txt --out gepa_stage2/manifests_v3/gt_hdepic.jsonl
  python gepa_stage2/make_gt_v3.py hdfoot --prompt-json $E/hdepic_medium_prompts.json --stage1-dir $E/results/hdepic_medium_multi_baseline_g36 \
      --out gepa_stage2/manifests_v3/gt_hdfoot.jsonl
  python gepa_stage2/make_gt_v3.py move --prompt-json $E/hdepic_move_prompts.json --gt-csv $E/hdepic_move_gt.csv \
      --names-csv $E/move_names.csv --stage1-dir $E/results/hdepic_move_multi_baseline_g36 --out gepa_stage2/manifests_v3/gt_hdmove.jsonl
"""
import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
import argparse, glob, json, re, sys
from collections import Counter
from pathlib import Path

import pandas as pd

pass  # (legacy sys.path insert removed)
pass  # (legacy sys.path insert removed)
from t2av_eval.judge.media import core as NE
from t2av_eval.judge.stage2 import two_stage as TS

CLIP_RE = re.compile(r"(P\d+-\d+-\d+_\d+)")
SHORT = {"original": "original", "fail_absent_sound": "absent_sound", "fail_hand_swap": "hand_swap", "fail_noun_swap": "noun_swap",
         "fail_audio_shift_early": "audio_shift_early", "fail_audio_shift_late": "audio_shift_late", "fail_order_swap": "order_swap",
         "fail_count_off": "count_off"}


def row(source, item_id, axis, variant, split_key, gt, eval_only=False):
    return dict(uid=f"{source}|{item_id}|{axis}", source=source, item_id=item_id, axis=axis, variant=variant,
                split_key=split_key, eval_only=eval_only, gt=gt)


def load_stage1_many(dirs):
    dfs = [TS.load_stage1(d) for d in dirs]
    df = pd.concat(dfs)
    df = df[~df.index.duplicated(keep="last")]
    print(f"[stage1] {len(df)} rows from {len(dirs)} run(s)")
    return df


def ids_for(axis, structs):
    if axis == "A":
        return [s["event_id"] for s in structs if s.get("has_audio")]
    if axis == "AVB":
        return [s["event_id"] for s in structs if s.get("has_binding")]
    return [s["event_id"] for s in structs]


def struct_for_prompt_event(structs, meta_events, prompt_eid):
    """scoring event_id for a prompt event id (e.g. 'e_sound_claim'): by source_id, else by prompt-order index."""
    for s in structs:
        if str(s.get("source_id", "")) == prompt_eid:
            return s["event_id"]
    ids = [e.get("id") for e in meta_events]
    if prompt_eid in ids:
        k = ids.index(prompt_eid)
        if k < len(structs):
            return structs[k]["event_id"]
    return None


def clip_key(iid):
    m = CLIP_RE.search(iid)
    return m.group(1) if m else iid


# ---------------------------------------------------------------- hdepic (v2 prompts)
def make_hdepic(a):
    raw = {x["item_id"]: x for x in json.load(open(a.prompt_json))}
    items = NE.load_prompt_items(Path(a.prompt_json))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    gt = pd.read_csv(a.gt_csv).drop_duplicates("item_id", keep="last").set_index("item_id")
    TS.STAGE1 = load_stage1_many(a.stage1_dir)
    drop = set(Path(a.drop_ids).read_text().split()) if a.drop_ids else set()
    import filters
    if a.seq_json:
        d = json.load(open(a.seq_json))
        if isinstance(d, dict):
            d = d.get("items", list(d.values()))
        seq = {x["item_id"]: x["sequence"] for x in d if isinstance(x, dict) and "sequence" in x}
        print(f"[tcr] event times from {a.seq_json} ({len(seq)} items)")
    else:
        _f, seq = filters.find_seq()          # slow: scans real_av_pilot recursively
    if not seq:
        sys.exit("no item file with 'sequence' found; pass --seq-json")
    rows, skipped = [], Counter()

    for iid, meta in metas.items():
        if iid in drop:
            skipped["dropped_id"] += 1; continue
        if iid not in gt.index:
            skipped["no_gt_row"] += 1; continue
        g = gt.loc[iid]; var = str(g["variant"]); clip = clip_key(iid)
        structs = NE.build_scoring_events(meta)
        all_ids = [s["event_id"] for s in structs]
        broken = None
        if pd.notna(g.get("broken_event_idx")) and str(g.get("broken_event_idx")) != "":
            k = int(float(g["broken_event_idx"]))
            broken = all_ids[k] if 0 <= k < len(all_ids) else None

        # ---- A
        a_ids = ids_for("A", structs)
        if var == "fail_absent_sound":
            claim = struct_for_prompt_event(structs, meta["events"], "e_sound_claim")
            if claim is None or claim not in a_ids:
                skipped["A_claim_not_found"] += 1
            else:
                rows.append(row("hdepic", iid, "A", "absent_sound", clip, {e: ("no" if e == claim else "yes") for e in a_ids}))
            continue                                   # `_A` items: A axis only (claim is scored on V/AVB too, by mistake)
        if var == "original" and a_ids:
            rows.append(row("hdepic", iid, "A", "original", clip, {e: "yes" for e in a_ids}))

        # ---- V
        if var == "fail_noun_swap":
            v2 = raw.get(iid, {}).get("v_fail_object_v2")
            b = struct_for_prompt_event(structs, meta["events"], v2["event"]) if v2 else broken
            if b is None:
                skipped["V_noun_event_not_found"] += 1
            else:
                rows.append(row("hdepic", iid, "V", "noun_swap", clip, {e: ("no" if e == b else "yes") for e in all_ids}))
        elif var == "fail_hand_swap":
            gtv = {e: ("no" if e == broken else "yes") for e in all_ids} if broken else {"__item__": "no"}
            rows.append(row("hdepic", iid, "V", "hand_swap", clip, gtv))
        elif var == "original":
            rows.append(row("hdepic", iid, "V", "original", clip, {e: "yes" for e in all_ids}))
        elif a.keep_eval_only and var in ("fail_audio_shift_early", "fail_audio_shift_late", "fail_order_swap"):
            rows.append(row("hdepic", iid, "V", SHORT.get(var, var), clip, {e: "yes" for e in all_ids}, eval_only=True))

        # ---- AVB
        if var in ("fail_audio_shift_early", "fail_audio_shift_late", "original"):
            judged, _ = TS.stage1_lookup(iid, TS.AVB, None)
            if judged:
                lab = "yes" if var == "original" else "no"
                rows.append(row("hdepic", iid, "AVB", SHORT[var], clip, {e["event_id"]: lab for e in judged}))
            else:
                skipped["AVB_no_stage1"] += 1

        # ---- TCR (gap filter on the window's event times)
        if var in ("fail_order_swap", "original"):
            w = iid.rsplit("_", 1)[0]
            s = seq.get(w + "_pass") or seq.get(iid)
            gap = filters.min_gap(s) if s else float("nan")
            if not (gap >= a.tcr_gap):
                skipped["TCR_gap_or_no_time"] += 1
            else:
                judged, _ = TS.stage1_lookup(iid, TS.TCR, None)
                if judged:
                    rows.append(row("hdepic", iid, "TCR", SHORT[var], clip, {"__item__": "yes" if var == "original" else "no"}))
                else:
                    skipped["TCR_no_stage1"] += 1
    write(rows, a.out); print("skipped / notes:", dict(skipped))


# ---------------------------------------------------------------- hdfoot (old prompts, footstep claims)
def make_hdfoot(a):
    raw = {x["item_id"]: x for x in json.load(open(a.prompt_json)) if x["item_id"].endswith("_A")}
    items = NE.load_prompt_items(Path(a.prompt_json))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    TS.STAGE1 = load_stage1_many(a.stage1_dir)
    rows, skipped = [], Counter()
    for iid, x in raw.items():
        claim_ev = next((e for e in x["events"] if e["id"] == "e_sound_claim"), None)
        txt = str((claim_ev or {}).get("target_sound") or (claim_ev or {}).get("action") or "").lower()
        if not any(c in txt for c in a.classes):
            skipped["other_class"] += 1; continue
        if iid not in metas:
            skipped["no_meta"] += 1; continue
        meta = metas[iid]; structs = NE.build_scoring_events(meta)
        a_ids = ids_for("A", structs)
        claim = struct_for_prompt_event(structs, meta["events"], "e_sound_claim")
        if claim is None or claim not in a_ids:
            skipped["claim_not_found"] += 1; continue
        if iid not in TS.STAGE1.index:
            skipped["no_stage1"] += 1
        rows.append(row("hdfoot", iid, "A", "absent_" + a.classes[0], clip_key(iid), {e: ("no" if e == claim else "yes") for e in a_ids}))
    write(rows, a.out); print("skipped / notes:", dict(skipped))


# ---------------------------------------------------------------- object movement (TCC)
def make_move(a):
    raw = {x["item_id"]: x for x in json.load(open(a.prompt_json))}
    items = NE.load_prompt_items(Path(a.prompt_json))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    gt = pd.read_csv(a.gt_csv).drop_duplicates("item_id", keep="last").set_index("item_id")
    bad = set(pd.read_csv(a.names_csv).query("exclude == 1").name) if a.names_csv else set()
    TS.STAGE1 = load_stage1_many(a.stage1_dir)
    rows, skipped = [], Counter()
    for iid, meta in metas.items():
        if iid not in gt.index:
            skipped["no_gt_row"] += 1; continue
        if any(e["action"].replace("move ", "", 1) in bad for e in raw[iid]["events"]):
            skipped["excluded_name"] += 1; continue
        lab = str(gt.loc[iid, "temporal_count_satisfaction"]).strip().lower()
        lab = "no" if lab in ("no", "fail", "false") else "yes"
        judged, _ = TS.stage1_lookup(iid, TS.TCC, None)
        if not judged:
            skipped["TCC_no_stage1"] += 1; continue
        var = "original" if iid.endswith("_pass") else "count_off"
        m = re.match(r"hdepicmove_(.+)_(\d{7})_", iid)
        key = f"{m.group(1)}_{m.group(2)}" if m else clip_key(iid)
        rows.append(row("hdmove", iid, "TCC", var, key, {"__item__": lab}))
    write(rows, a.out); print("skipped / notes:", dict(skipped))


def write(rows, out):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    df = pd.DataFrame(rows)
    df["fail"] = df["gt"].apply(lambda d: "no" in d.values())
    print(df.groupby(["source", "axis", "variant", "eval_only"]).fail.agg(n="size", n_fail="sum").to_string())
    print(f"-> {out} ({len(rows)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hdepic")
    h.add_argument("--prompt-json", required=True); h.add_argument("--gt-csv", required=True)
    h.add_argument("--stage1-dir", nargs="+", required=True); h.add_argument("--drop-ids", default=None)
    h.add_argument("--tcr-gap", type=float, default=1.0); h.add_argument("--keep-eval-only", action="store_true")
    h.add_argument("--seq-json", default=None, help="json with item_id + sequence (event times), e.g. real_av_pilot/items_hdepic_medium.json")
    h.add_argument("--out", required=True)
    f = sub.add_parser("hdfoot")
    f.add_argument("--prompt-json", required=True); f.add_argument("--stage1-dir", nargs="+", required=True)
    f.add_argument("--classes", nargs="+", default=["footstep"]); f.add_argument("--out", required=True)
    m = sub.add_parser("move")
    m.add_argument("--prompt-json", required=True); m.add_argument("--gt-csv", required=True); m.add_argument("--names-csv", default=None)
    m.add_argument("--stage1-dir", nargs="+", required=True); m.add_argument("--out", required=True)
    a = ap.parse_args()
    {"hdepic": make_hdepic, "hdfoot": make_hdfoot, "move": make_move}[a.cmd](a)