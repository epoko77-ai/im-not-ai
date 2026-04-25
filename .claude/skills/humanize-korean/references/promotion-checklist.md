# Promotion Checklist (v1.3~)

`pattern-candidates.md` 풀의 후보를 본진(`ai-tell-taxonomy.md`)으로 승격할지 결정할 때, taxonomist가 회차마다 동일한 정량 게이트를 통과시키도록 만든 체크리스트. 본 문서는 taxonomist의 판단 일관성을 시간·운영자에 무관하게 유지하기 위한 운영 표준입니다.

## 사용법

후보 1건마다 본 체크리스트를 위에서 아래로 순서대로 적용합니다. 한 게이트라도 fail이면 그 자리에서 판정 종료(승격 불가). 모든 게이트가 pass면 승격합니다. "hold"는 데이터 부족으로 다음 회차 이월(거부 아님).

판정 결과는 `_workspace/taxonomy_changelog.md`의 회차 표에 후보 ID·결과·통과/실패 게이트 번호 형식으로 기록합니다.

---

## Gate 0 — 사전 점검 (skip 시 다음 회차)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 0.1 | 풀 항목 상태 | `status == "pending"` | skip(이미 처리됨) |
| 0.2 | 필수 필드 완비 | `pattern_label`·`description`·`signature_examples ≥ 1`·`occurrences ≥ 1` 모두 비어있지 않음 | `hold + status_reason: "missing_required_fields"` |
| 0.3 | 사례 신선도 | `last_seen_at`이 90일 이내 | `rejected: "single_run_only — 90일 미재현"` (occurrences == 1일 때만) |

---

## Gate 1 — 재현 게이트 (Reproducibility)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 1.1 | 발견 횟수 | `occurrences ≥ 2` | `hold` (다음 회차 재검토) |
| 1.2 | run 분산 | 서로 다른 `source_run_id` 2건 이상 | `hold` |
| 1.3 | 작가/도메인 분산 | 같은 작가·같은 단일 도메인에서만 발견된 게 아님 (외부 메타로 확인 가능 시) | `rejected: "genre_dependent"` 또는 `hold` |

**판정 가이드:** 재현 게이트는 "이 패턴이 진짜 일반적인 AI 시그니처인지 vs 단발 사고인지"를 가른다. 1.1·1.2는 정량, 1.3은 정성. 1.3을 판정하기 어렵다면 보수적으로 `hold`.

---

## Gate 2 — 본진 중복 게이트 (Deduplication)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 2.1 | 본진 정확 일치 | `ai-tell-taxonomy.md`에 동일 의미·동일 표현의 패턴이 없음 | `merged: "흡수 → {본진ID}"` |
| 2.2 | 본진 변종 여부 | 본진 패턴의 변종이 아니거나, 변종이라도 본진 수정으로 흡수 불가능한 별개 시그니처 | `merged: "변종 → {본진ID} 보강"` (본진 항목의 시그니처 예문에 추가, 풀 후보는 닫음) |
| 2.3 | 카테고리 단일성 | 후보의 `proposed_category`가 단일(2개 이상 카테고리 후보가 아님) | `hold + status_reason: "category_uncertain"` |

**판정 가이드:** 풀의 가장 흔한 "부풀려진 후보"는 본진 변종이다. 본진 보강(`merged`)으로 처리하면 본진의 표현력이 늘면서 풀이 가벼워지므로 적극 활용한다.

---

## Gate 3 — 분류 적합성 게이트 (Taxonomy Fit)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 3.1 | AI 특이성 | 인간 필자가 "거의 안 쓴다"고 판단할 만한 시그니처 (한국어 필자 중간값 기준) | `rejected: "not_ai_specific"` |
| 3.2 | 객관 시그니처 | 어휘·구문·구조·통계로 객관적으로 식별 가능 (주관적 "어색함"이 아님) | `rejected: "subjective_aesthetic"` |
| 3.3 | 경계 안정성 | 본진의 인접 패턴과 경계가 명확 (같은 span에 두 패턴이 동시 매칭되는 모호 영역 작음) | `rejected: "ambiguous_overlap"` 또는 `hold` |
| 3.4 | 심각도 일관성 | `proposed_severity`(S1/S2/S3)가 본진의 동급 패턴들과 일관 (S1은 "한 번 나와도 결정적"인 것만) | `hold + status_reason: "severity_recalibration_needed"` (taxonomist가 심각도 재산정 후 다음 회차) |

---

## Gate 4 — 처방 적합성 게이트 (Fix Feasibility)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 4.1 | 처방 존재 | `suggested_fix_draft`가 비어있지 않거나, taxonomist가 본 회차에 작성 가능 | `hold + status_reason: "no_viable_fix_yet"` |
| 4.2 | 의미 불변 충돌 없음 | 처방 적용 시 사실·주장·수치·인용이 보존됨 | `rejected: "subjective_aesthetic"` (처방 자체가 의미 훼손이면 패턴 분류로 부적합) |
| 4.3 | 장르 유지 충돌 없음 | 처방이 입력 장르(칼럼·리포트·블로그·공적)에서 이탈하지 않음 | `rejected: "genre_dependent"` 또는 처방 수정 후 재판정 |
| 4.4 | 과윤문 위험 낮음 | 처방이 변경률 30% 임계를 단독으로 끌어올리지 않음 | 처방 수정 후 재판정 (게이트 fail은 아님) |
| 4.5 | rewriting-playbook 충돌 없음 | `references/rewriting-playbook.md`의 카테고리별 레시피와 일관 | 윤문가와 합의 후 재판정 (`hold + status_reason: "playbook_conflict"`) |

---

## Gate 5 — 본진 위계 게이트 (Authority Hierarchy)

| # | 항목 | 통과 조건 | fail 처리 |
|---|------|----------|----------|
| 5.1 | 무력화 정책 명시 | 새 패턴이 voice profile로 무력화 가능한지/불가능한지 명시 가능 | `hold + status_reason: "authority_unspecified"` |
| 5.2 | multiplier 캡 충돌 없음 | 새 패턴의 무력화 가능 옵션이 본진 권한 위계 §4의 캡(일반 ≤2.0, D ≤1.5, A-8/C-5 = 1.0)과 정합 | 캡 정책 갱신 후 재판정 |

**판정 가이드:** 게이트 5는 v1.2 권한 위계 도입 이후 신규 게이트. 새 패턴이 D 카테고리에 들어간다면 multiplier 캡이 자동으로 1.5 적용되는지 확인. 만약 새 패턴이 voice profile로 끌 수 없는 결정적 시그니처라면 `disable_blocked: true` 메타와 함께 본진 등재.

---

## 종합 판정 매트릭스

| Gate 0 | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Gate 5 | 결과 |
|--------|--------|--------|--------|--------|--------|------|
| pass | pass | pass | pass | pass | pass | **promoted** (본진에 새 ID 발급) |
| pass | pass | 2.1 fail | - | - | - | **merged** (본진 흡수) |
| pass | pass | 2.2 fail | - | - | - | **merged** (본진 항목 보강) |
| pass | fail | - | - | - | - | **hold** (재현 부족) |
| pass | pass | 2.3 fail | - | - | - | **hold** (카테고리 모호) |
| pass | pass | pass | 3.1·3.2 fail | - | - | **rejected** |
| pass | pass | pass | pass | 4.2·4.3 fail | - | **rejected** |
| 0.3 fail | - | - | - | - | - | **rejected** (90일 미재현 단일) |

---

## 자동 검증 가능 항목

본 체크리스트의 일부는 풀 파일을 파싱해 정량적으로 자동 판정할 수 있습니다. 향후 스크립트화 시 우선순위:

- **Gate 0.2** (필수 필드): YAML 파서로 즉시 자동화 가능
- **Gate 0.3** (90일 만료): `created_at` 비교로 자동화 가능
- **Gate 1.1** (occurrences): 정수 비교
- **Gate 1.2** (run 분산): `signature_examples[].source_run_id` distinct count
- **Gate 5.2** (multiplier 캡): 본진 카테고리 매핑으로 자동 검증

나머지 게이트(2.x, 3.x, 4.x, 5.1)는 의미 판단이 들어가므로 taxonomist의 정성 판정이 필요합니다. 자동 검증 스크립트는 추후 별도 PR에서 `scripts/check_promotion.py`로 추가 예정 — 현 v1.3에서는 taxonomist가 본 체크리스트를 수기 적용합니다.

---

## 사용 예시

회차 N의 후보 `cand-A-2026-007` 점검:

```
Gate 0.1 ✓ pending
Gate 0.2 ✓ 필수 필드 완비
Gate 0.3 ✓ last_seen_at 14일 전
Gate 1.1 ✓ occurrences = 3
Gate 1.2 ✓ source_run_id distinct = 3
Gate 1.3 ✓ 작가 2명·장르 2종 분산
Gate 2.1 ✓ 본진 정확 일치 없음
Gate 2.2 ✗ 본진 A-2(`~를 통하여` 남발)의 변종으로 판단 — `~을 매개로` 표현
→ merged: 흡수 → A-2 (본진 항목의 시그니처 예문에 `~을 매개로` 추가)
```

회차 N의 후보 `cand-D-2026-012` 점검:

```
Gate 0~1 ✓ all pass
Gate 2.1 ✓ 본진 일치 없음
Gate 2.2 ✓ 변종 아님 (별개 시그니처)
Gate 2.3 ✓ proposed_category = D 단일
Gate 3.1 ✓ AI 특이성 충족
Gate 3.2 ✓ 객관 시그니처
Gate 3.3 ✓ 경계 안정
Gate 3.4 ✓ S2 적정
Gate 4.1 ✓ suggested_fix_draft 존재
Gate 4.2~4.5 ✓ 모두 통과
Gate 5.1 ✓ 무력화 가능 (D 카테고리이지만 새 D-7로서 multiplier 캡 1.5 적용)
Gate 5.2 ✓ 캡 충돌 없음
→ promoted: 본진에 D-7로 신규 등재, taxonomy "버전 관리" 섹션에 v1.3 항목 추가
```
