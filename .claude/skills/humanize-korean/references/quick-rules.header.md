# Quick Rules — Monolith Fast Path 전용 (v2.0)

<!-- 이 파일은 build_quick_rules.py가 quick-rules.md를 생성할 때 앞부분에 그대로 붙이는 고정 템플릿이다. quick-rules.md를 직접 고치지 말 것 — 규칙 본문은 ai-tell-taxonomy.md(SSOT)에서 생성된다. 이 헤더·꼬리 고정부만 여기서 관리한다. -->

`humanize-monolith` 에이전트가 한 콜에서 탐지·윤문·자체검증을 끝내기 위해 사용하는 슬림 룰북. 본진 `ai-tell-taxonomy.md`에서 `quick: true` 패턴만 처방과 함께 한 줄로 압축해 **자동 생성**한다.

**원칙:** 정의 1줄 + 처방 1줄. 예문 생략. 본진 ID와 1:1 매칭(빌드가 보장).

**Do-NOT (탐지·윤문 모두 제외):** 고유명사·제품명·모델명·기관명, 수치·날짜·단위, 큰따옴표 안 직접 인용, 법률 조문, 수학·화학·통계 표기, 영어 약어(LLM·GPU·MCP·API 등 업계 표준).

**과윤문 가드:** 변경률 30% 초과 = 경고, 50% 초과 = 강제 중단·롤백. 판정은 자가 산출이 아니라 `scripts/verify_change_rate.py`가 한다(오케스트레이터 Phase 2.5).

---
