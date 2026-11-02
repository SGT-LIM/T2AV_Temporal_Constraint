"""Move legacy modules into the package (step 3 of the refactor):
  python tools/move_module.py LEGACY_REL PKG_DOTTED [LEGACY_REL PKG_DOTTED ...]

- copies legacy/evaluation/ablation/<LEGACY_REL> to t2av_eval/<pkg path>.py
- rewrites imports of every moved module (t2av_eval/_moved.json) across ALL package files, keeping the bound names
- path roots: _LEGACY_ROOT / T2AV_data expressions -> t2av_eval.paths (WORK for runs, caches and docs; INPUTS for read-only
  inputs; DATA for T2AV_data)
- replaces sys.path.insert statements by `pass`; adds the bridge import while a file still imports unmoved legacy modules
- adds a one-line pointer to the legacy file
tests/test_moved_equivalence.py imports rewrite(): each package module must equal rewrite(legacy file) apart from imports and
the manual edits listed in tests/moved_allowlist.json.
"""
import ast, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEG = REPO / "legacy/evaluation/ablation"
PKG = REPO / "t2av_eval"
MOVED_F = PKG / "_moved.json"
moved = json.load(open(MOVED_F)) if MOVED_F.exists() else {}
DATA = "/projectnb/ivc-ml/youngsun/T2AV_data"
MAIN = "/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint"
HDR = re.compile(r"^import os as _os, pathlib as _pl; _LEGACY_ROOT = .*# legacy path roots, see legacy/README.md\n", re.M)
POINTER = "# Replaced by {dst} (t2av_eval package); this copy is kept to reproduce the 10/28-11/02 runs.\n"
LEGACY_NAMES = {p.stem for p in list(LEG.glob("*.py")) + list((LEG / "gepa_stage2").glob("*.py")) + list((LEG / "Tool_Use").glob("*.py"))}


# run outputs that no package module produces: read from the main checkout, never written
READ_ONLY_RUNS = {"evaluation/ablation/gepa_stage2/runs/v3_test/heldout_v3.csv"}


def where(full):
    """WORK or INPUTS for a path that was under the main checkout (relative to it)"""
    if full in READ_ONLY_RUNS:
        return "_P.INPUTS", full
    if full.startswith("evaluation/ablation/gepa_stage2/runs/"):
        return "_P.WORK", full[len("evaluation/ablation/gepa_stage2/runs/"):]
    for d in ("caption_cache", "panels_1028", "focus_1028", "fresh_stage1_cache"):
        if f"/{d}" in "/" + full:
            return "_P.WORK", full[full.index(d):]
    if full.startswith("docs/"):
        return "_P.WORK", full
    return "_P.INPUTS", full


def offs(src):
    lines = src.splitlines(keepends=True)
    st = [0]
    for l in lines:
        st.append(st[-1] + len(l))
    return lambda ln, col: st[ln - 1] + len(lines[ln - 1].encode()[:col].decode())


def rewrite(src, todo):
    t = ast.parse(src); off = offs(src); rep = []
    span = lambda n: (off(n.lineno, n.col_offset), off(n.end_lineno, n.end_col_offset))
    handled = set()
    for n in ast.walk(t):
        # _pl.Path(_LEGACY_ROOT, "X") / "rest" | f"rest"
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) and isinstance(n.left, ast.Call) \
                and ast.unparse(n.left.func) == "_pl.Path" and len(n.left.args) == 2 and ast.unparse(n.left.args[0]) == "_LEGACY_ROOT":
            base = n.left.args[0 + 1].value
            r = n.right
            if isinstance(r, ast.Constant):
                root, rest = where(base + "/" + r.value)
                rep.append((*span(n), f'{root} / "{rest}"')); handled.add(id(n.left))
            elif isinstance(r, ast.JoinedStr) and isinstance(r.values[0], ast.Constant):
                head = r.values[0].value
                root, rest = where(base + "/" + head)
                txt = src[slice(*span(r))]
                q = txt[1]
                newf = "f" + q + rest + txt[2 + len(head):]
                rep.append((*span(n), f"{root} / {newf}")); handled.add(id(n.left))
        # (_LEGACY_ROOT + "/rest")
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and ast.unparse(n.left) == "_LEGACY_ROOT" and isinstance(n.right, ast.Constant):
            root, rest = where(n.right.value.lstrip("/"))
            rep.append((*span(n), f'str({root} / "{rest}")'))
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith(DATA) and n.value[len(DATA):len(DATA) + 1] in ("", "/"):
            rest = n.value[len(DATA):]
            rep.append((*span(n), f'(str(_P.DATA) + "{rest}")' if rest else "str(_P.DATA)"))
        # sys.path.insert(...) statements
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "sys.path.insert":
            rep.append((*span(n), "pass  # (legacy sys.path insert removed)"))
        # imports of moved modules
        if isinstance(n, ast.Import):
            new = []
            for a_ in n.names:
                nm = a_.name.split(".")[-1] if a_.name.startswith("Tool_Use.") else a_.name
                if nm in moved:
                    pk, md = moved[nm]["pkg"].rsplit(".", 1)
                    new.append(f"from {pk} import {md} as {a_.asname or a_.name}")
                else:
                    new.append(f"import {a_.name}" + (f" as {a_.asname}" if a_.asname else ""))
            if any((a_.name.split(".")[-1] if a_.name.startswith("Tool_Use.") else a_.name) in moved for a_ in n.names):
                rep.append((*span(n), "; ".join(new)))
        if isinstance(n, ast.ImportFrom) and n.module:
            nm = n.module.split(".")[-1] if n.module.startswith("Tool_Use.") else n.module
            if nm in moved:
                names = ", ".join(a_.name + (f" as {a_.asname}" if a_.asname else "") for a_ in n.names)
                rep.append((*span(n), f"from {moved[nm]['pkg']} import {names}"))
    # drop nested duplicates (keep outermost)
    rep.sort(key=lambda r: (r[0], -r[1]))
    out, last_end = [], -1
    for s_, e, txt in rep:
        if s_ < last_end:
            continue
        out.append((s_, e, txt)); last_end = e
    for s_, e, txt in sorted(out, reverse=True):
        src = src[:s_] + txt + src[e:]
    return src


def legacy_imports(src):
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            names |= {(a_.name.split(".")[-1] if a_.name.startswith("Tool_Use.") else a_.name.split(".")[0]) for a_ in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.module.startswith("t2av_eval"):
            names.add(n.module.split(".")[-1] if n.module.startswith("Tool_Use") else n.module.split(".")[0])
            if n.module == "Tool_Use":
                names |= {a_.name for a_ in n.names}
    return sorted(x for x in names if x in LEGACY_NAMES and x not in moved)


def fix_header(src):
    uses_pl = None
    src2 = HDR.sub("from t2av_eval import paths as _P\n", src)
    if "_pl." in src2 or "_os." in src2:
        src2 = src2.replace("from t2av_eval import paths as _P\n", "import os as _os, pathlib as _pl\nfrom t2av_eval import paths as _P\n", 1)
    return src2


BRIDGE = "import t2av_eval._legacy_bridge  # noqa: F401  (temporary: unmoved legacy modules)\n"


def main(pairs):
    for rel, dotted in pairs:
        moved[Path(rel).stem] = dict(legacy=rel, pkg=dotted)
    for rel, dotted in pairs:
        src = re.sub(r"(?m)^# Replaced by t2av_eval.*\n", "", (LEG / rel).read_text(), count=1)
        dst = PKG / (dotted.split(".", 1)[1].replace(".", "/") + ".py")
        dst.parent.mkdir(parents=True, exist_ok=True)
        d = dst.parent
        while d != PKG.parent:
            if not (d / "__init__.py").exists():
                (d / "__init__.py").write_text("")
            d = d.parent
        dst.write_text(fix_header(src))
        lsrc = (LEG / rel).read_text()
        if "# Replaced by t2av_eval" not in lsrc:
            ptr = POINTER.format(dst=dst.relative_to(REPO))
            first, rest = lsrc.split("\n", 1)
            (LEG / rel).write_text(first + "\n" + ptr + rest if first.startswith("#!") else ptr + lsrc)
    json.dump(moved, open(MOVED_F, "w"), indent=1, sort_keys=True)

    report = {}
    for f in sorted(PKG.rglob("*.py")):
        if f.name in ("_legacy_bridge.py", "paths.py", "__init__.py", "cli.py"):
            continue
        src = rewrite(f.read_text().replace(BRIDGE, ""), None)
        if "_P." in src and "from t2av_eval import paths as _P" not in src:
            t = ast.parse(src)
            first = next(n for n in t.body if isinstance(n, (ast.Import, ast.ImportFrom)) and getattr(n, "module", None) != "__future__")
            lines = src.splitlines(keepends=True)
            lines.insert(first.lineno - 1, "from t2av_eval import paths as _P\n")
            src = "".join(lines)
        if "_pl." not in src and "_os." not in src:
            src = src.replace("import os as _os, pathlib as _pl\n", "", 1)
        left = legacy_imports(src)
        if left:
            t = ast.parse(src)
            first = next((n for n in t.body if isinstance(n, (ast.Import, ast.ImportFrom)) and getattr(n, "module", None) != "__future__"), None)
            lines = src.splitlines(keepends=True)
            lines.insert(first.lineno - 1, BRIDGE)
            src = "".join(lines)
        f.write_text(src)
        ast.parse(src)
        manual = [l.strip()[:110] for l in src.splitlines() if re.search(r"_LEGACY_|/projectnb/ivc-ml/youngsun/T2AV_Temporal|HERE\s*/|ABL\s*/|HERE\.parent", l)
                  and not l.lstrip().startswith("#")]
        if left or manual:
            report[str(f.relative_to(REPO))] = dict(legacy_imports=left, manual=manual)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(list(zip(sys.argv[1::2], sys.argv[2::2])))
