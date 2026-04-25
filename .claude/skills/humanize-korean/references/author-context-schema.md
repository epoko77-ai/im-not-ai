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
  - id: "J-3"            # 무력화 대상 패턴 ID (taxonomy의 ID 그대로)
    action: "relax"      # disable | relax (둘 중 하나, 자유 텍스트 금지)
    threshold: 5         # action=relax 일 때만 사용. 단락당 허용 횟수
    reason: "작가가 em-dash를 의도적 리듬 장치로 활용 — 단행본 8.5만 자에서 150회 자연 등장"

  - id: "A-10"
    action: "disable"
    reason: "프로젝트 CLAUDE.md mandate: '~수 있다' 사용 권장"

# 보호 키워드 화이트리스트
# 이 키워드들이 포함된 span은 detector 단계에서 탐지 대상에서 제외된다.
# 책 제목·작가 고유 메타포·시리즈 명·고유 어휘 등 보호하고 싶은 표현만.
do_not_extra:
  - "기계의 지갑"
  - "지하경제 렌즈"

# 무력화 불가 패턴 (참고용 — 여기에 적어도 적용되지 않는다)
# 다음 ID는 pattern_overrides에 disable/relax로 들어와도 무시된다.
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
| `threshold` | number | `action=relax`일 때만 | 단락당 허용 횟수 |
| `reason` | string | 권장 | 무력화 사유 (감사 추적용) |

**금지 필드:** 자유 텍스트 명령(`mandate`, `instruction`, `note` 등). 추가 필드는 무시되며 검증기가 경고를 발행한다.

### `do_not_extra`
키워드 문자열 배열. detector가 이 키워드를 포함하는 span을 탐지에서 제외한다. 정규식 미지원, 정확한 부분 문자열 매칭만.

기존 do-not list(`rewriting-playbook.md` § 3 — 수치·고유명사·법률 조문 등)는 항상 보호된다. `do_not_extra`는 그 위에 사용자 정의 키워드를 추가하는 슬롯.

## 무력화 불가 패턴 처리

다음 ID는 `pattern_overrides`에 `disable` 또는 `relax`로 들어와도 무시된다.

- **A-8** 이중 피동 "~되어진다 / ~지게 된다"
- **C-5** 이모지 남발
- **D-1 ~ D-6** AI 특유 관용구 카테고리 전체

근거: `ai-tell-taxonomy.md` § 권한 위계 §4. 어떤 작가 의도로도 정당화되지 않는 결정적 AI 시그니처.

검증기는 이런 항목을 발견하면 다음 경고를 출력한다.
```
[author-context warning] Pattern A-8 cannot be overridden (taxonomy authority §4). Ignored.
```

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
    threshold: 5
    reason: "em-dash를 의도적 리듬 장치로 채용 — 8.5만 자에서 150회 자연 등장"
  - id: "A-10"
    action: "disable"
    reason: "프로젝트 CLAUDE.md mandate: '단정적 예측 ~할 것이다 금지, ~수 있다 사용'"
  - id: "E-2"
    action: "relax"
    threshold: 6
    reason: "단단한 서술체 voice의 의도된 종결어미 반복 (단, 무력화 불가 패턴이 아니므로 임계 완화만 허용)"

do_not_extra:
  - "1인칭 진입"
  - "장면→충돌→시도→결과→성찰→원칙"
```

이 예시에서 `E-2`는 동일 종결어미 반복 패턴이지만 D 카테고리가 아니므로 임계 완화 가능. 단, `naturalness-reviewer`는 voice profile을 모르므로 잔존 시그널을 다시 잡을 것이고, 오케스트레이터가 `accepted_by_voice_profile` 플래그로 처리한다.

## 변경 이력

- **v1.0** (2026-04-25): 초기 스키마 정의. v1.2 PR #3에서 도입.
