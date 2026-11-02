#!/usr/bin/env python3
"""Baseline GEPA run: evolve CAPTION_GENERAL_GUIDE for the V axis.

    python run_gepa.py --train manifests/train.jsonl --val manifests/val.jsonl \
        --run-dir gepa_runs/base_seed0 --max-metric-calls 300 --seed 0

Ablations (each is one flag):
    --no-caption-ok-feedback   drop the "caption describes this event correctly / not" line
    --include-source           tell the reflection LM which dataset each example is from
    --seed-guide FILE          start from a different guide (e.g. a one-line prompt)

Reflection LM = Gemini text-only (no video), same key as the judge. Task LM calls are
cached per (candidate, video) so re-evaluations of Pareto candidates are free.
Outputs in run-dir: gepa state (resume-able), best_candidate.txt, candidates.jsonl, summary.json.
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import gepa
from google import genai
from google.genai import types

import new_eval as NE
from adapter import COMPONENT, CaptionGuideAdapter, banned_phrases_from


REFLECTION_TEMPLATE = """A video-judging assistant (a multimodal LLM that watches the video and also receives a dense caption written by a separate captioning model) uses a long fixed system prompt. You are editing ONE section of that prompt: the policy that tells the judge how much to trust the caption and how to combine it with what it sees. Everything else (task description, output format, per-event criteria) is fixed elsewhere and must NOT be written here.

Current section:
```
<curr_param>
```

Examples of the judge's per-event decisions under this section, with the human ground truth and feedback:
```
<side_info>
```

Write an improved version of the section only. Requirements:
- Keep the same shape: a short heading plus bullet rules about caption trust and conflict handling.
- At most __MAXCHARS__ characters. Shorter is fine.
- General rules only. Do not mention specific objects, actions, videos, datasets or examples from the feedback; do not add a task description, output format, or per-event instructions.
- Focus on WHEN the caption should be trusted, discounted, or ignored, and what should happen when the caption contradicts, omits, or over-describes what the judge sees.

Provide the new section within ``` blocks."""


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def make_reflection_lm(client, model: str, thinking_level: str = "high"):
    def lm(prompt):
        if isinstance(prompt, list):  # chat format -> flatten
            prompt = "\n\n".join(f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in prompt)
        cfg = {"temperature": 1.0}
        if thinking_level != "none":
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
        r = client.models.generate_content(model=model, contents=[prompt], config=types.GenerateContentConfig(**cfg))
        return r.text or ""
    return lm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", type=Path, required=True)
    ap.add_argument("--val", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--model", default="gemini-3.1-pro-preview")
    ap.add_argument("--reflection-model", default=None, help="defaults to --model")
    ap.add_argument("--thinking-level", default="high", choices=["low", "high", "none"])
    ap.add_argument("--max-metric-calls", type=int, default=300)
    ap.add_argument("--minibatch", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-chars", type=int, default=0, help="candidate length cap; 0 = 1.25 x seed length")
    ap.add_argument("--fn-weight", type=float, default=0.25)
    ap.add_argument("--seed-guide", type=Path, default=None)
    ap.add_argument("--no-caption-ok-feedback", action="store_true")
    ap.add_argument("--include-source", action="store_true")
    ap.add_argument("--max-train", type=int, default=None, help="subsample train videos (Decagon: 20-100 is the sweet spot)")
    a = ap.parse_args()

    a.run_dir.mkdir(parents=True, exist_ok=True)
    train, val = read_jsonl(a.train), read_jsonl(a.val)
    if a.max_train:
        random.Random(a.seed).shuffle(train)
        train = train[: a.max_train]
    print(f"train={len(train)} val={len(val)}")

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=600_000)) if api_key \
        else genai.Client(http_options=types.HttpOptions(timeout=600_000))

    seed_text = a.seed_guide.read_text(encoding="utf-8") if a.seed_guide else NE.CAPTION_GENERAL_GUIDE
    if a.max_chars <= 0:
        a.max_chars = int(len(seed_text) * 1.25)
    print(f"seed guide {len(seed_text)} chars, cap {a.max_chars}")
    adapter = CaptionGuideAdapter(
        client, a.model, a.run_dir, thinking_level=a.thinking_level, fn_weight=a.fn_weight,
        max_chars=a.max_chars, workers=a.workers,
        feedback_caption_ok=not a.no_caption_ok_feedback, include_source=a.include_source,
    )
    # banned phrases: event labels / stems from train (needs item_meta -> build ctx lazily via prompt json)
    def meta_of(row):
        vp = Path(row["outputs_dir"]) / row["relpath"]
        return adapter._item_meta(row, NE.infer_item_id_from_path(vp))
    adapter.banned = [p for p in banned_phrases_from(train, meta_of)]
    print(f"banned phrases: {len(adapter.banned)}")

    seed_candidate = {COMPONENT: seed_text}
    (a.run_dir / "seed_candidate.txt").write_text(seed_text, encoding="utf-8")
    (a.run_dir / "config.json").write_text(json.dumps(vars(a), default=str, indent=2))

    result = gepa.optimize(
        seed_candidate=seed_candidate,
        trainset=train, valset=val, adapter=adapter,
        reflection_lm=make_reflection_lm(client, a.reflection_model or a.model, a.thinking_level),
        reflection_minibatch_size=a.minibatch,
        reflection_prompt_template=REFLECTION_TEMPLATE.replace("__MAXCHARS__", str(a.max_chars)),
        max_metric_calls=a.max_metric_calls,
        candidate_selection_strategy="pareto",
        run_dir=str(a.run_dir), seed=a.seed,
        display_progress_bar=True, raise_on_exception=False,
    )

    best = result.best_candidate[COMPONENT]
    (a.run_dir / "best_candidate.txt").write_text(best, encoding="utf-8")
    with (a.run_dir / "candidates.jsonl").open("w", encoding="utf-8") as f:
        for i, (c, s) in enumerate(zip(result.candidates, result.val_aggregate_scores)):
            f.write(json.dumps({"idx": i, "val_score": s, "parents": result.parents[i],
                                "chars": len(c[COMPONENT]), "text": c[COMPONENT]}, ensure_ascii=False) + "\n")
    summary = {
        "seed_val_score": result.val_aggregate_scores[0],
        "best_idx": result.best_idx, "best_val_score": result.val_aggregate_scores[result.best_idx],
        "n_candidates": len(result.candidates), "judge_calls": adapter.metric_calls,
        "best_chars": len(best),
    }
    (a.run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\n=== best candidate ===\n" + best)


if __name__ == "__main__":
    main()
