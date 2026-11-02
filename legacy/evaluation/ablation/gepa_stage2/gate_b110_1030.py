#!/usr/bin/env python3
"""Gate for the holdout step (10/30): Synchformer ACTION-WINDOW readings on the 110 B items; rule |offset| >= 1.0 s and p >= .5
applied to the anchor_1030 verdicts. Writes GATE_OK if the rule breaks 0 B originals, else GATE_STOP (threshold is NOT retuned).
No judge calls.  python gepa_stage2/gate_b110_1030.py"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_diag_1030 as TD

T = Path("/projectnb/ivc-ml/youngsun/T2AV_data/tools/synchformer_action_1030")
pe = pd.concat(pd.read_csv(f) for f in sorted((T / "b110").glob("per_event_shard*.csv")))
assert pe.item_id.nunique() == 110, f"only {pe.item_id.nunique()} items"
pe.to_csv(T / "b110" / "per_event.csv", index=False)
q, h, sw, base = TD.synch(pe)
print("## quantiles\n" + TD.md(q) + "\n\n## histogram\n" + TD.md(h, "{}") + f"\n\n## rule sweep {base}\n" + TD.md(sw, "{}"))
row = sw[(sw["T"] == 1.0) & (sw["P"] == 0.5)].iloc[0]
ok = int(row.broken_orig) == 0
(T / ("GATE_OK" if ok else "GATE_STOP")).write_text(f"T=1.0 P=0.5 fixed={row.fixed} broken_orig={row.broken_orig} orig_FA={row.orig_FA}\n")
print(f"\nGATE: {'OK' if ok else 'STOP'}  (T=1.0, P=0.5: fixed {row.fixed}, broken originals {row.broken_orig}, original FA {row.orig_FA})")
sw.to_csv(T / "b110" / "rule_sweep.csv", index=False)
