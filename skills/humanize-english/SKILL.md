---
name: humanize-english
version: "0.2.0"
description: AI(ChatGPT·Claude·Gemini 등)가 쓴 영어 텍스트를 사람이 쓴 글처럼 윤문하는 스킬. antithesis 대구("not X but Y")·범용 동사 수렴(delve·underscore·showcase)·문장 길이 분산 부족·명사화 과다·hedging·수동태 남용과 구조 티(불릿·이모지·콜론 헤딩·First/Second/Third)를 탐지·재작성한다. 내용은 한 글자도 바꾸지 않고 문체·리듬·표현만 손댄다. 트리거 — "humanize this English", "make this sound human", "remove AI tells", "this reads like ChatGPT", "de-slop", "영어 AI 티 제거", "영어 글 자연스럽게", "영문 윤문". 한국어 텍스트는 humanize-korean 스킬을 쓴다. 단순 문법·오탈자 교정(grammar check)이나 번역은 이 스킬이 아니다.
---

# Humanize English — AI 영어 티 제거 (v0.2)

> ⚠️ **임계는 장르에 종속된다 (v0.2 에서 측정·배선).** 초록 보정 임계를 블로그에
> 그대로 쓰면 인간 중앙값이 통째로 AI 쪽에 떨어져 라우터가 죽는다 — 분리도 0.29,
> 인간 에세이의 21% 를 heavy 로 오탐했다. 그래서 shim 에 `--genre` 를 넘겨
> **임계 셀을 고른다**(`abstract` · `blog`).
>
> | 셀 | 코퍼스 | 분리도 |
> |---|---|---|
> | abstract | arXiv 인간 42 vs AI 21 | **0.95** |
> | blog (기본) | LW·PG·SSC 인간 100 vs AI 102 | **0.65** |
> | blog / GPT 산문 | 같은 인간 vs codex CLI 34 | **1.37** |
>
> 두 셀 밖(마케팅 카피·기술 문서·소설)은 **미검증이다.** 그 경우 `route_hint` 를
> 근거로 들지 말고 사용자에게 한 줄로 알린다.
>
> **근거 상태를 먼저 밝힌다.** v0.2 기준 **임계는 E1**(자체 대조 코퍼스 실측 —
> abstract·blog 두 셀)이고, **규칙 자체는 여전히 E2·E3** 다(외부 발표 + 자체
> 스파이크). 그래서 **light/standard 2경로만 열고 heavy·finalize 는 닫는다** —
> 영어에는 finalize 에이전트도, 검증 증적을 주장할 근거도 아직 없다.
> 등급 정의: `${SKILL_ROOT}/core/principles.md`.

> **실측된 동작 (2026-09-05 · 홀드아웃 28편으로 확증).** 승격 지표 둘 다 유의하게
> 개선되고(p=.0034 · p<.00001), 게이트 위반이 **0%**(내용·서법·역주입·과소윤문),
> 변경률 중앙값 **0.5%**(최대 3.1%). **확증된 것은 방향과 안전이지 크기가 아니다.**
> 같은 글을 맨 프롬프트("make this sound human")로 고치면 지표는 크게 움직이지만
> 내용 43% · 서법 64% · 역주입 79% 에서 위반이 난다.
> **"망가뜨리지 않지만 많이 하지도 않는다"**가 현재 상태다 — 영어에서 근거가 붙은
> 규칙이 적어 손댈 자리도 적다. 근거: `docs/2026-09-05-en-efficacy-results.md`.

## Phase 0: 상태 줄 + 경로 결정

Phase 1(shim) 직후 다음 한 줄을 출력한다.

```
humanize-english v0.2 — path: {light|standard} ({route_hint|user}) / genre: {threshold_set} / run_id: {YYYY-MM-DD-NNN}
```

### 경로 결정
1. **사용자 명시가 최우선.** "가볍게"·"light"·"minimal" → light 고정.
1-b. **장르를 판정해 shim 에 넘긴다.** 학술 초록류면 `--genre abstract`,
   블로그·칼럼·에세이면 `--genre blog`(기본값). 두 셀 밖이면 `blog` 로 두되
   위 표의 미검증 고지를 붙인다. 넘긴 값은 `00_metrics.json` 의
   `threshold_set` 으로 되돌아오므로 상태 줄에 함께 적는다.
2. 명시가 없으면 `00_metrics.json` 의 `route_hint` 를 따른다.
3. **`route_hint` 가 `heavy` 여도 standard 로 처리한다.** 영어에는 heavy 경로가
   요구하는 finalize 에이전트가 없다. 대신 사용자에게 한 줄 고지한다:
   "This text scored heavy ({route_reason}). English support caps at standard —
   the deep-verification path needs measured evidence we don't have for English yet."
4. `route_hint` 부재·shim 실패 → standard.

### run_id 결정
- cwd 기준 `_workspace/{YYYY-MM-DD-NNN}/`. 기존 시퀀스는 **`Glob` 도구**로 조회:
  `Glob(pattern="_workspace/YYYY-MM-DD-*/01_input.txt")` → 폴더명에서 NNN 최댓값 + 1.
  Glob 은 디렉터리 자체를 매칭하지 못하므로 반드시 안의 표지 파일을 매칭한다.
  `Bash ls` 는 OS·셸에 따라 달라지므로 쓰지 않는다.
- 당일 폴더가 없으면 001.

## 스크립트 경로 규칙 (`${SKILL_ROOT}`)

**스크립트는 절대경로로 부른다.** `scripts/`·`core/`·`lang/` 은 설치 루트 기준이고
`_workspace/` 는 cwd 기준이다. 둘이 한 명령줄에 섞이므로 스크립트 쪽만 고정한다.

```bash
SKILL_ROOT="$(d="$(cd -P "${CLAUDE_SKILL_DIR}" && pwd)"; \
  while [ "$d" != / ] && [ ! -d "$d/.claude-plugin" ]; do d="$(dirname "$d")"; done; echo "$d")"
```

`cd -P` 가 핵심이다 — 심링크 설치에서 논리 경로를 따라가면 엉뚱한 곳으로 올라간다.

**확인**: `ls "${SKILL_ROOT}/lang/en/quick-rules.md"` 가 실패하면 경로 유도가 틀린 것이다.
추측하지 말고 **사용자에게 알린 뒤** shim·게이트 없이 진행한다.

## Phase 1: 입력 저장 + 정량 사전 점수

1. cwd 기준 `_workspace/{run_id}/` 생성
2. 입력을 `01_input.txt` 에 저장
   - **챗봇 잔재 위생**: 머리("Sure! Here's…", "Certainly —")·꼬리("Let me know if
     you'd like…", "I hope this helps!")를 벗겨낸다. 본문이 아니므로 의미 손실 0.
3. shim 1회 실행:
   ```
   python3 ${SKILL_ROOT}/scripts/prepare_monolith_input.py --run-dir _workspace/{run_id} --lang en \
     --genre {abstract|blog}
   ```
   - 산출: `00_metrics.json`(`route_hint`·`route_reason`·`route_signals`·
     `threshold_set`) + `01_input_with_metrics.txt`
   - 결합 파일의 지표·규칙 ID 는 **영어 것만** 실린다(v0.2 에서 수정 — 그 전에는
     한국어 v1.6 블록과 존재하지 않는 규칙 ID 가 실렸다).
   - graceful degrade 내장 — 실패 시 점수 블록 없이 진행하고 `00_metrics.error` 를 남긴다.
4. `route_hint` 를 읽어 경로를 확정하고 상태 줄을 출력한다.

## Light 경로 (1콜) — 이미 잘 쓴 글

목표는 **과윤문 방지**다. 많이 고치는 게 아니다.

1. `Read` 로 `01_input_with_metrics.txt` 와 `${SKILL_ROOT}/lang/en/quick-rules.md` 를 읽는다.
2. **보수 강도**로 윤문한다 — 확신 없는 구간은 그대로 둔다. 내용 명사·수치·인용은 원형 보존.
3. `Write` 로 `_workspace/{run_id}/final.md` 에 본문만 쓴다.
4. Phase 2 게이트 실행.
5. 손댄 곳이 거의 없으면 "This already reads well — I touched {N} spots ({요지})" 로 보고한다.

## Standard 경로 (1콜, 겨냥 윤문) — 보통의 AI 초안

한국어와 달리 **별도 진단 콜을 두지 않는다.** 영어 진단 인덱스가 없고, 룰북이 14규칙으로
작아 단일 콜에 전부 들어간다. 콜 수를 늘릴 근거가 없다.

1. `Read` 로 `01_input_with_metrics.txt` + `${SKILL_ROOT}/lang/en/quick-rules.md`.
2. `00_metrics.json` 의 `route_signals` 를 겨냥에 쓴다:
   - `en1_participial_per_1k` 가 높으면 → **EN-1 우선**(분사절을 절·독립문으로).
     룰북 최강 근거(AUC 0.787, 전 모델 일치, E1+E2+E3).
   - `en2_be_verb_per_1k` 가 낮으면 → **EN-2**(무거운 동사·명사구를 be동사로).
   - `tricolon_per_1k` 가 0 보다 크면 → **EN-3**(3항 등위를 두 항으로 줄이거나
     문장을 나눈다. 항목이 각기 다른 사실이면 보존한다).
   - ⚠️ `dispersion` 은 **G1 미통과**다(opus 는 인간보다 높다). 겨냥에 쓰지 않는다.
   - `lexicon.by_family` 에 `F-7` 이 있으면 → 범용 동사 교체 우선.
   - `comma_inclusion_rate` 가 높으면 → 쉼표 분절 정리.
3. Tier A 우선, Tier B 는 서식 문제가 실재할 때만.
4. **hedge·수동태·contraction·인칭은 건드리지 않는다** — LLM 이 이미 과소
   사용하므로 제거하면 더 AI처럼 된다(룰북 「건드리면 안 되는 것」).
4. `Write` 로 `final.md`.
5. Phase 2 게이트 실행.

## Phase 2: 결정적 게이트 (전 경로 공통 — LLM 콜 아님)

**다섯 게이트를 순서대로 Bash 로 실행한다.** 앞의 셋은 '내용을 바꿨다'를,
넷째는 '새 티를 심었다'를, 다섯째는 '너무 적게 했다'를 잡는다.
전부 언어 무관으로 검증된 코드다.

```bash
python3 ${SKILL_ROOT}/scripts/verify_change_rate.py \
  --before _workspace/{run_id}/01_input.txt \
  --after  _workspace/{run_id}/final.md
```
- exit 0 — 수렴. 통과.
- exit 1 — 30~50% 경고. 사용자에게 고지하고 진행.
- exit 2 — **50% 초과. 윤문본 채택 금지.** 보수 강도로 1회 재실행(총 2콜).
  재실행도 exit 2 면 사용자에게 알리고 원문을 유지한다.
- exit 3 — 실행 오류. 게이트 없이 진행했음을 **반드시 고지**한다.

```bash
python3 ${SKILL_ROOT}/core/content_preservation.py \
  --before _workspace/{run_id}/01_input.txt \
  --after  _workspace/{run_id}/final.md
```
- exit 0 — 수치·인용·전거·제목 보존. 통과.
- exit 1 — **철칙 #1 위반.** 없던 수치가 생겼거나(number_injected) 직접 인용·
  인용문헌·제목이 사라졌다. 해당 구간을 원문으로 되돌린 뒤 다시 돌린다.
  `advisory` 의 수치 소실은 판정이 아니다 — 문장 병합의 정상 부산물일 수 있다.
- exit 3 — 실행 오류. 고지 후 진행.

```bash
python3 ${SKILL_ROOT}/core/modality_loss.py \
  --before _workspace/{run_id}/01_input.txt \
  --after  _workspace/{run_id}/final.md
```
- exit 0 — 서법 보존. 통과.
- exit 1 — **유보·당위가 단정이 됐다.** `may`·`suggests`·`should` 를 지우는 건
  AI 티 제거가 아니라 필자의 주장 강도 변경이다. 지목된 문장의 표지를 되살린다.
- exit 3 — 실행 오류. 고지 후 진행.

```bash
python3 ${SKILL_ROOT}/core/reinjection.py \
  --before _workspace/{run_id}/01_input.txt \
  --after  _workspace/{run_id}/final.md --lang en
```
- exit 0 — 새 티 없음. 통과.
- exit 1 — **철칙 #6 위반.** 출력이 지목한 표현(em dash·결론 공식·cleft·초과 어휘)을
  원문 수준으로 되돌린 뒤 `final.md` 를 갱신하고 이 게이트를 다시 돌린다.
- exit 3 — 실행 오류. 고지 후 진행.

```bash
python3 ${SKILL_ROOT}/core/underedit.py \
  --before _workspace/{run_id}/01_input.txt \
  --after  _workspace/{run_id}/final.md \
  --lang en --genre {abstract|blog} --route-hint {00_metrics.json 의 route_hint 값}
```
- exit 0 — 지목된 티가 줄었다(또는 light 라 검사 생략). 통과.
- exit 1 — **과소윤문.** 라우터가 손댈 게 있다고 했는데 분산·장문율·쉼표·어휘가
  하나도 안 움직였다. 지목된 신호를 실제로 손봐 `final.md` 를 갱신하고 다시 돌린다.
  2회 시도 후에도 exit 1 이면 사용자에게 "티가 남아 있다"고 알린다.
- exit 3 — 실행 오류. 고지 후 진행.

> **왜 세 번째 게이트가 필요한가**: 실측(2026-09-02, n=4)에서 윤문 4회 중 1회가
> 변경률 0.4% 로 사실상 아무것도 하지 않았다 — 분산 7.04 → 7.00, 장문율 0.00%
> 그대로. 앞의 두 게이트는 "너무 많이 했다"만 잡으므로 통과시켰다.
> 같은 라운드의 맨 프롬프트 대조군은 6회 중 **4회**가 이 실패 모드였다.

> **왜 네 번째 게이트가 필요한가**: 실측(2026-09-02)에서 윤문이 목표 지표를 전부
> 0 으로 내리면서 em dash 를 2→5 로 늘렸다. 그 값(9.33/1k)은 윤문 모델 자신의
> 개인어(9.09/1k)와 거의 일치했다. 티를 지우는 행위가 새 티를 심는다.

> **왜 내용 게이트 둘이 필요한가**: 나머지 셋은 전부 **문체 축**이다. 수치·인용·
> 전거가 바뀌어도 셋 다 통과한다 — 철칙 #1 에 코드 방어가 하나도 없었다.
> 서법 게이트는 특히 영어에서 중요하다. LLM 은 hedge 를 인간보다 **적게** 쓰는데
> (세 연구 수렴 — `scholarship.md`), 윤문 지시는 문장을 짧고 세게 만들라고 한다.
> 그 압력이 `may`·`suggests` 를 지우는 쪽으로 작동한다.
> 검증: 실제 영어 윤문 4쌍 + 코퍼스 104편의 문장 병합·분할 교란에서 **오탐 0**,
> 표지 1개 삭제 주입에서 **탐지 85/85**(`lang/en/scholarship.md` 「게이트 검증」).

## 결과 전달

- `final.md` 경로와 경로(light/standard)를 알린다.
- 무엇을 왜 고쳤는지 3~5줄. 규칙 ID 를 든다(C-8·F-7·E-1 …).
- 게이트 결과를 숨기지 않는다 — 변경률·내용 보존·서법·역주입·과소윤문 다섯 판정을 함께 보고한다.
- `route_hint` 가 heavy 였으면 Phase 0 의 고지를 다시 한 번 붙인다.

## 주의 사항

- **수치·고유명사·인용 내부는 절대 변경 금지.**
- **원문에 없던 정보 추가 금지.** 문장을 이을 때 접속사·마침표를 쓰고 **내용을 만들지 않는다.**
- **contraction 을 펴지 않는다** — LLM 이 contraction 을 과소 사용하므로(Reinhart 2025)
  펴는 건 티를 더하는 쪽이다. 철칙 #5(register 양방향 보존).
- em dash 를 **줄이는 방향으로만** 다룬다. 규칙은 아니지만(G1 미통과) 늘리면 안 된다.
- 결핍 신호(인용·괄호 부족)는 **관측만 한다.** 없는 인용을 지어내면 철칙 #1 위반이다.
- 한국어 텍스트가 들어오면 이 스킬을 쓰지 말고 `humanize-korean` 을 안내한다.

## 참고 자료

- 언어 무관 원리·증거 기준: `${SKILL_ROOT}/core/principles.md`
- 영어 룰북: `${SKILL_ROOT}/lang/en/quick-rules.md` (Tier A 9 + Tier B 7)
- 영어 렉시콘: `${SKILL_ROOT}/lang/en/lexicon.json` (Kobak 407건, 라우터용 12건)
- **학술 근거 SSOT: `${SKILL_ROOT}/lang/en/scholarship.md`** — 규칙별 인용·등급·정정 기록
- 후보 풀: `${SKILL_ROOT}/lang/en/candidate-pool.md` — 커뮤니티 수집 35건 + 승격 절차
- 설계·근거: `docs/superpowers/specs/2026-09-02-multilingual-design.md`
