---
name: humanize-korean
description: AI(ChatGPT·Claude·Gemini)가 쓴 한글 텍스트를 사람이 쓴 글처럼 윤문한다. 번역투·영어 인용 과다·기계적 병렬·관용구·피동 남용·접속사 남발·리듬 균일·이모지/불릿 과다 등 10대 카테고리 40+ AI 티 패턴을 탐지·분류해 내용은 한 글자도 건드리지 않고 문체·리듬·표현만 자연스럽게 재작성한다. 트리거 — "AI 티 없애줘", "AI 윤문", "ChatGPT 티 제거", "번역투 고쳐", "사람이 쓴 것처럼", "humanize Korean". 단순 맞춤법 교정·번역·내용 추가는 대상 아님.
---

# Humanize Korean for Codex

Codex에서는 **Fast가 기본값**이다. 일반 `$humanize-korean` 호출은 단일 호출 안에서 탐지·윤문·자체검증을 끝낸다. **strict는 사용자가 명시적으로 요청한 경우에만** Codex subagent workflow로 실행한다.

## 모드 라우팅

- **Fast default**: 사용자가 그냥 "AI 티 없애줘", "윤문해줘", "humanize Korean"처럼 요청하면 Fast로 처리한다.
- **Strict explicit only**: 사용자가 `strict`, `정밀`, `5인 파이프라인`, `서브에이전트`, `subagent`, `parallel review`, `병렬 검증`처럼 Codex subagent 기반 정밀 워크플로를 분명히 요구한 경우에만 strict를 실행한다.
- 입력이 길거나 위험해 보여도 자동으로 strict를 시작하지 않는다. 필요한 경우 "정밀 검증은 strict Codex subagent workflow로 다시 요청할 수 있다"고 짧게 안내한다.
- Codex subagents를 사용할 수 없는 환경이면 같은 strict 산출물 계약을 main thread에서 순차 실행하고, 응답에 fallback 사실을 밝힌다.

## 철칙

1. **의미 불변**: 사실·주장·수치·날짜·고유명사·인용문은 원문과 100% 일치.
2. **근거 기반**: `references/quick-rules.md`에 매핑되지 않는 구간은 건드리지 않는다.
3. **장르 유지**: 입력 장르(칼럼·리포트·블로그·공적)에서 이탈 금지.
4. **register 보존**: 원문 격식체면 결과도 격식체. AI 티는 문법·수사이지 격식 자체가 아니다.
5. **과윤문 금지**: 변경률 30% 초과 = 경고, 50% 초과 = 작업 중단·롤백.
6. **Do-NOT**: 고유명사·수치·인용·법조문·영어 약어(LLM·GPU·API 등) 원형 보존.

## Fast 절차

1. **룰북 로드**: `references/quick-rules.md`를 읽어 S1·S2 패턴과 자체검증 체크리스트를 내재화한다.
2. **입력 확보**: 사용자가 붙여넣은 텍스트를 원문으로 한다. 인자가 파일 경로(.txt/.md)면 그 파일을 읽는다. 한국어가 아니면 "한국어 텍스트만 처리 가능" 안내 후 종료.
3. **장르 추정**: 첫 300자로 장르 추정(사용자 명시 시 우선).
4. **탐지**: A~J 카테고리 패턴을 메모리에서 스캔해 (ID, span, severity, fix) 수집. Do-NOT span은 제외.
5. **윤문**: D(관용구 삭제) -> A -> I -> G -> H -> F -> B -> C·J -> E 순서로 문단 단위 처리. 변경률을 모니터링하며 50% 임박 시 후속 edit 보류.
6. **자체검증**: quick-rules "자체검증 체크리스트" 6항 점검. 위반 항목 발견 시 해당 edit 롤백 -> 윤문 부분 재실행(최대 1회).
7. **출력**: cwd 기준 `_workspace/{run_id}/final.md` 작성(run_id = `YYYY-MM-DD-NNN`, 당일 기존 폴더 있으면 NNN+1). 본문 끝에 빈 줄 하나 두고 `<!-- HUMANIZE-SUMMARY ... -->` HTML 주석 블록 1개 추가:
   - 원본/윤문본 글자수·변경률
   - 카테고리별 탐지 건수(before -> after, quick-rules ID 기준)
   - 자체검증 6항 통과 여부
   - 등급(A/B/C/D) + 사유 1줄
   - 주요 변경 하이라이트 3~5건(before -> after, 각 100자 이내)
8. **응답**: 사용자에게 짧게 4가지 반환 — ① 한 줄 상태(`완료. 변경률 X% / 등급 Y / 자체검증 N/6 통과`) ② 핵심 카테고리 탐지 4~6건(before -> after) ③ 변경 하이라이트 1건 ④ 등급 B 이하면 "strict Codex subagent workflow로 정밀 검증 가능" 안내. 윤문본 본문은 응답에 인라인하지 말고 `final.md`에만 저장.

## Strict Codex Subagent Workflow

strict는 사용자의 명시적 요청이 있을 때만 시작한다. 시작 전 원문을 cwd 기준 `_workspace/{run_id}/01_input.txt`에 저장하고, 모든 subagent prompt에 이 파일 경로와 아래 reference 파일 경로를 포함한다. 각 subagent는 독립적으로 필요한 reference를 읽게 하며, 최종 판단은 main thread가 종합한다.

Codex는 subagent를 명시 요청 시에만 spawn한다. strict를 실행할 때도 같은 역할을 중복 spawn하지 말고, 각 dependency wave가 완료될 때까지 wait한 뒤 결과 파일과 최종 메시지를 읽어 다음 wave를 시작한다. wait 중 응답이 늦어도 살아 있는 subagent를 실패로 간주하지 않는다. 같은 역할이 아직 실행 중이면 **do not spawn another subagent for the same role**.

모든 subagent prompt는 다음 형식을 포함한다.

```text
TASK: <역할별 지시>
DELIVERABLE: <써야 할 파일과 반환 요약>
SCOPE: <입력 파일, reference 파일, 변경 금지 범위>
VERIFY: <성공 조건과 금지 조건>
```

1. **Dependency wave 1 — Detector subagent**: `references/quick-rules.md`와 `references/ai-tell-taxonomy.md`를 기준으로 Do-NOT span을 제외한 AI 티를 span 단위로 탐지한다. 출력은 `_workspace/{run_id}/02_detection.json`이며 항목은 `id`, `category`, `severity`, `span`, `reason`, `suggested_fix`를 포함한다. Parent는 completed subagent 결과를 wait한 뒤 JSON을 읽고 다음 wave로 간다.
2. **Dependency wave 2 — Rewriter subagent**: `02_detection.json`과 `references/rewriting-playbook.md`만 근거로 수술적으로 윤문한다. 사실·수치·고유명사·인용문을 바꾸지 않고 `_workspace/{run_id}/03_rewrite.md`를 쓴다. Parent는 completed subagent 결과와 파일을 모두 확인한다.
3. **Dependency wave 3 — parallel auditors**: 아래 둘은 동시에 실행할 수 있다. Parent는 둘 다 wait하고 완료 결과를 모두 읽은 뒤 종합한다.
   - **Fidelity auditor subagent**: `01_input.txt`와 `03_rewrite.md`를 비교해 의미 훼손, 누락, 추가 주장, 수치/날짜/고유명사 변경을 감사한다. 출력은 `_workspace/{run_id}/04_fidelity_audit.json`이다.
   - **Naturalness reviewer subagent**: `03_rewrite.md`를 다시 스캔해 잔존 S1/S2, 과윤문, 리듬 균일성, register 이탈을 평가한다. 출력은 `_workspace/{run_id}/05_naturalness_review.json`이다.
4. **Main thread synthesis**: 두 검증 결과를 종합한다. fidelity 실패면 문제 edit를 롤백하거나 보수적으로 재작성한다. 자연도 C/D면 한 번만 재윤문하고 다시 검토한다. 최종 `_workspace/{run_id}/final.md`와 `_workspace/{run_id}/summary.md`를 작성한다.

Strict 응답은 Fast와 같은 요약 형식을 유지하되, `summary.md` 경로와 subagent 산출물 경로를 함께 알려준다. subagent를 열어 실행했다면 결과 수령 후 완료된 subagent를 close/닫아 열린 agent를 남기지 않는다.

## 등급

- **A**: S1 0건, S2 2건 이하, 변경률 10~25%, 자체검증 6/6.
- **B**: S1 0건, S2 4건 이하, 자체검증 5/6 이상.
- **C/D**: S1 잔존 또는 과윤문 시그널 — 사용자가 원하면 strict Codex subagent workflow 권고.

## 옵션

- `장르: 칼럼|리포트|블로그|공적`
- `강도: 보수|기본|적극`
- `최소심각도: S1|S2|S3`
- `strict|정밀|5인 파이프라인|서브에이전트|parallel review`: 명시적 strict 실행

## 참고

- 슬림 룰북: `references/quick-rules.md` — S1·S2 핵심 패턴 + 자체검증 체크리스트
- 분류 체계 본진: `references/ai-tell-taxonomy.md` — 10대분류 × 40+ 패턴 전수
- 윤문 처방: `references/rewriting-playbook.md` — 카테고리별 치환 레시피
