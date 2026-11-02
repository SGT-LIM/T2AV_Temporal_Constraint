#!/usr/bin/env python3
"""CLI for the agentic (per-axis) T2AV evaluator.

Same inputs/outputs and CSV schema as new_eval.py, but each video is scored by
the hierarchical per-axis pipeline in agentic_orchestrator instead of a single
6-axis call. Adds per-axis tool toggles (--no-<axis>-tools) so any axis can be
run Gemini-only while others keep their routed evidence.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

MAX_RETRIES = 3

# # `new_eval.py` lives in the sibling `gemini/` directory; agentic_common
# # already adds it to sys.path on import, but this module also imports it
# # directly, so make sure the path is set up before that happens too.
# _GEMINI_DIR = str(Path(__file__).resolve().parent.parent / "gemini")
# if _GEMINI_DIR not in sys.path:
#     sys.path.insert(0, _GEMINI_DIR)

from t2av_eval.judge.media import core as NE
from t2av_eval.judge.media import common as AC
from t2av_eval.judge.media.common import build_context
from t2av_eval.judge.media.orchestrator import evaluate_video_agentic


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic per-axis Gemini evaluator for T2AV temporal-constraint videos.")
    # ---- I/O and run control (mirrors new_eval.main) ----
    parser.add_argument("--prompt-json", type=Path, required=True)
    parser.add_argument("--outputs-dir", type=Path, required=True)
    parser.add_argument("--model", type=str, default="gemini-3.1-pro-preview")
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--per-event-csv", type=Path, default=None, help="Long-format per-event CSV path. Defaults to <output-csv stem>_per_event.csv.")
    parser.add_argument("--no-per-event-csv", action="store_true")
    parser.add_argument("--media-fps", type=float, default=24.0, help="FPS metadata passed to Gemini. Use <=0 to omit.")
    parser.add_argument("--thinking-level", type=str, default="high", choices=["low", "high", "none"])
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--modality-filter", type=str, default=None, choices=NE.SUPPORTED_MODALITIES)
    parser.add_argument("--item-overrides-json", type=Path, default=None)
    parser.add_argument("--variant-indices", type=int, nargs="*", default=None)
    parser.add_argument("--max-videos", type=int, default=None)
    parser.add_argument("--check-id-map-only", action="store_true")
    parser.add_argument("--relative-only", action="store_true")

    # ---- Per-axis tool toggles (new) ----
    parser.add_argument("--no-audio-tools", action="store_true", help="Run Audio Event Correctness Gemini-only (no Whisper/CLAP/FLAM evidence).")
    parser.add_argument("--no-visual-tools", action="store_true", help="Run Visual Event Correctness Gemini-only (no MediaPipe evidence).")
    parser.add_argument("--no-binding-tools", action="store_true", help="Run Audio-Visual Binding Gemini-only.")
    parser.add_argument("--no-temporal-relation-tools", action="store_true", help="Run Temporal Relation Gemini-only.")
    parser.add_argument("--no-temporal-count-tools", action="store_true", help="Run Temporal Count Gemini-only.")
    parser.add_argument("--no-temporal-tools", action="store_true", help="Backward-compatible alias: disables tools for BOTH Temporal Relation and Temporal Count.")
    parser.add_argument("--no-compliance-tools", action="store_true", help="Run Constraint Compliance Gemini-only.")

    # ---- Pose evidence (MediaPipe) ----
    parser.add_argument("--pose-evidence-mode", type=str, default="none", choices=["none", "raw", "focused_raw"])
    parser.add_argument("--no-mediapipe-hint", action="store_true", help="Alias for --pose-evidence-mode none.")
    parser.add_argument("--mediapipe-fps", type=float, default=8.0)
    parser.add_argument("--mediapipe-model-complexity", type=int, default=1, choices=[0, 1, 2])
    parser.add_argument("--mediapipe-near-threshold-norm", type=float, default=0.60)
    parser.add_argument("--mediapipe-max-trajectory-samples", type=int, default=12)
    parser.add_argument("--raw-pose-max-frames", type=int, default=40)
    parser.add_argument("--pose-summary-lines", type=int, default=80)
    parser.add_argument("--pose-detail-chars", type=int, default=24000)
    parser.add_argument("--focus-planner-model", type=str, default=None)
    parser.add_argument("--focus-planner-thinking-level", type=str, default="low", choices=["low", "high", "none"])
    parser.add_argument("--no-focus-planner-fallback", action="store_true")

    parser.add_argument("--parent-labels-csv", type=str, default=None, help="Reuse A/V per-event labels from this all.csv (by item_id); skips the A, V, CC calls and runs only AVB/TC.")
    parser.add_argument("--axes", type=str, default="all", choices=["all", "av", "a", "v"],
                        help="'av': run ONLY the Audio and Visual agents (evidence-ablation rows); "
                             "AVB, TC-Relation, TC-Count, CC are skipped with no Gemini calls. "
                             "'a': run ONLY the Audio agent (input-modality ablation rows). "
                             "'all': full hierarchical pipeline.")

    # ---- Media input mode (input-modality ablation for the Audio axis) ----
    parser.add_argument("--media-input-mode", type=str, default="video",
                        choices=["video", "audio_only", "language_only"],
                        help="'video': upload the full video (default). "
                             "'audio_only': upload ONLY the extracted audio track "
                             "(blocks visual dominance on the Audio axis; requires --axes a). "
                             "'language_only': upload NO media; the judge sees only tool-output "
                             "text (Whisper/FLAM) plus prompt/metadata (requires --axes a and "
                             "a non-'none' --audio-evidence-mode).")
    parser.add_argument("--judge-backend", choices=["gemini", "openai", "local"], default="gemini",
                        help="openai: judge calls go to OpenAI (text / input_audio / frames). "
                             "local: in-process vLLM server (local_judge_server.py), video+audio by file path. "
                             "Evidence + prompts unchanged.")  # judge_backend_local_patched
    parser.add_argument("--local-judge-url", default=None, help="local backend: server url (default env LOCAL_JUDGE_URL or http://127.0.0.1:8010)")
    parser.add_argument("--frame-fps", type=float, default=8.0,
                        help="openai backend, video mode: frame sampling rate (frames sent as ordered images, no audio).")
    parser.add_argument("--frame-cache-dir", default="frame_cache")
    parser.add_argument("--frame-detail", default="low", choices=["low", "high", "auto"],
                        help="openai backend: image detail per frame (low = cheapest)")  # astra_patched
    parser.add_argument("--openai-reasoning-effort", default="low", choices=["minimal", "low", "medium", "high"])
    parser.add_argument("--audio-cache-dir", type=Path, default=Path("audio_only_cache"),
                        help="Cache directory for extracted audio tracks (audio_only mode).")

    # ---- Dense caption evidence (Gemini captioning pass or external captioner) ----
    parser.add_argument("--caption-evidence-mode", type=str, default="none", choices=["none", "gemini", "external"],
                        help="'gemini': a separate Gemini call captions each video; "
                             "'external': load precomputed captions (e.g. TimeChat-Captioner) from --caption-external-json.")
    parser.add_argument("--caption-model", type=str, default=None,
                        help="Model for the gemini captioning pass. Defaults to --model (same model, separate call).")
    parser.add_argument("--caption-style", type=str, default="timestamped", choices=["timestamped", "plain"],
                        help="'timestamped': [start-end] event lines; 'plain': chronological prose without timestamps.")
    parser.add_argument("--caption-cache-dir", type=Path, default=Path("caption_cache"),
                        help="Directory for per-video caption cache (skips re-captioning on resume).")
    parser.add_argument("--caption-external-json", type=Path, default=None,
                        help="JSON/JSONL of precomputed captions keyed by video relpath/filename/stem.")
    parser.add_argument("--caption-detail-chars", type=int, default=8000)

    # ---- Audio evidence (Whisper + CLAP + FLAM) ----
    parser.add_argument("--audio-evidence-mode", type=str, default="none", choices=["none", "whisper", "clap", "both", "flam", "whisper_flam", "clap_flam", "all"])
    parser.add_argument("--whisper-model-size", type=str, default="large-v3-turbo")
    parser.add_argument("--whisper-device", type=str, default="cuda")
    parser.add_argument("--whisper-compute-type", type=str, default="float16")
    parser.add_argument("--whisper-language", type=str, default="en")
    parser.add_argument("--whisper-max-segments", type=int, default=200)
    parser.add_argument("--whisper-detail-chars", type=int, default=4000)
    parser.add_argument("--clap-mode", type=str, default="temporal", choices=["global", "temporal"])
    parser.add_argument("--clap-window-seconds", type=float, default=0.75)
    parser.add_argument("--clap-hop-seconds", type=float, default=0.25)
    parser.add_argument("--clap-device", type=str, default="cuda")
    parser.add_argument("--clap-max-frames", type=int, default=60)
    parser.add_argument("--clap-detail-chars", type=int, default=8000)
    parser.add_argument("--clap-negative-queries", type=str, nargs="*", default=None)
    parser.add_argument("--flam-model-name", type=str, default="v1-base")
    parser.add_argument("--flam-device", type=str, default="cuda")
    parser.add_argument("--flam-ckpt-path", type=str, default="/tmp/openflam")
    parser.add_argument("--flam-method", type=str, default="unbiased", choices=["unbiased", "approximate"])
    parser.add_argument("--flam-max-duration-sec", type=float, default=10.0)
    parser.add_argument("--flam-hop-sec", type=float, default=0.0, help="Slide a max-duration window with this hop over long clips (0 = truncate).")
    parser.add_argument("--flam-threshold", type=float, default=0.98)
    parser.add_argument("--flam-min-duration-sec", type=float, default=0.05)
    parser.add_argument("--flam-merge-gap-sec", type=float, default=0.10)
    parser.add_argument("--flam-median-filter-size", type=int, default=3)
    parser.add_argument("--flam-top-k", type=int, default=5)
    parser.add_argument("--flam-detail-chars", type=int, default=8000)
    parser.add_argument("--start-index", type=int, default=0, help="0-based inclusive start index after filtering and sorting.")
    parser.add_argument("--end-index", type=int, default=None, help="0-based exclusive end index after filtering and sorting.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.no_mediapipe_hint:
        args.pose_evidence_mode = "none"
    if args.focus_planner_model is None:
        args.focus_planner_model = args.model

    if args.start_index < 0:
        parser.error("--start-index must be >= 0")

    if args.end_index is not None:
        if args.end_index < 0:
            parser.error("--end-index must be >= 0")
        if args.end_index < args.start_index:
            parser.error("--end-index must be greater than or equal to --start-index")

    # ---- Media input mode validation ----
    # caption-only V: judge sees ONLY a precomputed caption (no video/audio). Mirrors the
    # A-axis language_only ablation for the Visual axis.
    caption_only_v = (args.media_input_mode == "language_only" and args.axes == "v"
                      and args.caption_evidence_mode == "external")
    if args.media_input_mode != "video" and not caption_only_v:
        if args.axes != "a":
            parser.error(f"--media-input-mode {args.media_input_mode} requires --axes a "
                         "(Visual/AVB/Temporal/CC axes need the visual track), or --axes v with "
                         "--media-input-mode language_only --caption-evidence-mode external (caption-only V).")
        if args.caption_evidence_mode not in (None, "", "none"):
            parser.error(f"--media-input-mode {args.media_input_mode} is incompatible with "
                         "--caption-evidence-mode (captions are visual-track evidence).")
        if args.pose_evidence_mode not in (None, "", "none"):
            parser.error(f"--media-input-mode {args.media_input_mode} is incompatible with "
                         "--pose-evidence-mode (pose is visual-track evidence).")
    if args.media_input_mode == "language_only" and args.audio_evidence_mode == "none" and not caption_only_v:
        parser.error("--media-input-mode language_only requires a non-'none' --audio-evidence-mode "
                     "(e.g. whisper_flam); otherwise the judge has no observation at all.")
    if args.media_input_mode == "language_only" and NE.build_audio_evidence_section is None and args.audio_evidence_mode != "none":
        parser.error("--media-input-mode language_only requires the audio tools, but "
                     "'from Tool_Use.audio_evidence_flam import ...' failed at new_eval import time. "
                     "Run from a directory where the Tool_Use package is importable, symlink it into "
                     "the current directory, or add its parent to PYTHONPATH.")

    items = NE.load_prompt_items(args.prompt_json)
    item_overrides = NE.load_json_if_exists(args.item_overrides_json)
    item_meta_map = NE.build_item_meta_map(
        items,
        modality_filter=args.modality_filter,
        item_overrides=item_overrides,
        relative_only=args.relative_only,
    )
    if not item_meta_map:
        raise RuntimeError("No prompt items matched the provided filters.")

    video_files = NE.find_video_files(args.outputs_dir)
    if not video_files:
        raise RuntimeError(f"No mp4 files found under {args.outputs_dir}")

    total_video_count = len(video_files)

    video_files = video_files[
        args.start_index:args.end_index
    ]

    print(
        f"[INFO] Selected videos: "
        f"[{args.start_index}:{args.end_index}] "
        f"→ {len(video_files)} / {total_video_count} videos"
    )

    if args.check_id_map_only:
        NE.check_id_map_only(args.outputs_dir, item_meta_map)
        return

    AC.ensure_csv_header(args.output_csv)

    per_event_csv = None
    if not args.no_per_event_csv:
        per_event_csv = NE.per_event_csv_path(args.output_csv, args.per_event_csv)
        NE.ensure_per_event_csv_header(per_event_csv)
        print(f"[INFO] Per-event long CSV: {per_event_csv}")

    # api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    # client = genai.Client(api_key=api_key) if api_key else genai.Client()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    http_opts = types.HttpOptions(timeout=int(args.timeout_seconds * 1000))  # 밀리초 단위
    client = (genai.Client(api_key=api_key, http_options=http_opts)
            if api_key else genai.Client(http_options=http_opts))

    PARENTS = None
    if args.parent_labels_csv:
        import json as _json, pandas as _pd
        _df = _pd.read_csv(args.parent_labels_csv).drop_duplicates("item_id", keep="last")
        PARENTS = {}
        for _, r in _df.iterrows():
            try:
                PARENTS[r["item_id"]] = {"audio_event_correctness": _json.loads(r["audio_event_correctness_per_event"]),
                                         "visual_event_correctness": _json.loads(r["visual_event_correctness_per_event"])}
            except Exception as e:
                print(f"  [WARN] parent labels unreadable for {r['item_id']}: {e}")
        print(f"[INFO] Parent A/V labels loaded for {len(PARENTS)} items from {args.parent_labels_csv}; A/V/CC calls will be skipped")
    processed = skipped = errors = 0
    print(f"[INFO] Loaded {len(item_meta_map)} prompt items")
    print(f"[INFO] Found {len(video_files)} mp4 files under {args.outputs_dir}")
    print(f"[INFO] Output CSV: {args.output_csv}")
    if args.axes == "av":
        print("[INFO] Pipeline: A + V only (--axes av); AVB/TC-Relation/TC-Count/CC skipped")
    elif args.axes == "a":
        print("[INFO] Pipeline: A only (--axes a); V/AVB/TC-Relation/TC-Count/CC skipped")
    elif args.axes == "v":
        print("[INFO] Pipeline: V only (--axes v); A/AVB/TC-Relation/TC-Count/CC skipped")
    else:
        print(f"[INFO] Pipeline: A,V,CC -> AVB -> TC-Relation + per-event TC-Count")
    print(f"[INFO] Media input mode: {args.media_input_mode}"
          + (f" (audio cache: {args.audio_cache_dir})" if args.media_input_mode == "audio_only" else ""))
    print(f"[INFO] Pose evidence mode: {args.pose_evidence_mode} | Audio evidence mode: {args.audio_evidence_mode}")
    print(f"[INFO] Caption evidence mode: {args.caption_evidence_mode}"
          + (f" (model={args.caption_model or args.model}, style={args.caption_style})"
             if args.caption_evidence_mode == "gemini" else "")
          + (f" (file={args.caption_external_json})" if args.caption_evidence_mode == "external" else ""))
    if args.caption_evidence_mode == "external" and args.caption_external_json is None:
        parser.error("--caption-evidence-mode external requires --caption-external-json")
    tool_off = [a for a, off in [
        ("audio", args.no_audio_tools), ("visual", args.no_visual_tools),
        ("binding", args.no_binding_tools),
        ("temporal_relation", args.no_temporal_relation_tools or args.no_temporal_tools),
        ("temporal_count", args.no_temporal_count_tools or args.no_temporal_tools),
        ("compliance", args.no_compliance_tools)] if off]
    if tool_off:
        print(f"[INFO] Tools disabled for axes: {', '.join(tool_off)}")

    for video_path in video_files:
        relpath = str(video_path.relative_to(args.outputs_dir))
        item_id = NE.infer_item_id_from_path(video_path)
        variant_index = NE.parse_variant_index(video_path.name)

        if args.variant_indices is not None and variant_index not in set(args.variant_indices):
            skipped += 1
            continue

        item_meta = item_meta_map.get(item_id)
        if item_meta is None:
            print(f"[SKIP] No prompt metadata for item_id={item_id} ({relpath})")
            skipped += 1
            continue

        if not args.overwrite and NE.already_done(args.output_csv, relpath):
            print(f"[SKIP] Already evaluated: {relpath}")
            skipped += 1
            continue

        print(f"[EVAL] {relpath}")
        row = NE.build_success_row_base(
            relpath=relpath, video_path=video_path, item_id=item_id,
            variant_index=variant_index, item_meta=item_meta, args=args,
        )

        try:
            for attempt in range(MAX_RETRIES):
                try:
                    ctx = build_context(client, video_path, item_meta, args)
                    if PARENTS is not None:
                        ctx.config["parent_labels"] = PARENTS.get(item_id)
                        if ctx.config["parent_labels"] is None: print(f"  [WARN] no parent labels for {item_id}; running A/V")
                    result = evaluate_video_agentic(ctx)
                    break
                except genai_errors.ServerError as exc:  # 5xx only
                    if attempt == MAX_RETRIES - 1:
                        raise
                    wait = 30 * (2 ** attempt)
                    print(f"  [RETRY {attempt + 1}/{MAX_RETRIES}] {type(exc).__name__}: {exc} — waiting {wait}s", flush=True)
                    time.sleep(wait)
            row = AC.add_result_to_row(row, result)
            print(f"  -> overall_temporal_success={row['overall_temporal_success']} "
                  f"| A={result['audio_event_correctness']['label']} "
                  f"V={result['visual_event_correctness']['label']} "
                  f"AVB={result['audio_visual_binding']['label']} "
                  f"TC-Relation={result['temporal_relation_satisfaction']['label']} "
                  f"TC-Count={result['temporal_count_satisfaction']['label']} "
                  f"CC={result['constraint_compliance']['label']}")
            for pe in result["temporal_count_satisfaction"]["per_event"]:
                print(f"     [TC-Count] event_id={pe['event_id']} "
                      f"observed_count={pe['observed_count']} required_count={pe['required_count']} "
                      f"preconditions_ok={pe['preconditions_ok']} count_correct={pe['count_correct']}")
        except Exception as exc:
            errors += 1
            row = AC.add_error_to_row(row, exc, item_meta)
            print(f"  [ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)

        AC.append_row(args.output_csv, row)
        if per_event_csv is not None:
            NE.append_per_event_rows(per_event_csv, row.get("_per_event_long", []))
        processed += 1

        if args.max_videos is not None and processed >= args.max_videos:
            print(f"[INFO] Reached --max-videos={args.max_videos}")
            break

    print(f"[DONE] processed={processed}, skipped={skipped}, errors={errors}, output={args.output_csv}")


if __name__ == "__main__":
    main()
