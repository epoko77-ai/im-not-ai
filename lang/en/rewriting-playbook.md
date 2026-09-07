# English Rewriting Playbook

> 룰북(`quick-rules.md`)은 **무엇이 티인가**를 말한다. 이 문서는 **어떻게 고치는가**를 말한다.
> 한국어 `rewriting-playbook.md` 의 영어 대응물이다.
>
> **왜 필요한가**: 효능 측정(2026-09-05)에서 스킬 경로의 변경률 중앙값이 **0.5%** 였다.
> 방향과 안전은 확증됐지만 편집량이 작았고, 원인은 실행자가 아니라 **처방의 얇음**이었다.
> 룰북은 규칙마다 한 줄만 준다. 이 문서가 그 한 줄을 실행 가능한 치환으로 편다.

## 0. 대원칙

1. **의미 불변** — 사실·수치·고유명사·인용은 글자 단위로 보존한다. 모호해도 임의로 채우지 않는다.
2. **국소성** — 문장을 통째로 다시 쓰지 않는다. 티가 있는 구간만 손댄다.
3. **빼기 전용** — 처방 예시의 표현을 **원문에 없던 자리에 새로 심지 않는다.**
   특히 문장을 이을 때 **em dash 를 만들지 않는다**(철칙 #6 — 실측에서 윤문이 대시를 2→5 로 늘렸다).
4. **결핍 신호 불간섭** — hedge·수동태·contraction·1·2인칭은 **건드리지 않는다.**
   LLM 이 이미 인간보다 적게 쓰므로 제거하면 글이 더 AI처럼 된다.
5. **장르 유지** — 초록을 에세이로, 에세이를 카피로 옮기지 않는다.

## 1. Tier A — 규칙별 치환 레시피

### EN-1 · 현재분사절 (`, VERB-ing`)

프레임이 표적이다. 동사 목록이 아니다. **세 갈래로 푼다.**

| 원문 | 고침 | 어느 갈래 |
|---|---|---|
| `Costs rose 12%, reflecting weaker demand.` | `Costs rose 12%. Demand had weakened.` | 독립문 분리 |
| `The model was trained on 40B tokens, spanning six languages.` | `The model was trained on 40B tokens across six languages.` | 전치사구 |
| `Results cluster by translator, suggesting a strong idiolect.` | `Results cluster by translator, which suggests a strong idiolect.` | 관계절 |

- 원문이 **인과**를 뜻하면 인과로 푼다(`because`·`so`), **동시성**이면 전치사구로.
- 한 문단에 두 개 이상이면 **최소 하나는 반드시** 푼다. 전부 같은 갈래로 풀지 않는다.
- ⚠️ 분사절을 풀면서 **없던 인과를 만들지 않는다.** 관계 파악이 안 되면 독립문 분리가 안전하다.

### EN-2 · be동사 회피

`is/are` 자리에 무거운 동사·명사구를 놓는 습관을 되돌린다.

| 원문 | 고침 |
|---|---|
| `X constitutes a violation of the policy.` | `X is a policy violation.` |
| `Y represents an improvement over Z.` | `Y is better than Z.` |
| `This serves as evidence that …` | `This is evidence that …` |
| `The result demonstrates the existence of a gap.` | `There is a gap.` |

`F-4`(명사화)와 같은 편집이 되는 경우가 많다 — 한 번에 처리한다.

### EN-3 · 3항 등위 (`A, B, and C`)

**셋째 항이 앞 둘의 되풀이인지** 먼저 본다.

| 원문 | 고침 | 판단 |
|---|---|---|
| `careers, products, and strategy` | `careers and products` | 셋째가 앞 둘의 상위어 → 삭제 |
| `we shipped fast, learned, and adjusted` | `we shipped fast and adjusted as we learned` | 동사 셋 → 둘 + 종속 |
| `X, Y, and Z all collapsed` | `X and Y collapsed. So did Z.` | 항목이 각기 다른 사실 → **문장 분리, 삭제 금지** |
| `Archer, Fjelde, and McLeod` | (그대로) | **고유명사 열거는 내용이다 — 손대지 않는다** |

- 문단당 1회는 허용한다. 수사로서의 tricolon 은 사람도 쓴다.
- **항목이 각기 다른 사실이면 지우지 않는다.** 줄이는 것은 표현이지 내용이 아니다.

### EN-4 · 문장 파편 (마케팅 한정)

동사 없는 짧은 문장이 이어지는 리듬. **마케팅·회사 블로그에서만 규칙이다** —
분석적 에세이에서는 판별력이 없다(AUC 0.559).

| 원문 | 고침 |
|---|---|
| `That worked in 2019. Not anymore.` | `That worked in 2019, but it doesn't now.` |
| `We tried three tools. All slow.` | `We tried three tools, and all of them were slow.` |
| `The result? Zero.` | `The result was zero.` |

- **한 문단에 1회는 허용한다.** 리듬 장치로 사람도 쓴다(인간 중앙 5.56/1k).
- 파편을 이을 때 **대시를 쓰지 않는다**(철칙 #6). 쉼표·접속사·세미콜론으로 잇는다.
- 물음표 파편(`The result?`)은 수사 의문과 겹친다 — 둘 다 걸리면 한 번만 고친다.

### C-8 · 대구(antithesis)

프레임이 여러 개다: `not X but Y` · `it's not X, it's Y` · `neither X nor Y` ·
`less about X than Y` · `is not whether … but` · `rather than X, Y` · `not merely/simply/just X`.

| 원문 | 고침 |
|---|---|
| `It's not a decline, it's a redistribution.` | `It is a redistribution.` |
| `The question is not whether we act but when.` | `The question is when we act.` |
| `This is less about cost than about trust.` | `This is about trust.` |

- **문서당 1회까지 허용.** 나머지는 긍정형 단언으로 편다.
- 대구를 풀면 대비되던 한쪽이 사라진다 — **그 한쪽이 원문의 주장이면 문장을 나눠 둘 다 남긴다.**

### F-7 · 범용 동사 수렴

`delve` `underscore` `showcase` `leverage` `facilitate` `foster` `streamline`
`highlight` `navigate` `harness`.

| 원문 | 고침 |
|---|---|
| `This underscores a shift in demand.` | `Demand shifted.` / `The numbers show a shift.` |
| `We leveraged the existing pipeline.` | `We used the existing pipeline.` |
| `The tool facilitates collaboration.` | `The tool makes collaboration easier.` |

⚠️ 현세대 모델에서는 이 층이 많이 사라졌다(실측: Claude 20편에서 라우터 렉시콘 0건).
**없으면 만들어 고치지 않는다.**

### F-4 · 명사화 과다

`-tion` `-ment` `-ness` `-ity` 가 이어지면 동사로 되돌린다.

| 원문 | 고침 |
|---|---|
| `the implementation of the policy` | `implementing the policy` / `the policy took effect` |
| `a reduction in the frequency of failures` | `failures got rarer` |
| `the establishment of a baseline` | `we set a baseline` |

### C-12 · C-12b · E-5 — 쉼표 계열

셋은 같은 증상의 세 얼굴이다: **삽입구가 많고, 절이 짧고, 문장마다 쉼표가 있다.**

| 증상 | 처방 |
|---|---|
| 삽입구·동격구가 문장마다 | 하나는 앞 문장으로 빼거나 관계절로 붙인다 |
| 쉼표 절이 8어 미만으로 잘게 | 인접한 두 절을 접속사로 잇는다 (**대시로 잇지 않는다**) |
| 모든 문장에 쉼표 | 짧은 문장 두어 개를 쉼표 없이 남긴다 |

⚠️ 이 셋의 임계는 **초록 장르에서만 검증**됐다. 블로그·칼럼에서는 인간도 쉼표를 많이 쓴다 —
`route_signals` 가 지목했을 때만 손댄다.

## 2. Tier B — 구조·서식

| ID | 증상 | 처방 |
|---|---|---|
| C-1 | `First, … Second, … Third,` 가 문단을 지배 | 산문으로 편다. 매뉴얼·설명문 장르는 보존 |
| C-2 | 에세이·칼럼에 불릿 3블록 이상 | 문단으로 되돌린다. 리포트·문서는 보존 |
| C-3 | 콜론 헤딩(`Why this matters:`) | 문장으로 흡수 |
| C-5 | 이모지 | 제거 (장르가 SNS 면 보존) |
| C-6 | 요약 박스·`In summary` 문단 | 결론이 본문에 있으면 삭제, 없으면 한 문장으로 |
| C-9 | 굵은 글씨 남발 | 문단당 1회 이하로 |
| C-10 | 소제목마다 같은 문형 | 문형을 흩는다 |

## 3. 손대지 않는 것 — 이 목록이 처방보다 중요하다

| 대상 | 왜 |
|---|---|
| hedge (`may` `might` `appears to` `tends to` `arguably`) | LLM 이 **인간보다 적게** 쓴다(3연구 수렴). 지우면 더 AI처럼 되고, 논증문에서는 주장 강도를 바꾼다 |
| 무주어 수동태 | LLM 이 인간의 **절반**만 쓴다(Reinhart 2025 PNAS) |
| contraction (`don't` `it's`) | LLM 이 과소 사용. 펴면 티가 는다 |
| 1·2인칭 | 없는 인칭을 심으면 문체가 아니라 화자가 바뀐다 |
| em dash | 규칙이 아니라 **관측 지표**다(G1 미통과). 줄이는 방향으로만 다루고 늘리지 않는다 |
| 큰따옴표 안 · 수치 · 고유명사 · 인용문헌 | 철칙 #1 |

## 4. 고치고 나서 스스로 보는 것

1. 원문에 없던 **수치·주장**이 생기지 않았나
2. 유보·당위(`may`·`should`)가 단정으로 바뀌지 않았나
3. 문장을 이으면서 **em dash** 를 만들지 않았나
4. 상투구(`It's worth noting` · `At the end of the day`)를 새로 심지 않았나
5. 손댄 구간이 전부 **지목된 규칙에 연결**되나 — 아니면 되돌린다

이 다섯은 게이트가 결정적으로 재검사한다(`content_preservation` · `modality_loss` ·
`reinjection` · `verify_change_rate` · `underedit`). 자기 보고가 아니라 exit code 가 판정한다.
