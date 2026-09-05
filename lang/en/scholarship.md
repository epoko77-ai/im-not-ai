# Humanize English — Scholarship Reference (v0.1)

> 영어 룰북(`quick-rules.md`)의 학술 인용 SSOT. 한국어 `scholarship.md` 의 대응물.
> 등급 정의는 `core/principles.md` 「근거 등급 (E1~E4)」.
>
> **한국어와의 비대칭**: 한국어는 학술이 없어 코퍼스를 직접 지어야 했다
> (`empirical-validation.md`: "통계적 유의성을 보고한 한국어 번역투 연구가 사실상 없다").
> 영어는 반대다 — 동료심사 발표가 풍부하고, 규칙을 발표 수치로 세울 수 있다.
> **이건 이식 손실이 아니라 이식 이득이다.**

---

## ⚠️ 정정 기록 — 이 문서가 실제로 잡아낸 것

**2026-09-03.** 룰북 v0.1 의 Tier A 7규칙 중 **3개가 방향이 반대**였음이 학술 확인
과정에서 드러났다. 원인은 두 가지가 겹쳤다.

1. **한국어에서 이식**했다 — 한국어 A-9(피동)·G-1/G-2(완곡)는 한국어 실측 근거가
   있지만, 그 방향이 영어에서도 같다는 보장이 없었다.
2. **PDF 페치 요약을 믿었다** — Reinhart et al. 2025 을 요약 도구로 읽었고, 그 요약이
   "passives: LLM 과다"라고 했다. **본문 확인 결과 정반대다.**

이것이 `core/principles.md` 의 E2 등급에 "**본문 표를 직접 확인했는지 별도 표기**"
단서를 단 이유이고, 그 단서가 실제로 발동한 첫 사례다.

| 규칙 | v0.1 처방 | 학술 실측 | 조치 |
|---|---|---|---|
| **A-9** 수동태 | "행위자를 주어로 올려라" | LLM 의 **agentless passive 는 인간의 절반** | **철회** — 손대지 않는다 |
| **G-1** 관측형 완곡 | "단언으로 바꿔라" | LLM 이 hedge 를 **유의하게 적게** 쓴다 | **반전** — 보호 대상 |
| **G-2** 이중 완곡 | "완곡 하나만 남겨라" | 위와 동일 | **반전** — 보호 대상 |

---

## 커뮤니티 축 — 영어권 사용자가 실제로 거슬려 하는 것

학술(서술적)만으로는 "사용자가 신경 쓰는가"를 못 잡는다. 반대로 커뮤니티만으로는
"방향이 맞는가"를 못 잡는다. **둘을 교차**한다. 후보 전수는
`lang/en/candidate-pool.md`.

주 수집원: [blader/humanizer](https://github.com/blader/humanizer) — **41,448★**(2026-08),
35패턴. 등급 **E3 상단**(비심사이나 집계 규모가 크다).

**교차 결과가 이 프로젝트의 존재 이유를 보여준다** — 41k★ 목록의 처방 3건이
동료심사 연구와 반대다:

| blader | 그들의 처방 | 학술 |
|---|---|---|
| #13 passive voice | 능동태로 바꿔라 | Reinhart 2025 PNAS: LLM 의 agentless passive 는 **인간의 절반** |
| #14 em/en dash | 최종본에 있으면 안 된다 | Gemini 3.53 · Llama 0.00 vs 인간 4.76 — **G1 미통과** |
| #24 qualifiers | 줄여라 | Jiang & Hyland · Mizumoto · Reinhart **3연구가 LLM 의 hedge 과소 사용에 수렴** |

우리 v0.1 도 같은 셋을 틀렸다(아래 「정정 기록」). 차이는 **학술 확인이 잡아냈다는 것**이다.

반대로 **양축이 일치하는 항목**은 근거가 가장 단단하다 — #3 현재분사절(= EN-1)이
41k★ 와 PNAS 양쪽에서 지목된다.

## Tier A — 규칙별 학술 앵커

### E-1. 문장 길이 분산 부족 — **유지, 처방 수정**

- **LLM 은 인간보다 문장이 길고, 변이는 작다.** Reinhart et al. 은 LLM 이 "longer and
  more complex sentences" 를 쓰고 information density 가 높다고 보고한다.
- 자체 스파이크 실측(E3): AI 에세이 문장길이 표준편차 6.7~6.8 vs 대조 16.3~18.8.
  교차모델(E3): haiku 6.41 · opus 8.39 · sonnet 9.91 — 체급이 낮을수록 균일.
- ⚠️ **처방 정정**: v0.1 은 한국어 E-1("장문 부재")을 그대로 옮겨 "35어 이상 장문을
  더하라"고 했다. **영어에서는 반대다** — LLM 문장은 이미 길다. 분산을 올리려면
  **짧은 문장을 넣어야 한다.**
- _source_anchor: Reinhart, Markey, Laudenbach, Pantusen, Yurko, Weinberg, Brown (2025),
  "Do LLMs write like humans? Variation in grammatical and rhetorical styles", PNAS 122,
  e2422455122 · arXiv:2410.16107 · **E2, 본문 표 미확인(저자 노트북·소속기관 보도 교차확인)**_

### F-4. 명사화 과다 — **유지, 근거 강함**

- **LLM 은 명사화를 인간의 1.5~2배**로 쓴다(Reinhart). 독립 재현: Mizumoto et al. 은
  ChatGPT 에세이가 "more nominalization" 을 보인다고 보고하고, Jiang & Hyland 는
  "noun/preposition-based bundles" 가 ChatGPT 에 더 흔하다고 한다.
- **3개 연구 독립 수렴** — 영어 룰북에서 근거가 가장 단단한 항목이다.
- 이론 토대: Biber 의 MDA 차원 1(informational vs involved production). 명사화·전치사구는
  informational 극의 핵심 지표다. LLM 이 "informationally dense, noun-heavy style" 로
  훈련됐다는 Reinhart 의 해석과 맞물린다.
- _source_anchor: Reinhart et al. 2025 PNAS; Mizumoto, Yasuda, Tamura (2024),
  "Identifying ChatGPT-generated texts in EFL students' writing", Applied Corpus Linguistics;
  Jiang & Hyland (2025), English for Specific Purposes 79: 17-29 · **E2 ×3**_

### EN-1. 현재분사절 과다 — **신규, 최대 효과**

- **LLM 은 present participial clause 를 인간의 2~5배**로 쓴다. Reinhart et al. 이
  보고한 **가장 큰 차이 중 하나**다.
- 예: "…, gathering clauses as it goes", "…, highlighting the need for…",
  "…, reflecting a broader shift".
- 처방: 종속절·독립문으로 푼다. `X, reflecting Y` → `X. That reflects Y.` /
  `X, which reflects Y`. **내용을 추가하지 않는다.**
- ⚠️ v0.1 룰북에 **없었다.** 최대 효과 항목을 빠뜨렸다. 한국어 대응물이 없어
  영어 고유 ID(`EN-*`)를 새로 부여한다.
- **커뮤니티 축 일치**: blader/humanizer #3 "Shallow analysis with -ing phrases"
  (41k★) — `highlighting`·`underscoring`·`reflecting`·`showcasing` 을 같은 이유로 지목한다.
  **학술·커뮤니티가 모두 강한 유일한 항목**이다.
- **자체 실측(E1)**: arXiv 대조군에서 AUC **0.726** — 인간 42편의 **중앙값 0.00**
  (절반 이상이 0건) vs AI 10.26/1k. **E1+E2+E3 삼중 근거로 룰북 최강 항목이다.**
- ⚠️ **탐지는 프레임으로 한다.** 초판 정규식이 동사 목록(`highlight`·`underscor`·
  `reflect`…)이었고 인간·AI 모두 0.00 이 나왔다 — 그 목록은 블로그 장르의 분사이고
  학술 초록은 `spanning`·`suggesting`·`showing` 을 쓴다. 프레임(`, VERB-ing`)으로
  바꾸자 0.605 → 0.726. C-8 에 이어 같은 실패를 반복했다.
- _source_anchor: Reinhart et al. 2025 PNAS · **E2** + blader/humanizer #3 · **E3(41k★)**
  + 자체 실측 · **E1**_

### EN-2. be동사 회피 — **신규, 자체 실측 승격**

- **AI 는 `is/are/was/were` 를 인간의 절반만 쓴다** — 자체 실측 인간 19.31 vs AI
  10.15/1k, AUC 0.238(|0.5차| 0.262).
- 대신 무거운 동사·명사구가 들어간다: `X constitutes a violation` · `Y represents an
  improvement`. **F-4 명사화와 같은 현상의 다른 측면**이고 편집도 같다 —
  `X is a violation` 으로 되돌린다.
- 결핍 신호지만 **처방 가능하다**. 없는 내용을 만드는 게 아니라 이미 있는 구문을
  단순화하는 편집이기 때문이다(`core/principles.md` 결핍 신호 정책의 예외 조건).
- _source_anchor: 자체 실측(arXiv 대조군) · **E1** + blader/humanizer #8 · **E3(41k★)**_

### F-7. 범용 동사·초과 어휘 — **유지, 원자료 확인**

- Kobak et al. 은 PubMed 초록 15M편(2010–2024)에서 excess vocabulary 를 채굴했고,
  **2024 초과 어휘의 66% 가 동사**다(delve·underscore·showcase). 공개 원자료
  `results/excess_words.csv` 를 직접 재계산해 **65.8%** 로 검증했다.
- Reinhart 계열은 어휘 편향을 다른 각도로 재현한다 — ChatGPT 가 `camaraderie`·`tapestry`
  를 인간의 **약 150배**, Llama 가 `unease` 를 **60~100배**, 양쪽이 `palpable`·`intricate`
  선호.
- ⚠️ **자체 실측 반증(E3)**: 현세대 Claude 출력 20편에서 라우터 렉시콘 **0건**,
  전수 407건으로도 12.6~33.5/1k 이며 **모델 체급을 탄다**(haiku 33.5 > opus 18.5 >
  sonnet 12.6). Kobak 코퍼스는 2024년까지이고 생의학 초록이다. **이 층은 최신 대형
  모델에서 상당 부분 사라졌다** — 규칙은 유지하되 발화 기대치를 낮게 잡는다.
- _source_anchor: Kobak, Márquez, Horvát, Lause (2025), "Delving into LLM-assisted writing
  in biomedical publications through excess vocabulary", Science Advances ·
  arXiv:2406.07016 · 데이터 github.com/berenslab/llm-excess-vocab ·
  **E2, 원자료 직접 확인**_

### C-8. Antithesis 대구 — **등급 하향**

- 한국어에서는 최강 신호다 — 12.1배, 전 모델, 과업 무관(E1).
- **영어 학술 근거는 없다.** 블로그·해설이 "not just X, but Y" 를 LLM hallmark 로
  지목하지만 계량 연구를 찾지 못했다. 구문복잡도 연구가 ChatGPT 의 coordination
  구조 선호·병렬 구문 의존을 보고하는 것이 가장 가까운 간접 근거다.
- ⚠️ **아이러니**: 이 프로젝트가 "영어 최강 신호"로 밀어온 항목이 영어 근거가 가장 약하다.
  한국어 E1 의 이식이지 영어 실측이 아니다.
- **커뮤니티 축은 강하다**: blader #9 "Not X but Y and clipped negative endings"(41k★).
  계량 근거는 여전히 없으나 영어권 사용자가 실제로 거슬려 한다는 증거는 있다.
  E3 이하 단독 승격 금지는 유지하되, **C+A 결합 재평가 대상**으로 둔다.
- _source_anchor: 한국어 `empirical-validation.md` C-8 이식 + blader/humanizer #9 ·
  **E3 ×2(영어 계량 미검증)**_

---

## 결핍 신호 — LLM 이 **적게** 쓰는 것

여기가 v0.1 이 통째로 놓친 축이다. 그리고 **일부는 제거하면 안 되는 것을 제거하고 있었다.**

### 완곡·서법 (hedges · boosters · modals) — **보호 대상**

**3개 연구가 독립적으로 수렴한다.**

| 출처 | 발견 |
|---|---|
| Jiang & Hyland 2025 (ESP 79:17-29) | ChatGPT 에세이가 hedges·boosters·attitude markers 등 **interactional metadiscourse 를 유의하게 적게** 쓴다. 결과적으로 impersonal·expository 한 톤 |
| Mizumoto et al. 2024 (Applied Corpus Linguistics) | **인간** 에세이가 modals·epistemic markers·discourse markers 를 **더 많이** 쓴다 |
| Reinhart et al. 2025 (PNAS) | 같은 방향(hedges/downtoners) |

→ **`may`·`might`·`appears to`·`tends to`·`arguably` 를 제거하면 글이 더 AI처럼 된다.**
그리고 학술·논증 텍스트에서는 **주장의 강도를 바꾸는 내용 변경**이기도 하다(철칙 #1).

이론 토대: Hyland 의 metadiscourse 프레임(interactive vs interactional). hedging 은
학술 영어의 **규범**이지 군더더기가 아니다.

_source_anchor: Jiang & Hyland 2025 ESP 79: 17-29; Mizumoto et al. 2024;
Reinhart et al. 2025 PNAS · **E2 ×3**_

### Agentless passive — **손대지 않는다**

- **LLM 은 agentless passive 를 인간의 절반**만 쓴다(Reinhart et al.).
- 따라서 "행위자를 주어로 올려라"는 처방은 글을 AI 쪽으로 민다.
- 다만 "수동태를 늘려라"도 하지 않는다 — 결핍 신호 정책상 **처방 불가, 관측 전용**이다
  (`core/principles.md` 「결핍 신호 정책」).

_source_anchor: Reinhart et al. 2025 PNAS · **E2**_

### 1·2인칭 대명사 · contraction · discourse marker

- LLM 이 personal reference 를 적게 쓴다(Goulart et al., Reinhart 경유).
- contraction 과소 사용 — 원문의 contraction 을 펴면 티가 늘어난다(철칙 #5).
- **관측 전용.** 없는 인칭을 심으면 문체가 아니라 화자가 바뀐다.

---

## 게이트 검증 — 내용 게이트 2종 (2026-09-04)

hedge 보호는 위 세 연구가 방향을 주지만 **룰북 문장은 그것을 강제하지 못한다.**
"건드리지 마라"는 지시일 뿐이고, 실행자가 어겨도 문체 게이트 셋(변경률·역주입·
과소윤문)은 전부 통과시킨다. 그래서 결정적 게이트로 옮겼다 — `core/modality_loss.py`.
같은 이유로 수치·인용·전거를 지키는 `core/content_preservation.py` 를 함께 만들었다.

**설계 결정 두 개는 한국어에서 검증된 것을 그대로 가져왔다.**

- **수치는 주입만 FAIL, 소실은 advisory.** 문장 병합에서도 수치는 사라지므로
  소실을 게이트하면 양치기 소년이 된다(`scripts/checks.py`).
- **서법은 총수가 아니라 문장쌍으로 본다.** 총수는 오검출과 실손실이 상쇄돼
  진짜 위반을 가린다(한국어 P5 실측).

**한국어에서 가져오지 않은 것**: 발화 인용 분류기. 영어는 강조·용어 언급에도
큰따옴표를 쓴다(`the so-called "alignment problem"`). 대신 따옴표가 아니라
**그 안의 글자가 남았는지**를 본다 — 따옴표를 벗기는 편집은 통과하고 내용 삭제만 잡힌다.

### 실측 (E1 — 자체 코퍼스)

| 검증 | 결과 |
|---|---|
| 실제 영어 윤문 4쌍(arXiv 초록, 규칙 겨냥 윤문) | 오탐 **0/4** (양 게이트) |
| 코퍼스 104편 × 문장 전면 병합 | 오탐 **0** |
| 코퍼스 104편 × 접속사 분할 | 오탐 **0** |
| 표지 1개 삭제 주입 (hedge·deontic 무작위) | 탐지 **85/85** |

**분할 흡수는 실측이 강제한 설계다.** 초판은 `Results indicate that X, though Y.`
→ `Results indicate that X. Y.` 를 서법 소실로 오판했다(총수는 1→1 불변).
정렬이 원문 문장을 뒤쪽 조각에 붙이고 앞 조각을 삽입으로 남긴 탓이다. 인접 삽입
문장까지 창에 넣어 세도록 고쳤다. 한국어 복원기의 `split_gap` 과 같은 문제다.

**건수 기준도 실측이 강제했다.** 존재 여부로 보면 `may indicate` → `indicate` 를
놓친다(같은 부류 표지가 하나 남는다). 건수라서 `may` → `might` 등가 치환은 통과한다.

---

## 블로그 셀 2회차 — 음성 결과의 원인 규명 (2026-09-04)

1회차 blog 셀(HN 댓글)은 **판별 실패**였고, 그 셀의 caveat 은 원인을 열어 뒀다:
"HN 댓글은 대화체·단편적이고 인용/코드가 섞인다. 다듬어진 칼럼·블로그 에세이와는
다른 레지스터라, 이 음성 결과가 그쪽까지 확장되는지는 미검증."

**그 caveat 을 닫았다.** 인간 쪽만 다듬어진 장문 에세이로 바꾸고(LessWrong
2016~2021, 다저자 42편, 인용·코드 블록 제거 후 첫 300단어) 나머지 설계는 초록 셀과
동일하게 뒀다 — 같은 제목 생성(G2), 같은 오염 방어, 같은 지표.

### 결과: 재현. 레지스터가 원인이 아니었다

| | 1회차 (HN 댓글) | 2회차 (에세이) |
|---|---|---|
| 인간 n / AI n | 48 / 20 | 42 / 42 (3모델 균등) |
| 최대 \|AUC−0.5\| | 0.192 | 0.188 |
| 판정 | 판별 실패 | **판별 실패 (재현)** |

### 2회차가 준 더 나은 진단: 모델 방향이 갈린다

묶은 AUC 만 보면 "신호 없음"이지만, 모델별로 가르면 **부호가 반대인 모델끼리
상쇄된 것**이었다.

| 지표 | opus | sonnet | haiku | 방향 일치 |
|---|---|---|---|---|
| en2_be_verbs | 0.736 | 0.422 | 0.162 | ❌ |
| comma_usage_rate | 0.349 | 0.724 | 0.382 | ❌ |
| comma_inclusion_rate | 0.180 | 0.543 | 0.292 | ❌ |
| sentence_length_dispersion | 0.399 | 0.466 | 0.071 | ✅ (전부 AI 가 균일) |
| comma_segment_length | 0.446 | 0.394 | 0.290 | ✅ |
| **en1_participial** | 0.525 | 0.624 | 0.685 | ✅ (전부 AI 가 많음) |

**초록 셀의 최강 신호(쉼표 계열·EN-2)가 이 장르에서는 모델 개인어다** — G1 미통과.
방향이 살아남는 셋도 크기가 작아 규칙 임계로 쓸 수 없다. EN-1 만 두 장르에서
방향이 같다(초록 0.787 · 에세이 0.611).

### 라우터 실사용 판정 — 지표 AUC 보다 이 숫자가 중요하다

| | light | standard | heavy | 분리도 |
|---|---|---|---|---|
| 인간 에세이 | 12% | 62% | 26% | — |
| AI (코칭 프롬프트) | 0% | 55% | 45% | **0.31** |
| AI (맨 프롬프트) | 14% | 86% | 0% | **−0.28** |

초록 셀의 분리도는 0.95 였다. 에세이에서는 0.31 로 떨어지고, **맨 프롬프트에서는
부호가 뒤집힌다** — 라우터가 AI 글을 인간 글보다 더 "사람스럽다"고 판정한다.
인간 에세이의 **26% 를 heavy 로 오탐**한다.

맨 프롬프트 대조군은 "분량·형식을 지정한 코칭이 AI 티를 눌렀다"는 반론을 겨냥한
것이다. 눌린 게 아니었다 — 맨 프롬프트에서 EN-1 은 오히려 0.355(인간이 더 많음)로
내려간다.

### 조치

- `skills/humanize-english/SKILL.md` — 초록류가 아닌 입력에서는 `light` 를 채택하지
  않고 standard 로 올린다. `route_hint` 를 근거로 제시하지 않는다.
- `lang/en/quick-rules.md` — 장르 한계 경고를 2회차 결과로 갱신.
- 재현: `python3 scripts/build_en_blog_cell.py --fetch-human 42 --gen-ai 14
  --gen-bare 14 --report`

---

## 블로그 셀 3회차(R2) — 신호를 찾았다 (2026-09-04)

2회차까지의 결론은 "블로그는 판별 실패"였다. 그런데 부트스트랩 CI 를 내보니
**6지표 중 4개는 '무효과'가 아니라 '표본 부족'**이었다(분산 0.312, CI [0.202, 0.423]).
음성 결과를 확정하기 전에 네 방향으로 강화한 재실험이 R2 다.

| | 2회차 | R2 |
|---|---|---|
| 인간 | LessWrong 42 (단일 커뮤니티) | **100 — LW 40 · Paul Graham 30 · SSC 30** |
| AI | 42, "prose only, no headings" 코칭 | **102, 실사용자 프롬프트**("engaging blog post", 700단어, 형식 무지정) |
| 발췌 | 도입부 300단어 | **본문 중간 200~500단어** (도입부는 인간도 정형적이다) |
| 지표 | 통사 표면 6 | **16 — 유예됐던 담화층 후보 7 + 탐색 3 추가** |
| 판정 | 점추정 AUC | **AUC + 부트스트랩 CI + 모델별 방향(G1)** |

### 결과

| 지표 | 인간 | AI | AUC | 95% CI | 모델 일치 | 판정 |
|---|---|---|---|---|---|---|
| comma_segment_length | 9.68 | 8.34 | 0.281 | [0.215, 0.355] | ✅ | **승격 후보** |
| **tricolon** (blader #10) | 0.00 | 1.67 | 0.681 | [0.621, 0.740] | ✅ | 기준 미달(0.181) |
| en1_participial | 0.00 | 0.00 | 0.587 | [0.522, 0.651] | ✅ | 약함 |
| dispersion · comma_inclusion · en2 | | | 0.35~0.40 | | ❌ | 모델 개인어 |
| filler · vague_source · range · deeper_truth · closing · hype | 0.00 | 0.00 | ~0.50 | | | **미출현** |

**담화층 가설은 절반만 맞았다.** 유예됐던 blader 후보 7건 중 **여섯은 Claude
블로그 산문에 아예 나오지 않는다**(중앙값 0.00/0.00). 그 목록은 GPT 세대 슬롭을
보고 만들어졌고, 우리 AI 팔은 Claude 전용이다 — **후보 목록에 모델 세대 편향이
있다**는 뜻이지 패턴이 없다는 뜻이 아니다. 반면 **tricolon 하나는 크게 살아났다.**

### 승격 기준이 덜 강건한 쪽을 골랐다 — 기록해 둔다

| | 모델별 AUC | 인간 출처별 AUC |
|---|---|---|
| comma_segment_length (승격 후보) | 0.201 · 0.408 · 0.233 | 0.203 ~ 0.356 |
| **tricolon** (기준 미달) | 0.655 · 0.681 · 0.704 | 0.654 ~ 0.737 |

묶은 |AUC−0.5| ≥ 0.20 기준은 **덜 강건한 지표를 통과시키고 더 강건한 지표를
탈락시켰다.** tricolon 은 3모델·3출처 전부에서 좁은 범위에 모이고 인간 중앙값이
세 출처 모두 0.00 인데, 크기가 0.181 로 0.19 모자란다. 정규식을 네 변형으로
다시 짜 봐도 최대 0.685 였다(2회차 코퍼스에서도 동일) — **가공으로 넘길 수 있는
차이가 아니다.** 기준을 사후에 바꿔 통과시키지 않는다. 대신 **기준에
'모델·출처 최소값' 축을 추가하는 안**을 남긴다.

### 라우터 — 장르 보정만으로 분리도 0.29 → 0.65

지표 하나하나는 약해도 장르에 맞게 보정한 신호 3개를 합치면 라우터가 선다.

| 라우터 | 인간(light/std/heavy) | AI | 분리도 |
|---|---|---|---|
| 현행(초록 임계) | 21 / 58 / 21 | 4 / 63 / 33 | **0.29** |
| 블로그 보정 3신호 | 56 / 28 / 16 | 22 / 31 / 47 | **0.65** |

규칙: `comma_segment < 8.57`(인간 하위 25%) · `tricolon > 0` · `en1 > 0` —
2개 이상 heavy, 1개 standard, 0개 light. 초록 임계(10.82)를 그대로 쓰면 인간
중앙값 9.68 이 통째로 AI 쪽에 떨어져 라우터가 죽는다. **임계가 장르에 종속된다.**

과적합 점검 두 가지:
- **모델별** 0.58 · 0.60 · 0.78 — 3모델 전부에서 선다.
- **인간 출처 홀드아웃**(한 출처로 임계를 잡아 다른 출처에 적용) 0.53 · 0.68 · 0.74.
- 2회차 코퍼스(다른 프롬프트·다른 발췌 위치, AI 팔 완전 독립)에 적용해도 **0.65**.

초록 셀의 0.95 에는 못 미친다. 그러나 **블로그에 라우터가 없던 상태에서 서는
라우터가 생겼다.**

### 모델 계열 교차 — GPT 에서 더 강하다 (2026-09-05)

R2 까지 AI 팔은 Claude 3모델뿐이었다. "AI 티"인지 "Claude 개인어"인지 가르려면
계열을 건너뛰어야 한다 — G1 의 원래 취지다. 같은 제목·같은 프롬프트로 codex CLI
(OpenAI GPT)에서 34편을 뽑아 같은 인간 코퍼스에 붙였다.

| 지표 | 인간 | Claude | GPT | AUC(Claude) | **AUC(GPT)** |
|---|---|---|---|---|---|
| tricolon | 0.0 | 1.67 | **6.67** | 0.681 | **0.903** |
| comma_segment_length | 9.68 | 8.34 | **6.82** | 0.281 | **0.054** |
| sentence_length_dispersion | 9.86 | 8.26 | **5.68** | 0.349 | **0.065** |
| en1_participial | 0.0 | 0.0 | **3.33** | 0.587 | **0.675** |

**세 신호 전부 GPT 에서 더 강하다.** 라우터 분리도는 Claude 0.65 → **GPT 1.37**
(인간 대비 heavy 93% · light 0%). 블로그 신호는 Claude 개인어가 아니라 모델
계열을 건너뛰는 AI 티다. 방향으로 보면 오히려 **Claude 가 인간에 더 가깝고**,
우리 신호는 GPT 산문에서 가장 잘 듣는다. blader·Kobak 목록이 GPT 세대를 보고
만들어졌다는 점과도 맞는다.

n=34(Claude 팔과 같은 제목), 단일 모델(codex CLI 기본값)이다. Gemini·Llama 는 여전히 미검증.

### 남은 한계

- 승격은 **둘**이다 — `comma_segment_length`(0.224)와 `tricolon`(0.737, EN-3 으로 룰북 편입).
  전자는 sonnet 에서 약하고(0.408), 후자는 4모델 2계열 전부에서 안정적이다(0.655~0.903).
- **분산은 승격하지 않았다.** 통합 AUC 0.278 로 크기 기준은 넘지만 sonnet 만 방향이
  반대라(0.552) G1 미통과다. 통합 수치만 봤으면 모델 개인어를 규칙으로 올릴 뻔했다.
- 인간 코퍼스 3출처가 전부 **영미 테크·합리주의 계열 장문 산문**이다. 마케팅
  블로그·기업 블로그·라이프스타일 글은 여전히 미검증.
- 재현: `python3 scripts/build_en_blog_r2.py --fetch-human 100 --gen-ai 34 --report`

---

## Caveat

**C1. 코퍼스 장르 불일치.** Kobak 은 생의학 초록, Jiang & Hyland 와 Mizumoto 는 학생
논증 에세이, Reinhart 는 여러 장르 혼합. 이 스킬의 주 사용처(칼럼·블로그·리포트)와
정확히 겹치지 않는다. **방향 근거이지 임계가 아니다.**

**C2. 본문 표 미확인.** Reinhart·Kobak·Jiang & Hyland 모두 초록·저자 노트북·소속기관
보도·검색 요약으로 확인했다. Kobak 만 공개 원자료를 직접 재계산했다. 나머지는
수치를 인용할 때 이 한계를 함께 적는다. **v0.1 의 A-9 오류가 정확히 이 지점에서 났다.**

**C3. 모델 세대 이동.** Kobak 은 2024년까지, Reinhart 는 GPT-4o·Llama 3, Jiang & Hyland
와 Mizumoto 는 ChatGPT(3.5/4 세대). 자체 실측(2026-09, Claude 계열)에서 어휘 층은
이미 크게 약해졌다. **어휘 규칙은 유효기간이 짧다고 가정한다.**

**C4. E1 이 한 장르에만 있다.** 자체 대조 코퍼스는 arXiv 초록뿐이다(`lang/en/baseline.json`).
블로그 셀은 **검증된 지표가 0개**다 — 잰 지표 전부 |AUC−0.5| < 0.20 이었다. 초록에서
나온 임계를 칼럼·블로그에 그대로 쓸 근거가 없다. `core/principles.md` E3 조항에 따라
**영어 임계는 전부 잠정이며 heavy·finalize 경로를 열지 않는 근거**가 된다.

**C5. Biber·Hyland 원전 미확인.** MDA 차원과 metadiscourse 프레임은 2차 인용으로만
확인했다. 이론 토대로만 쓰고, 수치를 여기서 끌어오지 않는다.

---

## 참고 문헌

- Reinhart, A., Markey, B., Laudenbach, M., Pantusen, K., Yurko, R., Weinberg, G.,
  Brown, D. W. (2025). *Do LLMs write like humans? Variation in grammatical and
  rhetorical styles*. PNAS 122, e2422455122. arXiv:2410.16107.
  저자 노트북: refsmmat.com/notebooks/llm-style.html
- Kobak, D., Márquez, R. G., Horvát, E.-Á., Lause, J. (2025). *Delving into LLM-assisted
  writing in biomedical publications through excess vocabulary*. Science Advances.
  arXiv:2406.07016. 데이터: github.com/berenslab/llm-excess-vocab
- Jiang, F. (K.), Hyland, K. (2025). *Rhetorical distinctions: Comparing metadiscourse in
  essays by ChatGPT and students*. English for Specific Purposes 79: 17-29.
- Mizumoto, A., Yasuda, S., Tamura, Y. (2024). *Identifying ChatGPT-generated texts in
  EFL students' writing: Through comparative analysis of linguistic fingerprints*.
  Applied Corpus Linguistics.
- Rudnicka, K., Juzek, T. S. (2026). *Beyond "AI Language": The case for the idiolectal
  nature of LLM output*. arXiv:2608.06589. **E3 — 프리프린트.**
- SlopDetector (2026). *Is the Em Dash an AI Tell?* 인간 702,939 words vs 6모델.
  **E3 — 비심사, 인간 풀이 문학 고전.**
- Biber, D. (1988). *Variation across Speech and Writing*. **E4 — 2차 인용, 이론 토대.**
- Hyland, K. (2005). *Metadiscourse: Exploring Interaction in Writing*.
  **E4 — 2차 인용, 이론 토대.**
