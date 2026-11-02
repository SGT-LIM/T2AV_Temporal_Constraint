#!/usr/bin/env python3
"""GEPAAdapter for the V-axis caption evidence-use policy (CAPTION_GENERAL_GUIDE).

Candidate = {"caption_guide": <text>}. The text replaces CAPTION_GENERAL_GUIDE in
the Visual agent's system prompt (via ctx.config["caption_guide_override"], see
patch_caption_guide_override.py). Everything else (core prompt, criteria, caption
section, media, thinking level, temperature 0 / seed 42) is byte-identical to a
normal `run_agentic_eval.py --axes v --caption-evidence-mode external` run.

Per video: build_context once (video upload + caption section), cached in memory.
Per (candidate, video): axis_visual.evaluate, cached on disk by sha1(candidate).

Score per video = mean over GT events of
    1.0   correct
    FN_W  judge FAIL, GT PASS   (default 0.25: a missed pass is cheaper ...)
    0.0   judge PASS, GT FAIL   (... than a false PASS, RubricForge / WER cost-matrix)
Guardrails: candidates longer than --max-chars or containing a banned phrase
(train-set event labels / video stems) score 0 on every item with an explicit
feedback string, so GEPA learns the constraint instead of silently overfitting.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pickle
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from gepa.core.adapter import EvaluationBatch

import new_eval as NE
import axis_visual
from agentic_common import build_context
from run_agentic_eval import build_arg_parser

COMPONENT = "caption_guide"


def _sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


class CaptionGuideAdapter:
    propose_new_texts = None   # use gepa's default reflective proposer

    def __init__(self, client, model: str, run_dir: Path, *, thinking_level: str = "high",
                 media_fps: float = 24.0, fn_weight: float = 0.25, max_chars: int = 1500,
                 banned_phrases: list[str] | None = None, workers: int = 4,
                 feedback_caption_ok: bool = True, include_source: bool = False,
                 caption_chars_in_reflection: int = 1800, timeout_seconds: float = 600.0):
        self.client = client
        self.model = model
        self.run_dir = Path(run_dir)
        self.cache_dir = self.run_dir / "eval_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thinking_level = thinking_level
        self.media_fps = media_fps
        self.fn_weight = fn_weight
        self.max_chars = max_chars
        self.banned = [p.lower() for p in (banned_phrases or []) if len(p) >= 12]
        self.workers = workers
        self.feedback_caption_ok = feedback_caption_ok
        self.include_source = include_source
        self.caption_chars = caption_chars_in_reflection
        self.timeout_seconds = timeout_seconds
        self._ctx: dict[tuple, Any] = {}
        self._meta_maps: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.metric_calls = 0

    # ------------------------------------------------------------ context
    def _args_for(self, item: dict):
        argv = [
            "--prompt-json", item["prompt_json"], "--outputs-dir", item["outputs_dir"],
            "--output-csv", str(self.run_dir / "_unused.csv"), "--model", self.model,
            "--axes", "v", "--caption-evidence-mode", "external",
            "--caption-external-json", item["caption_json"],
            "--thinking-level", self.thinking_level, "--media-fps", str(self.media_fps),
            "--timeout-seconds", str(self.timeout_seconds), "--no-per-event-csv",
        ]
        args = build_arg_parser().parse_args(argv)
        args.avb_prereq_store = None
        args.focus_planner_model = args.model
        return args

    def _item_meta(self, item: dict, item_id: str) -> dict:
        key = item["prompt_json"]
        with self._lock:
            if key not in self._meta_maps:
                items = NE.load_prompt_items(Path(key))
                self._meta_maps[key] = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
        meta = self._meta_maps[key].get(item_id)
        if meta is None:
            raise KeyError(f"no prompt metadata for item_id={item_id} ({item['relpath']})")
        return meta

    def get_ctx(self, item: dict, rebuild: bool = False):
        key = (item["source"], item["outputs_dir"], item["relpath"])
        with self._lock:
            if not rebuild and key in self._ctx:
                return self._ctx[key]
        args = self._args_for(item)
        video_path = Path(item["outputs_dir"]) / item["relpath"]
        item_id = NE.infer_item_id_from_path(video_path)
        meta = self._item_meta(item, item_id)
        ctx = build_context(self.client, video_path, meta, args)
        with self._lock:
            self._ctx[key] = ctx
        return ctx

    # ------------------------------------------------------------ one judge call
    def _judge(self, item: dict, guide: str) -> dict:
        """Return {"per_event": [...], "user_text": str, "raw": str} for (guide, video), disk-cached."""
        cpath = self.cache_dir / f"{_sha(guide)}__{item['source']}__{_sha(item['outputs_dir'] + '/' + item['relpath'])}.pkl"
        if cpath.exists():
            return pickle.loads(cpath.read_bytes())
        last = None
        for attempt in range(2):
            ctx = self.get_ctx(item, rebuild=attempt > 0)
            ctx2 = dataclasses.replace(ctx, config={**ctx.config, "caption_guide_override": guide})
            try:
                v = axis_visual.evaluate(ctx2)
                out = {"per_event": v["per_event"], "user_text": v.get("user_text", ""), "raw": v.get("raw", "")}
                cpath.write_bytes(pickle.dumps(out))
                with self._lock:
                    self.metric_calls += 1
                return out
            except Exception as e:  # expired upload handle etc.: rebuild ctx once
                last = e
        return {"per_event": [], "user_text": "", "raw": "", "error": f"{type(last).__name__}: {last}"}

    # ------------------------------------------------------------ scoring
    def _score(self, item: dict, per_event: list[dict]):
        pred = {pe["event_id"]: ("PASS" if pe.get("label") == "yes" else "FAIL") for pe in per_event}
        if pred and not (set(pred) & set(item["gt"])):
            print(f"  [WARN] event_id mismatch for {item['relpath']}: judge={sorted(pred)} gt={sorted(item['gt'])}", flush=True)
        rows, total = [], 0.0
        for eid, gt in item["gt"].items():
            p = pred.get(eid, "MISSING")
            if p == gt:
                s = 1.0
            elif p == "FAIL" and gt == "PASS":
                s = self.fn_weight
            else:
                s = 0.0
            total += s
            rows.append((eid, gt, p, s))
        return (total / len(rows) if rows else 0.0), rows

    def _guardrail(self, guide: str) -> str | None:
        if len(guide) > self.max_chars:
            return f"Candidate is {len(guide)} chars; limit is {self.max_chars}. Shorten it."
        low = guide.lower()
        hits = [p for p in self.banned if p in low]
        if hits:
            return f"Candidate quotes item-specific content ({hits[0]!r}). Write general rules only."
        return None

    # ------------------------------------------------------------ GEPAAdapter API
    def evaluate(self, batch: list[dict], candidate: dict[str, str], capture_traces: bool = False) -> EvaluationBatch:
        guide = candidate[COMPONENT]
        bad = self._guardrail(guide)
        if bad:
            print(f"  [GUARDRAIL] {bad}", flush=True)
            trajs = [{"item": it, "per_event": [], "rows": [], "error": bad} for it in batch]
            return EvaluationBatch(outputs=[None] * len(batch), scores=[0.0] * len(batch),
                                   trajectories=trajs if capture_traces else None)

        def one(it):
            res = self._judge(it, guide)
            score, rows = self._score(it, res["per_event"])
            if res.get("error"):
                score = 0.0
            return res, score, rows

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            results = list(ex.map(one, batch))
        outputs = [{"relpath": it["relpath"], "rows": r[2]} for it, r in zip(batch, results)]
        scores = [r[1] for r in results]
        trajs = None
        if capture_traces:
            trajs = [{"item": it, "per_event": r[0]["per_event"], "rows": r[2],
                      "caption": self._caption_text(it), "error": r[0].get("error")}
                     for it, r in zip(batch, results)]
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajs)

    def _caption_text(self, item: dict) -> str:
        """Caption body for the reflective dataset. Uses the in-memory ctx if this video was
        judged in this process; otherwise reads the external caption JSON directly (no upload)."""
        key = (item["source"], item["outputs_dir"], item["relpath"])
        ctx = self._ctx.get(key)
        cap = (ctx.evidence.get("caption", "") if ctx else "") or self._caption_from_json(item)
        cap = re.sub(r"\s+", " ", cap or "").strip()
        return cap[: self.caption_chars] + (" ..." if len(cap) > self.caption_chars else "")

    def _caption_from_json(self, item: dict) -> str:
        path = item.get("caption_json")
        if not path:
            return ""
        with self._lock:
            if path not in self._meta_maps:
                try:
                    raw = json.loads(Path(path).read_text(encoding="utf-8"))
                except Exception:
                    raw = {}
                idx = {}
                for k, v in (raw.items() if isinstance(raw, dict) else []):
                    text = v.get("caption", "") if isinstance(v, dict) else str(v)
                    for alias in (k, Path(k).name, Path(k).stem):
                        idx.setdefault(alias, text)
                self._meta_maps[path] = idx
        idx = self._meta_maps[path]
        rp = item["relpath"]
        return idx.get(rp) or idx.get(Path(rp).name) or idx.get(Path(rp).stem) or ""

    def make_reflective_dataset(self, candidate, eval_batch: EvaluationBatch, components_to_update):
        recs = []
        for tr in eval_batch.trajectories or []:
            it = tr["item"]
            if tr.get("error") and not tr["rows"]:
                recs.append({"Inputs": "(guardrail / call failure)", "Generated Outputs": "", "Feedback": tr["error"]})
                continue
            ctx = self.get_ctx(it)
            meta = ctx.item_meta
            events = "\n".join(f"- {NE.describe_event(e)}" for e in meta.get("events", []))
            src = f"Source: {it['source']}\n" if self.include_source else ""
            inputs = (f"{src}Generation prompt: {meta.get('generated_prompt', '')}\n"
                      f"Target events:\n{events}\n"
                      f"Dense caption given to the judge:\n{tr['caption']}")
            reason_of = {pe["event_id"]: pe for pe in tr["per_event"]}
            outs, fb = [], []
            for eid, gt, pred, s in tr["rows"]:
                pe = reason_of.get(eid, {})
                outs.append(f"[{eid}] judge={pred} | reason: {pe.get('reason', '')} | evidence: {pe.get('evidence', '')}")
                if pred == gt:
                    line = f"[{eid}] CORRECT (human={gt})."
                elif pred == "PASS":
                    line = f"[{eid}] WRONG: judge PASS but humans marked FAIL (false pass, worst error)."
                else:
                    line = f"[{eid}] WRONG: judge FAIL but humans marked PASS (missed pass)."
                rat = it.get("rationale", {}).get(eid)
                if rat:
                    line += f" Human rationale: {rat}"
                if self.feedback_caption_ok:
                    co = it.get("caption_ok", {}).get(eid)
                    if co is True:
                        line += " The caption describes this event correctly."
                    elif co is False:
                        line += " The caption does NOT describe this event correctly (wrong object, wrong action, or omitted)."
                fb.append(line)
            recs.append({"Inputs": inputs, "Generated Outputs": "\n".join(outs),
                         "Feedback": "\n".join(fb) + f"\nVideo score: {sum(r[3] for r in tr['rows']) / max(1, len(tr['rows'])):.2f}"})
        return {COMPONENT: recs}


def banned_phrases_from(manifest_rows: list[dict], prompt_meta_loader) -> list[str]:
    """Event labels + video stems from the train manifest: the candidate must not quote them."""
    out = set()
    for r in manifest_rows:
        out.add(Path(r["relpath"]).stem.lower())
        try:
            meta = prompt_meta_loader(r)
            for e in meta.get("events", []):
                lab = (e.get("label") or e.get("description") or "").strip().lower()
                if len(lab) >= 12:
                    out.add(lab)
        except Exception:
            pass
    return sorted(out)
