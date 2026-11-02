#!/usr/bin/env python3
# Replaced by t2av_eval/gate/v_caption_diag.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""V-axis caption admission diagnostic (10/30). No judge calls.

For each v3-test V row (HD-EPIC 164, LTX 35, MOVA 35) and its cached AVoCaDO caption, per focal event
(FAIL rows: the GT-'no' events; PASS rows: all GT events):
  mention    = the event's head noun OR its verb (lemma) appears in the caption; for an item about hands
               (event has a body side) the stated side word must also appear
  contradict = hand item: the opposite side word appears within 6 tokens of the event's verb/noun and the stated side does not;
               object event: the event's verb appears, the event's head noun never does, and a different content word
               follows the verb within 4 tokens (the caption names another object for that action)
Row class: (b) contradicts if any focal event is contradicted; else (a) mentions if all focal events are mentioned;
(c) silent if none is; 'partial' otherwise. Lemmas: lower-case, letters only, suffix stripping (ies->y, es, s, ing, ed);
no POS tagger is available, so (b) for object events is a heuristic.
Cross: the one-call (Whisper+FLAM+caption) runs' V verdicts, stage1_lookup rule: HD-EPIC hdepic_medium_multi_tools_wf_hop5_g36
(10/26), 220 tools_min3_g36_1027 (10/27). There is no 10/28 one-call caption run.

  python gepa_stage2/v_caption_diag_1030.py   -> runs/obsval_1028/v_caption_diag_1030_rows.csv + printed tables
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, re, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ABL))
import rep_scoring as RS

EV = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
R = Path((_LEGACY_ROOT + "/eval_results/multi_agent"))
CAP = {"hdepic": _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps2_plain_v3_hdepic_items.json",
       "ltx": _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps8_plain_v3_LTX_2p3.json", "mova": _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps8_plain_v3_MOVA.json"}
PROMPT = {"hdepic": EV / "hdepic_medium_prompts_v2.json",
          "ltx": Path((_LEGACY_ROOT + "/new_prompts/generated/relative_500_v5_fixed.json"))}
PROMPT["mova"] = PROMPT["ltx"]
ONECALL = {"hdepic": [EV / "results/hdepic_medium_multi_tools_wf_hop5_g36"],
           "ltx": [R / "tools_min3_g36_1027/LTX_2p3.csv"], "mova": [R / "tools_min3_g36_1027/MOVA.csv"]}
STOP = set("a an the of on in into onto with to from at by for and or his her their its this that it up down off out over".split())
SIDE = {"left": "right", "right": "left"}


def lem(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)] + rep
    return w


def toks(text):
    return [lem(t) for t in re.findall(r"[A-Za-z_']+", text.replace("_", " "))]


def event_terms(e):
    act = (e.get("action") or e.get("label") or "").replace("_", " ")
    words = [w for w in re.findall(r"[A-Za-z]+", act)]
    verb = lem(words[0]) if words else ""
    nouns = [lem(w) for w in words[1:] if w.lower() not in STOP and w.lower() not in SIDE and w.lower() != "hand"]
    side = (e.get("body_side") or "").lower()
    side = side if side in SIDE else ""                      # 'both' / other values: no left-right claim
    if not side:
        m = re.search(r"\b(left|right)\b", (act + " " + (e.get("definition") or "")).lower())
        side = m.group(1) if m else ""
    return verb, nouns, side


def classify(cap_toks, verb, nouns, side):
    capset = set(cap_toks)
    head = nouns[-1] if nouns else ""
    hit_obj = bool(head) and head in capset
    hit_verb = bool(verb) and verb in capset
    pos = [i for i, t in enumerate(cap_toks) if t in ({verb} | ({head} if head else set()))]
    if side:
        near = [cap_toks[max(0, i - 6): i + 7] for i in pos]
        has_side = any(side in w for w in near) or side in capset
        opp = any(SIDE[side] in w for w in near)
        if (hit_obj or hit_verb) and opp and not any(side in w for w in near):
            return "contradict"
        return "mention" if (hit_obj or hit_verb) and has_side else ("silent" if not (hit_obj or hit_verb) else "partial_side")
    if hit_obj or hit_verb:
        if hit_verb and not hit_obj and head:
            for i, t in enumerate(cap_toks):
                if t == verb and any(x not in STOP and x != head and len(x) > 2 for x in cap_toks[i + 1: i + 5]):
                    return "contradict"
        return "mention"
    return "silent"


def main():
    import new_eval as NE
    man = [json.loads(l) for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "manifests_v3/test.jsonl")]
    rows = []
    for src in ("hdepic", "ltx", "mova"):
        caps = json.load(open(CAP[src]))
        byitem = {}
        for k, v in caps.items():
            byitem.setdefault(k.split("/")[0], v["caption"] if isinstance(v, dict) else v)
        items = json.load(open(PROMPT[src]))
        metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
        pitems = {x["item_id"]: x for x in items}
        oc = RS.load([str(p) for p in ONECALL[src]])
        for m in man:
            if m["source"] != src or m["axis"] != "V":
                continue
            iid = m["item_id"]
            cap = byitem.get(iid)
            structs = {s["event_id"]: s for s in NE.build_scoring_events(metas[iid])}
            pev = pitems[iid]["events"]
            y = "no" if "no" in m["gt"].values() else "yes"
            focal = [e for e, g in m["gt"].items() if (g == "no") == (y == "no")]
            res = []
            for eid in focal:
                k = int(eid.split("_")[1]) - 1
                e = pev[k] if k < len(pev) else {"action": structs[eid]["label"]}
                res.append("no_caption" if cap is None else classify(toks(cap), *event_terms(e)))
            if "no_caption" in res:
                cls = "no_caption"
            elif "contradict" in res:
                cls = "b_contradicts"
            elif all(r == "mention" for r in res):
                cls = "a_mentions"
            elif all(r == "silent" for r in res):
                cls = "c_silent"
            else:
                cls = "partial"
            rows.append(dict(source=src, item_id=iid, variant=m["variant"], y=y, cls=cls, per_event=res,
                             onecall=RS.row_label(oc, iid, "V", m["gt"])))
    d = pd.DataFrame(rows)
    d.to_csv(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028/v_caption_diag_1030_rows.csv", index=False)
    order = ["a_mentions", "b_contradicts", "c_silent", "partial", "no_caption"]
    t = d.groupby(["source", "y", "cls"]).size().unstack(fill_value=0).reindex(columns=order, fill_value=0)
    t["n"] = t.sum(1)
    print(t.to_string())
    print("\nshares:\n", (t[order].div(t["n"], axis=0)).round(2).to_string())
    o = d[(d.source == "hdepic") & (d.variant == "original")]
    fa = o[o.onecall == "no"]
    print(f"\nHD-EPIC originals: {len(o)}; one-call V false alarms: {len(fa)}; by caption class: {fa.cls.value_counts().to_dict()}")
    print(f"HD-EPIC originals by class: {o.cls.value_counts().to_dict()}")
    for src in ("ltx", "mova"):
        g = d[(d.source == src) & (d.y == "yes")]
        f = g[g.onecall == "no"]
        print(f"{src} PASS rows: {len(g)}; one-call false alarms: {len(f)}; by class: {f.cls.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
