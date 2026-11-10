#!/usr/bin/env python3
"""MOVA390 (prolific_mova_390 @ 650fe5ae): tool outputs and three conditions only — media only (row 1), one call plus tools (row 2),
two-stage always shown (all axes). NO gated condition (original or redesigned), NO threshold variants, NO caption check.
Same settings as the 2k_25 batch (chain_gen2k25_1104.sh, gen2k25_stage2_1104.py); in-process registration only, no existing module edited.
  source tag m390 / evidence set mova390 / model MOVA / always-shown stage-2 set M4
  prompts  T2AV_data/gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json (the adapter items the GT was built from)
  videos   T2AV_data/gen_prolific_mova390_1108_rev650fe5ae/videos/<item>/<item>_v1_raw.mp4 -> symlinks to
           T2AV_data/videos_repo/main_videos/MOVA/<item>/<file>.mp4 (canonical files untouched)
  tools    Whisper large-v3-turbo + FLAM records -> T2AV_data/tools/gen_evidence_1030/mova390/ (gen_evidence_1030 audio, generated settings)
           run_agentic_eval audio-evidence cache (gen_evidence_1030 cache, generated settings, no hop)
           AVoCaDO captions fps 8 plain greedy -> evaluation/ablation/captions/avocado_fps8_plain_v3_mova390.json
           Synchformer, anchor-time window from row 1 -> T2AV_data/tools/synchformer_gen_1030/mova390/ (sync_gen_1030 run, same code)
  rows     row 1 eval_results/multi_agent/mova390_row1_anchor_g36_1108, row 2 eval_results/multi_agent/mova390_row2_onecall_sync_g36_1108
           always shown: obs_judge_1028 rows set M4 (A: Whisper + FLAM text; V: caption; AVB / TR / TC: all four), calls/gen_tool_text/M4__*
  python gepa_stage2/mova390_pipeline_1108.py links | audio | cache | captions | sync | synctexts | rows4 | run4 | status
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, glob, json, os, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "Tool_Use"))
D = Path((_tp.DATA + "/gen_prolific_mova390_1108_rev650fe5ae"))
CANON = Path((_tp.DATA + "/videos_repo/main_videos/MOVA"))
M = Path((_tp.WORKSPACE + "/eval_results/multi_agent"))
R1, R2 = M / "mova390_row1_anchor_g36_1108", M / "mova390_row2_onecall_sync_g36_1108"
SRC, SETN, MODEL, S4 = "m390", "mova390", "MOVA", "M4"
SYO = Path((_tp.DATA + "/tools/synchformer_gen_1030")) / SETN
CAPF = HERE.parent / "captions/avocado_fps8_plain_v3_mova390.json"


def items():
    return {x["item_id"]: x for x in json.load(open(D / "prompts_mova390.json"))}


def mova390_videos():
    P = items()
    return [(i, MODEL, str((D / "videos" / i / f"{i}_v1_raw.mp4").resolve()), P[i]) for i in sorted(P) if (D / "videos" / i / f"{i}_v1_raw.mp4").exists()]


def register():
    import gen_evidence_1030 as GE, obs_judge_1028 as O, gen_stage2_1030 as G
    orig = GE.videos
    GE.videos = lambda which: mova390_videos() if which == SETN else orig(which)
    O.ANCHOR[SRC] = sorted(Path(p) for p in glob.glob(str(R1 / "mova390_shard*.csv")) if not p.endswith("_per_event.csv"))
    O.PROMPTS[SRC] = D / "prompts_mova390.json"
    G.CAP[SRC] = CAPF; G.MODEL[SRC] = MODEL; G.SETN[SRC] = SETN; G.BATCH[SRC] = f"{SETN}-{MODEL}"
    return GE, O, G


def stage_links(a):
    P = items(); n = made = 0
    for i in P:
        src = sorted((CANON / i).glob("*.mp4"))
        if len(src) != 1:
            print("NOT EXACTLY ONE CANONICAL VIDEO:", i, src); continue
        dst = D / "videos" / i / f"{i}_v1_raw.mp4"; dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            os.symlink(src[0].resolve(), dst); made += 1
        n += 1
    print(f"video links {n} (new {made})")


def stage_audio(a):
    GE, _, _ = register(); GE.stage_audio(argparse.Namespace(set=SETN, shard=a.shard, nshards=a.nshards))


def stage_cache(a):
    GE, _, _ = register(); GE.stage_cache(argparse.Namespace(set=SETN, shard=a.shard, nshards=a.nshards))


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
    if CAPF.exists():
        sys.exit(f"{CAPF} exists; not overwritten")
    json.dump(out, open(CAPF, "w"), indent=1)


def stage_sync(a):
    register()
    import sync_gen_1030 as SG
    SG.R1_BY_SET[SETN] = R1
    orig = SG.anchor_times
    SG.anchor_times = lambda prefix, iid: orig(SETN, iid)           # row 1 shards are named mova390_shard*.csv
    SG.stage_run(argparse.Namespace(set=SETN, shard=a.shard, nshards=a.nshards))


def stage_synctexts(a):
    """same section / line format as gen2k25_stage2_1104.stage_synctexts"""
    pe = pd.concat(pd.read_csv(f) for f in sorted(SYO.glob("per_event_shard*.csv")))
    sec, obs = {}, {}
    for iid, model, vid, item in mova390_videos():
        g = pe[pe.item_id == iid]
        if not len(g):
            continue
        multi = len(g) > 1; lines = []
        for r in g.itertuples():
            pre = f"'{r.label}': " if multi else ""
            lines.append(f"{pre}Synchformer, window around the action: no reading" if r.status != "ok" or pd.isna(r.offset) else
                         f"{pre}Synchformer, window around the action: most likely offset {float(r.offset):+.1f} s (positive = audio later than "
                         f"video), probability {float(r.prob):.2f}; probability of zero offset {float(r.p_offset0):.2f}")
        sec[str(Path(vid).resolve())] = ("Synchformer audio-visual synchronization (raw offset estimate):\n"
            "- Synchformer estimates the offset between the audio track and the video in a short window around each binding event's visible "
            "action. Offsets are on a 0.2 s grid; probabilities are the model's own, not correctness labels.\n" + "\n".join(f"- {l}" for l in lines))
        obs[iid] = "\n".join(lines)
    for name, d in (("sync_sections_mova390.json", sec), ("sync_obs_lines_mova390.json", obs)):
        if (SYO / name).exists():
            sys.exit(f"{name} exists; not overwritten")
        json.dump(d, open(SYO / name, "w"), indent=1)
    print(f"sections {len(sec)} (videos with a binding event and a reading record)")


def gt_rows():
    out = []
    for l in open(D / "gt_mova390.jsonl"):
        m = json.loads(l)
        out.append(dict(source=SRC, item_id=m["item_id"], axis=m["axis"], gt=m["gt"], uid=f"{SRC}|{m['item_id']}|{m['axis']}", variant=MODEL))
    return out


def text(G, axis, iid, obs):
    """always-shown observation text, as gen2k25_stage2_1104.text (gated=False)"""
    if axis == "A":
        return G.a_text(SRC, iid)
    if axis == "V":
        return G.v_text(SRC, iid)
    a = G.a_text(SRC, iid).replace("Observation (tool output):\n", "")
    c = G.caption(SRC, iid); s = obs.get(iid)
    parts = [p for p in (a, ("Dense caption written by a separate captioning model (AVoCaDO) that watched and listened to the same clip "
                             "without seeing the prompt:\n" + c.strip()) if c else "", s) if p]
    return "Observation (tool output):\n" + "\n\n".join(parts) if parts else ""


def stage_rows4(a):
    _, O, G = register()
    obs = json.load(open(SYO / "sync_obs_lines_mova390.json"))
    if any(r["set"] == S4 for r in O.jl(O.OUT / "rows.jsonl")):
        sys.exit(f"rows for set {S4} already exist; not rebuilt")
    new, miss = [], {}
    for r in gt_rows():
        t = text(G, r["axis"], r["item_id"], obs)
        if not t:
            miss[r["axis"]] = miss.get(r["axis"], 0) + 1; continue
        new += G.row(S4, r, t)
    G.add_rows(S4, new)
    print(f"{S4} rows: {len(new) // 2}; no tool text: {miss}")


def stage_run4(a):
    _, O, _ = register()
    O.stage_run(argparse.Namespace(cond="gen_tool_text", set=S4, model="gemini-3.6-flash", workers=a.workers, dry_run=a.dry_run))


def stage_status(a):
    st = dict(videos=len(mova390_videos()), whisper_flam_records=len(glob.glob(f"{_tp.DATA}/tools/gen_evidence_1030/{SETN}/*.json")),
              captions=CAPF.exists(), row1_shards=len(glob.glob(str(R1 / "mova390_shard*.csv"))) - len(glob.glob(str(R1 / "*_per_event.csv"))),
              sync_per_event=len(list(SYO.glob("per_event_shard*.csv"))) if SYO.exists() else 0, sync_texts=(SYO / "sync_sections_mova390.json").exists(),
              row2_shards=len(glob.glob(str(R2 / "mova390_shard*.csv"))) - len(glob.glob(str(R2 / "*_per_event.csv"))),
              M4_calls=len(glob.glob(str(HERE / f"runs/obsval_1028/calls/gen_tool_text/{S4}__*.json"))))
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["links", "audio", "cache", "captions", "sync", "synctexts", "rows4", "run4", "status"])
    ap.add_argument("--shard", type=int, default=0); ap.add_argument("--nshards", type=int, default=1); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", type=int, default=0)
    a = ap.parse_args(); globals()[f"stage_{a.stage}"](a)
