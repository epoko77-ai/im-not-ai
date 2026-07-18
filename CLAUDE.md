# Humanize KR — AI 한글 티 제거 하네스 (v2.1.0)

## 프로젝트 개요

AI(ChatGPT·Claude·Gemini 등)가 쓴 한글 텍스트를 "사람이 쓴 글처럼" 윤문해주는 이중 모드 하네스. 번역투·영어 인용 과다·기계적 병렬·관용구·피동태 남용·접속사 남발·리듬 균일성·이모지/불릿 과다 등 10대 카테고리 70개 AI 티 패턴(+A-17 hold 1건)을 탐지·분류해 **내용은 한 글자도 건드리지 않고** 문체·리듬·표현만 재작성한다.

- **Fast 모드 (디폴트)** — 정량 점수 shim 사전 처리 후 `humanize-monolith` 에이전트 1콜. 도구 호출 3회 캡, 5,000자 이하 2~3분. 장문(6,000자 초과)은 결정적 청킹(`--chunk`) 후 청크별 병렬 윤문 → 재조립.
- **정밀 모드 (`--strict`, 사용자 opt-in)** — 진단 1콜(`humanize-diagnostician`) → 겨냥 윤문(monolith 재사용) → 마무리 1콜(`humanize-finalizer`)의 3콜 구조. 입력 길이는 모드를 바꾸지 않는다(구 "8,000자+ 자동 승급"은 v2.1에서 폐지). 옛 5인 파이프라인은 v2.1에서 이 구조로 대체됐다.

## 철칙

1. **의미 불변 (Fidelity First)** — 사실·주장·수치·고유명사·인용은 100% 원문 보존.
2. **근거 기반 (Span-Grounded)** — 모든 변경은 탐지 finding에 연결. 탐지 없는 구간은 건드리지 않음.
3. **장르 유지 (Tone Match)** — 칼럼을 문학으로, 리포트를 에세이로 옮기지 않음.
4. **과윤문 금지 (No Over-Polish)** — 변경률 30% 초과 시 경고, 50% 초과 시 강제 중단.
5. **register 보존 — 양방향** — 격식체 입력은 격식체 출력, 구어 입력은 구어 출력. 원문보다 딱딱하게 만들지 않는다: **'-했-' → '-하였-' 치환 금지**, '~인데요/~거든요/~한 겁니다' 구어 종결 보존. (하향 금지만 있던 기존 단방향 규칙으로는 합쇼체가 유지되는 '했→하였' 상향을 못 잡았다.) AI 티는 문법·수사이지 격식 자체가 아니다.
6. **AI 티는 빼기만 하고 넣지 않는다 (No New Tells)** — 원문에 없던 상투구("기록적인 성과를 거두었다"·"괄목할 만한"·"~로 평가된다") 신규 삽입 금지. 살아있는 구어는 사람 글의 증거이므로 보존한다. 철칙 #2가 "탐지 없는 구간은 손대지 않는다"라면, #6은 "손대는 구간에도 새 AI 티를 심지 않는다" — 모순이 아니라 보완이다.

## 디렉토리 구조

```
im-not-ai/
├── CLAUDE.md                      # 본 파일 — 프로젝트 가이드
├── README.md / INSTALL.md         # 사용·설치 안내
├── RELEASING.md                   # 릴리스 체크리스트 (버전 문자열 전수 + 글로벌 심링크 동기화)
├── CONTRIBUTORS.md
├── .claude-plugin/                # Claude 플러그인 + 마켓플레이스 매니페스트
│   ├── plugin.json                # skills: ./.claude/skills/ · 에이전트는 루트 agents/ 자동탐색
│   └── marketplace.json           # /plugin marketplace add epoko77-ai/im-not-ai
├── gemini-extension.json          # Gemini CLI Extension 매니페스트
├── GEMINI.md                      # Gemini 에이전트 컨텍스트 (monolith 룰 인라인)
├── commands/                      # Gemini CLI 커스텀 명령 (/humanize-korean, /humanize, /humanize-redo)
├── install.sh / uninstall.sh / update.sh   # Claude·Codex·Gemini 전역 설치/제거 (심링크 기본)
├── scripts/
│   ├── prepare_monolith_input.py  # input shim — 정량 점수 + 결합 입력 (`--diagnosis`·`--chunk` 지원)
│   ├── reassemble_chunks.py       # 장문 청킹 재조립 (passthrough 원문 삽입 + 문자수 대사)
│   ├── verify_change_rate.py      # 변경률 게이트 — 철칙 #4의 결정적 판정 (exit code)
│   ├── build_quick_rules.py       # taxonomy quick 메타 → quick-rules.md 빌드 (ID 드리프트 차단)
│   ├── build_social_preview_v2.py
│   └── make_thumbnail.py
├── tests/                         # pytest — metrics 단위 + 청킹 + 빌드 sync + golden 픽스처
│   ├── test_metrics.py · test_metrics_v2.py · test_chunking.py · test_quick_rules_build.py
│   └── golden/                    # 윤문 품질 회귀 픽스처 + 결정적 채점기(checks.py)
├── agents/                        # 서브에이전트 9종 (플러그인 컨벤션 — 루트 agents/에 둬야 로드됨)
│   ├── humanize-monolith.md       # fast·정밀 공용 윤문 콜
│   ├── humanize-diagnostician.md  # 정밀 P1 진단 (지배 패턴 3~6개)
│   ├── humanize-finalizer.md      # 정밀 P3 마무리 (의미 15항 + 자연성)
│   ├── korean-ai-tell-taxonomist.md  # 유지보수 (SSOT 갱신)
│   └── … 개발용 지원 5종 (scholar·distiller·gap-analyzer·metric-engineer·integrator)
├── .claude/skills/                # 스킬 3종 (humanize-korean 오케스트레이터 + humanize·humanize-redo 진입)
│   └── humanize-korean/
│       ├── SKILL.md               # 오케스트레이터 (fast/정밀 분기·shim 배선, quick_rules_path: ${CLAUDE_SKILL_DIR}/...)
│       └── references/
│           ├── quick-rules.md          # fast 슬림 룰북 (build_quick_rules.py가 taxonomy에서 생성)
│           ├── quick-rules.header.md · quick-rules.footer.md  # 빌드 고정 템플릿
│           ├── ai-tell-taxonomy.md     # SSOT — 10대분류 × 활성 70 패턴 (+ _quick 빌드 메타)
│           ├── rewriting-playbook.md   # 카테고리별 치환 레시피
│           ├── metrics.py · metrics_v2.py     # v1.6 8종 + v2.0 post-editese 14종
│           ├── baseline.json · baseline_v2.json   # v1.6 baseline · v2.0(placeholder — calibration 대기)
│           ├── scholarship.md          # v2.0 학술 인용 외부 SSOT
│           └── web-service-spec.md     # 웹 확장 스펙 (옵션)
├── codex/skills/humanize-korean/  # Codex Fast Path 스킬 (references → SSOT 공유 심링크)
└── _workspace/                    # 런타임 산출물 (run_id별, gitignored)
    └── {YYYY-MM-DD-NNN}/
        ├── 01_input.txt · 00_metrics.json · 01_input_with_metrics.txt  # 원문·점수·결합
        ├── final.md                    # 윤문본 (끝에 <!-- HUMANIZE-SUMMARY --> 블록)
        ├── 01_chunk_{NN}… · 02_chunk_{NN}_rewritten.txt · 03_reassembled.md  # (장문 청킹)
        ├── 02_diagnosis.md             # (정밀 P1) 지배 패턴 진단
        ├── final_pre_finalize.md · 09_finalize.json   # (정밀 P3) 백업 · 판정
```

## 파이프라인

### Fast 모드 (디폴트)

```
01_input.txt
    ↓ [scripts/prepare_monolith_input.py --run-dir _workspace/{run_id} --genre {genre}]
00_metrics.json + 01_input_with_metrics.txt
    ↓ [humanize-monolith — 단일 호출, 도구 호출 3회 캡 (Read 입력 + Read 룰북 + Write final)]
final.md (본문 + <!-- HUMANIZE-SUMMARY --> 주석 블록)
    ↓ [scripts/verify_change_rate.py — 변경률 게이트 (exit code)]
```

shim은 graceful degrade 내장 — metrics 실패 시 점수 블록 없는 결합 파일을 쓰고 `00_metrics.error`를 남긴다. 장문(6,000자 초과)은 `--chunk`로 결정적 분할 후 청크별 monolith 병렬 호출(동시 최대 4) → `reassemble_chunks.py` 재조립.

### 정밀 모드 (3콜)

```
01_input.txt
    ↓ [shim] 01_input_with_metrics.txt
    ↓ [humanize-diagnostician]   — 지배 패턴 3~6개 진단 (P1)
02_diagnosis.md
    ↓ [shim --diagnosis] 진단+점수+원문 결합
    ↓ [humanize-monolith]        — 진단 겨냥 윤문 (장문이면 청크 병렬) (P2)
final.md
    ↓ [verify_change_rate.py]    — 변경률 게이트 (exit code, 결정적) (P2.5)
    ↓ [humanize-finalizer]       — 의미 15항 + 자연성 판정, 국소 보정 (P3)
final.md(보정) + 09_finalize.json
    ↓ [verify_change_rate.py]    — 최종 변경률 확정
```

finalize의 `verdict=hold_and_report`면 사람 검토 권고. 수렴 판정은 LLM 재탐지가 아니라 `verify_change_rate.py`(결정적, exit code)가 내린다.

## 에이전트 구성 (9개 — 역할 구분 필수)

**런타임 3종** (스킬 실행 중 호출):

1. **humanize-monolith** — fast·정밀 공용 윤문 콜. 한 콜에서 탐지·윤문·자체검증. 도구 호출 3회 캡 (v1.6.1).
2. **humanize-diagnostician** — 정밀 P1 진단. 글 전체의 지배 패턴 3~6개를 본진 ID로 진단 → `02_diagnosis.md`.
3. **humanize-finalizer** — 정밀 P3 마무리. 원문 직접 대조로 의미 15항 + 자연성(잔존·과윤문 양방향) 판정, 문제 구간만 국소 보정 → `09_finalize.json`. 도구 호출 4회 캡.

**유지보수 1종** (별도 명령으로만):

4. **korean-ai-tell-taxonomist** — 분류 체계 SSOT 관리. 신규 패턴 심사·승격.

**개발용 1회성 5종** (v2.0 학술 흡수 회차 전용 — 윤문 런타임에 로드되지 않음):

5. **translationese-research-distiller** — 번역투 학술 보고서 구조화 증류.
6. **korean-translation-scholar** — 학술 인용 계보를 taxonomy + scholarship.md 양면 안착.
7. **taxonomy-gap-analyzer** — 외부 후보 풀 vs 본진 3축 갭 매핑.
8. **post-editese-metric-engineer** — post-editese 3축을 metrics_v2.py로 코드화.
9. **quick-rules-integrator** — v2.0 변경 묶음의 quick-rules 안착 + 캡 회귀 검증 + PR 준비.

**은퇴 (v2.1)**: 옛 strict 5인 파이프라인의 `ai-tell-detector`·`korean-style-rewriter`·`content-fidelity-auditor`·`naturalness-reviewer`와 웹 확장 설계용 `humanize-web-architect`는 v2.1에서 은퇴(정의 파일 삭제). 탐지·감사·리뷰 역할은 diagnostician·finalizer와 `verify_change_rate.py` 게이트가 대체했다.

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
2. 디폴트는 fast(monolith 1콜, 장문 6,000자+는 청크 병렬). `--strict`·"정밀 모드"·부분 재실행은 정밀 3콜(진단→겨냥 윤문→finalize). 입력 길이는 모드를 바꾸지 않는다.
3. 결과: fast는 `final.md` 1개(끝에 summary 주석 블록), 정밀은 `final.md` + `02_diagnosis.md`·`09_finalize.json`.

## 파일 시스템 접근 규칙

에이전트가 파일·디렉토리에 접근할 때는 전용 도구를 우선 사용한다.
`Bash` 툴의 `ls`·`cat`·`echo`는 실행 환경(OS·경로 형식)에 따라 동작이 달라져 예측 불가한 오류를 일으킬 수 있다. 예외: `prepare_monolith_input.py`(shim)·`verify_change_rate.py`(변경률 게이트)·`reassemble_chunks.py`(청킹 재조립) 실행은 Bash `python3` 호출이 정규 경로다.

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

- **웹 서비스화**: 별도 코드베이스로 라이브 (imnotai.kr). 본 리포의 `web-service-spec.md`는 설계 산출물로만 보존 (설계 에이전트 `humanize-web-architect`는 v2.1에서 은퇴).
- **다국어 확장**: 일본어·중국어로 확장 시 언어별 taxonomy 분리 파일 추가.
- **장르 확장**: 현재 4장르(칼럼·리포트·블로그·공적). 학술 논문·법률 문서·제품 카피 추가 가능.

## 참고

- 오케스트레이터: `.claude/skills/humanize-korean/SKILL.md`
- 분류 체계: `.claude/skills/humanize-korean/references/ai-tell-taxonomy.md`
- 윤문 처방: `.claude/skills/humanize-korean/references/rewriting-playbook.md`
- 슬림 룰북(fast): `.claude/skills/humanize-korean/references/quick-rules.md`
- 학술 인용 SSOT: `.claude/skills/humanize-korean/references/scholarship.md`
- 웹 스펙: `.claude/skills/humanize-korean/references/web-service-spec.md`
