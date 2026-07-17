---
description: AI가 쓴 한글 텍스트를 자연스럽게 윤문 (탐지→윤문→감사→리뷰 5단계 풀 파이프라인)
argument-hint: [윤문할 텍스트 또는 파일 경로]
---

# /humanize — 한글 AI 티 제거 풀 파이프라인

`humanize-korean` 스킬을 발동해 인자로 전달된 한글 텍스트(또는 파일)에 5인 파이프라인을 끝까지 실행한다.

## 입력
$ARGUMENTS

## 동작

1. 인자가 비었으면: "윤문할 텍스트를 붙여넣어 주세요" 안내 후 종료.
2. 인자가 파일 경로(.txt/.md)로 보이면 Read로 본문을 불러온다.
3. 인자가 텍스트면 그대로 입력으로 사용한다.
4. `humanize-korean` 스킬 SKILL.md 절차에 따라 Phase 0 → strict 파이프라인(Phase A~D)을 끝까지 실행:
   - 첫 응답 한 줄로 버전·모드 출력 (`humanize-korean v2.0 — strict 모드 / run_id: ...`)
   - cwd 기준 `_workspace/{YYYY-MM-DD-NNN}/`에 새 run_id 생성
   - `ai-tell-detector` → `korean-style-rewriter` → 병렬(`content-fidelity-auditor` + `naturalness-reviewer`) → 최종 종합
5. 최종 결과를 사용자에게 전달:
   - 윤문본 본문 (마크다운 블록)
   - 카테고리별 탐지 건수 before/after 표
   - 점수 변화 + 품질 등급 (A/B/C/D)
   - 주요 변경 하이라이트 3~5건 (before/after)
   - 등급 B 이하면 "`/humanize-redo`로 2차 윤문 가능" 안내

## 옵션 (인자 끝에 자연어로 적기)

- `장르: 칼럼|리포트|블로그|공적` — 장르 명시 (생략 시 첫 300자로 자동 추정)
- `강도: 보수|기본|적극` — 윤문 강도 (기본값: 기본)
- `최소심각도: S1|S2|S3` — 탐지 임계값 (기본값: S2)

## 참고

- 분류 체계: [`ai-tell-taxonomy.md`](../skills/humanize-korean/references/ai-tell-taxonomy.md)
- 윤문 처방: [`rewriting-playbook.md`](../skills/humanize-korean/references/rewriting-playbook.md)
