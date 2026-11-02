# gepa_stage2 — 2단계 judge KEEP/REVISE 규칙 GEPA 최적화

설계: `design/gepa_stage2_rules_2026-10-19.md`. 배치: `evaluation/ablation/gepa_stage2/` (run_two_stage.py는 `evaluation/ablation/run_two_stage.py`를 교체).

## 파일
| 파일 | 역할 |
|---|---|
| `run_two_stage.py` | 기존 2단계 러너 리팩터. `install()`, `set_rules()`, `build_stage2_user_text()`, CLI `--stage2-rules <file>`, `--stage2-text-only`. 시드 규칙 = `SEED_RULES`(10/19 런과 동일 텍스트) |
| `make_gt.py` | item × axis GT manifest. `hdepic` / `gen` 서브커맨드 |
| `manifest.py` | 이전 캡션 GEPA split 재사용 + train/val 서브샘플, leak 체크 |
| `adapter.py` | GEPA 어댑터: item당 build_context 1회, (rules sha, uid) 디스크 캐시, 이벤트 피드백, guardrail, reflection 템플릿 |
| `run_gepa.py` | gepa 0.1.4 `optimize` 드라이버 |
| `eval_rules.py` | test에서 seed vs best, 기존 2단계 표와 같은 지표 + paired bootstrap CI |
| `sources.example.json` | 소스별 경로 설정 템플릿 → `sources.json`으로 복사해 채우기 |

## 코드 안의 TODO(확인) — SCC에서 돌리기 전에 3군데
1. `adapter.py` `CRITERIA`: A·V 축 criteria 빌더 이름(`new_eval`에서 grep `def build_.*criteria`). AVB는 확인됨.
2. `adapter.py` `CTX_EVENTS`: ctx의 A·V 이벤트 struct 속성명(`binding_events`는 확인됨). 없으면 `item_meta["events"]`로 fallback.
3. `make_gt.py`: HD-EPIC prompt json의 broken event 필드명(`broken_event_idx`), 220 `gt_event_majority.csv` 컬럼(video id, `event_key`, `A/V/AVB`).
4. `sources.json` hdepic `caption_json` 경로.

## 실행 순서
```bash
cd /projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/evaluation/ablation
module load miniconda ffmpeg/8.1; conda activate /projectnb/ivc-ml/youngsun/conda_envs/t2av_eval
export GEMINI_API_KEY=$(cat ~/.gemini_key) T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1 HF_HOME=/projectnb/ivc-ml/youngsun/hf_cache
E=/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval; R=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/eval_results
P=/projectnb/ivc-ml/youngsun/T2AV_Temporal_Constraint/new_prompts/generated/relative_500_v5_fixed.json
G=gepa_stage2

# 1. GT
python $G/make_gt.py hdepic --prompt-json $E/hdepic_medium_prompts.json --stage1-dir $E/results/hdepic_medium_multi_baseline \
    --vabl-ids $E/vabl_326_items.txt --out $G/manifests/gt_hdepic.jsonl
python $G/make_gt.py gen --prompt-json $P --gt-event-csv $R/min3_gt/gt_event_majority.csv \
    --stage1-csv $R/multi_agent/baseline_min3/LTX_2p3_agentic_pure_gemini.csv --source ltx --out $G/manifests/gt_ltx.jsonl
python $G/make_gt.py gen --prompt-json $P --gt-event-csv $R/min3_gt/gt_event_majority.csv \
    --stage1-csv $R/multi_agent/baseline_min3/MOVA_agentic_pure_gemini.csv --source mova --out $G/manifests/gt_mova.jsonl

# 2. split + subsample (이전 GEPA split 재사용)
python $G/manifest.py --gt $G/manifests/gt_*.jsonl --old-manifests gepa_caption_guide/manifests gepa_caption_guide/manifests_ltx \
    --out-dir $G/manifests --seed 0 --fail-frac 0.45
#   출력 끝의 "leak check: 0" 확인

# 3. smoke (Files API 비운 뒤)
python -u $G/run_gepa.py --sources $G/sources.json --train $G/manifests/train.jsonl --val $G/manifests/val.jsonl \
    --run-dir $G/runs/smoke --limit-train 5 --limit-val 3 --max-metric-calls 12 --workers 2

# 4. 본 런 (screen, 로그인 노드)
screen -S gepa_s2
python -u $G/run_gepa.py --sources $G/sources.json --train $G/manifests/train.jsonl --val $G/manifests/val.jsonl \
    --run-dir $G/runs/s0 --max-metric-calls 300 --minibatch 3 --workers 4 --seed 0 2>&1 | tee $G/runs/s0/log.txt

# 5. test 평가 (seed vs best, 영상만/한 번에 기준선 포함)
python $G/eval_rules.py --sources $G/sources.json --manifest $G/manifests/test.jsonl \
    --rules seed=$G/runs/s0/seed_candidate.txt best=$G/runs/s0/best_candidate.txt --run-dir $G/runs/s0 --oneshot $G/oneshot.json

# 6. best 규칙으로 일반 2단계 런 (전 축, 게이팅 포함)
python run_two_stage.py --stage1-dir $E/results/hdepic_medium_multi_baseline --stage2-rules $G/runs/s0/best_candidate.txt ... (기존 인자)
```
`oneshot.json` = `{"hdepic": "$E/results/hdepic_medium_multi_tools_wf_avocado", "ltx": "$R/multi_agent/tools_wf_avocado_min3/rep1/LTX_2p3_....csv", "mova": ...}`.

## 비용 어림
train 90 + val 50. 300 metric call이면 후보당 minibatch 3 + val 50 전체 재평가 → 후보 5~6개 수준. 2단계 호출 1회 ≈ 영상 1개 업로드(캐시) + Gemini 3.1 pro thinking high 1회. 캐시 덕에 같은 (규칙, item) 반복은 무료, test 평가(약 500~700 row × 2 규칙)가 가장 큼.
