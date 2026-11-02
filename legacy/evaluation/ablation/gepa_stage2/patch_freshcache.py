#!/usr/bin/env python3
"""Add the fresh-stage-1 disk cache to run_two_stage.py and gepa_stage2/adapter.py (10/21 B-3 prerequisite).
Run from evaluation/ablation:  python gepa_stage2/patch_freshcache.py
Idempotent; makes .bak_freshcache backups; aborts without writing if an anchor line is missing."""
import re, shutil, sys
from pathlib import Path

RT = Path("run_two_stage.py"); AD = Path("gepa_stage2/adapter.py")
for p in (RT, AD):
    if not p.exists():
        sys.exit(f"missing {p} (run from evaluation/ablation)")

# ---------------- run_two_stage.py
s = RT.read_text()
if "FRESH_CACHE_DIR" in s:
    print("run_two_stage.py already patched")
else:
    a1 = "def fresh_stage1(ctx, axis, criteria, rules, only_event_ids):"
    a2 = "    saved_ev, saved_tools = ctx.evidence, dict(ctx.use_tools)"
    a3 = ("    if axis == TCR:\n"
          "        return [dict(label=str(parsed.get(\"label\", \"\")).lower(), reason=parsed.get(\"reason\", \"\"), evidence=parsed.get(\"evidence\", \"\"))]\n"
          "    return list(parsed.get(\"per_event\", []))\n")
    for a in (a1, a2, a3):
        if s.count(a) != 1:
            sys.exit(f"anchor not found exactly once in run_two_stage.py: {a[:60]!r}")
    i1 = s.index(a1); i2 = s.index(a2); i3 = s.index(a3)
    tail = ("    if axis == TCR:\n"
            "        out = [dict(label=str(parsed.get(\"label\", \"\")).lower(), reason=parsed.get(\"reason\", \"\"), evidence=parsed.get(\"evidence\", \"\"))]\n"
            "    else:\n"
            "        out = list(parsed.get(\"per_event\", []))\n")
    s = (s[:i1]
         + "FRESH_CACHE_DIR = None   # set by gepa_stage2 adapters: fresh stage-1 results cached per (item, axis, events), independent of the rules\n\n\n"
         + s[i1:i2]
         + "    cache = None\n"
           "    if FRESH_CACHE_DIR:\n"
           "        key = f\"{ctx.item_meta.get('item_id')}|{axis}|{','.join(only_event_ids) if only_event_ids else 'all'}\"\n"
           "        cache = Path(FRESH_CACHE_DIR) / (re.sub(r\"[^A-Za-z0-9_.|,-]\", \"_\", key) + \".json\")\n"
           "        if cache.exists():\n"
           "            return json.load(open(cache))\n"
         + s[i2:i3]
         + tail
         + "    if cache is not None:\n"
           "        cache.parent.mkdir(parents=True, exist_ok=True)\n"
           "        json.dump(out, open(cache, \"w\"), default=str)\n"
           "    return out\n"
         + s[i3 + len(a3):])
    shutil.copy(RT, str(RT) + ".bak_freshcache"); RT.write_text(s)
    print("run_two_stage.py patched")

# ---------------- gepa_stage2/adapter.py
s = AD.read_text()
if "FRESH_CACHE_DIR" in s:
    print("adapter.py already patched")
else:
    a = "        from google import genai\n        self.client = genai.Client()\n"
    if s.count(a) != 1:
        sys.exit("anchor not found exactly once in adapter.py (genai.Client in __init__)")
    s = s.replace(a, "        # fresh stage-1 calls are shared by every run under gepa_stage2/, independent of rules\n"
                     "        TS.FRESH_CACHE_DIR = Path(__file__).resolve().parent / \"fresh_stage1_cache\"\n" + a)
    shutil.copy(AD, str(AD) + ".bak_freshcache"); AD.write_text(s)
    print("adapter.py patched")
print("check:", "FRESH_CACHE_DIR" in RT.read_text(), "FRESH_CACHE_DIR" in AD.read_text())
