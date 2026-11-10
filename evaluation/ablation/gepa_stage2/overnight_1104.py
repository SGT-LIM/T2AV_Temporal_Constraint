#!/usr/bin/env python3
"""Overnight 11/04 queue, scoring and step-8 rows. Writes markdown sections for docs/overnight_1104.md (printed to stdout).
  python gepa_stage2/overnight_1104.py step0          # AVB Synchformer-only (one call, --axes avb) vs rows 1 / 2 / 4 / 5, same rows
  python gepa_stage2/overnight_1104.py step8_rows     # two-stage with no tool text: sets HN (HD-EPIC) and GN (220 LTX / MOVA)
  python gepa_stage2/overnight_1104.py step8_score    # HN / GN vs media only (row 1) and gated (row 5), same rows
Groups: P01/P02 (v3-test + option (ii); V noun_swap = old rule) and P03-P09; generated per generator (220 LTX, 220 MOVA, 149 LTX).
Metrics: acc / FAIL precision / FAIL recall / FA on originals (HD-EPIC) or on GT-PASS rows (generated); n, n FAIL. No pooling.
"""
import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists()))); import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md
import glob, json, sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import rep_scoring as RS
import obs_judge_1028 as O
import hd_stage2_1101 as H
import gen_stage2_1030 as G

RES = O.RES
M = Path((_tp.WORKSPACE + "/eval_results/multi_agent"))
SYNC_HD = RES / "hdepic_main_g36_1104_avb_syncOnly"
SYNC_GEN = M / "gen_g36_1104_avb_syncOnly"
HD_SRC = {"hm_hdepic": "P01/P02", "hm_p12new": "P01/P02", "hm_oldnoun12": "P01/P02", "hm_p3p9": "P03-P09"}
GEN_SRC = {"g220ltx": "220 LTX", "g220mova": "220 MOVA", "g149": "149 LTX"}
NOTOOL_TEXT = "Observation: none. No tool was run for this call and no additional observation of the clip is available."


def load(fs):
    fs = [str(f) for f in fs if Path(f).exists() and "per_event" not in str(f)]
    return RS.load(fs) if fs else None


def metrics(g, c):
    h = g[g[c].isin(["yes", "no"])]
    if not len(h):
        return "–"
    tp = ((h[c] == "no") & (h.y == "no")).sum(); pf = (h[c] == "no").sum(); nf = (h.y == "no").sum()
    o = h[h.orig]
    f = lambda a, b: f"{a / b:.2f}".replace("0.", ".") if b else "–"
    return f"{f((h[c] == h.y).sum(), len(h))} / {f(tp, pf)} / {f(tp, nf)} / {f((o[c] == 'no').sum(), len(o))} ({len(h)}, {nf})"


def table(D, conds, names):
    out = ["| group / generator | axis | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for (g, ax), q in D.groupby(["group", "axis"], sort=False):
        out.append(f"| {g} | {ax} | " + " | ".join(metrics(q, c) for c in conds) + " |")
    return "\n".join(out)


def hd_rows(axes):
    S = pd.read_csv(O.OUT / "hd_stage2_rows_1101.csv")
    S["src"] = S.uid.str.split("|").str[0]; S["iid"] = S.uid.str.split("|").str[1]
    S = S[S.axis.isin(axes) & S.src.isin(HD_SRC)]
    S = S[~(S.src.isin(["hm_hdepic", "hm_p12new"]) & (S.variant == "noun_swap"))]
    S["group"] = S.src.map(HD_SRC); S["orig"] = S.variant == "original"
    return S


def gen_rows(axes, sets=GEN_SRC):
    P = pd.read_csv(O.OUT / "gen_row5_prereg_rows_1102.csv")
    src = {("220", "LTX_2p3"): "g220ltx", ("220", "MOVA"): "g220mova", ("149", "LTX_2p3"): "g149"}
    P["src"] = [src[(str(s), m)] for s, m in zip(P.set, P.model)]
    P["iid"] = P.uid.str.split("|").str[1]
    P = P[P.axis.isin(axes) & P.src.isin(sets)].rename(columns={"row5_prereg": "row5"})
    P["group"] = P.src.map(GEN_SRC); P["orig"] = P.y == "yes"
    return P


def step0():
    gt = {r["uid"]: r["gt"] for r in H.gt_rows()} | {r["uid"]: r["gt"] for r in G.gt_rows()}
    S = hd_rows(["AVB"])
    S = S[S.src != "hm_oldnoun12"]
    r2 = {"hm_hdepic": load(RES / "hdepic_main_row2_onecall_sync_g36_1101" / f"hdepic_p12_shard{k}.csv" for k in range(3)),
          "hm_p3p9": load(RES / "hdepic_main_row2_onecall_sync_g36_1101" / f"p3p9_shard{k}.csv" for k in range(24))}
    sy = {"hm_hdepic": load(sorted(SYNC_HD.glob("p12_shard*.csv"))), "hm_p12new": load(sorted(SYNC_HD.glob("p12new_shard*.csv"))),
          "hm_p3p9": load(sorted(SYNC_HD.glob("p3p9_shard*.csv")))}
    S["row2"] = [RS.row_label(r2[s], i, "AVB", gt[u]) if r2.get(s) is not None else "" for s, i, u in zip(S.src, S.iid, S.uid)]
    S["sync"] = [RS.row_label(sy[s], i, "AVB", gt[u]) if sy.get(s) is not None else "" for s, i, u in zip(S.src, S.iid, S.uid)]
    P = gen_rows(["AVB"])
    pre = {"g220ltx": "LTX_2p3", "g220mova": "MOVA", "g149": "gen149"}
    import gen_rows_score_1030 as GR
    for s, p in pre.items():
        d2 = load(sorted(glob.glob(str(GR.R / GR.RUNS["row2"] / f"{p}_shard*.csv")))); ds = load(sorted(SYNC_GEN.glob(f"{p}_shard*.csv")))
        m = P.src == s
        P.loc[m, "row2"] = [RS.row_label(d2, i, "AVB", gt[u]) if d2 is not None else "" for i, u in zip(P[m].iid, P[m].uid)]
        P.loc[m, "sync"] = [RS.row_label(ds, i, "AVB", gt[u]) if ds is not None else "" for i, u in zip(P[m].iid, P[m].uid)]
    D = pd.concat([S.assign(axis="AVB"), P.assign(axis="AVB")])[["group", "axis", "uid", "y", "orig", "row1", "row2", "row4", "row5", "sync"]]
    D.to_csv(O.OUT / "overnight_1104_step0_rows.csv", index=False)
    print(table(D, ["row1", "sync", "row2", "row4", "row5"],
                ["media only (row 1)", "media + Synchformer only (one call)", "media + all tools (row 2)", "always shown (row 4)", "gated (row 5)"]))


def step8_rows():
    rows = [r for r in H.gt_rows() if r["axis"] in ("AVB", "V") and r["source"] in HD_SRC
            and not (r["source"] in ("hm_hdepic", "hm_p12new") and r["variant"] == "noun_swap")]
    hn = [x for r in rows for x in G.row("HN", r, NOTOOL_TEXT)]
    G.add_rows("HN", hn)
    grows = [r for r in G.gt_rows() if r["axis"] in ("AVB", "V") and r["source"] in ("g220ltx", "g220mova")]
    gn = [x for r in grows for x in G.row("GN", r, NOTOOL_TEXT)]
    G.add_rows("GN", gn)
    print(f"HN rows {len(hn) // 2}, GN rows {len(gn) // 2}")


def lab(set_name, r):
    f = O.OUT / "calls" / G.COND / f"{set_name}__{r.uid}.json"
    if not f.exists():
        return ""
    rec = json.load(open(f))
    if rec["status"] != "ok":
        return ""
    return O.obs_label(rec, r.axis, r.gt)


def step8_score():
    gt = {r["uid"]: r["gt"] for r in H.gt_rows()} | {r["uid"]: r["gt"] for r in G.gt_rows()}
    S = hd_rows(["AVB", "V"]); P = gen_rows(["AVB", "V"], {"g220ltx": 1, "g220mova": 1})
    for D, s in ((S, "HN"), (P, "GN")):
        D["gt"] = D.uid.map(gt)
        D["notool"] = [lab(s, r) if r.gt is not None else "" for r in D.itertuples()]
        D["notool"] = [n if n else r1 for n, r1 in zip(D.notool, D.row1)]     # no call (stage 1 gated / no anchor) = stage 1
        D["changed"] = D.notool != D.row1
    D = pd.concat([S, P])
    D.to_csv(O.OUT / "overnight_1104_step8_rows.csv", index=False)
    print(table(D, ["row1", "notool", "row5"], ["media only (row 1)", "two-stage, no tool text", "gated (row 5)"]))
    ch = D.groupby(["group", "axis"]).agg(n=("uid", "size"), changed=("changed", "sum")).reset_index()
    print("\nRows where the no-tool stage 2 changed the stage-1 label:\n")
    print("| group / generator | axis | rows | changed |\n|---|---|---|---|")
    for r in ch.itertuples():
        print(f"| {r.group} | {r.axis} | {r.n} | {int(r.changed)} |")


# ------------------------------------------------------------------ steps 1-6 (user 11/04, second message)
F = lambda a, b: (f"{a / b:.2f}".replace("0.", ".") if b else "–")


def md(df, cols=None):
    cols = cols or list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in df.iterrows()])


def step1():
    T = pd.read_csv(O.OUT / "final_tables_1103.csv")
    keep = T[~T.line.astype(str).str.contains("additions")]
    keep.to_csv(O.OUT / "final_tables_1104.csv", index=False)
    print(f"- Final tables without the AVB additions: runs/obsval_1028/final_tables_1104.csv ({len(keep)} of {len(T)} lines; the "
          f"{len(T) - len(keep)} additions lines, incl. the >= 20 dB and stir lines, are removed). final_tables_1103.csv is kept unchanged.")


def step2():
    for tag, g in (("", "P01/P02"), ("_hm_ma39", "P03-P09")):
        d = pd.read_csv(O.OUT / f"hd_ma_rows{tag}_1101.csv")
        print(f"\n**{g}**: rows {len(d)}; " + ", ".join(f"{k} {v}" for k, v in d.variant.value_counts().items()) + "\n")
        print("| condition | acc / FAIL prec / FAIL rec / FA originals (n, FAIL) | FA on shams |\n|---|---|---|")
        for c, name in (("row1", "media only"), ("row4", "always shown"), ("row5", "gated")):
            h = d[d[c].isin(["yes", "no"])]; tp = ((h[c] == "no") & (h.y == "no")).sum(); o = h[h.variant == "original"]; sh = h[h.variant == "sham"]
            print(f"| {name} | {F((h[c] == h.y).sum(), len(h))} / {F(tp, (h[c] == 'no').sum())} / {F(tp, (h.y == 'no').sum())} / {F((o[c] == 'no').sum(), len(o))} ({len(h)}, {(h.y == 'no').sum()}) | {F((sh[c] == 'no').sum(), len(sh))} |")


def step3():
    T = pd.read_csv(O.OUT / "final_tables_1104.csv")
    print("### 3a. Generated, media + all tools (row 2) per axis, next to media only (row 1). acc / FAIL precision / FAIL recall (n, FAIL)\n")
    g = T[T.table.str.startswith("generated") & T.line.str.contains("rows 1 / 2")]
    print("| set | generator | axis | media only | media + all tools |\n|---|---|---|---|---|")
    for (tb, gm, ax), q in g.groupby(["table", "group", "axis"], sort=False):
        c = {r.cond: f"{F(r.acc, 1)} / {F(r.prec, 1)} / {F(r.rec, 1)} ({int(r.n)}, {int(r.n_fail)})" for r in q.itertuples()}
        print(f"| {tb.split()[1]} | {gm} | {ax} | {c.get('row1', '–')} | {c.get('row2', '–')} |")
    print("\n- 149 row 2: run 11/01, scored 11/03; 220 row 2: 10/30.\n")
    print("### 3b. Controller tables after the 6 same-pair noun_swap drops (rescored 11/03, `ctrl3_1102/table_1103.csv`; AVB additions groups omitted, reference only)\n")
    C = pd.read_csv(O.OUT / "ctrl3_1102/table_1103.csv"); C = C[~C.group.str.contains("avbadd")]
    C = C[C.cond.str.startswith("row5") | (C.cond == "row1")]
    C["cell"] = [f"{F(r.open_rate, 1) if r.cond != 'row1' else '–'} / {F(r.recall, 1)} / {F(r.FA_orig, 1)}" for r in C.itertuples()]
    W = C.pivot_table(index=["group", "model", "axis"], columns="cond", values="cell", aggfunc="first").reset_index()
    print("open rate / recall / FA on originals\n"); print(md(W, ["group", "model", "axis", "row1", "row5_code", "row5_gemini", "row5_openai"]))
    print("\n### 3c. AVB gate with the offset threshold alone (|offset| >= 1.8 s, no p condition), existing windows\n")
    S = hd_rows(["AVB"]); S = S[S.src != "hm_oldnoun12"]
    pe = H.sync_pe(); pe = pe[pe.status == "ok"].assign(a=lambda t: t.offset.abs())
    best = pe.sort_values(["a", "prob"], ascending=False).drop_duplicates("item_id").set_index("item_id")
    S["fire_full"] = S.iid.map(H.fires); S["fire_T"] = S.iid.map(lambda i: bool(i in best.index and best.a[i] >= H.RULE["T"] - 1e-9))
    S["rule_T"] = [("no" if f else r1) for f, r1 in zip(S.fire_T, S.row1)]
    S["judge_T"] = [((r4 or r1) if f else r1) for f, r1, r4 in zip(S.fire_T, S.row1, S.row4.fillna(""))]
    print("| group | gate | fires on rows | recall on shifted | FA on originals | originals broken (PASS -> FAIL) | acc |\n|---|---|---|---|---|---|---|")
    for grp, q in S.groupby("group"):
        for c, f, name in (("row5_rule", "fire_full", "full rule, code (T and P)"), ("row5", "fire_full", "full rule, gated judge"),
                           ("rule_T", "fire_T", "offset only, code"), ("judge_T", "fire_T", "offset only, gated judge")):
            h = q[q[c].isin(["yes", "no"])]; sh = h[h.y == "no"]; o = h[h.orig]
            print(f"| {grp} | {name} | {int(q[f].sum())} | {F((sh[c] == 'no').sum(), len(sh))} | {F((o[c] == 'no').sum(), len(o))} ({(o[c] == 'no').sum()} of {len(o)}) | "
                  f"{int(((o.row1 == 'yes') & (o[c] == 'no')).sum())} | {F((h[c] == h.y).sum(), len(h))} |")
    print("\n### 3d. Gated AVB by shift size (existing windows; fixed = row 1 PASS -> row 5 FAIL on a shifted row; broken = row 1 FAIL -> row 5 PASS)\n")
    items = {x["item_id"]: x for f in ((_tp.DATA + "/real_av_pilot/items_hdepic_medium_with_clips_v2.json"),
                                         (_tp.DATA + "/real_av_holdout_p3p9_1028/items_hdepic_p3p9_v1_with_clips_holdout.json")) for x in json.load(open(f))}
    S["shift_mag"] = S.iid.map(lambda i: abs(items[i]["media"]["shift_s"]) if i in items and "shift_s" in items[i].get("media", {}) else None)
    print("| group | |shift| | shifted rows scored | row 1 recall | row 5 judge recall | fixed / broken (judge) | row 5 code recall | fixed / broken (code) |\n|---|---|---|---|---|---|---|---|")
    for (grp, sz), q in S[S.shift_mag.notna()].groupby(["group", "shift_mag"]):
        h = q[q.row1.isin(["yes", "no"])]
        fx = lambda c: f"{int(((h.row1 == 'yes') & (h[c] == 'no')).sum())} / {int(((h.row1 == 'no') & (h[c] == 'yes')).sum())}"
        print(f"| {grp} | {sz:.1f} s | {len(h)} | {F((h.row1 == 'no').sum(), len(h))} | {F((h.row5 == 'no').sum(), len(h))} | {fx('row5')} | {F((h.row5_rule == 'no').sum(), len(h))} | {fx('row5_rule')} |")
    print("\n### 3e. tab:avb vs tab:main AVB\n")
    print("- tab:main AVB (final tables, 'AVB existing windows'): P01/P02 = all option (ii) windows (v3-test rows from 11/01; option (ii) rows: row 1 from 11/01 plus the 11/02 rerun of its failed items, stage 2 from 11/01-11/02); P03-P09 = 11/01.")
    print("- tab:avb (the 11/01 'AVB operating points' table): P01/P02 = the v3-test windows only (43 shifted / 51 originals, 11/01); P03-P09 = 11/01 (372 / 227). So for P01/P02 the two tables are on different rows.")
    print("- Re-cut below: tab:avb recomputed now, (i) on the 11/01 rows (P01/P02 v3-test windows) and (ii) on the tab:main rows.\n")
    print("| group | rows | condition | recall on shifted | FA on originals | acc |\n|---|---|---|---|---|---|")
    for grp, sub in (("P01/P02", "11/01 rows (v3-test windows)"), ("P01/P02", "tab:main rows (option ii)"), ("P03-P09", "11/01 = tab:main rows")):
        q = S[S.group == grp]
        if sub.startswith("11/01 rows"):
            q = q[q.src == "hm_hdepic"]
        for c, name in (("row1", "row 1 media only"), ("row5_rule", "row 5 code rule"), ("row5", "row 5 gated judge"), ("row4", "row 4 always shown")):
            h = q[q[c].isin(["yes", "no"])]; sh = h[h.y == "no"]; o = h[h.orig]
            print(f"| {grp} | {sub} | {name} | {F((sh[c] == 'no').sum(), len(sh))} (n {len(sh)}) | {F((o[c] == 'no').sum(), len(o))} ({(o[c] == 'no').sum()} of {len(o)}) | {F((h[c] == h.y).sum(), len(h))} |")


def step4():
    T = pd.read_csv(O.OUT / "final_tables_1104.csv")
    q = T[(T.table == "HD-EPIC") & (T.group == "P01/P02") & (T.axis == "V") & T.cond.isin(["row1", "row4", "row5"])]
    print("| line | condition | acc / FAIL prec / FAIL rec / FA originals (n, FAIL) |\n|---|---|---|")
    for r in q.itertuples():
        if "[row 2" in r.line:
            continue
        print(f"| {r.line.strip()} | {dict(row1='media only', row4='always shown', row5='gated')[r.cond]} | {F(r.acc, 1)} / {F(r.prec, 1)} / {F(r.rec, 1)} / {F(r.FA_orig, 1) if pd.notna(r.FA_orig) else '–'} ({int(r.n)}, {int(r.n_fail)}) |")


MUTE = Path((_tp.DATA + "/mute_1104"))
SILENT_A_TEXT = ("Observation (tool output):\n## Audio evidence\nThe clip contains NO audio stream (silent). Whisper/FLAM were not run; "
                 "any claimed sound cannot be present.")    # the pipeline's own text for a clip without an audio stream (new_eval)


def mute_rows():
    import new_eval as NE
    from make_gt_v3 import ids_for
    out = []
    for g, src in (("p12", "hm_mute12"), ("p3p9", "hm_mute39")):
        P = json.load(open(MUTE / g / "prompts_mute.json"))
        metas = NE.build_item_meta_map(P, modality_filter=None, item_overrides=None, relative_only=False)
        for x in P:
            st = NE.build_scoring_events(metas[x["item_id"]]); ids = [s["event_id"] for s in st]; a_ids = ids_for("A", st)
            for ax, gt in (("A", {e: "no" for e in a_ids}), ("V", {e: "yes" for e in ids})):
                if gt:
                    out.append(dict(source=src, item_id=x["item_id"], axis=ax, gt=gt, variant="mute", uid=f"{src}|{x['item_id']}|{ax}"))
    return out


def mute_caption(iid):
    if not hasattr(mute_caption, "c"):
        mute_caption.c = {}
        for f in sorted((MUTE / "gpu").glob("captions_*.json")):
            mute_caption.c.update({k.split("/")[0]: v["caption"] for k, v in json.load(open(f)).items() if v.get("caption")})
    return mute_caption.c.get(iid)


def step6_rows():
    rows, miss = [], 0
    for r in mute_rows():
        if r["axis"] == "A":
            rows += G.row("MU4", r, SILENT_A_TEXT)
        else:
            c = mute_caption(r["item_id"])
            if c is None:
                miss += 1; continue
            rows += G.row("MU4", r, "Observation (tool output):\nDense caption written by a separate captioning model (AVoCaDO) that "
                                    "watched and listened to the same clip without seeing the prompt:\n" + c.strip())
    G.add_rows("MU4", rows)
    print(f"MU4 rows {len(rows) // 2}; V rows without a caption {miss}")


def step6_vcheck(workers=4):
    """the 10/30 caption-check prompt (as hd_stage2_1101.stage_vcheck), on the mute V rows; cache calls/vcap_check/<uid>.json"""
    import hashlib, os, time
    from concurrent.futures import ThreadPoolExecutor
    from google import genai
    cache = O.OUT / "calls" / "vcap_check"
    todo = []
    for r in mute_rows():
        if r["axis"] != "V" or (cache / f"{r['uid']}.json").exists():
            continue
        c = mute_caption(r["item_id"])
        if c is None:
            continue
        evs = O.meta_for(r["source"], r["item_id"]); items = {x["item_id"]: x for x in json.load(open(O.PROMPTS[r["source"]]))}
        lines = [f"- event_{k + 1}: {e['definition']}" for k, e in enumerate(items[r["item_id"]]["events"]) if f"event_{k + 1}" in r["gt"]]
        user = ("Caption of a video (written by a captioning model that did not see any prompt):\n" + c.strip() +
                "\n\nTarget visual events:\n" + "\n".join(lines) +
                "\n\nFor each target event, answer with one verdict:\n- describes: the caption explicitly describes this event being "
                "performed as defined (action and, if stated, body side);\n- contradicts: the caption explicitly states something "
                "incompatible with the event (a different action in its place, the other body side, or that it does not happen);\n"
                "- not_mentioned: the caption says nothing about this event.\nQuote the caption phrase you used (empty if not_mentioned).")
        todo.append((r, dict(system=G.VCHK_SYSTEM, user=user, media=None, schema=G.VCHK_SCHEMA, anchor=[])))
    print(f"[vcap_check mute] to do {len(todo)}", flush=True)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def one(x):
        r, c = x
        try:
            parsed, raw = O.call(client, "gemini-3.6-flash", c, {"obs": {}, "uid": r["uid"]})
        except Exception as e:
            print(f"  [ERROR] {r['uid']}: {type(e).__name__}: {str(e)[:300]}", flush=True)
            return "error"
        json.dump(dict(status="ok", parsed=parsed, raw=raw, user=c["user"], user_md5=hashlib.md5(c["user"].encode()).hexdigest(), uid=r["uid"],
                       model="gemini-3.6-flash", thinking="high", time=time.strftime("%Y-%m-%dT%H:%M:%S")), open(cache / f"{r['uid']}.json", "w"))
        return "ok"
    n = {}
    with ThreadPoolExecutor(workers) as ex:
        for s in ex.map(one, todo):
            n[s] = n.get(s, 0) + 1
    print(f"[DONE] vcap_check mute: {n}", flush=True)


def step6_score():
    out = []
    for r in mute_rows():
        anc = RS.row_label(O.anchor_df(r["source"]), r["item_id"], r["axis"], r["gt"])
        f = O.OUT / "calls" / G.COND / f"MU4__{r['uid']}.json"
        r4 = ""
        if f.exists():
            rec = json.load(open(f)); r4 = O.obs_label(rec, r["axis"], r["gt"]) if rec["status"] == "ok" else ""
        if r["axis"] == "A":
            r5 = r4 or anc            # gate: a clip with no audio stream has nothing above T_flam -> FLAM-type text admitted (= row 4)
        else:
            vc = G.vcheck(r["uid"]) or {}
            r5 = (r4 or anc) if any(vc.get(e) == "contradicts" for e in r["gt"]) else anc
        out.append(dict(group="P01/P02" if r["source"] == "hm_mute12" else "P03-P09", axis=r["axis"], item_id=r["item_id"], y="no" if r["axis"] == "A" else "yes",
                        row1=anc, row4=r4, row5=r5))
    D = pd.DataFrame(out); D.to_csv(O.OUT / "overnight_1104_step6_rows.csv", index=False)
    S = hd_rows(["V"]); S = S[S.variant == "original"]
    print("**A on whole-audio mute items (GT FAIL): FAIL recall (n scored)**\n\n| group | media only | always shown | gated |\n|---|---|---|---|")
    for grp, q in D[D.axis == "A"].groupby("group"):
        print(f"| {grp} | " + " | ".join(f"{F((q[c] == 'no').sum(), q[c].isin(['yes', 'no']).sum())} ({q[c].isin(['yes', 'no']).sum()})" for c in ("row1", "row4", "row5")) + " |")
    print("\n**V on mute items (GT PASS) next to the same windows' originals: acc = share PASS, FA = share FAIL (n scored)**\n")
    print("| group | items | media only acc / FA | always shown acc / FA | gated acc / FA |\n|---|---|---|---|---|")
    for grp, q in D[D.axis == "V"].groupby("group"):
        o = S[(S.group == grp) & S.iid.isin({i.replace('_mute', '_pass') for i in q.item_id})]
        for name, h in (("mute", q), ("same windows' originals", o)):
            cells = []
            for c in ("row1", "row4", "row5"):
                k = h[h[c].isin(["yes", "no"])]
                cells.append(f"{F((k[c] == 'yes').sum(), len(k))} / {F((k[c] == 'no').sum(), len(k))} ({len(k)})")
            print(f"| {grp} | {name} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    globals()[sys.argv[1]]()
