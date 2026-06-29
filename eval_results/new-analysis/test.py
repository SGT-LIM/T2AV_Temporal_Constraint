import pandas as pd
g = pd.read_csv("/home/coder/T2AV/eval_results/gemini/LTX-2.3/NoTools.csv")
print("shape:", g.shape)
print("cols:", list(g.columns))
# TC-Relation 행이 어떻게 들어있는지
ax = [c for c in g.columns if 'axis' in c.lower()]
if ax:
    print("axis uniques:", list(g[ax[0]].unique()))
print(g.head(6).to_string())