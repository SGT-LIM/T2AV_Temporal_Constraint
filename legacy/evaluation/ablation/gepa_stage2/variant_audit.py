#!/usr/bin/env python3
"""What does each HD-EPIC variant actually change? (2026-10-23, after absent_sound turned out to be prompt-only)
For N clips per variant: compare the variant mp4 with the same clip's _pass mp4 (audio bytes, video bytes, duration),
and diff the prompt events (added / removed / changed fields). No API calls.
  python gepa_stage2/variant_audit.py --n 5 | tee gepa_stage2/runs/variant_audit.txt"""
import argparse, glob, hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "gepa_stage2"); sys.path.insert(0, ".")
import new_eval as NE

BASE = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
SUF = ["A", "mute", "AVBearly", "AVBlate", "TCC", "TCR", "Vhand", "Vnoun"]

def mp4(iid):
    f = glob.glob(f"{BASE}/hdepic_medium_shard*/{iid}/{iid}_v1_raw.mp4")
    return f[0] if f else None

def stream_md5(f, kind):
    args = ["-vn", "-ac", "1", "-ar", "16000", "-f", "s16le"] if kind == "a" else ["-an", "-vf", "scale=64:36", "-f", "rawvideo", "-pix_fmt", "gray"]
    out = subprocess.run(["ffmpeg", "-v", "quiet", "-i", f, *args, "-"], capture_output=True).stdout
    return hashlib.md5(out).hexdigest(), len(out)

def ev_key(e):
    return e.get("source_id") or e.get("label")

def diff_events(ea, ep):
    da, dp = {ev_key(e): e for e in ea}, {ev_key(e): e for e in ep}
    out = []
    for k in da.keys() - dp.keys():
        out.append(f"+ added {k}: {da[k].get('label')} | {str(da[k].get('definition',''))[:110]}")
    for k in dp.keys() - da.keys():
        out.append(f"- removed {k}: {dp[k].get('label')}")
    for k in da.keys() & dp.keys():
        for fld in ("label", "definition", "count", "index", "kind"):
            if da[k].get(fld) != dp[k].get(fld):
                out.append(f"~ {k}.{fld}: {str(dp[k].get(fld))[:70]!r} -> {str(da[k].get(fld))[:70]!r}")
    order_a = [ev_key(e) for e in sorted(ea, key=lambda e: e.get("index", 0))]
    order_p = [ev_key(e) for e in sorted(ep, key=lambda e: e.get("index", 0))]
    if [k for k in order_a if k in dp] != [k for k in order_p if k in da]:
        out.append(f"~ order: {order_p} -> {order_a}")
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=5); a = ap.parse_args()
    src = json.load(open("gepa_stage2/sources.json"))
    items = NE.load_prompt_items(Path(src["hdepic"]["prompt_json"]))
    metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    ids = sorted(k for k in metas if k.startswith("hdepic_"))
    for suf in SUF:
        cand = [i for i in ids if i.endswith("_" + suf) and mp4(i) and mp4(i[: -len(suf)] + "pass")][: a.n]
        print(f"\n################ _{suf}  ({len(cand)} clips)")
        same_a = same_v = 0
        for iid in cand:
            pid = iid[: -len(suf)] + "pass"
            fa, fp = mp4(iid), mp4(pid)
            (ha, la), (hpa, lpa) = stream_md5(fa, "a"), stream_md5(fp, "a")
            (hv, lv), (hpv, lpv) = stream_md5(fa, "v"), stream_md5(fp, "v")
            same_a += ha == hpa; same_v += hv == hpv
            print(f"== {iid.replace('hdepic_','')}  audio {'SAME' if ha == hpa else 'DIFF'} ({la} vs {lpa} B)  video {'SAME' if hv == hpv else 'DIFF'} ({lv} vs {lpv} B)")
            for line in diff_events(metas[iid]["events"], metas[pid]["events"]) or ["(prompt events identical)"]:
                print("    " + line)
        print(f"-- _{suf}: audio same {same_a}/{len(cand)}, video same {same_v}/{len(cand)}")

if __name__ == "__main__":
    main()
