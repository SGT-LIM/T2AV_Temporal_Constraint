import pandas as pd

df = pd.read_csv("three_prompting.csv")

axes = ["A", "V", "AVB", "TC"]

# axis-wise mean
axis_stats = df.groupby("variant")[axes].mean()

# overall axis mean
axis_stats["Mean"] = axis_stats.mean(axis=1)

# strict success
df["strict_success"] = (df[axes].sum(axis=1) == 4).astype(int)

strict_stats = df.groupby("variant")["strict_success"].mean()

print(axis_stats)
print(strict_stats)