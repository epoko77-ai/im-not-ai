---
description: 가장 최근 윤문 결과를 2차로 다시 다듬기 — strict run은 잔존 finding만, fast run은 strict 새 run
argument-hint: [조정 지시 — 예 "번역투만 다시" "이 문단만" "강도 낮춰" "강도 높여"]
---

# /humanize-redo — 2차 윤문 / 부분 재실행 (v1.6.1 계약)

가장 최근 cwd 기준 `_workspace/{run_id}/`를 찾아, 그 run의 산출물 종류에 따라 다르게 재실행한다. **monolith(fast)에는 부분 재실행 모드가 없다.**

## 사용자 지시
$ARGUMENTS

## 동작

1. cwd 기준 `_workspace/`에서 가장 최신 `run_id` 디렉토리 식별 (없으면 "이전 실행이 없습니다. `/humanize`로 시작하세요" 안내).
2. run 종류 판별:
   - **strict run** — `02_detection.json`·`03_rewrite.md`가 있다 → 아래 3으로.
   - **fast run** — `final.md`(+`01_input.txt`)뿐이다 → `final.md`를 새 입력으로 **새 run_id**를 만들고 strict를 Phase A(탐지)부터 실행한다. 사용자 지시(카테고리·문단·강도)는 detector·rewriter의 `target_filter`·`min_severity`로 전달.
3. strict run의 지시 파싱:
   - **카테고리 지정** ("번역투만", "관용구만", "이모지만" 등) → 해당 카테고리 finding만 다시 윤문
   - **문단 지정** ("이 문단만", "두 번째 문단만") → 해당 범위 finding만 처리
   - **강도 조정** ("강도 낮춰" / "보수적으로") → S1만 처리, "강도 높여" → S1+S2+S3 모두
   - **롤백 요청** ("이 변경 되돌려줘") → 해당 edit을 `content-fidelity-auditor` 롤백 명령으로 처리
   - 지시가 없거나 "2차 윤문해줘" → 잔존 finding 전체 대상으로 round 2
4. `korean-style-rewriter`를 재호출하되 입력에 기존 `02_detection.json` 또는 `05_naturalness_review.json`의 잔존 finding과 사용자 지시(`target_filter`)를 전달한다.
5. 산출물은 `03_rewrite_v2.md`(또는 v3)로 버전 분리 저장 → 병렬 검증 → 판정 매트릭스 → `final.md` 갱신(이전 `final.md`는 `final_prev.md`로 백업).

## 루프 한도

최대 round 3까지. 그 이상은 `hold_and_report`로 사람 검토 권고.

## 참고

- 풀 파이프라인 신규 실행은 [`/humanize`](./humanize.md) 사용.
- voice profile(`author-context.yaml`)·`accepted_by_voice_profile` 플래그는 v1.5에서 삭제됐다 — 재주입하지 않는다.
