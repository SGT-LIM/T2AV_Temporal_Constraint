"""Regression: replay the 11/01 HD-EPIC table from stored calls, zero Gemini calls, and require the 11/01 labels.

Fixture: tests/fixtures/replay_1101 (frozen by tests/replay_1101/freeze.py; MANIFEST.json has the origin, mtime and sha256 of
every file it was cut from). Rows: 3 per axis.
  rows 1 / 2  A, V, AVB, TCR, TCC  run_agentic_eval with the recorded 11/01 command; each model call is served the stored raw
                                   text of the stored call whose user prompt is identical (so prompts are checked too); system
                                   prompt and schema md5 must equal the pinned values (expected/call_settings.json)
  stage 2     A, V, AVB            rows 4 / 5 / 5-rule / framing b, c from the call cache through the real stage_score()
Code under test: every implementation in T2AV_REPLAY_CODE (comma list; default "legacy,package,cli"): legacy =
legacy/evaluation/ablation, package = t2av_eval, cli = t2av_eval through the CLI shard entry (paced client, stop hooks). A package case is skipped only while its entry module has not been moved yet.

  pytest tests/test_replay_1101.py -v
"""
import hashlib, importlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
FX = REPO / "tests/fixtures/replay_1101"
LEGACY = REPO / "legacy/evaluation/ablation"
IMPLS = os.environ.get("T2AV_REPLAY_CODE", "legacy,package,cli").split(",")
ENTRY = {"rows": "t2av_eval/judge/media/runner.py", "stage2": "t2av_eval/judge/stage2/hdepic.py"}


def code_for(impl, what):
    if impl == "legacy":
        return LEGACY
    if impl == "cli":
        return "cli"
    if not (REPO / ENTRY[what]).exists():
        pytest.skip(f"{ENTRY[what]} not moved yet")
    return "package"


def scoring(impl):
    """the stage1_lookup scorer of the implementation under test"""
    if impl == "package" and (REPO / "t2av_eval/scoring/lookup.py").exists():
        sys.path.insert(0, str(REPO))
        return importlib.import_module("t2av_eval.scoring.lookup")
    spec = importlib.util.spec_from_file_location("legacy_rep_scoring", LEGACY / "gepa_stage2/rep_scoring.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m
sys.path.insert(0, str(REPO / "tests/replay_1101"))
import common
LABEL_COLS = ["audio_event_correctness", "visual_event_correctness", "audio_visual_binding", "temporal_relation_satisfaction",
              "temporal_count_satisfaction", "constraint_compliance", "overall_temporal_success"]
PE_COLS = [c + "_per_event" for c in LABEL_COLS if c not in ("temporal_relation_satisfaction", "constraint_compliance",
                                                             "overall_temporal_success")]
COMMANDS = json.load(open(FX / "commands.json"))
EXPECTED = pd.read_csv(FX / "expected/rows_scored.csv", dtype=str).fillna("")
SETTINGS = json.load(open(FX / "expected/call_settings.json"))


def _gt():
    """GT dict per scored uid (set|item|axis): A / V / AVB from the frozen gt_rows, TCR / TCC item level."""
    hm2set = {"hm_hdepic": "hdepic_p12", "hm_hdfoot": "hdfoot_p12", "hm_p3p9": "p3p9"}
    out = {f"{hm2set[r['source']]}|{r['item_id']}|{r['axis']}": r["gt"] for r in json.load(open(FX / "stage2/gt_rows.json"))}
    out.update({r["uid"]: r["gt"] for r in json.load(open(FX / "expected/tc_item_gt.json"))})
    return out


def test_fixture_unchanged():
    man = json.load(open(FX / "MANIFEST.json"))
    assert man["files"] and all(v["same"] for v in man["code_md5_vs_1101_runs"].values())
    bad = [f for f, h in man["files"].items() if hashlib.sha256((FX / f).read_bytes()).hexdigest() != h]
    assert not bad, f"fixture files differ from MANIFEST.json: {bad}"
    assert {k: os.readlink(FX / k) for k in man["video_symlinks"]} == man["video_symlinks"]


@pytest.mark.parametrize("impl", IMPLS)
@pytest.mark.parametrize("row,s", sorted(tuple(k.split("|")) for k in COMMANDS))
def test_rows_replay(row, s, impl, tmp_path):
    out, rep = tmp_path / "out.csv", tmp_path / "report.json"
    argv, env = common.rows_cmd(FX, code_for(impl, "rows"), row, s, COMMANDS[f"{row}|{s}"], out, rep)
    if row == "row2":
        assert env.get("T2AV_AUDIO_EVIDENCE_CACHE_ONLY") == "1"
    p = subprocess.run(argv, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    r = json.load(open(rep))
    assert r["unmatched"] == [], f"prompts with no identical 11/01 prompt: {r['unmatched']}"
    assert len(r["served"]) == r["n_stored_prompts"], "not every stored call was replayed"
    if impl == "cli":
        assert r["pace_count"] == len(r["served"]) and not r["stop_file"] and r["rc"] == 0
    assert {(x["model"], x["temperature"], x["seed"], x["thinking"]) for x in r["served"]} == {("gemini-3.6-flash", 0.0, 42, "high")}
    for x in r["served"]:
        assert dict(system_md5=x["system_md5"], schema_md5=x["schema_md5"]) == SETTINGS[f"{row}|{x['key']}"], f"system prompt / schema: {row} {x['key']}"

    stored_csv = FX / "rows" / row / f"{s}.csv"
    new = pd.read_csv(out, engine="python", dtype=str, keep_default_na=False).set_index("item_id")
    old = pd.read_csv(stored_csv, engine="python", dtype=str, keep_default_na=False).set_index("item_id")
    assert sorted(new.index) == sorted(old.index)
    for iid in old.index:
        for col in LABEL_COLS + ["user_prompt", "raw_output"]:
            assert new.at[iid, col] == old.at[iid, col], f"{row} {iid} {col}"
        for col in PE_COLS:
            assert json.loads(new.at[iid, col]) == json.loads(old.at[iid, col]), f"{row} {iid} {col}"

    RS = scoring(impl)
    df = RS.load([str(out)])
    gt = _gt()
    exp = EXPECTED[(EXPECTED.row == row) & EXPECTED.uid.str.startswith(s + "|")]
    assert len(exp)
    for e in exp.itertuples():
        _, iid, ax = e.uid.split("|")
        assert RS.row_label(df, iid, ax, gt[e.uid]) == e.pred, f"{row} {e.uid}"


@pytest.mark.parametrize("impl", [i for i in IMPLS if i != "cli"])     # stage-2 replay makes no calls: no CLI-specific path
def test_stage2_replay(impl, tmp_path):
    code = code_for(impl, "stage2")
    fx = tmp_path / "fx"
    shutil.copytree(FX, fx, symlinks=True)
    rep = tmp_path / "report.json"
    argv, env = common.stage2_cmd(fx, code, rep)
    p = subprocess.run(argv, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-2000:]
    r = json.load(open(rep))
    n_calls = len(list((FX / "stage2/out/calls/gen_tool_text").glob("*.json")))
    assert r["checked_calls"] == n_calls
    assert r["text_mismatch"] == [], r["text_mismatch"]
    assert r["prompt_md5_mismatch"] == [], r["prompt_md5_mismatch"]
    assert {f"stage2|{k}": v for k, v in r["call_settings"].items()} == {k: v for k, v in SETTINGS.items() if k.startswith("stage2|")}

    cols = ["uid", "axis", "variant", "y", "row1", "row4", "admitted", "row5", "FRb", "FRc", "row5_rule"]
    new = pd.read_csv(fx / "stage2/out/hd_stage2_rows_1101.csv", dtype=str).fillna("").reindex(columns=cols, fill_value="")
    old = pd.read_csv(FX / "expected/stage2_rows.csv", dtype=str).fillna("").reindex(columns=cols, fill_value="")
    pd.testing.assert_frame_equal(new.sort_values("uid").reset_index(drop=True), old.sort_values("uid").reset_index(drop=True))
    assert set(old.axis) == {"A", "V", "AVB"} and old.groupby("axis").size().min() == 3
