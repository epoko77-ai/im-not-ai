---
name: im-not-ai
description: Korean AI-text humanizer for ChatGPT, Codex, and other agents. Use when the user asks to remove AI-like Korean writing tells, GPT or ChatGPT tone, translationese, mechanical structure, overused connectors, passive voice, excessive bullets or emoji, or to make Korean drafts sound human while preserving facts, numbers, names, claims, and quotes. Also use for follow-ups such as lower rewrite strength, retry one paragraph, strict audit, or fix only translationese.
---

# Im Not AI — 한글 AI 티 제거 오케스트레이터

AI(ChatGPT, Codex, Gemini 등)가 쓴 한글 초안을 사람이 쓴 글처럼 다듬되, 내용은 건드리지 않는다. 목표는 "더 멋진 글"이 아니라 원문의 사실, 주장, 수치, 고유명사, 인용을 그대로 보존하면서 AI 특유의 문체 흔적만 줄이는 것이다.

## 핵심 원칙

1. **의미 불변**: 사실, 주장, 수치, 날짜, 단위, 고유명사, 직접 인용은 원문과 100% 일치시킨다.
2. **근거 기반 수정**: 탐지된 AI 티 패턴에 연결되는 구간만 바꾼다. 근거 없는 문장은 놔둔다.
3. **장르 유지**: 칼럼은 칼럼으로, 리포트는 리포트로, 블로그는 블로그로 유지한다.
4. **과윤문 금지**: 변경률 30% 초과는 경고, 50% 초과는 중단하거나 보수적으로 롤백한다.
5. **직접 인용 보호**: 큰따옴표 안 직접 인용, 법률 조문, 학술 개념어는 임의로 고치지 않는다.

## 모드 결정

작업 시작 시 가능하면 다음 상태를 한 줄로 남긴다.

```text
im-not-ai — {fast|strict} 모드 / run_id: {YYYY-MM-DD-NNN 또는 inline}
```

- 사용자가 "정밀", "strict", "5인 파이프라인", "감사까지"를 말하면 **strict**.
- 입력이 8,000자를 넘으면 **strict**.
- 그 외에는 **fast**.
- "이 문단만", "번역투만", "강도 낮춰", "2차 윤문" 같은 후속 요청은 기존 결과를 기준으로 필요한 구간만 다시 처리한다.

## 런타임 형태

이 스킬은 ChatGPT, Codex, API/agent 런타임 모두에서 쓸 수 있게 작성되어 있다.

- 파일시스템이 있으면 현재 작업 폴더 기준 `_workspace/{run_id}/`를 만들고 산출물을 저장한다.
- 파일시스템이 없거나 ChatGPT 대화형 사용이면 본문과 요약을 채팅에 바로 반환한다.
- 스킬 내부 자료는 항상 현재 스킬 폴더 기준 상대 경로로 찾는다. `.claude`, `.Codex`, 사용자 홈 같은 하드코딩 경로에 의존하지 않는다.
- Codex 프로젝트에 `.codex/agents/`가 있고 사용자가 strict를 명시한 경우에만 보조 에이전트를 써도 된다. 없으면 같은 절차를 직접 수행한다.

## Fast 모드

5,000자 안팎의 일반 요청은 fast 모드로 처리한다.

1. 입력 원문을 보존한다. 파일시스템이 있으면 `_workspace/{run_id}/01_input.txt`에 저장한다.
2. `references/quick-rules.md`를 읽어 S1, S2 핵심 패턴을 확인한다.
3. 다음 순서로 AI 티를 탐지한다.
   - 번역투: `~를 통해`, `~에 대해`, `~에 있어서`, 이중 피동, `가지고 있다`
   - 관용구: `결론적으로`, `시사하는 바가 크다`, `주목할 만하다`, 과한 혁신/중요성 표현
   - 구조: 기계적 `첫째/둘째/셋째`, 과한 헤딩/불릿/이모지, 연결어미 뒤 쉼표
   - 리듬: 비슷한 길이의 문장 반복, 같은 종결어미 반복
   - 형식명사와 완곡: `것이다`, `점`, `수 있다`, `필요가 있다`, `보인다`
4. 탐지된 span만 수술적으로 고친다. 문단 전체를 새로 쓰지 않는다.
5. 자체검증 6항을 확인한다.
   - 고유명사, 수치, 날짜, 단위 보존
   - 직접 인용 보존
   - 원문 주장 누락 없음
   - 새 주장이나 예시 추가 없음
   - 장르와 격식 유지
   - 변경률 30% 이하 또는 경고 표시

## Strict 모드

정밀 요청, 장문, 민감한 문서, 재윤문 요청은 strict 모드로 처리한다.

1. `references/ai-tell-taxonomy.md`를 읽어 10대 카테고리와 severity 기준을 확인한다.
2. `references/rewriting-playbook.md`를 읽어 카테고리별 치환 원칙을 확인한다.
3. 탐지 결과를 span 단위로 만든다. 파일시스템이 있으면 `_workspace/{run_id}/02_detection.json`에 저장한다.
4. finding 단위로 윤문한다. 파일시스템이 있으면 `_workspace/{run_id}/03_rewrite.md`와 diff 요약을 저장한다.
5. 내용 감사와 자연스러움 리뷰를 분리해서 수행한다.
   - 내용 감사: 사실, 수치, 고유명사, 인용, 논리관계, 누락 여부
   - 자연스러움 리뷰: 잔존 S1/S2, 과윤문, 장르 이탈, 리듬 회복
6. 문제가 있으면 해당 edit만 롤백하거나 최대 3회까지 재윤문한다. 3회 뒤에도 의미 훼손이나 과윤문이 남으면 사람 검토를 권한다.

## 출력

파일시스템이 있으면 다음 파일을 만든다.

- `_workspace/{run_id}/final.md`: 최종 윤문본
- `_workspace/{run_id}/summary.md`: 변경률, 등급, 주요 finding, 자체검증 결과
- strict 모드에서는 `02_detection.json`, `03_rewrite.md`, `04_fidelity_audit.json`, `05_naturalness_review.json`도 가능하면 남긴다.

사용자에게는 다음 순서로 짧게 반환한다.

1. 완료 상태: `완료. 변경률 X% / 등급 Y / 자체검증 N/6 통과`
2. 윤문본 또는 저장 경로
3. 핵심 변경 3~5건
4. 남은 위험이나 사람 검토가 필요한 이유

채팅형 런타임에서는 윤문본을 직접 반환한다. Codex처럼 파일을 같이 다루는 런타임에서는 긴 본문을 `final.md`에 두고 응답에는 경로와 요약을 우선한다.

## 변경 금지 목록

- 수치, 단위, 날짜
- 인명, 회사명, 제품명, 모델명
- 큰따옴표 내부 직접 인용
- 법률 조문, 규정 문구
- 학술 개념어와 전문 용어
- 원문에 없는 주장, 예시, 평가
- 원문 정보의 삭제 또는 순서 왜곡

## 자료

- Fast 룰북: `references/quick-rules.md`
- 전체 분류 체계: `references/ai-tell-taxonomy.md`
- 윤문 처방: `references/rewriting-playbook.md`
- 번역투 학술 근거: `references/scholarship.md`
- 웹 서비스 설계가 필요할 때: `references/web-service-spec.md`
- 정량 지표가 필요할 때: `references/metrics.py`, `references/metrics_v2.py`
