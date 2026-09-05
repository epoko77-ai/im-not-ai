# English AI-Tell Candidate Pool (v0.1)

> 한국어의 「패턴 candidate 풀」(커밋 `5c0d00c`)에 대응하는 영어 후보 풀.
> **여기 있는 것은 아직 규칙이 아니다.** 승격 기준은 `core/principles.md` G1~G3 이고,
> 학술 앵커는 `lang/en/scholarship.md` 에 단다.

## 왜 이 목록인가

말씀의 출발점은 "**에이전트 문장이 어색하다**"는 영어권 사용자의 호소를 모으자는 것이었다.
그 호소가 가장 크게 집계된 곳이 **[blader/humanizer](https://github.com/blader/humanizer)**
(2026-08 기준 **41,448★**, `SKILL.md` 30KB, 35패턴)다. 별 4만 개는 "이게 AI 티다"라는
영어권의 집합적 동의이고, 우리 등급 체계로는 **커뮤니티 검증(E3)** 이다.

한국어 `empirical-validation.md` 는 이 목록을 **한국어로 직역해 검증했다가 1/35 만
생존**시켰다. 그건 이식 실패 기록이지 목록의 부정이 아니다 — **영어 원산 자료이므로
영어에서는 1차 자료다.** 저장소가 그때 이 목록을 "실패"로만 분류해 둔 탓에 영어 작업에서
한참 늦게 꺼냈다.

## 평가 2축

이 프로젝트의 차별점은 "AI가 더 하는 것"이 아니라 **"근거가 있는 것"**이다. 그래서 두 축으로 본다.

- **커뮤니티(C)** — 영어권 사용자가 실제로 거슬려 하는가 (blader 41k★ 등)
- **학술(A)** — 동료심사 연구가 방향을 뒷받침하는가 (`scholarship.md`)

둘 다 있으면 승격 1순위. **C만 있고 A가 반대면 채택하지 않는다** — 그게 우리가
일반 humanizer와 갈리는 지점이다.

---

## ⚠️ 충돌 3건 — 41k★ 목록이 동료심사 연구와 반대

**이것이 이 프로젝트의 존재 이유를 가장 잘 보여주는 자료다.**

| blader | 그들의 처방 | 학술 근거 | 우리 판정 |
|---|---|---|---|
| **#13** Passive voice and missing subjects | "능동태를 써서 행위자를 드러내라" | Reinhart et al. 2025 **PNAS**: LLM 의 **agentless passive 는 인간의 절반** | **채택 안 함.** 이 처방은 글을 AI 쪽으로 민다 |
| **#14** Em and en dashes | "최종 산출에 em dash 가 **있으면 안 된다**"(강한 금지) | SlopDetector 2026: Gemini 2.5 Pro 3.53 · Llama 3.1 8B **0.00** vs 인간 4.76/1k | **G1 미통과.** 모델 개인어이지 AI다움이 아니다. 관측만 |
| **#24** Too many qualifiers | "qualifier 를 줄여라" | Jiang & Hyland 2025 ESP · Mizumoto et al. 2024 · Reinhart 2025 — **3연구가 LLM 의 hedge 과소 사용에 수렴** | **반전. 보호 대상.** 제거하면 더 AI처럼 되고, 논증문에서는 주장 강도를 바꾼다 |

우리도 v0.1 에서 이 셋을 **똑같이 틀렸다**(`scholarship.md` 「정정 기록」). 차이는
**학술 확인이 잡아냈다는 것**이고, 그게 근거 기반 설계의 값어치다.

## ✅ 독립 확인 3건 — 커뮤니티와 학술이 같은 것을 지목

| blader | 우리 ID | 학술 |
|---|---|---|
| **#3** Shallow analysis with -ing phrases (`highlighting`·`underscoring`·`reflecting`·`showcasing`) | **EN-1** | Reinhart 2025: present participial clause **인간의 2~5배**, 보고된 최대 차이 중 하나 |
| **#9** Not X but Y | **C-8** | 영어 계량 연구 없음 — 그러나 **41k★ 커뮤니티 검증이 붙는다** |
| **#7** Overused AI words | **F-7** | Kobak 2025 Science Advances (초과 어휘 65.8% 동사) |

**#3 은 이 룰북에서 유일하게 커뮤니티·학술이 모두 강한 항목이다.** Tier A 최상단에 둘 근거가 된다.
**#9(C-8)은 등급을 재고할 수 있다** — `scholarship.md` 에서 "영어 근거 없음"으로 E3 강등했는데,
커뮤니티 축이 강하다. E3 이하 단독 승격 금지 원칙은 유지하되, C+A 결합 근거로 재평가 대상이다.

---

## 심사 1회차 결과 (2026-09-03) — `scripts/screen_en_candidates.py`

기존 arXiv 대조군(인간 42 · AI 21, 같은 제목)으로 정규식 계측 가능한 11건을 심사했다.
**신규 수집 0** — 이미 있는 코퍼스를 다시 잰 것뿐이다.

| 후보 | 인간 | AI | AUC | 판정 |
|---|---|---|---|---|
| **EN-1** 현재분사절(`, VERB-ing`) | 0.00 | 10.26 | **0.726** | **승격** — 인간 절반 이상이 0건 |
| **#8** be동사 회피 | 19.31 | 10.15 | **0.238** | **승격 → EN-2.** AI 가 절반만 쓴다 |
| #26 hyphenated pairs | 22.66 | 22.83 | 0.562 | 기각 |
| #11 repeated openings | 19.09 | 22.22 | 0.507 | 기각 |
| #5 · #12 · #23 · #25 · #27 · #31 · #32 | 0.00 | 0.00 | ~0.50 | **판정 불가(장르)** |

**판정 불가 7건이 중요하다.** 인간·AI 모두 0.00 이라는 건 패턴이 없다는 게 아니라
**학술 초록에 그 장르의 패턴이 없다**는 뜻이다 — filler·formulaic saying·generic
positive ending 은 블로그·마케팅 산문의 것이다. 기각이 아니라 **칼럼 코퍼스가
생기면 재심사**한다. 이게 칼럼 셀이 필요한 가장 구체적인 이유다.

## 심사 2회차 (2026-09-04) — 블로그 코퍼스로 유예분 재심사

R2 블로그 코퍼스(인간 100편 3출처 · AI 102편 3모델)로 위 유예 7건을 처음 쟀다.

| 후보 | 인간 중앙 | AI 중앙 | AUC | 판정 |
|---|---|---|---|---|
| **#10 tricolon** (3항 등위) | 0.00 | 1.67 | **0.737** | **EN-3 으로 승격** — Claude 단독 0.681 로 0.019 미달이었으나, GPT 34편을 더해 0.737(CI [0.683, 0.789]). 4모델 2계열 전부 같은 방향(0.655~0.903) · 인간 3출처 전부(0.713~0.786) |
| #23 filler · #5 vague sources · #12 false ranges · #25 generic endings · #27 deeper truth · #1·#4 hype | 0.00 | 0.00 | ~0.50 | **Claude 산문에 미출현** |

**미출현 6건의 해석에 주의.** blader 목록은 GPT 세대 슬롭을 보고 만들어졌고 우리
AI 팔은 Claude 3모델뿐이다. "패턴이 없다"가 아니라 **후보 목록에 모델 세대 편향이
있다**는 뜻이다. GPT·Gemini 팔이 생기면 재심사 대상이다.

#25 결말 공식은 초판 계측이 **원리적으로 불가능**했다 — 발췌 구간에 글의 끝이
없었다. R2 에서 마지막 60단어를 따로 실어 고쳤고, 그러고도 0.505 였다.

### ⚠️ 심사가 잡아낸 우리 오류 (3번째 같은 실패)

EN-1 초판 정규식이 **인간·AI 모두 0.00** 이었다. 동사 목록
(`highlight`·`underscor`·`reflect`…)을 박았는데 그건 **블로그 장르의 분사**이고,
학술 초록은 `spanning`·`suggesting`·`showing`·`tracking` 을 쓴다.
**통사 프레임(`, VERB-ing`)으로 바꾸자 AUC 0.605 → 0.726.**

C-8 첫 정규식(재현율 0/6), 렉시콘 전수 오발화에 이어 **세 번째로 같은 실패**다:
표면 예시를 인코딩하고 프레임을 놓쳤다. 영어 규칙을 쓸 때의 상시 위험으로 기록한다.

## 후보 전수 (35건) — 우리 상태 대조

| # | blader 패턴 | 우리 상태 |
|---|---|---|
| 1 | Inflated claims about importance and legacy | 후보 — ko D-2(의의 과장) 대응 |
| 2 | Name-dropping to prove importance | 후보 — ko 대응 없음, **영어 고유** |
| 3 | Shallow analysis with -ing phrases | **EN-1 채택** — E1+E2+E3 삼중, 룰북 최강 |
| 4 | Sales language | 후보 — ko D-4(hype) 대응 |
| 5 | Vague sources (`studies show`·`experts say`) | 후보 — ko **I-7 무주체 판정** 대응 |
| 6 | Formulaic challenges and outlook sections | 후보 — ko **D-12**. EN↔KO **양방향 생존 유일** |
| 7 | Overused AI words | **F-7 채택** |
| 8 | Avoiding is and are | **EN-2 채택** — 자체 실측 AUC 0.238(AI 가 절반만 씀) |
| 9 | Not X but Y and clipped negative endings | **C-8 채택** (등급 재고 대상) |
| 10 | Forced groups of three (tricolon) | **EN-3 채택** — 블로그 셀 자체 실측 AUC 0.737, 4모델 2계열 생존 |
| 11 | Changing names and repeating sentence openings | 후보 — **영어 고유**. E-1 분산의 어휘판 |
| 12 | False from X to Y ranges | 후보 — ko **D-7 변환 공식** 대응 |
| 13 | Passive voice and missing subjects | ❌ **채택 안 함** (학술 반대) |
| 14 | Em and en dashes | ❌ **G1 미통과**, 관측 전용 |
| 15 | Too much bold text | 후보 — Tier B 계열 |
| 16 | Lists with bold mini-headings | 후보 — Tier B 계열 |
| 17 | Title case in headings | 후보 — **영어 고유**(한국어에 대소문자 없음) |
| 18 | Emojis | **C-5 채택** |
| 19 | Curly quotation marks | 후보 — **영어 고유**. `sanitize_text.py` 영역일 수도 |
| 20 | Chatbot text left in the answer | 후보 — ko **챗봇 잔재 위생** 대응(SKILL.md Phase 1) |
| 21 | Knowledge-limit disclaimers | 후보 — 위와 같은 계열 |
| 22 | Overly agreeable tone | 후보 — **영어 고유**, 미검증 |
| 23 | Filler phrases | 후보 |
| 24 | Too many qualifiers | ❌ **반전 — 보호 대상** (학술 3연구 반대) |
| 25 | Generic positive endings | 후보 — ko **D-6 결말 공식** 대응 |
| 26 | Too many hyphenated word pairs | 후보 — **영어 고유** |
| 27 | Pretending to reveal a deeper truth | 후보 — ko 검증서 "격차 없음"으로 기각된 항목(§27). **영어에서는 미검증** |
| 28 | Announcing the next point | 후보 — ko C-6(요약 박스) 인접 |
| 29 | A heading repeated in the first sentence | 후보 — ko C-6 인접 |
| 30 | Writing about the previous version | 후보 — 편집 맥락 특화 |
| 31 | Forced punchlines and dramatic fragments | 후보 — ko D-13(성찰 부사) 인접 |
| 32 | Formulaic sayings | 후보 — ko D 관용구 계열 |
| 33 | Fake-candid openings | 후보 — ko 검증서에서 **정반대**(솔직히 = 사람 표지). **영어에서는 미검증** |
| 34 | Answering objections no one raised | 후보 — ko §34 무출현으로 기각. **영어에서는 미검증** |
| 35 | Rejecting fake alternatives | 후보 — ko 미검증 |

## 집계

- **채택 완료**: 6 (#3=EN-1 · #7 · #8=EN-2 · #9 · #10=EN-3 · #18)
- **채택 거부 (학술 반대)**: 3 (#13 · #14 · #24)
- **후보 대기**: 27 — 그중 **7건은 장르 탓 판정 불가**(칼럼 코퍼스 대기)
- 영어 고유(한국어 대응 없음): 6 (#2 · #11 · #17 · #19 · #22 · #26) — #8 은 채택됨

## 승격 절차

1. 커뮤니티 축은 이미 있다(41k★). **학술 축을 찾는다** — 없으면 승격하지 않고 후보로 둔다.
2. 학술이 없고 자체 실측만 가능하면 `scripts/build_en_baseline.py` 로 arXiv 대조군에 돌린다.
3. G1(전 모델 생존)·G2(과업 통제)를 통과해야 규칙이 된다.
4. 승격 시 `lang/en/quick-rules.md` 에 행을 추가하고 `scholarship.md` 에 앵커를 단다.

## 다른 수집원 (미착수)

- Reddit r/ChatGPT · r/writing — "AI writing feels off" 스레드
- Hacker News — LLM 산문 비판 토론
- 편집·교열 실무자 블로그
- 다른 humanizer 도구의 규칙 목록

**수집원마다 등급이 다르다.** 41k★ 는 집계 규모가 커서 E3 상단이고, 개별 블로그 글은
E4 에 가깝다. 수집할 때 출처와 규모를 함께 기록한다.
