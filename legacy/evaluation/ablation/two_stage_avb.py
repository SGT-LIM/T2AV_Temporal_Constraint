#!/usr/bin/env python3
"""Two-stage AVB judge, v0 ("perceive first, evidence second").

Stage 1 = the existing video-only run (its per-event AVB label/reason/evidence are reused, no new call).
Stage 2 = ONE new AVB call: same prompt builder as the pipeline, plus
          (a) the Whisper/FLAM evidence block copied from the existing W+F run's prompt (no tool rerun, no GPU),
          (b) the stage-1 judgment, and
          (c) rules that say: keep stage 1 unless the evidence contradicts it with specific timestamps.

Only events that stage 1 actually judged (A and V passed) are sent; precondition-failed events are copied as-is.

Run from T2AV_Temporal_Constraint/evaluation/ablation/ (so new_eval / agentic_common import), e.g.
  cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
  export GEMINI_API_KEY=$(cat ~/.gemini_key)
  python two_stage_avb.py \
    --stage1-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_baseline \
    --tools-dir  /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/hdepic_medium_multi_tools_wf \
    --prompt-json /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_prompts.json \
    --outputs-dir /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/hdepic_medium_shard{0..5} \
    --out-csv /projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval/results/two_stage_avb_v0/shard0.csv \
    --variants AVBearly,AVBlate,pass --media video --limit 2
Shard with --shard i --nshards n. Resumes: item_ids already in --out-csv are skipped.
"""
import argparse, csv, glob, json, os, re, sys, time
from pathlib import Path

import pandas as pd
from google import genai

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE
import agentic_common as AC
from agentic_common import build_context, build_axis_user_text, axis_system_prompt, call_gemini_json, PER_EVENT_AXIS_SCHEMA
import axis_binding as AB
from run_agentic_eval import build_arg_parser

AXIS = "audio_visual_binding"
PRECOND_RE = re.compile(r"precondition|not evaluable|not evaluated", re.I)

STAGE2_RULES = """
TWO-STAGE PROTOCOL (read carefully):
- You already judged this axis from the video and its audio ALONE. That stage-1 judgment is shown below under "Stage 1 (media only)".
- Tool evidence (Whisper / OpenFLAM) is now attached. It is approximate and can be wrong, incomplete, or empty.
- Your job in this call is to COMPARE stage 1 with the tool evidence, not to re-judge from scratch.
- KEEP the stage-1 label unless the tool evidence gives a specific, timestamped observation that directly contradicts what stage 1 heard and saw.
- Evidence that only says a sound exists, has no timestamps, lists no detections, or lists a peak near the visual action, is NOT by itself a reason to change a stage-1 "no" to "yes". A sound being present does not mean it is bound to the action.
- If the evidence shows a sound peak clearly separated in time from the visible action, that supports "no".
- Start each reason with "KEEP:" or "REVISE:" followed by the comparison you made."""


def load_run(d):
    fs = sorted(glob.glob(f"{d}/shard?.csv")) or sorted(glob.glob(f"{d}/all.csv"))
    if not fs:
        sys.exit(f"no csv under {d}")
    return pd.concat(pd.read_csv(f, engine="python") for f in fs).drop_duplicates("item_id", keep="last").set_index("item_id")


def audio_block_from_prompt(user_prompt_json):
    """Cut the Whisper+FLAM evidence section out of the W+F run's AVB user prompt."""
    try:
        txt = json.loads(user_prompt_json)[AXIS]
    except Exception:
        txt = str(user_prompt_json)
    i = txt.find("Whisper ASR transcription")
    j = txt.find("\nAxis criteria for")
    if i < 0 or j < 0 or j <= i:
        return None
    return txt[i:j].strip()


def stage1_block(pe_list):
    lines = ["Stage 1 (media only) judgment for this axis, made WITHOUT any tool evidence:"]
    for pe in pe_list:
        lines.append(f"- {pe['event_id']}: label={pe['label']}")
        lines.append(f"  reason: {str(pe.get('reason', '')).strip()}")
        if pe.get("evidence"):
            lines.append(f"  evidence: {str(pe.get('evidence', '')).strip()}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1-dir", required=True, help="video-only run results dir")
    ap.add_argument("--tools-dir", required=True, help="W+F run results dir (evidence text is copied from its prompts)")
    ap.add_argument("--prompt-json", required=True)
    ap.add_argument("--outputs-dir", required=True, nargs="+", help="clip dir(s), same as the runs (e.g. hdepic_medium_shard0 ... shard5)")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--thinking-level", default="high")
    ap.add_argument("--media", default="video", choices=["video", "language_only"],
                    help="video: stage 2 sees the clip again; language_only: stage 2 sees only text (stage-1 verdict + evidence)")
    ap.add_argument("--variants", default="AVBearly,AVBlate,pass", help="item_id suffixes to run, comma separated")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    a = ap.parse_args()

    s1 = load_run(a.stage1_dir)
    tools = load_run(a.tools_dir)

    # args object for build_context: no tools computed here, evidence is injected by hand
    pargs = build_arg_parser().parse_args([
        "--prompt-json", a.prompt_json, "--outputs-dir", a.outputs_dir[0], "--output-csv", a.out_csv,
        "--model", a.model, "--thinking-level", a.thinking_level,
        "--audio-evidence-mode", "none", "--caption-evidence-mode", "none", "--pose-evidence-mode", "none",
        "--media-input-mode", a.media, "--axes", "all",
    ])
    if pargs.focus_planner_model is None:
        pargs.focus_planner_model = pargs.model

    items = NE.load_prompt_items(pargs.prompt_json)
    item_meta_map = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
    vid_map = {}
    for d in a.outputs_dir:
        for p in NE.find_video_files(Path(d)):
            vid_map.setdefault(NE.infer_item_id_from_path(p), p)
    print(f"[INFO] {len(vid_map)} clips found", flush=True)

    suffixes = tuple("_" + v for v in a.variants.split(","))
    todo = [i for i in s1.index if i.endswith(suffixes) and i in tools.index and i in vid_map and i in item_meta_map]
    todo = sorted(todo)[a.shard::a.nshards]
    if a.limit:
        todo = todo[: a.limit]

    out = Path(a.out_csv); out.parent.mkdir(parents=True, exist_ok=True)
    done = set(pd.read_csv(out).item_id) if out.exists() else set()
    cols = ["item_id", "event_id", "stage1_label", "stage2_label", "changed", "stage2_reason", "stage2_evidence",
            "stage1_reason", "n_eligible", "note", "model", "media", "raw"]
    new_file = not out.exists()
    print(f"[INFO] {len(todo)} items in this shard, {len(done)} already done", flush=True)

    client = genai.Client()
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new_file:
            w.writeheader()
        for k, iid in enumerate(todo):
            if iid in done:
                continue
            try:
                pe1 = json.loads(s1.loc[iid, f"{AXIS}_per_event"])
            except Exception as e:
                w.writerow(dict(item_id=iid, note=f"stage1 per_event unreadable: {e}", model=a.model, media=a.media)); f.flush(); continue
            eligible = [pe for pe in pe1 if str(pe.get("label")).lower() in ("yes", "no") and not PRECOND_RE.search(str(pe.get("reason", "")))]
            if not eligible:
                for pe in pe1:
                    w.writerow(dict(item_id=iid, event_id=pe.get("event_id"), stage1_label=pe.get("label"), stage2_label=pe.get("label"),
                                    changed=False, stage1_reason=pe.get("reason"), n_eligible=0, note="precondition_fail_copied",
                                    model=a.model, media=a.media))
                f.flush(); continue
            block = audio_block_from_prompt(tools.loc[iid, "user_prompt"])
            if block is None:
                w.writerow(dict(item_id=iid, note="no evidence block in tools prompt", model=a.model, media=a.media)); f.flush(); continue

            t0 = time.time()
            item_meta = item_meta_map[iid]
            ctx = build_context(client, vid_map[iid], item_meta, pargs)
            ctx.evidence["audio"] = block
            ctx.evidence_modes["audio"] = "whisper_flam"
            ctx.use_tools[AXIS] = True

            ids = [pe["event_id"] for pe in eligible]
            criteria = NE.build_av_binding_axis_criteria(item_meta["events"])
            user_text = build_axis_user_text(ctx, AXIS, criteria, AB._RULES + "\n" + STAGE2_RULES, only_event_ids=ids)
            # insert the stage-1 block right before the axis criteria
            j = user_text.find("Axis criteria for")
            user_text = user_text[:j] + stage1_block(eligible) + "\n\n" + user_text[j:]
            system_prompt = axis_system_prompt(ctx, AXIS)

            parsed, raw = call_gemini_json(ctx, system_prompt, user_text, PER_EVENT_AXIS_SCHEMA)
            ev_structs = [s for s in ctx.binding_events if s["event_id"] in ids]
            pe2 = {pe["event_id"]: pe for pe in NE.normalize_label_per_event(parsed, ev_structs, AXIS)}

            for pe in pe1:
                eid = pe.get("event_id")
                if eid in pe2:
                    l1, l2 = str(pe.get("label")).lower(), str(pe2[eid].get("label")).lower()
                    w.writerow(dict(item_id=iid, event_id=eid, stage1_label=l1, stage2_label=l2, changed=(l1 != l2),
                                    stage2_reason=pe2[eid].get("reason"), stage2_evidence=pe2[eid].get("evidence"),
                                    stage1_reason=pe.get("reason"), n_eligible=len(eligible), note="", model=a.model, media=a.media, raw=raw))
                else:
                    w.writerow(dict(item_id=iid, event_id=eid, stage1_label=pe.get("label"), stage2_label=pe.get("label"), changed=False,
                                    stage1_reason=pe.get("reason"), n_eligible=len(eligible), note="precondition_fail_copied", model=a.model, media=a.media))
            f.flush()
            print(f"[{k+1}/{len(todo)}] {iid} {[(e, pe2[e]['label']) for e in pe2]} {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
