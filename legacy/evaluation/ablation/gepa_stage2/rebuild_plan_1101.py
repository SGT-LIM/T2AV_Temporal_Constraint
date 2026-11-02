#!/usr/bin/env python3
"""Dry run of the incremental A / AVB rebuild under the 11/01 eligible-anchor rule (user 11/01). No calls, no item files written.

Anchors: build_items find_anchors_eligible pairs (runs/obsval_1028/eligible_pairs_1101.csv) of the eligible classes (open / close,
cut / chop, stir / mix / whisk) that pass >= 20 dB (make_mute_anchor.db_reimpl, 25 s builder window). Windows and variants:
build_items.build_windows with ANCHOR_MODE = 'eligible', per group (P01/P02; P03-P09), windows running past the video end dropped
(as drop_short_windows / the holdout build). A items = originals with a sounding event + fail_absent_sound; AVB items = shift early /
late + originals of windows that have a shift. An existing A / AVB item is REUSED when the new build has the same item_id AND the
same prompt content (events: kind, verb, noun, classes, count, occurrences, sound, times; plus the absent-sound claim or the shift);
DROPPED when the new build lacks it or changes it; NEW when the new build has an item the old one lacks or changed.
V, TCR, TCC items are untouched. TCC check: count_off items whose counted event is a stir / mix / whisk action, and movement-set
items with a stir / mix / whisk event, are listed for exclusion.
  python gepa_stage2/rebuild_plan_1101.py   -> runs/obsval_1028/rebuild_plan_1101.json + printed tables
"""
import importlib.util, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
PILOT = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot")
HO = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av_holdout_p3p9_1028")
V12 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/hdepic/videos")
OUT = HERE / "runs/obsval_1028"
ELIG = {"open / close", "cut / chop", "stir / mix / whisk"}
STIR_VERBS = {"stir", "mix", "whisk", "beat", "fold"}
GROUPS = {"P01P02": ["P01", "P02"], "P03P09": [f"P0{k}" for k in range(3, 10)]}


def bi():
    spec = importlib.util.spec_from_file_location("build_items", PILOT / "build_items.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.ANCHOR_MODE = "eligible"
    return m


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def content(x):
    ev = [{k: e.get(k) for k in ("kind", "verb", "noun", "vc", "nc", "hand", "sound", "count", "occurrences", "t", "sound_t")} for e in x["events"]]
    return json.dumps(dict(ev=ev, seq=x.get("sequence"), claim=x.get("fail_reason") if x["variant"] == "fail_absent_sound" else None,
                           shift=(x.get("media") or {}).get("shift_s")), sort_keys=True, default=str)


def ab_items(items):
    shifted = {(x["video_id"], tuple(x["clip"])) for x in items if x["variant"] in ("fail_audio_shift_early", "fail_audio_shift_late")}
    A, AVB = {}, {}
    for x in items:
        v = x["variant"]
        if v == "fail_absent_sound" or (v == "original" and any(e["kind"] == "sounding" for e in x["events"])):
            A[x["item_id"]] = x
        if v in ("fail_audio_shift_early", "fail_audio_shift_late") or (v == "original" and (x["video_id"], tuple(x["clip"])) in shifted):
            AVB[x["item_id"]] = x
    return A, AVB


def main():
    B = bi()
    pairs = pd.read_csv(OUT / "eligible_pairs_1101.csv")
    anc_all = pairs[pairs["sound"].isin(ELIG) & (pairs.db >= 20)].copy()
    old12 = json.load(open(PILOT / "items_hdepic_medium_with_clips_v2.json"))
    old39 = json.load(open(HO / "items_hdepic_p3p9_v1_with_clips_holdout.json"))
    hodur = json.load(open(HO / "video_durations.json")) if (HO / "video_durations.json").exists() else {}
    plan = {}
    for grp, parts in GROUPS.items():
        s, n = B.load_hdepic(parts)
        anc = anc_all[anc_all.participant.isin(parts)][["video_id", "nid", "verb", "noun", "vc", "nc", "hand", "a_st", "a_en", "s_st", "s_en", "sound"]]
        anc = anc.astype({"vc": int, "nc": int}).where(anc.notna(), None).sort_values(["video_id", "a_st"]).reset_index(drop=True)
        new = B.build_windows(s, n, anc)
        durs = {}
        for x in new:
            v = x["video_id"]
            if v not in durs:
                durs[v] = float(hodur[v]) if v in hodur else dur(V12 / f"{v}.mp4")
        new = [x for x in new if x["clip"][1] <= durs[x["video_id"]]]
        old = old12 if grp == "P01P02" else old39
        oA, oV = ab_items(old)
        nA, nV = ab_items(new)
        res = {}
        for ax, o, nn in (("A", oA, nA), ("AVB", oV, nV)):
            reused = [i for i in nn if i in o and content(nn[i]) == content(o[i])]
            res[ax] = dict(before=len(o), after=len(nn), reused=len(reused), dropped=len(o) - len(reused), new=len(nn) - len(reused),
                           new_by_variant=dict(Counter(nn[i]["variant"] for i in nn if i not in reused)),
                           dropped_by_variant=dict(Counter(o[i]["variant"] for i in o if i not in reused)))
        newids = sorted({i for ax in ("A", "AVB") for i in (nA if ax == "A" else nV) if i not in [j for j in (nA if ax == "A" else nV)
                         if j in (oA if ax == "A" else oV) and content((nA if ax == "A" else nV)[j]) == content((oA if ax == "A" else oV)[j])]})
        snd = Counter(e["sound"] for x in new if x["variant"] == "original" for e in x["events"] if e["kind"] == "sounding")
        res.update(windows_before=len({(x["video_id"], tuple(x["clip"])) for x in old if x["variant"] == "original"}),
                   windows_after=len({(x["video_id"], tuple(x["clip"])) for x in new if x["variant"] == "original"}),
                   anchors_passing=len(anc), anchor_classes=dict(Counter(anc["sound"])), sounding_events_after=dict(snd),
                   new_item_ids=len(newids), new_A_rows=res["A"]["new"], new_AVB_rows=res["AVB"]["new"])
        plan[grp] = res
        json.dump(dict(new_items=[x for x in new if x["item_id"] in set(newids)]), open(OUT / f"rebuild_new_items_{grp}_1101.json", "w"))
    # TCC: count_off items counting a stir action; movement-set items with a stir event
    tcc = {}
    for grp, items in (("P01P02", old12), ("P03P09", old39)):
        hits = []
        for x in items:
            if x["variant"] == "fail_count_off":
                k = int(next(iter((x.get("count_override") or {"0": 0}).keys())))
                e = x["events"][k] if k < len(x["events"]) else {}
                if e.get("verb", "").split()[0] in STIR_VERBS or e.get("sound") == "stir / mix / whisk":
                    hits.append(x["item_id"])
        tcc[grp] = hits
    mv = json.load(open("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_move_prompts.json"))
    tcc["movement_set"] = [x["item_id"] for x in mv if any((e.get("action") or "").split()[0] in STIR_VERBS for e in x["events"])]
    plan["tcc_stir"] = {k: dict(n=len(v), items=v) for k, v in tcc.items()}
    json.dump(plan, open(OUT / "rebuild_plan_1101.json", "w"), indent=1)
    print(json.dumps({g: {k: v for k, v in plan[g].items()} for g in GROUPS}, indent=1))
    print("TCC stir:", {k: v["n"] for k, v in plan["tcc_stir"].items()}, {k: v["items"][:3] for k, v in plan["tcc_stir"].items()})


if __name__ == "__main__":
    main()
