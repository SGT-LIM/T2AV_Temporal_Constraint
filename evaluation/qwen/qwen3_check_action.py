import argparse
import csv
import json
import re
from pathlib import Path

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from qwen_vl_utils import process_vision_info


LABEL_TO_QUESTION = {
    "head_nod": "Does the person nod their head?",
    "head_shake": "Does the person shake their head side to side?",
    "shrug": "Does the person shrug?",
    "hand_wave": "Does the person wave one hand?",
    "pointing": "Does the person point forward with one hand?",
    "crossed_arms": "Does the person cross their arms?",
    "palm_up_gesture": "Does the person make a palm-up gesture with one hand?",
    "thumbs_up": "Does the person give a thumbs-up with one hand?",
    "hands_clasped_together": "Does the person clasp their hands together?",
    "bow": "Does the person give a small bow?",
    "knocking_on_a_door": "Does the person knock on a door?",
    "ringing_a_handbell": "Does the person ring a handbell?",
    "hammering": "Does the person hammer?",
    "tapping_a_pen": "Does the person tap a pen?",
    "typing_on_a_keyboard": "Does the person type on a keyboard?",
    "tapping_the_table_with_hand": "Does the person tap the table with one hand?",
    "clap": "Does the person clap?",
    "finger_snapping": "Does the person snap their fingers?",
    "stomp": "Does the person stomp one foot?",
    "patting_the_chest": "Does the person pat their chest?",
    "slapping_the_thigh": "Does the person slap their thigh?",
    "slapping_the_arm": "Does the person slap their arm?",
    "patting_the_shoulder": "Does the person pat their shoulder?",
    "throat_clearing": "Does the person clear their throat?",
    "sneezing": "Does the person sneeze?",
    "coughing": "Does the person cough?",
    "yeah": 'Does the person say "Yeah"?',
    "help": 'Does the person say "Help"?',
    "no": 'Does the person say "No"?',
    "okay": 'Does the person say "Okay"?',
    "right": 'Does the person say "Right"?',
    "wow": 'Does the person say "Wow"?',
    "oh": 'Does the person say "Oh"?',
    "thanks": 'Does the person say "Thanks"?',
    "sorry": 'Does the person say "Sorry"?',
    "i_dont_know": 'Does the person say "I don\'t know"?',
}


SYSTEM_PROMPT = """You are a strict video action evaluator.

Your job:
- Look at the video.
- Judge only whether the target action is performed.

Important:
- Ignore camera angle, framing, background, room type, and scene details.
- Ignore whether the person faces the camera.
- Ignore whether the background matches the prompt.
- Focus only on whether the target action is clearly performed.
- If the action is missing, different, or ambiguous, answer "no".
- Be conservative.

Return JSON only in this format:
{
  "label": "yes" or "no",
  "reason": "short explanation",
  "observed_action": "short description"
}
"""

def load_completed_videos(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()

    completed = set()
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_file = row.get("video_file", "").strip()
            result = row.get("result", "").strip()
            if video_file and result:
                completed.add(video_file)
    return completed


def load_existing_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def read_label(txt_path: Path) -> str:
    text = txt_path.read_text(encoding="utf-8")
    match = re.search(r"^label:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find label in {txt_path}")
    return match.group(1).strip()


def extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse JSON from output:\n{text}")
    return json.loads(match.group(0))


def evaluate_video(model, processor, video_path: Path, question: str) -> dict:
    user_text = f"""Question: {question}

Answer only whether the target action is performed in the video.
Return JSON only.
"""

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "user",
            "content": [
                {"type": "video", "video": str(video_path)},
                {"type": "text", "text": user_text},
            ],
        },
    ]

    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    # Qwen3-VL official pattern
    image_inputs, video_inputs, video_kwargs = process_vision_info(
        messages,
        image_patch_size=16,
        return_video_kwargs=True,
        return_video_metadata=True,
    )

    # If videos come back as (video_tensor, metadata), split them
    if video_inputs is not None:
        video_inputs, video_metadatas = zip(*video_inputs)
        video_inputs = list(video_inputs)
        video_metadatas = list(video_metadatas)
    else:
        video_metadatas = None

    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        video_metadata=video_metadatas,
        padding=True,
        return_tensors="pt",
        do_resize=False,
        **video_kwargs,
    )

    inputs = inputs.to(model.device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
        )

    trimmed_ids = [
        out_ids[len(in_ids):]
        for in_ids, out_ids in zip(inputs["input_ids"], output_ids)
    ]

    output_text = processor.batch_decode(
        trimmed_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]

    result = extract_json(output_text)
    result["raw_output"] = output_text
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        required=True,
        help="Directory containing .mp4 and matching .txt files",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen3-VL-8B-Instruct",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("qwen_action_eval_results.csv"),
    )
    args = parser.parse_args()


    video_files = sorted(args.outputs_dir.glob("*.mp4"))
    if not video_files:
        raise FileNotFoundError(f"No mp4 files found in {args.outputs_dir}")

    completed_videos = load_completed_videos(args.output_csv)
    print(f"Found {len(completed_videos)} already evaluated videos.")

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model,
        torch_dtype="auto",
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(args.model)

    rows = []
    for video_path in video_files:
        if video_path.name in completed_videos:
            print(f"Skipping {video_path.name}: already evaluated")
            continue

        txt_path = video_path.with_suffix(".txt")
        if not txt_path.exists():
            print(f"Skipping {video_path.name}: missing txt file")
            continue

        label = read_label(txt_path)
        if label not in LABEL_TO_QUESTION:
            print(f"Skipping {video_path.name}: unknown label {label}")
            continue

        question = LABEL_TO_QUESTION[label]
        result = evaluate_video(model, processor, video_path, question)

        row = {
            "video_file": video_path.name,
            "txt_file": txt_path.name,
            "label_name": label,
            "question": question,
            "result": result.get("label", ""),
            "reason": result.get("reason", ""),
            "observed_action": result.get("observed_action", ""),
            "raw_output": result.get("raw_output", ""),
        }
        rows.append(row)
        print(f"{video_path.name}: {row['result']} | {row['reason']}")

    existing_rows = load_existing_rows(args.output_csv)
    all_rows = existing_rows + rows

    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "video_file",
                "txt_file",
                "label_name",
                "question",
                "result",
                "reason",
                "observed_action",
                "raw_output",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)


    print(f"\nSaved results to {args.output_csv}")


if __name__ == "__main__":
    main()