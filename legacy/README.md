# legacy/

Copies of the evaluation/ablation scripts that produced the 10/28–11/02 results. They are kept runnable for
reproduction; new work uses the `t2av_eval` package. `evaluation/ablation/SOURCE.md` lists the origin and the md5 of
every file as copied.

## The one change: path roots

The originals read and write inside the main checkout (`/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint`), both
through absolute paths and through paths relative to the script (`HERE / "runs/obsval_1028"`, `ABL / "captions"`).
In these copies every such path goes through one environment variable:

| variable | default | used for |
|---|---|---|
| `T2AV_LEGACY_ROOT` | `<repo>/legacy_root` (gitignored) | everything that was under the main checkout and is not code: `eval_results/`, `new_prompts/`, `docs/*.md` outputs, `evaluation/ablation/{captions,caption_cache}`, `evaluation/ablation/gepa_stage2/{runs,manifests_v3,panels_1028,focus_1028,fresh_stage1_cache}` |

The root mirrors the main checkout layout, so `$T2AV_LEGACY_ROOT/evaluation/ablation/gepa_stage2/runs/obsval_1028` is
where `obs_judge_1028.py` keeps its call cache. Code paths (`sys.path`, `cd`, md5 of the scripts) point at the copies in
this folder (`_LEGACY_CODE` in Python, `$LEGACY_CODE` in the shell scripts).

Not changed:
- Paths under `/projectnb/ivc-ml/youngsun/T2AV_data/` (videos, tool outputs, the `real_av/eval/results` run dirs). The
  launchers still create their run dirs there. They refuse to overwrite an existing README, but pick a new dir name before
  launching anything.
- Paths relative to the current directory (`gepa_stage2/runs/...` in the old GEPA analysis scripts). Run from
  `legacy/evaluation/ablation/` as before, they resolve inside this folder; `runs/` there is gitignored.
- Numeric behavior. Only path expressions were rewritten (`git diff 786d16e -- legacy/` shows every change).

Never point `T2AV_LEGACY_ROOT` at the main checkout: the scripts write call caches and result tables under it.

## Inputs

`legacy/link_inputs.sh` symlinks the read-only inputs from the main checkout into the root: the v3 GT manifests,
the caption json files and the generation prompts. Output and cache folders are never linked, because a symlinked
output folder would send writes back into the main checkout. Copy a cache (`cp -r`) if a run should reuse it.
