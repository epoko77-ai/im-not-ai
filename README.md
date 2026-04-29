<p align="center">
  <img src="assets/social-preview.png" alt="im-not-ai — 한글 AI 티 제거기" width="820">
</p>

# Humanize KR — 한글 AI 티 제거기 v1.5

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

## 아키텍처 (v1.5)

**Fast 모드 (디폴트, 5,000자 이하)**

```
입력 텍스트
    ↓
[humanize-monolith]   ── 한 콜 안에서 탐지 → 윤문 → 자체검증 일괄
    ↓                     (도구 호출 4~5회 캡, opus, ~3분)
final.md + summary.md
```

**Strict 모드 (`--strict` 또는 8,000자+ 자동 승급)**

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

## 7인 에이전트

| 에이전트 | 모드 | 역할 |
|---------|---|------|
| `humanize-monolith` | **Fast 디폴트** | 단일 호출 윤문 (탐지·윤문·자체검증 일괄, 도구 호출 4~5회 캡) |
| `ai-tell-detector` | Strict | span 단위 JSON 탐지 리포트 생성 |
| `korean-style-rewriter` | Strict | finding 기반 수술적 윤문, 변경률 모니터링 |
| `content-fidelity-auditor` | Strict | 의미 동등성 감사 (13항), 훼손 시 롤백 지시 |
| `naturalness-reviewer` | Strict | 잔존 AI 티 · 과윤문 · 자연도 판정, 품질 등급 A~D |
| `korean-ai-tell-taxonomist` | 별도 명령 | 분류 체계(SSOT) 관리, 신규 패턴 심사 승격 |
| `humanize-web-architect` | 옵션 | Next.js 15 + Vercel 웹 서비스 확장 설계 |

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

Claude Code에서는 세 가지 방법 중 편한 쪽으로 사용합니다. Codex 사용자는 아래 **방법 D**의 community port를 참고하세요.

**방법 A — 자연어 한 문장 (가장 쉬움)**

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

**방법 B — 슬래시 커맨드** *(v1.2~)*

```
/humanize [윤문할 텍스트 또는 파일 경로]
```

옵션을 인자 끝에 자연어로 적을 수 있습니다: `장르: 칼럼`, `강도: 적극`, `최소심각도: S1`. 결과가 마음에 안 들면 `/humanize-redo "번역투만 다시"` 같은 식으로 재실행. 두 커맨드 정의: [`commands/`](.claude/commands/)

**방법 C — Plugin / 자동 설치기** *(@gaebalai 포크)*

[`gaebalai/im-not-ai`](https://github.com/gaebalai/im-not-ai) 포크가 Claude Code Plugin/Marketplace 규격으로 패키징되어 있습니다. `/plugin install humanize-korean@epoko77-ai-plugins` 또는 `./scripts/install.sh --target ~/my-project` 한 줄로 설치 가능합니다. 본체 정식 Plugin 지원은 v1.6 검토 중입니다 ([Issue 추적 예정](https://github.com/epoko77-ai/im-not-ai/issues)).

**방법 D — Codex Plugin (community)**

[`Squirbie/im-not-ai-codex`](https://github.com/Squirbie/im-not-ai-codex)에서 Codex Desktop/CLI용 community plugin 포트를 제공합니다. 원본 taxonomy/playbook을 유지하고 Codex plugin/skill 구조에 맞게 어댑터화한 별도 배포판이며, 공식 Claude Code 버전과 분리되어 관리됩니다.

설치:

```bash
codex plugin marketplace add Squirbie/im-not-ai-codex
```

**방법 E — Web UI (비공식)**

Claude Code 설치 없이 웹에서 바로 윤문을 체험해볼 수 있는 커뮤니티 제작 포트입니다.
- 접속: [im-not-ai-ocx.illuwa.click](https://im-not-ai-ocx.illuwa.click/)
- 비고: 터미널 환경이 낯설거나 즉석에서 간단한 테스트가 필요할 때 권장합니다. (제작: [@illuwa](https://github.com/illuwa))

### 4. 결과 확인

Claude Code가 입력 길이·옵션에 따라 두 모드 중 하나로 처리합니다.

**Fast 모드 (디폴트, 5,000자 이하 · ~3분)** — `humanize-monolith` 한 콜이 메모리 안에서 탐지·윤문·자체검증을 모두 끝냅니다. 산출물은 `_workspace/{실행날짜-번호}/`에 두 파일:

| 파일 | 내용 |
|------|------|
| `01_input.txt` | 원문 그대로 |
| `final.md` | 윤문본 |
| `summary.md` | 메트릭 · 카테고리 탐지 (before/after) · 자체검증 6항 · 등급 · 주요 변경 하이라이트 |

**Strict 모드 (`--strict` 또는 8,000자+ 자동 승급 · 더 정밀)** — 5인 파이프라인이 단계별 산출물을 분리해 저장합니다:

| 파일 | 내용 |
|------|------|
| `01_input.txt` | 원문 그대로 |
| `02_detection.json` | AI 티 탐지 리포트 (위치·종류·심각도) |
| `03_rewrite.md` | 윤문본 |
| `04_fidelity_audit.json` | 내용 훼손 감사 결과 |
| `05_naturalness_review.json` | 자연도 재측정 결과 |
| `final.md` + `summary.md` | 최종 윤문본 + 점수·주요 변경·등급 요약 |

부분 재실행("이 카테고리만 다시"·"2차 윤문")은 strict 모드로 자동 전환됩니다.

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

## v1.5 — v1.1 베이스라인 + Monolith Fast Path (2026-04-26)

v1.2(voice profile)·v1.3(candidate pool)·v1.4(역할별 모델 분산)이 모두 핫패스 비용을 잡지 못했음이 검증으로 확인됐습니다. 5,000자 입력 윤문 wall-clock이 **25분**까지 늘어났고, v1.4의 모델 다운그레이드로도 detector 1콜이 **8분**이었습니다. 진단 결과 진범은 모델이 아니라 **에이전트 간 컨텍스트 재로드 + 에이전트 내부 도구 호출 chain 누적**이었습니다.

v1.5는 v1.2~v1.4를 모두 폐기하고 **v1.1 단순 구조로 롤백한 뒤 단일 호출 monolith fast path만 추가**한 설계입니다.

**핵심 변경**

- **v1.2~v1.4 폐기 (롤백)** — 5인 에이전트 정의를 v1.1 commit `f25ee64` 시점으로 복원, voice profile·candidate pool 관련 reference 4개 파일 삭제, 권한 위계 §1~§6 절 제거
- **Monolith Fast Path 신설 (디폴트)** — `humanize-monolith` 에이전트(opus): 한 콜 안에서 탐지·윤문·자체검증 일괄 처리, 도구 호출 4~5회 캡(Read 입력 + Read 룰북 + Write final + Write summary), 5,000자 이하 wall-clock 2~3분 목표
- **`quick-rules.md` 신설 (~150줄)** — 본진 386줄에서 S1·S2 핵심 패턴만 추린 슬림 룰북. monolith 전용. 자체검증 6항 + 등급 기준 포함
- **Strict 모드 보존** — v1.1 5인 파이프라인을 `--strict` 또는 8,000자+ 자동 승급으로 그대로 유지. 부분 재실행("이 카테고리만 다시"·"2차 윤문")도 strict 자동 전환
- **분류 체계 본진 보존** — `ai-tell-taxonomy.md`의 v1.2~v1.3.1 발굴 신규 패턴(C-9·C-10·D-7·H-3·I-3·I-4 보강 등) 모두 그대로 유지

**검증 결과 (같은 칼럼 2,604자)**

| 항목 | v1.4 (detector haiku 1콜) | v1.5 (monolith opus 1콜) |
|---|---|---|
| Wall-clock | 7분 58초 | **3분 28초** |
| 도구 호출 | 12회 | **4회** |
| 토큰 | 113,621 | 68,045 |
| 윤문 등급 | (단계 1만 끝, 미완) | **A (자체검증 6/6, 변경률 22%)** |

5인 파이프라인 25분 → monolith 3.5분, 약 86% 단축. opus로 격상하고도 도구 호출 chain을 압축한 게 결정적이었습니다.

**호환성 안내**

- v1.3.1 사용자: `author-context.yaml`(voice profile)이 더 이상 작동하지 않습니다. 메인테이너 측 실전 사용 사례가 미확보였고, 필요 시 v1.6에서 monolith 옵션으로 재도입을 검토합니다.
- 슬래시 커맨드 `/humanize`·`/humanize-redo`는 그대로. 내부에서 v1.5 fast/strict 분기 자동.

**회고**

v1.4 작업은 모델 다운그레이드를 진단의 1순위로 잡았으나, 실측이 그 가설을 부쉈습니다. opus로 격상하고도 도구 호출 chain을 압축하니 더 빨라졌어요 — 모델보다 **에이전트 내부 도구 호출 횟수**가 wall-clock의 진짜 변수였습니다. 이 교훈이 v1.6 이후 설계의 1번 원칙입니다.

**본질 테스트 — 5편 다양성 검증 (2026-04-26)**

v1.5 발행 직후, 메인테이너가 원래 계획했던 본질 테스트(원본 AI 글이 사람 글로 진짜 변하나)를 5편으로 진행했습니다. 회차 1 합성 제조업 칼럼 1편 + 회차 3 Gemini 직접 호출 4편(핀테크 칼럼·제조 리포트·교육 블로그·헬스케어 정책)으로 모델·장르·길이 다양성을 확보.

| run | 입력 | 길이 | 변경률 | 등급 |
|---|---|---|---|---|
| 003 | 합성 제조 칼럼 | 716자 | 14% | **A** |
| 004 | Gemini 핀테크 칼럼 | 2,725자 | 18% | **A** |
| 005 | Gemini 제조 리포트 | 2,572자 | 18% | **A** |
| 006 | Gemini 교육 블로그 | 2,445자 | 22% | **A** |
| 007 | Gemini 헬스케어 정책 | 2,316자 | 18% | **A** |

**5편 모두 등급 A · 자체검증 6/6 통과 · 변경률 안전 구간(10~25%).** Gemini 시그니처(C-10 콜론 헤딩 · D-7 변환 공식 · D-4 hype 어휘 · J-2 따옴표 강조 · J-1 마크다운 ** 강조 · G-1 미래 단정 · I-4 권고형 결말)가 4개 장르 모두에서 일관되게 제거됐고, 고유명사·수치·인용은 100% 보존됐습니다.

**가속 효과 누적**: v1.3.1로 5편 직렬 처리 추정 약 125분 → v1.5 monolith 병렬 약 7분(병렬 효과 포함). **94% 단축, 17~18배 가속.** 메모리에 가설로 박아둔 "wall-clock 1/7로 줄어 7배 샘플 처리 가능"이 실측에서 18배로 확인됐습니다.

관련 PR: [#13](https://github.com/epoko77-ai/im-not-ai/pull/13) · 태그: [`v1.5.0`](https://github.com/epoko77-ai/im-not-ai/releases/tag/v1.5.0)

## v1.3.1 hotfix — 회차 3 Gemini 직접 호출 검증 + 본진 신규 2건·보강 3건 (2026-04-25)

v1.3 발행 직후, 사용자께서 직접 Gemini API 키를 제공해 회차 3 진짜 외부 데이터 검증을 진행했습니다. Gemini Pro 2.5 직접 호출 4편(약 10,058자, 자연 prompt만 사용)에서 본진 신규 2건과 보강 3건을 추가로 영구 반영하고, 회차 2 hold 후보의 모델 분산 검증을 마쳤습니다.

**본진 신규 2건 (Gemini-우세 시그니처)**

- **C-10 콜론 부제 헤딩 공식** "X: Y" 또는 "X: A에서 B로" — Gemini가 헤딩에 거의 자동으로 콜론을 사용하는 시그니처 (8회·3파일·3도메인 분산)
- **D-7 변환 공식** "X에서 Y로 / X을 넘어 Y로" — 패러다임 전환·진화·고도화를 표현할 때 자동 등장 (7회·2파일·2도메인)

**본진 보강 3건**

- **D-4 hype 어휘 셋 확장** — 본진 "혁신적·획기적·전례 없는"에 Gemini 어휘 추가: "압도적·막강한·폭발적·파격적·대대적·강력한·치열한·뜨거운"
- **J-2 빈도 임계 명시** — 한 문서에 따옴표 강조 어휘 5회 초과 시 S2 강화 (Gemini 한 문서 17~33회 사례)
- **I-4 권고형 결말 변종 추가** — 본진 "~할 필요가 있다"에 정책·보고서 결말 "~해야 한다·~해야 합니다" 변종 추가, 한 문서 5회 초과 임계

**회차 2 hold 후보 검증 결과 — GPT vs Gemini 모델 시그니처 차이**

| 회차 2 hold 후보 | GPT 빈도 | Gemini 빈도 | 결론 |
|---|---|---|---|
| "결국" 문두 단언 | 9+ | 1 | **GPT-우세 시그니처** |
| "X은 A가 아니라 B다" 부정-긍정 대구 | 7+ | 2 | **GPT-우세 시그니처** |
| 5~8개 영역 콤마 빠른 나열 | 4 | 0 | **GPT-특유 가능성 매우 강함** |

회차 2 hold 후보 3건이 Gemini에서 거의 재현되지 않았다는 사실은 **분류 체계에 "모델 우세 분포" 메타데이터 차원 도입 필요성**을 시사합니다(v1.4 검토 사항). 회차 4에서 국내 모델·Claude 데이터로 모델 분포를 확정한 뒤 결정합니다.

**회차 1·2·3 누적 결과 — v1.2 신규 0건이 v1.3.1에서 신규 3·보강 6건으로**

| 회차 | 데이터 | 본진 신규 | 본진 보강 | 누적 효과 |
|------|--------|----------|----------|----------|
| 1 | Claude 합성 샘플 2건 | C-9 (1) | I-2 (1) | 인프라 검증 |
| 2 | 뉴스핌 외부 GPT 2건 | 0 | I-3·H-3 (2) | Gate 1.3 보호장치 검증 |
| 3 | Gemini 직접 호출 4건 | C-10·D-7 (2) | D-4·J-2·I-4 (3) | 모델 분산 확보 + GPT/Gemini 차이 발견 |
| **합계** | 8건 (3 모델 × 다양 장르) | **3건** | **6건** | v1.2 멈춤 → v1.3.1 풍부 |

전체 v1.3.1 변경 이력: [`ai-tell-taxonomy.md` 버전 관리](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md#버전-관리)

## v1.3 — 서브 패턴 발굴 운영 체계 + 본진 신규 1건·보강 3건 (2026-04-25)

**에이전트들이 실전에서 만난 미분류 의심 패턴을 단일 풀에 누적·점검·승격하는 운영 인프라**를 도입하고, 발행 전 두 회차의 파일럿(회차 1 합성 샘플 인프라 검증 + 회차 2 외부 매체 진짜 GPT 출력 분석)에서 본진 신규 1건(`C-9` 숫자 괄호 인덱싱) + 본진 보강 3건(`I-2` 결합형 · `I-3` 결말 변종 · `H-3` 메타 진입 변종)을 영구 반영하고 hold 4건을 풀에 누적했습니다. v1.1까지는 패턴 추가가 사람의 1회성 결정이었고, v1.2에서는 voice profile 권한 위계가 들어왔다면, v1.3은 **분류 체계 자체가 시간을 따라 자라나는 구조**를 만듭니다.

v1.3은 v1.2와 **하위 호환**입니다 — 에이전트 입출력 변경 없음, voice profile 동작 동일. 본진 신규 1건은 v1.2 이후 멈춰 있던 패턴 발굴이 새 인프라로 깨지는지 검증하는 파일럿 결과이며, 새로 추가된 풀 적재는 부수 효과이고 적재 실패가 메인 파이프라인을 막지 않습니다.

**핵심 변경**

- **Pattern candidates 풀** (`references/pattern-candidates.md`) — 본진 승격 전 모든 의심 패턴을 누적하는 단일 그릇. 임시 ID(`cand-{대분류}-{YYYY}-{NNN}`), 4상태(pending/promoted/rejected/merged), 기각 사유 5종 표준 라벨, 90일 미재현 자동 만료
- **3개 에이전트 풀 적재 채널** — `ai-tell-detector`(미분류 span), `korean-style-rewriter`(윤문 저항·반복 잔존), `naturalness-reviewer`(voice profile 미주입 외부 시각). 각자 적재 트리거·필수 필드·중복 검사 절차 명문화
- **taxonomist 풀 운영자 역할** — 4가지 trigger(사용자 명시 / pending 10건 임계 / 단일 후보 occurrences ≥ 3 / 외부 PR) 기반 정기 점검. 6단계 점검 절차, `_workspace/taxonomy_changelog.md` 회차 기록 표준화
- **샘플 수집 파이프라인** (`references/sample-collection.md`) — 4축 다양성 매트릭스(모델·장르·길이·작가), 4종 채널(사용자 자발·합성 샘플·공개 데이터·외부 contributor), 익명화·저작권 5대 정책
- **승격 자동 검증 체크리스트** (`references/promotion-checklist.md`) — 6개 게이트(사전 점검·재현·본진 중복·분류 적합성·처방 적합성·본진 위계). 일부 게이트는 향후 스크립트 자동화 가능

**왜 이 구조인가**

v1.1까지의 패턴 7건 승격은 사람이 한 번에 작업한 결과였습니다. 이후 실전 사용 중 발견되는 의심 패턴이 늘어도 적재할 그릇이 없으면 매번 사람이 "이번에 뭘 봤지" 하고 메모해야 합니다. v1.3은 그 메모를 에이전트가 자동으로 풀에 떨어뜨리고, taxonomist가 회차 단위로 정량 게이트를 통과시켜 본진에 반영하는 구조입니다. 분류 체계가 단일 사용자 분포에 좁아지지 않도록 외부 샘플 채널도 함께 정의했습니다.

**발행 전 파일럿 회차 결과**

회차 1(인프라 검증, 합성 샘플 2건) → 본진 신규 1건(C-9 숫자 괄호 인덱싱) · 본진 보강 1건(I-2 결합형) · hold 1건. 인프라 작동 확인.

회차 2(외부 진짜 데이터, 뉴스핌 [AI로 읽는 경제] 시리즈 ① ② — ChatGPT 작성 명시 GPT 출력 약 4,500자) → 본진 보강 2건 + hold 3건:

| 후보 | 결과 | 사유 |
|------|------|------|
| "~라는 뜻이다 / ~다는 뜻이다" 결말 단언 공식 | **merged → I-3 보강** | Gate 2.2 (본진 변종) — I-3 시그니처 예문에 결말 변종 4건 흡수 |
| "이 점에서 / 이 관점에서 / 이 말은" 메타 진입 | **merged → H-3 보강** | Gate 2.2 (본진 변종) — H-3 시그니처 예문에 결합형 4건 흡수 |
| "결국" 문두 단언 남발 (9회+) | **hold** | Gate 1.3 (분산) — 같은 모델·같은 기자 시리즈, 다음 회차 다른 모델 데이터에서 재현 시 promoted 가능 (강력 후보) |
| "X은 A가 아니라 B다" 부정-긍정 대구 결산 (7회+) | **hold** | 동일 — D-7 신규 등재 자격 충분, 분산 검증 대기 |
| 5~8개 영역 콤마 빠른 나열 (4회) | **hold** | 동일 |

회차 2의 핵심 발견은 **Gate 1.3 분산 보호장치가 진짜 외부 데이터에서도 정확히 작동했다**는 점입니다. occurrences·source distinct 정량 기준은 모두 통과한 강력 후보 3건이, 같은 모델·같은 기자 시리즈라는 정성 분산 검사로 hold 처리되어 단일 출처 노이즈가 본진을 오염시키지 않았습니다. v1.2 워크플로였다면 5개 후보 모두 reviewer JSON에 기록됐다가 run 종료 후 묻혔을 정보입니다. v1.3에서는 본진 보강 2건이 즉시 영구 반영되고, 강력 후보 3건이 풀에 hold로 누적되어 다음 회차의 자동 승격 트리거가 마련됐습니다.

회차별 점검 로그는 운영 산출물이라 `_workspace/taxonomy_changelog.md`에 누적되며 (gitignored), 본진 변경은 [`ai-tell-taxonomy.md` 버전 관리](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md#버전-관리)에 영구 기록됩니다.

전체 v1.3 변경 이력: [`ai-tell-taxonomy.md` 버전 관리](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md#버전-관리)

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

- **MIT 라이선스** — [`LICENSE`](LICENSE) 참조. 코드·스킬·에이전트 정의·분류 체계 문서를 포함한 본 리포 전체에 적용됩니다. 외부 패키지 통합·fork·상용 활용 모두 허용되며, 저작권 표기와 라이선스 사본을 함께 배포하면 됩니다.
- 외부 contribution(PR·Issue 등)은 GitHub 기본 inbound = outbound 원칙에 따라 동일한 MIT 라이선스로 contribution됩니다.
- 본 도구는 "AI 탐지기 우회(Undetectable AI)"가 아니라 **한글 글쓰기 품질 개선**을 목적으로 합니다.
- 학술 제출·저널리즘 진실성 보증 도구가 아닙니다.
- 분류 체계(`ai-tell-taxonomy.md`)는 연구·교육·도구 통합 목적 자유 이용 가능합니다(MIT 범위 내).

## 기여

새로운 AI 티 패턴이나 회귀 사례를 발견했다면 [Issue](https://github.com/epoko77-ai/im-not-ai/issues)로 보고해 주세요. 실증 사례 2건 이상(가능하면 서로 다른 모델·장르·작가)이 함께면 분류학자 에이전트가 점검 회차에서 본진([`ai-tell-taxonomy.md`](.claude/skills/humanize-korean/references/ai-tell-taxonomy.md))으로 승격합니다. v1.3에서 운영했던 candidate pool은 핫패스 비용 문제로 v1.5에서 제거됐고, 외부 보고는 Issue 채널로 단순화됐습니다.

**외부 데이터 raw text 보존 정책 (v1.5~)** — 외부 매체 글(예: 뉴스 기사·블로그)을 검증 데이터로 제출할 때, 직접 raw text 인용이 저작권상 부담스러우면 **분석 노트만 보존하지 말고 안전한 인용 단위(문단 1~2개) + 출처 URL을 같이** 남겨주세요. v1.3 회차 2 뉴스핌 GPT 데이터가 분석 노트만 보존되고 raw text가 떨어져 v1.5 회귀 검증에서 재사용 불가했던 사례가 있었습니다. URL이 만료되면 검증 자산 자체가 사라지므로, fair use 범위의 짧은 인용 + URL 동시 보존이 권장됩니다.

다른 형태(외부 회귀 케이스 제공·슬래시 커맨드·Plugin 통합·다국어 확장 등)도 환영합니다. 자세한 안내와 기여자 명단은 [`CONTRIBUTORS.md`](CONTRIBUTORS.md)를 참고해주세요.

## Contributors

v1.2까지의 외부 기여자: **[@simonsez9510](https://github.com/simonsez9510)** (Issue #1, PR #3 — 권한 위계 기반 voice profile 도입), **[@gaebalai](https://github.com/gaebalai)** (Issue #5 LICENSE 지적, Issue #6 슬래시 커맨드 reference + 포크 distribution channel). 전체 명단과 기여 내역: [`CONTRIBUTORS.md`](CONTRIBUTORS.md).

---

Built with [Claude Code](https://claude.com/claude-code) + https://github.com/revfactory/harness 하네스 아키텍처 기반 프로젝트.
