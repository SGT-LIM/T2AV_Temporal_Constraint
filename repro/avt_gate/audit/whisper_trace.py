#!/usr/bin/env python3
"""Trace the Whisper (A speech) path of the reported runs from cached outputs. No API / GPU call; writes only $T2AV_OUT_DIR/<tag>.

For every scored A-speech unit of LTX and unified MOVA it rebuilds the original-gate A text exactly as the experiment did
(gen_stage2_1030.a_text / a_parts; section6_1106.a_gate) and records:
  opened (row level), why it opened (target word heard in the clip / FLAM line below T_flam / both), whether the request contains the
  Whisper transcript, which call set answered it (always-shown set when the gated text equals the full text, else the gated set),
  the event's own target-word presence, the AVT-Judge (= original-gate) label and the Gate-only label.
It checks the rebuilt openings against the stored ones and, for the example units, that the cached Stage-2 record's user-prompt md5
equals the md5 of the rebuilt request (so the quoted observation text is the text that was sent).
  python repro/avt_gate/audit/whisper_trace.py --tag whisper_trace
"""
import argparse, hashlib, json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "evaluation/ablation/gepa_stage2"), str(REPO / "evaluation/ablation"), str(REPO / "repro/avt_gate/analysis")]
sys.path.append(str(REPO))

SRC = {"220 LTX": "g220ltx", "220 MOVA": "g220mova", "149 LTX": "g149", "2k_25 LTX": "g2k25", "MOVA390": "m390"}
S2AV = {"220 LTX": "G4", "220 MOVA": "G4", "149 LTX": "G4", "2k_25 LTX": "K4", "MOVA390": "M4"}
A5 = {"220 LTX": "G5", "220 MOVA": "G5", "149 LTX": "G5", "2k_25 LTX": "K5", "MOVA390": "M5"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="whisper_trace"); a = ap.parse_args()
    import t2av_paths as tp
    out = tp.out_dir(a.tag)
    if out.exists():
        sys.exit(f"{out} exists")
    out.mkdir(parents=True)
    import pandas as pd
    import final_benchmark_1108 as FB, sanjoy_controls as SC
    M = FB.setup(); G, AU, O = M["G"], M["AU"], M["O"]
    U = pd.read_csv(FB.OUT / "unit_results_final.csv", low_memory=False)
    U = U[(U.axis == "A") & (U.family == "A speech") & U.scored_row1 & U.dataset.isin(list(SRC))].copy()
    IT = FB.items_all()
    rows, cache = [], {}
    for r in U.itertuples():
        src = SRC[r.dataset]
        if (src, r.item) not in cache:
            wtxt, fl, present = G.a_parts(src, r.item)
            g5, g4 = G.a_text(src, r.item, gated=True), G.a_text(src, r.item)
            cache[(src, r.item)] = (wtxt, fl, present, g5, g4)
        wtxt, fl, present, g5, g4 = cache[(src, r.item)]
        e = IT[FB.PSET[r.dataset]][r.item]["events"][int(r.event.split("_")[1]) - 1]
        segs = [s for s in (G.evidence(src, r.item) or {}).get("whisper", {}).get("segments", []) if s["no_speech_prob"] < 0.5]
        heard_gate_tok = bool(set(G.norm(e.get("text", ""))) & {w for s in segs for w in G.norm(s["text"])})
        heard_gateonly_tok = bool(set(SC.norm(e.get("text", ""))) & {w for s in segs for w in SC.norm(s["text"])})
        op, same = bool(g5), bool(g5) and g5 == g4
        flam_below = sum(1 for _, _, b in fl.values() if b)
        req_text = (g4 if same else g5) if op else ""
        rows.append(dict(group="LTX" if "LTX" in r.dataset else "MOVA", dataset=r.dataset, item=r.item, event=r.event, target_word=e.get("text", ""),
                         gt=r.gt, initial=r.initial, opened_rebuilt=op, opened_stored=bool(r.orig_opened),
                         why_open=("word heard + FLAM below T" if (present and flam_below) else "target word heard (any speech event of the clip)" if present
                                   else "FLAM below T for a sounding event only" if flam_below else "-") if op else "closed",
                         call_set=(S2AV[r.dataset] if same else A5[r.dataset]) if op else "", transcript_in_request="Whisper (speech recognizer)" in req_text,
                         flam_lines_in_request=req_text.count("FLAM (open-vocabulary"), event_word_heard=heard_gate_tok, event_word_heard_gateonly_tokenizer=heard_gateonly_tok,
                         avt_judge=r.original_gate, avt_judge_revised=(r.original_gate != r.initial) if isinstance(r.original_gate, str) else None,
                         gate_only=r.direct_comb if "direct_comb" in U.columns else None, request_text=req_text))
    R = pd.DataFrame(rows)
    S = pd.read_csv(FB.RUNS / "../../../../eval_results/analysis/sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv" if False else
                    Path(tp.WORKSPACE) / "eval_results/analysis/sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv", low_memory=False).set_index(["dataset", "unit"])
    R["gate_only"] = [S.direct_comb.get((d, f"{i}|A|{e}")) for d, i, e in zip(R.dataset, R["item"], R.event)]
    R["gate_only_revised"] = R.gate_only != R.initial
    R.drop(columns=["request_text"]).to_csv(out / "speech_units.csv", index=False)
    summ = []
    for (g, ini), q in R.groupby(["group", "initial"]):
        o = q[q.opened_rebuilt]
        summ.append(dict(group=g, initial=ini, units=len(q), opened=len(o), opened_with_transcript=int(o.transcript_in_request.sum()),
                         opened_without_transcript=int((~o.transcript_in_request).sum()), opened_because_flam_only=int((o.why_open == "FLAM below T for a sounding event only").sum()),
                         event_word_heard=int(q.event_word_heard.sum()), opened_but_event_word_not_heard=int((o.event_word_heard == False).sum()),
                         avt_judge_revised=int(q.avt_judge_revised.sum()), avt_judge_revised_correct=int((q.avt_judge_revised & (q.avt_judge == q["gt"])).sum()),
                         gate_only_revised=int(q.gate_only_revised.sum()), gate_only_revised_correct=int((q.gate_only_revised & (q.gate_only == q["gt"])).sum())))
    Sm = pd.DataFrame(summ); Sm.to_csv(out / "summary_by_group_initial.csv", index=False)
    chk = dict(opened_rebuilt_vs_stored=f"{int((R.opened_rebuilt == R.opened_stored).sum())} / {len(R)}",
               tokenizer_mismatch_units=int((R.event_word_heard != R.event_word_heard_gateonly_tokenizer).sum()))
    # examples with the request text, verified against the cached record md5
    ex = []
    pick = [("initial PASS, transcript sent, judge revised to FAIL", (R.initial == "yes") & R.transcript_in_request & R.avt_judge_revised),
            ("initial FAIL, transcript sent, judge revised to PASS", (R.initial == "no") & R.transcript_in_request & R.avt_judge_revised),
            ("opened by a FLAM line only (no transcript), speech label revised", (R.why_open == "FLAM below T for a sounding event only") & R.avt_judge_revised),
            ("opened by another speech event's word; this event's word not heard", R.opened_rebuilt & R.transcript_in_request & ~R.event_word_heard),
            ("initial PASS, transcript sent, judge kept PASS", (R.initial == "yes") & R.transcript_in_request & ~R.avt_judge_revised)]
    for name, m in pick:
        for r in R[m].head(2).itertuples():
            src = SRC[r.dataset]; uid = f"{src}|{r.item}|A"
            row = dict(set=r.call_set, source=src, uid=uid, item_id=r.item, axis="A", variant="", gt={}, clip=r.item, cond="gen_tool_text", obs={"text": r.request_text})
            cc = O.build_call(row); md5 = hashlib.md5(cc["user"].encode()).hexdigest() if cc else ""
            rec = AU.stage2_rec(r.call_set, uid)
            out_ev = next((e for e in ((rec or {}).get("parsed") or {}).get("per_event", []) if e.get("event_id") == r.event), {})
            ex.append(dict(case=name, dataset=r.dataset, item=r.item, event=r.event, target_word=r.target_word, gt=r.gt, initial=r.initial, call_set=r.call_set,
                           cached_record=f"calls/gen_tool_text/{r.call_set}__{uid}.json (or its substitution)", cached_user_md5=(rec or {}).get("user_md5"),
                           rebuilt_user_md5=md5, request_matches_cache=bool(rec and rec.get("user_md5") == md5),
                           observation_text=r.request_text, judge_label=r.avt_judge, judge_reason=str(out_ev.get("reason", ""))[:400], gate_only=r.gate_only))
    pd.DataFrame(ex).to_csv(out / "examples.csv", index=False)
    json.dump(dict(checks=chk, summary=summ, n_examples=len(ex), examples_request_match=sum(e["request_matches_cache"] for e in ex)),
              open(out / "summary.json", "w"), indent=1, default=str)
    print(json.dumps(chk, indent=1)); print(Sm.to_string(index=False))
    print(pd.DataFrame(ex)[["case", "dataset", "item", "event", "initial", "judge_label", "gt", "request_matches_cache"]].to_string(index=False))


if __name__ == "__main__":
    main()
