#!/usr/bin/env python3
"""Collect clips for a human GT check of prompt-side variants (2026-10-23). No API calls.
Groups (judge = video-only run, hdepic_medium_multi_baseline):
  TCC  original judged FAIL (is the narration count wrong?)      | count_off judged PASS (is the +1 really wrong?)
  TCR  original judged FAIL (is the narrated order wrong?)       | order_swap judged PASS (is the swapped order really wrong?)
  V    original judged FAIL (is the narrated hand/object wrong?) | hand_swap judged PASS | noun_swap judged PASS
Copies mp4s into one folder with readable names and writes checklist.csv with what to check + the judge's reason.
  python gepa_stage2/collect_check.py --per-group 4"""
import argparse, glob, json, os, random, re, shutil, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, "gepa_stage2"); sys.path.insert(0, "."); sys.path.insert(0, ".")
import new_eval as NE

BASE = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
RUN = f"{BASE}/results/hdepic_medium_multi_baseline"
OUT = f"{BASE}/gt_check_2026-10-23"
AX = {"TCC": "temporal_count_satisfaction", "TCR": "temporal_relation_satisfaction", "V": "visual_event_correctness"}
SUF = {"original": "pass", "count_off": "TCC", "order_swap": "TCR", "hand_swap": "Vhand", "noun_swap": "Vnoun"}
GROUPS = [("TCC", "original", "no"), ("TCC", "count_off", "yes"),
          ("TCR", "original", "no"), ("TCR", "order_swap", "yes"),
          ("V", "original", "no"), ("V", "hand_swap", "yes"), ("V", "noun_swap", "yes")]

def mp4(iid):
    f = glob.glob(f"{BASE}/hdepic_medium_shard*/{iid}/{iid}_v1_raw.mp4")
    return f[0] if f else None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--per-group", type=int, default=4); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); rng = random.Random(a.seed)
    src = json.load(open("gepa_stage2/sources.json"))
    metas = NE.build_item_meta_map(NE.load_prompt_items(Path(src["hdepic"]["prompt_json"])), modality_filter=None, item_overrides=None, relative_only=False)
    fs = sorted(glob.glob(f"{RUN}/shard?.csv")) or [f"{RUN}/all.csv"]
    run = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
    os.makedirs(OUT, exist_ok=True)
    rows, k = [], 0
    for ax, var, judged in GROUPS:
        col = AX[ax]
        cand = [i for i in run.index if str(i).endswith("_" + SUF[var]) and str(run.loc[i, col]).lower() == judged and mp4(i)]
        rng.shuffle(cand)
        for iid in cand[: a.per_group]:
            k += 1
            evs = metas[iid]["events"]
            try:
                pe = json.loads(run.loc[iid, f"{col}_per_event"])
            except Exception:
                pe = []
            judge_bits = []
            for e in pe:
                if ax == "TCC":
                    judge_bits.append(f"{e.get('event_id')}: observed {e.get('observed_count')} | {str(e.get('reason',''))[:160]}")
                elif str(e.get("label", "")).lower() == "no" or ax == "V":
                    judge_bits.append(f"{e.get('event_id')}: {e.get('label')} | {str(e.get('reason',''))[:160]}")
            if ax == "TCR":
                judge_bits = [f"{run.loc[iid, col]} | {str(run.loc[iid].get(col + '_reason', ''))[:300]}"]
            if ax == "TCC":
                what = " ; ".join(f"[{e.get('label')}] required {e.get('count')}" for e in evs if e.get("count") not in (None, 1) or var == "count_off")
                what = what or " ; ".join(f"[{e.get('label')}] required {e.get('count')}" for e in evs)
                q = "Count each event. Does the clip match the required count?"
            elif ax == "TCR":
                what = " -> ".join(f"{e.get('index')}:{e.get('label')}" for e in sorted(evs, key=lambda e: e.get("index", 0)))
                q = "Do the events happen in this order?"
            else:
                what = " ; ".join(f"[{e.get('label')}] {str(e.get('definition',''))[:120]}" for e in evs if e.get("kind") != "sounding_action" or True)
                q = "Is every listed action done as written (hand, object)?"
            gt = "yes" if var == "original" else "no"
            name = f"{k:02d}_{ax}_{var}_GT-{gt}_judge-{judged}_{iid.replace('hdepic_','')}.mp4"
            shutil.copy(mp4(iid), f"{OUT}/{name}")
            rows.append(dict(no=k, file=name, axis=ax, variant=var, gt=gt, judge=judged, question=q, prompt_events=what,
                             judge_reason=" || ".join(judge_bits)[:600], your_answer_yes_no_unsure="", who_is_right_GT_or_judge="", note=""))
    pd.DataFrame(rows).to_csv(f"{OUT}/checklist.csv", index=False)
    print(len(rows), "clips ->", OUT)
    for r in rows:
        print(f"{r['no']:02d} {r['axis']:3s} {r['variant']:10s} GT {r['gt']:3s} judge {r['judge']:3s} | {r['prompt_events'][:110]}")

if __name__ == "__main__":
    main()
