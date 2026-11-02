#!/usr/bin/env python3
"""TCC items from HD-EPIC object-movement annotations (assoc_info.json). 2026-10-24.
relation_type = order_count (new_eval reads per-event counts only for order_count); ordered_events / expanded_sequence
come from the human-labelled movement start times. Judge with --axes V,TCC only (TCR GT left empty)."""
import argparse, csv, json, os, random, re, subprocess

def base(n):
    return re.sub(r"\d+$", "", n.strip().lower()).strip()

def event(eid, name, n):
    d = (f"The person moves the {name}: picks it up and sets it down somewhere else. Each pick-up-and-set-down counts as "
         f"one move. This action is judged visually; no specific sound is required.")
    ev = dict(id=eid, modality="silent_action", actor="person_A", action=f"move {name}", body_part="hand", definition=d, count=n)
    return ev, {k: v for k, v in ev.items() if k not in ("id", "count")}

def prompt_text(objs):
    parts = [f"moves the {nm} exactly {n} time{'s' if n != 1 else ''}" for nm, n in objs]
    s = "A person in a home kitchen " + (", and ".join(parts) if len(parts) <= 2 else ", ".join(parts[:-1]) + ", and " + parts[-1]) + "."
    return s + " Each pick-up-and-set-down of an object counts as one move. No other move of these objects happens in the clip."

def make_item(iid, objs, starts):
    """objs: [(name, count)], starts: [[true start times]] (len = true count). count may differ from len (FAIL)."""
    order = sorted(range(len(objs)), key=lambda i: starts[i][0])
    evs, content, eid_of = [], {}, {}
    for k, i in enumerate(order, 1):
        nm, n = objs[i]
        e, c = event(f"e{k}_move", nm, n); evs.append(e); content[e["id"]] = c; eid_of[i] = e["id"]
    timeline, tail = [], []
    for i, (nm, n) in enumerate(objs):
        ts = starts[i]
        if n <= len(ts):
            timeline += [(t, eid_of[i]) for t in ts[:n]]
        else:
            timeline += [(t, eid_of[i]) for t in ts]
            tail += [eid_of[i]] * (n - len(ts))          # extra claimed moves go at the end (like existing count_off)
    expanded = [e for _, e in sorted(timeline)] + tail
    return dict(item_id=iid, canonical_item_id="real_hdepic_move_count", modality_combination="Action (silent)",
        subjects=[dict(id="person_A", description="one person cooking in a home kitchen, filmed from a head-mounted camera",
                       initial_pose="standing at the kitchen counter",
                       visibility="hands and manipulated objects visible; face not visible (egocentric view)")],
        prompt=prompt_text([objs[i] for i in order]), events=evs, content=content,
        temporal_constraint=dict(relation_type="order_count", task_type="count", count_constrained=True, n_events=len(evs),
                                 timing_type="relative",
                                 value=dict(events=[e["id"] for e in evs], ordered_events=[e["id"] for e in evs],
                                            expanded_sequence=expanded, event_counts={e["id"]: e["count"] for e in evs})))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", required=True); ap.add_argument("--assoc", required=True)
    ap.add_argument("--videos", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--n-windows", type=int, default=300); ap.add_argument("--max-objects", type=int, default=3)
    ap.add_argument("--win", type=float, default=25.0); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); rng = random.Random(a.seed)
    W = json.load(open(a.windows)); A = json.load(open(a.assoc))
    hi = [w for w in W if max(w["objects"].values()) >= 2]
    lo = [w for w in W if max(w["objects"].values()) == 1 and len(w["objects"]) >= 2]
    rng.shuffle(lo)
    sel = hi + lo[: max(0, a.n_windows - len(hi))]
    print(f"windows: max N>=2 {len(hi)}, N=1 with >=2 objects {len(lo)} -> selected {len(sel)}")
    shard = os.path.join(a.out, "hdepic_move_shard0"); os.makedirs(shard, exist_ok=True)
    clipdir = os.path.join(a.out, "..", "hdepic", "clips_move"); os.makedirs(clipdir, exist_ok=True)
    items, gt_rows, bad = [], [], 0
    for w in sel:
        v, t0 = w["video"], float(w["t0"]); t1 = t0 + a.win
        objs = sorted(w["objects"].items(), key=lambda x: (-x[1], x[0]))[: a.max_objects]
        starts = []
        for nm, n in objs:
            ts = sorted(t["time_segment"][0] for o in A[v].values() if base(o["name"]) == nm for t in o["tracks"]
                        if t["time_segment"][0] >= t0 and t["time_segment"][1] <= t1)
            starts.append([round(t - t0, 2) for t in ts])
        if any(len(s) != n for s, (_, n) in zip(starts, objs)):
            bad += 1; continue                                 # window file and assoc disagree -> skip
        key = f"{v}_{int(round(t0 * 1000)):07d}"
        clip = os.path.abspath(os.path.join(clipdir, f"{key}_move.mp4"))
        if not a.dry_run and not os.path.exists(clip):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{a.win:.3f}",
                            "-i", os.path.join(a.videos, f"{v}.mp4"), "-c:v", "libx264", "-preset", "veryfast",
                            "-c:a", "aac", "-movflags", "+faststart", clip], check=True)
        pid = f"hdepicmove_{key}_pass"
        items.append(make_item(pid, objs, starts))
        k = rng.randrange(len(objs)); nm, n = objs[k]
        new = n - 1 if (n >= 2 and rng.random() < 0.5) else n + 1
        fobjs = list(objs); fobjs[k] = (nm, new)
        fid = f"hdepicmove_{key}_TCC"
        fitem = make_item(fid, fobjs, starts); items.append(fitem)
        bidx_f = [e["action"] for e in fitem["events"]].index(f"move {nm}")
        for iid, var, tcc, bidx in ((pid, "original", "PASS", ""), (fid, "count_off", "FAIL", bidx_f)):
            if not a.dry_run:
                d = os.path.join(shard, iid); os.makedirs(d, exist_ok=True)
                dst = os.path.join(d, f"{iid}_v1_raw.mp4")
                if not os.path.exists(dst): os.symlink(clip, dst)
            gt_rows.append(dict(item_id=iid, source="hdepic_move", variant=var, clip_path=clip, broken_event_idx=bidx,
                                broken_event_kind="silent_action" if bidx != "" else "",
                                audio_event_correctness="PASS", visual_event_correctness="PASS", audio_visual_binding="PASS",
                                temporal_relation_satisfaction="", temporal_count_satisfaction=tcc,
                                move_starts_sec=json.dumps({nm: s for (nm, _), s in zip(objs, starts)})))
    json.dump(items, open(os.path.join(a.out, "hdepic_move_prompts.json"), "w"), indent=1)
    with open(os.path.join(a.out, "hdepic_move_gt.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(gt_rows[0])); wr.writeheader(); wr.writerows(gt_rows)
    ns = [n for it in items if it["item_id"].endswith("_pass") for n in it["temporal_constraint"]["value"]["event_counts"].values()]
    print(f"items {len(items)} (skipped {bad} windows) | per-object N in PASS: " + ", ".join(f"{n}:{ns.count(n)}" for n in sorted(set(ns))))
    print("example:", items[0]["prompt"], "| expanded:", items[0]["temporal_constraint"]["value"]["expanded_sequence"])

if __name__ == "__main__":
    main()
