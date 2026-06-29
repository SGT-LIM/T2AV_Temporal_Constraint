import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI

# ============================================================
# Configuration
# ============================================================

# Put your API key in the environment before running:
# export OPENAI_API_KEY="YOUR_KEY"
#
# Then run:
# python generate_single_modality_prompts.py

MODEL_NAME = "gpt-5.4-mini"
BASE_DIR = Path("/home/coder/T2AV/prompts")
GUIDE_PATH = BASE_DIR / "guidelines/may26_prompt_guideline.md"
SPECS_PATH = BASE_DIR / "specs/jun15_spec.jsonl"
OUTPUT_JSONL_PATH = BASE_DIR / "generated/6-comb_temporal_selected_specs_prompts.jsonl"
OUTPUT_JSON_PATH = BASE_DIR / "generated/6-comb_temporal_selected_specs_prompts.json"

MAX_RETRIES = 3
RETRY_SLEEP_SEC = 3


# ============================================================
# Helpers
# ============================================================

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def extract_text_from_response(response) -> str:
    # Most convenient accessor
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text.strip()

    # Fallback
    texts = []
    if hasattr(response, "output") and response.output:
        for item in response.output:
            content = getattr(item, "content", None)
            if not content:
                continue
            for c in content:
                if getattr(c, "type", None) == "output_text":
                    texts.append(getattr(c, "text", ""))

    return "\n".join(texts).strip()


def generate_prompt(
    client: OpenAI,
    instructions_text: str,
    spec: Dict[str, Any],
    model_name: str = MODEL_NAME,
) -> str:
    user_input = (
        "Generate one benchmark prompt for the following item.\n"
        "Return only the final prompt paragraph.\n\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.responses.create(
                model=model_name,
                instructions=instructions_text,
                input=user_input,
            )
            prompt_text = extract_text_from_response(response)

            if not prompt_text:
                raise RuntimeError("Empty response text returned by model.")

            return prompt_text

        except Exception as e:
            last_error = e
            print(f"[Retry {attempt}/{MAX_RETRIES}] Failed for {spec.get('item_id')}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SEC)

    raise RuntimeError(f"Failed after retries for {spec.get('item_id')}: {last_error}")


def write_jsonl(rows: List[Dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Please export it before running the script."
        )

    if not GUIDE_PATH.exists():
        raise FileNotFoundError(f"Guide file not found: {GUIDE_PATH}")

    if not SPECS_PATH.exists():
        raise FileNotFoundError(f"Specs file not found: {SPECS_PATH}")

    instructions_text = read_text(GUIDE_PATH)
    specs = read_jsonl(SPECS_PATH)

    client = OpenAI(api_key=api_key)

    print(f"Loaded guide: {GUIDE_PATH}")
    print(f"Loaded specs: {SPECS_PATH}")
    print(f"Total items: {len(specs)}")

    results = []
    for i, spec in enumerate(specs, start=1):
        item_id = spec.get("item_id", f"item_{i}")
        print(f"[{i}/{len(specs)}] Generating prompt for {item_id} ...")

        prompt_text = generate_prompt(
            client=client,
            instructions_text=instructions_text,
            spec=spec,
            model_name=MODEL_NAME,
        )

        row = {
            "item_id": item_id,
            "modality_combination": spec.get("modality_combination"),
            "subjects": spec.get("subjects"),
            "events": spec.get("events"),
            "content": spec.get("content"),
            "temporal_constraint": spec.get("temporal_constraint"),
            "scene_hint": spec.get("scene_hint"),
            "camera_hint": spec.get("camera_hint"),
            "generated_prompt": prompt_text,
        }
        results.append(row)

    write_jsonl(results, OUTPUT_JSONL_PATH)
    OUTPUT_JSON_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nDone.")
    print(f"Saved JSONL: {OUTPUT_JSONL_PATH}")
    print(f"Saved JSON:  {OUTPUT_JSON_PATH}")


if __name__ == "__main__":
    main()
