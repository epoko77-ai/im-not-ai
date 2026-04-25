<p align="center">
  <img src="assets/social-preview.png" alt="im-not-ai — 한글 AI 티 제거기" width="820">
</p>

# Humanize KR — 한글 AI 티 제거기 v1.2

AI(ChatGPT · Claude · Gemini 등)가 쓴 한글 글을 **내용은 한 글자도 건드리지 않고** 문체 · 리듬 · 표현만 자연스러운 한국어로 되돌리는 Claude Code 스킬입니다. 

번역투, 과도한 영어 인용, 기계적 병렬 ("첫째 · 둘째 · 셋째"), "결론적으로 / 시사하는 바가 크다" 같은 AI 특유 관용구, 피동태 남용, 문두 접속사 남발, 이모지·불릿 남용 등 **10대 카테고리 × 40+ 서브 패턴**을 심각도(S1/S2/S3)로 분류해 스팬 단위로 탐지한 뒤, 윤문합니다. 

## 왜 한글 특화인가

영어권 humanizer(QuillBot · Hix · Undetectable AI)는 한국어에 약합니다. 한글 AI 글의 티는 대부분 **영어 번역투**에서 나옵니다. 

- "AI 기술을 **통해** 효율을 높**일 수 있다**" → "AI로 효율을 높인다"
- "이에 **있어서** 중요한 **점은**" → "여기서 중요한 건"
- "~**에 의해** 생성된" → "~가 만든"
- "**결론적으로**, 이는 **시사하는 바가 크다**" → (삭제)

이 하네스는 그 한글 고유 패턴을 SSOT로 정리하고, 탐지·윤문·내용 감사·자연스러움 검증을 분리된 에이전트로 수행합니다.

## 4대 철칙

1. **의미 불변** — 사실 · 주장 · 수치 · 고유명사 · 직접 인용은 100% 원문 보존.
2. **근거 기반** — 탐지된 span에만 수술적 수정. 탐지 없는 구간은 건드리지 않음.
3. **장르 유지** — 칼럼을 문학으로, 리포트를 에세이로 옮기지 않음.
4. **과윤문 금지** — 변경률 30% 초과 시 경고, 50% 초과 시 강제 중단.

## 아키텍처

```
입력 텍스트
    ↓
[ai-tell-detector]        ── 탐지 (span · category · severity)
    ↓
[korean-style-rewriter]   ── finding 기반 수술적 윤문
    ↓
[병렬 검증 팀]
    ├─ [content-fidelity-auditor]  ── 13항 체크리스트로 의미 동등성 감사
    └─ [naturalness-reviewer]      ── 탐지 재실행으로 잔존·과윤문 판정
    ↓
[오케스트레이터 종합]
    ├─ accept              → final.md + summary.md
    ├─ rewrite_round_2     → 2차 윤문 (최대 3회)
    ├─ rollback_and_rewrite → 문제 edit 롤백
    └─ hold_and_report     → 사람 검토 권고
```

## 6인 에이전트

| 에이전트 | 역할 |
|---------|------|
| `korean-ai-tell-taxonomist` | 분류 체계(SSOT) 관리, 신규 패턴 심사 승격 |
| `ai-tell-detector` | span 단위 JSON 탐지 리포트 생성 |
| `korean-style-rewriter` | finding 기반 수술적 윤문, 변경률 모니터링 |
| `content-fidelity-auditor` | 의미 동등성 감사 (13항), 훼손 시 롤백 지시 |
| `naturalness-reviewer` | 잔존 AI 티 · 과윤문 · 자연도 판정, 품질 등급 A~D |
| `humanize-web-architect` | (옵션) Next.js 15 + Vercel 웹 서비스 확장 설계 |

## AI 티 분류 체계 (요약)

| ID | 대분류 | 대표 서브 패턴 |
|----|-------|---------------|
| A | 번역투 | "~를 통해", "~에 대해", "~에 있어서", 이중 피동 "~되어진다", "가지고 있다" |
| B | 영어 인용·용어 과다 | 과도한 괄호 병기, 번역 가능한 영어 그대로 |
| C | 구조적 AI 패턴 | 기계적 "첫째/둘째/셋째", 과도한 불릿·헤딩·이모지 |
| D | AI 특유 관용구 | "결론적으로", "시사하는 바가 크다", "주목할 만하다", "혁신적인" |
| E | 리듬 균일성 | 문장 길이 표준편차 낮음, 동일 종결어미 반복 |
| F | 수식·중복 | "매우", "정말", 동의어 이중 수식, "~적/~성/~화" 남발 |
| G | Hedging 남용 | "~할 수 있을 것으로 보인다" 다중 완곡 |
| H | 접속사 남발 | 문두 "또한/따라서/즉/나아가" 연속 |
| I | 형식명사 과다 | "것이다", "점", "수", "바", "~할 필요가 있다" |
| J | 시각 장식 남용 | 과도한 **볼드**, "따옴표", 대시(—) 남발 |

전체 40+ 서브 패턴과 처방: [`ai-tell-taxonomy.md`](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md) · [`rewriting-playbook.md`](.claude/skills/humanize-korean/references/rewriting-playbook.md)

## 심각도 & 품질 등급

**심각도**
- **S1 결정적**: 한 번만 나와도 AI 확신. 무조건 제거.
- **S2 강함**: 1~2회 허용, 3회+ 반복 시 제거.
- **S3 약함**: 다른 패턴과 중첩될 때만 문제.

**품질 등급 (윤문 후)**
- **A**: S1 0건, S2 ≤2건, 점수 개선 70%+
- **B**: S1 0건, S2 ≤4건, 개선 50%+
- **C**: S1 1~2건 or 과윤문 시그널 2개 → 2차 윤문
- **D**: S1 3건+ or 심각한 과윤문 → 사람 검토

## 사용법 — 5분이면 따라합니다

### 0. 전제

[Claude Code](https://claude.com/claude-code)가 설치돼 있어야 합니다. Mac · Windows · Linux 모두 지원합니다.

설치 확인:
```bash
claude --version
```

> Claude Code는 터미널에서 Claude(Anthropic의 AI)와 대화하며 파일을 같이 편집하는 CLI입니다. 이 리포의 스킬·에이전트는 Claude Code에서만 작동합니다. (웹 버전 Claude.ai나 일반 ChatGPT에서는 안 됩니다.)

### 1. 리포 받기

```bash
git clone https://github.com/epoko77-ai/im-not-ai.git
cd im-not-ai
```

### 2. 이 폴더 안에서 Claude Code 켜기

```bash
claude
```

> **중요:** 꼭 `im-not-ai` 폴더 **안에서** 실행하세요. 다른 위치에서 켜면 이 리포의 스킬이 로드되지 않아 일반 Claude Code처럼 동작합니다.

### 3. AI가 쓴 한글 글 붙여넣고 부탁하기

평소 말투 그대로 쓰면 됩니다:

```
이 AI 글 자연스럽게 윤문해줘:

[ChatGPT / Claude / Gemini 초안 여기에 붙여넣기]
```

아래 표현 중 아무거나 쓰면 스킬이 자동 발동합니다:
- "AI 티 없애줘"
- "GPT 문체 제거해줘"
- "사람이 쓴 것처럼 윤문해줘"
- "번역투 제거"
- "한글 AI 윤문"

명령어·슬래시·옵션 없이 **자연어 한 문장으로 충분합니다.**

### 4. 결과 확인

Claude Code가 이 순서로 처리합니다:

1. **탐지** — 어디가 어떤 AI 티인지 10대 카테고리 × 심각도로 정리
2. **윤문** — 내용·수치·고유명사·인용은 보존하고 문체·리듬만 수정
3. **검증** — 의미가 훼손됐는지 감사 + 다시 AI스럽지 않은지 재측정
4. **출력** — 윤문본, 주요 변경 diff, 품질 등급(A/B/C/D), 잔존 패턴

터미널에서 윤문본을 바로 받아볼 수 있고, 세부 산출물은 리포 안의 `_workspace/{실행날짜-번호}/`에 저장됩니다:

| 파일 | 내용 |
|------|------|
| `01_input.txt` | 원문 그대로 |
| `02_detection.json` | AI 티 탐지 리포트 (위치·종류·심각도) |
| `03_rewrite.md` | 윤문본 |
| `04_fidelity_audit.json` | 내용 훼손 감사 결과 |
| `05_naturalness_review.json` | 자연도 재측정 결과 |
| `summary.md` | 점수 변화·주요 변경·등급 요약 |

### 5. 결과가 맘에 안 들면

그대로 말씀하시면 됩니다. 재실행·수정 명령을 따로 외울 필요 없습니다:

- **"이 문단만 다시 윤문해줘"** — 해당 구간만 재시도
- **"번역투만 더 손봐줘"** (또는 "관용구만 다시") — 특정 카테고리만 재처리
- **"윤문 강도 낮춰줘"** — 보수적 윤문 (결정적 패턴만 제거)
- **"원문 톤을 더 살려줘"** — 변경률 상한을 낮춰 원문 유지
- **"2차 윤문해줘"** — 현재 결과를 한 번 더 다듬기

### 6. 다른 글로 또 돌리고 싶을 때

Claude Code 세션 안에서 새 글을 붙여넣고 똑같이 부탁하면 됩니다. 실행마다 새 `_workspace/{날짜-번호}/` 폴더가 만들어져 이전 결과와 섞이지 않습니다.

## Do-NOT List (탐지·윤문 대상 제외)

- 수치 · 단위 · 날짜
- 고유명사 · 인명 · 제품명 · 모델명
- 큰따옴표 내부 직접 인용
- 법률 · 규정 조문
- 학술 개념어 (불가피한 경우)

## 웹 서비스 확장 (옵션)

`humanize-web-architect` 에이전트가 Next.js 15 App Router + Vercel Fluid Compute + AI Gateway 기반 웹앱 설계를 담당한다. UX는 4화면(입력 → 탐지 하이라이트 → 좌우 diff → 윤문본 복사). 상세: [`web-service-spec.md`](.claude/skills/humanize-korean/references/web-service-spec.md).

로드맵: v0 MVP(익명·단일 호출) → v1(로그인·히스토리) → v2(Pro/Team · API · 웹훅) → v3(Chrome Extension) → v4(일본어·중국어 확장).

## v1.2 — 작가 voice profile (2026-04-25)

작가/책마다 고유한 voice가 일반 분류 패턴과 충돌하는 경우(예: 단단한 서술체 voice의 의도된 종결어미 반복, em-dash 리듬 장치, 책 mandate "~수 있다 사용 권장")를 위한 **opt-in 명시 주입** 메커니즘을 추가했습니다. v1.2의 모든 변경은 v1.1과 **하위 호환**입니다 — voice profile 미주입 시 v1.1과 100% 동일하게 동작합니다.

**핵심 변경**

- **권한 위계 §1~§6** 신설 — 객관 분류 우선, voice profile은 opt-in, 무력화 불가 패턴(A-8/C-5/D-1~D-6) 영구 default-on, naturalness-reviewer 분리 검증층 보존 (`ai-tell-taxonomy.md`)
- **`author-context.yaml`** 스키마 — 패턴 ID 단위 on/off + 임계 완화(multiplier 캡: 일반 ≤2.0, D-1~D-6 ≤1.5) + Do-NOT 키워드 화이트리스트만 허용 (`references/author-context-schema.md`)
- **자유 텍스트 mandate 금지** — LLM 자의 해석 차단. 모든 override는 구조화된 필드 단위
- **Schema validator** — 무력화 불가 disable 거부, multiplier 캡 위반 거부, prompt injection escape character 검증
- **Telemetry** — `voice_profile_log.json` 발행 (적용·거부·trigger 키워드 추적)
- **경로 토큰화** — SKILL.md 절대 경로 제거, `_workspace/`는 cwd 기준 (글로벌 설치 지원)

**사용 예시 (단행본 비소설 작가)**

```yaml
# author-context.yaml — 작업 cwd 또는 _workspace/{run_id}/에 명시 배치
version: "1.0"

profile:
  author: "Won Seongmuk"
  work: "단행본 비소설 (8.5만 자)"
  notes: "단단한 서술체, em-dash 리듬 장치"

pattern_overrides:
  - id: "J-3"            # em-dash 임계 완화
    action: "relax"
    multiplier: 2.0
  - id: "A-10"           # "~수 있다" 사용 권장 mandate
    action: "disable"

do_not_extra:            # 작가 고유 표현 보호
  - "1인칭 진입"

reviewer_contract:
  naturalness_reviewer_voice_blind: true   # §5 강제
```

**Issue #1 후속 — 외부 contributor**

v1.2는 [Issue #1](https://github.com/epoko77-ai/im-not-ai/issues/1)에서 8.5만 자 단행본 비소설 적용 후기·개선 제안 4건을 보내주신 [@simonsez9510](https://github.com/simonsez9510)의 기여로 시작됐습니다. 그분의 [PR #3](https://github.com/epoko77-ai/im-not-ai/pull/3)에서 다운스트림 caller adapter reference (`references/proposals/voice-aware-adapter.md`)와 multiplier 캡·`reviewer_contract` 강제 등 schema 강화 통찰을 받아 메인테이너 schema에 흡수했습니다.

**v1.2 회귀 안전성**

v1.2는 코드 변경이 거의 없고 대부분 문서·정책·schema 추가입니다. voice profile 미주입 모드(default)에서는 v1.1과 동일한 6인 에이전트가 동일한 입출력으로 동작합니다. voice profile 주입 모드는 신기능이라 회귀 대상이 아니며, 외부 회귀 케이스 검증 결과는 v1.2.1에서 별도 hotfix로 반영합니다(외부 케이스 모집은 별도 Issue로 진행 예정).

전체 v1.2 변경 이력: [`ai-tell-taxonomy.md` 버전 관리](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md#버전-관리)

---

## 라이선스 & 윤리

- 본 도구는 "AI 탐지기 우회(Undetectable AI)"가 아니라 **한글 글쓰기 품질 개선**을 목적으로 합니다.
- 학술 제출·저널리즘 진실성 보증 도구가 아닙니다
- 분류 체계(`ai-tell-taxonomy.md`)는 연구·교육 목적 자유 이용 가능합니다.

## 기여

새로운 AI 티 패턴을 발견했다면 `references/ai-tell-taxonomy.md` 하단 버전 섹션에 후보로 제안해 주세요. 실증 사례 2건 이상을 첨부하면 분류학자 에이전트가 v1 → v2 승격시킵니다.

---

Built with [Claude Code](https://claude.com/claude-code) + https://github.com/revfactory/harness 하네스 아키텍처 기반 프로젝트.
