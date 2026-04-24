# Humanize KR — AI 한글 티 제거 하네스

AI(ChatGPT · Claude · Gemini 등)가 쓴 한글 글을 **내용은 한 글자도 건드리지 않고** 문체 · 리듬 · 표현만 자연스러운 한국어로 되돌리는 Claude Code 하네스 입니다. 

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

## 사용법 (Claude Code 환경)

이 리포지토리는 https://github.com/revfactory/harness 기반으로 만들었습니다,  프로젝트 루트를 Claude Code 작업 디렉토리로 지정하면 오케스트레이터 스킬이 자동 트리거됩니다.

```
이 AI 글 자연스럽게 윤문해줘:

[여기에 AI가 쓴 한글 글 붙여넣기]
```

트리거 키워드: "AI 티 없애줘", "GPT 문체 제거", "사람이 쓴 것처럼 윤문", "한글 AI 윤문", "번역투 제거" 등.

결과 산출물은 `_workspace/{YYYY-MM-DD-NNN}/`에:
- `01_input.txt` — 원문
- `02_detection.json` — 탐지 리포트
- `03_rewrite.md` + `03_rewrite_diff.json` — 윤문본 + diff
- `04_fidelity_audit.json` — 내용 감사
- `05_naturalness_review.json` — 자연스러움 리뷰
- `final.md` + `summary.md` — 최종 결과 + 요약

## Do-NOT List (탐지·윤문 대상 제외)

- 수치 · 단위 · 날짜
- 고유명사 · 인명 · 제품명 · 모델명
- 큰따옴표 내부 직접 인용
- 법률 · 규정 조문
- 학술 개념어 (불가피한 경우)

## 웹 서비스 확장 (옵션)

`humanize-web-architect` 에이전트가 Next.js 15 App Router + Vercel Fluid Compute + AI Gateway 기반 웹앱 설계를 담당한다. UX는 4화면(입력 → 탐지 하이라이트 → 좌우 diff → 윤문본 복사). 상세: [`web-service-spec.md`](.claude/skills/humanize-korean/references/web-service-spec.md).

로드맵: v0 MVP(익명·단일 호출) → v1(로그인·히스토리) → v2(Pro/Team · API · 웹훅) → v3(Chrome Extension) → v4(일본어·중국어 확장).

## 라이선스 & 윤리

- 본 도구는 "AI 탐지기 우회(Undetectable AI)"가 아니라 **한글 글쓰기 품질 개선**을 목적으로 합니다.
- 학술 제출·저널리즘 진실성 보증 도구가 아닙니다
- 분류 체계(`ai-tell-taxonomy.md`)는 연구·교육 목적 자유 이용 가능합니다.

## 기여

새로운 AI 티 패턴을 발견했다면 `references/ai-tell-taxonomy.md` 하단 버전 섹션에 후보로 제안해 주세요. 실증 사례 2건 이상을 첨부하면 분류학자 에이전트가 v1 → v2 승격시킵니다.

---

Built with [Claude Code](https://claude.com/claude-code) + https://github.com/revfactory/harness 하네스 아키텍처 기반 프로젝트.
