#!/usr/bin/env python3
"""Replay stage 2 of the 11/01 HD-EPIC table (rows 4, 5, 5-rule and framing b / c) from the call cache, with zero Gemini calls.

The code under test (--code: a legacy module directory, or "package" for t2av_eval.judge.stage2.hdepic) is imported and
its input paths are pointed at the fixture: tool records (FLAM, captions, Synchformer, the pre-registered rule), the row 1
anchor rows, the prompt files, rows.jsonl and the call cache. Then, for every cached call row:
  - the tool text the code builds now must equal the text stored in rows.jsonl (A / V / AVB, gated A for HG5, + framing note);
  - the user prompt the code builds now must have the md5 stored in the call record (prompt drift check);
  - the md5 of the system prompt and response schema it builds is reported (the test compares them to the pinned values);
and the real stage_score() writes hd_stage2_rows_1101.csv into the fixture copy, which the test compares to the 11/01 file.
google.genai.Client is replaced by a class that raises, so any call attempt fails the run.

  python run_stage2.py --code DIR --fixture FIXTURE_COPY --report OUT.json
"""
import argparse, hashlib, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--code", required=True)
ap.add_argument("--fixture", required=True)
ap.add_argument("--report", required=True)
a = ap.parse_args()
F = Path(a.fixture).resolve()


class _NoClient:
    def __init__(self, *x, **k):
        raise RuntimeError("replay: Gemini client constructed")


import google.genai as genai
genai.Client = _NoClient
import importlib
if a.code == "package":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    H = importlib.import_module("t2av_eval.judge.stage2.hdepic")
else:
    code = Path(a.code).resolve()
    sys.path.insert(0, str(code)); sys.path.insert(0, str(code / "gepa_stage2"))
    H = importlib.import_module("hd_stage2_1101")
O, G = H.O, H.G
# every loaded copy of the observation judge (legacy obs_judge_1028 and/or the package module) gets the fixture paths
OJS = [m for m in list(sys.modules.values()) if hasattr(m, "OBS_RULES_MD5") and hasattr(m, "ANCHOR") and hasattr(m, "PROMPTS")]

S2 = F / "stage2"
for m in OJS:
    m.OUT = S2 / "out"
H.EVD, H.CAPD, H.SYA, H._PE, H._CAP = S2 / "evd", S2 / "captions", S2 / "sya", None, {}
H.RULE = json.load(open(S2 / "sya" / "PREREGISTERED_RULE.json"))  # replaced by the gate module once it moves
SETFILE = {"hm_hdepic": "hdepic_p12", "hm_hdfoot": "hdfoot_p12", "hm_p3p9": "p3p9"}
for m in OJS:
    for src, s in SETFILE.items():
        m.ANCHOR[src] = [F / "rows" / "row1" / f"{s}.csv"]
        m.PROMPTS[src] = F / "prompts" / f"{s}.json"
GT = json.load(open(S2 / "gt_rows.json"))
H.gt_rows = lambda: [dict(r) for r in GT]

rows = [r for r in O.jl(O.OUT / "rows.jsonl") if r["cond"] == H.COND]
gt_by_uid = {r["uid"]: r for r in GT}
S = G.framing_sentences()
text_bad, md5_bad, checked, sysmd5 = [], [], 0, {}
for r in rows:
    g = gt_by_uid[r["uid"]]
    src, iid, ax = g["source"], g["item_id"], g["axis"]
    base = {"A": H.a_text, "V": H.v_text, "AVB": H.avb_text}[ax]
    if r["set"] == H.SETS["row5"]:
        want = H.a_text(src, iid, gated=True)
    elif r["set"] in (H.SETS["frb"], H.SETS["frc"]):
        b, c = S[ax]
        want = base(src, iid) + "\n\nNote: " + (b if r["set"] == H.SETS["frb"] else c)
    else:
        want = base(src, iid)
    if want != r["obs"]["text"]:
        text_bad.append(dict(uid=r["uid"], set=r["set"], now=want, stored=r["obs"]["text"]))
    f = O.OUT / "calls" / H.COND / f"{r['set']}__{r['uid']}.json"
    rec = json.load(open(f))
    c = O.build_call(r)
    now = hashlib.md5(c["user"].encode()).hexdigest() if c else None
    if now != rec.get("user_md5"):
        md5_bad.append(dict(uid=r["uid"], set=r["set"], now=now, stored=rec.get("user_md5")))
    sysmd5[f"{r['set']}|{r['uid']}"] = dict(system_md5=hashlib.md5(c["system"].encode()).hexdigest(),
                                            schema_md5=hashlib.md5(json.dumps(c["schema"], sort_keys=True).encode()).hexdigest()) if c else None
    if rec.get("rules_md5") != O.OBS_RULES_MD5:
        md5_bad.append(dict(uid=r["uid"], set=r["set"], what="rules_md5", now=O.OBS_RULES_MD5, stored=rec.get("rules_md5")))
    checked += 1

H.stage_score(None)
json.dump(dict(modules=sorted({m.__file__ for m in (H, O, G, *OJS)}), checked_calls=checked, text_mismatch=text_bad, prompt_md5_mismatch=md5_bad, call_settings=sysmd5), open(a.report, "w"), indent=1)
