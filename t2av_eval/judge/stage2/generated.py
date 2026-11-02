#!/usr/bin/env python3
"""Generated block, stage 2 (rows 4, 5 and framing), 10/30. Text-only KEEP/REVISE calls through obs_judge_1028 (same OBS_RULES,
same stage-1 block, same call settings: gemini-3.6-flash, thinking high, temperature 0, seed 42). Stage 1 = row 1 anchor.

GT rows: 220 = manifests_v3 sources ltx / mova, 149 = gt_gen149.jsonl (majority); axes A, V, AVB (TCR / TCC: no tool, decided 10/30).
Sources: g220ltx, g220mova, g149 (registered in obs_judge_1028.ANCHOR / PROMPTS).

  python gepa_stage2/gen_stage2_1030.py rows4 [--axes A,V,AVB]   # set G4: the axis tool always shown (ungated)
  python gepa_stage2/gen_stage2_1030.py vcheck --workers 6       # V: text-only caption-vs-event check (one call per V row)
  python gepa_stage2/gen_stage2_1030.py rows5                    # set G5: only A rows whose gated text differs from G4
  python gepa_stage2/gen_stage2_1030.py framing                  # sets FRb / FRc: framing variants b, c
  python gepa_stage2/obs_judge_1028.py run --set G4|G5|FRb|FRc --cond gen_tool_text --workers 6
  python gepa_stage2/gen_stage2_1030.py score

Observation texts (all start "Observation (tool output):", as the B30 / HO30 tool texts):
  A   Whisper (if the item has a speech event): transcript of segments with no_speech_prob < 0.5, words with start times;
      FLAM (per sounding event, its first pipeline query, whole clip, threshold .98): detected with the score peak time, or not
      detected with the max frame score.
  V   the AVoCaDO caption (fps 8, plain), introduced as a caption from a separate model that did not see the prompt.
  AVB the Synchformer lines from synchformer_gen_1030 (anchor-time window), as in HO30.
Row 5 admission (code):
  A   Whisper part only if the transcript contains a word of a required speech text; a FLAM line only for an event whose
      first-query max score < T_flam (.2705, the audibility threshold). Nothing admitted -> anchor verdict kept.
  V   caption admitted only if the text-only check says the caption explicitly contradicts a GT event of the row (main);
      the lemma heuristic of v_caption_diag_1030 ("contradict") is scored as a second admission variant (no calls).
  AVB fires if the strongest binding-event reading has |offset| >= T and p >= P; main T/P = T_batch / P_batch (label-free,
      batch = 220-LTX, 220-MOVA, 149), comparison T_tool 1.8 s / .25. Code-rule variant: FAIL when it fires. Gated-judge
      variant: the G4 AVB call when it fires.
  A row-5 call whose text equals the G4 text is not repeated: the G4 call is used (identical prompt, temperature 0, seed 42).
Framing (row 5 sub-variant): (a) = the G4 call; (b) one sentence added after the observation; (c) (b) + one rule.
  AVB rows where Synchformer fires (main T/P): the sentence states the labeled range, values filled at run time from
      framing_config_1030.json -> PREREGISTERED_RULE.json (never typed into the prompt code).
  220 and (11/01) 149 V rows where the check says the caption does not mention a GT event: a descriptive sentence, no number.
"""
import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
from t2av_eval import paths as _P
from t2av_eval.gate import preregistered as PR
import argparse, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
pass  # (legacy sys.path insert removed); pass  # (legacy sys.path insert removed)
import obs_judge_1028 as O

EV = Path((str(_P.DATA) + "/tools/gen_evidence_1030"))
SYNC = Path((str(_P.DATA) + "/tools/synchformer_gen_1030"))
G149 = Path((str(_P.DATA) + "/gen_holdout_149_1030"))
CAP = {"g220ltx": _P.INPUTS / "evaluation/ablation/captions/avocado_fps8_plain_v3_LTX_2p3.json", "g220mova": _P.INPUTS / "evaluation/ablation/captions/avocado_fps8_plain_v3_MOVA.json",
       "g149": _P.INPUTS / "evaluation/ablation/captions/avocado_fps8_plain_v3_gen149.json"}
MODEL = {"g220ltx": "LTX_2p3", "g220mova": "MOVA", "g149": "LTX_2p3"}
SETN = {"g220ltx": "220", "g220mova": "220", "g149": "149"}
BATCH = {"g220ltx": "220-LTX_2p3", "g220mova": "220-MOVA", "g149": "149-LTX_2p3"}
FRAMING_CONFIG = _P.CONFIG / "framing_config_1030.json"
COND = "gen_tool_text"
VCHK_SCHEMA = {"type": "object", "properties": {"per_event": {"type": "array", "items": {"type": "object", "properties": {
    "event_id": {"type": "string"}, "verdict": {"type": "string", "enum": ["describes", "contradicts", "not_mentioned"]},
    "quote": {"type": "string"}}, "required": ["event_id", "verdict", "quote"]}}}, "required": ["per_event"]}
VCHK_SYSTEM = ("You compare a video caption with a list of target visual events. You do not see the video. Judge only what the "
               "caption text states.")


def gt_rows():
    out = []
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(_P.INPUTS / f"evaluation/ablation/gepa_stage2/manifests_v3/{s}.jsonl")]
    for m in man:
        if m["source"] in ("ltx", "mova") and m["axis"] in ("A", "V", "AVB"):
            src = {"ltx": "g220ltx", "mova": "g220mova"}[m["source"]]
            out.append(dict(source=src, item_id=m["item_id"], axis=m["axis"], gt=m["gt"]))
    for l in open(G149 / "gt_gen149.jsonl"):
        m = json.loads(l)
        if m["axis"] in ("A", "V", "AVB"):
            out.append(dict(source="g149", item_id=m["item_id"], axis=m["axis"], gt=m["gt"]))
    for r in out:
        r["uid"] = f"{r['source']}|{r['item_id']}|{r['axis']}"
        r["variant"] = MODEL[r["source"]]
    return out


def evidence(src, iid):
    f = EV / SETN[src] / f"{MODEL[src]}__{iid}.json"
    return json.load(open(f)) if f.exists() else None


def norm(t):
    return [w for w in (re.sub(r"[^a-z0-9']", "", x.lower()) for x in t.split()) if w]


def a_parts(src, iid):
    """(whisper_text or None, {event_id: (flam_line, max_score)}, speech_word_present)"""
    meta = O.meta_for(src, iid)
    rec = evidence(src, iid)
    T = json.load(open(EV / "flam_threshold.json"))["T_flam"]
    items = {x["item_id"]: x for x in json.load(open(O.PROMPTS[src]))}
    speech = [e for e in items[iid]["events"] if e["modality"] == "speech"]
    wtxt, present = None, False
    if speech:
        segs = [s for s in rec["whisper"]["segments"] if s["no_speech_prob"] < 0.5]
        if segs:
            words = [w for s in segs for w in s.get("words", [])]
            wtxt = ("Whisper (speech recognizer) on the clip audio: transcript \"" + " ".join(s["text"].strip() for s in segs) + "\"; words "
                    "with start times: " + ", ".join(f"{w['word'].strip()} @ {w['start']:.2f} s" for w in words))
            heard = {x for s in segs for x in norm(s["text"])}
            present = any(set(norm(e["text"])) & heard for e in speech)
        else:
            wtxt = "Whisper (speech recognizer) on the clip audio: no speech detected (no segment with no_speech_prob < 0.5)"
    fl = {}
    q1 = {e["event_id"]: e["queries"][0] for e in rec.get("events", []) if e["queries"]}
    for s in meta.get("events", []):
        pass
    from t2av_eval.judge.media import core as NE
    for s in NE.build_scoring_events(meta):
        if s["kind"] != "sounding_action" or s["event_id"] not in q1:
            continue
        q = q1[s["event_id"]]
        f = rec["flam"][q]
        if f["detections"]:
            d = max(f["detections"], key=lambda d: d.get("peak_score") or 0)
            line = (f"FLAM (open-vocabulary audio-text detector, whole clip audio): queried '{q}' -> detected, score peak at "
                    f"{d['peak_time']:.2f} s (detection threshold 0.98; scores are uncalibrated)")
        else:
            line = (f"FLAM (open-vocabulary audio-text detector, whole clip audio): queried '{q}' -> not detected (max frame score "
                    f"{f['max_score']:.3f}; detection threshold 0.98; scores are uncalibrated)")
        fl[s["event_id"]] = (line, f["max_score"], f["max_score"] < T)
    return wtxt, fl, present


def a_text(src, iid, gated=False):
    wtxt, fl, present = a_parts(src, iid)
    lines = []
    if wtxt and (not gated or present):
        lines.append(wtxt)
    lines += [l for l, _, below in fl.values() if not gated or below]
    return "Observation (tool output):\n" + "\n".join(lines) if lines else ""


def caption(src, iid):
    if not CAP[src].exists():
        return None
    c = {k.split("/")[0]: v["caption"] for k, v in json.load(open(CAP[src])).items()}
    return c.get(iid)


def v_text(src, iid):
    c = caption(src, iid)
    return None if c is None else ("Observation (tool output):\nDense caption written by a separate captioning model (AVoCaDO) that "
                                   "watched and listened to the same clip without seeing the prompt:\n" + c.strip())


def avb_text(src, iid):
    f = SYNC / "sync_obs_lines.json"
    if not f.exists():
        return None
    t = json.load(open(f)).get(f"{SETN[src]}|{MODEL[src]}|{iid}")
    return None if t is None else "Observation (tool output):\n" + t


def add_rows(set_name, rows):
    allrows = [r for r in O.jl(O.OUT / "rows.jsonl") if r["set"] != set_name]
    O.wjl(O.OUT / "rows.jsonl", allrows + rows)


def row(set_name, r, text, **extra):
    base = dict(set=set_name, source=r["source"], uid=r["uid"], item_id=r["item_id"], axis=r["axis"], variant=r["variant"],
                gt=r["gt"], clip=r["item_id"], **extra)
    return [{**base, "cond": "anchor"}, {**base, "cond": COND, "obs": {"text": text}}]


def stage_rows4(a):
    axes = a.axes.split(",")
    keep = [r for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == "G4" and r["axis"] not in axes]
    new, miss = [], {}
    for r in gt_rows():
        if r["axis"] not in axes:
            continue
        t = {"A": a_text, "V": v_text, "AVB": avb_text}[r["axis"]](r["source"], r["item_id"])
        if not t:
            miss[(r["source"], r["axis"])] = miss.get((r["source"], r["axis"]), 0) + 1
            continue
        new += row("G4", r, t)
    add_rows("G4", keep + new)
    print(f"G4 rows ({','.join(axes)}): {len(new) // 2}; no tool text: {miss}")


def stage_vcheck(a):
    from google import genai
    import os, hashlib, time
    from concurrent.futures import ThreadPoolExecutor
    cache = O.OUT / "calls" / "vcap_check"
    cache.mkdir(parents=True, exist_ok=True)
    todo = []
    for r in gt_rows():
        if r["axis"] != "V":
            continue
        c = caption(r["source"], r["item_id"])
        if c is None or (cache / f"{r['uid']}.json").exists():
            continue
        items = {x["item_id"]: x for x in json.load(open(O.PROMPTS[r["source"]]))}
        evs = items[r["item_id"]]["events"]
        ids = {e["id"]: f"event_{k + 1}" for k, e in enumerate(evs)}
        lines = [f"- {ids[e['id']]}: {e['definition']}" for e in evs if ids[e["id"]] in r["gt"]]
        user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() +
                "\n\nTarget visual events:\n" + "\n".join(lines) +
                "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
                "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
                "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
                "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
        todo.append((r, dict(system=VCHK_SYSTEM, user=user, media=None, schema=VCHK_SCHEMA, anchor=[])))
    print(f"[vcap_check] to do {len(todo)}", flush=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def one(x):
        r, c = x
        try:
            parsed, raw = O.call(client, a.model, c, {"obs": {}})
            rec = dict(status="ok", parsed=parsed, raw=raw, user_md5=hashlib.md5(c["user"].encode()).hexdigest(), user=c["user"])
        except Exception as e:
            return f"error {type(e).__name__}"
        rec.update(uid=r["uid"], model=a.model, thinking="high", time=time.strftime("%Y-%m-%dT%H:%M:%S"))
        json.dump(rec, open(cache / f"{r['uid']}.json", "w"))
        return "ok"

    n = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for i, s in enumerate(ex.map(one, todo)):
            n[s] = n.get(s, 0) + 1
            if i % 25 == 0:
                print(f"[vcap_check] {i + 1}/{len(todo)} {n}", flush=True)
    print(f"[DONE] vcap_check: {n}", flush=True)


def vcheck(uid):
    f = O.OUT / "calls" / "vcap_check" / f"{uid}.json"
    if not f.exists():
        return None
    return {e["event_id"]: e["verdict"] for e in json.load(open(f))["parsed"].get("per_event", [])}


def v_lemma(src, iid, gt):
    import v_caption_diag_1030 as VD
    c = caption(src, iid)
    if c is None:
        return None
    items = {x["item_id"]: x for x in json.load(open(O.PROMPTS[src]))}
    evs = items[iid]["events"]
    toks = VD.toks(c)
    out = {}
    for k, e in enumerate(evs):
        eid = f"event_{k + 1}"
        if eid in gt and e["modality"] != "speech":
            out[eid] = VD.classify(toks, *VD.event_terms(e))
    return out


def sync_fire():
    """{(source, item_id): {'main': bool, 'tool': bool}}, thresholds."""
    thr = json.load(open(SYNC / "batch_thresholds.json"))
    pe = pd.concat(pd.read_csv(f) for s in ("220", "149") for f in sorted((SYNC / s).glob("per_event_shard*.csv")))
    pe["batch"] = pe["set"].astype(str) + "-" + pe["model"]
    ok = pe[pe.status == "ok"].assign(absoff=lambda t: t.offset.abs())
    best = ok.sort_values(["absoff", "prob"], ascending=False).drop_duplicates(["batch", "item_id"])
    out = {}
    for r in best.itertuples():
        t = thr[r.batch]
        src = {"220-LTX_2p3": "g220ltx", "220-MOVA": "g220mova", "149-LTX_2p3": "g149"}[r.batch]
        out[(src, r.item_id)] = dict(main=bool(r.absoff >= t["T_batch"] - 1e-9 and r.prob >= t["P_batch"] - 1e-9),
                                     tool=bool(r.absoff >= t["T_tool"] - 1e-9 and r.prob >= t["P_tool"] - 1e-9))
    return out, thr


def stage_rows5(a):
    new = []
    for r in gt_rows():
        if r["axis"] != "A":
            continue
        g4, g5 = a_text(r["source"], r["item_id"]), a_text(r["source"], r["item_id"], gated=True)
        if g5 and g5 != g4:
            new += row("G5", r, g5)
    add_rows("G5", new)
    print(f"G5 rows (A, gated text differs from G4): {len(new) // 2}")


def framing_sentences():
    cfg = json.load(open(FRAMING_CONFIG))
    rule = PR.avb_rule()
    T, P = rule[cfg["avb"]["T_key"]], rule[cfg["avb"]["P_key"]]
    avb_b = cfg["avb"]["b"].format(T=T, P=P)
    return dict(AVB=(avb_b, avb_b + "\n" + cfg["avb"]["c_rule"]), V=(cfg["v"]["b"], cfg["v"]["b"] + "\n" + cfg["v"]["c_rule"]))


def stage_framing(a):
    fire, _ = sync_fire()
    S = framing_sentences()
    rb, rc, log = [], [], []
    for r in gt_rows():
        if r["axis"] == "AVB" and fire.get((r["source"], r["item_id"]), {}).get("main"):
            t = avb_text(r["source"], r["item_id"])
        elif r["axis"] == "V":                                 # 11/01: 149 V rows included (user)
            vc = vcheck(r["uid"]) or {}
            if not any(vc.get(e) == "not_mentioned" for e in r["gt"]):
                continue
            t = v_text(r["source"], r["item_id"])
        else:
            continue
        if not t:
            continue
        b, c = S[r["axis"]]
        rb += row("FRb", r, t + "\n\nNote: " + b)
        rc += row("FRc", r, t + "\n\nNote: " + c)
        log.append(dict(uid=r["uid"], axis=r["axis"], b=b, c=c))
    add_rows("FRb", rb); add_rows("FRc", rc)
    json.dump(log, open(O.OUT / "framing_sentences_1030.json", "w"), indent=1)
    print(f"framing rows: {len(rb) // 2} (AVB {sum(x['axis'] == 'AVB' for x in log)}, V {sum(x['axis'] == 'V' for x in log)})")
    print("sentences:", json.dumps(S, indent=1))


def call_label(set_name, r):
    f = O.OUT / "calls" / COND / f"{set_name}__{r['uid']}.json"
    if not f.exists():
        return ""
    rec = json.load(open(f))
    return O.obs_label(rec, r["axis"], r["gt"]) if rec["status"] == "ok" else ""


def stage_score(a):
    from t2av_eval.scoring import lookup as RS
    fire, thr = (sync_fire() if (SYNC / "batch_thresholds.json").exists() else ({}, {}))
    out = []
    g4uids = {r["uid"] for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == "G4" and r["cond"] == COND}
    for r in gt_rows():
        src, iid, ax, gt = r["source"], r["item_id"], r["axis"], r["gt"]
        if r["uid"] not in g4uids:          # no tool text yet (149 V before its captions): not scored for rows 4 / 5
            continue
        anc = RS.row_label(O.anchor_df(src), iid, ax, gt)
        g4 = call_label("G4", r)
        d = dict(source=src, model=MODEL[src], set=SETN[src], uid=r["uid"], axis=ax, y="no" if "no" in gt.values() else "yes",
                 row1=anc, row4=g4 or anc)
        if ax == "A":
            g5t, g4t = a_text(src, iid, gated=True), a_text(src, iid)
            d["admitted"] = bool(g5t)
            d["row5"] = anc if not g5t else (g4 if g5t == g4t else call_label("G5", r)) or anc
        elif ax == "V":
            vc = vcheck(r["uid"]) or {}
            lm = v_lemma(src, iid, gt) or {}
            d["admitted"] = any(vc.get(e) == "contradicts" for e in gt)
            d["row5"] = (g4 or anc) if d["admitted"] else anc
            d["row5_lemma"] = (g4 or anc) if any(lm.get(e) == "contradict" for e in gt) else anc
            d["not_mentioned"] = any(vc.get(e) == "not_mentioned" for e in gt)
        else:
            f = fire.get((src, iid), {})
            d["admitted"] = f.get("main", False)
            d["row5_rule_batch"] = "no" if f.get("main") else anc
            d["row5_rule_tool"] = "no" if f.get("tool") else anc
            d["row5"] = (g4 or anc) if f.get("main") else anc                     # gated judge, T_batch
            d["row5_judge_tool"] = (g4 or anc) if f.get("tool") else anc
        for v in ("FRb", "FRc"):
            d[v] = call_label(v, r)
        out.append(d)
    D = pd.DataFrame(out)
    # rows with a G4 row whose call never returned a parseable answer are excluded from every condition (same n everywhere)
    g4rows = {r["uid"] for r in O.jl(O.OUT / "rows.jsonl") if r["set"] == "G4" and r["cond"] == COND}
    bad = [u for u in g4rows if not (O.OUT / "calls" / COND / f"G4__{u}.json").exists()]
    if bad:
        print(f"excluded (G4 call failed): {bad}")
    D = D[~D.uid.isin(bad)]
    D.to_csv(O.OUT / "gen_stage2_rows_1030.csv", index=False)
    cols = [c for c in ("row1", "row4", "row5", "row5_lemma", "row5_rule_batch", "row5_rule_tool", "row5_judge_tool") if c in D]
    tab = []
    for (m, s, ax), g in D.groupby(["model", "set", "axis"]):
        for c in cols:
            h = g[g[c].isin(["yes", "no"])] if c in g else g.iloc[:0]
            if not len(h):
                continue
            mt = RS.metrics(h.y, h[c])
            tab.append(dict(set=s, model=m, axis=ax, cond=c, n=mt["n"], n_fail=mt["n_fail"], acc=mt["acc"], prec=mt["prec"], rec=mt["rec"],
                            admitted=int(g.admitted.sum()) if c.startswith("row5") else None))
    T = pd.DataFrame(tab)
    T.to_csv(O.OUT / "gen_stage2_table_1030.csv", index=False)
    pd.set_option("display.width", 220)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    if thr:
        print("\nSynchformer batch thresholds:", json.dumps(thr, indent=1))
    fr = D[D.FRb.isin(["yes", "no"])]
    if len(fr):
        print("\nframing rows (a = G4 call):")
        for (m, s, ax), g in fr.groupby(["model", "set", "axis"]):
            for c in ("row4", "FRb", "FRc"):
                mt = RS.metrics(g.y, g[c])
                print(f"  {s} {m} {ax} {c}: n {mt['n']} acc {mt['acc']:.2f} prec {mt['prec']} rec {mt['rec']} revised_vs_row1 "
                      f"{int((g[c] != g.row1).sum())}")


def stage_groups(a):
    """Row 5 rows per axis and model in three groups: gate closed (stage 1 kept, no call), gate open with the row 4 text
    (row 4 call reused), gate open with a different text (new G5 call). AVB: main admission T_batch / P_batch."""
    fire = sync_fire()[0] if (SYNC / "batch_thresholds.json").exists() else None
    out = []
    for r in gt_rows():
        src, iid, ax = r["source"], r["item_id"], r["axis"]
        if ax == "A":
            g5, g4 = a_text(src, iid, gated=True), a_text(src, iid)
            grp = "closed" if not g5 else ("open_reused" if g5 == g4 else "open_new_call")
        elif ax == "V":
            vc = vcheck(r["uid"])
            grp = "pending (caption check)" if vc is None else ("open_reused" if any(vc.get(e) == "contradicts" for e in r["gt"]) else "closed")
        else:
            grp = "pending (Synchformer)" if fire is None else ("open_reused" if fire.get((src, iid), {}).get("main") else "closed")
        out.append(dict(set=SETN[src], model=MODEL[src], axis=ax, group=grp))
    t = pd.DataFrame(out).groupby(["set", "model", "axis", "group"]).size().unstack(fill_value=0)
    t.to_csv(O.OUT / "gen_stage2_groups_1030.csv")
    print(t.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["rows4", "vcheck", "rows5", "framing", "score", "groups"])
    ap.add_argument("--axes", default="A,V,AVB")
    ap.add_argument("--model", default="gemini-3.6-flash")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    globals()[f"stage_{a.stage}"](a)
