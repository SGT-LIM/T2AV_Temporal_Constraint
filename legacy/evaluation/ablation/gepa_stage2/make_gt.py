#!/usr/bin/env python3
"""Build the item x axis GT manifest for stage-2 rule optimisation (design/gepa_stage2_rules_2026-10-19.md).

One jsonl row per (item, axis):
  {"uid": "hdepic|<item_id>|A", "source": "hdepic"|"ltx"|"mova", "item_id": ..., "axis": "A"|"V"|"AVB",
   "variant": ..., "split_key": <clip or item id>, "eval_only": bool, "gt": {"<event_id>": "yes"|"no", ...}}
Event ids come from new_eval.build_scoring_events(item_meta), i.e. exactly what the judge returns.
Per axis the GT covers the events the judge labels on that axis: A -> has_audio, V -> all, AVB -> has_binding.

HD-EPIC  (hdepic_medium_gt.csv: item_id, variant, broken_event_idx, <axis> PASS/FAIL ...; broken_event_idx indexes
          build_scoring_events order, as in gepa_caption_guide/make_gt_hdepic.py)
  A   : fail_absent_sound (broken event -> no)         + original (all yes)
  V   : fail_hand_swap / fail_noun_swap (broken -> no) + original (all yes); other variants -> all yes, eval_only
        (--vabl-ids restricts V rows to the 326 subset; omit = all)
  AVB : fail_audio_shift_early / late (all judged -> no) + original (all judged -> yes); only events with a stage-1 AVB label
  TCR : fail_order_swap (item no) + original (item yes); only items with a stage-1 TC-Rel label
  TCC : fail_count_off (broken event no) + original (all yes); only events with a stage-1 observed_count
220  (gt_event_majority.csv: model, video_file, event_key, event_kind, A, V, AVB with PASS/FAIL/TIE/empty)
  Dependent axes keep only rows whose parent axes PASS in the human GT (AVB: A and V of that event; TC: A, V, AVB of the
  video), so every remaining FAIL is a failure of that axis itself, not one inherited through the hierarchy.
  event_key = kind[_k] in prompt order (kind in speech / sounding_action / silent_action), same rule as
  eval_results/m2_event_flips.py (D). TIE / empty -> dropped.

  cd evaluation/ablation
  python gepa_stage2/make_gt.py hdepic --prompt-json $E/hdepic_medium_prompts.json --gt-csv $E/hdepic_medium_gt.csv \
        --stage1-dir $E/results/hdepic_medium_multi_baseline [--vabl-ids file] --out gepa_stage2/manifests/gt_hdepic.jsonl
  python gepa_stage2/make_gt.py gen --prompt-json $P --gt-event-csv $D/gt_annotations/min3_gt/gt_event_majority.csv \
        --stage1-csv $R/multi_agent/baseline_min3/LTX_2p3_agentic_pure_gemini.csv --model LTX_2p3 --source ltx --out gepa_stage2/manifests/gt_ltx.jsonl
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import new_eval as NE
import run_two_stage as TS

CLIP_RE = re.compile(r"(P\d+-\d+-\d+_\d+)")
V_FAIL = {"fail_hand_swap", "fail_noun_swap"}
AVB_FAIL = {"fail_audio_shift_early", "fail_audio_shift_late"}
A_FAIL = {"fail_absent_sound"}
SHORT = {"original": "original", "fail_absent_sound": "absent_sound", "fail_hand_swap": "hand_swap", "fail_noun_swap": "noun_swap",
         "fail_audio_shift_early": "audio_shift_early", "fail_audio_shift_late": "audio_shift_late", "fail_mute": "mute",
         "fail_order_swap": "order_swap", "fail_count_off": "count_off"}


def row(source, item_id, axis, variant, split_key, gt, eval_only=False):
    return dict(uid=f"{source}|{item_id}|{axis}", source=source, item_id=item_id, axis=axis, variant=variant,
                split_key=split_key, eval_only=eval_only, gt=gt)


def scoring(meta):
    return NE.build_scoring_events(meta)


def ids_for(axis, structs):
    if axis == "A":
        return [s["event_id"] for s in structs if s.get("has_audio")]
    if axis == "AVB":
        return [s["event_id"] for s in structs if s.get("has_binding")]
    return [s["event_id"] for s in structs]


# ---------------------------------------------------------------- HD-EPIC
def make_hdepic(a):
    items = NE.load_prompt_items(Path(a.prompt_json))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    gt = pd.read_csv(a.gt_csv).drop_duplicates("item_id", keep="last").set_index("item_id")
    TS.STAGE1 = TS.load_stage1(a.stage1_dir)
    vabl = set(Path(a.vabl_ids).read_text().split()) if a.vabl_ids else None
    vabl_clips = {CLIP_RE.search(i).group(1) for i in vabl if CLIP_RE.search(i)} if vabl else None
    rows, skipped = [], Counter()

    for iid, meta in metas.items():
        if iid not in gt.index:
            skipped["no_gt_row"] += 1; continue
        g = gt.loc[iid]
        var = str(g["variant"])
        m = CLIP_RE.search(iid); clip = m.group(1) if m else iid
        structs = scoring(meta)
        all_ids = [s["event_id"] for s in structs]
        broken = None
        if pd.notna(g.get("broken_event_idx")) and str(g.get("broken_event_idx")) != "":
            k = int(float(g["broken_event_idx"]))
            broken = all_ids[k] if 0 <= k < len(all_ids) else None
            if broken is None:
                skipped["bad_broken_idx"] += 1

        # ---- A
        a_ids = ids_for("A", structs)
        if var in A_FAIL and a_ids:
            if broken in a_ids:
                rows.append(row("hdepic", iid, "A", SHORT[var], clip, {e: ("no" if e == broken else "yes") for e in a_ids}))
            else:
                rows.append(row("hdepic", iid, "A", SHORT[var], clip, {"__item__": "no"})); skipped["A_item_level"] += 1
        elif var == "original" and a_ids:
            rows.append(row("hdepic", iid, "A", "original", clip, {e: "yes" for e in a_ids}))

        # ---- V
        in_v = vabl is None or iid in vabl or (var == "original" and clip in vabl_clips)
        if in_v:
            if var in V_FAIL:
                gtv = {e: ("no" if e == broken else "yes") for e in all_ids} if broken else {"__item__": "no"}
                rows.append(row("hdepic", iid, "V", SHORT[var], clip, gtv))
            elif var == "original":
                rows.append(row("hdepic", iid, "V", "original", clip, {e: "yes" for e in all_ids}))
            else:                                     # frames identical to the original: V PASS, false-alarm check only
                rows.append(row("hdepic", iid, "V", SHORT.get(var, var), clip, {e: "yes" for e in all_ids}, eval_only=True))

        # ---- AVB: only events stage 1 actually judged
        if var in AVB_FAIL or var == "original":
            judged, _ = TS.stage1_lookup(iid, TS.AVB, None)
            if judged:
                lab = "yes" if var == "original" else "no"
                rows.append(row("hdepic", iid, "AVB", SHORT[var], clip, {e["event_id"]: lab for e in judged}))
            else:
                skipped["AVB_no_stage1"] += 1

        # ---- TC-Rel: one label per item; only items stage 1 judged (A and V passed there)
        if var in ("fail_order_swap", "original"):
            judged, _ = TS.stage1_lookup(iid, TS.TCR, None)
            if judged:
                rows.append(row("hdepic", iid, "TCR", SHORT[var], clip, {"__item__": "yes" if var == "original" else "no"}))
            else:
                skipped["TCR_no_stage1"] += 1
        # ---- TC-Cnt: per event (observed_count == required_count); broken event -> no
        if var in ("fail_count_off", "original"):
            judged, _ = TS.stage1_lookup(iid, TS.TCC, None)
            if judged:
                jids = [e["event_id"] for e in judged]
                if var == "original":
                    gtc = {e: "yes" for e in jids}
                elif broken in jids:
                    gtc = {e: ("no" if e == broken else "yes") for e in jids}
                else:
                    gtc = {"__item__": "no"}; skipped["TCC_item_level"] += 1
                rows.append(row("hdepic", iid, "TCC", SHORT[var], clip, gtc))
            else:
                skipped["TCC_no_stage1"] += 1

    write(rows, a.out)
    print("skipped / notes:", dict(skipped))


# ---------------------------------------------------------------- 220 generated (LTX / MOVA)
LAB = {"clapping_hands": "clap", "slapping_the_thigh": "slap", "snapping_fingers": "snap"}


def event_key_candidates(meta):
    """judge event_id -> list of possible gt event_keys, in priority order.
    1. the prompt event's source_id (same key system as gt_event_majority: speech, sounding_action, silent_action_2 ...)
    2. its aliases, 3. label-based keys (clap / slap / snap, open_palm, speech_<word>), 4. kind[_rank] recomputed."""
    structs = scoring(meta)
    cnt, out = Counter(), {}
    for s in structs:
        kind = str(s.get("kind", ""))
        cnt[kind] += 1
        lab = str(s.get("label", ""))
        cands = [str(s.get("source_id", ""))] + [str(a) for a in s.get("aliases", []) or []]
        cands += [LAB.get(lab, lab), f"speech_{lab}", kind if cnt[kind] == 1 else f"{kind}_{cnt[kind]}"]
        out[s["event_id"]] = [c for c in cands if c]
    return out


def make_gen(a):
    items = NE.load_prompt_items(Path(a.prompt_json))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    g = pd.read_csv(a.gt_event_csv)
    g = g[g["model"].astype(str) == a.model]
    g["stem"] = g.video_id.astype(str).str.replace(rf"__{re.escape(a.model)}$", "", regex=True)
    s1 = TS.load_stage1(a.stage1_csv)
    rows, skipped = [], Counter()
    for iid in s1.index:
        if iid not in metas:
            skipped["no_meta"] += 1; continue
        meta = metas[iid]
        gi = g[g.stem == str(iid)]
        if gi.empty:
            skipped["no_gt_video"] += 1; continue
        if gi.video_file.nunique() > 1:
            skipped["multi_video_first_used"] += 1
            gi = gi[gi.video_file == sorted(gi.video_file.unique())[0]]
        cands = event_key_candidates(meta)
        by_key = {str(r.event_key): r for _, r in gi.iterrows()}
        structs = scoring(meta)
        for ax in ("A", "V", "AVB"):
            gt = {}
            for eid in ids_for(ax, structs):
                r = next((by_key[c] for c in cands[eid] if c in by_key), None)
                if r is None:
                    skipped[f"{ax}_key_unmatched"] += 1; continue
                lab = str(r[ax]).upper()
                if lab not in ("PASS", "FAIL"):
                    continue                           # TIE / empty
                if ax == "AVB" and not (str(r["A"]).upper() == "PASS" and str(r["V"]).upper() == "PASS"):
                    skipped["AVB_parent_fail_dropped"] += 1   # human AVB FAIL inherited from A / V: not a binding failure
                    continue
                gt[eid] = "yes" if lab == "PASS" else "no"
            if gt:
                rows.append(row(a.source, iid, ax, "generated", str(iid), gt))
    if a.gt_video_csv:
        rows += gen_tc_rows(a, s1.index, skipped)
    write(rows, a.out)
    print("skipped / notes:", dict(skipped))


def _find_col(cols, pats):
    for pat in pats:
        for c in cols:
            if re.search(pat, c, re.I):
                return c
    return None


def gen_tc_rows(a, item_ids, skipped):
    """220 TC-Rel / TC-Cnt: video-level human labels from gt_video.csv -> item-level GT ({"__item__": yes/no})."""
    v = pd.read_csv(a.gt_video_csv)
    mcol = _find_col(v.columns, [r"^model$"])
    if mcol:
        v = v[v[mcol].astype(str) == a.model]
    vid = _find_col(v.columns, [r"^video_id$", r"^video_file$", r"^item_id$", r"^video$"])
    rel = _find_col(v.columns, [r"tc.?rel", r"relation"])
    cnt = _find_col(v.columns, [r"tc.?cnt", r"tc.?count", r"count"])
    if not (vid and rel and cnt):
        sys.exit(f"gt_video.csv: could not find video / TC-Rel / TC-Cnt columns among {list(v.columns)}; "
                 f"found video={vid} rel={rel} cnt={cnt}")
    v["stem"] = v[vid].astype(str).str.replace(rf"__{re.escape(a.model)}$", "", regex=True).str.replace(r"_*v\d+_raw(\.mp4)?$", "", regex=True)
    print(f"[gen TC] columns: video={vid} rel={rel} cnt={cnt} model_col={mcol}")
    rows = []
    for iid in item_ids:
        g = v[v.stem == str(iid)]
        if g.empty:
            skipped["TC_no_gt_video"] += 1; continue
        r = g.iloc[0]
        parents = [_find_col(v.columns, [rf"^{p}_gt$", rf"^{p}$"]) for p in ("A", "V", "AVB")]
        if any(str(r[c]).upper() != "PASS" for c in parents if c):
            skipped["TC_parent_fail_dropped"] += 1     # TC FAIL inherited from A / V / AVB: not a temporal failure
            continue
        for ax, col in (("TCR", rel), ("TCC", cnt)):
            lab = str(r[col]).upper()
            if lab not in ("PASS", "FAIL"):
                continue
            rows.append(row(a.source, iid, ax, "generated", str(iid), {"__item__": "yes" if lab == "PASS" else "no"}))
    return rows


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
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hdepic")
    h.add_argument("--prompt-json", required=True); h.add_argument("--gt-csv", required=True); h.add_argument("--stage1-dir", required=True)
    h.add_argument("--vabl-ids", default=None, help="text file with the 326 vabl item_ids (one per line); omit = all")
    h.add_argument("--out", required=True)
    gn = sub.add_parser("gen")
    gn.add_argument("--prompt-json", required=True); gn.add_argument("--gt-event-csv", required=True)
    gn.add_argument("--stage1-csv", required=True); gn.add_argument("--model", required=True, help="LTX_2p3 or MOVA (model column)")
    gn.add_argument("--source", required=True, choices=["ltx", "mova"]); gn.add_argument("--out", required=True)
    gn.add_argument("--gt-video-csv", default=None, help="gt_video.csv with video-level TC-Rel / TC-Cnt human labels (adds TCR/TCC rows)")
    a = ap.parse_args()
    {"hdepic": make_hdepic, "gen": make_gen}[a.cmd](a)
