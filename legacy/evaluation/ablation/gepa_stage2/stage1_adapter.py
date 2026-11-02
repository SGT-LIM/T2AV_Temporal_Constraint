#!/usr/bin/env python3
"""GEPA adapter for STAGE 1 (10/21 meeting: optimise stage 1 first, then stage 1 + tools, only then stage 2).

One candidate = the per-axis decision-rule block that the normal single-call judge already uses
(axis_*.py `_RULES` / `RULES` / `DECISION_RULES`, i.e. the `decision_rules` argument of agentic_common.build_axis_user_text).
One run = ONE axis (--axis A|V|AVB|TCR|TCC), so the component is just "rules" and the reflection is per axis.

mode="video": the judge sees the video (+ its audio) only, evidence stripped exactly like run_two_stage.fresh_stage1.
mode="tools": the judge sees the video + the same tool evidence routing as the one-shot W+F+caption run
              (A: Whisper+FLAM, V: caption, AVB: both, TC: whatever build_context routes), evidence from cache.

Everything else (sources.json, manifests, GT, scoring, cache layout, guardrails) is shared with adapter.Stage2Adapter.
Reference column for eval: mode video -> the existing video-only run (sources[src]["stage1"]);
                           mode tools -> the one-shot run (eval_rules --oneshot).
"""
import copy, hashlib, json, re, sys, time, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapter import Stage2Adapter, AXIS_FULL, AXIS_MOD, CRITERIA, CTX_EVENTS, AX_FILTER, BANNED, axis_rules
import new_eval as NE
import agentic_common as AC
import run_two_stage as TS

COMPONENT = "rules"
AXIS_NAME = {"A": "audio event correctness", "V": "visual event correctness", "AVB": "audio-visual binding (sync)",
             "TCR": "temporal relation (event order)", "TCC": "temporal count"}


class Stage1Adapter(Stage2Adapter):
    def __init__(self, sources, run_dir, axis, mode="video", max_chars_mult=1.5, **kw):
        assert axis in AXIS_FULL and mode in ("video", "tools")
        self.axis, self.mode = axis, mode
        self.seed_rules = axis_rules(AXIS_MOD[axis])
        kw.setdefault("max_chars", int(len(self.seed_rules) * max_chars_mult))
        super().__init__(sources, run_dir, **kw)
        self.log(f"[stage1] axis {axis} mode {mode}; seed rules {len(self.seed_rules)} chars, cap {self.max_chars}")

    # ------------------------------------------------------------ one stage-1 call
    def _ctx_for_call(self, ctx):
        """mode video: a shallow copy with evidence blanked and this axis' tools off (same as fresh_stage1, but no mutation
        of the shared ctx, so workers > 1 is safe). mode tools: the shared ctx as built (evidence from cache)."""
        if self.mode == "tools":
            return ctx
        c = copy.copy(ctx)
        c.evidence = {k: "" for k in ctx.evidence}
        c.use_tools = dict(ctx.use_tools)
        c.use_tools[AXIS_FULL[self.axis]] = False
        return c

    def judge(self, row, rules):
        src, iid, ax = row["source"], row["item_id"], row["axis"]
        assert ax == self.axis, f"row axis {ax} != adapter axis {self.axis}"
        axis = AXIS_FULL[ax]
        meta = self._metas[src][iid]
        ctx = self._ctx_for_call(self._context(src, iid))
        structs_all = NE.build_scoring_events(meta)
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
        only = None if ax == "TCR" else ids
        text = TS._ORIG(ctx, axis, criteria, rules, only_event_ids=only)      # unpatched builder: plain single-stage text
        sysp = AC.axis_system_prompt(ctx, axis)
        parsed, raw = AC.call_gemini_json(ctx, sysp, text, TS.SCHEMA[axis])

        # reference labels = the existing video-only run (so eval tables keep a "video_only" column and a changed/right/wrong block)
        with self._lock:
            TS.STAGE1 = self._stage1[src]
            ref_entries, _missing = TS.stage1_lookup(iid, axis, only)
        if ax == "TCR":
            e1 = ref_entries[0] if ref_entries else {}
            return dict(labels={"__item__": str(parsed.get("label", "")).lower()},
                        reasons={"__item__": str(parsed.get("reason", ""))},
                        stage1={"__item__": str(e1.get("label", "")).lower()}, stage1_reasons={"__item__": str(e1.get("reason", ""))},
                        s1src="ref", raw=raw)
        if ax == "TCC":
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
                        stage1={e["event_id"]: cnt_label(e) for e in ref_entries if "event_id" in e},
                        stage1_reasons={e["event_id"]: str(e.get("reason", "")) for e in ref_entries if "event_id" in e},
                        s1src="ref", raw=raw)
        structs = getattr(ctx, CTX_EVENTS[ax], None) or structs_all
        structs = [s for s in structs if s["event_id"] in ids]
        pe = NE.normalize_label_per_event(parsed, structs, axis)
        return dict(labels={p["event_id"]: str(p.get("label", "")).lower() for p in pe},
                    reasons={p["event_id"]: str(p.get("reason", "")) for p in pe},
                    stage1={e["event_id"]: str(e.get("label", "")).lower() for e in ref_entries if "event_id" in e},
                    stage1_reasons={e["event_id"]: str(e.get("reason", "")) for e in ref_entries if "event_id" in e},
                    s1src="ref", raw=raw)

    # ------------------------------------------------------------ feedback (no KEEP/REVISE story here)
    def feedback(self, row, out, per, score):
        lines = [f"axis={row['axis']}  score={score:.2f}"]
        if "__item__" in per:
            p, g = per["__item__"]
            for e, lab in out["labels"].items():
                lines.append(f"- {e}: judged {lab}")
                lines.append(f"    reason: {out['reasons'].get(e, '')[:220].replace(chr(10), ' ')}")
            want = "the item label" if "__item__" in out["labels"] else ("at least one event must be 'no'" if g == "no" else "every event must be 'yes'")
            lines.append(f"- item verdict: {p}; correct answer: {g} ({want}) -> {'correct' if p == g else 'WRONG'}")
            if p != g:
                lines.append("    -> something required by the prompt is missing or wrong in this clip but the judge passed it."
                             if g == "no" else "    -> the clip does satisfy the prompt but the judge failed it.")
            return "\n".join(lines)
        for e, (p, g) in per.items():
            lines.append(f"- {e}: judged {p}; correct answer={g} -> {'correct' if p == g else 'WRONG'}")
            lines.append(f"    reason: {out['reasons'].get(e, '')[:220].replace(chr(10), ' ')}")
            if p != g:
                lines.append("    -> false pass: the event is missing or wrong in the clip." if g == "no" else
                             "    -> false fail: the event is actually there and correct.")
        return "\n".join(lines)

    # cache key includes mode so video / tools runs never share a cached verdict even for identical rules
    def _cache_path(self, rules, uid):
        sha = hashlib.sha1(f"{self.mode}|{self.axis}|{rules}".encode()).hexdigest()[:12]
        d = self.run_dir / "cache" / sha
        d.mkdir(exist_ok=True)
        return d / (re.sub(r"[^A-Za-z0-9_.|-]", "_", uid) + ".json")

    def evaluate(self, batch, candidate, capture_traces=False):
        from concurrent.futures import ThreadPoolExecutor
        from adapter import EvaluationBatch
        self._rows_by_uid.update({r["uid"]: r for r in batch})
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
                continue
            if "violation" in rec:
                items.append({"Inputs": "candidate rule block", "Generated Outputs": "(not run)", "Feedback": rec["violation"]})
                continue
            out = rec["out"]
            fb = self.feedback(row, out, {k: tuple(v) for k, v in rec["per"].items()}, rec["score"])
            items.append({"Inputs": f"events to judge: {list(row['gt'].keys())}  (correct answers: {row['gt']})",
                          "Generated Outputs": f"judge labels: {out['labels']}", "Feedback": fb})
        return {COMPONENT: items}


REFLECTION_TEMPLATE = """You are improving ONE section of a long, fixed evaluation prompt used by a video judge for the axis
"{axis_name}". The judge watches the video{evidence_clause} and outputs a label per event (or one label for the clip)
with a reason. The section you are editing is the decision-rule block: how the judge should decide pass / fail for this axis.
Everything else in the prompt (task description, event list, output format) is fixed and not shown here.

Current rule block:
<<<
{current}
>>>

Below are examples: what the judge answered after reading this rule block, and feedback saying which answers were right or
wrong and why (false pass = the event was missing / wrong but got 'yes'; false fail = it was correct but got 'no').
<<<
{examples}
>>>

Write a new rule block that would make more of these answers correct.
Constraints:
- Output ONLY the rule block text, nothing else. At most {max_chars} characters.
- Keep it general: do not mention any specific object, action, word, sound, timestamp, video, person, dataset, camera style,
  or whether a video is real or generated. The same block is used for every video.
- Do not restate the task and do not change the output format; keep any instruction in the current block about how to write
  the label or the reason.
- Keep the lines that define the scope of this axis (per-event / between-event, which events are judged) as they are; add or change only the decision rules after them.
- Do not fix the examples one by one; write rules about how to look, listen, and decide. No parenthetical examples (no "e.g."): a rule that needs an example is too specific.
"""
EVIDENCE_CLAUSE = {"video": " and listens to its audio, with NO other evidence",
                   "tools": ", listens to its audio, and also gets text evidence from tools (a speech transcript, sound detections "
                            "with timestamps, and/or a dense caption), which is approximate and can be wrong or incomplete"}


def make_propose_new_texts(reflection_lm, max_chars, axis, mode, log=print):
    def propose(candidate, reflective_dataset, components_to_update):
        out = {}
        for comp in components_to_update:
            ex = reflective_dataset.get(comp, [])
            ex_txt = "\n\n".join(f"[{i + 1}] {d['Inputs']}\n{d['Generated Outputs']}\n{d['Feedback']}" for i, d in enumerate(ex))
            prompt = REFLECTION_TEMPLATE.format(axis_name=AXIS_NAME[axis], evidence_clause=EVIDENCE_CLAUSE[mode],
                                                current=candidate[comp].strip(), examples=ex_txt, max_chars=max_chars)
            txt = reflection_lm(prompt).strip()
            txt = re.sub(r"^```[a-z]*\n|\n```$", "", txt).strip()
            log(f"[reflect] proposed {len(txt)} chars")
            out[comp] = txt
        return out
    return propose
