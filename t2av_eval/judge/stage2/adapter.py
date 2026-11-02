#!/usr/bin/env python3
"""GEPA adapter: one candidate = one STAGE2_RULES text block; one metric call = one stage-2 judge call on (item, axis).

What a metric call does (mirrors run_two_stage.py exactly, minus gating):
  1. build_context(video, item_meta, pipeline args) once per item (cached in memory) -> same evidence routing as the real
     run (A: Whisper+FLAM, V: external caption, AVB: both), evidence from cache (T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1).
  2. stage-1 judgment = the existing video-only run csv (fresh video-only call only if missing, as in run_two_stage).
  3. one stage-2 call for this axis with the CANDIDATE rules, video included, only the GT events.
  4. score = mean over GT events of (stage-2 label == GT)   (item-level if gt == {"__item__": ...}).
Disk cache key = (sha of rules, uid). Guardrails: candidate longer than seed x 1.5 or naming datasets / regimes -> score 0.

sources.json (paths; one entry per source, see README):
  {"hdepic": {"prompt_json": ..., "outputs_dirs": [...], "stage1": <dir or csv>, "caption_json": ..., "flam_ckpt": ...},
   "ltx":    {...}, "mova": {...}}
"""
import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)
from t2av_eval import paths as _P
import hashlib, json, os, re, sys, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

pass  # (legacy sys.path insert removed)
from t2av_eval.judge.media import core as NE
from t2av_eval.judge.media import common as AC
from t2av_eval.judge.media.axes import audio as axis_audio; from t2av_eval.judge.media.axes import visual as axis_visual; from t2av_eval.judge.media.axes import binding as axis_binding; from t2av_eval.judge.media.axes import temporal_relation as axis_temporal_relation; from t2av_eval.judge.media.axes import temporal_count as axis_temporal_count
import run_two_stage as TS
from t2av_eval.judge.media.runner import build_arg_parser

try:
    from gepa.core.adapter import EvaluationBatch
except Exception:                                  # gepa < 0.1 layout
    from gepa import EvaluationBatch

AXIS_FULL = {"A": TS.A, "V": TS.V, "AVB": TS.AVB, "TCR": TS.TCR, "TCC": TS.TCC}
AXIS_MOD = {"A": axis_audio, "V": axis_visual, "AVB": axis_binding, "TCR": axis_temporal_relation, "TCC": axis_temporal_count}


def axis_rules(mod):
    for name in ("_RULES", "RULES", "DECISION_RULES"):
        if hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"{mod.__name__}: no rules constant (_RULES / RULES / DECISION_RULES)")
# TODO(확인): criteria builders for A and V in new_eval (AVB one is confirmed from two_stage_avb.py).
CRITERIA = {
    "A": getattr(NE, "build_audio_axis_criteria", None) or getattr(NE, "build_audio_event_axis_criteria", None),
    "V": getattr(NE, "build_visual_axis_criteria", None) or getattr(NE, "build_visual_event_axis_criteria", None),
    "AVB": NE.build_av_binding_axis_criteria,
    # TC criteria need the temporal constraint: called as f(events, meta["temporal_constraint"])
    "TCR": NE.build_temporal_relation_criteria,
    "TCC": NE.build_temporal_count_criteria,
}
# per-axis event struct list on ctx (confirmed 10/20: audio_events, all_events, binding_events)
CTX_EVENTS = {"A": "audio_events", "V": "all_events", "AVB": "binding_events", "TCC": "all_events", "TCR": "all_events"}
AX_FILTER = {"A": "has_audio", "V": None, "AVB": "has_binding", "TCC": None, "TCR": None}   # which scoring events the judge labels

# words a rule block must not contain: dataset / regime / item identifiers (reflection template says the same)
BANNED = re.compile(r"hd-?epic|epic-?kitchens?|\bltx\b|\bmova\b|egocentric|first[- ]person|head[- ]mounted|\bkitchen\b|"
                    r"\bgenerated (video|clip)s?\b|\bsynthetic\b|\bAI[- ]generated\b|\breal (video|footage)\b|"
                    r"\bP\d{2}-\d{2}-\d{2}\b|\bevent_\d+\b|absent_sound|hand_swap|noun_swap|AVB(early|late)", re.I)

COMPONENT = "stage2_rules"


class Stage2Adapter:
    def __init__(self, sources, run_dir, model="gemini-3.1-pro-preview", thinking="high", workers=4,
                 max_chars=None, fn_weight=0.0, log=print):
        self.sources, self.run_dir, self.model, self.thinking = sources, Path(run_dir), model, thinking
        self.workers, self.fn_weight, self.log = workers, fn_weight, log
        self.max_chars = max_chars or int(len(TS.SEED_RULES) * 1.5)
        (self.run_dir / "cache").mkdir(parents=True, exist_ok=True)
        # fresh stage-1 calls are shared by every run under gepa_stage2/, independent of rules
        TS.FRESH_CACHE_DIR = _P.WORK / "fresh_stage1_cache"
        from google import genai
        self.client = genai.Client()
        self._lock = threading.Lock()
        self._ctx = {}                       # item_id -> ctx
        self._rows_by_uid = {}               # uid -> manifest row (for make_reflective_dataset)
        self._pargs, self._metas, self._vids, self._stage1 = {}, {}, {}, {}
        for src, cfg in sources.items():
            self._prepare_source(src, cfg)
        self.n_calls = 0

    # ------------------------------------------------------------ per-source pipeline objects
    def _prepare_source(self, src, cfg):
        argv = ["--prompt-json", cfg["prompt_json"], "--outputs-dir", cfg["outputs_dirs"][0],
                "--output-csv", str(self.run_dir / f"_unused_{src}.csv"), "--model", self.model, "--thinking-level", self.thinking,
                "--axes", "all", "--pose-evidence-mode", "none", "--media-input-mode", cfg.get("media", "video"),
                "--audio-evidence-mode", "whisper_flam", "--flam-ckpt-path", cfg["flam_ckpt"],
                "--caption-evidence-mode", "external", "--caption-style", "plain", "--caption-external-json", cfg["caption_json"]]
        pargs = build_arg_parser().parse_args(argv)
        if getattr(pargs, "focus_planner_model", None) is None:
            pargs.focus_planner_model = pargs.model
        items = NE.load_prompt_items(Path(cfg["prompt_json"]))
        metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
        vids = {}
        for d in cfg["outputs_dirs"]:
            for p in NE.find_video_files(Path(d)):
                vids.setdefault(NE.infer_item_id_from_path(p), p)
        self._pargs[src], self._metas[src], self._vids[src] = pargs, metas, vids
        self._stage1[src] = TS.load_stage1(cfg["stage1"])
        self.log(f"[adapter] {src}: {len(metas)} items, {len(vids)} clips, stage-1 {len(self._stage1[src])} rows")

    def _context(self, src, item_id):
        with self._lock:
            if item_id in self._ctx:
                return self._ctx[item_id]
        ctx = AC.build_context(self.client, self._vids[src][item_id], self._metas[src][item_id], self._pargs[src])
        with self._lock:
            self._ctx[item_id] = ctx
        return ctx

    # ------------------------------------------------------------ one stage-2 call
    def judge(self, row, rules):
        """Returns dict(labels={event_id: label}, stage1={event_id: label}, reasons={event_id: reason}, src=...).
        TCR: single item label stored under key "__item__". TCC: per-event observed_count -> yes/no vs required_count."""
        src, iid, ax = row["source"], row["item_id"], row["axis"]
        axis = AXIS_FULL[ax]
        meta = self._metas[src][iid]
        ctx = self._context(src, iid)
        structs_all = NE.build_scoring_events(meta)          # event_id / has_audio / has_binding / required_count live here
        flag = AX_FILTER[ax]
        axis_ids = [s["event_id"] for s in structs_all if flag is None or s.get(flag)]
        ids = [e for e in row["gt"] if e != "__item__"] or axis_ids
        if ax in ("TCR", "TCC"):
            tc = meta.get("temporal_constraint") or meta.get("constraint")
            if tc is None:
                raise KeyError("item_meta has no temporal_constraint")
            criteria = CRITERIA[ax](meta["events"], tc)
        else:
            criteria = CRITERIA[ax](meta["events"])
        base_rules = axis_rules(AXIS_MOD[ax])
        only = None if ax == "TCR" else ids
        with self._lock:                                   # TS.STAGE1 is module-global; swap per source
            TS.STAGE1 = self._stage1[src]
            text, entries, s1src = TS.build_stage2_user_text(ctx, axis, criteria, base_rules, only_event_ids=only, rules=rules)
        sysp = AC.axis_system_prompt(ctx, axis)
        parsed, raw = AC.call_gemini_json(ctx, sysp, text, TS.SCHEMA[axis])

        if ax == "TCR":                                    # one label for the whole item
            e1 = entries[0] if entries else {}
            return dict(labels={"__item__": str(parsed.get("label", "")).lower()},
                        reasons={"__item__": str(parsed.get("reason", ""))},
                        stage1={"__item__": str(e1.get("label", "")).lower()},
                        stage1_reasons={"__item__": str(e1.get("reason", ""))}, s1src=s1src, raw=raw)
        if ax == "TCC":                                    # observed_count vs required_count -> yes / no
            req = {s["event_id"]: s.get("required_count") for s in structs_all}

            def cnt_label(e):
                oc, rc = e.get("observed_count"), req.get(e.get("event_id"))
                if oc is None or rc is None:
                    return ""
                try:
                    return "yes" if int(oc) == int(rc) else "no"
                except (TypeError, ValueError):
                    return ""
            pe = [e for e in parsed.get("per_event", []) if e.get("event_id") in ids]
            return dict(labels={e["event_id"]: cnt_label(e) for e in pe},
                        reasons={e["event_id"]: f"observed={e.get('observed_count')} required={req.get(e['event_id'])}; " + str(e.get("reason", "")) for e in pe},
                        stage1={e["event_id"]: cnt_label(e) for e in entries if "event_id" in e},
                        stage1_reasons={e["event_id"]: f"observed={e.get('observed_count')}; " + str(e.get("reason", "")) for e in entries if "event_id" in e},
                        s1src=s1src, raw=raw)

        structs = getattr(ctx, CTX_EVENTS[ax], None) or structs_all
        structs = [s for s in structs if s["event_id"] in ids]
        pe = NE.normalize_label_per_event(parsed, structs, axis)
        return dict(labels={p["event_id"]: str(p.get("label", "")).lower() for p in pe},
                    reasons={p["event_id"]: str(p.get("reason", "")) for p in pe},
                    stage1={e["event_id"]: str(e.get("label", "")).lower() for e in entries if "event_id" in e},
                    stage1_reasons={e["event_id"]: str(e.get("reason", "")) for e in entries if "event_id" in e},
                    s1src=s1src, raw=raw)

    # ------------------------------------------------------------ scoring
    @staticmethod
    def score_row(row, out):
        gt = row["gt"]
        if "__item__" in gt:
            if "__item__" in out["labels"]:                   # TCR: the judge gives one item label
                item = out["labels"]["__item__"]
            else:
                labs = [l for l in out["labels"].values() if l in ("yes", "no")]
                item = "no" if "no" in labs else ("yes" if labs else "")
            return float(item == gt["__item__"]), {"__item__": (item, gt["__item__"])}
        per = {e: (out["labels"].get(e, ""), g) for e, g in gt.items()}
        ok = [float(p == g) for p, g in per.values()]
        return (sum(ok) / len(ok) if ok else 0.0), per

    def feedback(self, row, out, per, score):
        lines = [f"axis={row['axis']}  score={score:.2f}"]
        if "__item__" in per:                                   # item-level GT: show every event, then the item verdict
            p, g = per["__item__"]
            for e, lab in out["labels"].items():
                lines.append(f"- {e}: stage1={out['stage1'].get(e, '?')} -> stage2={lab} ({'kept' if lab == out['stage1'].get(e) else 'revised'})")
                lines.append(f"    stage-2 reason: {out['reasons'].get(e, '')[:220]}")
            if "__item__" in out["labels"]:
                want = "the item label"
            else:
                want = "at least one event must be 'no'" if g == "no" else "every event must be 'yes'"
            lines.append(f"- item verdict: {p}; correct answer: {g} ({want}) -> {'correct' if p == g else 'WRONG'}")
            if p != g and g == "no":
                lines.append("    -> something required by the prompt is missing or wrong in this clip but the judgment stayed 'yes'; the evidence or a re-check of the media should have revealed it.")
            return "\n".join(lines)
        for e, (p, g) in per.items():
            s1 = out["stage1"].get(e, "?")
            verdict = "correct" if p == g else "WRONG"
            move = "kept" if p == s1 else "revised"
            lines.append(f"- {e}: stage1={s1} -> stage2={p} ({move}); correct answer={g} -> {verdict}")
            r2 = out["reasons"].get(e, "")[:220].replace("\n", " ")
            lines.append(f"    stage-2 reason: {r2}")
            if p != g:
                r1 = out["stage1_reasons"].get(e, "")[:160].replace("\n", " ")
                lines.append(f"    stage-1 reason: {r1}")
                if s1 == g:
                    lines.append("    -> stage 1 was right; the revision was a mistake.")
                elif p == s1:
                    lines.append("    -> stage 1 was wrong and stage 2 kept it; the attached evidence or a re-check of the media should have changed it.")
        return "\n".join(lines)

    # ------------------------------------------------------------ guardrails + cache
    def _violation(self, rules):
        if len(rules) > self.max_chars:
            return f"rule block too long: {len(rules)} chars > {self.max_chars}"
        m = BANNED.search(rules)
        if m:
            return f"rule block names a dataset / regime / item ('{m.group(0)}'); rules must be generic"
        return None

    def _cache_path(self, rules, uid):
        sha = hashlib.sha1(rules.encode()).hexdigest()[:12]
        d = self.run_dir / "cache" / sha
        d.mkdir(exist_ok=True)
        return d / (re.sub(r"[^A-Za-z0-9_.|-]", "_", uid) + ".json")

    def _one(self, row, rules):
        p = self._cache_path(rules, row["uid"])
        if p.exists():
            return json.load(open(p))
        for attempt in range(3):
            try:
                out = self.judge(row, rules)
                break
            except Exception as e:
                self.log(f"[adapter] {row['uid']} attempt {attempt + 1} failed: {e}")
                time.sleep(5 * (attempt + 1))
        else:
            out = dict(labels={}, reasons={}, stage1={}, stage1_reasons={}, s1src="error", raw=traceback.format_exc())
        score, per = self.score_row(row, out)
        rec = dict(uid=row["uid"], score=score, per=per, out={k: v for k, v in out.items() if k != "raw"})
        if out["s1src"] == "error":
            rec["error"] = str(out["raw"])[-500:]            # scored 0 this time, not cached, hidden from reflection
        else:
            json.dump(rec, open(p, "w"))
        with self._lock:
            self.n_calls += 1
        return rec

    # ------------------------------------------------------------ GEPA protocol
    def evaluate(self, batch, candidate, capture_traces=False):
        self._rows_by_uid.update({r["uid"]: r for r in batch})   # make_reflective_dataset gets no batch; pair by uid
        rules = candidate[COMPONENT]
        bad = self._violation(rules)
        if bad:
            outs = [dict(uid=r["uid"], score=0.0, violation=bad) for r in batch]
            return EvaluationBatch(outputs=outs, scores=[0.0] * len(batch), trajectories=outs if capture_traces else None)
        with ThreadPoolExecutor(self.workers) as ex:
            recs = list(ex.map(lambda r: self._one(r, rules), batch))
        scores = [r["score"] for r in recs]
        self.log(f"[adapter] batch {len(batch)} mean {sum(scores) / max(len(scores), 1):.3f}  (calls so far {self.n_calls})")
        return EvaluationBatch(outputs=recs, scores=scores, trajectories=recs if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        items = []
        for rec in (eval_batch.trajectories or eval_batch.outputs):
            row = self._rows_by_uid[rec["uid"]]
            if "error" in rec:
                continue                                       # pipeline error, not the rule block's fault
            if "violation" in rec:
                items.append({"Inputs": "candidate rule block", "Generated Outputs": "(not run)", "Feedback": rec["violation"]})
                continue
            out = rec["out"]
            fb = self.feedback(row, out, {k: tuple(v) for k, v in rec["per"].items()}, rec["score"])
            items.append({"Inputs": f"stage-1 labels: {out['stage1']}  (correct answers: {row['gt']})",
                          "Generated Outputs": f"stage-2 labels: {out['labels']}", "Feedback": fb})
        return {COMPONENT: items}


REFLECTION_TEMPLATE = """You are improving ONE section of a long, fixed evaluation prompt used by a video judge.
The judge first labels each event from the video and audio alone (stage 1). Then, in a second call, it sees the video again
plus the stage-1 labels plus text evidence from tools (speech transcript, sound detections with timestamps, a dense caption),
and must output a final label per event. The section you are editing is the rule block that tells the judge when to KEEP
the stage-1 label and when to REVISE it. Everything else in the prompt is fixed and not shown here.

Current rule block:
<<<
{current}
>>>

Below are examples: the stage-1 labels, what the judge answered after reading this rule block, and feedback saying which
answers were right or wrong and why (a kept wrong label, a revised right label, ...).
<<<
{examples}
>>>

Write a new rule block that would make more of these answers correct.
Constraints:
- Output ONLY the rule block text, nothing else. At most {max_chars} characters.
- Keep it general: do not mention any specific object, action, word, sound, timestamp, video, person, dataset, camera style,
  or whether a video is real or generated. Do not write rules of the form "for axis X always ...". The same block is used for
  every axis and every video.
- Do not restate the task; the fixed prompt already does that. Only the KEEP / REVISE policy.
- Keep the instruction that each reason starts with "KEEP:" or "REVISE:".
"""


def make_propose_new_texts(reflection_lm, max_chars, log=print):
    def propose(candidate, reflective_dataset, components_to_update):
        out = {}
        for comp in components_to_update:
            ex = reflective_dataset.get(comp, [])
            ex_txt = "\n\n".join(f"[{i + 1}] {d['Inputs']}\n{d['Generated Outputs']}\n{d['Feedback']}" for i, d in enumerate(ex))
            prompt = REFLECTION_TEMPLATE.format(current=candidate[comp].strip(), examples=ex_txt, max_chars=max_chars)
            txt = reflection_lm(prompt).strip()
            txt = re.sub(r"^```[a-z]*\n|\n```$", "", txt).strip()
            if not txt.startswith("\n"):
                txt = "\n" + txt
            log(f"[reflect] proposed {len(txt)} chars")
            out[comp] = txt
        return out
    return propose
