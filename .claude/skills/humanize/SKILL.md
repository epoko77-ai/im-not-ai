---
name: humanize
description: AI가 쓴 한글 텍스트를 자연스럽게 윤문하는 진입 명령. humanize-korean 파이프라인을 Fast 모드(기본)로 실행하고 `--strict`면 정밀 3콜(진단→겨냥 윤문→finalize). 트리거 — "/humanize".
argument-hint: "[윤문할 텍스트 또는 파일 경로]"
disable-model-invocation: true
---

# /humanize — 한글 AI 티 제거

`humanize-korean` 스킬을 발동해 인자로 전달된 한글 텍스트(또는 파일)에 윤문을 실행한다.

## 입력
$ARGUMENTS

## 동작
1. 인자가 비면: "윤문할 텍스트를 붙여넣어 주세요" 안내 후 종료.
2. 인자가 파일 경로(.txt/.md)면 `Read`로 본문 로드.
3. 인자가 텍스트면 그대로 입력으로 사용.
4. `humanize-korean` 스킬 SKILL.md 절차(Phase 0 → 결과 전달)를 따른다 — 기본 **Fast 모드**, `--strict` 시 정밀 3콜(진단→겨냥 윤문→finalize).
5. 결과 전달:
   - 한 줄 상태(변경률 / 등급 / 자체검증 통과)
   - 윤문본 본문(마크다운 블록)
   - 카테고리별 탐지 건수 before/after
   - 주요 변경 하이라이트 3~5건
   - 등급 B 이하면 "`/humanize-redo`로 2차 윤문 가능" 안내

## 옵션 (인자 끝에 자연어로)
- `장르: 칼럼|리포트|블로그|공적` — 장르 명시 (생략 시 첫 300자로 자동 추정)
- `강도: 보수|기본|적극` — 윤문 강도 (기본값: 기본)
- `최소심각도: S1|S2|S3` — 탐지 임계값 (기본값: S2)
- `--strict` — 정밀 3콜(진단→겨냥 윤문→finalize) 강제

## 참고
- 분류 체계: `humanize-korean/references/ai-tell-taxonomy.md`
- 윤문 처방: `humanize-korean/references/rewriting-playbook.md`
