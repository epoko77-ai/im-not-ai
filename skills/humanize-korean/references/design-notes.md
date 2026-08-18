# Humanize Korean — 설계 근거·버전 히스토리 (design-notes)

> SKILL.md에서 이관된 설계 근거 — **실행 규칙은 SKILL.md 참조.** 이 파일은
> 스킬 발동 시 로드되지 않는다. 규칙을 되돌리려는 기여자가 "왜 이렇게
> 됐는가"를 확인하는 용도다.

## 버전 히스토리 (상세)

- **v1.5 (2026-04-26)** — v1.1 5인 파이프라인 위에 단일 호출 `humanize-monolith` fast path 신설. voice profile·candidate pool·권한 위계 §1~§6은 핫패스 비용 문제로 삭제.
- **v1.6 (2026-05-07)** — KatFish·LREAD 기반 정량 점수 레이어 도입. `scripts/prepare_monolith_input.py`(입력 shim)가 monolith 호출 *전* 외부 사전 처리로 점수를 산출해 결합 입력 파일에 prepend.
- **v1.6.1 (2026-05-07)** — fast 산출물을 `final.md` 1개로 통합(본문 끝 `<!-- HUMANIZE-SUMMARY -->` HTML 주석 블록). monolith 도구 호출 캡 4회 → **3회**.
- **v2.0 (2026-05-07)** — 한국 번역학계 8유형 + post-editese metric 트랙(`metrics_v2.py`) 흡수. 분류 체계 본진 v2.0(활성 패턴 70건 + A-17 hold 1건).
- **v2.0.1** — 패치 릴리스: shim 실행 절차 명문화, 실사용 백포트(격식 상향 금지·구조/각주 보존·과윤문 게이트 코드화), quick-rules 빌드 생성.
- **v2.1.0** — 정밀 모드를 5인 파이프라인 → **3콜 구조**(진단→겨냥 윤문→finalize)로 재편. 옛 4종+web-architect 은퇴. 8,000자 strict 자동 승급 폐지.
- **v2.2.0** — **경량 경로 재설계.** shim이 산출하는 `route_hint`(light|standard|heavy)로 디폴트 경로를 3단 분기. **단일 콜 우선 원칙** 명문화 — 1만자급도 청킹 없이 단일 콜(실측: 청킹 7콜 610K 토큰 → 단일 콜 134K, 품질 동등). 청킹은 shim이 실제로 청크를 2개 이상 만들 때만. finalize는 heavy·의심·사용자 요청 시로 한정.
- **v2.3.0** — **효율화 릴리스.** ① Tier 1 구조 수렴 게이트(`verify_gates.py` 4축: 문자율 + 진단 목표달성 z 수렴 + C-8 대구 전멸 + golden/수치) — 문자 change_rate가 못 보는 구조 편집(쉼표·대구 해체)을 결정적으로 검증, LLM 콜 0. ② 진단 입력을 taxonomy 전량(74.8KB) → `diagnosis-rules.md` 슬림 인덱스(~13KB, 빌드 생성)로 교체, 진단 콜 토큰 35~50%↓. 실측 회귀에서 하중 패턴(C-8·C-11·E-5·D-7) 지목 동등.

## 설계 노트 — 단일 콜 우선 (v2.2 실측 근거)

**1만자 글 실측**: 정밀 청킹 경로(7콜) = **610K 토큰**. 같은 입력 단일 콜 = **134K 토큰**(4.5배 절감), 품질 동등. 폭발 원인은 청크 콜마다 룰북·진단·시스템 프롬프트를 재로드한 것 — 절감은 모델 교체가 아니라 **콜 수 축소**에서 온다. 요즘 모델은 1만자를 단일 콜로 무리 없이 처리하므로, 청킹은 "shim이 실제로 쪼갤 수밖에 없는 초장문"의 예외 경로다.

또 하나의 실증: 어휘 티 0·구조 티만 있는 잘 쓴 글에도 최중량 파이프라인을 돌리고 있었다. v2.2의 route_hint 분기가 이를 차단한다.

(v2.1까지의 "왜 5인에서 3콜로" 배경: 옛 5인 파이프라인은 detector span 열거가 0↔18개로 요동쳐 불안정했고, 587줄 taxonomy를 이중 로드해 탐지에만 wall-clock 54%를 썼다. 웹앱 실증에서 "지배 패턴 진단 1콜 + 결정적 지표 수렴"이 동급 품질을 냈고, 3콜 구조는 그 이식이다. v2.2는 같은 원리를 한 단계 더 밀어 진단·finalize조차 필요할 때만 쓰게 했다.)

## 설계 노트 — 진단 슬림 인덱스 (v2.3)

진단(humanize-diagnostician)의 핸드오프 계약은 "정확한 본진 ID + 지배도 판단"이다. taxonomy 전량(74.8KB)의 대부분은 예문·처방·학술 인용·버전주석 — 진단에 불필요. `scripts/build_diagnosis_rules.py`가 SSOT에서 71패턴 전수(ID·정의·탐지 시그니처)를 ~13KB로 결정적 생성한다(83% 절감). quick-rules로 대체할 수 없는 이유: 진단은 문서 레벨 패턴(C-8 대구·E-1 리듬·D-6 결말공식 등 quick:false 23종)을 반드시 봐야 한다. drift는 CI `--check`가 차단.

## 테스트 시나리오

### Light — 잘 쓴 글
- 입력: 사람이 쓴 칼럼 또는 어휘 티 없는 글 (route_hint=light)
- 기대: monolith 1콜(보수), 변경률 5% 미만, "이미 좋습니다 + 손댄 곳 요약" 보고. 진단·finalize 콜 0

### Standard — 보통의 AI 초안
- 입력: ChatGPT가 생성한 AI 칼럼 초안 (2,000~10,000자, route_hint=standard)
- 기대: 진단 1콜 + 윤문 1콜 = 2콜, **1만자도 청킹 없음**, 변경률 15~25%, 등급 A/B, finalize 생략

### Heavy — 중증·증적 필요
- `--strict` 명시 또는 route_hint=heavy
- 기대: 진단→윤문→finalize 3콜. 변경률 11~22%, `09_finalize.json` verdict=accept/corrected

### 초장문 — 청킹은 shim의 결정
- heavy + shim 청킹 임계 초과 입력 → `--chunk` 실행, manifest body 청크 2+개일 때만 병렬. 청크가 1개로 나오면 단일 콜. 손실 없는 분할 + 헤딩 승격 + 각주 passthrough

### 엣지 케이스 — route_hint 부재
- 구버전 shim·metrics 실패(`00_metrics.error`) → standard 경로로 진행. 게이트는 항상 실행

## 에이전트 계보 (은퇴·개발용)

**개발용 1회성 5종 (릴리스 회차 전용 — 런타임 미로드)**
- `translationese-research-distiller` · `korean-translation-scholar` · `taxonomy-gap-analyzer` · `post-editese-metric-engineer` · `quick-rules-integrator` — v2.0 학술 흡수 회차에서 사용된 개발 도구. 윤문 실행과 무관

> v2.1에서 옛 정밀(strict) 파이프라인 4종(`ai-tell-detector`·`korean-style-rewriter`·`content-fidelity-auditor`·`naturalness-reviewer`)과 미사용 `humanize-web-architect`를 은퇴시켰다. 진단·윤문·finalize 3콜이 이들을 대체한다.
