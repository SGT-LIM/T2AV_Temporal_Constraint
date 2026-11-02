"""No API calls. 220 AVB media-only drift: 10/16 (baseline_min3_g36/rep1) vs 10/27 (baseline_min3_g36_1027) on v3 test AVB rows.
Per GT event: label, whether AVB was actually called or gated by a failed parent (A/V), and parent labels. Writes runs/v3_test/avb_drift_220_events.csv.
  python gepa_stage2/avb_drift_220.py"""
import json, pandas as pd
R = "/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results/multi_agent"
RUNS = {"1016": {"ltx": f"{R}/baseline_min3_g36/rep1/LTX_2p3_agentic_baseline_per_event.csv", "mova": f"{R}/baseline_min3_g36/rep1/MOVA_agentic_baseline_per_event.csv"},
        "1027": {"ltx": f"{R}/baseline_min3_g36_1027/LTX_2p3_per_event.csv", "mova": f"{R}/baseline_min3_g36_1027/MOVA_per_event.csv"}}
AX = {"A": "audio_event_correctness", "V": "visual_event_correctness", "AVB": "audio_visual_binding"}
pe = {k: {s: pd.read_csv(f, engine="python").drop_duplicates(["item_id", "event_id", "axis"], keep="last").set_index(["item_id", "event_id", "axis"])
          for s, f in v.items()} for k, v in RUNS.items()}
man = [json.loads(l) for l in open("gepa_stage2/manifests_v3/test.jsonl")]
rows = []
for m in man:
    if m["axis"] != "AVB" or m["source"] not in ("ltx", "mova"): continue
    for ev, gt in m["gt"].items():
        r = dict(source=m["source"], item_id=m["item_id"], event_id=ev, y=gt)
        for k in RUNS:
            df = pe[k][m["source"]]
            get = lambda ax, col: df.loc[(m["item_id"], ev, AX[ax]), col] if (m["item_id"], ev, AX[ax]) in df.index else ""
            r[f"avb_{k}"] = str(get("AVB", "label")).lower(); r[f"A_{k}"] = str(get("A", "label")).lower(); r[f"V_{k}"] = str(get("V", "label")).lower()
            reason = str(get("AVB", "reason")); r[f"gated_{k}"] = reason.startswith("Binding not evaluated"); r[f"reason_{k}"] = reason
        rows.append(r)
d = pd.DataFrame(rows)
d.to_csv("gepa_stage2/runs/v3_test/avb_drift_220_events.csv", index=False)
for s in ("ltx", "mova"):
    g = d[d.source == s]; print(f"\n== {s}: {len(g)} GT events ({(g.y=='no').sum()} FAIL), items {g.item_id.nunique()}")
    for k in RUNS:
        called = ~g[f"gated_{k}"]
        print(f"  {k}: AVB no {(g[f'avb_{k}']=='no').sum()} | gated {g[f'gated_{k}'].sum()} | called {called.sum()} -> no {((g[f'avb_{k}']=='no') & called).sum()} | A no {(g[f'A_{k}']=='no').sum()} V no {(g[f'V_{k}']=='no').sum()}")
    f = g[(g.y == "yes") & (g.avb_1016 == "yes") & (g.avb_1027 == "no")]
    print(f"  PASS events yes(10/16) -> no(10/27): {len(f)} | of which gated in 10/27: {f.gated_1027.sum()} (A no {(f.A_1027=='no').sum()}, V no {(f.V_1027=='no').sum()}) | AVB called and said no: {(~f.gated_1027).sum()}")
    b = g[(g.y == "yes") & (g.avb_1016 == "no") & (g.avb_1027 == "yes")]
    print(f"  PASS events no -> yes: {len(b)}")
    item = g.groupby("item_id").agg(y=("y", lambda x: "no" if (x == "no").any() else "yes"),
                                    p16=("avb_1016", lambda x: "no" if (x == "no").any() else "yes"), p27=("avb_1027", lambda x: "no" if (x == "no").any() else "yes"))
    for k in ("p16", "p27"): print(f"  item acc {k}: {(item[k]==item.y).mean():.2f} (n{len(item)}, FAIL {(item.y=='no').sum()})")
