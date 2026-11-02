#!/usr/bin/env python3
"""Freeze the 11/01 replay fixture (tests/fixtures/replay_1101) from the stored 11/01 outputs. Reads only; makes no Gemini call.

Selection (deterministic, from the 11/01 files as they are at freeze time; sources of the main table only: hm_hdepic, hm_hdfoot,
hm_p3p9; the hm_p12new rows added at 22:58 are not part of the 11/01 table):
  stage 2  A:   one row per row-5 group (closed / open_reused / open_new_call)
           V:   closed, open_reused, and one row with a framing call
           AVB: closed, and one row per group where the pre-registered rule fires (every fired row also has a framing call)
           preferring rows that have a row 2 label, then rows where row 1 / 4 / 5 / framing disagree, so a changed label cannot hide.
  rows 1/2 the items of those rows (A / V / AVB), plus 3 TCR rows and 3 TCC rows scored in both rows.
Writes the fixture and MANIFEST.json (origin path, size, mtime and sha256 of every file read; freeze time), then pins the
system prompt / schema md5 of every call (pin(); 11/01 stored neither).

  python tests/replay_1101/freeze.py --scratch WORKDIR [--out tests/fixtures/replay_1101] [--pin-only]
"""
import argparse, csv, hashlib, json, os, re, shlex, shutil, subprocess, sys, time
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
LEG = REPO / "legacy/evaluation/ablation"
MAIN = Path("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint")
G2 = MAIN / "evaluation/ablation/gepa_stage2/runs/obsval_1028"
DATA = Path("/projectnb/ivc-ml/youngsun/T2AV_data")
RES = DATA / "real_av/eval/results"
RUNDIR = {"row1": RES / "hdepic_main_row1_anchor_g36_1101", "row2": RES / "hdepic_main_row2_onecall_sync_g36_1101"}
NSH = {"hdepic_p12": 3, "hdfoot_p12": 1, "hdmove_p12": 2, "p3p9": 24}
SRC2SET = {"hm_hdepic": "hdepic_p12", "hm_hdfoot": "hdfoot_p12", "hm_p3p9": "p3p9"}
EVD = DATA / "tools/gen_evidence_1030"
SYA = DATA / "tools/synchformer_action_1030"
CAPD = DATA / "real_av/eval/hdepic_main_1101_captions"
VID = DATA / "real_av/eval/hdepic_main_1101"
PY = sys.executable
READ = {}


def src(p):
    p = Path(p)
    if str(p) not in READ:
        st = p.stat()
        READ[str(p)] = dict(size=st.st_size, mtime=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                            sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    return p


def disagree(r, cols):
    v = {str(r[c]) for c in cols if c in r and str(r[c]) in ("yes", "no")}
    return len(v) > 1


def pick(df, n_cols, k=1, exclude=(), prefer=()):
    """first k uids, ranked by (has a row 2 label, conditions disagree), then uid"""
    df = df[~df.uid.isin(exclude)]
    rank = df.apply(lambda r: (r.uid not in prefer, not disagree(r, n_cols), r.uid), axis=1)
    return [df.uid.iloc[i] for i in sorted(range(len(df)), key=lambda i: rank.iloc[i])[:k]]


def select():
    s2 = pd.read_csv(src(G2 / "hd_stage2_rows_1101.csv"), dtype=str).fillna("")
    s2 = s2[s2.source.isin(SRC2SET)]
    sc = pd.read_csv(src(G2 / "hd_rows_scored_1101.csv"), dtype=str).fillna("")
    p1, p2 = (sc[sc.row == r].set_index("uid").pred for r in ("row1", "row2"))
    as_hm = lambda u: "hm_" + {"hdepic_p12": "hdepic", "hdfoot_p12": "hdfoot", "p3p9": "p3p9"}.get(u.split("|")[0], "?") + "|" + u.split("|", 1)[1]
    r2 = {as_hm(u) for u in p2.index if p2[u] in ("yes", "no")}
    C = ["row1", "row4", "row5", "row5_rule", "FRb", "FRc"]
    out = []
    a = s2[s2.axis == "A"]
    for g in ("closed", "open_reused", "open_new_call"):
        out += pick(a[a.admitted == g], C, prefer=r2)
    v = s2[s2.axis == "V"]
    out += pick(v[(v.admitted == "closed") & (v.FRb == "")], C, prefer=r2) + pick(v[(v.admitted == "open_reused") & (v.FRb == "")], C, prefer=r2)
    out += pick(v[v.FRb != ""], C, exclude=out, prefer=r2)
    b = s2[s2.axis == "AVB"]                     # every fired AVB row also has a framing call: one closed + one fired row per group
    out += pick(b[b.admitted == "closed"], C, prefer=r2)
    for grp in ("P01P02", "P03P09"):
        out += pick(b[(b.admitted == "open_reused") & (b.group == grp)], C, exclude=out, prefer=r2)
    s2sel = s2[s2.uid.isin(out)]

    both = sorted(u for u in p1.index.intersection(p2.index) if p1[u] in ("yes", "no") and p2[u] in ("yes", "no"))
    tc = []
    for ax, first in (("TCR", "hdepic_p12"), ("TCC", "hdmove_p12")):
        us = [u for u in both if u.endswith("|" + ax)]
        dis = lambda u: p1[u] != p2[u]
        a1 = [u for u in us if u.startswith(first + "|")]
        a2 = [u for u in us if u.startswith("p3p9|")]
        tc += (sorted(a1, key=lambda u: not dis(u))[:1] + sorted(a2, key=lambda u: not dis(u))[:2])
    s2uids = [f"{SRC2SET[u.split('|')[0]]}|{u.split('|')[1]}|{u.split('|')[2]}" for u in s2sel.uid]
    scsel = sc[sc.uid.isin(s2uids + tc)]
    return s2sel, scsel


def copy_rows(fx, items_by_set):
    for row, d in RUNDIR.items():
        (fx / "rows" / row).mkdir(parents=True, exist_ok=True)
        for s, items in items_by_set.items():
            fs = [d / f"{s}_shard{k}.csv" for k in range(NSH[s]) if (d / f"{s}_shard{k}.csv").exists()]
            df = pd.concat(pd.read_csv(src(f), engine="python", dtype=str, keep_default_na=False) for f in fs)
            df = df[df.item_id.isin(items)].drop_duplicates("item_id", keep="last")
            missing = set(items) - set(df.item_id)
            if missing:
                sys.exit(f"{row} {s}: items not in the stored run: {missing}")
            df.to_csv(fx / "rows" / row / f"{s}.csv", index=False)


def commands():
    """first recorded command per set and row, from the run README; output / index args dropped, paths templated."""
    out = {}
    for row, d in RUNDIR.items():
        for line in open(src(d / "README.md")):
            if "python -u run_agentic_eval.py" not in line:
                continue
            tok = shlex.split(line.strip())
            i = tok.index("python")
            env = dict(t.split("=", 1) for t in tok[:i])
            args = tok[i + 3:]
            s = Path(args[args.index("--outputs-dir") + 1]).name
            if (row, s) in out:
                continue
            drop = {"--output-csv", "--start-index", "--end-index"}
            clean, j = [], 0
            while j < len(args):
                if args[j] in drop:
                    j += 2; continue
                clean.append(args[j]); j += 1
            out[(row, s)] = dict(env=env, args=clean)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "tests/fixtures/replay_1101"))
    ap.add_argument("--scratch", required=True, help="work dir for the record runs (outside the repo)")
    ap.add_argument("--pin-only", action="store_true", help="only (re)write expected/call_settings.json on an existing fixture")
    a = ap.parse_args()
    fx, work = Path(a.out), Path(a.scratch)
    if a.pin_only:
        return pin(fx, work)
    if fx.exists():
        sys.exit(f"exists, not overwriting: {fx}")
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    s2sel, scsel = select()
    items_by_set = {}
    for u in scsel.uid:
        s, iid, _ = u.split("|")
        items_by_set.setdefault(s, set()).add(iid)
    items_by_set = {s: sorted(v) for s, v in items_by_set.items()}
    fx.mkdir(parents=True)
    copy_rows(fx, items_by_set)

    # prompts (subset of the run's prompt file) and video symlinks (to the resolved original targets)
    cmds = commands()
    (fx / "prompts").mkdir(); (fx / "videos").mkdir()
    for s, items in items_by_set.items():
        pj = Path(cmds[("row1", s)]["args"][cmds[("row1", s)]["args"].index("--prompt-json") + 1])
        P = [x for x in json.load(open(src(pj))) if x["item_id"] in items]
        json.dump(P, open(fx / "prompts" / f"{s}.json", "w"), indent=1, ensure_ascii=False)
        for iid in items:
            v = VID / s / iid / f"{iid}_v1_raw.mp4"
            (fx / "videos" / s / iid).mkdir(parents=True)
            os.symlink(os.path.realpath(v), fx / "videos" / s / iid / v.name)

    # row 2 inputs: caption subset, Synchformer section subset, audio cache entries (recorded by one replay on the live cache)
    r2 = fx / "row2_inputs"; (r2 / "captions").mkdir(parents=True); (r2 / "audio_cache").mkdir()
    sync_live = Path(cmds[("row2", "p3p9")]["env"]["T2AV_SYNC_EVIDENCE_JSON"])
    SY = json.load(open(src(sync_live)))
    sy = {}
    for s, items in items_by_set.items():
        c = cmds[("row2", s)]["args"]
        cj = Path(c[c.index("--caption-external-json") + 1])
        CJ = json.load(open(src(cj)))
        keys = [f"{iid}/{iid}_v1_raw.mp4" for iid in items]
        json.dump({k: CJ[k] for k in keys if k in CJ}, open(r2 / "captions" / f"{s}.json", "w"), indent=1, ensure_ascii=False)
        for iid in items:
            k = os.path.realpath(VID / s / iid / f"{iid}_v1_raw.mp4")
            if k in SY:
                sy[k] = SY[k]
    json.dump(sy, open(r2 / "sync_sections.json", "w"), indent=1, ensure_ascii=False)

    cmd_out = {f"{r}|{s}": c for (r, s), c in cmds.items() if s in items_by_set}
    json.dump(cmd_out, open(fx / "commands.json", "w"), indent=1)
    keyfile = work / "audio_keys.txt"
    live_cache = Path(os.environ.get("T2AV_AUDIO_EVIDENCE_CACHE", DATA / "audio_evidence_cache"))
    for s in items_by_set:
        c = cmds[("row2", s)]
        args = [x for x in c["args"]]
        args[args.index("--prompt-json") + 1] = str(fx / "prompts" / f"{s}.json")
        args[args.index("--outputs-dir") + 1] = str(fx / "videos" / s)
        args[args.index("--caption-external-json") + 1] = str(r2 / "captions" / f"{s}.json")
        env = {**os.environ, **c["env"], "T2AV_SYNC_EVIDENCE_JSON": str(r2 / "sync_sections.json"), "T2AV_AUDIO_EVIDENCE_CACHE": str(live_cache)}
        p = subprocess.run([PY, str(Path(__file__).parent / "run_rows.py"), "--code", str(LEG), "--stored-csv", str(fx / "rows/row2" / f"{s}.csv"),
                            "--report", str(work / f"record_row2_{s}.json"), "--workdir", str(work / f"record_cwd_{s}"),
                            "--record-audio-keys", str(keyfile), "--",
                            *args, "--output-csv", str(work / f"record_row2_{s}.csv")], env=env, capture_output=True, text=True)
        if p.returncode:
            sys.exit(f"record run failed for {s}:\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    for k in sorted(set(open(keyfile).read().split())):
        f = live_cache / k
        if f.exists():
            shutil.copy2(src(f), r2 / "audio_cache" / k)

    # stage 2: gt rows (legacy builder), rows.jsonl subset, call records, tool records
    S2 = fx / "stage2"; (S2 / "out/calls/gen_tool_text").mkdir(parents=True); (S2 / "out/calls/vcap_check").mkdir(parents=True)
    uids = set(s2sel.uid)
    lroot = work / "legacy_root"
    subprocess.run(["bash", str(REPO / "legacy/link_inputs.sh")], env=dict(os.environ, T2AV_LEGACY_ROOT=str(lroot)), check=True,
                   capture_output=True)
    src(MAIN / "evaluation/ablation/gepa_stage2/manifests_v3/test.jsonl")
    code = ("import sys, json; sys.path[:0] = [%r, %r]; import hd_stage2_1101 as H; "
            "json.dump([r for r in H.gt_rows() if r['uid'] in set(json.loads(sys.argv[1]))], sys.stdout)") % (str(LEG / "gepa_stage2"), str(LEG))
    p = subprocess.run([PY, "-c", code, json.dumps(sorted(uids))], env=dict(os.environ, T2AV_LEGACY_ROOT=str(lroot)),
                       capture_output=True, text=True, cwd=LEG)
    if p.returncode:
        sys.exit(p.stderr[-3000:])
    gt = json.loads(p.stdout)
    if {r["uid"] for r in gt} != uids:
        sys.exit(f"gt_rows does not reproduce the selected uids: {uids ^ {r['uid'] for r in gt}}")
    json.dump(gt, open(S2 / "gt_rows.json", "w"), indent=1)

    with open(S2 / "out/rows.jsonl", "w") as w:
        for line in open(src(G2 / "rows.jsonl")):
            if json.loads(line)["uid"] in uids:
                w.write(line)
    for st in ("HG4", "HG5", "HFRb", "HFRc"):
        for u in uids:
            f = G2 / "calls/gen_tool_text" / f"{st}__{u}.json"
            if f.exists():
                shutil.copy2(src(f), S2 / "out/calls/gen_tool_text" / f.name)
    for u in uids:
        f = G2 / "calls/vcap_check" / f"{u}.json"
        if f.exists():
            shutil.copy2(src(f), S2 / "out/calls/vcap_check" / f.name)

    (S2 / "evd/hdA").mkdir(parents=True); (S2 / "captions").mkdir(); (S2 / "sya/b110").mkdir(parents=True)
    shutil.copy2(src(EVD / "flam_threshold.json"), S2 / "evd/flam_threshold.json")
    shutil.copy2(src(SYA / "PREREGISTERED_RULE.json"), S2 / "sya/PREREGISTERED_RULE.json")
    caps = {}
    for r in gt:
        s = SRC2SET[r["source"]]
        if r["axis"] == "A":
            shutil.copy2(src(EVD / "hdA" / f"{s}__{r['item_id']}.json"), S2 / "evd/hdA" / f"{s}__{r['item_id']}.json")
        if r["axis"] == "V":
            if s not in caps:
                caps[s] = json.load(open(src(CAPD / f"{s}.json")))
            k = f"{r['item_id']}/{r['item_id']}_v1_raw.mp4"
            sub = json.load(open(S2 / "captions" / f"{s}.json")) if (S2 / "captions" / f"{s}.json").exists() else {}
            sub[k] = caps[s][k]
            json.dump(sub, open(S2 / "captions" / f"{s}.json", "w"), indent=1, ensure_ascii=False)
    avb_items = {r["item_id"] for r in gt if r["axis"] == "AVB"}
    header, keep = None, []
    for d in ("b110", "holdout", "p12all", "avbadd"):
        for f in sorted((SYA / d).glob("per_event_shard*.csv")):
            with open(src(f), newline="") as h:
                rd = csv.reader(h)
                hd = next(rd)
                header = header or hd
                if hd != header:
                    sys.exit(f"Synchformer header differs in {f}")
                keep += [x for x in rd if x[hd.index("item_id")] in avb_items]
    with open(S2 / "sya/b110/per_event_shard0.csv", "w", newline="") as h:
        w = csv.writer(h); w.writerow(header); w.writerows(keep)

    # expected labels (the 11/01 outputs)
    (fx / "expected").mkdir()
    s2sel.to_csv(fx / "expected/stage2_rows.csv", index=False)
    scsel.to_csv(fx / "expected/rows_scored.csv", index=False)
    tcgt = [dict(uid=u, gt={"__item__": y}) for u, y in zip(scsel.uid, scsel.y) if u.split("|")[2] in ("TCR", "TCC")]
    json.dump(tcgt, open(fx / "expected/tc_item_gt.json", "w"), indent=1)

    man = dict(frozen=t0, frozen_by="tests/replay_1101/freeze.py", legacy_code_commit=subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip(),
        selection=dict(stage2=sorted(uids), rows=sorted(scsel.uid.unique())),
        sources=READ, files={},
        video_symlinks={str(p.relative_to(fx)): os.readlink(p) for p in sorted(fx.rglob("*.mp4"))})
    json.dump(man, open(fx / "MANIFEST.json", "w"), indent=1)
    pin(fx, work)
    print(f"frozen {len(uids)} stage-2 rows, {scsel.uid.nunique()} scored rows, items {dict((s, len(v)) for s, v in items_by_set.items())}")


def pin(fx, work):
    """Pin what 11/01 did not store: the md5 of the system prompt and response schema of every replayed call, as built by the
    legacy code. Valid only if the legacy row 1 / 2 code is the code that ran on 11/01: checked against the md5 list in both run
    READMEs; any difference stops the pin."""
    sys.path.insert(0, str(Path(__file__).parent))
    import common
    fx, work = Path(fx), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    check = {}
    for row, d in RUNDIR.items():
        for line in open(src(d / "README.md")):
            m = re.match(r"^([0-9a-f]{32})  ([a-z_]+\.py)$", line.strip())
            if m:
                body = re.sub(rb"(?m)^# Replaced by t2av_eval.*\n", b"", (LEG / m.group(2)).read_bytes(), count=1)  # pointer line of step 3
                now = hashlib.md5(body).hexdigest()
                check[f"{row}|{m.group(2)}"] = dict(run=m.group(1), legacy=now, same=m.group(1) == now)
    bad = [k for k, v in check.items() if not v["same"]]
    if not check or bad:
        sys.exit(f"legacy code differs from the 11/01 run, not pinning: {bad or 'no md5 list found'}")
    cmds = json.load(open(fx / "commands.json"))
    settings = {}
    for k, c in sorted(cmds.items()):
        row, s = k.split("|")
        argv, env = common.rows_cmd(fx, LEG, row, s, c, work / f"pin_{row}_{s}.csv", work / f"pin_{row}_{s}.json")
        p = subprocess.run(argv, env=env, capture_output=True, text=True)
        r = json.load(open(work / f"pin_{row}_{s}.json"))
        if p.returncode or r["unmatched"]:
            sys.exit(f"pin replay failed for {k}:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
        settings.update({f"{row}|{x['key']}": dict(system_md5=x["system_md5"], schema_md5=x["schema_md5"]) for x in r["served"]})
    cp = work / "pin_stage2_fx"
    shutil.rmtree(cp, ignore_errors=True); shutil.copytree(fx, cp, symlinks=True)
    argv, env = common.stage2_cmd(cp, LEG, work / "pin_stage2.json")
    p = subprocess.run(argv, env=env, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"pin stage-2 replay failed:\n{p.stderr[-2000:]}")
    settings.update({f"stage2|{k}": v for k, v in json.load(open(work / "pin_stage2.json"))["call_settings"].items()})
    json.dump(settings, open(fx / "expected/call_settings.json", "w"), indent=1, sort_keys=True)
    man = json.load(open(fx / "MANIFEST.json"))
    man["sources"].update(READ)
    man["code_md5_vs_1101_runs"] = check
    man["pinned"] = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S%z"), what="expected/call_settings.json: system prompt and response "
                         "schema md5 per call, built by legacy/evaluation/ablation (identical to the 11/01 code, see code_md5_vs_1101_runs)")
    man["files"] = {str(p.relative_to(fx)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(fx.rglob("*")) if p.is_file() and not p.is_symlink() and p.name != "MANIFEST.json"}
    json.dump(man, open(fx / "MANIFEST.json", "w"), indent=1)
    print(f"pinned {len(settings)} calls")


if __name__ == "__main__":
    main()
