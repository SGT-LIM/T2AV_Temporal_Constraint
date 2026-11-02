#!/usr/bin/env python
"""Gemini dense caption을 미리 뽑아 external-caption JSON으로 저장.

- caption_evidence.py의 캐시(ablation/caption_cache)를 그대로 재사용: 있으면 API 호출 없음, 없으면 생성 후 캐시에 저장.
- 출력: captions/gemini_{ts|plain}_v3_{LTX_2p3,MOVA}.json  ({video_relpath: {"caption": ...}} = avocado JSON과 같은 형식)
- 이후 judge 실험은  --caption-evidence-mode external --caption-external-json captions/gemini_plain_v3_$M.json  로 실행.

사용 (로그인 노드, GPU 불필요):
  cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
  export GEMINI_API_KEY=...
  python make_gemini_captions.py --styles timestamped plain
  python make_gemini_captions.py --styles plain --models MOVA --limit 3 --dry-run   # 확인용
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[3] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[0])  # legacy path roots, see legacy/README.md
import argparse, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import caption_evidence as CE  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--videos-root", type=Path, default=Path("/projectnb/ivc-ml/youngsun/T2AV_data/eval_subsets/min3"))
ap.add_argument("--models", nargs="+", default=["LTX_2p3", "MOVA"])
ap.add_argument("--styles", nargs="+", default=["timestamped", "plain"], choices=["timestamped", "plain"])
ap.add_argument("--caption-model", default="gemini-3.1-pro-preview")
ap.add_argument("--cache-dir", type=Path, default=_pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "caption_cache")
ap.add_argument("--out-dir", type=Path, default=_pl.Path(_LEGACY_ROOT, "evaluation/ablation") / "captions")
ap.add_argument("--media-fps", type=float, default=0.0, help="0 = Gemini 기본 샘플링 (judge run과 동일하게 두는 것을 권장)")
ap.add_argument("--limit", type=int, default=None, help="모델당 처리할 비디오 수 제한 (테스트용)")
ap.add_argument("--dry-run", action="store_true", help="캐시 hit/miss 집계만, API 호출 없음")
ap.add_argument("--keep-uploads", action="store_true", help="업로드한 파일을 Gemini Files API에서 삭제하지 않음")
args = ap.parse_args()

STYLE_TAG = {"timestamped": "ts", "plain": "plain"}
BACKEND = "gemini"


def make_client():
    from google import genai
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
    return genai.Client(api_key=key)


def upload_video(client, path: Path, retries: int = 5):
    """Files API 업로드 후 ACTIVE 될 때까지 대기."""
    for attempt in range(retries):
        try:
            f = client.files.upload(file=str(path))
            while getattr(f.state, "name", str(f.state)) == "PROCESSING":
                time.sleep(2)
                f = client.files.get(name=f.name)
            if getattr(f.state, "name", str(f.state)) != "ACTIVE":
                raise RuntimeError(f"upload state={f.state}")
            return f
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"    [upload retry {attempt+1}/{retries}] {e} -> sleep {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"upload failed: {path}")


def caption_with_retry(client, uploaded, style, retries: int = 6):
    for attempt in range(retries):
        try:
            cap = CE.generate_caption_gemini(client, uploaded, args.caption_model, style, media_fps=args.media_fps)
            if cap:
                return cap
            raise RuntimeError("empty caption")
        except Exception as e:
            msg = str(e)
            wait = 10 * (attempt + 1) if ("429" in msg or "503" in msg or "RESOURCE_EXHAUSTED" in msg) else 3
            print(f"    [caption retry {attempt+1}/{retries}] {msg[:120]} -> sleep {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("caption failed")


def main():
    args.out_dir.mkdir(parents=True, exist_ok=True)
    client = None
    total_calls = 0
    for model in args.models:
        root = args.videos_root / model
        videos = sorted(root.rglob("*.mp4"))
        if args.limit: videos = videos[: args.limit]
        print(f"\n== {model}: {len(videos)} videos under {root}")

        # 출력 JSON (있으면 이어서)
        outs, out_paths = {}, {}
        for style in args.styles:
            p = args.out_dir / f"gemini_{STYLE_TAG[style]}_v3_{model}.json"
            out_paths[style] = p
            outs[style] = json.loads(p.read_text()) if p.exists() else {}

        # 캐시 hit/miss 집계
        need = {style: [] for style in args.styles}
        for v in videos:
            rel = str(v.relative_to(root))
            for style in args.styles:
                cached = CE._cache_load(CE._cache_path(args.cache_dir, v, BACKEND, args.caption_model, style))
                if cached:
                    outs[style][rel] = {"caption": cached, "model": args.caption_model, "style": style,
                                        "prompt_version": CE.CAPTION_PROMPT_VERSION, "source": "cache"}
                elif rel not in outs[style]:
                    need[style].append(v)
        for style in args.styles:
            print(f"  {style:11s}: cache hit {len(videos) - len(need[style])}, to generate {len(need[style])}")
        if args.dry_run:
            continue

        # 생성 (비디오당 업로드 1회, 스타일별 호출)
        todo = sorted({v for style in args.styles for v in need[style]})
        for i, v in enumerate(todo, 1):
            rel = str(v.relative_to(root))
            styles_here = [s for s in args.styles if v in need[s]]
            if client is None: client = make_client()
            print(f"  [{i}/{len(todo)}] {rel}  styles={styles_here}", flush=True)
            uploaded = upload_video(client, v)
            try:
                for style in styles_here:
                    cap = caption_with_retry(client, uploaded, style)
                    total_calls += 1
                    CE._cache_store(CE._cache_path(args.cache_dir, v, BACKEND, args.caption_model, style),
                                    v, BACKEND, args.caption_model, style, cap)
                    outs[style][rel] = {"caption": cap, "model": args.caption_model, "style": style,
                                        "prompt_version": CE.CAPTION_PROMPT_VERSION, "source": "generated"}
                    out_paths[style].write_text(json.dumps(outs[style], ensure_ascii=False, indent=1))  # 매 건 저장(중단 대비)
            finally:
                if not args.keep_uploads:
                    try: client.files.delete(name=uploaded.name)
                    except Exception: pass

        for style in args.styles:
            out_paths[style].write_text(json.dumps(outs[style], ensure_ascii=False, indent=1))
            n = len(outs[style]); missing = len(videos) - n
            print(f"  saved {out_paths[style]}  ({n} captions" + (f", {missing} MISSING" if missing else "") + ")")
    print(f"\ndone. API caption calls: {total_calls}")


if __name__ == "__main__":
    main()
