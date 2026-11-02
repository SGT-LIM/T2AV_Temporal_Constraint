import os as _os, pathlib as _pl; _LEGACY_ROOT = _os.environ.get("T2AV_LEGACY_ROOT", str(_pl.Path(__file__).resolve().parents[4] / "legacy_root")); _LEGACY_CODE = str(_pl.Path(__file__).resolve().parents[1])  # legacy path roots, see legacy/README.md
# writes gepa_stage2/sources_v3.json from the existing sources.json (run from evaluation/ablation)
import json
s = json.load(open("gepa_stage2/sources.json"))
E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
R = (_LEGACY_ROOT + "/eval_results/multi_agent/baseline_min3_g36/rep1")
hd = s["hdepic"]; med = [f"{E}/hdepic_medium_shard{i}" for i in range(6)]
out = {
  "hdepic": dict(prompt_json=f"{E}/hdepic_medium_prompts_v2.json", outputs_dirs=med, caption_json=hd["caption_json"],
                 flam_ckpt=hd["flam_ckpt"], flam_hop_sec=5, audio="whisper_flam",
                 stage1=[f"{E}/results/hdepic_medium_multi_baseline_g36", f"{E}/results/hdepic_regen_multi_baseline_g36"]),
  "hdfoot": dict(prompt_json=f"{E}/hdepic_medium_prompts.json", outputs_dirs=med, caption_json=hd["caption_json"],
                 flam_ckpt=hd["flam_ckpt"], flam_hop_sec=5, audio="whisper_flam",
                 stage1=[f"{E}/results/hdepic_medium_multi_baseline_g36"]),
  "hdmove": dict(prompt_json=f"{E}/hdepic_move_prompts.json", outputs_dirs=[f"{E}/hdepic_move_shard{i}" for i in range(6)],
                 caption_json=None, flam_ckpt=hd["flam_ckpt"], flam_hop_sec=0, audio="none",
                 stage1=[f"{E}/results/hdepic_move_multi_baseline_g36"]),
}
for src, m in (("ltx", "LTX_2p3"), ("mova", "MOVA")):
    c = dict(s[src]); c.update(flam_hop_sec=0, audio="whisper_flam", stage1=[f"{R}/{m}_agentic_baseline.csv"]); out[src] = c
json.dump(out, open("gepa_stage2/sources_v3.json", "w"), indent=1)
for k, v in out.items(): print(k, {kk: (vv if not isinstance(vv, list) else f"[{len(vv)}] {vv[0]}") for kk, vv in v.items()})
