#!/usr/bin/env python3
"""Qwen3-VL-8B action timestamps, reproducing sa004/QWEN_timestamps (10/30). Run in the vllm020 env on a GPU. No Gemini calls.

Settings recovered from the release (README + the `prompt` / `model` / `fps` fields of its JSON files):
  model Qwen/Qwen3-VL-8B-Instruct; video frames only (no audio) at 2 fps, at most 448x448 pixels per frame;
  actions = the non-speech actions of the item prompt, alphabetical, no counts / order; greedy decoding, <= 1024 new tokens;
  a reply with >= 20 spans for one action = repetition loop -> re-run once with repetition_penalty 1.1.
  Prompt (HD-EPIC wording), byte-identical to the stored `prompt` fields:
"""
from t2av_eval import paths as _P
import os
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_v] = "4"
import argparse, importlib.util, json, sys
from pathlib import Path

Q = Path((str(_P.DATA) + "/tools/qwen_timestamps_1030/qwen_timestamps_share"))
OUT = Path((str(_P.DATA) + "/tools/qwen_timestamps_1030/move_1030"))
MODEL = "Qwen/Qwen3-VL-8B-Instruct"
FPS, MAX_PIX, MAX_NEW, LOOP = 2.0, 448 * 448, 1024, 20
MAX_FRAMES = 52     # Qwen3-VL's video `longest_edge` is a TOTAL pixel budget over all frames: 448x448 per frame x (25 s x 2 fps + margin)
HEAD = {"hdepic": "Watch this first-person kitchen video carefully.", "generated": "Watch this video carefully."}


def prompt_for(actions, kind="hdepic"):
    return (f"{HEAD[kind]}\n\nFor each action in the list below, find EVERY time it happens in the video. An action may happen zero, "
            "one, or several times. Report the start and end time of each occurrence in seconds from the start of the video.\n\n"
            "Actions:\n" + "\n".join(f"- {a}" for a in actions) + "\n\nAnswer with JSON only, in exactly this form, using the action names "
            'exactly as written:\n{"<action>": [[start_seconds, end_seconds], ...], ...}\nUse an empty list for an action that does not happen.')


def parse_qwen():
    spec = importlib.util.spec_from_file_location("parse_qwen", Q / "parse_qwen.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Runner:
    def __init__(self):
        import torch
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
        self.torch = torch
        self.proc = AutoProcessor.from_pretrained(MODEL)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16).to("cuda").eval()

    def reply(self, video, text, rep=1.0):
        msgs = [{"role": "user", "content": [{"type": "video", "video": str(video)}, {"type": "text", "text": text}]}]
        inp = self.proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt",
                                            processor_kwargs={"fps": FPS, "do_sample_frames": True,
                                                              "size": {"longest_edge": MAX_PIX * MAX_FRAMES, "shortest_edge": 4096}}).to("cuda")
        if not getattr(self, "_shown", False):          # log what the model actually receives, once
            self._shown = True
            vg = inp.get("video_grid_thw")
            print(f"[qwen] video_grid_thw {vg.tolist() if vg is not None else None}; input tokens {inp['input_ids'].shape[1]}", flush=True)
        with self.torch.no_grad():
            out = self.model.generate(**inp, max_new_tokens=MAX_NEW, do_sample=False, repetition_penalty=rep)
        return self.proc.batch_decode(out[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]


def run_one(R, PQ, video, actions, kind="hdepic"):
    text = prompt_for(actions, kind)
    rec = dict(model=MODEL, fps=FPS, actions=actions, prompt=text)
    r = R.reply(video, text)
    spans, err = PQ.parse(r, actions)
    if err.startswith("repetition loop"):
        r = R.reply(video, text, rep=1.1)
        rec["repetition_penalty"] = 1.1
    rec["reply"] = r
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["calib", "move"])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--reverse", action="store_true", help="move: process items from the end (second GPU job; files already written are skipped)")
    a = ap.parse_args()
    PQ = parse_qwen()
    R = Runner()
    if a.stage == "calib":
        # re-run release items and compare spans with the stored replies
        import csv
        idx = [r for r in csv.DictReader(open(Q / "index.csv")) if r["set"] == "hdepic" and r["variant"] == "original" and r["usable"] == "yes"][: a.n]
        res = []
        for row in idx:
            old = json.load(open(Q / row["qwen_file"]))
            vid = Path((str(_P.DATA) + "/real_av/eval/hdepic_medium_shard0")).parent
            mp4 = next(Path((str(_P.DATA) + "/real_av/eval")).glob(f"hdepic_medium_shard*/{row['video']}"))
            assert prompt_for(old["actions"]) == old["prompt"], "prompt text differs from the release"
            rec = run_one(R, PQ, mp4, old["actions"])
            s_old, _ = PQ.parse(old["reply"], old["actions"])
            s_new, e_new = PQ.parse(rec["reply"], old["actions"])
            res.append(dict(item=row["qwen_file"], old=s_old, new=s_new, err=e_new))
            print(json.dumps(res[-1]), flush=True)
        OUT.mkdir(parents=True, exist_ok=True)
        json.dump(res, open(OUT / "calib.json", "w"), indent=1)
        return
    # move set: v3 test hdmove TCC rows (count_off + original); one run per clip (same frames, same action list)
    items = {x["item_id"]: x for x in json.load(open((str(_P.DATA) + "/real_av/eval/hdepic_move_prompts.json")))}
    man = [json.loads(l) for l in open(_P.INPUTS / "evaluation/ablation/gepa_stage2/manifests_v3/test.jsonl")]
    rows = [m for m in man if m["source"] == "hdmove" and m["axis"] == "TCC"]
    if a.reverse:
        rows = rows[::-1]
    (OUT / "hdepicmove").mkdir(parents=True, exist_ok=True)
    done = {}
    for m in rows:
        it = items[m["item_id"]]
        acts = sorted({e["action"] for e in it["events"] if e.get("modality") != "speech"})
        mp4 = next(Path((str(_P.DATA) + "/real_av/eval")).glob(f"hdepic_move_shard*/{m['item_id']}/{m['item_id']}_v1_raw.mp4"))
        key = (str(mp4.resolve()), tuple(acts))
        f = OUT / "hdepicmove" / f"{m['item_id']}.json"
        if f.exists():                                     # written by this or the other GPU job
            continue
        if key not in done:
            done[key] = run_one(R, PQ, mp4, acts)
        rec = {**done[key], "video": m["split_key"], "relpath": f"{m['item_id']}/{m['item_id']}_v1_raw.mp4", "source_video": key[0]}
        json.dump(rec, open(f, "w"), indent=1)
        print(f"[move] {m['item_id']} {m['variant']}", flush=True)


if __name__ == "__main__":
    main()
