# Taxonomy Candidates — 영속 후보·hold·승격 이력 (v2.0.1 신설, 2026-09-22)

`korean-ai-tell-taxonomist`의 대기 목록이자 승격 입력. `_workspace/`는 gitignore라 여기(추적 파일)에 둔다.
승격 규칙(에이전트 정의): 서로 다른 입력 **2건 이상 실증** · ID는 기존 A~J 하위 번호로 **append-only**(K 등 새 카테고리 신설 금지) · severity 이동은 역증거 3건+ · 학술 anchor는 `scholarship.md`.
상태: `pending`(1건 실증) · `hold`(실증 부족·판정 보류) · `promoted`(taxonomy 반영, 버전 기록) · `rejected`.

## 후보 목록

| 임시ID | 패턴 | 실증 (run/파일 · 모델) | 상태 | status_reason / 다음 단계 |
|---|---|---|---|---|
| K-1 | 열거 구분자 과치환 — 다어절 구 열거를 가운뎃점(·)으로 일괄 치환해 항목 경계가 무너짐("지역 안과 내원·정밀검사 결과·재검·추적") | afternoon-platform `_workspace/2026-09-22-001/02_detection.json`·`04_fidelity_audit.json` · Claude strict run | pending | 승격 시 C 또는 J 하위 번호. 처방 후보: 가운뎃점은 단어·짧은 명사 열거에만, 2어절+ 구는 쉼표 유지 |
| C-11-X | C-11(연결어미 뒤 쉼표) 예외 조건 — 주어가 바뀌는 절 경계·낭독 무휴지 60자+에서는 쉼표 유지 또는 마침표 분할 | 위 run(공적 발제, 낭독 존) | pending | playbook C-11 레시피에 예외 조건 추가 검토 |
| C-11-RL | C-11 run-length 회귀 — 쉼표 제거로 무휴지 구간 41→56자(60자 임계 미달이라 미탐지), 상승폭이 신호 | z-beyond 콜드리드 2026-09-22 `naturalness-reviewer` unclassified_candidates | pending | metrics 후보 `run_delta`(윤문 전후 최장 무휴지 증가율) +30% WARN |
| C-8-X | "A가 아니라 B" 부정-긍정 대구 반복(14회) — C-8 변종 | afternoon 2026-09-22-001(GPT-우세 시그니처 이력) | hold | v1.3.1 회차 2 hold 3건과 동일 계열, 인간 필자 중간값 대조 필요 |
| J-3/C-6-X | "**볼드 라벨** — 설명" 대시 정의 공식(6회) | afternoon 2026-09-22-001 | pending | J-3(대시)와 C-6 사이 — 갭 분석 후 하위 번호 |
| C-1-R | 열거 결속 붕괴(역효과) — C-1(첫째/둘째/셋째) 제거 후 예고문에 수사("세 가지")를 신설하면 수적 약속은 남고 이행 표지는 사라짐 | z-beyond 콜드리드 2026-09-22(`humanize-monolith` fast → fidelity 이관 → naturalness S2) | pending | 처방 후보: 수사를 예고문에 넣으면 최소 1개 항목 표지(`도`·`역시`) 유지 — playbook C-1 레시피의 예고문 측 부작용 |
| D-X-meta | 메타담화 서두·결산 ("이 글에서는 …알아보겠습니다", "이 순서는 ~아니라 ~입니다") — z-beyond T10 규칙의 범용성 미판정 | z-beyond PRODUCTION_SPEC_v2 §2 T10(10편 이상 실측) | pending | 타 프로젝트 실증 1건 더 필요(현재는 프로젝트 규칙) |
| E-2-X | 발화동사 종결 편중("봅니다/살핍니다/설명합니다" 100% 종결) — E-2 변종 | z-beyond YTR-0037/38 2026-08-25(ai-tell-detector 93건·37건) | pending | E-2와 병합 여부 갭 분석 |
| H-X-head | T10 제거의 문두 키워드 편중 — 메타담화 서두 제거 후 주제어 시작 문장 비율 36→50% | z-beyond 콜드리드 2026-09-22 | hold | metrics 후보 `head_repeat_ratio` — WARN 전용·자동 수정 금지(문두를 흔들면 H-1/A-16 재유입) |
| A-17 | '-들' 복수 접미 과잉(NMT 원본 회차) | v2.0 회차(학술 근거 강함, 우리 데이터 양성 0) | hold | v2.1 재평가 조건: NMT 원본 회차에서 양성 확보 |

## 승격·기각 이력

- 2026-09-22: 파일 신설. 위 10건 등록(promoted 0). 다음 회차부터 taxonomist가 이 표를 읽고 이어간다.
