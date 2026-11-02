"""Cache keys under the canonical data root (paths.canonical_video).

- On SCC (default data_root) the canonical path is exactly str(Path(video).resolve()), so the audio-evidence key equals the
  legacy key and no existing cache entry is renamed.
- With the data copied elsewhere (same layout, data_root overridden), the audio-evidence key, the Synchformer section lookup
  and the caption cache file equal what they are on SCC.
- The other caches a collaborator reuses carry no paths: Gemini call cache (calls/<cond>/<set>__<uid>.json and the user
  prompt md5 inside), the stored row 1 / 2 prompts and raw outputs, and the stage-1 lookup (item_id).
"""
import importlib.util, json, os
from pathlib import Path

import pandas as pd
import pytest

from t2av_eval import paths as P
from t2av_eval.evidence import captions as CAP
from t2av_eval.judge.media import common as AC
from t2av_eval.judge.media import core as NE

REPO = Path(__file__).resolve().parents[1]
FX = REPO / "tests/fixtures/replay_1101"
SCC = Path("/projectnb/ivc-ml/youngsun/T2AV_data")
META = {"events": [{"kind": "sounding_action", "label": "close drawer"}, {"kind": "silent_action", "label": "open drawer"}],
        "original_item_id": "x"}
KW = dict(audio_evidence_mode="whisper_flam", whisper_model_size="large-v3", flam_model_name="v1-base", flam_hop_sec=5.0,
          flam_threshold=0.98, flam_device="cuda")


def _legacy_key():
    spec = importlib.util.spec_from_file_location("legacy_new_eval_keys", REPO / "legacy/evaluation/ablation/new_eval.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m._audio_evidence_cache_key


def test_root_is_scc_default():
    assert P.CACHE_KEY_DATA_ROOT == SCC


@pytest.mark.skipif(os.environ.get("T2AV_DATA_ROOT") not in (None, "", str(SCC)), reason="data_root overridden")
def test_scc_keys_unchanged():
    legacy = _legacy_key()
    vids = sorted(FX.rglob("*.mp4"))
    assert vids
    for v in vids:
        assert P.canonical_video(v) == str(v.resolve())
        assert NE._audio_evidence_cache_key(v, META, KW) == legacy(v, META, KW)


def test_relocated_root_gives_scc_keys(tmp_path, monkeypatch):
    rel = Path("real_av/hdepic/clips/P01-x_orig.mp4")
    data = tmp_path / "data"
    (data / rel).parent.mkdir(parents=True)
    (data / rel).write_bytes(b"")
    link = tmp_path / "videos/hdepic_p12/item/item_v1_raw.mp4"      # run dirs hold symlinks to the clips, as on SCC
    link.parent.mkdir(parents=True)
    os.symlink(data / rel, link)
    monkeypatch.setattr(P, "DATA", data)

    assert P.canonical_video(link) == str(SCC / rel)
    assert NE._audio_evidence_cache_key(link, META, KW) == _legacy_key()(SCC / rel, META, KW)

    sync = tmp_path / "sync.json"
    sync.write_text(json.dumps({str(SCC / rel): "## Synchformer\nreading"}))
    monkeypatch.setenv("T2AV_SYNC_EVIDENCE_JSON", str(sync))
    monkeypatch.setattr(AC, "_SYNC_MAP", None)
    assert AC.sync_section(link) == "## Synchformer\nreading"

    # caption cache file = <stem of the path the caller passes>__backend__style__<digest of the canonical path>; the run dir
    # passes the same link name on SCC and elsewhere, so only the digest depends on where the data lives
    here = CAP._cache_path(tmp_path, link, "external", "m", "plain").name
    monkeypatch.setattr(P, "DATA", SCC)
    scc = CAP._cache_path(tmp_path, SCC / rel, "external", "m", "plain").name
    assert here.startswith(link.stem + "__external__plain__") and here.rsplit("__", 1)[1] == scc.rsplit("__", 1)[1]


def test_outside_data_root_unchanged(tmp_path):
    f = tmp_path / "v.mp4"
    f.write_bytes(b"")
    assert P.canonical_video(f) == str(f.resolve())


def test_other_caches_carry_no_paths():
    for f in (FX / "stage2/out/calls").rglob("*.json"):
        assert "/projectnb" not in f.name
        rec = json.load(open(f))
        assert "/projectnb" not in json.dumps({k: rec.get(k) for k in ("parsed", "raw", "anchor", "uid", "set")}), f.name
    for line in open(FX / "stage2/out/rows.jsonl"):
        assert "/projectnb" not in line
    for f in (FX / "rows").rglob("*.csv"):
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        for c in ("user_prompt", "raw_output", "item_id"):
            assert not d[c].str.contains("/projectnb", regex=False).any(), (f.name, c)
        assert not d.item_id.str.contains("/", regex=False).any()
