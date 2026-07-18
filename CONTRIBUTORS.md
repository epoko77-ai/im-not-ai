# Contributors

`im-not-ai`(humanize-korean) 개발에 기여해 주신 분들을 기록합니다. GitHub의 자동 Contributors 통계는 commit author 기준이라 외부 통찰·reference 작업이 잘 잡히지 않아, 별도 명단으로 정리합니다.

## Maintainer

- **[@epoko77-ai](https://github.com/epoko77-ai)** (이승현, epoko@nate.com) — 프로젝트 창립 및 유지보수. 분류 체계(`ai-tell-taxonomy.md`) 설계, 초기 5인 에이전트 파이프라인 구축(v2.1에서 정밀 3콜 구조로 재편), v1.0~v1.2 릴리스 책임.

## v1.2 외부 기여자

### [@simonsez9510](https://github.com/simonsez9510) (Won Seongmuk)

**기여**: 한국어 비소설 단행본 원고(약 8.5만 자, 9개 챕터+에필로그) 출판사 송고 전 최종 검수에 v1.1을 실전 적용한 후기 + 개선 제안 4건 + 어댑터 reference PR.

**반영**:
- [Issue #1](https://github.com/epoko77-ai/im-not-ai/issues/1) "실전 사용 후기 + 개선 제안 4건 — 단행본 원고 8.5만 자 적용 결과"
  - v1.2 권한 위계 §1~§6 신설 동기 (`ai-tell-taxonomy.md`)
  - `author-context.yaml` 스키마 신설 (`references/author-context-schema.md`)
  - 에이전트 주입 분리 정책 (detector/rewriter/auditor 주입, naturalness-reviewer 미주입)
- [PR #3](https://github.com/epoko77-ai/im-not-ai/pull/3) "v1.2 권한 위계 다운스트림 어댑터 reference"
  - Multiplier 캡 정책 (일반 ≤ 2.0, D-1~D-6 ≤ 1.5, A-8·C-5 = 1.0 고정)
  - `reviewer_contract.naturalness_reviewer_voice_blind` 강제 필드
  - Schema validator 책임 강화 (자유 텍스트 거부, prompt injection escape character 검증)
  - Telemetry 정책 (`voice_profile_log.json`)
  - Hard-block은 caller/adapter 책임 명시
  - 어댑터 reference 본체는 `references/proposals/` 격리 보존 예정 (book_essay 보강 후 머지)

**관련 commit**: `bfcf676`, `9f39ce0`, `81fd1b9`

### [@gaebalai](https://github.com/gaebalai) (AI-fluent liberal arts Engineer)

**기여**: LICENSE 누락 지적 + 슬래시 커맨드/Plugin/자동 설치기 reference + 외부 distribution channel 운영.

**반영**:
- [Issue #5](https://github.com/epoko77-ai/im-not-ai/issues/5) "라이선스 내용이 추가해주심이?"
  - MIT License 본체 도입 (`LICENSE`, `adc2814`)
- [Issue #6](https://github.com/epoko77-ai/im-not-ai/issues/6) "슬래시커맨드가 있으면 더 좋을것 같아요"
  - `/humanize`, `/humanize-redo` 슬래시 커맨드 본체 도입 (`9054518`)
  - v1.3 메이저 업데이트 검토 ([Issue #8](https://github.com/epoko77-ai/im-not-ai/issues/8))
- [`gaebalai/im-not-ai`](https://github.com/gaebalai/im-not-ai) 포크
  - Claude Code Plugin/Marketplace 규격 패키징 reference
  - 자동 설치기(`install.sh`) reference
  - 6개 슬래시 커맨드 reference
  - README "방법 C"에서 본체 distribution channel로 안내

**관련 commit**: `adc2814`, `9054518`

## 기여하기

본 프로젝트는 MIT 라이선스이며 외부 기여를 환영합니다. 기여 형태는 다음 중 무엇이든 좋습니다.

- **새 AI 티 패턴 제보** — `references/ai-tell-taxonomy.md` 후보로 Issue 등록 (실증 사례 2건+ 첨부 시 승격 검토)
- **사용성 개선 제안** — 슬래시 커맨드, Plugin 통합, 자동화 reference 등
- **다국어 확장** — 일본어/중국어 분류 체계 적용 가능성 검토
- **버그 리포트** — Issue로 등록

PR 보내실 때는 GitHub 기본 inbound = outbound 원칙에 따라 동일한 MIT 라이선스로 contribution됩니다. 본 명단은 v1.x 단위로 갱신됩니다.
