#!/usr/bin/env python3
"""2k_25 batch (source g2k25): tool texts and stage 2 up to the gated condition, then stop (user 11/04). Text-only calls through
obs_judge_1028 (sets K4 = always shown, K5 = gated A rows whose text differs from K4) and a caption check (calls/vcap_check).
Tool routing (user 11/04), always shown: A = Whisper + FLAM; V = caption; AVB / TR / TC = all four (Whisper + FLAM lines, caption,
Synchformer lines) in one observation.
Gated: A = the FLAM-below-T_flam / Whisper-word gate of gen_stage2_1030.a_text(gated=True) (new K5 call when the text differs from K4);
V = the K4 call when the caption check says a GT event is contradicted; AVB = the K4 call when the pre-registered Synchformer rule fires
(|offset| >= 1.8 s and p >= .25 on the strongest binding-event reading); TR / TC = closed by gate (media only).
Stages (no GPU):
  captions   merge gen_prolific2k25_1104/gpu/captions_<k>.json -> captions/avocado_fps8_plain_v3_gen2k25.json (all 1,870 or exit 1)
  synctexts  Synchformer section / observation lines from synchformer_gen_1030/gen2k25/per_event_shard*.csv
  rows4gated K4 rows only where the gate opens (A: gated text = full text; V: caption check says contradicts; AVB: rule fires)
  rows4      all K4 rows (always shown; calls made for rows4gated are reused from the cache, same set / uid / text)
  vcheck [--workers]  caption check;  rows5  K5 rows;  score  rows 1 / 2 / 4 / 5 table (rows 2 / 4 empty until run)
Order (user 11/04): media only -> Synchformer -> gated (vcheck, rows4gated + K4, rows5 + K5, score) -> one call -> always shown.
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, glob, hashlib, json, os, sys, time
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import obs_judge_1028 as O
import gen_stage2_1030 as G
import rep_scoring as RS

SRC = "g2k25"
D = Path((_tp.DATA + "/gen_prolific2k25_1104"))
SYO = G.SYNC / "gen2k25"
CAPF = G.ABL / "captions/avocado_fps8_plain_v3_gen2k25.json"
R1 = O.R220 / "gen2k25_row1_anchor_g36_1104"
R2 = O.R220 / "gen2k25_row2_onecall_sync_g36_1104"
RULE = json.load(open((_tp.DATA + "/tools/synchformer_action_1030/PREREGISTERED_RULE.json")))
G.CAP[SRC] = CAPF; G.MODEL[SRC] = "LTX_2p3"; G.SETN[SRC] = "gen2k25"; G.BATCH[SRC] = "gen2k25-LTX_2p3"   # in-process registration only


def gt_rows():
    out = []
    for l in open(D / "gt_gen2k25.jsonl"):
        m = json.loads(l)
        out.append(dict(source=SRC, item_id=m["item_id"], axis=m["axis"], gt=m["gt"], uid=f"{SRC}|{m['item_id']}|{m['axis']}", variant="LTX_2p3"))
    return out


def stage_captions(a):
    out = {}
    for f in sorted(glob.glob(str(D / "gpu/captions_*.json"))):
        out.update(json.load(open(f)))
    ids = os.listdir(D / "videos")
    miss = [i for i in ids if f"{i}/{i}_v1_raw.mp4" not in out]
    bad = [k for k, v in out.items() if not (v.get("caption") or "").strip()]
    print(f"captions {len(out)}, videos {len(ids)}, missing {len(miss)}, empty {len(bad)}")
    if miss or bad:
        sys.exit(1)
    json.dump(out, open(CAPF, "w"), indent=1)


def stage_synctexts(a):
    pe = pd.concat(pd.read_csv(f) for f in sorted(SYO.glob("per_event_shard*.csv")))
    from gen_evidence_1030 import videos
    sec, obs = {}, {}
    for iid, model, vid, item in videos("gen2k25"):
        g = pe[pe.item_id == iid]
        if not len(g):
            continue
        multi = len(g) > 1
        lines = []
        for r in g.itertuples():
            pre = f"'{r.label}': " if multi else ""
            lines.append(f"{pre}Synchformer, window around the action: no reading" if r.status != "ok" or pd.isna(r.offset) else
                         f"{pre}Synchformer, window around the action: most likely offset {float(r.offset):+.1f} s (positive = audio later than "
                         f"video), probability {float(r.prob):.2f}; probability of zero offset {float(r.p_offset0):.2f}")
        sec[str(Path(vid).resolve())] = ("Synchformer audio-visual synchronization (raw offset estimate):\n"
            "- Synchformer estimates the offset between the audio track and the video in a short window around each binding event's visible "
            "action. Offsets are on a 0.2 s grid; probabilities are the model's own, not correctness labels.\n" + "\n".join(f"- {l}" for l in lines))
        obs[iid] = "\n".join(lines)
    json.dump(sec, open(SYO / "sync_sections_gen2k25.json", "w"), indent=1)
    json.dump(obs, open(SYO / "sync_obs_lines_gen2k25.json", "w"), indent=1)
    print(f"sections {len(sec)} (videos with a binding event and a reading record)")


_OBS = None


def sync_lines(iid):
    global _OBS
    if _OBS is None:
        _OBS = json.load(open(SYO / "sync_obs_lines_gen2k25.json"))
    return _OBS.get(iid)


def text(axis, iid, gated=False):
    if axis == "A":
        return G.a_text(SRC, iid, gated=gated)
    if axis == "V":
        return G.v_text(SRC, iid)
    a = G.a_text(SRC, iid).replace("Observation (tool output):\n", "")
    c = G.caption(SRC, iid)
    s = sync_lines(iid)
    parts = [p for p in (a, ("Dense caption written by a separate captioning model (AVoCaDO) that watched and listened to the same clip "
                             "without seeing the prompt:\n" + c.strip()) if c else "", s) if p]
    return "Observation (tool output):\n" + "\n\n".join(parts) if parts else ""


def fires(iid):
    if not hasattr(fires, "_pe"):
        pe = pd.concat(pd.read_csv(f) for f in sorted(SYO.glob("per_event_shard*.csv")))
        ok = pe[pe.status == "ok"].assign(a=lambda t: t.offset.abs())
        best = ok.sort_values(["a", "prob"], ascending=False).drop_duplicates("item_id")
        fires._pe = {r.item_id: bool(r.a >= RULE["T"] - 1e-9 and r.prob >= RULE["P"] - 1e-9) for r in best.itertuples()}
    return fires._pe.get(iid, False)


def stage_rows4(a):
    new, miss = [], {}
    for r in gt_rows():
        t = text(r["axis"], r["item_id"])
        if not t:
            miss[r["axis"]] = miss.get(r["axis"], 0) + 1
            continue
        new += G.row("K4", r, t)
    G.add_rows("K4", new)
    print(f"K4 rows: {len(new) // 2}; no tool text: {miss}")


def stage_rows4gated(a):
    new, n = [], {}
    for r in gt_rows():
        ax, iid = r["axis"], r["item_id"]
        if ax == "A":
            g4, g5 = text("A", iid), text("A", iid, gated=True)
            open_ = bool(g4 and g5 and g5 == g4)
        elif ax == "V":
            vc = G.vcheck(r["uid"]) or {}
            open_ = any(vc.get(e) == "contradicts" for e in r["gt"])
        elif ax == "AVB":
            open_ = fires(iid)
        else:
            open_ = False
        t = text(ax, iid) if open_ else ""
        if t:
            new += G.row("K4", r, t); n[ax] = n.get(ax, 0) + 1
    G.add_rows("K4", new)
    print(f"K4 gated-open rows: {len(new) // 2} {n}")


def stage_vcheck(a):
    from google import genai
    from concurrent.futures import ThreadPoolExecutor
    cache = O.OUT / "calls" / "vcap_check"
    items = {x["item_id"]: x for x in json.load(open(O.PROMPTS[SRC]))}
    todo = []
    for r in gt_rows():
        if r["axis"] != "V" or (cache / f"{r['uid']}.json").exists():
            continue
        c = G.caption(SRC, r["item_id"])
        if c is None:
            continue
        evs = items[r["item_id"]]["events"]; ids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(evs)}
        lines = [f"- {ids[e['id']]}: {e['definition']}" for e in evs if ids[e["id"]] in r["gt"]]
        user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() +
                "\n\nTarget visual events:\n" + "\n".join(lines) +
                "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
                "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
                "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
                "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
        todo.append((r, dict(system=G.VCHK_SYSTEM, user=user, media=None, schema=G.VCHK_SCHEMA, anchor=[])))
    print(f"[vcap_check] to do {len(todo)}", flush=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def one(x):
        r, c = x
        try:
            parsed, raw = O.call(client, a.model, c, {"obs": {}})
        except Exception as e:
            print(f"  [ERROR] {r['uid']}: {type(e).__name__}: {str(e)[:300]}", flush=True)
            return "error"
        json.dump(dict(status="ok", parsed=parsed, raw=raw, user=c["user"], user_md5=hashlib.md5(c["user"].encode()).hexdigest(),
                       uid=r["uid"], model=a.model, thinking="high", time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(cache / f"{r['uid']}.json", "w"))
        return "ok"
    n = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, todo)):
            n[s] = n.get(s, 0) + 1
            if i % 50 == 0:
                print(f"[vcap_check] {i + 1}/{len(todo)} {n}", flush=True)
    print(f"[DONE] vcap_check: {n}", flush=True)


def stage_rows5(a):
    new = []
    for r in gt_rows():
        if r["axis"] != "A":
            continue
        g4, g5 = text("A", r["item_id"]), text("A", r["item_id"], gated=True)
        if g4 and g5 and g5 != g4:
            new += G.row("K5", r, g5)
    G.add_rows("K5", new)
    print(f"K5 rows (A, gated text differs from K4): {len(new) // 2}")


def lab(set_name, r):
    f = O.OUT / "calls" / G.COND / f"{set_name}__{r['uid']}.json"
    if not f.exists():
        return ""
    rec = json.load(open(f))
    return O.obs_label(rec, r["axis"], r["gt"]) if rec["status"] == "ok" else ""


def stage_score(a):
    d1 = RS.load([f for f in sorted(glob.glob(str(R1 / "gen2k25_shard*.csv"))) if "per_event" not in f])
    f2 = [f for f in sorted(glob.glob(str(R2 / "gen2k25_shard*.csv"))) if "per_event" not in f]
    d2 = RS.load(f2) if f2 else None
    out = []
    for r in gt_rows():
        iid, ax, gt = r["item_id"], r["axis"], r["gt"]
        r1 = RS.row_label(d1, iid, ax, gt)
        r4 = lab("K4", r)
        r4f = r4 or r1
        if ax == "A":
            g5, g4 = text("A", iid, gated=True), text("A", iid)
            r5 = r1 if not g5 else (r4f if g5 == g4 else (lab("K5", r) or r1))
        elif ax == "V":
            vc = G.vcheck(r["uid"]) or {}
            r5 = r4f if any(vc.get(e) == "contradicts" for e in gt) else r1
        elif ax == "AVB":
            r5 = r4f if fires(iid) else r1
        else:
            r5 = r1
        out.append(dict(uid=r["uid"], axis=ax, y="no" if "no" in gt.values() else "yes", row1=r1,
                        row2=RS.row_label(d2, iid, ax, gt) if d2 is not None else "", row4=r4, row5=r5))
    Dd = pd.DataFrame(out)
    Dd.to_csv(O.OUT / "gen2k25_rows_1104.csv", index=False)
    tab = []
    for ax, g in Dd.groupby("axis", sort=False):
        for c in ("row1", "row2", "row4", "row5"):
            h = g[g[c].isin(["yes", "no"])]
            if not len(h):
                continue
            m = RS.metrics(h.y, h[c]); p = h[h.y == "yes"]
            tab.append(dict(axis=ax, cond=c, n=m["n"], n_fail=m["n_fail"], acc=round(m["acc"], 3), prec=round(m["prec"], 3), rec=round(m["rec"], 3),
                            FA=round(float((p[c] == "no").mean()), 3) if len(p) else None))
    T = pd.DataFrame(tab); T.to_csv(O.OUT / "gen2k25_table_1104.csv", index=False)
    print(T.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["captions", "synctexts", "rows4gated", "rows4", "vcheck", "rows5", "score"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--model", default="gemini-3.6-flash")
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
