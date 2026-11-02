#!/usr/bin/env python
"""--axes v (Visual agent만 실행) 추가. 백업 *.bak_axesv
사용: cd evaluation/ablation && python patch_axes_v.py
"""
import shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent

def patch(path, reps):
    src = path.read_text(encoding="utf-8"); out = src
    for old, new, desc in reps:
        if old not in out:
            if new in out: print(f"  [skip] {path.name}: {desc} (already)"); continue
            sys.exit(f"  [FAIL] {path.name}: not found: {desc}")
        if out.count(old) != 1: sys.exit(f"  [FAIL] {path.name}: not unique: {desc}")
        out = out.replace(old, new); print(f"  [ok] {path.name}: {desc}")
    if out != src:
        shutil.copy(path, path.with_suffix(path.suffix + ".bak_axesv")); path.write_text(out, encoding="utf-8")

# ---- run_agentic_eval.py ----
patch(HERE / "run_agentic_eval.py", [
('choices=["all", "av", "a"],', 'choices=["all", "av", "a", "v"],', "add v to --axes choices"),
('''    elif args.axes == "a":
        print("[INFO] Pipeline: A only (--axes a); V/AVB/TC-Relation/TC-Count/CC skipped")''',
 '''    elif args.axes == "a":
        print("[INFO] Pipeline: A only (--axes a); V/AVB/TC-Relation/TC-Count/CC skipped")
    elif args.axes == "v":
        print("[INFO] Pipeline: V only (--axes v); A/AVB/TC-Relation/TC-Count/CC skipped")''', "log line for v"),
])

# ---- agentic_orchestrator.py ----
patch(HERE / "agentic_orchestrator.py", [
('''    if axes_mode in ("av", "a"):
        import time
        t0 = time.perf_counter()
        a = axis_audio.evaluate(ctx)
        print(f"[TIME] Audio: {time.perf_counter() - t0:.2f}s")

        raws["audio_event_correctness"] = a["raw"]
        prompts["audio_event_correctness"] = a["user_text"]
        aec_pe = a["per_event"]

        if axes_mode == "av":''',
 '''    if axes_mode in ("av", "a", "v"):
        import time
        if axes_mode in ("av", "a"):
            t0 = time.perf_counter()
            a = axis_audio.evaluate(ctx)
            print(f"[TIME] Audio: {time.perf_counter() - t0:.2f}s")
            raws["audio_event_correctness"] = a["raw"]
            prompts["audio_event_correctness"] = a["user_text"]
            aec_pe = a["per_event"]
        else:
            aec_pe = []

        if axes_mode in ("av", "v"):''', "run audio only for av/a, visual for av/v"),
('''            note = "Axis not run (--axes av: audio/visual-only evidence ablation)."
            visual_result = {''',
 '''            note = ("Axis not run (--axes av: audio/visual-only evidence ablation)." if axes_mode == "av"
                    else "Axis not run (--axes v: visual-axis-only caption ablation).")
            visual_result = {''', "note for v"),
('''        result: Dict[str, dict] = {
            "audio_event_correctness": {
                "label": NE._agg_label([pe["label"] for pe in aec_pe]),
                "reason": NE._agg_field(aec_pe, "reason"),
                "evidence": NE._agg_field(aec_pe, "evidence"), "per_event": aec_pe,
            },''',
 '''        audio_result = ({
                "label": NE._agg_label([pe["label"] for pe in aec_pe]),
                "reason": NE._agg_field(aec_pe, "reason"),
                "evidence": NE._agg_field(aec_pe, "evidence"), "per_event": aec_pe,
            } if axes_mode in ("av", "a") else _skipped_axis(note))
        result: Dict[str, dict] = {
            "audio_event_correctness": audio_result,''', "audio result skipped for v"),
('''        else:
            result["overall_reason"] = (
                f"A-only run ({ctx.config.get('media_input_mode', 'video')} input): "
                f"A={result['audio_event_correctness']['label']}. Other axes skipped."
            )''',
 '''        elif axes_mode == "v":
            result["overall_reason"] = (
                f"V-only run ({ctx.config.get('media_input_mode', 'video')} input): "
                f"V={result['visual_event_correctness']['label']}. Other axes skipped."
            )
        else:
            result["overall_reason"] = (
                f"A-only run ({ctx.config.get('media_input_mode', 'video')} input): "
                f"A={result['audio_event_correctness']['label']}. Other axes skipped."
            )''', "overall_reason for v"),
])
