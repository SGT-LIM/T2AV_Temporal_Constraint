"""Every module moved into t2av_eval must equal its legacy source after the mechanical move (tools/move_module.rewrite: imports
of moved modules, path roots -> t2av_eval.paths, sys.path inserts dropped). Compared as ASTs with all imports dropped.
Any other difference must be listed in tests/moved_allowlist.json as {package module: {name: reason}}; a listed name (function,
class, or assigned name; "__doc__" for the module docstring) is dropped from both sides before the comparison.
This covers the moved code that the replay test does not run (data builders, generated-set stage 2, screening)."""
import ast, difflib, json, re, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import move_module as MM

MOVED = json.load(open(REPO / "t2av_eval/_moved.json")) if (REPO / "t2av_eval/_moved.json").exists() else {}
ALLOW = json.load(open(REPO / "tests/moved_allowlist.json"))
BLOCKS = ("body", "orelse", "finalbody")


def _norm(src, drop):
    t = ast.parse(src)
    if "__doc__" in drop and t.body and isinstance(t.body[0], ast.Expr) and isinstance(t.body[0].value, ast.Constant):
        t.body = t.body[1:]

    def keep(n):
        if isinstance(n, (ast.Import, ast.ImportFrom, ast.Pass)):
            return False
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "sys.path.insert":
            return False
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in drop:
            return False
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            names = {ast.unparse(x) for x in (n.targets if isinstance(n, ast.Assign) else [n.target])}
            if names & (set(drop) | {"_LEGACY_ROOT", "_LEGACY_CODE"}):
                return False
        return True

    for n in ast.walk(t):
        for f in BLOCKS:
            b = getattr(n, f, None)
            if isinstance(b, list) and b and isinstance(b[0], ast.stmt):
                setattr(n, f, [x for x in b if keep(x)] or ([ast.Pass()] if f == "body" else []))
        if isinstance(n, ast.ExceptHandler):
            n.body = [x for x in n.body if keep(x)] or [ast.Pass()]
    return t


@pytest.mark.parametrize("name", sorted(MOVED))
def test_moved_module_equals_legacy(name):
    m = MOVED[name]
    leg = re.sub(r"(?m)^# Replaced by t2av_eval.*\n", "", (MM.LEG / m["legacy"]).read_text(), count=1)
    pkg_file = REPO / (m["pkg"].replace(".", "/") + ".py")
    drop = ALLOW.get(m["pkg"], {})
    a = _norm(MM.rewrite(MM.fix_header(leg), None), drop)
    b = _norm(pkg_file.read_text(), drop)
    if ast.dump(a) != ast.dump(b):
        diff = "\n".join(difflib.unified_diff(ast.unparse(a).splitlines(), ast.unparse(b).splitlines(), "legacy (rewritten)", m["pkg"], lineterm="", n=2))
        pytest.fail(f"{m['pkg']} differs from {m['legacy']} beyond imports / allowlist:\n{diff[:6000]}")


def test_allowlist_names_exist():
    for pkg, names in ALLOW.items():
        assert pkg in {m["pkg"] for m in MOVED.values()}, f"allowlist entry for a module not moved: {pkg}"
        src = (REPO / (pkg.replace(".", "/") + ".py")).read_text()
        for n in names:
            assert n == "__doc__" or re.search(rf"(def|class)\s+{re.escape(n)}\b|^\s*{re.escape(n)}\s*=", src, re.M), f"{pkg}: {n} not found"
