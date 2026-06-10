# LTX-2.3 Environment Reproduction Notes

**Documented by:** Claude Code (automated inspection)
**Date documented:** 2026-05-25
**Working project path:** `/home/coder/T2V_Gen/LTX-2/`

---

## 1. LTX-2.3 Model / Version

| Field | Value |
|---|---|
| Model family | LTX-2 (Lightricks) |
| Model variant | `ltx-2.3-22b-dev` |
| Internal model version (safetensors metadata) | `2.3.0` |
| Checkpoint filename | `ltx-2.3-22b-dev.safetensors` |
| Checkpoint size | ~43 GB |
| Local checkpoint path | `/home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors` |
| HuggingFace repo | [`Lightricks/LTX-2.3`](https://huggingface.co/Lightricks/LTX-2.3) |
| Direct download URL | `https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-dev.safetensors` |
| License | LTX-2 Community License (see safetensors metadata; commercial use requires a paid agreement) |

**Commands used to verify:**
```bash
ls -lh /home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors
python3 -c "
import struct, json
with open('/home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors','rb') as f:
    header_len = struct.unpack('<Q', f.read(8))[0]
    header = json.loads(f.read(header_len))
    print(json.dumps(header.get('__metadata__', {}).get('model_version'), indent=2))
"
```

### Model Architecture (from safetensors `config` metadata)

- **Transformer:** `AVTransformer3DModel`, 48 layers, 32 attention heads, head dim 128, dual-stream audio-video with bidirectional cross-modal attention
- **Video VAE:** `CausalVideoAutoencoder`, 128 latent channels
- **Audio VAE:** stereo, 16 kHz, 8 latent channels
- **Vocoder:** HiFi-GAN-style neural vocoder with bandwidth extension (16 kHz → 48 kHz)

---

## 2. Python Version and Conda Environment

| Field | Value |
|---|---|
| Conda distribution | Miniforge3 |
| Conda version | 25.9.1 |
| Conda binary | `/home/coder/miniforge3/bin/conda` |
| **Active environment name** | **`ltx23`** |
| Environment prefix | `/home/coder/miniforge3/envs/ltx23` |
| Python version | **3.10.20** |
| Python binary | `/home/coder/miniforge3/envs/ltx23/bin/python` |

**Other available conda environments on this machine (not used for LTX-2.3):**
`base`, `AVGen`, `eval_agent`, `flux2`, `qwen_edit`, `science-t2i`, `spar`, `takehome`, `vabench`, `wan2p2`

**Commands used to verify:**
```bash
/home/coder/miniforge3/bin/conda info --envs
/home/coder/miniforge3/envs/ltx23/bin/python --version
```

**To activate the environment:**
```bash
conda activate ltx23
# or
source /home/coder/miniforge3/bin/activate ltx23
```

---

## 3. LTX Core Packages (Editable Installs from GitHub)

Both LTX packages are installed as **editable installs** directly from the local git clone:

| Package | Version | Editable Source |
|---|---|---|
| `ltx-core` | 1.1.3 | `/home/coder/T2V_Gen/LTX-2/github/packages/ltx-core` |
| `ltx-pipelines` | 1.1.3 | `/home/coder/T2V_Gen/LTX-2/github/packages/ltx-pipelines` |

**GitHub repository:** `https://github.com/Lightricks/LTX-2.git`
**Pinned git commit:** `1799988521d5e9725a4fbd4533d0cc12f07c07ed`
(Latest commit message: *"Merge pull request #212 from Lightricks/pr-2026-05-11-a904df5"*)

**To reproduce the editable install:**
```bash
git clone https://github.com/Lightricks/LTX-2.git /home/coder/T2V_Gen/LTX-2/github
cd /home/coder/T2V_Gen/LTX-2/github
git checkout 1799988521d5e9725a4fbd4533d0cc12f07c07ed

# Editable install
pip install -e packages/ltx-core
pip install -e packages/ltx-pipelines
```

**pip freeze entries for these packages:**
```
-e git+https://github.com/Lightricks/LTX-2.git@1799988521d5e9725a4fbd4533d0cc12f07c07ed#egg=ltx_core&subdirectory=packages/ltx-core
-e git+https://github.com/Lightricks/LTX-2.git@1799988521d5e9725a4fbd4533d0cc12f07c07ed#egg=ltx_pipelines&subdirectory=packages/ltx-pipelines
```

---

## 4. Key Python Package Versions (Version-Sensitive Dependencies)

All packages installed in the `ltx23` conda environment. Verified with:
```bash
/home/coder/miniforge3/envs/ltx23/bin/pip list
/home/coder/miniforge3/envs/ltx23/bin/pip show <package>
```

### PyTorch and CUDA

| Package | Version | Notes |
|---|---|---|
| `torch` | `2.7.1+cu128` | Built against CUDA 12.8; install from PyTorch index |
| `torchaudio` | `2.7.1+cu128` | Must match torch version |
| `torchvision` | `0.22.1+cu128` | Must match torch version |
| `triton` | `3.3.1` | Installed as torch dependency |

**Install command (from `ltx-core` pyproject.toml):**
```bash
# PyTorch index for CUDA 12.9 (cu129) wheel source as specified in pyproject.toml:
# [[tool.uv.index]] url = "https://download.pytorch.org/whl/cu129"
# Actual installed version is cu128; install with:
pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
```

### Diffusion / Inference Framework

| Package | Version |
|---|---|
| `diffusers` | `0.37.1` |
| `transformers` | `4.57.3` |
| `accelerate` | `1.13.0` |
| `safetensors` | `0.7.0` |
| `huggingface_hub` | `0.36.2` |
| `hf-xet` | `1.5.0` |
| `tokenizers` | `0.22.2` |

### Text / Tokenization

| Package | Version |
|---|---|
| `sentencepiece` | `0.2.1` |
| `protobuf` | `4.25.9` |
| `ftfy` | `6.3.1` |

### Google / Gemini / GenAI SDK

| Package | Version | Notes |
|---|---|---|
| `google-genai` | `2.0.0` | GenAI Python SDK (google-genai, not google-generativeai) |
| `google-auth` | `2.49.1` | Authentication library |

> **Note:** The package installed is `google-genai` (the new unified SDK), **not** `google-generativeai`. These are separate packages.

### Numerical / Scientific

| Package | Version |
|---|---|
| `numpy` | `2.2.6` |
| `scipy` | `1.15.3` |
| `einops` | `0.8.2` |
| `jax` | `0.6.2` |
| `jaxlib` | `0.6.2` |

### Audio / Video I/O

| Package | Version |
|---|---|
| `av` | `17.0.0` |
| `torchaudio` | `2.7.1+cu128` |
| `librosa` | `0.11.0` |
| `faster-whisper` | `1.2.1` |
| `ctranslate2` | `4.7.2` |
| `decord` | `0.6.0` |
| `soundfile` | `0.13.1` |
| `moviepy` | `2.2.1` |
| `imageio` | `2.37.3` |
| `imageio-ffmpeg` | `0.6.0` |

### Image Processing / Vision

| Package | Version |
|---|---|
| `pillow` | `11.3.0` |
| `opencv-python` | `4.13.0.92` |
| `opencv-contrib-python` | `4.13.0.92` |
| `OpenImageIO` | `3.1.13.1` |
| `mediapipe` | `0.10.14` |

### ONNX / Quantization

| Package | Version |
|---|---|
| `onnxruntime` | `1.23.2` |

### ML Utilities

| Package | Version |
|---|---|
| `tqdm` | `4.67.3` |
| `pydantic` | `2.12.5` |
| `packaging` | `26.2` |

### API Clients (also installed)

| Package | Version | Notes |
|---|---|---|
| `openai` | `2.30.0` | OpenAI Python SDK |
| `runwayml` | `4.14.0` | RunwayML Python SDK |

### CUDA / NVIDIA Runtime Packages

| Package | Version |
|---|---|
| `cuda-bindings` | `13.2.0` |
| `cuda-pathfinder` | `1.5.4` |
| `cuda-toolkit` | `13.0.2` |
| `nvidia-cublas-cu12` | `12.8.3.14` |
| `nvidia-cudnn-cu12` | `9.7.1.26` |
| `nvidia-nccl-cu12` | `2.26.2` |
| `nvidia-nvjitlink-cu12` | `12.8.61` |

---

## 5. API Clients and SDKs

| SDK | Version | Purpose |
|---|---|---|
| `google-genai` | `2.0.0` | Google GenAI SDK (prompt enhancement, video understanding) |
| `openai` | `2.30.0` | OpenAI API client |
| `runwayml` | `4.14.0` | RunwayML API client |

> **Note on `google-genai` vs `google-generativeai`:** The installed package is `google-genai==2.0.0`. This is the **new unified Google GenAI SDK** (`from google import genai`), not the older `google-generativeai` package. Do **not** install `google-generativeai` — use `google-genai` instead.

---

## 6. Gemma / Google Model Information

### Local Gemma Checkpoint

| Field | Value |
|---|---|
| Model name | Gemma 3 12B Instruction-Tuned (QAT) |
| HuggingFace model ID | `google/gemma-3-12b-it-qat-q4_0-unquantized` |
| Architecture | `Gemma3ForConditionalGeneration` (multimodal: text + SigLIP vision) |
| Local path | `/home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it/` |
| Model type | `gemma3` (text: `gemma3_text`, vision: `siglip_vision_model`) |
| Text config: hidden size | 3840 |
| Text config: num layers | 48 |
| Text config: num heads | 16 |
| Text config: max position | 131072 |
| Vision config: image size | 896, patch size 14, 27 layers |
| Torch dtype | `bfloat16` |
| Config created with transformers version | `4.52.0.dev0` |
| License | Gemma license (requires accepting terms on HuggingFace) |

**HuggingFace download metadata files are cached at:**
`/home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it/.cache/huggingface/download/`

**To download Gemma locally:**
```bash
# Requires accepting the Gemma license on HuggingFace first
huggingface-cli download google/gemma-3-12b-it-qat-q4_0-unquantized \
  --local-dir /home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it
```

> **Important:** The model stored in `checkpoints/gemma-3-12b-it/` is the **unquantized** bfloat16 version of the QAT checkpoint. The README in the checkpoint dir notes that quantization to Q4_0 is recommended to save memory, but this setup uses the unquantized weights.

---

## 7. HuggingFace Model IDs, Cache Paths, and Config Files

### HuggingFace Model IDs

| Model | HuggingFace ID |
|---|---|
| LTX-2.3 checkpoint | `Lightricks/LTX-2.3` |
| Gemma text encoder | `google/gemma-3-12b-it-qat-q4_0-unquantized` |
| IC-LoRA Union Control | `Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control` |
| IC-LoRA Motion Track | `Lightricks/LTX-2.3-22b-IC-LoRA-Motion-Track-Control` |
| IC-LoRA HDR | `Lightricks/LTX-2.3-22b-IC-LoRA-HDR` |
| IC-LoRA LipDub | `Lightricks/LTX-2.3-22b-IC-LoRA-LipDub` |

### Local Checkpoint Layout

```
/home/coder/T2V_Gen/LTX-2/checkpoints/
├── ltx-2.3-22b-dev.safetensors          # 43 GB — main model checkpoint
├── .cache/huggingface/
│   └── download/
│       └── ltx-2.3-22b-dev.safetensors.metadata   # HF download tracking
└── gemma-3-12b-it/                       # Gemma text encoder (local copy)
    ├── config.json
    ├── tokenizer.json
    ├── tokenizer.model
    ├── tokenizer_config.json
    ├── special_tokens_map.json
    ├── added_tokens.json
    ├── preprocessor_config.json
    ├── processor_config.json
    ├── chat_template.json
    ├── generation_config.json
    ├── model.safetensors.index.json
    ├── model-00001-of-00005.safetensors
    ├── model-00002-of-00005.safetensors
    ├── model-00003-of-00005.safetensors
    ├── model-00004-of-00005.safetensors
    ├── model-00005-of-00005.safetensors
    └── .cache/huggingface/download/      # HF download tracking metadata
```

### HuggingFace Cache Environment

| Variable | Value |
|---|---|
| `HF_HOME` | Not set (using default `~/.cache/huggingface`) |
| `TRANSFORMERS_CACHE` | Not set |
| `HUGGINGFACE_HUB_CACHE` | Not set |

The LTX-2.3 and Gemma checkpoints are stored **directly in the project directory**, not in the default HF cache. The `.cache/huggingface/` subdirectories inside the checkpoint folders contain HuggingFace download tracking files (commit hashes and etags), not model weights.

---

## 8. Main Entry Point Scripts

### Primary Generation Script

**File:** `/home/coder/T2V_Gen/LTX-2/generate_ltx23_dev_t2av.py`

This is the main orchestration script for the T2AV (Text-to-Audio-Video) generation pipeline. It:
1. Reads prompts from a JSON file
2. Invokes `python -m ltx_pipelines.ti2vid_one_stage` as a subprocess for each item/variant
3. Writes metadata `.txt` files alongside each output `.mp4`

**Default parameters hardcoded in the script:**
```python
DEFAULT_PYTHON_BIN  = "/home/coder/miniforge3/envs/ltx23/bin/python"
DEFAULT_LTX_REPO    = "/home/coder/T2V_Gen/LTX-2"
DEFAULT_CHECKPOINT  = "/home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors"
DEFAULT_GEMMA_ROOT  = "/home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it"
DEFAULT_OUTPUT_ROOT = "/home/coder/T2V_Gen/LTX-2/outputs"
DEFAULT_PROMPT_JSON = "/home/coder/T2V_Gen/prompt_gen/output/4-comb_temporal_selected_specs_prompts.json"

# Generation defaults
width=768, height=512, num_frames=121, frame_rate=24.0
base_seed=42, variants=3, seed_mode="adjacent"
```

**Invocation example:**
```bash
conda activate ltx23
python /home/coder/T2V_Gen/LTX-2/generate_ltx23_dev_t2av.py \
  --prompt-json /path/to/prompts.json \
  --output-root /home/coder/T2V_Gen/LTX-2/outputs \
  --width 768 --height 512 --num-frames 121 --frame-rate 24 \
  --base-seed 42 --variants 3
```

**Dry-run mode:**
```bash
python generate_ltx23_dev_t2av.py --dry-run
```

### Underlying CLI (called as subprocess)

```
python -m ltx_pipelines.ti2vid_one_stage \
  --checkpoint-path <safetensors> \
  --gemma-root <gemma dir> \
  --prompt "<text>" \
  --output-path <mp4> \
  --width 768 --height 512 \
  --num-frames 121 --frame-rate 24 \
  --seed <int>
```

**Source:** `/home/coder/T2V_Gen/LTX-2/github/packages/ltx-pipelines/src/ltx_pipelines/ti2vid_one_stage.py`

### Pipeline Used

`TI2VidOneStagePipeline` — single-stage text/image-to-video, generates at target resolution in one diffusion pass with CFG. Default: 30 inference steps.

Other available pipelines (not used by this script):
- `TI2VidTwoStagesPipeline` — production quality, 2× upsampling
- `DistilledPipeline` — fastest, 8 fixed sigma steps
- `A2VidPipelineTwoStage` — audio-conditioned
- `KeyframeInterpolationPipeline`, `ICLoraPipeline`, `LipDubPipeline`, `RetakePipeline`

### Evaluation / Log Outputs

Multi-GPU runs were launched with 4 parallel processes, each assigned a range of items:
```
logs/gpu0_0_9.log    # GPU 0, items 0–9
logs/gpu1_10_19.log  # GPU 1, items 10–19
logs/gpu2_20_29.log  # GPU 2, items 20–29
logs/gpu3_30_39.log  # GPU 3, items 30–39
```

Output files follow the pattern:
```
outputs/<item_id>/<item_id>_v<variant>_raw.mp4
outputs/<item_id>/<item_id>_v<variant>_raw.txt
```

---

## 9. Environment Variables Referenced

| Variable | Where Referenced | Required? | Notes |
|---|---|---|---|
| `HF_TOKEN` | Not found in scripts | Optional | May be needed by `huggingface-cli` for gated models (Gemma) |
| `HUGGING_FACE_HUB_TOKEN` | Not found in scripts | Optional | Alternative HF token env var |
| `LOCAL_RANK` | `ltx-trainer/__init__.py` | No (trainer only) | Auto-set by `torchrun` for multi-GPU training |
| `OPENCV_IO_ENABLE_OPENEXR` | `ltx-pipelines/utils/media_io.py` | No | Set internally to `"1"` when writing EXR files; not needed externally |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Not found in LTX-2 scripts | Possibly needed | May be required if `google-genai` SDK is used for prompt enhancement elsewhere in the project |

> **Secret values are not recorded here.** To set a HuggingFace token:
> ```bash
> export HF_TOKEN=<your_token_here>
> # or log in interactively:
> huggingface-cli login
> ```

---

## 10. Hardware Environment

| Component | Value |
|---|---|
| GPU count | 4 |
| GPU model | NVIDIA A100-SXM4-80GB (SXM4) |
| GPU memory per card | 80 GB |
| CUDA driver version | 12.4 |
| CUDA toolkit on system | `/usr/local/cuda-12.4` (via `nvcc`) |
| PyTorch CUDA build | cu128 (12.8 — bundled with torch wheel) |
| OS | Amazon Linux 2 (kernel `5.10.230-223.885.amzn2.x86_64`) |

> **Note on CUDA version mismatch:** System CUDA is 12.4, but `torch 2.7.1+cu128` bundles CUDA 12.8 runtime libraries. This is intentional — PyTorch wheels bundle their own CUDA runtime, so the system CUDA driver only needs to be ≥ the minimum supported version (which 12.4 satisfies for cu128 wheels).

---

## 11. Reproduction Checklist

### Step 1 — Clone the LTX-2 GitHub Repository

```bash
git clone https://github.com/Lightricks/LTX-2.git /home/coder/T2V_Gen/LTX-2/github
cd /home/coder/T2V_Gen/LTX-2/github
git checkout 1799988521d5e9725a4fbd4533d0cc12f07c07ed
```

### Step 2 — Create the Conda Environment

```bash
conda create -n ltx23 python=3.10.20 -y
conda activate ltx23
```

### Step 3 — Install PyTorch (CUDA 12.8 build)

```bash
pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 torchvision==0.22.1+cu128 \
  --index-url https://download.pytorch.org/whl/cu128
```

### Step 4 — Install LTX Packages (Editable)

```bash
pip install -e /home/coder/T2V_Gen/LTX-2/github/packages/ltx-core
pip install -e /home/coder/T2V_Gen/LTX-2/github/packages/ltx-pipelines
```

### Step 5 — Install Remaining Key Dependencies

```bash
pip install \
  diffusers==0.37.1 \
  transformers==4.57.3 \
  accelerate==1.13.0 \
  safetensors==0.7.0 \
  huggingface_hub==0.36.2 \
  sentencepiece==0.2.1 \
  protobuf==4.25.9 \
  google-genai==2.0.0 \
  google-auth==2.49.1 \
  einops==0.8.2 \
  av==17.0.0 \
  numpy==2.2.6 \
  scipy==1.15.3 \
  pillow==11.3.0 \
  tqdm==4.67.3 \
  faster-whisper==1.2.1 \
  librosa==0.11.0 \
  decord==0.6.0 \
  openimageio==3.1.13.1 \
  opencv-python==4.13.0.92
```

### Step 6 — Download Model Checkpoints

**LTX-2.3 dev checkpoint (43 GB):**
```bash
mkdir -p /home/coder/T2V_Gen/LTX-2/checkpoints
huggingface-cli download Lightricks/LTX-2.3 ltx-2.3-22b-dev.safetensors \
  --local-dir /home/coder/T2V_Gen/LTX-2/checkpoints
```

**Gemma 3 12B text encoder (requires Gemma license acceptance on HuggingFace):**
```bash
huggingface-cli login  # enter HF token with Gemma access
huggingface-cli download google/gemma-3-12b-it-qat-q4_0-unquantized \
  --local-dir /home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it
```

### Step 7 — Verify Installation

```bash
conda activate ltx23
python -c "
import torch
print('torch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
import transformers; print('transformers:', transformers.__version__)
import diffusers; print('diffusers:', diffusers.__version__)
import ltx_core; print('ltx-core OK')
import ltx_pipelines; print('ltx-pipelines OK')
"
```

### Step 8 — Run a Test Generation

```bash
conda activate ltx23
python -m ltx_pipelines.ti2vid_one_stage \
  --checkpoint-path /home/coder/T2V_Gen/LTX-2/checkpoints/ltx-2.3-22b-dev.safetensors \
  --gemma-root /home/coder/T2V_Gen/LTX-2/checkpoints/gemma-3-12b-it \
  --prompt "A dog runs along a sunny beach, waves crashing in the background." \
  --output-path /tmp/test_output.mp4 \
  --width 768 --height 512 --num-frames 121 --frame-rate 24 --seed 42
```

---

## 12. Important Notes for Reproduction

1. **`ltx-core` requires `transformers>=4.52`** (from `pyproject.toml`). The installed version is 4.57.3, which is compatible.

2. **Resolution constraints:** LTX-2 requires `width` and `height` to be divisible by 32, and `num_frames` to be `8k + 1` (e.g., 121, 97, 73).

3. **Default dtype:** The pipeline uses `torch.bfloat16` throughout. A100 GPUs support bfloat16 natively.

4. **Memory model:** Each pipeline component (transformer, VAE, text encoder) loads into GPU memory on demand and is freed after use. Even on 80 GB A100s, the 22B parameter model is memory-intensive.

5. **The `diffusers` version (0.37.1) is notably new** — this is likely a pre-release or custom build. Standard PyPI diffusers may be at a different version. Check `pip show diffusers` to confirm.

6. **Gemma access is gated:** Downloading `google/gemma-3-12b-it-qat-q4_0-unquantized` requires accepting the Gemma license on HuggingFace and using an authenticated `HF_TOKEN`.

7. **No `google-generativeai` package** is installed. The Google AI SDK in use is `google-genai==2.0.0` (the new unified SDK). Do not confuse these.

8. **`uv` was also installed** (`uv==0.11.2`) — the official LTX-2 repo uses `uv sync --frozen` for installation, but this environment was set up with `pip` + conda instead.

9. **The `pyproject.toml` for `ltx-core` specifies `torch~=2.7`** (compatible with 2.7.x), `transformers>=4.52`, and `scipy>=1.14`.

10. **conda-installed system libraries** include `ffmpeg 8.0.1` (GPL build with hardware codec support), `cairo`, `harfbuzz`, `libass`, and other multimedia system libraries — these are required by `av` and `OpenImageIO` and must be present in the conda environment (they are installed automatically when using conda/miniforge for the base env).

---

## Appendix A: Full `pip list` Output (ltx23 env)

```
Package                  Version      Editable project location
------------------------ ------------ -------------------------------------------------------
absl-py                  2.4.0
accelerate               1.13.0
annotated-doc            0.0.4
annotated-types          0.7.0
anyio                    4.13.0
attrs                    26.1.0
audioread                3.1.0
av                       17.0.0
cairocffi                1.7.1
CairoSVG                 2.9.0
certifi                  2026.4.22
cffi                     2.0.0
charset-normalizer       3.4.7
click                    8.3.1
coloredlogs              15.0.1
contourpy                1.3.2
cryptography             46.0.7
cssselect2               0.9.0
ctranslate2              4.7.2
cuda-bindings            13.2.0
cuda-pathfinder          1.5.4
cuda-toolkit             13.0.2
cycler                   0.12.1
decorator                5.2.1
decord                   0.6.0
defusedxml               0.7.1
diffusers                0.37.1
distro                   1.9.0
einops                   0.8.2
et_xmlfile               2.0.0
exceptiongroup           1.3.1
faster-whisper           1.2.1
filelock                 3.29.0
flatbuffers              25.12.19
fonttools                4.62.1
fsspec                   2026.4.0
ftfy                     6.3.1
gitdb                    4.0.12
GitPython                3.1.50
google-auth              2.49.1
google-genai             2.0.0
h11                      0.16.0
h5py                     3.16.0
hf-xet                   1.5.0
httpcore                 1.0.9
httpx                    0.28.1
huggingface_hub          0.36.2
humanfriendly            10.0
idna                     3.14
ImageIO                  2.37.3
imageio-ffmpeg           0.6.0
importlib_metadata       9.0.0
jax                      0.6.2
jaxlib                   0.6.2
Jinja2                   3.1.6
jiter                    0.13.0
joblib                   1.5.3
kiwisolver               1.5.0
lazy-loader              0.5
librosa                  0.11.0
llvmlite                 0.47.0
ltx-core                 1.1.3        /home/coder/T2V_Gen/LTX-2/github/packages/ltx-core
ltx-pipelines            1.1.3        /home/coder/T2V_Gen/LTX-2/github/packages/ltx-pipelines
markdown-it-py           4.0.0
MarkupSafe               3.0.3
matplotlib               3.10.9
mdurl                    0.1.2
mediapipe                0.10.14
ml_dtypes                0.5.4
moviepy                  2.2.1
mpmath                   1.3.0
msgpack                  1.1.2
networkx                 3.4.2
numba                    0.65.0
numpy                    2.2.6
nvidia-cublas-cu12       12.8.3.14
nvidia-cuda-cupti-cu12   12.8.57
nvidia-cuda-nvrtc-cu12   12.8.61
nvidia-cuda-runtime-cu12 12.8.57
nvidia-cudnn-cu12        9.7.1.26
nvidia-cufft-cu12        11.3.3.41
nvidia-cufile-cu12       1.13.0.11
nvidia-curand-cu12       10.3.9.55
nvidia-cusolver-cu12     11.7.2.55
nvidia-cusparse-cu12     12.5.7.53
nvidia-cusparselt-cu12   0.6.3
nvidia-nccl-cu12         2.26.2
nvidia-nvjitlink-cu12    12.8.61
nvidia-nvtx-cu12         12.8.55
onnxruntime              1.23.2
openai                   2.30.0
opencv-contrib-python    4.13.0.92
opencv-python            4.13.0.92
OpenImageIO              3.1.13.1
openpyxl                 3.1.5
opt_einsum               3.4.0
packaging                26.2
pandas                   2.3.3
pillow                   11.3.0
pip                      26.1.1
platformdirs             4.9.4
pooch                    1.9.0
proglog                  0.1.12
protobuf                 4.25.9
psutil                   7.2.2
pyasn1                   0.6.3
pyasn1_modules           0.4.2
pycparser                3.0
pydantic                 2.12.5
pydantic_core            2.41.5
Pygments                 2.20.0
pyparsing                3.3.2
python-dateutil          2.9.0.post0
python-dotenv            1.2.2
pytz                     2026.1.post1
PyYAML                   6.0.3
regex                    2026.3.32
requests                 2.34.0
rich                     14.3.3
runwayml                 4.14.0
safetensors              0.7.0
scikit-learn             1.7.2
scipy                    1.15.3
sentencepiece            0.2.1
sentry-sdk               2.60.0
setuptools               81.0.0
shellingham              1.5.4
six                      1.17.0
smmap                    5.0.3
sniffio                  1.3.1
sounddevice              0.5.5
soundfile                0.13.1
soxr                     1.0.0
sympy                    1.14.0
tabulate                 0.10.0
tenacity                 9.1.4
threadpoolctl            3.6.0
tinycss2                 1.5.1
tokenizers               0.22.2
torch                    2.7.1+cu128
torchaudio               2.7.1+cu128
torchvision              0.22.1+cu128
tqdm                     4.67.3
transformers             4.57.3
triton                   3.3.1
typer                    0.24.1
typing_extensions        4.15.0
typing-inspection        0.4.2
tzdata                   2025.3
urllib3                  2.7.0
uv                       0.11.2
wcwidth                  0.7.0
webencodings             0.5.1
websockets               16.0
wheel                    0.47.0
zipp                     3.23.0
```

---

*End of document. Generated by inspecting live environment at `/home/coder/T2V_Gen/LTX-2/` on 2026-05-25.*
