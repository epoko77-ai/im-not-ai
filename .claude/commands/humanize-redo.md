---
description: 가장 최근 윤문 결과를 2차로 다시 다듬기 — 특정 카테고리·문단·강도 조정도 가능
argument-hint: [조정 지시 — 예 "번역투만 다시" "이 문단만" "강도 낮춰" "강도 높여"]
---

# /humanize-redo — 2차 윤문 / 부분 재실행

가장 최근 cwd 기준 `_workspace/{run_id}/`를 찾아 `humanize-korean` 스킬 strict 파이프라인의 Phase B(윤문) 또는 Phase C(검증)부터 재호출한다.

## 사용자 지시
$ARGUMENTS

## 동작

1. cwd 기준 `_workspace/`에서 가장 최신 `run_id` 디렉토리 식별 (없으면 "이전 실행이 없습니다. `/humanize`로 시작하세요" 안내).
2. 사용자 지시 파싱:
   - **카테고리 지정** ("번역투만", "관용구만", "이모지만" 등) → 해당 카테고리 finding만 다시 윤문
   - **문단 지정** ("이 문단만", "두 번째 문단만") → 해당 범위 finding만 처리
   - **강도 조정** ("강도 낮춰" / "보수적으로") → S1만 처리, "강도 높여" → S1+S2+S3 모두
   - **롤백 요청** ("이 변경 되돌려줘") → 해당 edit을 `content-fidelity-auditor` 롤백 명령으로 처리
   - 지시가 없거나 "2차 윤문해줘" → 잔존 finding 전체 대상으로 round 2
3. `korean-style-rewriter`를 재호출하되 입력에:
   - 기존 `02_detection.json` 또는 `05_naturalness_review.json`의 잔존 finding
   - 사용자 지시를 `target_filter`로 전달
4. 산출물은 `03_rewrite_v2.md` (또는 v3)로 버전 분리 저장.
5. Phase C 병렬 검증 → Phase D 최종 출력 (변경 비교 표, 신규 등급).

## 루프 한도

최대 round 3까지. 그 이상은 `hold_and_report`로 사람 검토 권고.

## 참고

- 풀 파이프라인 신규 실행은 [`/humanize`](./humanize.md) 사용.
