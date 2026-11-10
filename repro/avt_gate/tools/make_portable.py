#!/usr/bin/env python3
"""Make portable copies of the experiment code (deterministic; every substitution is logged).

The experiment code hard-codes absolute lab paths. This tool copies each source file and replaces only those path prefixes with
attributes of `t2av_paths` (environment variables). Nothing else in the code is changed, except the few explicitly listed
analysis-script lines in SPECIAL (code location and output directory).

  * code string literals:   "PREFIX/rest"   ->  (_tp.DATA + "/rest")      f"PREFIX/{x}"  ->  f"{_tp.DATA}/{x}"
  * comments / docstrings:  PREFIX          ->  $T2AV_DATA (documentation only)
  * one header line is inserted after the module docstring:  it appends the nearest ancestor holding t2av_paths.py to sys.path
    (append, so it never shadows other modules) and imports it as _tp.

Usage:  python make_portable.py --src <experiment checkout root> --dst <repo root> --files <list.txt> --log <log.csv>
"""
import argparse, csv, hashlib, io, re, sys, tokenize
from pathlib import Path

PREFIXES = [  # longest first
    ("/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint", "WORKSPACE", "T2AV_WORKSPACE"),
    ("/projectnb/ivc-ml/youngsun/T2AV_data", "DATA", "T2AV_DATA"),
    ("/projectnb/ivc-ml/youngsun/.hf_cache", "HF_CACHE", "T2AV_HF_CACHE"),
    ("/projectnb/ivc-ml/youngsun/tmp", "EXT_TMP", "T2AV_EXT_TMP"),
]
HEADER = ('import sys as _sys, pathlib as _pl; _sys.path.append(str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "t2av_paths.py").exists())));'
          ' import t2av_paths as _tp  # portable path roots (T2AV_* environment variables); see repro/avt_gate/README.md\n')
# analysis scripts lived in eval_results/analysis/<dir>/scripts/; in the repo they live in repro/avt_gate/analysis/.
SPECIAL = {
    "sanjoy_controls.py": [
        ('GS = ROOT / "evaluation/ablation/gepa_stage2"', 'GS = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2"   # portable: code dir of this checkout'),
        ('OUT = ROOT / "eval_results/analysis/sanjoy_two_baselines_2026-11-08"', 'OUT = _tp.out_dir("sanjoy_two_baselines_2026-11-08")   # portable: $T2AV_OUT_DIR/<name>'),
    ],
    "alpha_sensitivity.py": [
        ('GS = ROOT / "evaluation/ablation/gepa_stage2"', 'GS = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2"   # portable: code dir of this checkout'),
        ('OUT = ROOT / "eval_results/analysis/sensitivity_2026-11-10"', 'OUT = _tp.out_dir("sensitivity_2026-11-10")   # portable: $T2AV_OUT_DIR/<name>'),
    ],
    "score_handoff.py": [
        ('OUT = ROOT / "eval_results/analysis/paper_tables_handoff_2026-11-09"', 'OUT = _tp.out_dir("paper_tables_handoff_2026-11-09")   # portable: $T2AV_OUT_DIR/<name>'),
        ('FB = ROOT / "evaluation/ablation/gepa_stage2/runs/obsval_1028/final_benchmark_1108"',
         'FB = _pl.Path(__file__).resolve().parents[3] / "evaluation/ablation/gepa_stage2/runs/obsval_1028/final_benchmark_1108"   # portable: via the linked runs/ dir'),
    ],
}


def has_prefix(s):
    return any(p in s for p, _, _ in PREFIXES)


def doc_sub(s):
    for p, _, env in PREFIXES:
        s = s.replace(p, "$" + env)
    return s


def split_string_token(tok):
    m = re.match(r"(?is)^([rbuf]*)('''|\"\"\"|'|\")(.*)\2$", tok)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def code_sub(tok):
    sp = split_string_token(tok)
    if sp is None:
        return None, "unparsed"
    pre, q, body = sp
    if "b" in pre.lower():
        return None, "bytes literal"
    if len(q) == 3:
        return pre + q + doc_sub(body) + q, "triple-quoted (documentation substitution)"
    if "f" in pre.lower():
        for p, attr, _ in PREFIXES:
            body = body.replace(p, "{_tp." + attr + "}")
        return pre + q + body + q, "f-string"
    parts, rest = [], body
    pat = re.compile("|".join(re.escape(p) for p, _, _ in PREFIXES))
    out = []
    pos = 0
    for mm in pat.finditer(body):
        if mm.start() > pos:
            out.append(pre + q + body[pos:mm.start()] + q)
        attr = next(a for p, a, _ in PREFIXES if p == mm.group(0))
        out.append("_tp." + attr)
        pos = mm.end()
    if pos < len(body):
        out.append(pre + q + body[pos:] + q)
    return "(" + " + ".join(out) + ")", "string concatenation"


def transform(src_text, name, log):
    for old, new in SPECIAL.get(name, []):
        if src_text.count(old) != 1:
            raise SystemExit(f"{name}: special line not found exactly once: {old}")
        src_text = src_text.replace(old, new)
        log.append(dict(file=name, line="", kind="special", old=old, new=new))
    toks = list(tokenize.generate_tokens(io.StringIO(src_text).readline))
    lines = src_text.splitlines(keepends=True)
    edits = []   # (start(row,col), end(row,col), new)
    for t in toks:
        if t.type == tokenize.STRING and has_prefix(t.string):
            new, kind = code_sub(t.string)
            if new is None:
                raise SystemExit(f"{name}:{t.start[0]}: cannot handle {kind}: {t.string[:80]}")
            edits.append((t.start, t.end, new)); log.append(dict(file=name, line=t.start[0], kind=kind, old=t.string, new=new))
        elif t.type == tokenize.COMMENT and has_prefix(t.string):
            new = doc_sub(t.string); edits.append((t.start, t.end, new)); log.append(dict(file=name, line=t.start[0], kind="comment", old=t.string, new=new))
    off = [0]
    for l in lines:
        off.append(off[-1] + len(l))
    text = src_text
    for (sr, sc), (er, ec), new in sorted(edits, key=lambda e: (e[0][0], e[0][1]), reverse=True):
        a, b = off[sr - 1] + sc, off[er - 1] + ec
        text = text[:a] + new + text[b:]
    if "_tp." in text or "_tp.out_dir" in text:
        # insert the header after the module docstring (or shebang / coding lines)
        toks2 = list(tokenize.generate_tokens(io.StringIO(text).readline))
        ins_line = 1
        for t in toks2:
            if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.ENCODING):
                continue
            if t.type == tokenize.STRING:
                ins_line = t.end[0] + 1
            else:
                ins_line = t.start[0]
            break
        L = text.splitlines(keepends=True)
        fut = [i + 1 for i, l in enumerate(L) if l.startswith("from __future__")]
        if fut:
            ins_line = max(ins_line, fut[-1] + 1)
        L.insert(ins_line - 1, HEADER); text = "".join(L)
        log.append(dict(file=name, line=ins_line, kind="header", old="", new=HEADER.strip()))
    compile(text, name, "exec")
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True); ap.add_argument("--dst", required=True); ap.add_argument("--map", required=True,
                    help="TSV: source path (relative to --src) <TAB> destination path (relative to --dst)")
    ap.add_argument("--log", required=True); ap.add_argument("--sums", required=True)
    a = ap.parse_args()
    src, dst = Path(a.src), Path(a.dst); log, sums = [], []
    for line in open(a.map):
        if not line.strip() or line.startswith("#"):
            continue
        s, d = line.rstrip("\n").split("\t")
        raw = (src / s).read_bytes(); sums.append((hashlib.sha256(raw).hexdigest(), hashlib.md5(raw).hexdigest(), s, d))
        out = dst / d; out.parent.mkdir(parents=True, exist_ok=True)
        if s.endswith(".py"):
            out.write_text(transform(raw.decode(), Path(s).name, log))
        else:
            txt = raw.decode()
            if has_prefix(txt):
                raise SystemExit(f"{s}: non-Python file contains a lab path")
            out.write_bytes(raw)
    with open(a.log, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "line", "kind", "old", "new"]); w.writeheader(); w.writerows(log)
    with open(a.sums, "w") as f:
        f.write("# sha256  md5  experiment_source_path  ->  portable_path   (hashes of the ORIGINAL experiment files, before make_portable.py)\n")
        for s256, m5, s, d in sums:
            f.write(f"{s256}  {m5}  {s}  ->  {d}\n")
    print(f"{len(sums)} files, {len(log)} logged edits")


if __name__ == "__main__":
    main()
