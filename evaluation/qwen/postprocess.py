import pandas as pd

# 입력 / 출력 파일명
input_csv = "qwen3_omni_eval_results.csv"
output_csv = "qwen3_omni_review_sheet.csv"

df = pd.read_csv(input_csv)

def map_modality(label_type: str) -> str:
    if label_type == "speech":
        return "speech"
    return "silent_action"

review_df = pd.DataFrame({
    "index": range(1, len(df) + 1),
    "modality": df["label_type"].apply(map_modality),
    "label": df["label_name"],
    "Qwen answer": df["result"],
    "My answer": ""
})

review_df.to_csv(output_csv, index=False)
print(f"Saved to {output_csv}")