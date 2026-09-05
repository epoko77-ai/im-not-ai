# English AI-Tell Rulebook (quick-rules, v0.2)

> **v0.2 정정 (2026-09-03).** Tier A 7규칙 중 **3개(A-9·G-1·G-2)가 방향이 반대**였다.
> 한국어에서 이식하고 PDF 페치 요약을 믿은 결과이며, 학술 원문 확인에서 드러났다.
> 셋은 「건드리면 안 되는 것」으로 옮겼고, 누락돼 있던 최대 효과 항목(PPC 현재분사절
> 2~5배)을 추가했다. 전말: `${SKILL_ROOT}/lang/en/scholarship.md` 「정정 기록」.
>
> ⚠️ **장르 한계 (2026-09-04 갱신 · 두 번 실측).** 이 룰북의 임계와 승격 근거는
> **학술 초록 장르에서만 검증됐다.** 블로그 셀은 두 번 실패했다.
> ① HN 댓글(인간 48 vs AI 20) — 전 지표 |0.5차| < 0.20, 최대 0.192.
> ② **다듬어진 장문 에세이**(LessWrong 2016~2021, 인간 42 vs AI 42, 3모델) — 재현.
> 최대 0.188. ②는 ①의 "댓글이라 그런 것 아니냐"를 겨냥한 대조였고, **레지스터가
> 원인이 아니었다.**
>
> ③ **R2**(인간 100편 3출처 · AI 136편 4모델 2계열 · 실사용자 프롬프트 ·
> 본문 중간 발췌 · 지표 16종 · CI 판정) — **여기서 신호가 나왔다.**
>
> R2 결론 넷:
> 1. **임계가 장르에 종속된다.** 초록 임계(쉼표 절 < 10.82)를 블로그에 쓰면 인간
>    중앙값 9.68 이 통째로 AI 쪽에 떨어진다. 장르 보정만으로 라우터 분리도가
>    **0.29 → 0.65** 로 오른다(모델별 0.58~0.78, 출처 홀드아웃 0.53~0.74).
> 2. **tricolon 을 EN-3 으로 승격했다.** Claude 3모델만으로는 AUC 0.681 로 기준에
>    0.019 모자랐는데, GPT 34편을 더하니 **0.737**(CI [0.683, 0.789])로 넘었다.
>    **기준을 낮춘 것이 아니라 표본을 넓힌 것이다.**
> 3. **분산은 승격하지 않았다.** 통합 AUC 0.278 로 기준은 넘지만 sonnet 만 방향이
>    반대여서(0.552) G1 미통과다. 통합 수치만 봤으면 모델 개인어를 규칙으로
>    올릴 뻔했다. 쉼표 포함률·EN-2 도 같은 이유로 관측 전용이다.
> 4. **GPT 산문에서 더 잘 선다** — 같은 신호로 분리도 1.37(Claude 0.65).
>    블로그 신호는 Claude 개인어가 아니다.
>
> **비형식 산문에서는 초록 임계를 근거 있는 것으로 여기지 말 것.**
> 상세: `lang/en/baseline.json` genres.blog / blog_essay / blog_essay_r2.
>
> **근거 상태 — 먼저 읽을 것.** E1(자체 대조 코퍼스 실측)이 붙은 규칙은
> **EN-1·EN-2·EN-3·C-12·C-12b·E-5 여섯**이고, 그 근거는 **학술 초록과 블로그
> 에세이 두 장르**에서 나왔다. 나머지는 한국어 실측 이식과 외부 발표(E2)·자체
> 스파이크(E3)다. 두 장르 밖은 미검증이므로 영어 경로는 **light/standard 만 열고
> heavy·finalize 는 닫는다** — 증적을 주장할 근거가 없는 것을 증적처럼 내놓지 않는다.
> 등급 정의: `core/principles.md` 「근거 등급 (E1~E4)」.
>
> **em dash 는 규칙이 아니라 관측 지표다.** G1(전 모델 생존) 미통과 —
> 인간 4.76/1k 에 대해 Gemini 2.5 Pro 3.53, Llama 3.1 8B 0.00 으로 인간 이하다
> (SlopDetector 2026, E3). 모델 개인어이지 "AI다움"이 아니다. 세되, 고치지 않는다.

## 철칙 (언어 무관 — `core/principles.md`)

1. **Fidelity First** — 사실·주장·수치·고유명사·인용은 100% 보존.
2. **Span-Grounded** — 탐지된 구간만 손댄다.
3. **Tone Match** — 장르를 옮기지 않는다.
4. **No Over-Polish** — 변경률 30% 경고 / 50% 중단. `scripts/verify_change_rate.py` 가 판정.
5. **Register 양방향 보존** — 원문보다 격식을 올리지도 내리지도 않는다. contraction 을 펴지 말 것(LLM 이 contraction 을 과소 사용한다 — Reinhart 2025).
6. **No New Tells** — 손대는 구간에 새 티를 심지 않는다.
   **실사고**: 스파이크 윤문이 장문 부재를 고치려 문장을 이어 붙이면서 접합부에
   em dash 를 3개 새로 심었다(2→5, 9.33/1k = 이 모델의 개인어 9.09/1k 와 일치).
   문장을 이을 때는 접속사·세미콜론·마침표를 쓰고 대시로 잇지 않는다.

---

## Tier A — 외부 근거 + 한국어 실측 양쪽

| ID | 트리거 | 처방 | 근거 |
|---|---|---|---|
| **C-8** | 대구·antithesis 반복. 프레임이 여러 개다: `not X but Y` · `it's not X, it's Y` · `neither X nor Y` · `less about X than Y` · `is not whether … but` · `rather than X, Y` · `not merely/simply/just X` | 문서당 1회까지 허용. 나머지는 **긍정형 단언**으로 편다: `It's not a decline, it's a redistribution` → `It is a redistribution` | **E3** — ko 12.1× 는 한국어 실측이고 **영어 계량 연구를 찾지 못했다.** 구문복잡도 연구의 coordination 편중이 간접 근거 |
| **F-7** | 범용 동사 수렴 — `delve` `underscore` `showcase` `leverage` `facilitate` `foster` `streamline` `highlight` `navigate` `harness` | 구체 동사로 교체하거나 문장을 재구성. `This underscores a shift` → `The numbers show a shift` / `Costs rose` | **E2** Kobak 2025 (초과 어휘 65.8%가 동사, 원자료 확인). ⚠️ **E3 반증**: 현세대 Claude 20편에서 라우터 렉시콘 0건 — 이 층은 대형 모델에서 상당 부분 사라졌다 |
| **C-12b** | **문장당 쉼표가 많다** — 인간 0.96, AI 1.67 | 삽입구·동격구를 덜어낸다. 내용은 그대로 | **E1** AUC 0.888 — **이 룰북 최강**. 교차언어 확인: 한국어 abstract 셀 1.39배 vs 영어 1.75배 |
| **E-5** | **쉼표 절이 짧다** — 인간 중앙값 12.5어, AI 9.05어 | 짧게 끊긴 절을 잇는다. **대시로 잇지 않는다(철칙 #6)** | **E1** AUC 0.149 (\|0.5차\| 0.351) — 이 룰북 최강 판별 지표 |
| **C-12** | **쉼표 포함률이 높다** — 인간 57.7%, AI 71.4% | 삽입구를 덜어낸다. 내용은 그대로 | **E1** AUC 0.719 (\|0.5차\| 0.219) |
| **EN-1** | **현재분사절 남발** — 통사 프레임 `, VERB-ing` 전체다. 동사 목록이 아니다 (`, spanning…` `, suggesting…` `, showing…` `, reflecting…` `, highlighting…`) | 종속절·독립문으로 푼다. `X, reflecting Y` → `X. That reflects Y.` / `X, which reflects Y`. **내용 추가 금지** | **E1+E2+E3 — 룰북 최강.** 자체 실측 AUC 0.726(인간 중앙값 **0.00** vs AI 10.26/1k) · Reinhart 2025 PNAS 인간의 2~5배 · blader #3(41k★) |
| **EN-2** | **be동사 회피** — `X constitutes a violation` · `Y represents an improvement` 처럼 `is/are` 자리에 무거운 동사·명사구를 놓는다 | 단순 be동사로 되돌린다. `X constitutes a violation` → `X is a violation`. **F-4 와 같은 편집이다** | **E1+E3** 자체 실측 AUC 0.238 (인간 19.31 vs AI **10.15**/1k — AI 가 절반만 씀) · blader #8(41k★) |
| **EN-3** | **3항 등위 남발** — 통사 프레임 `A, B, and C` 다. 어휘 목록이 아니다 (`careers, products, and strategy` · `we shipped fast, learned, and adjusted`) | 문단당 1회까지 허용. 반복되면 **두 항으로 줄이거나 문장을 나눈다**. `X, Y, and Z 가 모두 무너졌다` → `X 와 Y 가 무너졌다. Z 도 마찬가지다`. 셋째 항이 앞 둘의 되풀이면 지운다 — **내용 추가·삭제 금지, 항목이 각기 다른 사실이면 보존한다** | **E1+E3** 자체 실측 AUC 0.737 (인간 중앙값 **0.00** vs AI 1.67/1k). 4모델·2계열 전부 같은 방향(0.655~0.903) · 인간 3출처 전부(0.713~0.786) · blader #10(41k★) |
| **F-4** | 명사화 과다 — `-tion` `-ment` `-ness` `-ity` 체인 | 동사로 되돌린다. `the implementation of the policy` → `implementing the policy` / `the policy took effect` | **E2 ×3** Reinhart 2025 (**1.5~2배**) + Mizumoto 2024 + Jiang & Hyland 2025 — 3개 연구 독립 수렴, 이 룰북에서 근거 최강 |

## Tier B — 구조·서식 (언어 무관성이 자명)

| ID | 트리거 | 처방 | 근거 |
|---|---|---|---|
| **C-1** | `First, … Second, … Third, …` 가 문단을 지배 | 산문으로 푼다. 장르가 열거를 요구하면(매뉴얼·설명문) 보존 | **E1→이식** ko C-1 (논설·에세이 한정) |
| **C-2** | 에세이·칼럼에서 3개 이상 연속 불릿 블록 | 문단으로 되돌린다. 리포트·문서 장르는 보존 | **E1→이식** ko C-2 |
| **C-3** | `Introduction / Body / Conclusion` 식 도식 헤딩 | 내용을 반영한 헤딩으로 바꾸거나 제거 | **E1→이식** ko C-3 |
| **C-5** | 이모지가 리스트 머리·헤딩·강조에 박힘 | 제거. 원문 인용 안이면 보존 | **E1→이식** ko C-5 (S1) |
| **C-6** | 헤딩 직후 `In this section, we will …` 안내문 | 삭제 — 본문이 이미 말한다 | **E1→이식** ko C-6 |
| **C-9** | 인접 문장에서 `1) … 2) … 3)` 인덱싱 | 산문 연결로 바꾼다 | **E1→이식** ko C-9 |
| **C-10** | 헤딩이 거의 자동으로 `X: Y` 콜론 부제 | 콜론을 걷어낸 한 구절 헤딩으로 | **E1→이식** ko C-10 |

## 🛑 건드리면 안 되는 것 — LLM 이 **적게** 쓰는 것

v0.1 이 여기서 틀렸다. hedging·수동태 제거를 Tier A 로 권장했는데 **방향이 반대**였다.

| 항목 | 왜 보호하나 | 근거 |
|---|---|---|
| **hedges · modals** (`may` `might` `appears to` `tends to` `arguably`) | LLM 이 인간보다 **적게** 쓴다. 제거하면 더 AI처럼 된다. 게다가 논증문에서는 **주장의 강도를 바꾸는 내용 변경**(철칙 #1) | **E2 ×3** Jiang & Hyland 2025 (hedges·boosters 유의하게 낮음) · Mizumoto 2024 (인간이 modals·epistemic marker 더 많음) · Reinhart 2025 |
| **agentless passive** | LLM 이 인간의 **절반**만 쓴다. "행위자를 주어로" 처방은 역효과 | **E2** Reinhart 2025 |
| **contraction** | LLM 과소 사용. 펴면 티가 는다 (철칙 #5) | **E2** Reinhart 2025 |
| **1·2인칭 대명사 · discourse marker** | LLM 과소 사용. **관측 전용** — 없는 인칭을 심으면 화자가 바뀐다 | **E2** Mizumoto 2024 · Reinhart 2025 |

> **처방 불가, 관측 전용.** 결핍을 메우려고 없던 hedge·인칭을 심지 않는다
> (`core/principles.md` 「결핍 신호 정책」).

## 규칙으로 세우지 않은 것 (근거 미달 — 넣지 말 것)

| ID | 왜 뺐나 |
|---|---|
| **E-1 문장길이 분산** | **G1 미통과(2026-09-03).** opus 0.59 · sonnet 0.24 · haiku 0.05 — opus 는 인간보다 분산이 **높다**. 방향이 모델마다 갈리는 개인어다. 게다가 시대 교란 40%. **관측 전용** |
| em dash (ko J-3) | **G1 미통과.** Gemini 3.53·Llama 0.00 이 인간 4.76 이하. 모델 개인어. **관측만 한다** |
| 문두 접속사 (ko H-1) | ko 에서 haiku 단독(사람 0.43 vs fable 0.26·gpt 0.83·haiku 6.85) + 과업 편향까지 겹침 |
| 메타 진입 (ko H-3) | ko 에서 haiku 단독. 사람도 쓰는 정상 담화 장치 |
| 안전 균형 (ko G-3) | ko 에서 표본 부족으로 판정 불가(hold) |
| hype 어휘 (ko D-4) | ko 과업매칭 대조군에서 0.00 — 근거 약함 |
| **A-9 수동태 승격** | **v0.1 에서 철회.** LLM 의 agentless passive 는 인간의 절반(Reinhart 2025) — 처방이 반대였다 |
| **G-1 · G-2 완곡 제거** | **v0.1 에서 반전.** 3개 연구가 LLM 의 hedge 과소 사용에 수렴 — 위 「건드리면 안 되는 것」으로 이동 |

## 결핍 신호 — 처방하지 않는다

Reinhart 2025 는 LLM 이 contraction · 1·2인칭 대명사 · 현재시제를 **과소** 사용한다고
보고한다. 이는 탐지·오탐 방지용 **관측 지표**다. 없는 것을 지어내는 처방은 의미
드리프트를 부르고 철칙 #1 을 깬다(`core/principles.md` 결핍 신호 정책).
다만 **원문에 있던 contraction 을 펴지 않는 것**은 철칙 #5 로 강제된다.

## 자체검증 (출력 전)

1. 수치·고유명사·인용 내부가 원문과 일치하는가
2. 원문에 없던 표현을 새로 심지 않았는가 — **특히 em dash 를 늘리지 않았는가**
3. contraction·인칭·시제를 원문보다 격식화하지 않았는가
4. 문장 길이 분산이 올라갔는가(줄었으면 실패)
## 학술 근거

규칙별 인용·등급·caveat 전문: `${SKILL_ROOT}/lang/en/scholarship.md`