#!/usr/bin/env python3
"""GEPA v3 driver: multi-agent stage 2, 5 per-axis KEEP/REVISE paragraphs, video-unit minibatches, balanced score.

  cd evaluation/ablation
  export GEMINI_API_KEY=$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1
  python -u gepa_stage2/run_gepa_v3.py --sources gepa_stage2/sources_v3.json \
      --train gepa_stage2/manifests_v3/train.jsonl --val gepa_stage2/manifests_v3/val.jsonl \
      --run-dir gepa_stage2/runs/v3_s0 --seed 0 --budget-mult 15 --minibatch 4 --workers 6
Smoke:  ... --limit-train 6 --limit-val 4 --max-metric-calls 20 --run-dir gepa_stage2/runs/v3_smoke
Budget: --max-metric-calls counts video UNITS evaluated (GEPA's unit); default = budget-mult x val units.
        Judge calls ~= units x rows-per-unit (printed at start).
Outputs: run_dir/{seed,best}_candidate.json (5 paragraphs), best_<axis>.txt, candidates.json, gepa_state/.
"""
import argparse, inspect, json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gepa
import run_two_stage as TS
from adapter_v3 import V3Adapter, AXES, COMP, load_units, set_weights, make_propose_new_texts


def gemini_text_lm(model):
    from google import genai
    client = genai.Client()

    def call(prompt):
        for k in range(3):
            try:
                return client.models.generate_content(model=model, contents=prompt).text or ""
            except Exception as e:
                print(f"[reflect] attempt {k + 1} failed: {e}", flush=True)
        return ""
    return call


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True); ap.add_argument("--train", required=True); ap.add_argument("--val", required=True)
    ap.add_argument("--run-dir", required=True); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seed-rules", default=None, help="json {rules_A: ..., ...}; default = run_two_stage.SEED_RULES for every axis")
    ap.add_argument("--max-metric-calls", type=int, default=None); ap.add_argument("--budget-mult", type=float, default=15)
    ap.add_argument("--minibatch", type=int, default=4); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-chars-mult", type=float, default=3.0)
    ap.add_argument("--judge-model", default="gemini-3.6-flash"); ap.add_argument("--thinking", default="high")
    ap.add_argument("--reflection-model", default="gemini-3.1-pro-preview")
    ap.add_argument("--limit-train", type=int, default=None); ap.add_argument("--limit-val", type=int, default=None)
    a = ap.parse_args()

    run_dir = Path(a.run_dir); run_dir.mkdir(parents=True, exist_ok=True)
    log = lambda s: print(s, flush=True)
    train, val = load_units(a.train), load_units(a.val)
    rng = random.Random(a.seed)
    if a.limit_train: rng.shuffle(train); train = train[:a.limit_train]
    if a.limit_val: rng.shuffle(val); val = val[:a.limit_val]
    wt, wv = set_weights(train), set_weights(val)
    rows_t, rows_v = sum(len(u["rows"]) for u in train), sum(len(u["rows"]) for u in val)
    budget = a.max_metric_calls or int(a.budget_mult * len(val))
    log(f"[v3] train {len(train)} units / {rows_t} rows {wt}\n[v3] val {len(val)} units / {rows_v} rows {wv}")
    log(f"[v3] budget {budget} unit evaluations (~{budget * rows_v / max(len(val), 1):.0f} judge calls), "
        f"one full val pass = {rows_v} calls")

    seed = json.load(open(a.seed_rules)) if a.seed_rules else {COMP[ax]: TS.SEED_RULES for ax in AXES}
    max_chars = int(max(len(t) for t in seed.values()) * a.max_chars_mult)
    adapter = V3Adapter(json.load(open(a.sources)), run_dir, model=a.judge_model, thinking=a.thinking,
                        workers=a.workers, max_chars=max_chars, log=log)
    reflection_lm = gemini_text_lm(a.reflection_model)
    adapter.propose_new_texts = make_propose_new_texts(reflection_lm, max_chars, log=log)
    json.dump(seed, open(run_dir / "seed_candidate.json", "w"), indent=1)

    kw = dict(seed_candidate=seed, trainset=train, valset=val, adapter=adapter, reflection_lm=reflection_lm,
              max_metric_calls=budget, reflection_minibatch_size=a.minibatch, candidate_selection_strategy="pareto",
              run_dir=str(run_dir / "gepa_state"), seed=a.seed, display_progress_bar=True)
    params = inspect.signature(gepa.optimize).parameters
    if "module_selector" in params:
        kw["module_selector"] = "round_robin"           # one paragraph (axis) per proposal, cycling A, V, AVB, TCR, TCC
    if "use_merge" in params:
        kw["use_merge"] = False
    if "perfect_score" in params:
        kw["perfect_score"] = float(len(val))           # unit scores are scaled; effectively never "perfect"
    log(f"[v3] gepa.optimize args: {sorted(k for k in kw if k not in ('trainset', 'valset', 'adapter', 'seed_candidate'))}")
    result = gepa.optimize(**kw)

    best = result.best_candidate
    json.dump(best, open(run_dir / "best_candidate.json", "w"), indent=1)
    for ax in AXES:
        (run_dir / f"best_{ax}.txt").write_text(best[COMP[ax]])
    cands = [dict(idx=i, val_score=s, changed=[ax for ax in AXES if c[COMP[ax]] != seed[COMP[ax]]], rules=c)
             for i, (c, s) in enumerate(zip(result.candidates, result.val_aggregate_scores))]
    json.dump(cands, open(run_dir / "candidates.json", "w"), indent=1)
    log("\n== candidates (val = mean over axes of balanced acc)")
    for c in cands:
        log(f"  cand{c['idx']}: val {c['val_score']:.3f}  paragraphs changed vs seed: {c['changed']}")
    log(f"\n== best idx {result.best_idx}; judge calls used {adapter.n_calls}")
    for ax in AXES:
        same = best[COMP[ax]] == seed[COMP[ax]]
        log(f"\n--- {ax} {'(= seed)' if same else ''}\n{best[COMP[ax]].strip()}")


if __name__ == "__main__":
    main()