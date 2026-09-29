---
name: humanize-redo
description: 가장 최근 윤문 결과를 2차로 다시 다듬는다 — 특정 카테고리·문단·강도 조정도 가능. humanize-korean heavy 경로를 기존 run_id의 final.md에 다시 돌린다. 트리거 — "/humanize-redo".
argument-hint: "[조정 지시 — 예: \"번역투만 다시\" \"이 문단만\" \"강도 낮춰\"]"
disable-model-invocation: true
---

# /humanize-redo — 2차 윤문 / 부분 재실행

cwd 기준 가장 최근 `_workspace/{run_id}/`를 찾아 `humanize-korean` 스킬의 heavy 경로로 다시 돌린다.

## 사용자 지시
$ARGUMENTS

## 동작
1. `Glob`으로 `_workspace/*/final.md`를 매칭해 최신 `run_id`(폴더명 `YYYY-MM-DD-NNN-TAG`)를 찾는다. 없으면 "이전 실행이 없습니다. `/humanize`로 시작하세요" 안내 후 종료.
2. `humanize-korean` SKILL.md의 「부분 재실행 / 후속 명령」 표를 따른다. 사용자 지시(카테고리만·이 문단만·강도 조정·장르 변경)를 그 표의 행에 대응시키고, 지시가 없으면 "2차 윤문" 행으로 처리한다 — 기존 run_id(TAG 포함)의 `final.md`를 새 입력으로 heavy P1부터.
3. 새 결과를 쓰기 전에 이전 `final.md`를 `final_prev.md`로 백업한다. 특정 변경만 되돌려 달라는 요청이면 `final_prev.md`(또는 `01_input.txt`)에서 해당 문장만 복원한다.
4. 결과 전달은 `humanize-korean`의 「결과 전달」을 따르고, 이전 결과 대비 변경 비교를 덧붙인다.

## 루프 한도
최대 round 3. 그 이상 미해결이면 `hold_and_report`로 사람 검토 권고.

## 참고
- 풀 파이프라인 신규 실행은 `/humanize`.
