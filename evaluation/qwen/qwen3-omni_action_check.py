import argparse
import csv
import json
import re
from pathlib import Path

import torch
# from transformers import AutoProcessor, AutoModelForCausalLM
from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor
from qwen_omni_utils import process_mm_info


LABEL_TO_QUESTION = {
    "head_nod": "Does the person nod their head?",
    "head_shake": "Does the person shake their head side to side?",
    "shrug": "Does the person shrug?",
    "hand_wave": "Does the person wave one hand?",
    "pointing": "Does the person point with one hand?",
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
    "stomp": "Does the person stomp?",
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

SPEECH_LABELS = {
    "yeah", "help", "no", "okay", "right", "wow", "oh",
    "thanks", "sorry", "i_dont_know"
}

SYSTEM_PROMPT = """You are a strict video behavior evaluator.

Your job:
- Watch the video and listen to the audio.
- Judge only whether the target behavior is clearly present.

Rules for action labels:
- Focus only on whether the target action is clearly performed.
- Ignore camera angle, framing, background, room type, and scene details.
- Ignore whether the person faces the camera.
- If the action is missing, different, or ambiguous, answer "no".

Rules for speech labels:
- Focus on whether the target utterance is actually spoken in the audio.
- Prioritize AUDIO over visual cues such as lip movement.
- Do not guess from mouth shape alone.
- If the utterance is missing, different, partial, unclear, too noisy, or ambiguous, answer "no".

General:
- Be conservative.
- Return JSON only.

Return JSON only in this format:
{
  "label": "yes" or "no",
  "reason": "short explanation",
  "observed_behavior": "short description"
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


def make_user_text(label: str, question: str) -> str:
    if label in SPEECH_LABELS:
        return f"""Question: {question}

Determine whether the target utterance is actually spoken in the video's audio.
Use the audio as the primary evidence.
Return JSON only.
"""
    return f"""Question: {question}

Determine whether the target action is clearly performed in the video.
Use visual evidence primarily, but you may also use audio if helpful.
Return JSON only.
"""


def move_inputs_to_device(inputs, model):
    moved = {}
    for k, v in inputs.items():
        if hasattr(v, "to"):
            moved[k] = v.to(model.device)
        else:
            moved[k] = v

    for k, v in list(moved.items()):
        if hasattr(v, "dtype") and torch.is_floating_point(v):
            moved[k] = v.to(model.dtype)

    return moved


def evaluate_video(
    model,
    processor,
    video_path: Path,
    label: str,
    question: str,
    fps: float = 2.0,
    use_audio_in_video: bool = True,
) -> dict:
    user_text = make_user_text(label, question)

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
        add_generation_prompt=True,
        tokenize=False,
    )

    audios, images, videos = process_mm_info(
        messages,
        use_audio_in_video=use_audio_in_video,
    )

    inputs = processor(
        text=text,
        audio=audios,
        images=images,
        videos=videos,
        return_tensors="pt",
        padding=True,
        fps=fps,
        use_audio_in_video=use_audio_in_video,
    )

    inputs = move_inputs_to_device(inputs, model)

    with torch.inference_mode():
        # output_ids = model.generate(
        #     **inputs,
        #     max_new_tokens=256,
        #     do_sample=False,
        #     use_audio_in_video=use_audio_in_video,
        #     return_audio=False,
        # )

        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            use_audio_in_video=use_audio_in_video,
            return_audio=False,
        )

    if isinstance(output_ids, tuple):
        output_ids = output_ids[0]

    trimmed_ids = []
    for in_ids, out_ids in zip(inputs["input_ids"], output_ids):
        trimmed_ids.append(out_ids[len(in_ids):])

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
        default="Qwen/Qwen3-Omni-30B-A3B-Instruct",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("/home/coder/T2V_Gen/qwen/dev_outputs/seed421-qwen3_omni_behavior_eval_results-fps6.csv"),
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=4.0,
        help="Video sampling fps for visual frames",
    )
    parser.add_argument(
        "--disable-audio-in-video",
        action="store_true",
        help="Disable using audio from video. Not recommended for speech labels.",
    )
    args = parser.parse_args()

    use_audio_in_video = not args.disable_audio_in_video

    video_files = sorted(args.outputs_dir.glob("*.mp4"))
    if not video_files:
        raise FileNotFoundError(f"No mp4 files found in {args.outputs_dir}")

    completed_videos = load_completed_videos(args.output_csv)
    print(f"Found {len(completed_videos)} already evaluated videos.")

    # model = AutoModelForCausalLM.from_pretrained(
    #     args.model,
    #     torch_dtype="auto",
    #     device_map="auto",
    #     trust_remote_code=True,
    # )
    model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
        args.model,
        dtype="auto",
        device_map="auto",
        enable_audio_output=False,
    )

    processor = Qwen3OmniMoeProcessor.from_pretrained(args.model)

    # processor = AutoProcessor.from_pretrained(
    #     args.model,
    #     trust_remote_code=True,
    # )

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

        try:
            result = evaluate_video(
                model=model,
                processor=processor,
                video_path=video_path,
                label=label,
                question=question,
                fps=args.fps,
                use_audio_in_video=use_audio_in_video,
            )
            result_label = result.get("label", "")
            reason = result.get("reason", "")
            observed_behavior = result.get("observed_behavior", "")
            raw_output = result.get("raw_output", "")
        except Exception as e:
            result_label = "error"
            reason = str(e)
            observed_behavior = ""
            raw_output = ""

        row = {
            "video_file": video_path.name,
            "txt_file": txt_path.name,
            "label_name": label,
            "question": question,
            "result": result_label,
            "reason": reason,
            "observed_behavior": observed_behavior,
            "raw_output": raw_output,
            "label_type": "speech" if label in SPEECH_LABELS else "action",
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
                "label_type",
                "question",
                "result",
                "reason",
                "observed_behavior",
                "raw_output",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved results to {args.output_csv}")


if __name__ == "__main__":
    main()