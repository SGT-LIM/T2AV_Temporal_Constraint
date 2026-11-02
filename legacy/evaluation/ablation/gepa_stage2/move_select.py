import json, re, collections
AN = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/annotations"
A = json.load(open(f"{AN}/data/scene-and-object-movements/assoc_info.json"))
GAP, WIN = 1.1, 25.0
BAD = re.compile(r"\b(half|first|second|third|fourth|fifth|piece|part|left|right)\b", re.I)
def base(n): return re.sub(r"\d+$", "", n.strip().lower()).strip()
def head(n): return n.split()[-1] if n.split() else n
def clash(a, b):
    return a != b and (a in b or b in a or head(a) == head(b))

def windows(v):
    objs = A[v]
    segs = {oid: sorted(t["time_segment"] for t in o["tracks"]) for oid, o in objs.items()}
    names = {oid: base(o["name"]) for oid, o in objs.items()}
    out, why = [], collections.Counter()
    for t0 in sorted({s for ss in segs.values() for s, _ in ss}):
        w0 = max(0.0, t0 - 2.0); w1 = w0 + WIN
        moving = {oid for oid, ss in segs.items() if any(s < w1 and e > w0 for s, e in ss)}
        mnames = [names[o] for o in moving]
        ok = {}
        for oid in moving:
            nm, ss = names[oid], segs[oid]
            inside = [(s, e) for s, e in ss if s >= w0 and e <= w1]
            if not nm or BAD.search(nm) or not inside: continue
            if any((s < w0 < e) or (s < w1 < e) for s, e in ss): continue
            if mnames.count(nm) > 1: why["same_name"] += 1; continue
            if any(clash(nm, m) for m in mnames): why["name_overlap"] += 1; continue
            if any(b[0] - a[1] < GAP for a, b in zip(inside, inside[1:])): continue
            ok[nm] = len(inside)
        if ok: out.append((w0, w1, ok))
    return out, why

def score(ok): return (len(ok) >= 2, max(ok.values()) >= 2, len(ok), sum(ok.values()))
picked, why_all = [], collections.Counter()
for v in [v for v in A if v.startswith(("P01", "P02"))]:
    ws, why = windows(v); why_all += why
    taken = []
    for w0, w1, ok in sorted(ws, key=lambda x: score(x[2]), reverse=True):
        if all(w1 <= a or w0 >= b for a, b in taken):
            taken.append((w0, w1)); picked.append((v, w0, ok))
two = sum(1 for _, _, ok in picked if len(ok) >= 2)
nmax = collections.Counter(max(ok.values()) for _, _, ok in picked)
print(f"non-overlapping windows {len(picked)} | >=2 objects {two} | max-count {dict(sorted(nmax.items()))} | object drops {dict(why_all)}")
json.dump([dict(video=v, t0=round(w0, 2), win=WIN, objects=ok) for v, w0, ok in picked],
          open(f"{AN}/move_windows_25s.json", "w"), indent=1)
