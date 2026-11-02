#!/usr/bin/env python3
"""No API calls. HD-EPIC AVB early vs late shift on the SAME windows (same clip, same shift size, opposite direction), paired.
Video-only runs, Gemini 3.1 and 3.6. A window counts only if AVB was judged (not gated) for both variants.
  python gepa_stage2/paired_shift.py"""
import glob, re, sys
import pandas as pd
E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
RUNS = {"3.1": f"{E}/results/hdepic_medium_multi_baseline", "3.6": f"{E}/results/hdepic_medium_multi_baseline_g36"}
AVB = "audio_visual_binding"
SKIP = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)
lab = lambda x: str(x).strip().lower()

def load(p):
    return pd.concat(pd.read_csv(f, engine="python") for f in sorted(glob.glob(f"{p}/shard?.csv"))).drop_duplicates("item_id", keep="last").set_index("item_id")

for name, p in RUNS.items():
    df = load(p)
    wins = sorted({i[:-len("_AVBearly")] for i in df.index if i.endswith("_AVBearly")})
    rows = []
    for w in wins:
        e, l = w + "_AVBearly", w + "_AVBlate"
        if e not in df.index or l not in df.index: continue
        re_, rl = df.loc[e], df.loc[l]
        if SKIP.search(str(re_.get(AVB + "_reason", ""))) or SKIP.search(str(rl.get(AVB + "_reason", ""))): continue
        if lab(re_[AVB]) not in ("yes", "no") or lab(rl[AVB]) not in ("yes", "no"): continue
        rows.append((lab(re_[AVB]) == "no", lab(rl[AVB]) == "no"))
    n = len(rows); both = sum(a and b for a, b in rows); eo = sum(a and not b for a, b in rows); lo = sum(b and not a for a, b in rows)
    print(f"{name}: paired windows {n} | early caught {sum(a for a, _ in rows)/n:.2f}  late caught {sum(b for _, b in rows)/n:.2f} | "
          f"both {both}  early only {eo}  late only {lo}  neither {n-both-eo-lo}")
    print(f"      among windows where late is caught, early also caught: {both/max(both+lo,1):.2f}; McNemar-style discordant pairs {eo} vs {lo}")
