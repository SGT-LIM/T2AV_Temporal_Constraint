#!/usr/bin/env python3
"""Client side of --judge-backend local: send one axis call to local_judge_server.py.

Same contract as agentic_common.call_gemini_json: returns (parsed_json, raw_text).
Server URL from --local-judge-url (ctx.config["local_judge_url"]) or env LOCAL_JUDGE_URL.
The video is passed as a PATH (server and shards share the filesystem); no upload.
"""
import json, os, time
from pathlib import Path

import requests

import new_eval as NE

DELAYS = [15, 30, 60, 120]


def call_local_json(ctx, system_prompt: str, user_text: str, schema: dict):
    cfg = ctx.config
    url = (cfg.get("local_judge_url") or os.environ.get("LOCAL_JUDGE_URL") or "http://127.0.0.1:8010").rstrip("/")
    mode = cfg.get("media_input_mode", "video") or "video"
    video = None if mode == "language_only" else cfg.get("video_path")
    if mode == "audio_only":
        raise RuntimeError("local backend: audio_only not supported (send the video with use_audio instead)")
    tl = str(cfg.get("thinking_level") or "high").lower()
    payload = {
        "system": system_prompt, "user": user_text, "video": video, "schema": schema,
        "use_audio": True, "thinking": tl != "none",
        "reasoning_budget": {"low": 2048, "high": 8192}.get(tl, 8192),
        "max_tokens": int(cfg.get("local_max_tokens") or 12288), "temperature": 0.0,
    }
    last = None
    for attempt in range(len(DELAYS) + 1):
        try:
            r = requests.post(url + "/judge", json=payload, timeout=3600)
            r.raise_for_status()
            box = r.json()
            if "error" in box:
                raise RuntimeError(box["error"])
            raw = box.get("text", "") or ""
            # provenance for the CSV (uploaded_file_uri column)
            cfg.setdefault("_local_prov", f"local:{url} think={payload['thinking']} tokens={box.get('tokens')}")
            return NE.parse_model_json(raw), raw
        except Exception as e:
            last = e
            if attempt == len(DELAYS):
                raise
            print(f"    [RETRY {attempt + 1}/{len(DELAYS)}] local judge: {type(e).__name__}: {str(e)[:200]} "
                  f"-> {DELAYS[attempt]}s", flush=True)
            time.sleep(DELAYS[attempt])
    raise last
