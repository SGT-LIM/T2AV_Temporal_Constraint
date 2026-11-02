# GEPA 2단계 규칙 최적화: 데이터, 세팅, 처음부터 끝까지 예시, 예상 결과 (2026-10-19)

코드는 `evaluation/ablation/gepa_stage2/` (프로젝트 `code/gepa_stage2/`). 설계 근거는 `design/gepa_stage2_rules_2026-10-19.md`, 출발점 수치는 `status/two_stage_results_2026-10-19.md`.

## 1. 한 줄로
2단계 judge가 1단계 판정을 거의 안 바꾸는 이유는 2차 프롬프트의 KEEP 우선 규칙 블록이다. 그 블록 하나만 GEPA로 바꾼다. 다른 건 전부 고정(1단계 판정, 증거 라우팅, 영상, 모델). 점수는 "2단계 최종 라벨이 GT와 맞는 이벤트 비율"의 item 평균 하나뿐이고, "해치지 말 것"과 "도움 챙길 것" 두 방향은 데이터 구성이 담당한다.

## 2. 데이터

item × axis 한 줄이 GEPA의 데이터 한 개다. 같은 영상도 A, V, AVB 세 줄로 따로 들어간다.

| source | axis | REVISE가 정답이어야 하는 쪽 (GT FAIL) | KEEP이 정답이어야 하는 쪽 (GT PASS) |
|---|---|---|---|
| HD-EPIC | A | absent_sound 194 (1단계가 .80 PASS로 틀림) | 원본 194 |
| HD-EPIC | V | Vhand 40 + Vnoun 40 (326 서브셋) | 원본 40, 프레임 동일 변형 206은 test에서 오탐 체크만 |
| HD-EPIC | AVB | early 124 + late 101 (1단계 AVB 판정 있는 것) | 원본 194 |
| 220 LTX·MOVA | A, V, AVB | 사람 GT FAIL 이벤트 | 사람 GT PASS 이벤트 (TIE 제외) |

왜 이 구성인가. 지금 2단계의 실패는 두 종류다. A absent(1단계 PASS를 2단계가 그대로 KEEP, 156/194)와 220 V FAIL(캡션이 맞는데 안 믿음). 반대로 지금 2단계가 잘하는 건 AVB·V 원본을 KEEP해서 오탐을 안 늘리는 것이다. 네 묶음을 한 점수에 넣으면, "다 REVISE"도 "다 KEEP"도 점수가 안 오른다. 증거와 영상을 실제로 대조해야만 오르게 된다.

split: HD-EPIC은 이전 캡션 GEPA의 clip 단위 split(seed 0, 60/15/25)을 그대로 재사용한다. 같은 clip의 변형(_pass, _A, _Vhand, _AVBearly...)은 전부 같은 split에 들어가므로 test 영상이 train에 다른 변형으로 새는 일이 없다. 220은 비디오 단위 66/16/28. `manifest.py` 끝에 leak 체크가 0인지 확인.

크기: train 약 90(축당 HD-EPIC 20 + LTX 5 + MOVA 5, FAIL 비율 0.45로 맞춤), val 약 50(축당 HD-EPIC 10은 FAIL/PASS 반반, 220 6은 자연 비율), test 나머지(HD-EPIC 수백 + 220 각 28 비디오분). FAIL 비율을 0.45로 맞추는 이유는 run 1 교훈: 정답 비율이 소스마다 다르면 "이런 영상이면 KEEP" 같은 데이터셋 규칙이 점수를 올리기 때문.

## 3. 실험 세팅

- 최적화 대상: `run_two_stage.SEED_RULES` 텍스트 블록(약 700자). 시드 = 10/19 런의 KEEP 규칙 그대로.
- judge: gemini-3.1-pro-preview, thinking high, 영상 포함(기존 2단계 런과 동일). 1단계는 기존 영상만 런 csv에서 읽음(`hdepic_medium_multi_baseline`, `baseline_min3`), 없으면 그 자리에서 영상만 호출 1회.
- 증거: 기존 AXIS_EVIDENCE_ROUTE 그대로(A = Whisper+FLAM, V = AVoCaDO 캡션, AVB = 둘 다), 오디오 증거는 캐시에서(`T2AV_AUDIO_EVIDENCE_CACHE_ONLY=1`), GPU 불필요.
- metric 호출 1회 = (item, axis) 2단계 호출 1회. 게이팅 없이 축 독립. 디스크 캐시 키 (규칙 sha, uid)라 같은 규칙으로 같은 item은 재호출 없음.
- 점수: 이벤트 단위 정오(1/0)의 item 평균. broken event 필드가 없는 absent_sound는 item 라벨(이벤트 중 하나라도 no면 no)로 채점.
- 피드백(reflection이 읽는 것): 이벤트별 "1단계 라벨 → 2단계 라벨(kept/revised), 정답, 맞음/틀림", 2단계 reason 앞 220자, 틀린 경우 1단계 reason과 한 줄 진단("1단계가 맞았는데 바꿈" / "1단계가 틀렸는데 유지").
- guardrail: 후보가 시드 × 1.5자 초과, 또는 데이터셋·regime·아이템 식별어(hdepic, ltx, mova, egocentric, first-person, kitchen, generated video, synthetic, P01-..., event_3, hand_swap 등) 포함 → 점수 0 + 그 이유를 피드백으로. reflection 템플릿에도 같은 금지를 적는다. 방향("더 REVISE 해라")은 안 적는다.
- GEPA: 0.1.4, pareto 선택, minibatch 3, 300 metric call, workers 4, reflection = Gemini 텍스트만(영상 안 봄). 로그인 노드 screen.
- 평가: test에서 seed vs best. HD-EPIC은 축 × 변형별 item 단위 FAIL 판정률(변형은 검출, 원본·프레임 동일 변형은 오탐), 220은 모델별 축별 plain accuracy(이벤트 단위, 괄호에 item 단위). 비교 열 = 영상만(1단계) / 한 번에 주기(`--oneshot`) / seed / best. best − seed는 item 단위 paired bootstrap 5,000회 95% CI.

## 4. A부터 Z까지: 한 item이 어떻게 흘러가나

예시 item: `hdepic_P01-xx-xx_0345_A` (absent_sound 변형, 프롬프트는 "컵을 내려놓는 소리가 난다"고 주장하지만 실제 오디오엔 그 소리가 없음). 숫자는 설명용이고 실제 run 값은 아니다.

a. `make_gt.py hdepic`이 이 item을 읽는다. 변형 접미사 `_A` → absent_sound. prompt json의 broken event가 event_2이면 GT = {event_1: yes, event_2: no, event_3: yes}. 같은 item은 V축 줄로도 하나 더 생기는데(프레임은 원본과 같으니 V GT 전부 yes) `eval_only=True`라 test에만 간다. AVB 줄은 안 생긴다(absent_sound는 AVB 데이터가 아님).

b. `manifest.py`가 clip id `P01-xx-xx_0345`를 이전 캡션 GEPA manifest에서 찾아 split을 받는다. 이 clip이 train이면 A축 HD-EPIC train 풀(FAIL 쪽)에 들어가고, 축당 20개 중 FAIL 9개 안에 뽑힐 수 있다.

c. GEPA가 시작한다. 시드 후보 = 현재 KEEP 규칙. 먼저 val 50개 전체를 시드로 채점한다(val 호출 50). 예를 들어 val 점수 .72.

d. 반복 1: train에서 minibatch 3개를 뽑는다. 예: 위 item(A), `..._0912_pass`의 AVB 줄, MOVA 비디오 한 개의 V 줄. 각각 `adapter.judge()`가 돈다.

e. 위 item에서 judge가 하는 일: `build_context`로 영상 업로드 + Whisper/FLAM 증거 로드(한 번만, 이후 메모리 캐시) → 1단계 csv에서 A 판정을 읽음(event_2: yes, reason "a soft clink is audible around 3s") → 축 기본 규칙 + **후보 규칙 블록** + 1단계 블록 + 증거 블록(FLAM: "cup placed on table" max_score .998 at 2.9s, Whisper: 없음)으로 2단계 호출 → 결과 event_2: yes, reason "KEEP: FLAM detects the sound near 3s, consistent with stage 1".

f. 채점: event_2 정답 no인데 yes → 이 item 점수 1/3(event_1, 3은 맞음) = .33. 피드백 문자열:
```
- event_2: stage1=yes -> stage2=yes (kept); correct answer=no -> WRONG
    stage-2 reason: KEEP: FLAM detects the sound near 3s, consistent with stage 1
    stage-1 reason: a soft clink is audible around 3s
    -> stage 1 was wrong and stage 2 kept it; the attached evidence or a re-check of the media should have changed it.
```
AVB 원본 줄은 KEEP yes로 맞아서 1.0, MOVA V 줄은 캡션이 "right hand"라고 하는데 1단계 "left hand" PASS를 KEEP해서 0.0 같은 식.

g. reflection: Gemini 텍스트 모델이 현재 규칙 + 이 3개 피드백 + 템플릿("규칙 블록 하나만, N자 이하, 특정 물체·데이터셋·영상 언급 금지")을 읽고 새 블록을 쓴다. 예를 들어 "증거가 1단계와 일치해 보여도, 1단계가 PASS인 경우 요구된 소리/동작이 영상에서 그 시점에 실제로 보이고 들리는지 다시 확인하고, 확인되지 않으면 REVISE" 같은 문장이 들어올 수 있다. 어떤 방향으로 쓸지는 우리가 안 정한다.

h. guardrail: 새 블록이 1,050자 넘거나 "kitchen", "egocentric" 같은 단어가 있으면 그 후보는 minibatch 점수 0, 피드백에 이유가 들어가고 다음 reflection이 고치게 된다.

i. 새 후보로 같은 minibatch 3개를 다시 채점(캐시 키가 다르니 호출 3회). 위 item이 이번엔 "REVISE: re-listening, no placement sound at 2.9s; FLAM peak is a mis-detection" → no가 되면 .33 → 1.0. 세 개 합이 시드보다 높으면 val 50 전체 채점(호출 50)으로 올라간다. 아니면 버림.

j. val에서 시드 .72 → 후보 .75면 pareto front에 올라가고 다음 반복의 부모 후보가 된다. 300 호출이면 val 재평가 50 × 5~6번이 예산 대부분이고, 후보는 대략 5~6개 나온다.

k. 끝나면 `best_candidate.txt`, `candidates.json`(모든 후보와 val 점수). 먼저 후보 텍스트를 눈으로 읽는다. 이전 cand3 때처럼 "직접 관찰이 최종 권위" 같은 일반 규칙인지, 아니면 금지어를 피해 쓴 regime 규칙("손이 화면 아래에서 들어오는 영상이면..." 같은)인지.

l. `eval_rules.py`로 test. seed와 best 둘 다 test 전체(HD-EPIC 수백 줄 + 220)에 돌려 표를 찍는다. 이 item이 test였다면 A absent 검출 행의 분자에 들어간다. 같은 item의 V 줄(eval_only)은 V 프레임 동일 변형 오탐 행에 들어간다.

m. best가 좋으면 `run_two_stage.py --stage2-rules best_candidate.txt`로 전 축 게이팅 포함 정식 런을 돌려 기존 2단계 표를 다시 채운다. GEPA 어댑터는 축 독립이라 AVB·TC 게이팅 효과는 이 정식 런에서만 보인다.

## 5. 예상 효과와 결과를 읽는 법

출발점(test 전체 기준 10/19 2단계): A absent 검출 .20, AVB 원본 오탐 .11, early/late 검출 .52/.91, V 원본 오탐 .45, 220 V FAIL LTX .71 / MOVA .61.

성공으로 볼 조건(설계 문서 그대로):
- A absent 검출 .20 → .37 근처(한 번에 주기 수준). 이 중 FLAM 탐지가 아예 없는 39개는 규칙 문장으로 잡혀야 하고, FLAM이 틀리게 .998을 준 117개는 재청취로만 고쳐지므로 .37을 넘으면 영상 포함이 값을 한 것이다.
- 220 V FAIL 회복(LTX .71 → .86, MOVA .61 → .89 방향).
- AVB 원본 오탐 .11, early/late .52/.91, V 원본 오탐 .45는 CI 안에서 유지. 이게 깨지면 "증거를 더 믿어라"로 퇴행한 것이고 한 번에 주기와 같아진다.

예상 시나리오 세 가지:
1. 둘 다 잡힘(기대). 규칙이 "1단계 PASS + 증거에 요구된 소리/동작 없음 → 재확인 후 REVISE", "1단계 FAIL은 증거만으로 뒤집지 말 것" 같은 비대칭 규칙으로 간다. 이러면 "2단계 judge + 최적화된 KEEP/REVISE 정책"이 논문의 해결책 섹션이 된다.
2. 한쪽만 잡힘. A absent는 오르는데 V 원본 오탐도 같이 오름(V 엄격 모드 재등장). 이러면 한 블록으로 전 축을 덮는 게 한계라는 결과이고, 다음 수는 축별 블록(V만 따로) 또는 피드백에 "증거 정오"를 넣는 것.
3. 거의 안 바뀜(seed와 CI 겹침). 이전 캡션 GEPA도 run 1은 val 편향으로 실패했으니 먼저 val 구성(HD-EPIC FAIL/PASS 균형)과 후보가 전부 guardrail에 걸렸는지 확인. 그래도 안 바뀌면 규칙이 아니라 judge가 재청취로 FLAM 오탐을 못 가리는 것이고(C1 지각 blind spot), 그때는 text-only 전환으로 비용을 반으로 줄이는 쪽이 맞다.

꼭 같이 볼 것: `eval_rules.py` 마지막 표의 "changed / right after change / wrong after change". seed는 HD-EPIC에서 changed가 5% 수준이었다. best에서 changed가 올라가면서 right가 wrong보다 훨씬 많아야 규칙이 일을 한 것이다. changed만 오르고 right/wrong이 비슷하면 노이즈(V 재실행 노이즈 .15 기억).

## 6. 돌리기 전 확인 3가지 (코드 TODO)
`adapter.py`의 A·V criteria 빌더 이름과 ctx 이벤트 속성명, `make_gt.py`의 prompt json broken event 필드명과 220 GT csv 컬럼, `sources.json`의 hdepic 캡션 경로. README에 적어 둠. smoke(`--limit-train 5 --limit-val 3 --max-metric-calls 12`)로 세 가지가 맞으면 본 런.
