---
name: humanize-korean
version: "2.0.1"
description: AI(ChatGPT·Claude·Gemini 등)가 쓴 한글 텍스트를 "사람이 쓴 글처럼" 윤문해주는 오케스트레이터 스킬. 번역투·영어 인용 과다·기계적 병렬·관용구·피동태 남용·접속사 남발·리듬 균일성·이모지/불릿 과다 등 10대 카테고리 70개 AI 티 패턴을 탐지·분류해 내용은 한 글자도 건드리지 않고 문체·리듬·표현만 자연스러운 한국어로 재작성한다. 트리거 — "AI 티 없애줘", "AI 같은 글 자연스럽게", "GPT/ChatGPT 문체", "AI 번역투 고쳐", "사람이 쓴 것처럼 윤문", "AI 윤문", "ChatGPT 티 제거", "한글 AI 탐지·윤문", "AI 글 사람처럼", "번역투 제거", "영어 인용 많은 글 윤문", "AI 글 티 안 나게", "휴머나이저", "humanize Korean", "AI detector bypass 한글". 후속 작업 — "특정 카테고리만 다시", "윤문 강도 조정", "장르 바꿔서", "이 문단만", "2차 윤문" 도 모두 이 스킬. 단순 맞춤법·오탈자 교정은 직접 처리, 번역은 번역 스킬, 내용 추가·삭제를 동반한 재작성은 별도 집필 스킬.
---

# Humanize Korean — AI 한글 티 제거 오케스트레이터 (v2.0)

> **버전 요약 (v2.0.1 기준)**
> - **v1.5 (2026-04-26)** — v1.1 5인 파이프라인 위에 단일 호출 `humanize-monolith` fast path 신설. voice profile·candidate pool·권한 위계 §1~§6은 핫패스 비용 문제로 삭제.
> - **v1.6 (2026-05-07)** — KatFish·LREAD 기반 정량 점수 레이어 도입. `scripts/prepare_monolith_input.py`(입력 shim)가 monolith 호출 *전* 외부 사전 처리로 점수를 산출해 결합 입력 파일에 prepend.
> - **v1.6.1 (2026-05-07)** — fast 산출물을 `final.md` 1개로 통합(본문 끝 `<!-- HUMANIZE-SUMMARY -->` HTML 주석 블록). monolith 도구 호출 캡 4회 → **3회**.
> - **v2.0 (2026-05-07)** — 한국 번역학계 8유형 + post-editese metric 트랙(`metrics_v2.py`) 흡수. 분류 체계 본진 v2.0(활성 패턴 70건 + A-17 hold 1건).
> - **v2.0.1** — 패치 릴리스: shim 실행 절차를 본 오케스트레이터에 명문화하고 버전·산출물·캡 표기를 실제 구현과 정합.
>
> **두 모드**
> - **Fast 모드(디폴트)** — shim 사전 처리 후 `humanize-monolith` 에이전트가 한 콜에서 탐지·윤문·자체검증 일괄 처리. 도구 호출 3회 캡. 5,000자 이하 wall-clock 2~3분 목표.
> - **Strict 모드(`--strict`)** — v1.1 5인 파이프라인(detector·rewriter·auditor·reviewer + taxonomist 분류 자산 유지). 정밀 검증·장문(8,000자+) 처리.

## Phase 0: 컨텍스트 확인 및 모드 결정

작업 시작 시 가장 먼저 다음 한 줄을 사용자에게 출력한다.

```
humanize-korean v2.0 — {fast|strict} 모드 / run_id: {YYYY-MM-DD-NNN}
```

### 모드 결정
- 사용자가 `--strict`·"정밀 모드"·"5인 파이프라인" 명시 → **strict**
- 입력 8,000자 초과 → **strict** (자동 승급 + 사용자에 1줄 고지)
- 그 외 모두 → **fast (디폴트)**

### run_id 결정
- 모든 경로는 **cwd 기준**. 새 폴더 생성도 cwd 기준 `_workspace/{YYYY-MM-DD-NNN}/`에 만든다.
- 기존 시퀀스 확인은 **`Glob` 도구**로 표지 파일을 매칭해 간접 조회.
  올바른 사용법: `Glob(pattern="_workspace/YYYY-MM-DD-*/01_input.txt")` → 결과에서 폴더명 추출 후 NNN 최댓값 + 1.
  주의: Glob은 디렉토리 자체는 매칭하지 못한다. 반드시 그 안의 표지 파일(`01_input.txt`)을 매칭할 것.
  `Bash ls`는 OS·셸 환경에 따라 경로 해석이 달라지므로 사용 금지.
- 당일 폴더가 없으면 NNN = 001. 있으면 마지막 NNN + 1.
- 부분 재실행 신호("이 카테고리만 다시"·"2차 윤문")일 경우 기존 run_id 재사용 + strict 모드로 자동 승급.

## Fast 모드 (디폴트)

### Phase 1: 입력 저장 + 정량 사전 점수 (input shim)
1. cwd 기준 `_workspace/{run_id}/` 생성
2. 입력 텍스트를 `01_input.txt`에 저장
3. 첫 300자로 장르 자동 추정 (사용자 명시 시 우선)
4. 사전 처리 shim을 Bash로 1회 실행:
   ```
   python3 scripts/prepare_monolith_input.py --run-dir _workspace/{run_id} --genre {genre}
   ```
   - `--genre` 값은 영문 키: `essay | column | report | blog | abstract` (생략 시 `essay`). 장르 힌트 매핑: 칼럼→`column`, 리포트→`report`, 블로그→`blog`, 공적/기타→`essay`.
   - `--run-dir`는 프로젝트 루트 기준 상대 경로 허용 (스크립트가 절대화). 그 외 인자: `--text`(run-dir 없이 즉석 실행 시 새 run 디렉토리 자동 생성), `--baseline`(baseline JSON 경로 override, 평소 불필요), `--diagnosis`(진단 텍스트 파일을 점수 블록 앞에 prepend — 정밀 3콜 구조용, 현재 fast 경로에서는 사용하지 않음).
   - 산출: `00_metrics.json`(정량 점수) + `01_input_with_metrics.txt`(점수 블록을 원문 앞에 붙인 결합 파일).
   - **graceful degrade 내장**: metrics 계산이 실패하면 shim이 점수 블록 없이 원문만 감싼 결합 파일을 쓰고 `00_metrics.error`를 남긴다. monolith는 v1.5처럼 동작하므로 오케스트레이터 쪽 분기 로직은 불필요.

### Phase 2: Monolith 호출
`humanize-monolith` 에이전트를 `Agent` 도구로 1회 호출.

입력:
```
input_path: <abs path>/_workspace/{run_id}/01_input_with_metrics.txt
quick_rules_path: <abs path>/.claude/skills/humanize-korean/references/quick-rules.md
genre_hint: 칼럼 | 리포트 | 블로그 | 공적 | null
```

출력 (에이전트가 직접 작성):
- `_workspace/{run_id}/final.md` — 윤문본. 본문 끝에 `<!-- HUMANIZE-SUMMARY -->` HTML 주석 블록 1개로 메트릭·카테고리 탐지·자체검증·등급·하이라이트 통합 (v1.6.1~)

monolith는 단일 호출 안에서 다음을 모두 수행 (자세히는 에이전트 정의 참조):
1. quick-rules 룰북 로드 → 메모리에서 패턴 탐지 + 윤문 + 자체검증 6항 점검
2. 변경률 50% 초과 시 자동 롤백 (1차 방어선 — 확정 판정은 Phase 2.5)
3. 자체검증 위반 시 1회 부분 재실행
4. final.md 작성 (본문 + summary 주석 블록, 단일 Write — 도구 호출 3회 캡: Read 입력 + Read 룰북 + Write final)

### Phase 2.5: 변경률 게이트 (철칙 #4 — 결정적 검증)

monolith가 자체 보고한 변경률은 **참고값**이다. 철칙 #4의 게이트 판정은 코드가 한다.
윤문본이 나온 직후 Bash로 1회 실행:

```
python3 scripts/verify_change_rate.py \
    --before _workspace/{run_id}/01_input.txt \
    --after  _workspace/{run_id}/final.md
```

exit code로 분기한다:

| exit | 판정 | 후속 |
|---|---|---|
| 0 | 수렴 (< 30%) | Phase 3 진행 |
| 1 | 경고 (30~50%) | Phase 3 진행 + **사용자에게 과윤문 가능성 고지** |
| 2 | 중단 (≥ 50%) | **윤문본 채택 금지.** monolith에 롤백 지시 후 1회 재실행, 재차 2면 `hold_and_report` |
| 3 | 판정 불가 | 입력 파일 확인 후 재시도. 게이트를 건너뛰지 않는다 |

- 스크립트가 `<!-- HUMANIZE-SUMMARY -->` 블록을 자동 제거하고 비교하므로 별도 전처리 불필요.
- 헤딩·불릿 산문화가 많아 변경률이 부풀려진 것으로 보이면 `--ignore-markup`으로 본문만 재측정해 교차 확인한다. **판정을 뒤집는 근거로 쓰려면 두 수치를 모두 사용자에게 보고할 것.**
- **이 수치가 SSOT다.** Phase 3의 상태 줄과 summary 블록에는 스크립트 출력값을 쓴다. 에이전트 자가 산출값으로 덮어쓰지 않는다.

### Phase 3: 결과 전달
사용자에게 다음 4개를 반환:
1. 한 줄 상태: `완료. 변경률 X% / 등급 Y / 자체검증 N/6 통과` — 변경률은 **Phase 2.5 스크립트 출력값**을 그대로 쓴다 (에이전트 자가 산출값 아님)
2. 윤문본 본문 (마크다운 블록)
3. final.md 끝 `<!-- HUMANIZE-SUMMARY -->` 블록의 핵심 표 (메트릭 + 카테고리 탐지 + 자체검증)
4. 등급 B 이하면 "정밀 검증이 필요하면 `--strict`로 5인 파이프라인" 안내

**디폴트 wall-clock 목표:** 5,000자 이하 2~3분, 8,000자 5~7분.

## Strict 모드 (`--strict` 또는 자동 승급)

v1.1 5인 파이프라인 그대로. 검증 분리·재윤문 루프가 의미 있을 때만 사용.

### Phase A: 탐지
`ai-tell-detector` 호출 → `02_detection.json`

### Phase B: 윤문 (최대 3회 루프)
`korean-style-rewriter` 호출 → `03_rewrite.md` + `03_rewrite_diff.json`

### Phase C: 병렬 검증
`Agent` 도구로 다음 두 에이전트를 동시에(한 응답에서 병렬) 호출:
- `content-fidelity-auditor` → `04_fidelity_audit.json` (의미 동등성)
- `naturalness-reviewer` → `05_naturalness_review.json` (잔존·과윤문)

두 결과 수신 후 종합 판정 매트릭스에 따라 분기:

| fidelity | naturalness | 종합 | 후속 |
|---|---|---|---|
| full_pass | accept / accept_with_note | **최종 승인** | Phase D |
| full_pass | rewrite_round_2 | **2차 윤문** | Phase B 재호출 (target finding) |
| full_pass | rollback_and_rewrite | **롤백 후 재윤문** | 윤문가에 edit 롤백 지시 |
| conditional_pass | - | **롤백된 edit만 재시도** | Phase B 재호출 |
| fail | - | **전면 재작업** | Phase B 전면 재호출 |

2차/3차 윤문 진입 시 `03_rewrite_v2.md`·`v3.md`로 버전 분리. **최대 3회 후 미해결이면 `hold_and_report`**로 사람 개입.

### Phase D: 최종 출력
1. `final.md`에 최종 윤문본 복사
2. `summary.md` 생성 (점수·카테고리 탐지 before/after·등급·하이라이트 — strict 모드 전용 별도 파일)
3. 사용자에게 결과 + 등급 + 안내

## 부분 재실행 / 후속 명령

| 사용자 신호 | 처리 |
|---|---|
| "특정 카테고리만 다시" | strict 모드로 자동 전환, 해당 카테고리 finding만 Phase B 재실행 |
| "이 문단만" | strict 모드, 해당 문단만 입력으로 새 run_id 생성 |
| "2차 윤문"·"`/humanize-redo`" | 기존 run_id의 `final.md`를 새 입력으로 strict Phase B 재실행 |
| "윤문 강도 조정" | strict 모드, `min_severity` 옵션 변경 후 Phase A부터 재실행 |
| "장르 바꿔서" | `genre_hint` 변경 후 Phase A부터 재실행 |

## 옵션 (인자 끝에 자연어로)

- `장르: 칼럼|리포트|블로그|공적` — 장르 명시 (생략 시 자동 추정)
- `강도: 보수|기본|적극` — 윤문 강도 (기본값: 기본)
- `최소심각도: S1|S2|S3` — 탐지 임계값 (기본값: S2)
- `--strict` — 5인 파이프라인 강제 사용

## 데이터 흐름 요약

### Fast 모드 (디폴트)
```
01_input.txt
    ↓ [scripts/prepare_monolith_input.py — 정량 점수 shim, Bash 1회]
00_metrics.json + 01_input_with_metrics.txt
    ↓ [humanize-monolith — 단일 호출, 도구 호출 3회 캡]
    ├ 메모리: quick-rules 로드 → 탐지 → 윤문 → 자체검증
    └→ final.md (본문 + <!-- HUMANIZE-SUMMARY --> 주석 블록)
```

### Strict 모드
```
01_input.txt
    ↓ [ai-tell-detector]
02_detection.json
    ↓ [korean-style-rewriter]
03_rewrite.md + 03_rewrite_diff.json
    ↓ [병렬 팀]
    ├→ [content-fidelity-auditor] → 04_fidelity_audit.json
    └→ [naturalness-reviewer]      → 05_naturalness_review.json
    ↓ [오케스트레이터 종합]
    ├→ (재작업) Phase B로 복귀 (최대 3회)
    └→ (승인) final.md + summary.md
```

## 에이전트 호출 규칙

**모델:** 모두 `model: opus` 통일 (v1.1 베이스라인). 모델 다운그레이드는 v1.4에서 시도했으나 도구 호출 chain이 진짜 병목이라 효과 미미했음.

**에이전트 정의 위치:** Claude Code가 다음 우선순위로 자동 탐색.
1. `<cwd>/.claude/agents/` (프로젝트 로컬)
2. `~/.claude/agents/` (글로벌, 본 프로젝트는 프로젝트→글로벌 심볼릭 링크)

`.claude/agents/`에는 총 12개 정의가 있으나, **본 스킬 런타임이 호출하는 것은 5종뿐**이다.

**런타임 5종 (스킬 실행 중 호출)**
- `humanize-monolith` — fast 모드 전용 단일 호출
- `ai-tell-detector` · `korean-style-rewriter` · `content-fidelity-auditor` · `naturalness-reviewer` — strict 5인 파이프라인 중 4명

**유지보수 1종 (별도 명령으로만 트리거)**
- `korean-ai-tell-taxonomist` — 분류 체계(SSOT) 유지·확장. 본 스킬 실행 중에는 호출되지 않음

**개발용 1회성 5종 (릴리스 회차 전용 — 런타임 미로드)**
- `translationese-research-distiller` · `korean-translation-scholar` · `taxonomy-gap-analyzer` · `post-editese-metric-engineer` · `quick-rules-integrator` — v2.0 학술 흡수 회차에서 사용된 개발 도구. 윤문 실행과 무관

**미사용 1종**
- `humanize-web-architect` — 웹 서비스 확장 설계용. 웹앱이 별도 구현·운영 중이라 현재 미사용 (거취는 메인테이너 결정 대기)

## 테스트 시나리오

### Fast 정상 흐름
- 입력: ChatGPT가 생성한 AI 칼럼 초안 (2,000~5,000자, 번역투·결말 공식·hype 어휘 풍부)
- 기대: monolith 1콜로 변경률 15~25%, 등급 A/B, wall-clock 2~3분, 자체검증 5~6/6

### Strict 정밀 검증 흐름
- 사용자 명시 `--strict` 또는 8,000자+ 입력
- 5인 파이프라인 끝까지 실행, 변경률 18~22%, 검증팀 full_pass

### 엣지 케이스 — 이미 사람이 쓴 글
- monolith 자체 탐지에서 매치 거의 없음 → 변경률 5% 미만 + final.md의 `<!-- HUMANIZE-SUMMARY -->` 블록에 "윤문 불필요 가능성" 메모
- 사용자가 `--strict`로 강제 검증 가능

## 주의 사항

- **의미 불변이 최상위 불문율.** monolith·strict 모두에서 위반 즉시 롤백.
- **수치·고유명사·직접 인용은 탐지/윤문 대상 아님.** Do-NOT list 엄수.
- **장르 이탈 금지.** 칼럼이 에세이로, 에세이가 문학으로 옮겨가지 않는다.
- **register 보존 — 양방향.** 격식체 입력 → 격식체 출력, 구어 입력 → 구어 출력. 격식 상향('-했-'→'-하였-') 금지, 구어 종결('~인데요/~거든요') 보존.
- **AI 티는 빼기만 하고 넣지 않는다.** 원문에 없던 상투구("기록적인 성과를 거두었다"류) 신규 삽입 금지.
- **변경률 30% 초과 → 경고, 50% 초과 → 강제 중단.**
- **자동 로드 금지.** 프로젝트 CLAUDE.md 등 다른 파일을 자동 파싱해 옵션을 추론하지 않는다.

## 참고 자료

- 슬림 룰북 (Fast 전용): [`references/quick-rules.md`](references/quick-rules.md) — S1·S2 핵심 패턴 + 자체검증 체크리스트
- 정량 점수 shim (Fast 전용): `scripts/prepare_monolith_input.py` — `references/metrics_v2.py`(실패 시 `metrics.py` fallback) + `references/baseline.json` 기반 사전 점수 계산
- 분류 체계 본진 (Strict 전용): [`references/ai-tell-taxonomy.md`](references/ai-tell-taxonomy.md) — 10대분류 × 활성 70 패턴 (+A-17 hold 1건) 전수
- 윤문 처방 (Strict 전용): [`references/rewriting-playbook.md`](references/rewriting-playbook.md) — 카테고리별 치환 레시피·장르별 허용 표
- 학술 인용 외부 SSOT: [`references/scholarship.md`](references/scholarship.md) — v2.0 학자 인용·caveat verbatim 보존
- 웹 서비스 스펙 (옵션): [`references/web-service-spec.md`](references/web-service-spec.md) — 웹 확장 시 로드
