"""Gemini Files storage check before a launch that uploads clips (media conditions): per key, free storage (cap minus the
sum of size_bytes of the listed files) must be at least the clips this key's shards will upload plus a margin. Uploads are
deleted after use during the run (T2AV_DELETE_UPLOADS=1), so only the launch is checked; there is no mid-run pause."""
from pathlib import Path


def used_gb(client):
    return sum((getattr(f, "size_bytes", 0) or 0) for f in client.files.list()) / 1e9


def needed_gb(videos):
    return sum(Path(v).stat().st_size for v in videos if Path(v).exists()) / 1e9


def check(clients_need, cap_gb, margin_gb, used=used_gb):
    """clients_need: {key id: (client, needed GB)} -> ({key id: (used, free, needed)}, list of failures)"""
    out, bad = {}, []
    for kid, (client, need) in clients_need.items():
        u = used(client)
        free = cap_gb - u
        out[kid] = (round(u, 2), round(free, 2), round(need, 2))
        if free < need + margin_gb:
            bad.append(f"{kid}: free {free:.2f} GB < needed {need:.2f} + {margin_gb} GB")
    return out, bad
