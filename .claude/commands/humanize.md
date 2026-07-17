---
description: AI가 쓴 한글 텍스트를 정밀 모드로 윤문 (진단→겨냥 윤문→finalize 3콜)
argument-hint: [윤문할 텍스트 또는 파일 경로]
---

# /humanize — 한글 AI 티 제거 정밀 파이프라인

`humanize-korean` 스킬을 **정밀 모드**로 발동해 인자로 전달된 한글 텍스트(또는 파일)를 3콜(진단→겨냥 윤문→finalize)로 처리한다. (빠른 1콜 처리만 원하면 스킬을 fast 모드로 직접 트리거한다.)

## 입력
$ARGUMENTS

## 동작

1. 인자가 비었으면: "윤문할 텍스트를 붙여넣어 주세요" 안내 후 종료.
2. 인자가 파일 경로(.txt/.md)로 보이면 Read로 본문을 불러온다.
3. 인자가 텍스트면 그대로 입력으로 사용한다.
4. `humanize-korean` 스킬 SKILL.md의 **정밀 모드(Phase P1~P4)**를 끝까지 실행:
   - 첫 응답 한 줄로 버전·모드 출력 (`humanize-korean v2.1 — 정밀 모드 / run_id: ...`)
   - cwd 기준 `_workspace/{YYYY-MM-DD-NNN}/`에 새 run_id 생성
   - shim(정량 점수) → `humanize-diagnostician`(지배 패턴 3~6개 진단) → shim `--diagnosis` 결합 → `humanize-monolith`(진단 겨냥 윤문, 장문이면 청크 병렬) → `verify_change_rate.py`(변경률 게이트) → `humanize-finalizer`(의미 15항+자연성, 국소 보정) → 최종 변경률 확정
5. 최종 결과를 사용자에게 전달:
   - 윤문본 본문 (마크다운 블록)
   - `02_diagnosis.md`의 지배 패턴 + `09_finalize.json`의 verdict
   - 변경률(verify_change_rate.py 출력값) + 품질 등급
   - 주요 변경 하이라이트 3~5건 (before/after)
   - `verdict=hold_and_report`면 사람 검토 안내

## 옵션 (인자 끝에 자연어로 적기)

- `장르: 칼럼|리포트|블로그|공적` — 장르 명시 (생략 시 첫 300자로 자동 추정)
- `강도: 보수|기본|적극` — 진단 지배 패턴 개수 조정 (기본값: 기본)

## 참고

- 분류 체계: [`ai-tell-taxonomy.md`](../skills/humanize-korean/references/ai-tell-taxonomy.md)
- 윤문 처방: [`rewriting-playbook.md`](../skills/humanize-korean/references/rewriting-playbook.md)
