#!/usr/bin/env python3
"""In-process vLLM judge server for GPUs in EXCLUSIVE_PROCESS compute mode.

`vllm serve` forks an EngineCore child that cannot get the GPU when the parent already
holds a CUDA context (SCC A6000 nodes). This server loads `LLM()` in ONE process
(VLLM_ENABLE_V1_MULTIPROCESSING=0) and exposes a tiny HTTP API that the evaluation
pipeline calls through `local_judge.py` (--judge-backend local).

Requests arriving within a short window are batched into one `llm.chat()` call, so
6 shard processes hitting the server concurrently get real batching.

Start (screen, GPU session):
  module load miniconda ffmpeg/8.1 gcc/13.2.0        # gcc >= 11 for torch.compile (-std=c++20)
  conda activate /projectnb/ivc-ml/youngsun/conda_envs/vllm020
  export HF_HOME=/scratch/youngsun/hf
  VLLM_ENABLE_V1_MULTIPROCESSING=0 CUDA_VISIBLE_DEVICES=1 python local_judge_server.py --port 8010

Check:  curl -s localhost:8010/health
POST /judge  {"system": str, "user": str, "video": "/abs/path.mp4" | null, "schema": dict | null,
              "use_audio": bool, "max_tokens": int, "thinking": bool, "reasoning_budget": int}
  -> {"text": final answer text, "reasoning_chars": int, "tokens": int, "batch": int, "sec": float}
"""
import argparse, json, os, queue, threading, time, traceback
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-FP8")
ap.add_argument("--port", type=int, default=8010)
ap.add_argument("--max-model-len", type=int, default=65536)
ap.add_argument("--gpu-mem", type=float, default=0.92)
ap.add_argument("--fps", type=float, default=2.0)
ap.add_argument("--num-frames", type=int, default=128)
ap.add_argument("--max-batch", type=int, default=16)
ap.add_argument("--window-sec", type=float, default=0.5, help="collect requests for this long before one llm.chat()")
ap.add_argument("--media-root", default="/projectnb/ivc-ml/youngsun")
ap.add_argument("--reasoning-parser", default="nemotron_v3")
ap.add_argument("--no-schema", action="store_true", help="never use structured outputs; parse JSON from text")
ap.add_argument("--enforce-eager", action="store_true",
                help="disable CUDA graphs (needed on Ampere + FP8/Marlin: 'Workspace is locked ... marlin_locks' with batches)")
ap.add_argument("--log", default=None)
args = ap.parse_args()

os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
from vllm import LLM, SamplingParams
try:
    from vllm.sampling_params import StructuredOutputsParams
except Exception:  # older name
    StructuredOutputsParams = None

print(f"[server] loading {args.model} ...", flush=True)
t0 = time.time()
llm_kwargs = dict(
    model=args.model, trust_remote_code=True, max_model_len=args.max_model_len,
    kv_cache_dtype="fp8", gpu_memory_utilization=args.gpu_mem,
    media_io_kwargs={"video": {"fps": args.fps, "num_frames": args.num_frames}},
    allowed_local_media_path=args.media_root, limit_mm_per_prompt={"video": 1},
    enforce_eager=args.enforce_eager,
)
if args.reasoning_parser:
    # lets structured outputs apply AFTER the reasoning block (otherwise the schema would forbid thinking)
    llm_kwargs["structured_outputs_config"] = {"reasoning_parser": args.reasoning_parser}
try:
    llm = LLM(**llm_kwargs)
except TypeError as e:
    print(f"[server] LLM() rejected structured_outputs_config ({e}); retrying without it", flush=True)
    llm_kwargs.pop("structured_outputs_config", None)
    llm = LLM(**llm_kwargs)
print(f"[server] model ready in {time.time() - t0:.0f}s", flush=True)

LOGF = open(args.log, "a") if args.log else None


def log(msg):
    line = f"{time.strftime('%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    if LOGF:
        LOGF.write(line + "\n"); LOGF.flush()


class Req(BaseModel):
    system: str = ""
    user: str
    video: str | None = None
    schema: dict | None = None
    use_audio: bool = True
    max_tokens: int = 8192
    thinking: bool = True
    reasoning_budget: int = 8192
    temperature: float = 0.0


def to_messages(r: Req):
    content = []
    if r.video:
        content.append({"type": "video_url", "video_url": {"url": Path(r.video).resolve().as_uri()}})
    content.append({"type": "text", "text": r.user})
    msgs = []
    if r.system:
        msgs.append({"role": "system", "content": r.system})
    msgs.append({"role": "user", "content": content})
    return msgs


def sampling_for(r: Req, with_schema: bool):
    kw = dict(max_tokens=r.max_tokens, temperature=r.temperature, top_p=1.0 if r.temperature == 0 else 0.95, seed=42)
    if with_schema and r.schema and StructuredOutputsParams is not None and not args.no_schema:
        kw["structured_outputs"] = StructuredOutputsParams(json=r.schema)
    return SamplingParams(**kw)


def split_reasoning(out):
    """vLLM offline output: reasoning may sit in out.outputs[0].reasoning (0.11+) or stay inline."""
    o = out.outputs[0]
    reasoning = getattr(o, "reasoning", None) or getattr(o, "reasoning_content", None) or ""
    text = o.text or ""
    if not reasoning and "</think>" in text:
        reasoning, text = text.split("</think>", 1)
    return reasoning, text.strip(), len(o.token_ids)


# ------------------------------------------------------------------ batching worker
Q: "queue.Queue[tuple[Req, threading.Event, dict]]" = queue.Queue()


def run_batch(items, with_schema):
    reqs = [it[0] for it in items]
    msgs = [to_messages(r) for r in reqs]
    sps = [sampling_for(r, with_schema) for r in reqs]
    # per-batch kwargs must be uniform: group by (use_audio, thinking, budget) before calling
    r0 = reqs[0]
    outs = llm.chat(msgs, sps, use_tqdm=False,
                    mm_processor_kwargs={"use_audio_in_video": r0.use_audio},
                    chat_template_kwargs={"enable_thinking": r0.thinking, "reasoning_budget": r0.reasoning_budget})
    return outs


def worker():
    while True:
        first = Q.get()
        items = [first]
        t_end = time.time() + args.window_sec
        while len(items) < args.max_batch and time.time() < t_end:
            try:
                items.append(Q.get(timeout=max(0.0, t_end - time.time())))
            except queue.Empty:
                break
        # group by uniform kwargs
        groups = {}
        for it in items:
            r = it[0]
            groups.setdefault((r.use_audio, r.thinking, r.reasoning_budget), []).append(it)
        for key, grp in groups.items():
            t0 = time.time()
            try:
                outs = run_batch(grp, with_schema=True)
            except Exception as e:
                log(f"[batch] structured call failed ({type(e).__name__}: {e}); retrying without schema")
                try:
                    outs = run_batch(grp, with_schema=False)
                except Exception as e2:
                    err = f"{type(e2).__name__}: {e2}\n{traceback.format_exc()}"
                    for _, ev, box in grp:
                        box["error"] = err; ev.set()
                    continue
            dt = time.time() - t0
            for (r, ev, box), out in zip(grp, outs):
                reasoning, text, ntok = split_reasoning(out)
                box.update(text=text, reasoning_chars=len(reasoning), tokens=ntok, batch=len(grp), sec=round(dt, 1))
                ev.set()
            log(f"[batch] n={len(grp)} audio={key[0]} think={key[1]} {dt:.0f}s "
                f"tokens={[len(o.outputs[0].token_ids) for o in outs]}")


threading.Thread(target=worker, daemon=True).start()

# ------------------------------------------------------------------ HTTP
app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True, "model": args.model, "fps": args.fps, "num_frames": args.num_frames, "queue": Q.qsize()}


@app.post("/judge")
def judge(r: Req):
    if r.video and not Path(r.video).exists():
        return {"error": f"video not found: {r.video}"}
    ev, box = threading.Event(), {}
    Q.put((r, ev, box))
    ev.wait()
    return box


uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
