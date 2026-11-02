#!/usr/bin/env python3
# Replaced by t2av_eval/judge/stage2/two_stage.py (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.
"""Two-stage judge, full pipeline ("perceive first, evidence second"), all axes.  (refactored 10/19: importable)

Same behaviour as before, plus
  * `install(stage1_dir, rules=None, side=None)`  installs the stage-2 patch from Python (used by gepa_stage2/adapter.py)
  * `set_rules(text)`                               swaps the STAGE2_RULES block at run time
  * `--stage2-rules <file>`                         CLI: use a rules file (e.g. GEPA best candidate) in a normal run
  * `--stage2-text-only`                            CLI: stage 2 without the video (media_input_mode=language_only)

CLI usage is unchanged otherwise:
  cd evaluation/ablation
  python run_two_stage.py --stage1-dir $R/hdepic_medium_multi_baseline [--stage2-rules gepa_stage2/runs/s0/best_candidate.txt] \
      --prompt-json ... --outputs-dir ... --output-csv $R/hdepic_medium_multi_two_stage/shard0.csv \
      --axes all --pose-evidence-mode none $WF --caption-evidence-mode external --caption-style plain \
      --caption-external-json $CAP --model gemini-3.1-pro-preview --thinking-level high
A sidecar <output-csv stem>_stage1.jsonl records the stage-1 judgment that each stage-2 call saw.
"""
import glob, json, re, sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE
import agentic_common as AC
import axis_audio, axis_visual, axis_binding, axis_temporal_count, axis_temporal_relation

A, V, AVB, TCC, TCR = ("audio_event_correctness", "visual_event_correctness", "audio_visual_binding",
                       "temporal_count_satisfaction", "temporal_relation_satisfaction")
PER_EVENT_AXES = {A, V, AVB, TCC}
SCHEMA = {A: AC.PER_EVENT_AXIS_SCHEMA, V: AC.PER_EVENT_AXIS_SCHEMA, AVB: AC.PER_EVENT_AXIS_SCHEMA,
          TCC: AC.PER_EVENT_COUNT_SCHEMA, TCR: AC.AXIS_RESULT_SCHEMA}
SKIP_RE = re.compile(r"precondition|not evaluable|not evaluated|skipped", re.I)

# The seed for GEPA. Keep this text byte-identical to the 10/19 run so "seed" in eval tables == that run.
SEED_RULES = """
TWO-STAGE PROTOCOL (read carefully):
- You already judged this axis from the video and its audio ALONE. That stage-1 judgment is shown below under "Stage 1 (media only)".
- Tool evidence is now attached. It is approximate and can be wrong, incomplete, or empty.
- Your job in this call is to COMPARE stage 1 with the tool evidence, not to re-judge from scratch.
- KEEP the stage-1 answer unless the tool evidence gives a specific observation (a transcribed word, a timestamped sound, a described action) that directly contradicts what stage 1 heard and saw.
- Evidence that is empty, has no timestamps, or merely agrees with the visible action is NOT by itself a reason to change stage 1.
- Start each reason with "KEEP:" or "REVISE:" followed by the comparison you made."""

STAGE2_RULES = SEED_RULES          # module variable; replaced by set_rules()
STAGE1 = None                      # DataFrame indexed by item_id, set by install()
SIDE = None                        # sidecar path or None
_ORIG = AC.build_axis_user_text    # unpatched builder (fresh stage-1 calls go through it)
_INSTALLED = False


# ---------------------------------------------------------------- rules
def set_rules(text):
    """Swap the stage-2 KEEP/REVISE rule block (GEPA candidate)."""
    global STAGE2_RULES
    STAGE2_RULES = text if text.startswith("\n") else "\n" + text


def load_stage1(stage1_dir):
    fs = [stage1_dir] if str(stage1_dir).endswith(".csv") else (
        sorted(glob.glob(f"{stage1_dir}/shard?.csv")) or sorted(glob.glob(f"{stage1_dir}/all.csv")))
    if not fs:
        sys.exit(f"no csv under {stage1_dir}")
    df = pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")
    print(f"[two-stage] stage-1 rows: {len(df)} from {stage1_dir}", flush=True)
    return df


# ---------------------------------------------------------------- stage-1 lookup
def stage1_lookup(item_id, axis, only_ids):
    """Return (entries, missing_ids). entries: list of per-event dicts (or [single dict] for TCR)."""
    if STAGE1 is None or item_id not in STAGE1.index:
        return [], list(only_ids or [])
    r = STAGE1.loc[item_id]
    if axis == TCR:
        lab = str(r.get(TCR, "")).lower()
        if lab in ("yes", "no") and not SKIP_RE.search(str(r.get(TCR + "_reason", ""))):
            return [dict(label=lab, reason=r.get(TCR + "_reason", ""), evidence=r.get(TCR + "_evidence", ""))], []
        return [], ["__single__"]
    try:
        pe = json.loads(r[f"{axis}_per_event"])
    except Exception:
        return [], list(only_ids or [])
    good = {}
    for e in pe:
        if SKIP_RE.search(str(e.get("reason", ""))):
            continue
        if axis == TCC:
            if e.get("observed_count") is None:
                continue
        elif str(e.get("label", "")).lower() not in ("yes", "no"):
            continue
        good[e["event_id"]] = e
    want = list(only_ids) if only_ids is not None else list(good.keys())
    return [good[i] for i in want if i in good], [i for i in want if i not in good]


def fresh_stage1(ctx, axis, criteria, rules, only_event_ids):
    """One video-only call for this axis (evidence stripped), returns per-event list or [single]."""
    saved_ev, saved_tools = ctx.evidence, dict(ctx.use_tools)
    ctx.evidence = {k: "" for k in saved_ev}
    ctx.use_tools[axis] = False
    try:
        text = _ORIG(ctx, axis, criteria, rules, only_event_ids=only_event_ids)
        sysp = AC.axis_system_prompt(ctx, axis)
        print(f"    [two-stage] fresh stage-1 call for {axis} {only_event_ids}", flush=True)
        parsed, _raw = AC.call_gemini_json(ctx, sysp, text, SCHEMA[axis])
    finally:
        ctx.evidence, ctx.use_tools = saved_ev, saved_tools
    if axis == TCR:
        return [dict(label=str(parsed.get("label", "")).lower(), reason=parsed.get("reason", ""), evidence=parsed.get("evidence", ""))]
    return list(parsed.get("per_event", []))


def fmt_block(axis, entries):
    lines = [f"Stage 1 (media only) judgment for {axis}, made WITHOUT any tool evidence:"]
    for e in entries:
        head = f"- {e['event_id']}: " if "event_id" in e else "- "
        if axis == TCC:
            head += f"observed_count={e.get('observed_count')}"
        else:
            head += f"label={e.get('label')}"
        lines.append(head)
        lines.append(f"  reason: {str(e.get('reason', '')).strip()}")
        if e.get("evidence"):
            lines.append(f"  evidence: {str(e.get('evidence', '')).strip()}")
    return "\n".join(lines)


# ---------------------------------------------------------------- the patch
def build_stage2_user_text(ctx, axis, criteria_text, decision_rules, only_event_ids=None, rules=None):
    """Stage-2 user text = normal axis text + stage-1 block + (decision rules + stage-2 rules).
    Returns (text, entries, src). `rules` overrides the module STAGE2_RULES (adapter passes the candidate)."""
    item_id = ctx.item_meta.get("item_id")
    entries, missing = stage1_lookup(item_id, axis, only_event_ids)
    src = "stage1_run"
    if missing:
        ids = None if missing == ["__single__"] else missing
        entries = entries + fresh_stage1(ctx, axis, criteria_text, decision_rules, ids)
        src = "stage1_run+fresh" if len(entries) > len(missing) else "fresh"
    text = _ORIG(ctx, axis, criteria_text, decision_rules + "\n" + (rules or STAGE2_RULES), only_event_ids=only_event_ids)
    j = text.find("Axis criteria for")
    text = text[:j] + fmt_block(axis, entries) + "\n\n" + text[j:]
    return text, entries, src


def patched_build_axis_user_text(ctx, axis, criteria_text, decision_rules, only_event_ids=None):
    if axis not in SCHEMA:                      # constraint_compliance: no evidence, unchanged
        return _ORIG(ctx, axis, criteria_text, decision_rules, only_event_ids=only_event_ids)
    text, entries, src = build_stage2_user_text(ctx, axis, criteria_text, decision_rules, only_event_ids)
    if SIDE:
        with open(SIDE, "a") as f:
            f.write(json.dumps(dict(item_id=ctx.item_meta.get("item_id"), axis=axis, source=src, stage1=entries), default=str) + "\n")
    return text


def install(stage1_dir, rules=None, side=None):
    """Load the stage-1 table and patch the pipeline's axis-text builder. Idempotent."""
    global STAGE1, SIDE, _INSTALLED
    STAGE1 = load_stage1(stage1_dir)
    SIDE = side
    if rules is not None:
        set_rules(rules)
    if not _INSTALLED:
        for mod in (axis_audio, axis_visual, axis_binding, axis_temporal_count, axis_temporal_relation):
            mod.build_axis_user_text = patched_build_axis_user_text
        AC.build_axis_user_text = patched_build_axis_user_text
        _INSTALLED = True


def _pop(flag, with_value=True):
    if flag not in sys.argv:
        return None
    i = sys.argv.index(flag)
    val = sys.argv[i + 1] if with_value else True
    del sys.argv[i:i + (2 if with_value else 1)]
    return val


if __name__ == "__main__":
    stage1_dir = _pop("--stage1-dir")
    if stage1_dir is None:
        sys.exit("need --stage1-dir <video-only results dir>")
    rules_file = _pop("--stage2-rules")
    text_only = _pop("--stage2-text-only", with_value=False)
    if text_only:
        # the whole pipeline (incl. fresh stage-1 calls) runs without media; matches the 10/19 text-only experiment
        sys.argv += ["--media-input-mode", "language_only"]
    out_csv = sys.argv[sys.argv.index("--output-csv") + 1]
    side = Path(out_csv).with_name(Path(out_csv).stem + "_stage1.jsonl")
    rules = Path(rules_file).read_text() if rules_file else None
    install(stage1_dir, rules=rules, side=side)
    if rules_file:
        print(f"[two-stage] stage-2 rules from {rules_file} ({len(STAGE2_RULES)} chars)", flush=True)
    import run_agentic_eval as RAE
    RAE.main()
