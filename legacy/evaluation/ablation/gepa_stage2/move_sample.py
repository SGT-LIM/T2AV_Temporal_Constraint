import csv, json, os, random, shutil
E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
OUT = f"{E}/move_check_2026-10-24"; os.makedirs(OUT, exist_ok=True)
rows = [r for r in csv.DictReader(open(f"{E}/hdepic_move_gt.csv")) if r["variant"] == "original"]
rng = random.Random(0)
hi = [r for r in rows if max(len(v) for v in json.loads(r["move_starts_sec"]).values()) >= 2]
lo = [r for r in rows if r not in hi]
pick = rng.sample(hi, 7) + rng.sample(lo, 3)
out = []
for i, r in enumerate(pick, 1):
    name = f"{i:02d}_{r['item_id'].replace('hdepicmove_','').replace('_pass','')}.mp4"
    shutil.copy(r["clip_path"], f"{OUT}/{name}")
    for obj, ts in json.loads(r["move_starts_sec"]).items():
        out.append(dict(no=i, file=name, object=obj, count=len(ts), move_start_sec=" ".join(f"{t:.1f}" for t in ts),
                        your_count="", note=""))
with open(f"{OUT}/checklist.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out: print(f"{o['no']:02d} {o['object']:28s} count {o['count']}  at {o['move_start_sec']} s")
print("->", OUT)
