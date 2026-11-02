#!/usr/bin/env python3
"""One short card per clip in gt_check_2026-10-23: only what to look at (2026-10-23). No API calls.
Variant clips: the event(s) changed vs the same clip's _pass prompt. Original clips judged FAIL: the event(s) the judge flagged.
  python gepa_stage2/check_cards.py | tee /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/gt_check_2026-10-23/cards.txt"""
import glob, json, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, "gepa_stage2"); sys.path.insert(0, ".")
import new_eval as NE

BASE = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
OUT = f"{BASE}/gt_check_2026-10-23"
RUN = f"{BASE}/results/hdepic_medium_multi_baseline"
AX = {"TCC": "temporal_count_satisfaction", "TCR": "temporal_relation_satisfaction", "V": "visual_event_correctness"}
SUF = {"count_off": "TCC", "order_swap": "TCR", "hand_swap": "Vhand", "noun_swap": "Vnoun"}

src = json.load(open("gepa_stage2/sources.json"))
metas = NE.build_item_meta_map(NE.load_prompt_items(Path(src["hdepic"]["prompt_json"])), modality_filter=None, item_overrides=None, relative_only=False)
fs = sorted(glob.glob(f"{RUN}/shard?.csv")) or [f"{RUN}/all.csv"]
run = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
ck = pd.read_csv(f"{OUT}/checklist.csv")

def key(e): return e.get("source_id") or e.get("label")
def hand(d): m = re.search(r"with the (left|right) hand", str(d)); return m.group(1) if m else "(no hand)"
def short(d): return re.sub(r"\s*This action is judged visually; no specific sound is required\.", "", str(d)).strip()

def per_event(iid, col):
    try: return {e.get("event_id"): e for e in json.loads(run.loc[iid, f"{col}_per_event"])}
    except Exception: return {}

cards = []
for _, r in ck.iterrows():
    iid = "hdepic_" + re.sub(r"^\d+_[A-Z]+_[a-z_]+_GT-\w+_judge-\w+_", "", r["file"]).replace(".mp4", "")
    ax, var = r["axis"], r["variant"]
    ev = sorted(metas[iid]["events"], key=lambda e: e.get("index", 0))
    lines = []
    if var == "original":
        pe = per_event(iid, AX[ax])
        if ax == "TCC":
            for i, e in enumerate(ev, 1):
                j = pe.get(f"event_{i}", {})
                oc, rc = j.get("observed_count"), e.get("count")
                if oc is not None and rc is not None and str(oc) != str(rc):
                    lines.append(f"COUNT '{e['label']}': prompt says {rc}, judge counted {oc}.  -> count it yourself")
                    lines.append(f"   judge: {str(j.get('reason',''))[:200]}")
        elif ax == "TCR":
            lines.append("ORDER (prompt): " + "  ->  ".join(e["label"] for e in ev))
            lines.append(f"   judge said NO: {str(run.loc[iid].get(AX[ax] + '_reason', ''))[:260]}")
        else:
            for i, e in enumerate(ev, 1):
                j = pe.get(f"event_{i}", {})
                if str(j.get("label", "")).lower() == "no":
                    lines.append(f"ACTION '{e['label']}': {short(e.get('definition'))}  -> is it done like this?")
                    lines.append(f"   judge: {str(j.get('reason',''))[:200]}")
    else:
        pid = iid[: -len(SUF[var])] + "pass"
        evp = sorted(metas[pid]["events"], key=lambda e: e.get("index", 0))
        dp = {key(e): e for e in evp}
        if var == "count_off":
            for e in ev:
                p = dp.get(key(e))
                if p and p.get("count") != e.get("count"):
                    lines.append(f"COUNT '{e['label']}': real (narration) {p.get('count')}, prompt changed to {e.get('count')}.  -> how many times does it happen?")
        elif var == "order_swap":
            lines.append("REAL order:    " + "  ->  ".join(e["label"] for e in evp))
            lines.append("PROMPT order:  " + "  ->  ".join(e["label"] for e in ev))
            moved = [e["label"] for e, p in zip(ev, evp) if key(e) != key(p)]
            lines.append(f"   swapped: {' <-> '.join(moved)}  -> which one happens first? or at the same time?")
        else:
            for e in ev:
                p = dp.get(key(e))
                if p is None:
                    lines.append(f"ACTION (new) '{e['label']}': {short(e.get('definition'))}")
                elif p.get("definition") != e.get("definition") or p.get("label") != e.get("label"):
                    if var == "hand_swap":
                        lines.append(f"HAND '{e['label']}': real {hand(p.get('definition'))}, prompt changed to {hand(e.get('definition'))}.  -> which hand?")
                    else:
                        lines.append(f"OBJECT: real '{p['label']}' -> prompt '{e['label']}'.  -> which object is it?")
    cards.append(f"[{r['no']:02d}] {ax} {var}  (GT {r['gt']}, judge {r['judge']})  {r['file']}\n    " + ("\n    ".join(lines) or "(could not locate the changed / flagged event, look at full prompt in checklist.csv)"))

print("\n\n".join(cards))
