# Humanize KR — AI 한글 티 제거 하네스 (v2.0.1)

## 프로젝트 개요

AI(ChatGPT·Claude·Gemini 등)가 쓴 한글 텍스트를 "사람이 쓴 글처럼" 윤문해주는 이중 모드 하네스. 번역투·영어 인용 과다·기계적 병렬·관용구·피동태 남용·접속사 남발·리듬 균일성·이모지/불릿 과다 등 10대 카테고리 70개 AI 티 패턴(+A-17 hold 1건)을 탐지·분류해 **내용은 한 글자도 건드리지 않고** 문체·리듬·표현만 재작성한다.

- **Fast 모드 (디폴트)** — 정량 점수 shim 사전 처리 후 `humanize-monolith` 에이전트 1콜. 도구 호출 3회 캡, 5,000자 이하 2~3분.
- **Strict 모드 (`--strict` 또는 8,000자+ 자동 승급)** — v1.1 계보의 5인 파이프라인 (탐지→윤문→병렬 검증→종합 판정).

## 철칙

1. **의미 불변 (Fidelity First)** — 사실·주장·수치·고유명사·인용은 100% 원문 보존.
2. **근거 기반 (Span-Grounded)** — 모든 변경은 탐지 finding에 연결. 탐지 없는 구간은 건드리지 않음.
3. **장르 유지 (Tone Match)** — 칼럼을 문학으로, 리포트를 에세이로 옮기지 않음.
4. **과윤문 금지 (No Over-Polish)** — 변경률 30% 초과 시 경고, 50% 초과 시 강제 중단.
5. **register 보존** — 격식체 입력은 격식체 출력. AI 티는 문법·수사이지 격식 자체가 아니다.

## 디렉토리 구조

```
humanize-ko/
├── CLAUDE.md                      # 본 파일 — 프로젝트 가이드
├── README.md                      # 공개 문서
├── RELEASING.md                   # 릴리스 체크리스트 (버전 문자열 전수 목록)
├── CONTRIBUTORS.md
├── scripts/
│   ├── prepare_monolith_input.py  # v1.6 input shim — 정량 점수 계산 + 결합 입력 파일 생성
│   ├── build_social_preview_v2.py
│   └── make_thumbnail.py
├── tests/                         # metrics 단위 테스트 (pytest)
│   ├── test_metrics.py
│   └── test_metrics_v2.py
├── .claude/
│   ├── commands/                  # /humanize · /humanize-redo 슬래시 커맨드
│   ├── agents/                    # 12개 정의 — 아래 "에이전트 구성" 참조
│   └── skills/humanize-korean/
│       ├── SKILL.md               # 오케스트레이터 (fast/strict 분기·shim 배선)
│       └── references/
│           ├── quick-rules.md          # monolith 전용 슬림 룰북 (fast)
│           ├── ai-tell-taxonomy.md     # SSOT — 10대분류 × 활성 70 패턴 (strict)
│           ├── rewriting-playbook.md   # 카테고리별 치환 레시피 (strict)
│           ├── metrics.py              # v1.6 정량 지표 (KatFish baseline 8종)
│           ├── metrics_v2.py           # v2.0 post-editese 14종 (shim이 우선 import)
│           ├── baseline.json           # v1.6 baseline
│           ├── baseline_v2.json        # v2.0 baseline (placeholder 셀 포함)
│           ├── scholarship.md          # v2.0 학술 인용 외부 SSOT
│           └── web-service-spec.md     # 웹 확장 스펙 (옵션)
└── _workspace/                    # 런타임 산출물 (run_id별, gitignored)
    └── {YYYY-MM-DD-NNN}/
        ├── 01_input.txt                # 원문
        ├── 00_metrics.json             # shim 정량 점수 (fast)
        ├── 01_input_with_metrics.txt   # 점수 블록 + 원문 결합 파일 (fast, monolith 입력)
        ├── final.md                    # 윤문본 (fast: 끝에 <!-- HUMANIZE-SUMMARY --> 블록)
        ├── 02_detection.json           # (strict)
        ├── 03_rewrite.md + 03_rewrite_diff.json   # (strict)
        ├── 04_fidelity_audit.json      # (strict)
        ├── 05_naturalness_review.json  # (strict)
        └── summary.md                  # (strict 전용 — fast는 v1.6.1부터 final.md에 통합)
```

## 파이프라인

### Fast 모드 (디폴트)

```
01_input.txt
    ↓ [scripts/prepare_monolith_input.py --run-dir _workspace/{run_id} --genre {genre}]
00_metrics.json + 01_input_with_metrics.txt
    ↓ [humanize-monolith — 단일 호출, 도구 호출 3회 캡 (Read 입력 + Read 룰북 + Write final)]
final.md (본문 + <!-- HUMANIZE-SUMMARY --> 주석 블록)
```

shim은 graceful degrade 내장 — metrics 실패 시 점수 블록 없는 결합 파일을 쓰고 `00_metrics.error`를 남긴다. monolith는 v1.5처럼 동작하므로 오케스트레이터 분기 불필요.

### Strict 모드

```
입력 텍스트
    ↓
[ai-tell-detector] — 탐지 (span·category·severity·suggested_fix)
    ↓
[korean-style-rewriter] — 윤문 (finding 기반 수술적 수정)
    ↓
[병렬 검증]
    ├─ [content-fidelity-auditor] — 의미 동등성 감사 (13항)
    └─ [naturalness-reviewer]     — 잔존 + 과윤문 판정
    ↓
[오케스트레이터 종합 판정]
    ├─ accept → final.md + summary.md
    ├─ rewrite_round_2 → 윤문가 재호출 (최대 3회)
    ├─ rollback_and_rewrite → 문제 edit 롤백
    └─ hold_and_report → 사람 검토 권고
```

## 에이전트 구성 (12개 — 역할 구분 필수)

**런타임 5종** (스킬 실행 중 호출):

1. **humanize-monolith** — fast 전용. 한 콜에서 탐지·윤문·자체검증. 도구 호출 3회 캡 (v1.6.1).
2. **ai-tell-detector** — strict 탐지기. span 단위 JSON 리포트.
3. **korean-style-rewriter** — strict 윤문가. finding 기반 수술적 재작성, 변경률 모니터링.
4. **content-fidelity-auditor** — strict 내용 감사관. 13항 체크리스트 → 롤백 지시.
5. **naturalness-reviewer** — strict 자연스러움 리뷰어. 잔존·과윤문 계측, 등급 판정.

**유지보수 1종** (별도 명령으로만):

6. **korean-ai-tell-taxonomist** — 분류 체계 SSOT 관리. 신규 패턴 심사·승격.

**개발용 1회성 5종** (v2.0 학술 흡수 회차 전용 — 윤문 런타임에 로드되지 않음):

7. **translationese-research-distiller** — 번역투 학술 보고서 구조화 증류.
8. **korean-translation-scholar** — 학술 인용 계보를 taxonomy + scholarship.md 양면 안착.
9. **taxonomy-gap-analyzer** — 외부 후보 풀 vs 본진 3축 갭 매핑.
10. **post-editese-metric-engineer** — post-editese 3축을 metrics_v2.py로 코드화.
11. **quick-rules-integrator** — v2.0 변경 묶음의 quick-rules 안착 + 캡 회귀 검증 + PR 준비.

**미사용 1종**:

12. **humanize-web-architect** — 웹 확장 설계용. 웹앱(imnotai.kr)이 별도 코드베이스로 구현·운영 중이라 현재 미사용. 삭제·거취는 메인테이너 결정 대기.

## 심각도 기준

- **S1 결정적**: 한 번만 나와도 AI라고 확신하게 되는 패턴. 무조건 제거.
- **S2 강함**: 1~2회 허용, 3회+ 반복 시 제거.
- **S3 약함**: 다른 패턴과 중첩될 때만 문제.

## 품질 등급

- **A**: S1 0건, S2 2건 이하, score 개선 70%+
- **B**: S1 0건, S2 4건 이하, score 개선 50%+
- **C**: S1 1~2건 또는 과윤문 시그널 2개 — 2차 윤문
- **D**: S1 3건 이상 또는 심각한 과윤문 — 사람 검토

## 사용 방법

1. 새 세션에서 오케스트레이터 스킬 트리거:
   ```
   이 AI 글 자연스럽게 윤문해줘:
   ```
   (텍스트 첨부) — 또는 `/humanize` 슬래시 커맨드.
2. 5,000자 이하는 fast(monolith 1콜), `--strict`·8,000자+·부분 재실행은 strict 5인 파이프라인.
3. 결과: fast는 `final.md` 1개(끝에 summary 주석 블록), strict는 `final.md` + `summary.md`.

## 파일 시스템 접근 규칙

에이전트가 파일·디렉토리에 접근할 때는 전용 도구를 우선 사용한다.
`Bash` 툴의 `ls`·`cat`·`echo`는 실행 환경(OS·경로 형식)에 따라 동작이 달라져 예측 불가한 오류를 일으킬 수 있다. 예외: `prepare_monolith_input.py` shim 실행은 Bash `python3` 호출이 정규 경로다.

| 작업 | 올바른 방법 | 피할 방법 |
|---|---|---|
| 파일 존재 확인 | `Glob` 도구 | `Bash` 툴 `ls` |
| 디렉토리 목록 열거 | `Glob` 도구로 안의 표지 파일 매칭 (예: `*/01_input.txt`) | `Bash` 툴 `ls` |
| 파일 읽기 | `Read` 도구 | `Bash` 툴 `cat` / `head` |
| 파일 쓰기·편집 | `Write` / `Edit` 도구 | `Bash` 툴 리다이렉션 |

## 주요 금기

- 수치·단위·날짜 변경 금지.
- 고유명사·제품명·모델명 변경 금지.
- 큰따옴표 인용문 내부 변경 금지.
- 법률 조문·학술 개념어 임의 치환 금지.
- 새로운 주장·사실·예시 추가 금지.
- 원문에 있던 정보 누락 금지.

## 릴리스

버전 문자열이 흩어져 있어 릴리스마다 누락 사고가 반복됐다 (v1.6.1·v2.0에서 SKILL.md 두 번 연속 누락). **릴리스 전 반드시 `RELEASING.md` 체크리스트를 따를 것.** 태그는 발행 노트·문서 갱신 커밋이 main에 머지된 뒤에 찍는다.

## 확장 포인트

- **웹 서비스화**: 별도 코드베이스로 라이브 (imnotai.kr). 본 리포의 `humanize-web-architect`·`web-service-spec.md`는 설계 산출물로만 보존.
- **다국어 확장**: 일본어·중국어로 확장 시 언어별 taxonomy 분리 파일 추가.
- **장르 확장**: 현재 4장르(칼럼·리포트·블로그·공적). 학술 논문·법률 문서·제품 카피 추가 가능.

## 참고

- 오케스트레이터: `.claude/skills/humanize-korean/SKILL.md`
- 분류 체계: `.claude/skills/humanize-korean/references/ai-tell-taxonomy.md`
- 윤문 처방: `.claude/skills/humanize-korean/references/rewriting-playbook.md`
- 슬림 룰북(fast): `.claude/skills/humanize-korean/references/quick-rules.md`
- 학술 인용 SSOT: `.claude/skills/humanize-korean/references/scholarship.md`
- 웹 스펙: `.claude/skills/humanize-korean/references/web-service-spec.md`
