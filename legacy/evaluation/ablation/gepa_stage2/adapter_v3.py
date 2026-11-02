#!/usr/bin/env python3
"""GEPA v3 adapter (2026-10-26): multi-agent stage 2 (anchor + evidence), one KEEP/REVISE paragraph PER AXIS.

Structure (status/decisions_2026-10-26_gepa_v3.md):
  * candidate = 5 components {rules_A, rules_V, rules_AVB, rules_TCR, rules_TCC}; the pipeline stays multi-agent: each axis
    is its own stage-2 call (video + stage-1 label of that axis + routed tool evidence + THAT axis' paragraph).
  * one GEPA data instance = one video unit (source, item_id) = all its (item, axis) GT rows. Minibatch = units.
  * score = class-balanced: each row weighs 1 / (n_axes * 2 * n_rows of its (axis, class) in that split), times n_units,
    so the mean over units = mean over axes of balanced accuracy. "Always yes" scores 0.5 per axis.
  * reflection for component rules_X sees only axis-X rows of the minibatch, each with: stage-1 label -> stage-2 label,
    correct answer, reasons, AND a short summary of the tool evidence that call received (FLAM per query: score /
    detections / NOT QUERIED, Whisper speech yes/no + words, caption mentions of the event words), plus the other axes'
    verdicts of the same video as context.
  * no gating inside GEPA (rows already exist only where the GT/parents allow it).

sources_v3.json: {src: {"prompt_json", "outputs_dirs": [...], "stage1": [dir/csv, ...], "caption_json" | null,
                        "flam_ckpt", "flam_hop_sec": 5 | 0, "audio": "whisper_flam" | "none"}}
"""
import hashlib, json, re, sys, threading, time, traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE
import agentic_common as AC
import run_two_stage as TS
from run_agentic_eval import build_arg_parser
from adapter import Stage2Adapter, AXIS_FULL, BANNED

try:
    from gepa.core.adapter import EvaluationBatch
except Exception:
    from gepa import EvaluationBatch

AXES = ("A", "V", "AVB", "TCR", "TCC")
COMP = {ax: f"rules_{ax}" for ax in AXES}
AX_OF = {v: k for k, v in COMP.items()}
EVIDENCE_OF = {"A": ("audio",), "V": ("caption",), "AVB": ("audio", "caption"), "TCR": ("audio", "caption"), "TCC": ("audio", "caption")}
STOP = set("the a an of to with and or in on at from into onto for by up down off out over is are be".split())


# ---------------------------------------------------------------- data
def load_units(path):
    """jsonl rows -> list of units {uid, source, item_id, rows: [...]}, order kept."""
    units = {}
    for l in open(path):
        r = json.loads(l)
        k = f"{r['source']}|{r['item_id']}"
        units.setdefault(k, dict(uid=k, source=r["source"], item_id=r["item_id"], rows=[]))["rows"].append(r)
    return list(units.values())


def is_fail(row):
    return "no" in row["gt"].values()


def set_weights(units, axes=AXES):
    """row['w'] so that mean over units of unit_score = mean over present axes of balanced acc."""
    cnt = Counter((r["axis"], is_fail(r)) for u in units for r in u["rows"])
    present = [ax for ax in axes if cnt[(ax, True)] + cnt[(ax, False)] > 0]
    n_units = len(units)
    for u in units:
        for r in u["rows"]:
            n_cls = cnt[(r["axis"], is_fail(r))]
            both = cnt[(r["axis"], True)] > 0 and cnt[(r["axis"], False)] > 0
            r["w"] = n_units / (len(present) * (2 if both else 1) * n_cls)
    return {f"{ax}_{'FAIL' if f else 'PASS'}": c for (ax, f), c in sorted(cnt.items())}


# ---------------------------------------------------------------- evidence summary (what the call saw)
def parse_flam(section):
    """{query: dict(max=, dets=[(s,e,peak,score)])} from the OpenFLAM part of the audio evidence text."""
    out, cur = {}, None
    j = section.find("OpenFLAM")
    for line in section[j:].splitlines() if j >= 0 else []:
        m = re.match(r"\s*Query:\s*['\"](.+?)['\"]\s*\(max_score=([\d.]+)", line)
        if m:
            cur = m.group(1); out[cur] = dict(max=float(m.group(2)), dets=[]); continue
        m = re.match(r"\s*\[\s*([\d.]+)\s*-\s*([\d.]+)\]\s*peak@([\d.]+)s\s*score=([\d.]+)", line)
        if m and cur:
            out[cur]["dets"].append(tuple(float(x) for x in m.groups()))
    return out


def parse_whisper(section):
    sp = re.search(r"has_speech[^:]*:\s*(True|False)", section)
    words = re.findall(r"\]\s*\"?([^\n\"]{1,80})\"?", section[section.find("Segments:"):section.find("OpenFLAM")] if "Segments:" in section else "")
    return (sp.group(1) == "True") if sp else None, " ".join(w.strip() for w in words)[:120]


def caption_text(section):
    j = section.find("Dense caption:")
    return section[j + len("Dense caption:"):].strip().lower() if j >= 0 else ""


def content_words(label):
    return [w for w in re.findall(r"[a-z]+", str(label).lower()) if len(w) > 2 and w not in STOP]


def evidence_lines(ctx, axis, structs):
    """one line per event: the evidence this axis call received for it."""
    ev = getattr(ctx, "evidence", {}) or {}
    audio, cap = str(ev.get("audio", "") or ""), caption_text(str(ev.get("caption", "") or ""))
    flam = parse_flam(audio) if "audio" in EVIDENCE_OF[axis] else {}
    speech, words = parse_whisper(audio) if ("audio" in EVIDENCE_OF[axis] and audio) else (None, "")
    lines = {}
    for s in structs:
        parts, lab, kind = [], str(s.get("label", "")), s.get("kind")
        if "audio" in EVIDENCE_OF[axis]:
            if not audio:
                parts.append("audio tools: none attached")
            elif kind == "speech":
                parts.append(f"Whisper: speech={'yes' if speech else 'no'}" + (f" '{words[:60]}'" if words else ""))
            elif kind == "sounding_action":
                q = next((k for k in flam if lab.lower() in k.lower() or k.lower() in lab.lower()), None)
                if q is None:
                    parts.append("FLAM: NOT QUERIED for this sound")
                else:
                    f = flam[q]
                    d = "; ".join(f"{a:.1f}-{b:.1f}s" for a, b, _, _ in f["dets"][:3]) or "no detection above threshold"
                    parts.append(f"FLAM '{q}': max {f['max']:.2f}, {d}")
        if "caption" in EVIDENCE_OF[axis]:
            if not cap:
                parts.append("caption: none attached")
            else:
                cw = content_words(lab)
                hit = [w for w in cw if w in cap]
                parts.append(f"caption mentions {len(hit)}/{len(cw)} event words" + (f" {hit}" if hit else f" (none of {cw})"))
        lines[s["event_id"]] = " | ".join(parts) if parts else "(no tool evidence for this axis)"
    return lines


# ---------------------------------------------------------------- adapter
class V3Adapter(Stage2Adapter):
    def __init__(self, sources, run_dir, max_chars=None, **kw):
        self._cap = max_chars or int(len(TS.SEED_RULES) * 3)
        super().__init__(sources, run_dir, max_chars=self._cap, **kw)
        self._units_by_uid = {}

    def _prepare_source(self, src, cfg):
        argv = ["--prompt-json", cfg["prompt_json"], "--outputs-dir", cfg["outputs_dirs"][0],
                "--output-csv", str(self.run_dir / f"_unused_{src}.csv"), "--model", self.model, "--thinking-level", self.thinking,
                "--axes", "all", "--pose-evidence-mode", "none", "--media-input-mode", cfg.get("media", "video")]
        if cfg.get("audio", "whisper_flam") == "none":
            argv += ["--audio-evidence-mode", "none"]
        else:
            argv += ["--audio-evidence-mode", "whisper_flam", "--flam-ckpt-path", cfg["flam_ckpt"],
                     "--flam-hop-sec", str(cfg.get("flam_hop_sec", 0))]
        if cfg.get("caption_json"):
            argv += ["--caption-evidence-mode", "external", "--caption-style", "plain", "--caption-external-json", cfg["caption_json"]]
        else:
            argv += ["--caption-evidence-mode", "none"]
        pargs = build_arg_parser().parse_args(argv)
        if getattr(pargs, "focus_planner_model", None) is None:
            pargs.focus_planner_model = pargs.model
        items = NE.load_prompt_items(Path(cfg["prompt_json"]))
        metas = NE.build_item_meta_map(items, modality_filter=None, item_overrides=None, relative_only=False)
        vids = {}
        for d in cfg["outputs_dirs"]:
            for p in NE.find_video_files(Path(d)):
                vids.setdefault(NE.infer_item_id_from_path(p), p)
        s1 = cfg["stage1"] if isinstance(cfg["stage1"], list) else [cfg["stage1"]]
        import pandas as pd
        df = pd.concat([TS.load_stage1(x) for x in s1])
        self._pargs[src], self._metas[src], self._vids[src] = pargs, metas, vids
        self._stage1[src] = df[~df.index.duplicated(keep="last")]
        self.log(f"[v3] {src}: {len(metas)} items, {len(vids)} clips, stage-1 {len(self._stage1[src])} rows, "
                 f"audio={cfg.get('audio', 'whisper_flam')} hop={cfg.get('flam_hop_sec', 0)} caption={'yes' if cfg.get('caption_json') else 'no'}")

    # ---- one (item, axis) stage-2 call with that axis' paragraph, plus the evidence summary
    def judge_row(self, row, rules):
        out = self.judge(row, rules)
        ctx = self._context(row["source"], row["item_id"])
        structs = NE.build_scoring_events(self._metas[row["source"]][row["item_id"]])
        ids = set(out["labels"]) | set(e for e in row["gt"] if e != "__item__")
        out["evidence"] = evidence_lines(ctx, row["axis"], [s for s in structs if s["event_id"] in ids or not ids])
        out["event_names"] = {s["event_id"]: str(s.get("label", "")) for s in structs}
        return out

    def _cache_path(self, rules, uid):
        sha = hashlib.sha1(rules.encode()).hexdigest()[:12]
        d = self.run_dir / "cache" / sha
        d.mkdir(parents=True, exist_ok=True)
        return d / (re.sub(r"[^A-Za-z0-9_.|-]", "_", uid) + ".json")

    def _one_row(self, row, rules):
        p = self._cache_path(rules, row["uid"])
        if p.exists():
            return json.load(open(p))
        for attempt in range(3):
            try:
                out = self.judge_row(row, rules); break
            except Exception as e:
                self.log(f"[v3] {row['uid']} attempt {attempt + 1} failed: {e}")
                time.sleep(5 * (attempt + 1))
        else:
            out = dict(labels={}, reasons={}, stage1={}, stage1_reasons={}, s1src="error", raw=traceback.format_exc())
        score, per = self.score_row(row, out)
        rec = dict(uid=row["uid"], axis=row["axis"], score=score, per=per, out={k: v for k, v in out.items() if k != "raw"})
        if out["s1src"] == "error":
            rec["error"] = str(out["raw"])[-500:]
        else:
            json.dump(rec, open(p, "w"))
        with self._lock:
            self.n_calls += 1
        return rec

    def _violation_all(self, cand):
        for ax in AXES:
            r = cand[COMP[ax]]
            if len(r) > self._cap:
                return ax, f"rules for axis {ax} too long: {len(r)} chars > {self._cap}"
            m = BANNED.search(r)
            if m:
                return ax, f"rules for axis {ax} name a dataset / regime / item ('{m.group(0)}'); rules must be generic"
        return None, None

    def evaluate(self, batch, candidate, capture_traces=False):
        for u in batch:
            self._units_by_uid[u["uid"]] = u
        ax_bad, bad = self._violation_all(candidate)
        if bad:
            outs = [dict(uid=u["uid"], score=0.0, rows=[], violation=bad, violation_axis=ax_bad) for u in batch]
            return EvaluationBatch(outputs=outs, scores=[0.0] * len(batch), trajectories=outs if capture_traces else None)
        jobs = [(u, r) for u in batch for r in u["rows"]]
        with ThreadPoolExecutor(self.workers) as ex:
            recs = list(ex.map(lambda ur: self._one_row(ur[1], candidate[COMP[ur[1]["axis"]]]), jobs))
        by_unit = defaultdict(list)
        for (u, r), rec in zip(jobs, recs):
            rec["w"] = r.get("w", 1.0)
            by_unit[u["uid"]].append(rec)
        outs, scores = [], []
        for u in batch:
            rs = by_unit[u["uid"]]
            s = sum(x["w"] * x["score"] for x in rs if "error" not in x)
            outs.append(dict(uid=u["uid"], score=s, rows=rs)); scores.append(s)
        self.log(f"[v3] batch {len(batch)} units / {len(jobs)} rows, mean {sum(scores) / max(len(scores), 1):.3f} (judge calls so far {self.n_calls})")
        return EvaluationBatch(outputs=outs, scores=scores, trajectories=outs if capture_traces else None)

    # ---- reflection data: per component, the rows of that axis with evidence + same-video context
    def row_feedback(self, rec):
        out, per, ax = rec["out"], {k: tuple(v) for k, v in rec["per"].items()}, rec["axis"]
        names, evl = out.get("event_names", {}), out.get("evidence", {})
        lines = []
        if "__item__" in per:
            p, g = per["__item__"]
            for e, lab in out["labels"].items():
                s1 = out["stage1"].get(e, "?")
                lines.append(f"- {e} '{names.get(e, '')}': stage1={s1} -> stage2={lab} ({'kept' if lab == s1 else 'revised'})")
                lines.append(f"    evidence given: {evl.get(e, '?')}")
                lines.append(f"    stage-2 reason: {out['reasons'].get(e, '')[:200]}")
            lines.append(f"- clip verdict {p}; correct {g} -> {'correct' if p == g else 'WRONG'}")
            return "\n".join(lines)
        for e, (p, g) in per.items():
            s1 = out["stage1"].get(e, "?")
            tag = "correct" if p == g else "WRONG"
            lines.append(f"- {e} '{names.get(e, '')}': stage1={s1} -> stage2={p} ({'kept' if p == s1 else 'revised'}); correct={g} -> {tag}")
            lines.append(f"    evidence given: {evl.get(e, '?')}")
            lines.append(f"    stage-2 reason: {out['reasons'].get(e, '')[:200].replace(chr(10), ' ')}")
            if p != g and s1 == g:
                lines.append("    -> stage 1 was right; this revision was a mistake.")
            elif p != g:
                lines.append("    -> stage 1 was wrong and was kept.")
        return "\n".join(lines)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        data = {c: [] for c in COMP.values()}       # all axes: the proposer may switch to another axis if the target has none
        for urec in (eval_batch.trajectories or eval_batch.outputs):
            if "violation" in urec:
                c = COMP.get(urec.get("violation_axis"))
                if c in data:
                    data[c].append({"Inputs": "rule paragraph", "Generated Outputs": "(not run)", "Feedback": urec["violation"]})
                continue
            ctx_line = "other axes on this video: " + ", ".join(
                f"{r['axis']} {'ok' if r['score'] >= 0.999 else 'wrong'}" for r in urec["rows"] if "error" not in r)
            for r in urec["rows"]:
                c = COMP[r["axis"]]
                if c not in data or "error" in r:
                    continue
                data[c].append({"Inputs": f"video {urec['uid'].split('|', 1)[0]} clip; {ctx_line}",
                                "Generated Outputs": f"stage-2 labels: {r['out']['labels']}",
                                "Feedback": f"axis {r['axis']} score {r['score']:.2f}\n" + self.row_feedback(r),
                                "wrong": r["score"] < 0.999})
        return data


AXIS_NAME = {"A": "audio event correctness (is each required sound / speech audible)",
             "V": "visual event correctness (is each required action visible as described)",
             "AVB": "audio-visual binding (does each sound line up in time with its visible action)",
             "TCR": "temporal relation (do the events happen in the required order)",
             "TCC": "temporal count (does each event happen the required number of times)"}

REFLECTION_TEMPLATE = """You are improving ONE paragraph of a fixed evaluation prompt used by a video judge.
The judge works per axis. For the axis "{axis_name}" it first labels each event from the video and audio alone (stage 1).
In a second call it sees the video again, the stage-1 label, and text evidence from tools (a speech transcript, sound
detections with scores and timestamps, a dense caption), and outputs the final label. The paragraph you are editing is the
KEEP / REVISE policy for THIS AXIS ONLY: when the stage-1 label should stand and when the tool evidence justifies changing it.
The other axes have their own paragraphs.

Current paragraph:
<<<
{current}
>>>

Examples from recent videos. Each shows the stage-1 and final label, the correct answer, the evidence the judge was given
for that event (e.g. whether the sound detector was even asked about that sound, its score, whether the caption mentions
the event's words), and the judge's reason.
<<<
{examples}
>>>

Write a new paragraph that would make more of these answers correct. Think about WHICH evidence is reliable for this axis
and under WHICH conditions it should override stage 1, and when evidence is missing rather than negative.
Constraints:
- Output ONLY the paragraph, nothing else. At most {max_chars} characters.
- Keep it general: do not mention any specific object, action, word, sound name, timestamp, video, person, dataset,
  camera style, or whether a video is real or generated. Do not quote the examples or write parenthetical examples.
- Do not restate the task; only the KEEP / REVISE policy for this axis.
- Keep the instruction that each reason starts with "KEEP:" or "REVISE:".
"""


def make_propose_new_texts(reflection_lm, max_chars, log=print):
    def propose(candidate, reflective_dataset, components_to_update):
        out = {}
        for target in components_to_update:
            out[target] = candidate[target]
            comp = target
            if not reflective_dataset.get(comp):
                # target axis absent from this minibatch: edit the axis with the most wrong rows instead
                wrong = {c: sum(1 for d in v if d.get("wrong")) for c, v in reflective_dataset.items() if v}
                if not wrong:
                    log(f"[reflect] {target}: no examples for any axis, kept"); continue
                comp = max(wrong, key=lambda c: (wrong[c], len(reflective_dataset[c])))
                log(f"[reflect] {target}: no examples, switching to {comp} ({wrong[comp]} wrong of {len(reflective_dataset[comp])})")
            ax = AX_OF[comp]
            ex = reflective_dataset[comp]
            ex_txt = "\n\n".join(f"[{i + 1}] {d['Inputs']}\n{d['Generated Outputs']}\n{d['Feedback']}" for i, d in enumerate(ex))
            prompt = REFLECTION_TEMPLATE.format(axis_name=AXIS_NAME[ax], current=candidate[comp].strip(), examples=ex_txt,
                                                max_chars=max_chars)
            txt = reflection_lm(prompt).strip()
            txt = re.sub(r"^```[a-z]*\n|\n```$", "", txt).strip()
            if not txt:
                log(f"[reflect] {comp}: empty reflection output, kept"); continue
            log(f"[reflect] {comp}: proposed {len(txt)} chars from {len(ex)} examples")
            out[comp] = "\n" + txt
        return out
    return propose
