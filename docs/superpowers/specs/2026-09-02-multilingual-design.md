# 다국어 확장 설계 (2026-09-02)

> 선행 산출물: `docs/spikes/2026-09-02-en-transplant.md` (전수 태깅 + 영어 실측).
> 결정 이력: D1-C(스파이크 우선) · D2-A(영어) · D3-C(미니 코퍼스로 근거 절충)
> → 스파이크 결과와 외부 리서치로 **D3-C는 폐기**한다. 코퍼스를 짓지 않고 발표 수치를 인용한다.

## 1. 리서치가 바꾼 것

### 1.1 인간 영어 대조군 문제가 해소됐다 — 짓지 않고 인용한다

스파이크의 최대 한계는 "인간 영어 코퍼스가 없어 *AI만의 특징인가*에 답 못 함"이었다.
영어는 한국어와 달리 **대규모 human-vs-AI 계량 연구가 이미 여럿 발표돼 있다.**

| 출처 | 등급 | 규모 | 우리에게 주는 것 |
|---|---|---|---|
| **Kobak et al. 2025** (Science Advances) | **E2** (본문 표 미확인 — 페치 요약) | PubMed 초록 **15M편, 2010–2024** | 초과 어휘 291개 + **excess vocabulary 법** |
| **Reinhart et al. 2025** (PNAS) | **E2** (본문 표 미확인 — 페치 요약, 방향만) | Biber 67자질, human(COCA) vs GPT-4o·Llama 3 병렬 | **문법·수사 층 방향** = 우리 T2 층과 동일 층위 |
| **SlopDetector 2026** | **E3** (비심사 블로그, 인간 풀이 문학 고전) | 인간 산문 **702,939 words** vs 6모델 | em dash 실측 (모델별 분해 포함) |
| **Rudnicka & Juzek 2026** | **E3** (프리프린트) | 2024·2026 코호트 각 6모델 | 모델 개인어 반증 |

등급 정의는 `core/principles.md` 「근거 등급 (E1~E4)」. **E3 이하는 단독으로 규칙을
세우지 못한다** — 방향 가설로만 쓰고, 규칙 승격은 E1 또는 표 확인된 E2 를 요구한다.
현재 영어 baseline 후보는 **E1 이 하나도 없다.** 이것이 영어팩이 light/standard 만
열고 heavy·finalize 를 닫는 이유다.

**결론: `lang/en/baseline.json`을 발표 수치로 채운다.** 언어당 수 주였던 캘리브레이션 비용이
인용 작업으로 줄어든다. ko의 `_source_anchor` 관습을 그대로 쓴다.

⚠️ 대가: 장르가 우리와 다르다(생의학 초록·COCA·문학 고전). 인용 수치는 **방향 근거**이지
우리 장르의 임계가 아니다. `evidence: external-published` 라벨로 등급을 명시한다.

### 1.2 Kobak의 방법론이 ko에도 역수입된다

excess vocabulary 법은 **라벨된 코퍼스가 필요 없다.** 초과사망 개념을 빌려,
LLM 이전 연도를 기준선으로 삼고 이후의 초과 사용을 잰다.

ko는 지금 "2022-01-01 이전 발행 확인 + Wayback 이중 검증" 인간 코퍼스를 손으로 짓고 있고,
그 소스는 **시간이 갈수록 마른다**. 시계열 한국어 코퍼스만 있으면 60×60 대조를 짓지 않고도
어휘 티를 채굴할 수 있다. **다국어 작업의 부산물로 ko가 이득을 본다.**

### 1.3 교차언어 확인 — ko 발견이 영어에서 독립 재현됐다

| ko 발견 | 영어 독립 근거 |
|---|---|
| **C-8 대구** (12.1×, 전모델, 과업 무관 — ko 최강) | "not just X, but Y" = antithesis, LLM 산문의 hallmark로 복수 소스 지목. 구문복잡도 연구: ChatGPT는 **coordination 구조 선호·병렬 구문 의존·변이 낮음** |
| **F-7 범용 동사 수렴** (3.4×) | Kobak 2024 초과 어휘의 **66%가 동사**(delve·underscore·showcase), 형용사 14%. 2021 코로나기 초과어는 "거의 전부 내용명사"였던 것과 대조 |
| **F-4 명사화 과다** | Reinhart: nominalization LLM 과다 |
| **G-1·G-2 hedging** | Reinhart: hedges/downtoners LLM 과다 |
| **A-9 피동** | Reinhart: passives LLM 과다 |

ko가 자체 코퍼스로 세운 상위 규칙들이 **완전히 독립적인 영어 연구에서 같은 방향으로 나왔다.**
이건 T2 태깅의 사후 검증이다.

### 1.4 E-1의 불변량은 '장문 부재'가 아니라 '분산 부족'이다 — ko 정정 필요

Reinhart는 LLM 문장이 인간보다 **더 길다**고 보고한다. 동시에 **변이는 적다**.
버스티니스 문헌도 같다 — 인간은 짧은 평서문에 긴 절 문장을 섞어 "터지는데",
LLM은 14–22어 중앙값에 작은 분산으로 "메트로놈처럼" 간다.

ko는 E-1을 "문장 길이 균일" → "**장문 부재**"로 실체화했다(G²=60.9).
영어 증거를 합치면 **장문 부재는 한국어에서의 발현형이고, 언어 불변 축은 dispersion이다.**
스파이크 실측도 그렇게 나왔다(AI 에세이 stdev 6.7~6.8 vs 대조 16.3~18.8).

→ **ko 백포트**: E-1을 "분산 부족(한국어 발현: 장문 부재)"로 재framing.

### 1.5 설계를 바꾼 반증 — 모델 개인어

Rudnicka & Juzek 2026은 "AI language"라는 단일 초변종 관점에 반대하며,
**모델별 언어 서명이 인간의 개인어(idiolect)처럼 공존한다**고 본다.
근거: 2026 코호트 6모델의 contraction 빈도가 **1,200 ~ 30,000/M (25배 폭)**.

SlopDetector의 em dash 실측이 같은 그림을 보여준다:

| | /1k words |
|---|---|
| 인간 (702,939 words 풀) | 4.76 (통제 기준선 3.23) |
| GPT-4.1 | 10.62 (3.3×) |
| Claude Opus 4.6 | 9.09 |
| DeepSeek V3 | 6.95 |
| **Gemini 2.5 Pro** | **3.53** ← 인간과 구별 불가 |
| **Llama 3.1 8B** | **0.00** ← 인간보다 낮음 |

저자 결론: **"em dash는 약한 신호이지 지문이 아니다."**

**ko는 이미 이 문제의 답을 갖고 있다.** `empirical-validation.md`의 판정 기준:
> "모든 모델에서 사람보다 높아야 모델 계열과 무관한 'AI다움'이라 부를 수 있다."

이 기준을 위 표에 적용하면 **J-3(em dash)은 즉시 탈락한다.** 스파이크에서 내가
Tier 2에 넣었던 걸 외부 데이터가 뒤집었다. ko의 H-1(haiku 단독)과 완전히 같은 구조다.

### 1.6 역주입의 메커니즘이 밝혀졌다

스파이크 윤문에서 em dash가 2건 → 5건(**9.33/1k**)으로 늘었다.
SlopDetector가 측정한 **Claude Opus 4.6 = 9.09/1k**.

우연이 아니다. **윤문 콜은 티를 지우면서 자기 모델의 개인어를 심는다.**
철칙 #6(No New Tells)이 다루던 현상의 메커니즘이 이제 특정됐고, **모델별로 측정 가능하다.**

---

## 2. 설계

### 2.1 핵심 통찰 — 이식 가치의 순위가 뒤집혔다

| 순위 | 층 | 이식 비용 | 근거 |
|---|---|---|---|
| **1** | **원리** — 철칙 6개, 증거 기준, 게이트 설계, 역주입 경계 | **0** | 영어 실측이 셋 다 *필요함*을 증명 |
| 2 | **계측** — dispersion·쉼표·길이 분포·변경률 | **0** | `verify_change_rate.py` 무수정 작동(12.8%, exit=0) |
| 3 | **규칙** — T2 48개 | 중 | 발화·윤문 확인됨. 탐지 프레임 재작성 필요 |
| 4 | **탐지 구현** — 정규식 | **불가** | 재현율 0/6에서 출발 |

가장 값진 자산은 taxonomy가 아니라 **증거 기준**이다.
따라서 아키텍처의 중심은 언어팩이 아니라 **커널 = 판정 규칙**이다.

### 2.2 증거 기준을 코드/문서로 명문화 — 이게 커널이다

ko가 비싸게 얻은 3개 판정 규칙을 언어 무관 계약으로 승격한다.

- **G1 전 모델 생존** — 모든 테스트 모델에서 인간 초과여야 규칙이 된다.
  근거: ko H-1(haiku 단독) · EN em dash(Llama 0.00 · Gemini 3.53)
- **G2 과업 통제** — 인간·AI 표본의 과업 조건이 다르면 측정 무효.
  근거: ko J-2 뒤집힘(0.00 → 26.89) · EN 스파이크에서 리포 문서 vs 에세이로 재현
- **G3 역주입 금지** — 윤문 전후를 같은 지표로 재측정, 신규 상승분이 있으면 실패.
  근거: 스파이크 em dash 2→5, 윤문 모델 개인어와 일치

이 셋은 언어와 무관하고, **영어 실측이 셋 다 필요함을 증명했다.** 그게 커널의 자격이다.

### 2.3 디렉터리 (최종형 — R3에서 도달)

```
core/                       # ← 저장소 루트. `${SKILL_ROOT}/core/` 로 런타임 접근
  principles.md             # 철칙 6개 + 증거 기준 G1·G2·G3  ← SSOT의 SSOT
  change_rate.py            # 문자 diff (언어 무관) — metrics_v2 에서 분리
  metrics_universal.py      # dispersion·쉼표·길이 분포 (산술 — 언어 무관)
skills/
  humanize-korean/          # 현행 유지 (R3 에서 lang/ko 로 이동)
  humanize-english/         # R2 신설
scripts/                    # 게이트·shim·빌드 (현행 유지)
```

> **경로 정정 (계획 수립 중 발견).** 초안은 `skills/humanize/core/` 였으나
> `skills/humanize/` 는 **이미 존재하는 진입 스킬**이라 커널이 스킬 안에 중첩된다.
> 저장소 루트 `core/` 로 옮긴다 — ko SKILL.md 가 이미 쓰는 `${SKILL_ROOT}` 규약으로
> 런타임 접근이 되고, `install.sh` 가 `skills/*` 를 명시적 목록으로 순회하므로 간섭이 없다.

언어 감지는 유니코드 스크립트 비율 한 줄. `lang/<code>/manifest.json`이 룰북·메트릭·baseline을 가리킨다.

### 2.4 탐지 어댑터 — 의존성 없이 간다

정규식 재현율 0/6이 문제였다. `pybiber`(Biber 67자질, spaCy 기반)가 기성 해답이지만
ko의 "표준 라이브러리만" 정책과 충돌하고 ~500MB를 끌고 온다.

**도입하지 않는다.** 이유:

ko의 shim도 사실 *전체 탐지*를 하지 않는다 — 정량 점수로 `route_hint`를 정할 뿐이고,
실제 탐지는 monolith 콜이 룰북을 보고 한다. 영어도 같은 분업이면 된다.

| 담당 | 영어에서 | 이식 |
|---|---|---|
| shim (결정적) | 계측형 지표만 — dispersion·쉼표·길이 → route_hint | **100%** |
| shim (결정적) | lexicon 히트 — Kobak 291단어 등 단순 문자열 | **stdlib로 충분** |
| monolith 콜 (LLM) | 통사 프레임 — C-8 antithesis 등 | 원래 LLM 몫 |

**즉 정규식이 못 잡는 건 애초에 LLM이 잡을 것이었다.** 의존성 추가 없음.

### 2.5 영어 baseline은 발표 수치로 채운다

```
lang/en/baseline.json
  F-7 generic-verb    ← Kobak 291 excess words (66% 동사)   evidence: external-published
  F-4 nominalization  ← Reinhart (LLM 과다)                  evidence: external-published
  G-1·G-2 hedging     ← Reinhart (LLM 과다)                  evidence: external-published
  A-9 passive         ← Reinhart (LLM 과다)                  evidence: external-published
  E-1 dispersion      ← Reinhart + 버스티니스 문헌 + 스파이크 실측
  C-8 antithesis      ← 복수 문헌 + 구문복잡도 연구(coordination 편중)
  J-3 em dash         ← SlopDetector — **G1 미통과. 규칙 아님, 관측 지표로만**
```

신규 축(ko에 없음, Reinhart 결핍 신호): contraction↓ · 1·2인칭 대명사↓ · present tense↓.
ko의 결핍 신호 정책을 그대로 적용 — **처방 불가, 탐지·오탐 방지용 관측만**
(없는 것을 지어내는 처방은 의미 드리프트를 부른다).

### 2.6 영어 규칙 출발 세트

T2 48개 전부로 출발하지 않는다. **G1을 발표 수치로 통과시킬 수 있는 것부터.**

- **Tier A (외부 근거 + ko 실측 양쪽)** — C-8 · F-7 · E-1(dispersion) · F-4 · G-1/G-2 · A-9
- **Tier B (구조·서식, 언어 무관성이 자명)** — C-2 불릿 · C-3 헤딩 · C-5 이모지 · C-6 요약박스 · C-9 인덱싱 · C-10 콜론 헤딩 · C-1 열거
- **제외** — J-3(G1 미통과) · H-1 · H-3 · G-3 · D-4 (ko에서도 근거 흔들림)

Tier A + B ≈ 13~15개로 출발. ko의 81개와 비교하면 작지만 **개당 근거 강도는 더 높다.**

---

## 3. 로드맵

### R1 — 원리 층 추출 (언어 이동 없음, 저위험)
- `core/principles.md` 신설: 철칙 6개 + 증거 기준 G1·G2·G3
- ko는 그대로 두고 참조만 연결
- 부수 정정 2건: ① 패턴 수 70/71 → **81** ② E-1을 "분산 부족(한국어 발현: 장문 부재)"로 재framing

### R2 — **R2a(엔진) / R2b(패키징)로 분할** (실행 중 결정, 2026-09-02)

원안은 "영어 스킬 신설" 한 덩어리였으나, 그 안에서 매니페스트 3종·`install.sh`·
버전 승급이 차지하는 비중이 컸다. 동작과 무관한 배관이므로 엔진을 먼저 돌린다.

- **R2a — 엔진** (완료): `lang/en/` 데이터·지표 + shim `--lang` + 영어 룰북 +
  G3 역주입 게이트. 스킬 신설 없음. `core/metrics_universal` 의 첫 실사용처.
- **R2b — 패키징** (미착수): 스킬 디렉터리·매니페스트·`install.sh`·버전 승급.

#### R2a 실행에서 나온 근거 정정 2건

1. **Kobak 목록은 탐지 렉시콘이 아니다.** 407건 전수를 라우터에 쓰자 평범한 영어가
   heavy 로 갔다(`This is a plain sentence.` 반복 → 142.86/1k). 목록이 "2010–2021
   기준선 대비 **증가분**"이라 `this`·`across`·`between`·`however` 같은 초고빈도어를
   포함한다. 논문은 희귀·고비율(r)과 흔한·고격차(δ)를 구분하지만 공개 저장소에
   per-word r/δ 표가 없어 재현할 수 없다. → 논문이 명시 호명한 **12건만** 라우터에
   쓰고 나머지 395건은 룰북 자원으로 돌렸다. 실측 뒷받침: 전수 계수는 AI 에세이
   18·18 vs 사람 검수 문서 19·25 로 평평 — 문서 단위 판별력이 없다.
2. **밀도 지표에는 최소 분량이 필요하다.** 39토큰 영어 표본이 렉시콘 4건으로
   102.56/1k 를 내 heavy 로 튀었다. G3 의 "밀도 지표를 볼 때는 분모를 함께 본다"가
   라우터 자신에게 적용된 사례. `MIN_TOKENS_FOR_RATE=200` 가드를 넣었다.

또 하나: Kobak 논문의 핵심 주장("2024 초과 어휘의 66%가 동사")을 공개 원자료로
재계산해 **65.8%** 로 검증했다. 페치 요약이 아니라 1차 데이터 확인이다.

### (원안) R2 — 영어 스킬 신설 (ko 디렉터리 무수정)
- `skills/humanize-english/` 독립 스킬. **ko를 옮기지 않는다** — 두 번째 사례를 실제로 만들어봐야
  커널 경계가 상상이 아니라 실측으로 정해진다(D1-C 원칙 유지)
- baseline은 발표 수치 인용, Tier A+B 13~15규칙
- 게이트·청킹·재조립은 ko 스크립트 재사용(언어 무관 실증 완료)
- light/standard 경로만. heavy·finalize는 닫는다 — 증적을 주장할 근거가 아직 얕다

### R3 — 커널 추출 (경계가 실측된 뒤)
- ko·en에서 **실제로 중복된 것만** `core/`로 승격, `lang/{ko,en}` 구조로 이동
- 경로가 문서 20여 곳·`install.sh`·`.claude-plugin/`·`gemini-extension.json`·CI에 박혀 있으므로
  이 이동은 마지막에, 한 번에

### R4 (선택) — ko 역수입
- excess vocabulary 법으로 ko 어휘 채굴 파이프라인 교체.
  손으로 짓는 "2022 이전 인간 코퍼스" 의존을 끊는다

---

## 4. 열려 있는 결정

**D4. 영어 규칙을 몇 개로 출발할 것인가**
- (a) Tier A+B 13~15개 — 근거 강도 최우선. ko 81개 대비 커버리지 1/6
- (b) + Tier 2 유형론 근거분까지 ~40개 — `evidence: typological, en-unverified` 라벨
- (c) T2 48개 전부

**D5. 영어 스킬을 같은 리포에 둘 것인가**
프로젝트명이 "Humanize KR"이고 브랜드가 imnotai.kr이다.
- (a) 같은 리포 — 커널 공유가 쉽고 R3 이동이 자연스럽다. 이름·브랜드 정체성은 흐려진다
- (b) 별도 리포 — 정체성 보존. core 버전 스큐 비용

## 5. 참고

- Kobak et al. 2025, *Delving into LLM-assisted writing in biomedical publications through excess vocabulary*, Science Advances. arXiv:2406.07016 · 데이터 github.com/berenslab/llm-excess-vocab
- Reinhart et al. 2025, *Do LLMs write like humans? Variation in grammatical and rhetorical styles*, PNAS 122. arXiv:2410.16107
- Rudnicka & Juzek 2026, *Beyond "AI Language": The case for the idiolectal nature of LLM output*. arXiv:2608.06589
- SlopDetector 2026, *Is the Em Dash an AI Tell?* — 인간 702,939 words vs 6모델
