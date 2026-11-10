#!/usr/bin/env python3
"""Reproducibility manifest, perturbation LaTeX table and ZIP for the corrected A-axis run. Reads only; writes only below the output dir."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, os, platform, subprocess, time, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(os.environ["T2AV_OUT_DIR"]) / "a_axis_event_gate_v3_2026-11-10"
WS, DATA = Path(os.environ["T2AV_WORKSPACE"]), Path(os.environ["T2AV_DATA"])


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()


def perturbation_tex():
    import pandas as pd
    p = pd.read_csv(OUT / "tables/perturbation_P03_P09_A.csv")
    keep = ["MLLM-only", "MLLM + Tools", "Reconsideration", "Reconsideration + Tools", "AVT-Judge a05", "Gate-only a05", "AVT-Judge old a05", "Gate-only old a05"]
    lines = [r"% P03-P09 A (anchor-mute perturbation): share of units predicted FAIL / accuracy. A sounding only (no speech), so corrected = old.",
             r"\begin{tabular}{l" + "c" * len(keep) + "}", r"\toprule", "Row type & " + " & ".join(k.replace(" a05", r" 5\%") for k in keep) + r" \\", r"\midrule"]
    for rt, g in p.groupby("row_type"):
        g = g.set_index("method")
        lines.append(rt + " & " + " & ".join(f"{g.loc[k, 'predicted_FAIL_share']:.3f} / {g.loc[k, 'accuracy']:.3f} (n={int(g.loc[k, 'N'])})" for k in keep) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (OUT / "tables/perturbation_P03_P09_A.tex").write_text("\n".join(lines) + "\n")


def main():
    perturbation_tex()
    import pandas as pd
    FBD = WS / "evaluation/ablation/gepa_stage2/runs/obsval_1028/final_benchmark_1108"
    inputs = {
        "final_benchmark_1108/unit_results_final.csv": FBD / "unit_results_final.csv",
        "sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv": WS / "eval_results/analysis/sanjoy_two_baselines_2026-11-08/results/unit_predictions.csv",
        "sensitivity_2026-11-10/results/unit_labels_openings.csv": WS / "eval_results/analysis/sensitivity_2026-11-10/results/unit_labels_openings.csv",
        "new_prompts/generated/relative_500_v5_fixed.json": WS / "new_prompts/generated/relative_500_v5_fixed.json",
        "gen_holdout_149_1030/prompts_gen149.json": DATA / "gen_holdout_149_1030/prompts_gen149.json",
        "gen_prolific2k25_1104/prompts_gen2k25.json": DATA / "gen_prolific2k25_1104/prompts_gen2k25.json",
        "gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json": DATA / "gen_prolific_mova390_1108_rev650fe5ae/prompts_mova390.json",
    }
    for t in ("a01", "a05", "a10"):
        inputs[f"configs/sensitivity/{t}/frozen_config.json"] = REPO / f"repro/avt_gate/configs/sensitivity/{t}/frozen_config.json"
    inputs["configs/main/frozen_p12_config.json"] = REPO / "repro/avt_gate/configs/main/frozen_p12_config.json"
    hashes = {k: md5(v) for k, v in inputs.items()}
    P = pd.read_csv(OUT / "call_plan.csv").fillna("")
    reused = sorted(set(P.reuse_source) - {""})
    stage2 = {os.path.relpath(p, WS) if p.startswith(str(WS)) else p: md5(p) for p in reused}
    ev_dir = DATA / "tools/gen_evidence_1030"
    F = pd.read_csv(OUT / "a_event_features_openings.csv", keep_default_na=False, low_memory=False)
    code = {str(p.relative_to(REPO)): md5(p) for p in sorted((REPO / "repro/avt_gate/a_axis_v3").rglob("*.py")) if "__pycache__" not in str(p)}
    import numpy, pandas
    try:
        import google.genai as gg; genai_v = gg.__version__
    except Exception:
        genai_v = "unavailable"
    man = dict(created=time.strftime("%Y-%m-%dT%H:%M:%S"), git=dict(repo="SGT-LIM/T2AV_Temporal_Constraint", branch=git("rev-parse", "--abbrev-ref", "HEAD"),
                                                                     commit=git("rev-parse", "HEAD"), dirty_tracked=bool(git("status", "--porcelain", "--untracked-files=no"))),
               environment=dict(python=sys.version.split()[0], platform=platform.platform(), conda_env=sys.prefix,
                                numpy=numpy.__version__, pandas=pandas.__version__, google_genai=genai_v),
               model_settings=dict(model="gemini-3.6-flash", thinking="high", temperature=0.0, seed=42, response="application/json + run_two_stage.SCHEMA['A']",
                                   media="none (text only)", system_md5="1ac460ed7a517e5d4db6505943ba97cc"),
               input_md5=hashes, code_md5=code, reused_stage2_records=len(stage2), reused_stage2_record_md5=stage2,
               new_call_records={p.name: md5(p) for p in sorted((OUT / "calls").glob("*.json"))},
               evidence_dir=str(ev_dir), a_units=len(F),
               commands=[l.strip() for l in (REPO / "repro/avt_gate/a_axis_v3/README.md").read_text().split("```bash")[1].split("```")[0].splitlines() if l.strip()],
               outputs={k: str(OUT / k) for k in ("REPORT.md", "walkthrough/WALKTHROUGH.md", "predictions/", "tables/", "checks.json", "cost.json", "call_plan.csv", "calls/", "prompts/")},
               run_start=(OUT / "run_full_start.txt").read_text().strip() if (OUT / "run_full_start.txt").exists() else "")
    json.dump(man, open(OUT / "MANIFEST.json", "w"), indent=1)
    z = OUT.parent / f"{OUT.name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                zf.write(p, f"{OUT.name}/{p.relative_to(OUT)}")
        for p in sorted((REPO / "repro/avt_gate/a_axis_v3").rglob("*")):
            if p.is_file() and "__pycache__" not in str(p):
                zf.write(p, f"{OUT.name}/code/{p.relative_to(REPO)}")
    print("manifest + zip:", z, round(z.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
