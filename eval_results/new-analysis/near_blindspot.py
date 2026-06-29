#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Near-blind-spot ranking: stable_wrong(=전부 실패)만이 아니라
'거의 항상 틀리는' unit까지 스펙트럼으로 본다.
입력: stability_deep/stability_matrix.csv (이미 생성됨)
"""
import os, pandas as pd, numpy as np

OUT = "/home/coder/T2AV/eval_results/new-analysis/stability_deep"
df = pd.read_csv(os.path.join(OUT, "stability_matrix.csv"))

# fail_frac = 실패한 config 수 / 비교 가능한 config 수
df["fail_frac"] = df["n_disagree"] / df["n_present"]

# 1) 실패한 config 개수별 분포 (8개,7개 실패가 몇 건인지)
dist = (df.groupby(["model", "n_present", "n_disagree"])
          .size().reset_index(name="units")
          .sort_values(["model", "n_disagree"], ascending=[True, False]))
dist.to_csv(os.path.join(OUT, "blindspot_count_distribution.csv"), index=False)

# 2) near-blind-spot: 거의 다 실패 (fail_frac >= 0.7 이고 최소 5개 config에서 평가됨)
near = df[(df["fail_frac"] >= 0.70) & (df["n_present"] >= 5)].copy()
cols = ["model","video_file","event","axis","n_present","n_disagree","fail_frac","class"]
cols = [c for c in cols if c in near.columns]
near = near[cols].sort_values(["fail_frac","n_disagree"], ascending=False)
near.to_csv(os.path.join(OUT, "near_blindspot_units.csv"), index=False)

# 3) 어느 축이 near-blind-spot에 많이 걸리나
by_axis = (near.groupby(["model","axis"]).size()
              .reset_index(name="near_blindspot_units")
              .sort_values(["model","near_blindspot_units"], ascending=[True,False]))

# 4) 어느 '이벤트 슬롯'이 많이 걸리나 (video 가로질러 event_k 반복 실패)
by_event = (near.groupby(["axis","event"]).size()
               .reset_index(name="units")
               .sort_values("units", ascending=False))

print("=== 실패 config 개수 분포 (n_disagree 큰 순) ===")
print(dist.to_string(index=False))
print(f"\n=== near-blind-spot units (fail_frac>=0.7, n_present>=5): {len(near)}건 ===")
print(near.to_string(index=False))
print("\n=== 축별 near-blind-spot 집계 ===")
print(by_axis.to_string(index=False))
print("\n=== 이벤트 슬롯별 (axis x event) near-blind-spot 집계 ===")
print(by_event.head(15).to_string(index=False))
print("\n[saved] blindspot_count_distribution.csv / near_blindspot_units.csv ->", OUT)
