#!/usr/bin/env python3
"""TC tool screening (TCR, TCC) on HD-EPIC P01-P09 and the generated 220 / 149, 11/02. No Gemini calls; existing tool outputs only.

Rows: screen_common_1031.rows (p1p2 = manifests_v3 all splits, calibration; p3p9 = v3 rules; 220; 149), axes TCR and TCC.
  TCC rows whose counted event is a stir / mix / whisk action are dropped (user, 11/01).
Claims (prompt temporal_constraint): order = first-occurrence order of ordered_events / expanded_sequence / sequence; sync = value.events;
  counts = event_counts, or value.event + value.count.
Tools, per event (an event the tool cannot measure is skipped; a row with nothing measurable is not scored = tool silent):
  flam     sounding_action events: the first pipeline query of the event in the clip's FLAM record (gen_evidence_1030: hdA / p12A for
           HD-EPIC, matched by clip and event label; 220 / 149 records), audible only if max score >= T_flam (.2705); times = detection
           peak_times (FLAM threshold .98), count = number of detections.
  whisper  speech events: words of segments with no_speech_prob < .5 that match the event's word; times = word starts, count = matches.
  audio    Whisper for speech events + FLAM for sounding events on one timeline (needed for the generated mixed items).
  caption  AVoCaDO caption (HD-EPIC fps 2 plain, generated fps 8 plain): mentions of the event (action verb lemma; speech: the quoted
           word); order = first-mention token position; count = mentions, or an explicit count word right after a mention
           ("twice", "two times", ...).
  qwen3s   existing Qwen3-VL 3-sample scores (screen_1031/qwen3s/scores_all.csv), reported as stored (threshold k = 4 of 0-3: never open).
Row score (higher = more FAIL-like): order -> max over claimed pairs (a before b) of t_a - t_b (s; caption: 1 if any pair is reversed,
  else 0); sync -> max |t_a - t_b|; count -> max over events |tool count - claimed count|.
Threshold per tool and axis: on p1p2 PASS rows with a score, the smallest theta with FA (score > theta) <= .05, written to
  T2AV_data/tools/screen_1031/tc_1102/thresholds.json BEFORE any other set is scored. No p1p2 PASS row with a score -> no threshold
  (closed by gate: cannot be calibrated). Applied unchanged to p3p9, 220, 149.
Report per tool, axis, set, model: n rows, n scored, open rate (over all rows), FA on PASS rows, agreement with the human label when open,
  recall on FAIL rows, and the media-only row 1 on the same open rows (HD-EPIC: hd_rows_scored_1101.csv row1; generated:
  gen_rows_scored_1030.csv row1).
  python gepa_stage2/tc_screen_1102.py
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import glob, json, os, re, sys, time
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import screen_common_1031 as S
import gen_stage2_1030 as G
import hd_rows_score_1101 as HR

EV = Path((_tp.DATA + "/tools/gen_evidence_1030"))
OUT = S.OUT / "tc_1102"
CAPD = Path((_tp.DATA + "/real_av/eval/hdepic_main_1101_captions"))
T_FLAM = json.load(open(EV / "flam_threshold.json"))["T_flam"]
STIR = re.compile(r"\b(stir|mix|whisk)", re.I)
NUM = {"once": 1, "twice": 2, "thrice": 3, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def norm(t):
    return re.findall(r"[a-z']+", t.lower())


def stem(w):
    for suf in ("ing", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


# ------------------------------------------------------------------ claims
def claims(item):
    tc = item.get("temporal_constraint") or {}
    v = tc.get("value") or {}
    seq = v.get("expanded_sequence") or v.get("ordered_events") or v.get("sequence") or []
    order = list(dict.fromkeys(seq)) if tc.get("task_type") == "order" or v.get("ordered_events") else []
    sync = list(v.get("events") or []) if tc.get("task_type") == "sync" else []
    counts = dict(v.get("event_counts") or {})
    if not counts and "event" in v and "count" in v:
        counts = {v["event"]: int(v["count"])}
    return order, sync, counts


# ------------------------------------------------------------------ tool readings
_REC = None


def flam_index():
    global _REC
    if _REC is None:
        _REC = {}
        for d in ("hdA", "p12A", "220", "149"):
            for f in sorted(glob.glob(str(EV / d / "*.json"))):
                r = json.load(open(f))
                k = os.path.realpath(r["video"])
                if k not in _REC or r["item_id"].endswith("_pass"):      # prefer the original's record of a clip
                    _REC[k] = r
    return _REC


def flam_read(r, ev):
    rec = flam_index().get(os.path.realpath(r["video"]))
    if rec is None or ev["modality"] != "sounding_action":
        return None
    lab = (ev.get("action") or "").strip().lower()
    qs = [e["queries"][0] for e in rec.get("events", []) if e.get("queries") and e.get("label", "").strip().lower() == lab]
    if not qs and len(rec.get("events", [])) and r["set"] in ("220", "149"):
        snd = [e for e in rec["events"] if e.get("queries")]
        qs = [snd[0]["queries"][0]] if len(snd) == 1 else []
    if not qs or qs[0] not in rec["flam"]:
        return None
    f = rec["flam"][qs[0]]
    if f["max_score"] < T_FLAM:
        return dict(times=[], count=0, audible=False)
    ds = sorted(f["detections"], key=lambda d: d["peak_time"])
    return dict(times=[d["peak_time"] for d in ds], count=len(ds), audible=True)


def whisper_read(r, ev):
    if ev["modality"] != "speech":
        return None
    rec = flam_index().get(os.path.realpath(r["video"]))
    if rec is None:
        return None
    target = set(norm(ev.get("text", "")))
    ws = [w for s in rec["whisper"].get("segments", []) if s["no_speech_prob"] < 0.5 for w in s.get("words", [])]
    hit = [w["start"] for w in ws if set(norm(w["word"])) & target]
    return dict(times=hit, count=len(hit), audible=True)


_CAP = {}


def caption_of(r):
    if r["set"] in ("p1p2", "p3p9"):
        files = {"p1p2": {"hdepic": "hdepic_p12", "hdmove": "hdmove_p12", "hdfoot": "hdfoot_p12"}.get(r["model"]), "p3p9": "p3p9"}
        name = files[r["set"]]
        if name not in _CAP:
            _CAP[name] = {k.split("/")[0]: v["caption"] for k, v in json.load(open(CAPD / f"{name}.json")).items()}
        return _CAP[name].get(r["item_id"])
    src = {("220", "LTX_2p3"): "g220ltx", ("220", "MOVA"): "g220mova", ("149", "LTX_2p3"): "g149"}[(r["set"], r["model"])]
    return G.caption(src, r["item_id"])


def caption_read(r, ev):
    c = caption_of(r)
    if not c:
        return None
    toks = norm(c)
    st = [stem(t) for t in toks]
    if ev["modality"] == "speech":
        target = set(norm(ev.get("text", "")))
        pos = [i for i, t in enumerate(toks) if t in target]
    else:
        words = norm(ev.get("action") or "")
        if not words:
            return None
        v = stem(words[0])
        pos = [i for i, t in enumerate(st) if t == v]
    if not pos:
        return dict(times=[], count=0, audible=False)
    cnt = len(pos)
    for i in pos:
        nxt = toks[i + 1: i + 8]
        for k, w in enumerate(nxt):
            if w in ("twice", "thrice", "once"):
                cnt = max(cnt, NUM[w]); break
            if w in NUM and k + 1 < len(nxt) and nxt[k + 1] == "times":
                cnt = max(cnt, NUM[w]); break
    return dict(times=[float(p) for p in pos], count=cnt, audible=True)


def audio_read(r, ev):
    """combined audio timeline: Whisper word times for speech events, FLAM peaks for sounding events"""
    return whisper_read(r, ev) if ev["modality"] == "speech" else flam_read(r, ev)


READ = {"flam": flam_read, "whisper": whisper_read, "audio": audio_read, "caption": caption_read}


def row_score(r, tool):
    """(score or None, n measurable events, kind)"""
    order, sync, counts = claims(r["item"])
    evs = {e["id"]: e for e in r["item"]["events"]}
    rd = {i: READ[tool](r, evs[i]) for i in evs}
    if r["axis"] == "TCR":
        seq = order or sync
        m = [i for i in seq if rd.get(i) and rd[i]["times"]]
        if len(m) < 2:
            return None, len(m), "order" if order else "sync"
        t = {i: rd[i]["times"][0] for i in m}
        if order:
            d = max(t[a] - t[b] for x, a in enumerate(m) for b in m[x + 1:])
            return (float(d > 0) if tool == "caption" else d), len(m), "order"
        return max(abs(t[a] - t[b]) for x, a in enumerate(m) for b in m[x + 1:]), len(m), "sync"
    m = [i for i in counts if i in evs and rd.get(i) is not None and not STIR.search(evs[i].get("action") or "")]
    if not m:
        return None, 0, "count"
    return max(abs(rd[i]["count"] - int(counts[i])) for i in m), len(m), "count"


def media_only():
    ref = {}
    d = pd.read_csv(HERE / "runs/obsval_1028/hd_rows_scored_1101.csv")
    for r in d[d.row == "row1"].itertuples():
        s, iid, ax = r.uid.split("|")
        ref[({"hdepic_p12": "p1p2", "hdmove_p12": "p1p2"}.get(s, s), iid, ax)] = r.pred
    g = pd.read_csv(HERE / "runs/obsval_1028/gen_rows_scored_1030.csv")
    for r in g[g.row == "row1"].itertuples():
        s, m, iid, ax = r.uid.split("|")
        ref[(s, iid, ax)] = r.pred
    return ref


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    R = {w: [r for r in S.rows(w) if r["axis"] in ("TCR", "TCC") and not (r["axis"] == "TCC" and r["item_id"] in HR.TCC_STIR_DROP)]
         for w in ("p1p2", "p3p9", "220", "149")}
    rows = []
    for w, rs in R.items():
        for r in rs:
            for tool in READ:
                s, nm, kind = row_score(r, tool)
                rows.append(dict(set=w, model=r["model"] if w != "p3p9" else "P03-P09", participant=r["model"], item_id=r["item_id"], axis=r["axis"],
                                 kind=kind, y=r["y"], tool=tool, score=s, n_meas=nm))
    D = pd.DataFrame(rows)
    # thresholds from p1p2 PASS rows only, written before scoring the other sets
    th = {}
    for (tool, ax), g in D[(D.set == "p1p2") & (D.y == "yes")].groupby(["tool", "axis"]):
        for kind, h in g.groupby("kind"):
            s = h.score.dropna().values
            if not len(s):
                th[f"{tool}|{ax}|{kind}"] = dict(threshold=None, n_pass_scored=0, note="no p1p2 PASS row with a score: cannot be calibrated")
                continue
            cand = sorted(set(s.tolist()) | {min(s) - 1})
            theta = next(c for c in cand if np.mean(s > c) <= 0.05)
            th[f"{tool}|{ax}|{kind}"] = dict(threshold=float(theta), n_pass_scored=int(len(s)), fa_on_p1p2=float(np.mean(s > theta)),
                                             n_pass_rows=int(len(h)), rule="FAIL if score > threshold")
    for tool in READ:
        for ax, kinds in (("TCR", ("order", "sync")), ("TCC", ("count",))):
            for kind in kinds:
                th.setdefault(f"{tool}|{ax}|{kind}", dict(threshold=None, n_pass_scored=0, note="no p1p2 PASS row of this kind"))
    th["_written"] = time.strftime("%Y-%m-%dT%H:%M:%S"); th["_T_flam"] = T_FLAM
    json.dump(th, open(OUT / "thresholds.json", "w"), indent=1)
    ref = media_only()

    def fail_call(r):
        t = th.get(f"{r.tool}|{r.axis}|{r.kind}", {}).get("threshold")
        return None if (t is None or pd.isna(r.score)) else bool(r.score > t)
    D["tool_fail"] = [fail_call(r) for r in D.itertuples()]
    D["mo"] = [ref.get((r.set, r.item_id, r.axis), "") for r in D.itertuples()]
    D.to_csv(OUT / "rows.csv", index=False)
    tab = []
    for (tool, ax, w, m), g in D.groupby(["tool", "axis", "set", "model"]):
        op = g[g.tool_fail == True]
        fail = g[g.y == "no"]; pas = g[g.y == "yes"]
        om = op[op.mo.isin(["yes", "no"])]
        tab.append(dict(tool=tool, axis=ax, set=w, model=m, n=len(g), n_fail=len(fail), n_scored=int(g.score.notna().sum()),
                        open=len(op), open_rate=round(len(op) / len(g), 3), FA_pass=round(float((pas.tool_fail == True).mean()), 3) if len(pas) else None,
                        agree_open=round(float((op.y == "no").mean()), 3) if len(op) else None,
                        recall=round(float((fail.tool_fail == True).mean()), 3) if len(fail) else None,
                        open_with_mo=len(om), mo_agree_open=round(float((om.mo == om.y).mean()), 3) if len(om) else None,
                        tool_agree_same=round(float((om.y == "no").mean()), 3) if len(om) else None))
    T = pd.DataFrame(tab)
    T.to_csv(OUT / "report.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    print(json.dumps(th, indent=1))
    print(T.to_string(index=False))
    # diagnostics, not gates: what the never-open tools would look like (no threshold from p3p9 / generated is used anywhere)
    from sklearn.metrics import roc_auc_score
    for (tool, ax, kind), g in D.groupby(["tool", "axis", "kind"]):
        for w, h in g.groupby("set"):
            h = h[h.score.notna()]
            if len(h) >= 10 and h.y.nunique() == 2:
                print(f"[diag] {tool} {ax} {kind} {w}: scored {len(h)}, AUC {roc_auc_score(h.y == 'no', h.score):.2f}, "
                      f"PASS with score > 0: {(h[h.y == 'yes'].score > 0).mean():.2f}, FAIL with score > 0: {(h[h.y == 'no'].score > 0).mean():.2f}")


if __name__ == "__main__":
    main()
