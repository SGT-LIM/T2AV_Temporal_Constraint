"""No package module imports legacy code (the step-3 bridge is gone). Static check over every t2av_eval module.
The only legacy names still imported are the optional MediaPipe pose tools, inside new_eval's try/except fallback: pose
evidence is not in the package, so pose_evidence_mode must be none (the main table uses none)."""
import ast, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import move_module as MM

OPTIONAL = {"t2av_eval/judge/media/core.py": {"raw_mediapipe", "focused_raw_mediapipe"}}


def test_no_bridge_and_no_legacy_imports():
    assert not (REPO / "t2av_eval/_legacy_bridge.py").exists()
    bad = {}
    for f in sorted((REPO / "t2av_eval").rglob("*.py")):
        src = f.read_text()
        rel = str(f.relative_to(REPO))
        if "_legacy_bridge" in src or "legacy/evaluation" in src.replace("legacy/evaluation/ablation/run_agentic_eval.py", ""):
            bad[rel] = "references legacy/"
            continue
        names = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Import):
                names |= {a.name.split(".")[-1] if a.name.startswith("Tool_Use.") else a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0 and not n.module.startswith("t2av_eval"):
                names.add(n.module.split(".")[-1] if n.module.startswith("Tool_Use") else n.module.split(".")[0])
        left = (names & MM.LEGACY_NAMES) - OPTIONAL.get(rel, set())
        if left:
            bad[rel] = sorted(left)
    assert not bad, bad
