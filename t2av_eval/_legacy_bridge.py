"""Temporary, removed at the end of the move (step 3): modules not yet moved into the package are imported from legacy/.
Order: gepa_stage2 first, as the 11/01 scripts resolved it (run_two_stage, adapter)."""
import sys
from pathlib import Path

_L = Path(__file__).resolve().parents[1] / "legacy/evaluation/ablation"
for _p in (_L / "Tool_Use", _L, _L / "gepa_stage2"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
