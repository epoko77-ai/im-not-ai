# Pattern Candidates Pool (v1.3~)

분류 체계 본진(`ai-tell-taxonomy.md`)에 승격되기 전, 에이전트들이 실전에서 발견한 "AI 티 의심 패턴" 후보를 단일 그릇으로 누적하는 곳. taxonomist가 이 풀을 주기적으로 점검해 v1.x로 승격하거나 기각한다.

## 역할 분담

- **detector·rewriter·naturalness-reviewer**: 미분류 의심 span을 발견하면 본 풀에 후보로 적재(또는 기존 후보의 `occurrences`를 +1).
- **korean-ai-tell-taxonomist**: 풀 운영자. 재현 2회 이상·심각도 일관 후보를 본진으로 승격, 부적합·중복은 기각.

본 풀은 SSOT가 아니라 **승격 전 작업대**다. 탐지기·윤문가는 풀의 후보를 직접 적용하지 않는다 — 본진(`ai-tell-taxonomy.md`)에 승격된 패턴만 운영 규칙이다.

## 후보 스키마

각 후보는 다음 YAML 항목으로 풀에 누적된다.

```yaml
- id: "cand-A-2026-001"      # 임시 ID. 형식: cand-{대분류 힌트}-{YYYY}-{NNN}
  pattern_label: "한 줄 라벨"  # taxonomy 본진 항목명과 동일 톤
  proposed_category: "A | B | C | D | E | F | G | H | I | J"
  proposed_severity: "S1 | S2 | S3"
  description: |
    이 패턴이 무엇이고 왜 AI 티인지 1~3줄 설명.
  signature_examples:          # 실제 발견된 원문 span (최소 1건, 승격 시 2건+)
    - text: "원문 span"
      context: "한 문장 정도의 주변 맥락"
      source_run_id: "2026-04-25-001"   # _workspace/{run_id}/01_input.txt에서 발견
      discovered_by: "ai-tell-detector | korean-style-rewriter | naturalness-reviewer | external"
      discovered_at: "2026-04-25"
  suggested_fix_draft: "윤문 처방 초안 (있을 때만)"
  occurrences: 1               # 동일 패턴이 다른 run에서 재현될 때마다 +1
  status: "pending"            # pending | promoted | rejected | merged
  status_reason: ""            # 기각·병합 시 사유 + 머지된 본진 ID (있을 때)
  created_at: "2026-04-25"
  last_seen_at: "2026-04-25"
  reviewed_by_taxonomist: false
```

## 적재 절차 (에이전트용)

1. **중복 검사**: 새 후보를 추가하기 전 풀의 기존 `pending` 항목을 훑어 동일 패턴이 있는지 확인. 같은 패턴이면 신규 항목 생성 대신 다음을 갱신:
   - `occurrences` +1
   - `signature_examples`에 새 사례 append (최대 5건까지, 그 이상은 누락)
   - `last_seen_at` 갱신
2. **본진 중복 검사**: `ai-tell-taxonomy.md`의 기존 패턴(`A-1`~`J-N`)과 의미가 겹치면 후보로 추가하지 말고, run 산출물에 "기존 ID `X-N`로 분류 가능" 기록만 남긴다.
3. **신규 항목 ID 발급**: `cand-{대분류 힌트}-{YYYY}-{NNN}`. NNN은 해당 연도 안에서 풀 전체 누적 카운트(대분류와 무관). 대분류 힌트가 불확실하면 `cand-X-YYYY-NNN`로 두고 taxonomist가 분류.
4. **원문 보존 필수**: `signature_examples[].text`는 원문 그대로. 윤문된 형태나 일반화된 형태로 적지 않는다.
5. **기록 후 알림**: 적재 직후 본 run의 산출물(예: `05_naturalness_review.json`의 `unclassified_candidates_appended`)에 신규/갱신된 후보 ID 목록을 남겨 taxonomist 점검 trigger.

## 승격 기준 (taxonomist 운영)

후보가 다음 조건을 모두 충족하면 본진으로 승격 가능 (taxonomist 최종 판정):

1. **재현**: `occurrences ≥ 2` (서로 다른 source_run_id 기준 2건 이상)
2. **장르 분산**: 같은 작가·같은 run에서만 발견된 패턴은 보류 — 최소 2개 이상의 서로 다른 입력 맥락 필요
3. **수술 가능성**: `suggested_fix_draft`가 의미 불변·장르 유지·과윤문 금지 4대 철칙과 충돌하지 않음
4. **본진 중복 아님**: 기존 패턴의 변종이면 본진 항목에 보강(예: `A-2`의 시그니처 예문 추가)으로 처리하고 후보는 `merged`로 닫음

승격 시: 본 후보의 `status`를 `promoted`로 갱신, `status_reason`에 머지된 본진 ID(예: `promoted to A-16`) 기재. 기각 시: `status: rejected` + 사유. 본진 보강으로 흡수: `status: merged` + 본진 ID.

**기각 사유 표준 라벨:**
- `not_ai_specific` — 인간 필자도 흔히 쓰는 표현
- `single_run_only` — 한 run에서만 발견, 장르 분산 미달
- `genre_dependent` — 특정 장르(에세이·SNS)에서만 자연스러운 변별, 일반화 불가
- `subjective_aesthetic` — "어색하다"는 주관 평가에 가깝고 객관 시그니처 부족
- `ambiguous_overlap` — 본진 패턴과 경계가 흐려 어느 쪽으로도 분류 불안정

## 라이프사이클 정책

- `pending` 상태로 90일 이상 머무르면서 `occurrences == 1`인 후보는 다음 taxonomist 점검 회차에서 자동 후보 만료(`status: rejected`, `status_reason: "single_run_only — 90일 미재현"`).
- `promoted`·`rejected`·`merged` 상태는 본 풀에 계속 보존(삭제 금지). taxonomy 변경 이력의 한 축이며, 같은 후보가 재제안되는 것을 방지한다.
- 본 풀의 항목 수가 200을 넘으면 `references/archive/pattern-candidates-{YYYY}.md`로 closed(promoted/rejected/merged) 항목을 분리해 본 파일은 pending 중심으로 유지.

## 외부 contributor 적재 (Issue/PR 경로)

GitHub Issue 또는 PR로 외부에서 후보를 제출할 때도 본 스키마를 그대로 사용한다.

- `discovered_by: "external"`
- `signature_examples[].source_run_id`: 외부 사례면 Issue/PR 번호 (예: `gh-issue-12`)
- 외부 contributor는 `id`를 직접 발급하지 말고 `cand-X-YYYY-pending`로 두면 머지 시 maintainer가 정식 ID 발급
- 외부 후보도 동일 승격 기준(재현 2회+·장르 분산·본진 중복 아님)을 적용

`§6 외부 회귀 검증 케이스 모집`(Issue #4)과 별개 트랙 — Issue #4는 voice profile 회귀용, 본 풀은 신규 패턴 발굴용이다.

## 풀 운영 주기 (taxonomist)

기본은 사용자 trigger 기반(taxonomist는 호출되어야 작동). 다음 4가지 trigger 중 하나에 해당하면 풀 점검:

1. **사용자 명시 요청**: "패턴 풀 점검", "후보 승격 검토", "v1.x 분류 확장"
2. **풀 누적 임계**: `pending` 항목 10건 이상
3. **고빈도 후보 등장**: 단일 후보의 `occurrences ≥ 3`
4. **외부 PR/Issue 도착**: 외부 contributor 후보가 새로 등재됨

점검 산출물은 `_workspace/taxonomy_changelog.md`에 회차별로 누적(어떤 후보가 어떤 사유로 승격·기각되었는지 추적 가능).

---

## 풀

<!-- pending: 아직 점검 전 -->
<!-- 신규 후보는 이 섹션에 append. 적재 절차의 중복 검사·필수 필드를 지킬 것. -->

(현재 0건)

---

<!-- promoted: 본진 승격 완료 -->

(현재 0건)

---

<!-- rejected: 기각 -->

(현재 0건)

---

<!-- merged: 본진 패턴에 흡수 -->

(현재 0건)
