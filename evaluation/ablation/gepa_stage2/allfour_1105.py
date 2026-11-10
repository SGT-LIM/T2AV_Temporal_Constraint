#!/usr/bin/env python3
"""Two-stage, always shown, with all four tools on AVB / TR / TC (user 11/04-05). Stage 1 unchanged (cached media-only anchors).
The stage-2 observation text of an AVB / TR / TC row is the one-call condition's own evidence block for the item, verbatim:
  audio section (Whisper + FLAM) + Synchformer section, then the caption section, exactly as agentic_common.build_axis_user_text
  inserts them for these axes (lines 694-697 / 710; routing agentic_common.AXIS_EVIDENCE_ROUTE, SYNC_AXES).
  Source of the block: the stored one-call prompt of the item (row 2 CSV user_prompt, any of the AVB / TCR / TCC prompts; the three
  axes receive the identical block). Items without a one-call run (P01/P02 option (ii) windows): the block is rebuilt with the same
  functions (new_eval audio-evidence cache, cache-only, hop 5; agentic_common.sync_section; caption_evidence external, plain) and
  the rebuild is checked to reproduce stored blocks exactly (stage "check").
Everything else of the stage-2 call is the current two-stage call (obs_judge_1028.build_call: generation prompt, axis criteria,
OBS_RULES, stage-1 block, observation; media-only system prompt; text only). New sets: HA4 (HD-EPIC), GA4 (generated).
A and V are not touched; the gated condition is not touched.
  python gepa_stage2/allfour_1105.py check | build | counts | diff | score
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import argparse, glob, json, os, re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import obs_judge_1028 as O
import hd_stage2_1101 as H
import gen_stage2_1030 as G
import hd_rows_score_1101 as HR
import gen_rows_score_1030 as GR
import rep_scoring as RS

E = Path((_tp.DATA + "/real_av/eval"))
R11 = E / "results/hdepic_main_row2_onecall_sync_g36_1101"
R10 = Path((_tp.WORKSPACE + "/eval_results/multi_agent/gen_row2_onecall_sync_g36_1030"))
ONECALL = {"hm_hdepic": [R11 / f"hdepic_p12_shard{k}.csv" for k in range(3)], "hm_hdmove": [R11 / f"hdmove_p12_shard{k}.csv" for k in range(2)],
           "hm_p3p9": [R11 / f"p3p9_shard{k}.csv" for k in range(24)],
           **{s: [f for f in sorted(R10.glob(f"{p}_shard*.csv")) if "per_event" not in f.name] for s, p in (("g220ltx", "LTX_2p3"), ("g220mova", "MOVA"), ("g149", "gen149"))}}
SETOF = lambda src: "GA4" if src.startswith("g") else "HA4"
AXK = {"AVB": "audio_visual_binding", "TCR": "temporal_relation_satisfaction", "TCC": "temporal_count_satisfaction"}
GROUP = {"hm_hdepic": "P01/P02", "hm_p12new": "P01/P02", "hm_hdmove": "P01/P02", "hm_p3p9": "P03-P09", "g220ltx": "220 LTX", "g220mova": "220 MOVA", "g149": "149 LTX"}
OUTD = O.OUT / "allfour_1105"


def rows():
    """main-table scope AVB / TCR / TCC rows: [dict(source, item_id, axis, gt, uid, variant)]"""
    out = []
    for r in H.gt_rows():
        if r["axis"] == "AVB" and r["source"] in ("hm_hdepic", "hm_p12new", "hm_p3p9"):
            out.append(dict(r))
    for g in HR.gt_all():
        if g["axis"] in ("TCR", "TCC"):
            src = {"hdepic_p12": "hm_hdepic", "hdmove_p12": "hm_hdmove", "p3p9": "hm_p3p9"}[g["set"]]
            out.append(dict(source=src, item_id=g["item_id"], axis=g["axis"], gt=g["gt"], variant=g["variant"]))
    for r in G.gt_rows():
        if r["axis"] == "AVB":
            out.append(dict(r))
    for g in GR.gt():
        if g["axis"] in ("TCR", "TCC"):
            src = {("220", "LTX_2p3"): "g220ltx", ("220", "MOVA"): "g220mova", ("149", "LTX_2p3"): "g149"}[(g["set"], g["model"])]
            out.append(dict(source=src, item_id=g["item_id"], axis=g["axis"], gt=g["gt"], variant="generated"))
    out = [r for r in out if r["source"] not in ("hm_hdepic", "hm_p12new", "hm_hdmove")]   # 11/05 (user): scope P03-P09 + generated; no P01/P02
    for r in out:
        r["uid"] = f"{r['source']}|{r['item_id']}|{r['axis']}"
    return out


_STORED = {}


def stored_block(src, iid):
    """the one-call evidence block for the item, cut verbatim from a stored AVB / TCR / TCC prompt; None if no one-call prompt."""
    if src not in ONECALL:
        return None
    if src not in _STORED:
        m = {}
        for f in ONECALL[src]:
            if not Path(f).exists():
                continue
            d = pd.read_csv(f, usecols=["item_id", "user_prompt"]).drop_duplicates("item_id", keep="last")
            for r in d.itertuples():
                try:
                    up = json.loads(r.user_prompt)
                except (TypeError, ValueError):
                    continue
                for ax in ("audio_visual_binding", "temporal_relation_satisfaction", "temporal_count_satisfaction"):
                    b = cut(up.get(ax) or "")
                    if b:
                        m[r.item_id] = b
                        break
        _STORED[src] = m
    return _STORED[src].get(iid)


def cut(user_text):
    import new_eval as NE
    i = user_text.find(NE.GUIDELINE_DEFINITIONS)
    j = user_text.find("Axis criteria for ")
    if i < 0 or j < 0:
        return None
    b = user_text[i + len(NE.GUIDELINE_DEFINITIONS):j].strip()
    return b or None


_SYNC = None


def rebuilt_block(src, iid):
    """rebuild with the one-call functions and settings of the source's one-call run (cache-only audio evidence):
    HD-EPIC: hop 5, Synchformer action-window sections, A100 fps 2 plain captions; generated: no hop, anchor-time Synchformer
    sections (sync_sections_oncall.json), fps 8 plain captions. Used for items without a stored one-call prompt."""
    import new_eval as NE
    import agentic_common as AC
    import caption_evidence as CE
    import run_agentic_eval as R
    global _SYNC
    os.environ["T2AV_AUDIO_EVIDENCE_CACHE_ONLY"] = "1"
    if _SYNC is None:
        _SYNC = {}
        for f in ((_tp.DATA + "/tools/synchformer_action_1030/hdepic_sync_sections_avb_syncOnly_1104.json"),
                  (_tp.DATA + "/tools/synchformer_gen_1030/sync_sections_oncall.json")):
            _SYNC.update(json.load(open(f)))
    os.environ["T2AV_SYNC_EVIDENCE_JSON"] = "set"
    AC._SYNC_MAP = _SYNC                                       # both families; keys are resolved video paths
    if src.startswith("g"):
        from gen_evidence_1030 import videos
        if not hasattr(rebuilt_block, "_vid"):
            rebuilt_block._vid = {}
            for s, m in (("220", None), ("149", None)):
                for i_, model, vid_, item in videos(s):
                    key = {("220", "LTX_2p3"): "g220ltx", ("220", "MOVA"): "g220mova", ("149", "LTX_2p3"): "g149"}[(s, model)]
                    rebuilt_block._vid[(key, i_)] = vid_
        vid = Path(rebuilt_block._vid.get((src, iid), ""))
        if not vid.name:
            return None, "no video"
        vroot = vid.parent.parent
        capf = G.CAP[src]; hop = []
    else:
        vroot = {"hm_hdepic": E / "hdepic_main_1101/hdepic_p12", "hm_p12new": E / "hdepic_main_1101/p12all_new", "hm_hdmove": E / "hdepic_main_1101/hdmove_p12",
                 "hm_p3p9": E / "hdepic_main_1101/p3p9"}[src]
        vid = vroot / iid / f"{iid}_v1_raw.mp4"
        capf = E / "hdepic_main_1101_captions" / ({"hm_hdepic": "hdepic_p12", "hm_p12new": "p12all_new", "hm_hdmove": "hdmove_p12", "hm_p3p9": "p3p9"}[src] + ".json")
        hop = ["--flam-hop-sec", "5"]
    meta = O.meta_for(src, iid)
    args = R.build_arg_parser().parse_args(["--prompt-json", "x", "--outputs-dir", "x", "--output-csv", "x", "--audio-evidence-mode", "whisper_flam"] + hop)
    kw = {k: getattr(args, k) for k in vars(args) if k.startswith(("whisper_", "clap_", "flam_"))}
    kw["audio_evidence_mode"] = "whisper_flam"
    audio, aerr = NE.build_audio_evidence_section(video_path=vid, item_meta=meta, **kw)
    if aerr and not audio:
        return None, f"audio: {aerr}"
    sync = AC.sync_section(vid)
    capsec, cerr = CE.build_caption_evidence_section(client=None, uploaded=None, video_path=vid, mode="external", caption_model="",
                                                     caption_style="plain", cache_dir=None, external_json=capf, videos_root=vroot)
    if cerr and not capsec:
        return None, f"caption: {cerr}"
    a = ((audio or "") + ("\n\n" + sync if sync else "")).strip()
    blocks = [x.strip() for x in (a, capsec or "") if x and x.strip()]
    return "\n\n".join(blocks), (aerr or "") + (cerr or "")


def block(src, iid):
    b = stored_block(src, iid)
    if b:
        return b, "stored one-call prompt"
    b, err = rebuilt_block(src, iid)
    return b, ("rebuilt" if b else f"missing ({err})")


V_INTRO = "Dense caption written by a separate captioning model (AVoCaDO) that watched and listened to the same clip without seeing the prompt:\n"
CAP_RE = re.compile(r"=== DENSE CAPTION EVIDENCE.*?\nDense caption:\n(.*?)\n=== END DENSE CAPTION EVIDENCE ===", re.S)


def v_style(b):
    """11/05 (user, option 2): the caption section in the V rows' short form (gen_stage2_1030.v_text intro + the same caption text);
    Whisper / FLAM / Synchformer sections unchanged. Returns (block, caption text or None)."""
    m = CAP_RE.search(b)
    if not m:
        return b, None
    cap = m.group(1).strip()
    return b[:m.start()] + V_INTRO + cap + b[m.end():], cap


def caption_file_text(src, iid):
    return (G.caption(src, iid) if src.startswith("g") else H.caption(src, iid)) or ""


def stage_check(a):
    """rebuild the block for stored items and compare (exact string equality)"""
    allr = rows()
    rs = [r for r in allr if r["source"] in ("hm_hdepic", "hm_p3p9") and r["axis"] == "AVB"][:40] + \
         [r for r in allr if r["source"] == "g220ltx" and r["axis"] == "AVB"][:15] + [r for r in allr if r["source"] == "g220mova" and r["axis"] == "AVB"][:15] + \
         [r for r in allr if r["source"] == "g149" and r["axis"] == "AVB"][:15]
    ok = bad = 0
    for r in rs:
        s = stored_block(r["source"], r["item_id"])
        b, _ = rebuilt_block(r["source"], r["item_id"])
        if s is None:
            continue
        if s == b:
            ok += 1
        else:
            bad += 1
            if bad == 1:
                import difflib
                print("\n".join(list(difflib.unified_diff(s.splitlines(), (b or "").splitlines(), "stored", "rebuilt", lineterm=""))[:40]))
    print(f"rebuild == stored: {ok}, differs: {bad}")


def stage_build(a):
    OUTD.mkdir(parents=True, exist_ok=True)
    new = {"HA4": [], "GA4": []}
    src_count, miss = {}, {}
    for r in rows():
        b, how = block(r["source"], r["item_id"])
        key = (GROUP[r["source"]], r["axis"])
        if not b:
            miss[key] = miss.get(key, 0) + 1
            continue
        src_count[how.split(" (")[0]] = src_count.get(how.split(" (")[0], 0) + 1
        b, cap = v_style(b)
        same = cap is not None and cap == caption_file_text(r["source"], r["item_id"]).strip()
        src_count["caption text == caption file" if same else ("no caption section" if cap is None else "caption text differs")] = \
            src_count.get("caption text == caption file" if same else ("no caption section" if cap is None else "caption text differs"), 0) + 1
        new[SETOF(r["source"])] += G.row(SETOF(r["source"]), r, "Observation (tool output):\n" + b)
    for s, rr in new.items():
        G.add_rows(s, rr)
    json.dump(dict(block_source=src_count, missing={f"{k[0]}|{k[1]}": v for k, v in miss.items()}), open(OUTD / "build.json", "w"), indent=1)
    print("rows:", {s: len(rr) // 2 for s, rr in new.items()}, "| block source:", src_count, "| no block:", miss)


def stage_counts(a):
    import collections
    c, na = collections.Counter(), collections.Counter()
    for r in O.jl(O.OUT / "rows.jsonl"):
        if r["set"] in ("HA4", "GA4") and r["cond"] == G.COND:
            ok = bool(O.anchor_entries(r["source"], r["item_id"], r["axis"]))
            (c if ok else na)[(GROUP[r["source"]], r["axis"])] += 1
    print("| dataset | AVB | TR | TC | total |\n|---|---|---|---|---|")
    for g in ("P01/P02", "P03-P09", "220 LTX", "220 MOVA", "149 LTX"):
        v = [c[(g, ax)] for ax in ("AVB", "TCR", "TCC")]
        print(f"| {g} | " + " | ".join(str(x) for x in v) + f" | {sum(v)} |")
    print("total calls", sum(c.values()), "| rows without stage-1 entries (no call):", dict(na))


def stage_diff(a):
    import difflib
    old = {r["uid"]: r for r in O.jl(O.OUT / "rows.jsonl") if r["set"] in ("HG4", "G4") and r["cond"] == G.COND and r["axis"] == "AVB"}
    for s in ("HA4", "GA4"):
        r = next(x for x in O.jl(O.OUT / "rows.jsonl") if x["set"] == s and x["cond"] == G.COND and x["axis"] == "AVB" and x["uid"] in old)
        co, cn = O.build_call(old[r["uid"]]), O.build_call(r)
        print(f"===== {s}: {r['uid']} (old set {'HG4' if s == 'HA4' else 'G4'}) | system prompt identical: {co['system'] == cn['system']} | schema identical: {co['schema'] == cn['schema']} | media: {cn['media']}")
        print("\n".join(difflib.unified_diff(co["user"].splitlines(), cn["user"].splitlines(), "current two-stage user prompt", "all-four user prompt", lineterm="")))


def stage_score(a):
    out = []
    for r in rows():
        src, iid, ax, gt = r["source"], r["item_id"], r["axis"], r["gt"]
        anc = RS.row_label(O.anchor_df(src), iid, ax, gt)
        f = O.OUT / "calls" / G.COND / f"{SETOF(src)}__{r['uid']}.json"
        lab = ""
        if f.exists():
            rec = json.load(open(f))
            lab = O.obs_label(rec, ax, gt) if rec["status"] == "ok" else ""
        out.append(dict(group=GROUP[src], axis=ax, uid=r["uid"], y="no" if "no" in gt.values() else "yes",
                        orig=(r.get("variant") == "original") if not src.startswith("g") else ("no" not in gt.values()), row1=anc, row4_allfour=lab or anc))
    D = pd.DataFrame(out)
    D.to_csv(OUTD / "rows_scored.csv", index=False)
    print(D.groupby(["group", "axis"]).size().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["check", "build", "counts", "diff", "score"])
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
