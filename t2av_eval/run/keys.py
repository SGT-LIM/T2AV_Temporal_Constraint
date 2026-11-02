"""Gemini keys from the environment only: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, ...

A key is identified in READMEs and logs by its variable name and the first 8 hex digits of its sha256; the key itself is
never written anywhere. Shard i uses key i mod n. A shard process gets its key as GEMINI_API_KEY (what the judge code reads)
and no other key variable.
"""
import hashlib, os, re

_VAR = re.compile(r"^GEMINI_API_KEY(?:_(\d+))?$")


def gemini_keys(env=None):
    """[(variable name, value)] in order GEMINI_API_KEY, _2, _3, ...; empty values skipped"""
    env = os.environ if env is None else env
    found = [(int(m.group(1) or 1), k) for k in env if (m := _VAR.match(k)) and env[k].strip()]
    return [(k, env[k].strip()) for _, k in sorted(found)]


def key_id(name, value):
    return f"{name}:{hashlib.sha256(value.encode()).hexdigest()[:8]}"


def for_shard(i, keys):
    if not keys:
        raise RuntimeError("no Gemini key in the environment (GEMINI_API_KEY, GEMINI_API_KEY_2, ...)")
    return keys[i % len(keys)]


def shard_env(base, name, value):
    """environment of a shard process: every key variable removed, the chosen key as GEMINI_API_KEY, its id as T2AV_KEY_ID"""
    env = {k: v for k, v in base.items() if not _VAR.match(k) and k != "GOOGLE_API_KEY"}
    env.update(GEMINI_API_KEY=value, T2AV_KEY_ID=key_id(name, value))
    return env
