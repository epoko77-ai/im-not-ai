---
name: humanize
description: AI가 쓴 한글 텍스트를 자연스럽게 윤문하는 진입 명령. humanize-korean 파이프라인을 shim 의 route_hint 가 정한 경로(light 1콜 · standard 2콜 · heavy 3+콜)로 실행하고 `--strict`면 heavy 고정. 트리거 — "/humanize".
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
4. `humanize-korean` 스킬 SKILL.md 절차(Phase 0 → 결과 전달)를 따른다 — 경로는 **route_hint**(light|standard|heavy)가 정하고, `--strict` 시 heavy 고정.
5. 결과 전달은 `humanize-korean`의 「결과 전달」 절을 그대로 따른다.

## 옵션 (인자 끝에 자연어로)
- `장르: 칼럼|리포트|블로그|공적` — 장르 명시 (생략 시 첫 300자로 자동 추정)
- `강도: 보수|기본|적극` — 윤문 강도 (기본값: 기본)
- `--strict` — 정밀 3콜(진단→겨냥 윤문→finalize) 강제

