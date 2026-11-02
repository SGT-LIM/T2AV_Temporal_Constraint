#!/usr/bin/env python3
"""TC tool check on the generated sets, before any TC judge run (10/30). CPU only, no Gemini calls.

  python gepa_stage2/tc_tool_check_1030.py            # both sets; writes runs/obsval_1028/tc_tool_check_1030_{rows,table}.csv

Question: are the audio / caption tools accurate enough on TCR order and TCC count to be shown to the judge?
Sets: 220 (manifests_v3 rows of source ltx / mova, axes TCR / TCC, all splits) and 149 (gt_gen149.jsonl, majority labels).
Per event, from the evidence of gen_evidence_1030.py:
  speech          Whisper word timestamps (segments with no_speech_prob < 0.5); time = start of the first occurrence of the
                  phrase (exact match after lower-casing and stripping punctuation); count = occurrences of the phrase.
  sounding_action FLAM, first pipeline query of the event (the query T_flam was defined on); audible iff whole-clip max score
                  >= T_flam; peaks = detection peak_times, a peak within one FLAM frame (0.3125 s) of the previous kept peak is
                  merged; time = first peak; count = number of kept peaks (0 if not audible).
  silent_action   no audio time.
Caption (AVoCaDO plain): an event is mentioned at the first caption token matching any content-word lemma of its action name
(speech: the quoted phrase); caption order = order of first mentions; caption count = an explicit count word within 4 tokens of
a mention (once / twice / three times / two ...), else undetermined.
Verdicts (tool says PASS / FAIL; FAIL = positive class), only on rows where the tool determines the answer:
  TCR order items (order, order_count; single-event items skipped)
                    audio order: >= 2 events of the sequence with an audio time; PASS iff their time order equals the prompt order.
                    caption order: >= 2 events mentioned; PASS iff the mention order equals the prompt order.
  TCR sync items    no verdict; the spread (max - min) of the audio times is reported per GT label.
  TCC rows (any item type)  required counts: the count item value, order_count event_counts, sync_count count per event, else 1
                    per event. FAIL if any tool-determined count differs; PASS only if every count is determined and equal.
                    caption count: an explicit count word found; PASS iff it equals the required count.
"Order error" = share of GT-PASS determined order rows where the tool order differs from the prompt order (the quantity that
was 37% for Qwen on the HD-EPIC originals).
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ABL = HERE.parent
EV = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/gen_evidence_1030")
G149 = Path("/projectnb/ivc-ml/youngsun/T2AV_data/gen_holdout_149_1030")
REL500 = Path((_LEGACY_ROOT + "/new_prompts/generated/relative_500_v5_fixed.json"))
CAP = {("220", "LTX_2p3"): _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps8_plain_v3_LTX_2p3.json", ("220", "MOVA"): _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps8_plain_v3_MOVA.json",
       ("149", "LTX_2p3"): _pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions/avocado_fps8_plain_v3_gen149.json"}
OUT = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028"
FRAME = 0.3125
NUM = {"once": 1, "one": 1, "twice": 2, "two": 2, "thrice": 3, "three": 3, "four": 4, "five": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
STOP = set("a an the of on in into onto with to from at by for and or his her their its this that it up down off out over hand sign".split())
sys.path.insert(0, str(HERE))
from v_caption_diag_1030 import lem


def lemd(w):
    w = lem(w)
    return w[:-1] if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "aeiouls" else w   # snapp -> snap


def norm(t):
    return [re.sub(r"[^a-z0-9']", "", w.lower()) for w in t.split() if re.sub(r"[^a-z0-9']", "", w.lower())]


def rows():
    out = []
    P = {x["item_id"]: x for x in json.load(open(REL500))}
    man = [json.loads(l) for s in ("train", "val", "test") for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / f"manifests_v3/{s}.jsonl")]
    for m in man:
        if m["source"] in ("ltx", "mova") and m["axis"] in ("TCR", "TCC"):
            out.append(dict(set="220", model={"ltx": "LTX_2p3", "mova": "MOVA"}[m["source"]], item_id=m["item_id"], axis=m["axis"],
                            y=m["gt"]["__item__"], item=P[m["item_id"]]))
    P = {x["item_id"]: x for x in json.load(open(G149 / "prompts_gen149.json"))}
    for l in open(G149 / "gt_gen149.jsonl"):
        m = json.loads(l)
        if m["axis"] in ("TCR", "TCC"):
            out.append(dict(set="149", model="LTX_2p3", item_id=m["item_id"], axis=m["axis"], y=m["gt"]["__item__"], item=P[m["item_id"]]))
    return out


def audio_events(item, rec, T):
    """{event id: (first time or None, count, source)}"""
    words = [(w["start"], re.sub(r"[^a-z0-9']", "", w["word"].lower())) for s in rec["whisper"]["segments"] if s["no_speech_prob"] < 0.5
             for w in s.get("words", [])]
    words = [w for w in words if w[1]]
    q1 = {e["label"]: e["queries"][0] for e in rec.get("events", []) if e["queries"]}
    res = {}
    for e in item["events"]:
        if e["modality"] == "speech":
            ph = norm(e["text"])
            hits = [words[i][0] for i in range(len(words) - len(ph) + 1) if [w for _, w in words[i:i + len(ph)]] == ph]
            res[e["id"]] = (hits[0] if hits else None, len(hits), "whisper")
        elif e["modality"] == "sounding_action":
            q = q1.get(e["action"]) or next((v for k, v in q1.items() if k.replace(" ", "_") == e["action"]), None)
            f = rec["flam"].get(q) if q else None
            if f is None:
                res[e["id"]] = (None, None, "flam_missing")
                continue
            if f["max_score"] < T:
                res[e["id"]] = (None, 0, "flam")
                continue
            peaks = []
            for t in sorted(d["peak_time"] for d in f["detections"]):
                if not peaks or t - peaks[-1] > FRAME:
                    peaks.append(t)
            res[e["id"]] = (peaks[0] if peaks else None, len(peaks), "flam")
        else:
            res[e["id"]] = (None, None, "silent")
    return res


def caption_events(item, cap):
    raw = re.findall(r"[A-Za-z0-9_']+", cap.replace("_", " ").replace("-", " "))
    tk = [lemd(t) for t in raw]
    low = [t.lower() for t in raw]
    res = {}
    for e in item["events"]:
        if e["modality"] == "speech":
            ph = [lemd(w) for w in norm(e["text"])]
            pos = [i for i in range(len(tk) - len(ph) + 1) if tk[i:i + len(ph)] == ph]
        else:
            terms = {lemd(w) for w in re.findall(r"[A-Za-z]+", e["action"].replace("_", " ")) if w.lower() not in STOP}
            pos = [i for i, t in enumerate(tk) if t in terms]
        cnt = None
        for i in pos:
            for j in range(max(0, i - 4), min(len(low), i + 5)):
                if low[j] in NUM and not (low[j] == "one" and j + 1 < len(low) and low[j + 1] in ("hand", "of")):
                    cnt = NUM[low[j]]
                    break
            if cnt is not None:
                break
        res[e["id"]] = (pos[0] if pos else None, cnt)
    return res


def order_verdict(seq, pos):
    have = [(pos[e], e) for e in seq if pos.get(e) is not None]
    if len(have) < 2:
        return None
    got = [e for _, e in sorted(have)]
    return "yes" if got == [e for e in seq if pos.get(e) is not None] else "no"


def count_verdict(req, got):
    """FAIL if any determined count differs from the required count; PASS only if every count is determined and equal."""
    det = {e: c for e, c in got.items() if c is not None}
    if any(c != req[e] for e, c in det.items()):
        return "no", json.dumps(det)
    return ("yes" if len(det) == len(req) else None), json.dumps(det)


def main():
    T = json.load(open(EV / "flam_threshold.json"))["T_flam"]
    caps = {}
    for k, f in CAP.items():
        if f.exists():
            caps[k] = {key.split("/")[0]: v["caption"] for key, v in json.load(open(f)).items()}
    out = []
    for r in rows():
        it, tc = r["item"], r["item"]["temporal_constraint"]
        f = EV / r["set"] / f"{r['model']}__{r['item_id']}.json"
        rec = json.load(open(f)) if f.exists() else None
        ae = audio_events(it, rec, T) if rec else {}
        cap = caps.get((r["set"], r["model"]), {}).get(r["item_id"])
        ce = caption_events(it, cap) if cap else {}
        d = dict(set=r["set"], model=r["model"], item_id=r["item_id"], axis=r["axis"], task=tc["task_type"], y=r["y"],
                 evidence=rec is not None, caption=cap is not None,
                 modalities="+".join(e["modality"] for e in it["events"]))
        v = tc["value"]
        if r["axis"] == "TCR":
            d["task"] = tc["task_type"] if len(it["events"]) > 1 else "single_event"
            if d["task"] == "order":
                seq = v.get("sequence") or v["ordered_events"]
                d["audio"] = order_verdict(seq, {e: ae.get(e, (None,))[0] for e in seq}) if rec else None
                d["caption_v"] = order_verdict(seq, {e: ce.get(e, (None,))[0] for e in seq}) if cap else None
            elif d["task"] == "sync":
                ts = [ae[e][0] for e in v["events"] if e in ae and ae[e][0] is not None]
                d["sync_spread"] = round(max(ts) - min(ts), 3) if len(ts) >= 2 else None
        else:
            d["task"] = "count"
            req = {v["event"]: int(v["count"])} if "event" in v else (v.get("event_counts") or {e["id"]: int(v.get("count", 1)) for e in it["events"]})
            d["required"] = json.dumps(req)
            d["audio"], d["audio_counts"] = count_verdict(req, {e: ae.get(e, (None, None))[1] for e in req}) if rec else (None, None)
            d["caption_v"], d["caption_counts"] = count_verdict(req, {e: ce.get(e, (None, None))[1] for e in req}) if cap else (None, None)
            d["audio_src"] = "+".join(sorted({ae.get(e, (None, None, "silent"))[2] for e in req}))
        out.append(d)
    D = pd.DataFrame(out)
    D.to_csv(OUT / "tc_tool_check_1030_rows.csv", index=False)
    print(f"T_flam {T}; rows {len(D)}; evidence present {int(D.evidence.sum())}; caption present {int(D.caption.sum())}")
    tab = []
    for (s, m, task), g in D.groupby(["set", "model", "task"]):
        for tool in ("audio", "caption_v"):
            if tool not in g or task == "sync":
                continue
            h = g[g[tool].isin(["yes", "no"])]
            tp = int(((h[tool] == "no") & (h.y == "no")).sum())
            ps = h[h.y == "yes"]
            tab.append(dict(set=s, model=m, task=task, tool=tool.replace("_v", ""), n=len(g), n_gt_fail=int((g.y == "no").sum()),
                            determined=len(h), acc=round((h[tool] == h.y).mean(), 3) if len(h) else None,
                            prec=round(tp / max(1, int((h[tool] == "no").sum())), 3) if (h[tool] == "no").any() else None,
                            rec=round(tp / max(1, int((h.y == "no").sum())), 3) if (h.y == "no").any() else None,
                            pass_rows_det=len(ps), err_on_pass=round((ps[tool] == "no").mean(), 3) if len(ps) else None))
    T_ = pd.DataFrame(tab)
    T_.to_csv(OUT / "tc_tool_check_1030_table.csv", index=False)
    print(T_.to_string(index=False))
    sy = D[D.task == "sync"]
    if len(sy):
        print("\nsync items, audio time spread (s) by GT label:")
        print(sy.groupby(["set", "model", "y"]).sync_spread.agg(["size", "count", "median"]).to_string())


if __name__ == "__main__":
    main()
