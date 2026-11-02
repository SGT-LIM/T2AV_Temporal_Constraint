#!/usr/bin/env python3
"""Tool-only diagnostics for sets B30 / C30 / C30T (10/30). No judge calls.
  (1) Synchformer offsets / probabilities by variant; sweep of the no-judge rule
      "REVISE to FAIL only if |offset| >= T and p >= P" applied to today's anchor verdicts (rows scored as in the B30 table).
  (2) TCR: does Qwen's first-occurrence order of the prompt's actions agree with the prompt's ordered_events?
  (3) TCC: Qwen occurrence count vs the true count (movement tracks) per action and per item.
  python gepa_stage2/tool_diag_1030.py      # prints markdown tables; writes runs/obsval_1028/tool_diag_1030_*.csv
"""
import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
L = _pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "runs/obsval_1028"
EV = Path("/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval")
QW = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/qwen_timestamps_1030")
SY = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_1030")
spec = importlib.util.spec_from_file_location("parse_qwen", QW / "qwen_timestamps_share/parse_qwen.py")
PQ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PQ)
VAR = {"audio_shift_early": "shift_early", "audio_shift_late": "shift_late", "original": "original"}


def md(df, floatfmt="{:.2f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def synch(pe=None):
    pe = pd.read_csv(SY / "per_event.csv") if pe is None else pe
    pe["var"] = pe.variant.map(VAR)
    ok = pe[pe.status == "ok"]
    q = ok.groupby("var").agg(n_events=("offset", "size"),
                              off_q10=("offset", lambda s: s.quantile(.1)), off_q25=("offset", lambda s: s.quantile(.25)),
                              off_med=("offset", "median"), off_q75=("offset", lambda s: s.quantile(.75)), off_q90=("offset", lambda s: s.quantile(.9)),
                              p_q25=("prob", lambda s: s.quantile(.25)), p_med=("prob", "median"), p_q75=("prob", lambda s: s.quantile(.75)),
                              p0_med=("p_offset0", "median")).reindex(["shift_early", "shift_late", "original"]).reset_index()
    nospan = pe[pe.status != "ok"].groupby("var").size().reindex(["shift_early", "shift_late", "original"]).fillna(0).astype(int)
    q.insert(2, "no_reading", nospan.values)
    bins = np.arange(-2.25, 2.26, 0.5)
    lab = [f"{(a + b) / 2:+.1f}" for a, b in zip(bins[:-1], bins[1:])]
    ok = ok.assign(bin=pd.cut(ok.offset, bins, labels=lab))
    h = ok.groupby(["var", "bin"], observed=False).size().unstack(fill_value=0).reindex(["shift_early", "shift_late", "original"]).reset_index()
    # rule sweep on the scored B30 rows (anchor_1030 verdicts)
    rows = pd.read_csv(L / "scores_rows.csv")
    a = rows[(rows["set"] == "B30") & (rows.cond == "anchor") & rows.pred.isin(["yes", "no"])][["uid", "variant", "y", "pred"]]
    a["item_id"] = a.uid.str.split("|").str[1]
    ev = pe.groupby("item_id")
    sw = []
    for T in (0.5, 1.0, 1.5, 2.0):
        for P in (0.3, 0.5, 0.7):
            def fire(iid):
                if iid not in ev.groups:
                    return False
                g = ev.get_group(iid)
                return bool(((g.status == "ok") & (g.offset.abs() >= T - 1e-9) & (g.prob >= P)).any())
            new = np.where(a.item_id.map(fire), "no", a.pred)
            ra, rb = a.pred.values == a.y.values, new == a.y.values
            o = a.variant.values == "original"
            sw.append(dict(T=T, P=P, fixed=int((~ra & rb).sum()), broken=int((ra & ~rb).sum()),
                           fixed_early=int((~ra & rb & (a.variant.values == "audio_shift_early")).sum()),
                           fixed_late=int((~ra & rb & (a.variant.values == "audio_shift_late")).sum()),
                           broken_orig=int((ra & ~rb & o).sum()),
                           orig_FA=f"{(a.pred.values[o] == 'no').mean():.2f} -> {(new[o] == 'no').mean():.2f}"))
    sw = pd.DataFrame(sw)
    base = dict(n_rows=len(a), n_shift_wrong=int(((a.pred != a.y) & (a.variant != "original")).sum()), n_orig=int((a.variant == "original").sum()))
    return q, h, sw, base


def first_order(spans, actions):
    firsts = {}
    for act in actions:
        sp = spans.get(act) or []
        if not sp:
            return None, "action not found"
        firsts[act] = min(s for s, _ in sp)
    if len(set(firsts.values())) < len(firsts):
        return None, "tied first starts"
    return sorted(actions, key=lambda x: firsts[x]), ""


def tcr():
    P = {x["item_id"]: x for x in json.load(open(EV / "hdepic_medium_prompts.json"))}
    rows = pd.read_csv(L / "scores_rows.csv")
    a = rows[(rows["set"] == "C30") & (rows.cond == "anchor") & rows.pred.isin(["yes", "no"])]
    out = []
    for uid, var in zip(a.uid, a.variant):
        iid = uid.split("|")[1]
        it = P[iid]
        ids = {e["id"]: e["action"] for e in it["events"]}
        want = [ids[e] for e in it["temporal_constraint"]["value"]["ordered_events"]]
        r = json.load(open(QW / "qwen_timestamps_share/hdepic" / f"{iid}.json"))
        sp, err = PQ.parse(r["reply"], r["actions"])
        if sp is None:
            out.append(dict(item=iid, variant=var, result="undetermined", why=err))
            continue
        got, why = first_order(sp, list(dict.fromkeys(want)))
        res = "undetermined" if got is None else ("agree" if got == list(dict.fromkeys(want)) else "disagree")
        out.append(dict(item=iid, variant=var, result=res, why=why))
    d = pd.DataFrame(out)
    t = d.groupby(["variant", "result"]).size().unstack(fill_value=0).reindex(columns=["agree", "disagree", "undetermined"], fill_value=0)
    t["n"] = t.sum(1)
    t["correct answer"] = ["disagree" if v == "order_swap" else "agree" for v in t.index]
    why = d[d.result == "undetermined"].why.value_counts().to_dict()
    return t.reset_index(), why, d


def tcc():
    gt = pd.read_csv(EV / "hdepic_move_gt.csv").set_index("item_id")
    M = {x["item_id"]: x for x in json.load(open(EV / "hdepic_move_prompts.json"))}
    man = [json.loads(l) for l in open(_pl.Path(_LEGACY_ROOT, "evaluation/ablation/gepa_stage2") / "manifests_v3/test.jsonl")]
    per_act, per_item = [], []
    for m in man:
        if m["source"] != "hdmove" or m["axis"] != "TCC":
            continue
        iid = m["item_id"]
        true = {f"move {k}": len(v) for k, v in json.loads(gt.loc[iid, "move_starts_sec"]).items()}
        prompt = {e["action"]: e.get("count") for e in M[iid]["events"]}
        r = json.load(open(QW / "move_1030/hdepicmove" / f"{iid}.json"))
        sp, err = PQ.parse(r["reply"], r["actions"])
        if sp is None:
            per_item.append(dict(item=iid, variant=m["variant"], usable=False))
            continue
        errs, match_prompt = [], []
        for act, tc in true.items():
            qc = len(sp.get(act, []))
            per_act.append(dict(item=iid, variant=m["variant"], action=act, true=tc, prompt=prompt.get(act), qwen=qc, err=qc - tc))
            errs.append(qc - tc)
            match_prompt.append(qc == prompt.get(act))
        per_item.append(dict(item=iid, variant=m["variant"], usable=True, exact=all(e == 0 for e in errs),
                             matches_prompt=all(match_prompt)))
    pa, pi = pd.DataFrame(per_act), pd.DataFrame(per_item)
    s1 = pa.groupby("variant").agg(actions=("err", "size"), exact=("err", lambda e: (e == 0).mean()), MAE=("err", lambda e: e.abs().mean()),
                                   over=("err", lambda e: (e > 0).mean()), under=("err", lambda e: (e < 0).mean()),
                                   mean_signed=("err", "mean")).reset_index()
    u = pi[pi.usable]
    s2 = u.groupby("variant").agg(items=("exact", "size"), all_counts_exact=("exact", "mean"),
                                  qwen_counts_equal_prompt=("matches_prompt", "mean")).reset_index()
    s2["unusable"] = [int((~pi.usable & (pi.variant == v)).sum()) for v in s2.variant]
    return s1, s2, pa


if __name__ == "__main__":
    q, h, sw, base = synch()
    print("## Synchformer quantiles\n" + md(q) + "\n\n## offset histogram (0.5 s bins, centre)\n" + md(h, "{}") +
          f"\n\n## rule sweep (rows {base})\n" + md(sw, "{}"))
    t, why, d = tcr()
    print("\n## TCR order\n" + md(t, "{}") + f"\nundetermined reasons: {why}")
    s1, s2, pa = tcc()
    print("\n## TCC per action\n" + md(s1) + "\n\n## TCC per item\n" + md(s2))
    sw.to_csv(L / "tool_diag_1030_sweep.csv", index=False)
    d.to_csv(L / "tool_diag_1030_tcr.csv", index=False)
    pa.to_csv(L / "tool_diag_1030_tcc.csv", index=False)
