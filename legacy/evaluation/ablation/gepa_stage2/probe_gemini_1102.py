#!/usr/bin/env python3
"""One-call quota probe for the 11/02 auto-start (gemini-3.6-flash, short text prompt, thinking low).
Exit 0 = call ok, 2 = 429 RESOURCE_EXHAUSTED, 1 = any other error. Prints one line with the time and the outcome.
  python gepa_stage2/probe_gemini_1102.py
"""
import os, sys, time
from google import genai
from google.genai import types, errors as ge

t = time.strftime("%Y-%m-%dT%H:%M:%S")
key = os.environ.get("GEMINI_API_KEY")
if not key:
    print(f"{t} probe: GEMINI_API_KEY missing"); sys.exit(1)
try:
    client = genai.Client(api_key=key)     # keep a reference: a temporary client is closed before the call
    r = client.models.generate_content(
        model="gemini-3.6-flash", contents="Reply with the single word OK.",
        config=types.GenerateContentConfig(temperature=0.0, thinking_config=types.ThinkingConfig(thinking_level="low")))
    print(f"{t} probe: ok ({(r.text or '').strip()[:20]!r})"); sys.exit(0)
except ge.ClientError as e:
    code = getattr(e, "code", None)
    print(f"{t} probe: ClientError {code}: {str(e)[:200]}"); sys.exit(2 if code == 429 else 1)
except Exception as e:
    print(f"{t} probe: {type(e).__name__}: {str(e)[:200]}"); sys.exit(1)
