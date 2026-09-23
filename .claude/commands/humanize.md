---
description: AI가 쓴 한글 텍스트를 자연스럽게 윤문 — 기본 fast(humanize-monolith 1콜), --strict면 5인 파이프라인
argument-hint: [윤문할 텍스트 또는 파일 경로] [--strict] [장르: …] [강도: …] [최소심각도: …]
---

# /humanize — 한글 AI 티 제거 (v1.6.1 계약)

`humanize-korean` 스킬(SKILL.md v1.6.1)을 발동한다. 기본은 **fast**(`humanize-monolith` 단일 호출, 도구 호출 3회, 산출물 `final.md` 하나), `--strict`·"정밀 모드"·8,000자 초과면 **strict**(detector → rewriter → fidelity ∥ naturalness).

## 입력
$ARGUMENTS

## 동작

1. 인자가 비었으면: "윤문할 텍스트를 붙여넣어 주세요" 안내 후 종료.
2. 인자가 파일 경로(.txt/.md)로 보이면 Read로 본문을 불러온다. 텍스트면 그대로 입력으로 쓴다.
3. SKILL.md Phase 0 → 모드 결정 → 실행:
   - 첫 응답 한 줄: `humanize-korean v1.6.1 — {fast|strict} 모드 / run_id: {YYYY-MM-DD-NNN}`
   - cwd 기준 `_workspace/{run_id}/`에 `01_input.txt` 저장
   - **fast**: `humanize-monolith`를 Agent 도구로 1회 호출(`input_path`·`quick_rules_path`·`genre_hint`) → `final.md`(본문 + 끝 `<!-- HUMANIZE-SUMMARY -->` 주석)
   - **strict**: `ai-tell-detector` → `korean-style-rewriter` → 병렬(`content-fidelity-auditor` + `naturalness-reviewer`) → 판정 매트릭스 → `final.md`(같은 주석 블록)
4. 사용자에게 전달: 한 줄 상태(변경률/등급/자체검증) · 윤문본 본문 · HUMANIZE-SUMMARY 핵심 표 · 등급 B 이하면 "`--strict`로 정밀 검증" 안내.

## 옵션 (인자 끝에 자연어로 적기)

- `장르: 칼럼|리포트|블로그|공적` — 엔진이 받는 값은 이 4종. 그 밖의 장르·register(의학 정보체·낭독 스크립트·개조식 등)는 자연어로 덧붙인다(생략 시 첫 300자로 자동 추정).
- `강도: 보수|기본|적극` — 윤문 강도 (기본값: 기본)
- `최소심각도: S1|S2|S3` — 탐지 임계값 (기본값: S2)
- `--strict` — 5인 파이프라인 강제

## 호출자가 넣어야 하는 것 (엔진은 범용이다)

프로젝트 지식 — 장르·register, 골든 레퍼런스 문단, 브랜드 고정 문구, 절대 보존 목록(헤지 강도·수치 경계·귀속·캐비어트), 금지어·컴플라이언스 — 는 호출 프롬프트 산문으로 넣는다(monolith에 정식 슬롯은 없다). **의학·법률·정책 텍스트는 `G-2·A-10 단언화 처방을 적용하지 마라`를 축자로 넣고 strict를 권장한다.**

## 참고

- 분류 체계: [`ai-tell-taxonomy.md`](../skills/humanize-korean/references/ai-tell-taxonomy.md) · fast 슬림 룰북: [`quick-rules.md`](../skills/humanize-korean/references/quick-rules.md)
- 윤문 처방: [`rewriting-playbook.md`](../skills/humanize-korean/references/rewriting-playbook.md)
- 2차 윤문·부분 재실행: [`/humanize-redo`](./humanize-redo.md)
- voice profile(`author-context.yaml`)은 v1.5에서 삭제됐다 — 더 이상 탐색하지 않는다.
