#!/usr/bin/env python3
"""Stage-2 ORCHESTRATOR: one call per video that sees the video, ALL tool evidence (W+F and caption), the stage-1
judgments of ALL axes, and the KEEP/REVISE rules, and returns the final labels of all axes at once (RESULT_SCHEMA).
Compare against the per-axis stage 2 (adapter.py / run_two_stage.py) with the same stage-1 run, evidence, rules and test rows.

Writes the same long csv as eval_rules.py (heldout_test_<tag>.csv: uid, source, item_id, axis, variant, eval_only, event_id,
gt, stage1, pred, tag), so eval_rules.py --extra-heldout orch=<csv> puts it in the same tables.

  cd evaluation/ablation
  python -u gepa_stage2/run_orchestrator.py --sources gepa_stage2/sources.json --manifest gepa_stage2/manifests/test.jsonl \
      --rules gepa_stage2/runs/s0/seed_candidate.txt --tag orch_seed --run-dir gepa_stage2/runs/orch --workers 4
Cache: run_dir/cache_orch/<rules sha>/<item>.json  (one call covers every axis row of that item). Resumable.
"""
import argparse, hashlib, json, re, sys, threading, time, traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE
import agentic_common as AC
import run_two_stage as TS
from adapter import Stage2Adapter, AXIS_FULL, AXIS_MOD, CRITERIA, axis_rules, BANNED
try:
    from gepa.core.adapter import EvaluationBatch
except Exception:
    from gepa import EvaluationBatch

AXES = ["A", "V", "AVB", "TCR", "TCC"]

ORCH_HEAD = """
TWO-STAGE PROTOCOL, ALL AXES AT ONCE:
- Below, under "Stage 1 (media only)", are the judgments you already made for EACH axis from the video and audio alone.
- Tool evidence (speech transcript, sound detections, dense caption) is attached. Output the final label of every axis.
- The axes are hierarchical: an event that fails A or V cannot pass AVB; a clip with any A / V / AVB failure fails the TC axes.
  Use this when deciding whether a failure belongs to an axis itself or is inherited from a parent axis.
"""


class Orchestrator(Stage2Adapter):
    """Reuses the adapter's per-source pipeline objects, contexts and stage-1 tables; replaces the call."""

    def stage1_blocks(self, src, iid, ctx, meta):
        """Stage-1 block for every axis (fresh video-only call for events that stage 1 never judged)."""
        structs = NE.build_scoring_events(meta)
        blocks, s1 = [], {}
        with self._lock:
            TS.STAGE1 = self._stage1[src]
            for ax in AXES:
                axis = AXIS_FULL[ax]
                entries, missing = TS.stage1_lookup(iid, axis, None)
                if missing:
                    tc = meta.get("temporal_constraint") or meta.get("constraint")
                    crit = CRITERIA[ax](meta["events"], tc) if ax in ("TCR", "TCC") else CRITERIA[ax](meta["events"])
                    ids = None if missing == ["__single__"] else missing
                    try:
                        entries = entries + TS.fresh_stage1(ctx, axis, crit, axis_rules(AXIS_MOD[ax]), ids)
                    except Exception as e:
                        self.log(f"[orch] fresh stage-1 {ax} failed for {iid}: {e}")
                if entries:
                    blocks.append(TS.fmt_block(axis, entries))
                    s1[ax] = entries
        return "\n\n".join(blocks), s1, structs

    def judge_item(self, src, iid, rules):
        meta = self._metas[src][iid]
        ctx = self._context(src, iid)
        s1_text, s1, structs = self.stage1_blocks(src, iid, ctx, meta)
        ev = ctx.evidence
        user = NE.make_user_text(meta, body_pose_section="", audio_evidence_section=ev.get("audio", "") or "")
        cap = ev.get("caption", "") or ""
        insert = (cap + "\n\n" if cap else "") + s1_text + "\n"
        j = user.find("Axis criteria")
        user = (user[:j] + insert + "\n" + user[j:]) if j >= 0 else (user + "\n\n" + insert)
        user += "\n" + ORCH_HEAD + rules
        modes = ctx.evidence_modes
        sysp = NE.build_system_prompt(pose_evidence_mode="none", audio_evidence_mode=modes.get("audio", "none"),
                                      caption_evidence_mode=modes.get("caption", "none"), single_axis=False)
        parsed, raw = AC.call_gemini_json(ctx, sysp, user, NE.RESULT_SCHEMA)
        req = {s["event_id"]: s.get("required_count") for s in structs}
        FLAG = {"A": "has_audio", "V": None, "AVB": "has_binding"}

        def canon(e):
            """model may answer with the prompt's own event ids (e2_close) -> map to event_N via index / source_id / aliases."""
            eid = str(e.get("event_id", ""))
            if eid in req:
                return eid
            m = re.match(r"^e(\d+)[_-]", eid) or re.match(r"^event[_ ]?(\d+)$", eid, re.I)
            if m:
                for s_ in structs:
                    if int(s_.get("index", -1)) == int(m.group(1)):
                        return s_["event_id"]
            low = eid.lower()
            for s_ in structs:
                if low in {str(s_.get("source_id", "")).lower(), str(s_.get("label", "")).lower()} | {str(a).lower() for a in s_.get("aliases", []) or []}:
                    return s_["event_id"]
            return eid

        def cnt(e):
            oc, rc = e.get("observed_count"), req.get(e.get("event_id"))
            try:
                return "yes" if int(oc) == int(rc) else "no"
            except (TypeError, ValueError):
                return ""
        out = {}
        for ax in AXES:
            axis = AXIS_FULL[ax]
            r = parsed.get(axis, {}) or {}
            if ax == "TCR":
                out[ax] = dict(labels={"__item__": str(r.get("label", "")).lower()}, reasons={"__item__": str(r.get("reason", ""))},
                               stage1={"__item__": str(s1.get(ax, [{}])[0].get("label", "")).lower()} if s1.get(ax) else {})
            elif ax == "TCC":
                pe = [dict(e, event_id=canon(e)) for e in (r.get("per_event", []) or []) if "event_id" in e]
                out[ax] = dict(labels={e["event_id"]: cnt(e) for e in pe},
                               reasons={e["event_id"]: str(e.get("reason", "")) for e in pe},
                               stage1={e["event_id"]: cnt(e) for e in s1.get(ax, []) if "event_id" in e})
            else:
                flag = FLAG[ax]
                ax_structs = [s_ for s_ in structs if flag is None or s_.get(flag)]
                try:
                    pe = NE.normalize_label_per_event(r, ax_structs, axis)        # same id normalisation as the per-axis pipeline
                except Exception as ex:
                    self.log(f"[orch] normalize failed for {ax} ({ex}); using raw ids")
                    pe = [dict(e, event_id=canon(e)) for e in (r.get("per_event", []) or []) if "event_id" in e]
                out[ax] = dict(labels={e["event_id"]: str(e.get("label", "")).lower() for e in pe if "event_id" in e},
                               reasons={e["event_id"]: str(e.get("reason", "")) for e in pe if "event_id" in e},
                               stage1={e["event_id"]: str(e.get("label", "")).lower() for e in s1.get(ax, []) if "event_id" in e})
        return out

    def run_item(self, src, iid, rules):
        sha = hashlib.sha1(rules.encode()).hexdigest()[:12]
        d = self.run_dir / "cache_orch" / sha; d.mkdir(parents=True, exist_ok=True)
        p = d / (re.sub(r"[^A-Za-z0-9_.|-]", "_", f"{src}|{iid}") + ".json")
        if p.exists():
            return json.load(open(p))
        for attempt in range(3):
            try:
                out = self.judge_item(src, iid, rules)
                json.dump(out, open(p, "w"))
                with self._lock:
                    self.n_calls += 1
                return out
            except Exception as e:
                self.log(f"[orch] {src}|{iid} attempt {attempt + 1} failed: {e}")
                time.sleep(5 * (attempt + 1))
        self.log(traceback.format_exc())
        return None


# ---------------------------------------------------------------- GEPA adapter: one data instance = one video (all its axis rows)
def group_rows(rows):
    """manifest rows -> [{"uid": "src|item", "source", "item_id", "rows": [row, ...]}], one per video."""
    by = defaultdict(list)
    for r in rows:
        by[(r["source"], r["item_id"])].append(r)
    return [dict(uid=f"{s}|{i}", source=s, item_id=i, rows=rs) for (s, i), rs in sorted(by.items())]


class OrchAdapter(Orchestrator):
    """GEPA adapter over grouped items: score = mean of the item's axis-row scores; feedback lists every axis."""

    def _row_out(self, out, row):
        o = (out or {}).get(row["axis"]) or {"labels": {}, "reasons": {}, "stage1": {}}
        return dict(labels=o["labels"], reasons=o.get("reasons", {}), stage1=o["stage1"], stage1_reasons={}, s1src="orch", raw="")

    def _one_item(self, it, rules):
        out = self.run_item(it["source"], it["item_id"], rules)
        per_rows, scores = [], []
        for row in it["rows"]:
            ro = self._row_out(out, row)
            sc, per = self.score_row(row, ro)
            scores.append(sc); per_rows.append((row, ro, per, sc))
        score = sum(scores) / len(scores) if scores else 0.0
        return dict(uid=it["uid"], score=score, rows=per_rows, error=(out is None))

    def evaluate(self, batch, candidate, capture_traces=False):
        from adapter import COMPONENT
        rules = candidate[COMPONENT]
        bad = self._violation(rules)
        if bad:
            outs = [dict(uid=it["uid"], score=0.0, violation=bad) for it in batch]
            return EvaluationBatch(outputs=outs, scores=[0.0] * len(batch), trajectories=outs if capture_traces else None)
        with ThreadPoolExecutor(self.workers) as ex:
            recs = list(ex.map(lambda it: self._one_item(it, rules), batch))
        scores = [r["score"] for r in recs]
        self.log(f"[orch-adapter] batch {len(batch)} items mean {sum(scores) / max(len(scores), 1):.3f}  (calls so far {self.n_calls})")
        return EvaluationBatch(outputs=recs, scores=scores, trajectories=recs if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        from adapter import COMPONENT
        items = []
        for rec in (eval_batch.trajectories or eval_batch.outputs):
            if rec.get("error"):
                continue
            if "violation" in rec:
                items.append({"Inputs": "candidate rule block", "Generated Outputs": "(not run)", "Feedback": rec["violation"]}); continue
            fb, s1, s2 = [], {}, {}
            for row, ro, per, sc in rec["rows"]:
                fb.append(self.feedback(row, ro, {k: tuple(v) for k, v in per.items()}, sc))
                s1[row["axis"]] = ro["stage1"]; s2[row["axis"]] = ro["labels"]
            items.append({"Inputs": f"stage-1 labels per axis: {s1}", "Generated Outputs": f"stage-2 labels per axis: {s2}",
                          "Feedback": "\n".join(fb)})
        return {COMPONENT: items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True); ap.add_argument("--manifest", required=True)
    ap.add_argument("--rules", required=True); ap.add_argument("--tag", required=True); ap.add_argument("--run-dir", required=True)
    ap.add_argument("--workers", type=int, default=4); ap.add_argument("--judge-model", default="gemini-3.1-pro-preview")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.manifest)]
    rules = Path(a.rules).read_text()
    if BANNED.search(rules):
        print(f"[orch] warning: rules mention '{BANNED.search(rules).group(0)}'", flush=True)
    by_item = defaultdict(list)
    for r in rows:
        by_item[(r["source"], r["item_id"])].append(r)
    items = sorted(by_item)
    if a.limit:
        items = items[: a.limit]
    print(f"[orch] {len(rows)} rows -> {len(items)} items, one call each", flush=True)

    orch = Orchestrator(json.load(open(a.sources)), a.run_dir, model=a.judge_model, workers=a.workers,
                        max_chars=10 ** 6, log=lambda s: print(s, flush=True))
    with ThreadPoolExecutor(a.workers) as ex:
        outs = list(ex.map(lambda k: (k, orch.run_item(k[0], k[1], rules)), items))

    recs = []
    for (src, iid), out in outs:
        for row in by_item[(src, iid)]:
            ax = row["axis"]
            o = (out or {}).get(ax, {"labels": {}, "stage1": {}})
            gt = row["gt"]
            if "__item__" in gt:
                if "__item__" in o["labels"]:
                    pred = o["labels"]["__item__"]; s1 = o["stage1"].get("__item__", "")
                else:
                    labs = [l for l in o["labels"].values() if l in ("yes", "no")]
                    pred = "no" if "no" in labs else ("yes" if labs else "")
                    l1 = [l for l in o["stage1"].values() if l in ("yes", "no")]
                    s1 = "no" if "no" in l1 else ("yes" if l1 else "")
                recs.append(dict(uid=row["uid"], source=src, item_id=iid, axis=ax, variant=row["variant"], eval_only=row["eval_only"],
                                 event_id="__item__", gt=gt["__item__"], stage1=s1, pred=pred, tag=a.tag))
            else:
                for e, g in gt.items():
                    recs.append(dict(uid=row["uid"], source=src, item_id=iid, axis=ax, variant=row["variant"], eval_only=row["eval_only"],
                                     event_id=e, gt=g, stage1=o["stage1"].get(e, ""), pred=o["labels"].get(e, ""), tag=a.tag))
    df = pd.DataFrame(recs)
    out = Path(a.run_dir) / f"heldout_test_{a.tag}.csv"
    df.to_csv(out, index=False)
    ok = (df.pred == df["gt"])
    print(f"[orch] {len(df)} events, overall acc {ok.mean():.3f}; calls {orch.n_calls} -> {out}")
    print(df.assign(ok=ok).groupby(["source", "axis"]).ok.mean().round(3).to_string())


if __name__ == "__main__":
    main()
