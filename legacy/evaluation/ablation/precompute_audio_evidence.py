#!/usr/bin/env python3
"""Fill the audio evidence cache (Whisper + FLAM) for every video, without Gemini.

Run once on a GPU node. Afterwards, every evaluation condition can run with
T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 on any node (no GPU) and gets identical evidence.

Usage:
    python precompute_audio_evidence.py --prompt-json ... --outputs-dir <videos/LTX_2p3> <videos/MOVA> \
        --audio-evidence-mode whisper_flam --flam-ckpt-path /projectnb/.../openflam
Tool options and defaults mirror run_agentic_eval.py.
"""
import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--outputs-dir", type=Path, nargs="+", required=True)
    ap.add_argument("--audio-evidence-mode", default="whisper_flam")
    ap.add_argument("--whisper-model-size", default="large-v3-turbo")
    ap.add_argument("--whisper-device", default="cuda")
    ap.add_argument("--whisper-compute-type", default="float16")
    ap.add_argument("--whisper-language", default="en")
    ap.add_argument("--whisper-max-segments", type=int, default=200)
    ap.add_argument("--whisper-detail-chars", type=int, default=4000)
    ap.add_argument("--clap-negative-queries", nargs="*", default=None)
    ap.add_argument("--clap-mode", default="global")
    ap.add_argument("--clap-window-seconds", type=float, default=1.0)
    ap.add_argument("--clap-hop-seconds", type=float, default=0.5)
    ap.add_argument("--clap-device", default="cuda")
    ap.add_argument("--clap-max-frames", type=int, default=60)
    ap.add_argument("--clap-detail-chars", type=int, default=4000)
    ap.add_argument("--flam-model-name", default="v1-base")
    ap.add_argument("--flam-device", default="cuda")
    ap.add_argument("--flam-ckpt-path", default="/tmp/openflam")
    ap.add_argument("--flam-method", default="unbiased")
    ap.add_argument("--flam-max-duration-sec", type=float, default=10.0)
    ap.add_argument("--flam-hop-sec", type=float, default=0.0)
    ap.add_argument("--flam-threshold", type=float, default=0.98)
    ap.add_argument("--flam-min-duration-sec", type=float, default=0.05)
    ap.add_argument("--flam-merge-gap-sec", type=float, default=0.10)
    ap.add_argument("--flam-median-filter-size", type=int, default=3)
    ap.add_argument("--flam-top-k", type=int, default=5)
    ap.add_argument("--flam-detail-chars", type=int, default=8000)
    args = ap.parse_args()

    items = NE.load_prompt_items(args.prompt_json)
    meta = NE.build_item_meta_map(items)
    tool_kwargs = {k: v for k, v in vars(args).items() if k not in ("prompt_json", "outputs_dir")}

    videos = []
    for d in args.outputs_dir:
        videos += sorted(NE.find_video_files(d))
    print(f"[INFO] {len(videos)} videos | cache dir: {NE._AUDIO_EVIDENCE_CACHE_DIR}")
    ok = fail = 0
    t0 = time.time()
    for i, v in enumerate(videos, 1):
        item_id = NE.infer_item_id_from_path(v)
        m = meta.get(item_id) or meta.get(v.parent.name)
        if m is None:
            print(f"  [SKIP] no prompt meta for {v}"); continue
        section, err = NE.build_audio_evidence_section(video_path=v, item_meta=m, **tool_kwargs)
        if err or not section:
            fail += 1; print(f"  [FAIL] {v.parent.name}: {err[:160]}")
        else:
            ok += 1
        if i % 10 == 0:
            print(f"  [{i}/{len(videos)}] ok={ok} fail={fail} elapsed={time.time()-t0:.0f}s", flush=True)
    print(f"[DONE] ok={ok} fail={fail}")


if __name__ == "__main__":
    main()
