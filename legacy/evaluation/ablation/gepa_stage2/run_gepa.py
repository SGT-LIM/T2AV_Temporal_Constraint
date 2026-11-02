#!/usr/bin/env python3
"""Run GEPA (0.1.4) on a judge rule block.

Stage 2 (10/19 KEEP/REVISE rules, unchanged):
  python -u gepa_stage2/run_gepa.py --sources gepa_stage2/sources.json \
      --train gepa_stage2/manifests/train.jsonl --val gepa_stage2/manifests/val.jsonl \
      --run-dir gepa_stage2/runs/s0 --max-metric-calls 300 --minibatch 3 --workers 4 --seed 0
Stage 1 (10/21: one run per axis; --stage1 video = media only, --stage1 tools = media + tool evidence):
  python -u gepa_stage2/run_gepa.py --stage1 video --axis A --sources gepa_stage2/sources.json \
      --train gepa_stage2/manifests/train.jsonl --val gepa_stage2/manifests/val.jsonl \
      --run-dir gepa_stage2/runs/s1video_A --max-metric-calls 150 --minibatch 3 --workers 4 --seed 0
  (train/val rows are filtered to --axis; seed = the axis module's own rule block unless --seed-rules is given)
Resume: same command (gepa reads run_dir state; our disk cache makes repeated calls free).
Smoke: --limit-train 5 --limit-val 3 --max-metric-calls 12
Outputs: run_dir/seed_candidate.txt, best_candidate.txt, candidates.json (all candidates + val scores), gepa_state/.
"""
import argparse, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gepa
from adapter import Stage2Adapter, make_propose_new_texts
import adapter as S2
import run_two_stage as TS


def load(p, limit=None, seed=0, axis=None):
    rows = [json.loads(l) for l in open(p)]
    if axis:
        rows = [r for r in rows if r["axis"] == axis]
    if limit:
        random.Random(seed).shuffle(rows); rows = rows[:limit]
    return rows


def gemini_text_lm(model):
    from google import genai
    client = genai.Client()

    def call(prompt):
        for k in range(3):
            try:
                r = client.models.generate_content(model=model, contents=prompt)
                return r.text or ""
            except Exception as e:
                print(f"[reflect] attempt {k + 1} failed: {e}", flush=True)
        return ""
    return call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True); ap.add_argument("--train", required=True); ap.add_argument("--val", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--seed-rules", default=None, help="text file; default = run_two_stage.SEED_RULES (stage 2) or the axis module rules (stage 1)")
    ap.add_argument("--max-metric-calls", type=int, default=300); ap.add_argument("--minibatch", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-chars-mult", type=float, default=1.5)
    ap.add_argument("--judge-model", default="gemini-3.1-pro-preview"); ap.add_argument("--thinking", default="high")
    ap.add_argument("--reflection-model", default="gemini-3.1-pro-preview")
    ap.add_argument("--limit-train", type=int, default=None); ap.add_argument("--limit-val", type=int, default=None)
    ap.add_argument("--orchestrator", action="store_true", help="optimise the rules for the one-call-per-video stage 2 (run_orchestrator.OrchAdapter)")
    ap.add_argument("--stage1", choices=["video", "tools"], default=None, help="optimise the STAGE-1 per-axis rule block instead (needs --axis)")
    ap.add_argument("--axis", choices=["A", "V", "AVB", "TCR", "TCC"], default=None)
    a = ap.parse_args()
    if a.stage1 and not a.axis:
        sys.exit("--stage1 needs --axis")

    run_dir = Path(a.run_dir); run_dir.mkdir(parents=True, exist_ok=True)
    log = lambda s: print(s, flush=True)
    train, val = load(a.train, a.limit_train, a.seed, a.axis), load(a.val, a.limit_val, a.seed, a.axis)

    if a.stage1:
        from stage1_adapter import Stage1Adapter, COMPONENT
        from stage1_adapter import make_propose_new_texts as make_propose_s1
        adapter = Stage1Adapter(json.load(open(a.sources)), run_dir, axis=a.axis, mode=a.stage1, max_chars_mult=a.max_chars_mult,
                                model=a.judge_model, thinking=a.thinking, workers=a.workers, log=log)
        seed_rules = Path(a.seed_rules).read_text() if a.seed_rules else adapter.seed_rules
        max_chars = adapter.max_chars
        reflection_lm = gemini_text_lm(a.reflection_model)
        adapter.propose_new_texts = make_propose_s1(reflection_lm, max_chars, a.axis, a.stage1, log=log)
    else:
        COMPONENT = S2.COMPONENT
        seed_rules = Path(a.seed_rules).read_text() if a.seed_rules else TS.SEED_RULES
        max_chars = int(len(seed_rules) * a.max_chars_mult)
        if a.orchestrator:
            from run_orchestrator import OrchAdapter, group_rows
            train, val = group_rows(train), group_rows(val)
            print(f"[gepa] orchestrator mode: train {len(train)} videos, val {len(val)} videos (one call each)", flush=True)
            adapter = OrchAdapter(json.load(open(a.sources)), run_dir, model=a.judge_model, thinking=a.thinking,
                                  workers=a.workers, max_chars=max_chars, log=log)
        else:
            adapter = Stage2Adapter(json.load(open(a.sources)), run_dir, model=a.judge_model, thinking=a.thinking,
                                    workers=a.workers, max_chars=max_chars, log=log)
        reflection_lm = gemini_text_lm(a.reflection_model)
        adapter.propose_new_texts = make_propose_new_texts(reflection_lm, max_chars, log=log)

    (run_dir / "seed_candidate.txt").write_text(seed_rules)
    print(f"[gepa] train {len(train)} val {len(val)} rows; seed {len(seed_rules)} chars, cap {max_chars}"
          + (f"; stage1 {a.stage1} axis {a.axis}" if a.stage1 else ""), flush=True)

    result = gepa.optimize(
        seed_candidate={COMPONENT: seed_rules},
        trainset=train, valset=val, adapter=adapter,
        reflection_lm=reflection_lm,                 # used only if adapter.propose_new_texts were None
        max_metric_calls=a.max_metric_calls, reflection_minibatch_size=a.minibatch,
        candidate_selection_strategy="pareto", perfect_score=1.0,
        run_dir=str(run_dir / "gepa_state"), seed=a.seed, display_progress_bar=True,
    )

    best = result.best_candidate[COMPONENT]
    (run_dir / "best_candidate.txt").write_text(best)
    cands = [dict(idx=i, val_score=s, chars=len(c[COMPONENT]), rules=c[COMPONENT])
             for i, (c, s) in enumerate(zip(result.candidates, result.val_aggregate_scores))]
    json.dump(cands, open(run_dir / "candidates.json", "w"), indent=1)
    print("\n== candidates (val aggregate)")
    for c in cands:
        print(f"  cand{c['idx']}: val {c['val_score']:.3f}  {c['chars']} chars")
    print(f"\n== best (idx {result.best_idx}):\n{best}\n-> {run_dir}/best_candidate.txt   metric calls used: {adapter.n_calls}")


if __name__ == "__main__":
    main()
