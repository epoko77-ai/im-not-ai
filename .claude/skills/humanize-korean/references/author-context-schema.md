# Author Context Schema (v1.2~)

작가/작품별 voice profile을 humanize-korean 파이프라인에 명시 주입하는 양식. 분류 체계의 패턴이 작가 의도와 충돌할 때 제한적 무력화를 허용하되, **권한 위계**(`ai-tell-taxonomy.md` § 권한 위계)의 6개 규칙을 강제한다.

## 사용 시점

작가별 고유 voice가 객관 분류 패턴과 정면 충돌할 때만 사용한다. 예:
- 단단한 서술체 voice를 가진 작가가 em-dash를 의도적 리듬 장치로 활용 → J-3 임계 완화
- 작가/책 mandate가 "~수 있다 사용 권장" → A-10 무력화
- 책 고유 메타포가 도구의 일반 윤문 대상이 되는 것을 차단 → do_not_extra 키워드

장르가 다르다는 이유만으로(예: "내 책은 단행본이니까") 무력화하지 않는다. 장르는 SKILL.md의 `genre_hint`로 처리된다.

## 4대 제약

1. **opt-in 명시 주입만 허용**. 자동 로드(프로젝트 CLAUDE.md 자동 파싱 등)는 거절.
2. **자유 텍스트 mandate 금지**. 모든 override는 패턴 ID 또는 키워드 단위로 구조화.
3. **무력화 불가 패턴 존재**. A-8(이중 피동), C-5(이모지), D-1~D-6(AI 특유 관용구)은 어떤 이유로도 끄지 못한다. `pattern_overrides`에 들어와도 `naturalness-reviewer`가 잔존을 다시 잡는다.
4. **`naturalness-reviewer` 미주입**. voice profile은 `ai-tell-detector`·`korean-style-rewriter`·`content-fidelity-auditor` 3개 에이전트에만 주입된다. 분리 검증층을 한 층 남겨 두는 것이 도구의 신뢰성 근거다.

## 파일 위치

작업 cwd 또는 `_workspace/{run_id}/` 둘 중 한 곳에 `author-context.yaml` 파일로 둔다. 오케스트레이터가 Phase 0에서 다음 우선순위로 탐색한다.

1. `<cwd>/_workspace/{run_id}/author-context.yaml` (이번 실행 전용)
2. `<cwd>/author-context.yaml` (프로젝트 단위 기본값)

탐색 결과가 없으면 voice profile 미주입 모드로 진행(v1.1과 동일 동작).

## 스키마

```yaml
# author-context.yaml — voice profile 양식 (humanize-korean v1.2~)
#
# 권한 위계: ai-tell-taxonomy.md § "권한 위계 (Authority Hierarchy)" 참조
# 자유 텍스트 mandate 금지. 패턴 ID 또는 키워드 단위만 허용.

version: "1.0"

# 메타 정보 (검증 로직에 영향 없음, 리포트·로그용)
profile:
  author: "작가 식별자"
  work: "작품/문서 식별자"
  notes: "voice 특성 한 줄 요약"

# 패턴 무력화 — 분류 체계의 특정 패턴 ID에 한해 적용 강도 조절
pattern_overrides:
  - id: "J-3"             # 무력화 대상 패턴 ID (taxonomy의 ID 그대로)
    action: "relax"       # disable | relax (둘 중 하나, 자유 텍스트 금지)
    multiplier: 2.0       # action=relax 일 때만 사용. taxonomy 기본 임계 × 배율
                          # 일반 패턴 캡: ≤ 2.0 / D-1~D-6 캡: ≤ 1.5 / A-8·C-5: 1.0 고정
    reason: "작가가 em-dash를 의도적 리듬 장치로 활용"

  - id: "A-10"
    action: "disable"
    reason: "프로젝트 CLAUDE.md mandate: '~수 있다' 사용 권장"

# 보호 키워드 화이트리스트
# 이 키워드들이 포함된 span은 detector 단계에서 탐지 대상에서 제외된다.
# 책 제목·작가 고유 메타포·시리즈 명·고유 어휘 등 보호하고 싶은 표현만.
do_not_extra:
  - "기계의 지갑"
  - "지하경제 렌즈"

# 분리 검증 계약 — naturalness-reviewer voice-blind 강제 (§5)
# 이 필드는 반드시 true. false로 설정하면 schema validator가 거부한다.
# v1.2 권한 위계 §5: voice profile은 naturalness-reviewer에 도달하지 않는다.
reviewer_contract:
  naturalness_reviewer_voice_blind: true

# 무력화 불가 패턴 (참고용 — 여기에 적어도 적용되지 않는다)
# 다음 ID는 pattern_overrides에 disable/relax로 들어와도 거부된다.
# - A-8 (이중 피동 ~되어진다)
# - C-5 (이모지 남발)
# - D-1 ~ D-6 (AI 특유 관용구)
```

## 필드 명세

### `version`
스키마 버전. 현재 `"1.0"`. 향후 스키마 변경 시 호환성 검증에 사용.

### `profile`
메타 정보 블록. 검증 로직에 영향 없으며 리포트·로그·디버깅용. 모든 필드 선택사항.

| 필드 | 타입 | 설명 |
|------|------|------|
| `author` | string | 작가 식별자 |
| `work` | string | 작품·문서 식별자 |
| `notes` | string | voice 특성 메모 |

### `pattern_overrides`
무력화 규칙 배열. 각 항목은 다음 구조.

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `id` | string | 필수 | taxonomy의 패턴 ID (예: `J-3`, `A-10`) |
| `action` | enum | 필수 | `disable` 또는 `relax`만 허용 |
| `multiplier` | number | `action=relax`일 때만 | taxonomy 기본 임계 × 배율. 캡 적용 (아래 표) |
| `reason` | string | 권장 | 무력화 사유 (감사 추적용) |

**Multiplier 캡** (taxonomy 권한 위계 §4):

| 패턴 종류 | 캡 | 비고 |
|----------|----|------|
| 일반 패턴(A-1~A-7, A-9, A-10~A-15, B-*, C-1~C-4, C-6~C-8, E-*, F-*, G-*, H-*, I-*, J-*) | `0.5 ≤ multiplier ≤ 2.0` | 작가 voice 보존 |
| **D-1 ~ D-6** AI 특유 관용구 | `0.5 ≤ multiplier ≤ 1.5` | 단일 사용 leniency만. 임계 우회를 통한 사실상 disable 방지 |
| **A-8** 이중 피동, **C-5** 이모지 | `multiplier = 1.0` 고정 | 임계 완화 자체 불허 |

**`action: "disable"` 거부 ID** (schema validator가 항목째 거부 + 경고 출력):
- `A-8`, `C-5`, `D-1` ~ `D-6`

**금지 필드:** 자유 텍스트 명령(`mandate`, `instruction`, `note`, `voice_anchors` 등 모든 자연어 advisory). 추가 필드는 schema validator가 거부한다(무시되지 않고 명시적 reject — 사용자가 의도한 것일 수 있어 silent ignore는 위험).

### `do_not_extra`
키워드 문자열 배열. detector가 이 키워드를 포함하는 span을 탐지에서 제외한다. 정규식 미지원, 정확한 부분 문자열 매칭만.

기존 do-not list(`rewriting-playbook.md` § 3 — 수치·고유명사·법률 조문 등)는 항상 보호된다. `do_not_extra`는 그 위에 사용자 정의 키워드를 추가하는 슬롯.

### `reviewer_contract`
v1.2 권한 위계 §5 강제 메커니즘. 분리 검증층 보존을 schema 단계에서 contract로 잠근다.

| 필드 | 타입 | 필수 | 허용 값 | 설명 |
|------|------|------|---------|------|
| `naturalness_reviewer_voice_blind` | bool | 필수 | `true` 고정 | `false`로 설정 시 schema validator가 파일 전체를 거부 |

이 필드는 미래 schema 확장에서도 `true` 외 값을 허용하지 않는다. 분리 검증층은 도구 신뢰성의 근거이며 voice profile 사용자가 임의로 끄지 못한다.

## Schema validator 책임 (v1.2~)

검증기는 다음 위반을 거부(reject)하며, 거부 시 파일 전체가 미적용 처리된다(silent fallback 금지 — 명시적 에러로 사용자에게 보고).

1. **무력화 불가 ID의 disable**: `A-8`, `C-5`, `D-1`~`D-6`이 `action: "disable"`로 등재
2. **Multiplier 캡 초과**: 일반 패턴 `multiplier > 2.0`, D-1~D-6 `multiplier > 1.5`, A-8·C-5 `multiplier ≠ 1.0`
3. **금지 필드 등재**: `mandate`, `instruction`, `voice_anchors`, `note`(profile 외) 등 자유 텍스트 advisory
4. **`reviewer_contract.naturalness_reviewer_voice_blind: false`**
5. **Schema 이스케이프 시도** (prompt injection 방어): 모든 string 필드(reason, do_not_extra, profile.notes 등)에서 다음 패턴 거부
   - Triple backtick (` ``` `)
   - Role-prefix 토큰 (`system:`, `assistant:`, `user:`, `<|...|>` 등)
   - Markdown 헤딩 (`#`로 시작하는 줄)
   - 모델 제어 시퀀스 (`<|im_start|>`, `<|endoftext|>` 등)

거부 발생 시 출력 예:
```
[author-context error] Validation failed: pattern_overrides[0] — D-3 cannot be disabled (taxonomy authority §4). File rejected, voice profile not applied.
```

## Telemetry (감사 추적)

오케스트레이터는 voice profile 적용 시 다음 정보를 `_workspace/{run_id}/voice_profile_log.json`에 기록한다.

```json
{
  "applied": true,
  "schema_version": "1.0",
  "profile_meta": {"author": "...", "work": "..."},
  "overrides_accepted": [
    {"id": "J-3", "action": "relax", "multiplier": 2.0, "applied_threshold": 4},
    {"id": "A-10", "action": "disable"}
  ],
  "overrides_rejected": [
    {"id": "D-3", "action": "disable", "reason": "permanent default-on per taxonomy §4"}
  ],
  "do_not_extra_triggered": [
    {"keyword": "기계의 지갑", "occurrences": 3, "spans_protected": [142, 891, 1502]}
  ],
  "naturalness_reviewer_received_voice_profile": false
}
```

이 로그는 §6 회귀 테스트 게이트가 measurable 하기 위한 필수 산출물. 외부 케이스 비교 시 voice profile이 없는 baseline run과 voice profile 있는 run의 finding 차이를 이 로그로 추적한다.

마지막 필드 `naturalness_reviewer_received_voice_profile: false`는 §5 분리 검증층 보존이 실제로 작동했음을 입증하는 audit 항목이다. 이 값이 `true`로 기록된 run은 즉시 incident로 처리하고 v1.2 회귀 게이트 리포트에 포함한다.

## Hard-block (caller/adapter 책임)

특정 경로(fiction·legal·third-party 등)에서 humanize-korean 호출 자체를 거부하는 hard-block은 **caller/adapter 책임**이다. 메인테이너 schema는 입력된 텍스트를 처리할 뿐, 어떤 종류의 텍스트인지 판단하지 않는다.

caller/adapter가 자체 schema에 `hard_blocks` 필드를 정의해 사용하는 것은 권장되나, 메인테이너 schema의 표준 부분이 아니다. PR #3의 `proposals/voice-aware-adapter.md`에 caller-side hard-block 패턴이 reference로 제공된다.

## 무력화 불가 패턴 처리

다음 ID는 `pattern_overrides`의 `action: "disable"`로 등재되면 schema validator가 거부한다(silent ignore 아닌 명시적 reject).

- **A-8** 이중 피동 "~되어진다 / ~지게 된다"
- **C-5** 이모지 남발
- **D-1 ~ D-6** AI 특유 관용구 카테고리 전체

`action: "relax"`의 경우:
- A-8·C-5: `multiplier = 1.0` 외 거부 (사실상 임계 완화 불허)
- D-1~D-6: `multiplier ≤ 1.5` 까지만 허용 (단일 사용 leniency)

근거: `ai-tell-taxonomy.md` § 권한 위계 §4. 어떤 작가 의도로도 정당화되지 않는 결정적 AI 시그니처.

## 에이전트별 주입 정책

| 에이전트 | voice profile 주입 | 비고 |
|----------|-------------------|------|
| `korean-ai-tell-taxonomist` | 미주입 | 분류 체계 자체를 정의하는 역할. voice profile에 좌우되면 SSOT가 흔들림 |
| `ai-tell-detector` | **주입** | `pattern_overrides`로 탐지 우회, `do_not_extra`로 보호 키워드 |
| `korean-style-rewriter` | **주입** | 무력화된 패턴은 윤문 대상에서 제외 |
| `content-fidelity-auditor` | **주입** | `do_not_extra` 키워드는 절대 보존 대상 추가 |
| `naturalness-reviewer` | **미주입** | 분리 검증층 보존. voice profile을 모르는 외부 시각이 한 층 남아야 함 |
| `humanize-web-architect` | 해당 없음 | 웹 확장 모드 전용 |

## 잔존 패턴의 처리

`naturalness-reviewer`가 voice profile을 모르기 때문에, 무력화된 패턴이 잔존 finding으로 다시 잡힐 수 있다. 이 경우 오케스트레이터가 다음 규칙으로 처리한다.

- 무력화된 패턴 ID에 해당하는 잔존 finding → `accepted_by_voice_profile` 플래그를 달고 등급 계산에서 제외
- 무력화 불가 패턴(A-8/C-5/D-*)이 잔존하면 → 무력화 시도와 무관하게 정상 잔존으로 처리, 2차 윤문 트리거

이 규칙으로 분리 검증층의 독립성을 유지하면서도 voice profile 사용자가 같은 패턴으로 반복 재윤문되지 않도록 한다.

## 회귀 테스트 게이트

이 스키마에 새로운 무력화 옵션(예: 새 `action` 값, 새 필드)을 추가할 때는 외부 케이스 2~3건(다른 작가·다른 장르)에서 false positive·false negative 비교 리포트를 통과해야 한다. 단일 사용자 self-reported 결과만으로 스키마를 확장하지 않는다(taxonomy 권한 위계 §6).

## 예시 — 단행본 비소설 작가

Issue #1에서 보고된 케이스: 단행본 비소설 작가가 단단한 서술체 voice + em-dash 리듬 장치를 사용. 프로젝트 CLAUDE.md mandate에 "~수 있다 사용 권장" 명시.

```yaml
version: "1.0"

profile:
  author: "Won Seongmuk"
  work: "단행본 비소설 (8.5만 자, 9챕터+에필로그)"
  notes: "단단한 서술체, em-dash 리듬 장치, 1인칭 진입+분석 결합"

pattern_overrides:
  - id: "J-3"
    action: "relax"
    multiplier: 2.0
    reason: "em-dash를 의도적 리듬 장치로 채용 — 8.5만 자에서 150회 자연 등장"
  - id: "A-10"
    action: "disable"
    reason: "프로젝트 CLAUDE.md mandate: '단정적 예측 ~할 것이다 금지, ~수 있다 사용'"
  - id: "E-2"
    action: "relax"
    multiplier: 1.8
    reason: "단단한 서술체 voice의 의도된 종결어미 반복"

do_not_extra:
  - "1인칭 진입"
  - "장면→충돌→시도→결과→성찰→원칙"

reviewer_contract:
  naturalness_reviewer_voice_blind: true
```

이 예시에서 `E-2`는 동일 종결어미 반복 패턴이지만 D 카테고리가 아니므로 일반 캡(2.0) 적용 가능. 단, `naturalness-reviewer`는 voice profile을 모르므로 잔존 시그널을 다시 잡을 것이고, 오케스트레이터가 `accepted_by_voice_profile` 플래그로 처리한다.

## 관련 자료

- **메인테이너 SSOT**: `references/ai-tell-taxonomy.md` § "권한 위계 (Authority Hierarchy)" §1~§6
- **다운스트림 caller reference (PR #3 proposal)**: `references/proposals/voice-aware-adapter.md` — 어댑터가 humanize-korean을 wrap할 때의 호출 envelope·hard-block·post-pass 패턴 reference. proposals/와 메인테이너 schema가 다르면 메인테이너 schema가 우선.
- **Telemetry 로그 위치**: `_workspace/{run_id}/voice_profile_log.json`

## 변경 이력

- **v1.0** (2026-04-25): 초기 스키마 정의. v1.2 PR #3에서 도입.
- **v1.0.1** (2026-04-25): PR #3 어댑터 reference의 통찰 반영(PR #4).
  - `threshold` (절대값) → `multiplier` (taxonomy 기본 임계 × 배율)로 표현 통일
  - Multiplier 캡: 일반 ≤ 2.0, D-1~D-6 ≤ 1.5, A-8·C-5 = 1.0 고정
  - `reviewer_contract.naturalness_reviewer_voice_blind: true` 강제 필드 신설 (§5 schema 단계 강제)
  - Schema validator 책임 강화: 무력화 불가 disable 거부, multiplier 캡 위반 거부, 자유 텍스트 advisory 거부, prompt injection 방어 (escape character 검증)
  - Telemetry 정책 명문화: `voice_profile_log.json` 발행, `naturalness_reviewer_received_voice_profile` 감사 항목 포함
  - Hard-block은 caller/adapter 책임 명시 (메인테이너 schema 외)
