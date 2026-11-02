#!/usr/bin/env python3
"""Replay one recorded run_agentic_eval command (row 1 or row 2 of the 11/01 HD-EPIC table) with zero Gemini calls.

The code under test is --code: a legacy module directory (legacy/evaluation/ablation) or "package" (t2av_eval). Only the
network edge is replaced, on every loaded copy of the core module:
  - google.genai.Client -> a fake whose generate_content serves the stored raw text of the axis whose stored user prompt is
    identical to the prompt the code just built. A prompt with no identical stored prompt is an error (prompt drift).
  - new_eval.upload_and_wait -> a stub handle (no upload).
  - new_eval.find_video_files -> the fixture's video symlinks (they may dangle; the targets are never read when the audio
    evidence comes from the cache).
Writes the run's CSV to --output-csv and a JSON report to --report: served calls (with the md5 of the system prompt and
response schema each call was built with) and unmatched prompts.

  python run_rows.py --code DIR --stored-csv CSV --report OUT.json -- <run_agentic_eval argv>
"""
import argparse, json, os, sys, types as _types
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--code", required=True)
ap.add_argument("--stored-csv", required=True, help="the stored 11/01 rows of the items being replayed")
ap.add_argument("--report", required=True)
ap.add_argument("--workdir", required=True, help="cwd of the run (cwd-relative defaults such as caption_cache/ land here)")
ap.add_argument("--record-audio-keys", default=None, help="append the audio-evidence cache files used to this file")
a, argv = ap.parse_known_args()
argv = [x for x in argv if x != "--"]

import pandas as pd

stored = pd.read_csv(a.stored_csv, engine="python")
SERVE, CLASH = {}, []
for r in stored.itertuples():
    prompts, raws = json.loads(r.user_prompt), json.loads(r.raw_output)
    for ax, u in prompts.items():
        if not u:
            continue
        if u in SERVE and SERVE[u][1] != raws.get(ax, ""):
            CLASH.append((r.item_id, ax))
        SERVE[u] = (f"{r.item_id}|{ax}", raws.get(ax, ""))
if CLASH:
    sys.exit(f"identical stored prompts with different raw outputs: {CLASH}")

served, unmatched = [], []


def _md5(x):
    import hashlib
    return hashlib.md5((x if isinstance(x, str) else json.dumps(x, sort_keys=True)).encode()).hexdigest()


class _Resp:
    def __init__(self, text):
        self.text = text


class _Models:
    def generate_content(self, model, contents, config=None):
        user = contents[-1] if isinstance(contents[-1], str) else None
        if user not in SERVE:
            unmatched.append(dict(model=model, user_head=(user or "")[:300], user_len=len(user or "")))
            raise RuntimeError("replay: no stored call with an identical user prompt")
        key, raw = SERVE[user]
        tl = getattr(getattr(config, "thinking_config", None), "thinking_level", None)
        served.append(dict(key=key, model=model, temperature=getattr(config, "temperature", None), seed=getattr(config, "seed", None),
                           thinking=str(getattr(tl, "value", tl)).lower(),
                           system_md5=_md5(getattr(config, "system_instruction", None)),
                           schema_md5=_md5(getattr(config, "response_json_schema", None))))
        return _Resp(raw)


class _Files:
    def upload(self, *a_, **k):
        raise RuntimeError("replay: upload attempted")


class FakeClient:
    def __init__(self, *a_, **k):
        self.models, self.files = _Models(), _Files()


import google.genai as genai
genai.Client = FakeClient
import importlib
if a.code == "package":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    entry = "t2av_eval.judge.media.runner"
else:
    sys.path.insert(0, a.code)
    entry = "run_agentic_eval"
os.makedirs(a.workdir, exist_ok=True)
os.chdir(a.workdir)
RAE = importlib.import_module(entry)

# patch the network edge on every loaded copy of the core module (legacy new_eval and/or t2av_eval.judge.media.core)
cores = [m for m in list(sys.modules.values()) if all(hasattr(m, x) for x in ("upload_and_wait", "find_video_files", "_audio_evidence_cache_key"))]
assert cores, "core module not found"
for NE in cores:
    NE.upload_and_wait = lambda client, video_path, **k: _types.SimpleNamespace(name="files/replay", uri="replay://" + Path(video_path).name,
                                                                              mime_type="video/mp4")
    NE.find_video_files = lambda outputs_dir: sorted(Path(outputs_dir).rglob("*.mp4"))
    if a.record_audio_keys:
        def _rec(video_path, item_meta, _NE=NE, _orig=NE.build_audio_evidence_section, **kwargs):
            with open(a.record_audio_keys, "a") as f:
                f.write(_NE._audio_evidence_cache_key(video_path, item_meta, kwargs) + ".json\n")
            return _orig(video_path=video_path, item_meta=item_meta, **kwargs)
        NE.build_audio_evidence_section = _rec

sys.argv = ["run_agentic_eval.py"] + argv
try:
    RAE.main()
finally:
    json.dump(dict(served=served, unmatched=unmatched, n_stored_prompts=len(SERVE), entry=RAE.__file__,
                   cores=sorted(m.__file__ for m in cores)), open(a.report, "w"), indent=1)
