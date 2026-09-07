# R1 — 원리 층 추출 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 언어와 무관한 원리·계측 층을 저장소 루트 `core/` 로 추출하고, 다국어 확장이 딛고 설 증거 기준(G1·G2·G3)을 문서·테스트로 못박는다.

**Architecture:** 한국어 자산은 **한 파일도 옮기지 않는다.** 새 `core/` 디렉터리에 (a) 판정 규칙 문서 `principles.md`, (b) `metrics_v2.py` 에서 분리한 언어 무관 `change_rate.py`, (c) 새 `metrics_universal.py` 를 만든다. 기존 import 경로는 재수출(re-export)로 전부 살려 둔다. 더불어 스파이크·리서치에서 드러난 문서 오류 2건(패턴 수 70/71→81, E-1 실체 재framing)을 결정적 테스트와 함께 고친다.

**Tech Stack:** Python 3.11+ 표준 라이브러리만 (이 저장소는 stdlib-only, pytest 가 유일한 테스트 의존성). 새 의존성 추가 금지.

**Spec:** `docs/superpowers/specs/2026-09-02-multilingual-design.md`
**선행 근거:** `docs/spikes/2026-09-02-en-transplant.md`

## Global Constraints

- **stdlib only.** `pip install` 대상은 pytest 뿐이다 (`.github/workflows/test.yml`). spaCy·pybiber·konlpy·mecab 도입 금지.
- **한국어 자산 이동 금지.** `skills/humanize-korean/` 아래 파일의 **경로 변경 없음**. 내용 수정은 Task 3 의 E-1 항목과 Task 4 의 재수출 라인만.
- **런타임 경계 유지.** 프로덕션 코드(`scripts/`·`core/`)는 `tests/` 트리를 import 하지 않는다 (`tests/test_runtime_boundary.py` 가 감시).
- **버전 SSOT.** `skills/humanize-korean/SKILL.md` frontmatter 의 `version:` 이 SSOT다. R1 은 버전을 올리지 않는다 — 매니페스트 3종(`.claude-plugin/plugin.json`·`plugin.json`·`.claude-plugin/marketplace.json`)을 건드리지 않는다.
- **테스트는 unittest 클래스 + pytest 양쪽 실행 가능**하게 쓴다 (기존 `tests/*.py` 관례).
- **한국어로 쓴다.** 문서·주석·docstring 은 기존 저장소와 같이 한국어.
- CI 전체 재현 명령: `pytest tests/ -v && python3 scripts/build_quick_rules.py --check && python3 scripts/build_diagnosis_rules.py --check && bash tests/test_install_flags.sh`

---

### Task 1: 증거 기준 문서 `core/principles.md`

이 저장소가 비싸게 얻은 판정 규칙 3개를 언어 무관 계약으로 승격한다. 지금은 `empirical-validation.md` 본문 여기저기에 흩어져 있어, 새 언어를 만드는 사람이 같은 기준을 적용할 방법이 없다.

**Files:**
- Create: `core/principles.md`
- Create: `tests/test_principles_contract.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `core/principles.md` 안에 정확한 앵커 문자열 `### G1`, `### G2`, `### G3` 과 `## 철칙` 절. Task 2·3 및 R2 계획이 이 앵커를 참조한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_principles_contract.py`:

```python
"""core/principles.md 계약 — 증거 기준이 문서에 실재하는지 결정적 검증.

`test_agent_inventory.py` 가 SKILL.md 서술과 agents/ 실물의 drift 를 막듯,
이 테스트는 "증거 기준을 문서에 적어두고 잊는" drift 를 막는다.
stdlib only, claude CLI 불필요 — CI 에서 항상 실행된다.
"""
from __future__ import annotations

import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_PRINCIPLES = os.path.join(_ROOT, "core", "principles.md")
_KO_SKILL = os.path.join(_ROOT, "skills", "humanize-korean", "SKILL.md")

# 증거 기준 3종. 언어팩을 새로 만드는 사람은 이 셋을 통과시켜야 한다.
GATE_ANCHORS = ("### G1", "### G2", "### G3")

# 각 게이트가 반드시 인용해야 하는 실측 앵커 — 근거 없는 규칙을 막는 것이
# 이 문서의 존재 이유이므로, 문서 자신이 근거를 달지 않으면 자기모순이다.
GATE_EVIDENCE = {
    "### G1": ("H-1", "em dash"),
    "### G2": ("J-2",),
    "### G3": ("역주입",),
}


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class PrinciplesContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            os.path.isfile(_PRINCIPLES),
            f"core/principles.md 가 없다: {_PRINCIPLES}",
        )
        self.text = _read(_PRINCIPLES)

    def test_six_ironclad_rules_present(self) -> None:
        """철칙은 6개다 — CLAUDE.md 가 선언한 수와 일치해야 한다."""
        self.assertIn("## 철칙", self.text)
        numbered = [f"{n}." for n in range(1, 7)]
        for marker in numbered:
            self.assertIn(
                marker,
                self.text,
                f"철칙 {marker} 항목이 core/principles.md 에 없다",
            )

    def test_evidence_gates_present(self) -> None:
        for anchor in GATE_ANCHORS:
            self.assertIn(
                anchor,
                self.text,
                f"증거 기준 {anchor} 절이 없다 — 새 언어팩이 적용할 기준이 사라진다",
            )

    def test_each_gate_cites_its_evidence(self) -> None:
        """게이트마다 실측 앵커를 인용한다. 근거 없는 기준은 기준이 아니다."""
        sections = {}
        current = None
        for line in self.text.splitlines():
            if line.strip() in GATE_ANCHORS:
                current = line.strip()
                sections[current] = []
            elif current is not None:
                if line.startswith("## "):
                    current = None
                else:
                    sections[current].append(line)
        for anchor, needles in GATE_EVIDENCE.items():
            body = "\n".join(sections.get(anchor, []))
            for needle in needles:
                self.assertIn(
                    needle,
                    body,
                    f"{anchor} 절이 근거 '{needle}' 를 인용하지 않는다",
                )

    def test_ko_skill_links_principles(self) -> None:
        """ko 스킬이 커널 문서를 가리켜야 한 방향 참조가 성립한다."""
        self.assertIn(
            "core/principles.md",
            _read(_KO_SKILL),
            "SKILL.md 가 core/principles.md 를 참조하지 않는다",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_principles_contract.py -v`
Expected: 4개 테스트 모두 FAIL — `setUp` 에서 `core/principles.md 가 없다` AssertionError.

- [ ] **Step 3: `core/principles.md` 를 쓴다**

```markdown
# Humanize — 언어 무관 원리 (core/principles.md)

> **커널 문서.** 언어별 taxonomy 는 이 아래에 있다. 새 언어팩을 만들 때
> 규칙 하나하나는 달라져도 이 문서는 그대로 적용된다.
>
> 근거 원문: `skills/humanize-korean/references/empirical-validation.md`,
> `docs/spikes/2026-09-02-en-transplant.md`,
> `docs/superpowers/specs/2026-09-02-multilingual-design.md`

## 철칙

1. **의미 불변 (Fidelity First)** — 사실·주장·수치·고유명사·인용은 100% 원문 보존.
2. **근거 기반 (Span-Grounded)** — 모든 변경은 탐지 finding 에 연결. 탐지 없는 구간은 건드리지 않는다.
3. **장르 유지 (Tone Match)** — 칼럼을 문학으로, 리포트를 에세이로 옮기지 않는다.
4. **과윤문 금지 (No Over-Polish)** — 변경률 30% 초과 경고, 50% 초과 강제 중단. 판정은 `scripts/verify_change_rate.py` 가 내린다(LLM 자가보고 아님).
5. **register 보존 — 양방향** — 격식체 입력은 격식체 출력, 구어 입력은 구어 출력. 원문보다 딱딱하게 만들지 않는다. AI 티는 문법·수사이지 격식 자체가 아니다.
6. **AI 티는 빼기만 하고 넣지 않는다 (No New Tells)** — 원문에 없던 상투구 신규 삽입 금지. 철칙 #2 가 "탐지 없는 구간은 손대지 않는다"라면, #6 은 "손대는 구간에도 새 AI 티를 심지 않는다".

## 증거 기준 — 무엇을 규칙이라 부를 수 있는가

패턴이 규칙이 되려면 셋을 통과해야 한다. 셋 다 언어와 무관하며, 한국어와 영어
양쪽 실측에서 각각 필요함이 증명됐다.

### G1 — 전 모델 생존

어떤 패턴도 **테스트한 모든 모델에서 사람보다 높아야** 규칙이 된다.
한 모델이 총계를 끌어올린 항목은 그 모델의 개인어이지 "AI다움"이 아니다.

근거 (한국어): H-1 문두 접속사 — 사람 0.43 vs fable-5 0.26 · gpt-5.6-sol 0.83 · haiku-4.5 **6.85**/1k.
haiku 단독이었다. 처방을 "문서 일괄 제거"에서 "한 문단 3회+ 밀집 시 일부만"으로 보수화하고
fast 경로의 잔존 목록에서 뺐다. H-3 도 같은 이유로 강등.

근거 (영어): em dash — 인간 4.76(통제 3.23) vs GPT-4.1 10.62 · Claude Opus 4.6 9.09 ·
DeepSeek V3 6.95 · **Gemini 2.5 Pro 3.53** · **Llama 3.1 8B 0.00** /1k
(SlopDetector 2026, 인간 702,939 words). Gemini 는 인간과 구별 불가, Llama 는 인간보다 낮다.
→ **G1 미통과. em dash 는 규칙이 아니라 관측 지표다.**

이론적 뒷받침: Rudnicka & Juzek 2026 (arXiv:2608.06589) — "AI language" 초변종과
모델별 개인어가 공존한다. 같은 코호트 6모델의 contraction 이 1,200~30,000/M (25배 폭).

### G2 — 과업 통제

인간 표본과 AI 표본의 **과업 조건이 다르면 측정은 무효**다. 문체 차이로 보이는 것이
과업 차이일 수 있다.

근거 (한국어): J-2 따옴표 — 사람 11.36 vs AI 0.00 으로 "AI 는 따옴표를 안 쓴다"로 읽혔다.
같은 프롬프트·같은 모델에 **과업 조건만 사람 코퍼스에 맞추자**(직접 인용 2회+·수치/기관명 3회+·800~1000자)
AI 가 **26.89** 로 튀었다. 결론이 뒤집혔다 — 인용을 요구하면 AI 가 2.4배 더 쓴다.
같은 대조군에서 H-1 은 2.29→0.13, D-4 hype 는 0.34→0.00 으로 무너졌고,
**C-8 대구만 6.30→6.13 으로 흔들리지 않았다.**

근거 (영어): 스파이크에서 참조 문서(인용·삽입구가 원래 많은 장르)와 에세이를 비교하자
따옴표·대시가 문서 쪽에서 훨씬 높게 나왔다. 같은 함정이 같은 지표에서 재현됐다.

### G3 — 역주입 금지

윤문 전후를 **같은 지표로 재측정**한다. 지우기로 한 티가 줄었어도 **다른 지표가 새로 올랐으면 실패**다.
윤문 콜은 티를 지우면서 자기 모델의 개인어를 심는다.

근거 (한국어): D-9 결산 정리가 '결국' 을 역주입해 재실측에서 2→4 로 늘었다.
D-14·C-11 회차에서 같은 실패 모드가 반복돼 결정적 차단을 넣었다.

근거 (영어): 스파이크 윤문에서 목표 지표는 전부 내려갔으나(D-1·D-6·D-8·D-11·D-12·A-15·F-7 → 0.00)
em dash 가 2건 → 5건(**9.33/1k**)으로 늘었다. 장문 부재를 고치려고 문장을 이어 붙이면서
접합부에 대시를 심은 것이다. 발표된 **Claude Opus 4.6 = 9.09/1k** 와 거의 일치한다 —
우연이 아니라 윤문 모델의 개인어 주입이다.

**밀도 지표를 볼 때는 분모를 함께 본다.** 같은 스파이크에서 I-4 3.42→3.73,
F-1 1.71→1.87 의 상승은 역주입이 아니라 본문이 짧아진 artifact 였다(원시 건수 2건·1건 불변).

## 이식 가치 순위

다국어 확장에서 무엇을 먼저 옮길지의 답. 스파이크 실측으로 뒤집힌 순서다.

| 순위 | 층 | 이식 비용 |
|---|---|---|
| 1 | **원리** — 철칙 6개, 증거 기준 G1·G2·G3, 역주입 경계 | 0 |
| 2 | **계측** — 분산·쉼표·길이 분포·변경률 (산술) | 0 |
| 3 | **규칙** — 담화·수사 층 패턴 | 중 |
| 4 | **탐지 구현** — 정규식 | 불가 (영어 첫 시도 재현율 0/6) |

## 결핍 신호 정책

AI 가 **과다한 것**만큼 **결핍한 것**도 강한 신호다. 다만 **처방 가능한 것만 규칙화하고
나머지는 관측만 한다** — 없는 것을 만들어내는 처방은 의미 드리프트를 부르고 철칙 #1 을 깬다.

- 처방 가능: 장문 결핍(인접 문장 잇기 — 내용 추가 금지)
- 관측 전용: 인용 결핍, 괄호 결핍, contraction 결핍, 1·2인칭 대명사 결핍
```

- [ ] **Step 4: ko SKILL.md 에 한 줄 참조를 넣는다**

`skills/humanize-korean/SKILL.md` 의 `## 참고 자료` 절 첫 항목으로 추가 (버전 문자열은 건드리지 않는다):

```markdown
- 언어 무관 원리·증거 기준: [`${SKILL_ROOT}/core/principles.md`](../../core/principles.md)
```

- [ ] **Step 5: 테스트 통과를 확인한다**

Run: `python3 -m pytest tests/test_principles_contract.py -v`
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add core/principles.md tests/test_principles_contract.py skills/humanize-korean/SKILL.md
git commit -m "feat(core): 언어 무관 원리 층 추출 — 철칙 6 + 증거 기준 G1·G2·G3"
```

---

### Task 2: 패턴 수 정정 (70/71 → 81) + 결정적 카운트 가드

문서가 "10대분류 × 활성 70 패턴(+A-17 hold 1건)" 이라고 적고 있으나 SSOT 의 실제 ID 수는 **81** 이다. v2.6 라운드에서 10건이 늘었는데 헤더 갱신이 누락됐다. 사람의 체크리스트 대신 테스트가 막게 한다.

**Files:**
- Create: `tests/test_pattern_count_sync.py`
- Modify: `CLAUDE.md` (프로젝트 개요 절 · 참고 절)
- Modify: `skills/humanize-korean/SKILL.md` (frontmatter `description` 의 "70개 AI 티 패턴")
- Modify: `scripts/build_diagnosis_rules.py` (헤더의 "71패턴 전수" 를 실측 수로 생성)
- Modify: `skills/humanize-korean/references/diagnosis-rules.md` (빌드 산출물 — 재생성)

**Interfaces:**
- Consumes: 없음
- Produces: `tests/test_pattern_count_sync.py` 의 `ssot_pattern_ids() -> set[str]` — Task 3 이 E-1 존재 확인에 재사용한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_pattern_count_sync.py`:

```python
"""패턴 수 동기화 — 문서가 선언한 수와 SSOT 실물의 drift 를 막는다.

v2.6 에서 패턴이 10건 늘었는데 CLAUDE.md·SKILL.md·diagnosis-rules 헤더가
"70/71" 에 멈춰 있었다(2026-09-02 발견). 사람이 세는 방식으로는 또 어긋난다.

stdlib only, CI 상시 실행.
"""
from __future__ import annotations

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_TAXONOMY = os.path.join(
    _ROOT, "skills", "humanize-korean", "references", "ai-tell-taxonomy.md"
)
_DIAGNOSIS = os.path.join(
    _ROOT, "skills", "humanize-korean", "references", "diagnosis-rules.md"
)
_CLAUDE_MD = os.path.join(_ROOT, "CLAUDE.md")
_KO_SKILL = os.path.join(_ROOT, "skills", "humanize-korean", "SKILL.md")

# diagnosis-rules.md 는 SSOT 에서 생성된 전수 인덱스라 ID 집합의 기준으로 쓴다.
_ID_RE = re.compile(r"^- \*\*([A-J]-\d+)\*\*", re.M)

# 문서들이 패턴 수를 선언하는 자리. CLAUDE.md 와 SKILL.md 는 **각각 두 형식으로
# 두 번씩** 선언한다(실측 2026-09-02: CLAUDE.md:5·78, SKILL.md:4·328).
# search() 로 첫 매치만 보면 나머지가 70 에 남아도 테스트가 통과한다 — finditer 로 전수 검사.
_DECLARATION_FORMS = (
    re.compile(r"활성\s*(\d+)\s*패턴"),
    re.compile(r"카테고리\s*(\d+)\s*개\s*AI 티 패턴"),
    re.compile(r"\*\*(\d+)\s*패턴 전수\*\*"),
)
_DECLARING_FILES = (_CLAUDE_MD, _KO_SKILL, _DIAGNOSIS)

# 최소 몇 곳에서 선언을 찾아야 하는지 — 정규식이 조용히 아무것도 못 잡는 것을 막는다.
_MIN_DECLARATION_SITES = 5


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def ssot_pattern_ids() -> set[str]:
    """SSOT 가 정의한 패턴 ID 전수."""
    return set(_ID_RE.findall(_read(_DIAGNOSIS)))


class PatternCountSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ids = ssot_pattern_ids()

    def test_ssot_has_patterns(self) -> None:
        self.assertGreater(len(self.ids), 50, "SSOT 파싱이 깨졌다")

    def test_declared_counts_match_ssot(self) -> None:
        actual = len(self.ids)
        found = 0
        for path in _DECLARING_FILES:
            text = _read(path)
            for pattern in _DECLARATION_FORMS:
                for match in pattern.finditer(text):
                    found += 1
                    declared = int(match.group(1))
                    line = text[: match.start()].count("\n") + 1
                    self.assertEqual(
                        declared,
                        actual,
                        f"{os.path.basename(path)}:{line} 선언 {declared} "
                        f"!= SSOT 실측 {actual}",
                    )
        self.assertGreaterEqual(
            found,
            _MIN_DECLARATION_SITES,
            f"패턴 수 선언을 {found}곳만 찾았다 — 정규식이 실물과 어긋났을 수 있다",
        )

    def test_taxonomy_and_diagnosis_agree(self) -> None:
        """빌드 산출물이 SSOT 와 같은 ID 집합을 담는지."""
        taxonomy_ids = set(
            re.findall(r"^#{3,4}\s+\*{0,2}([A-J]-\d+)", _read(_TAXONOMY), re.M)
        )
        missing = self.ids - taxonomy_ids
        self.assertFalse(
            missing,
            f"diagnosis-rules 에만 있고 taxonomy 에 없는 ID: {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_pattern_count_sync.py -v`
Expected: `test_declared_counts_match_ssot` FAIL — `CLAUDE.md 선언 70 != SSOT 실측 81`.

> 정규식은 실물로 검증했다(2026-09-02): `^#{3,4}\s+\*{0,2}([A-J]-\d+)` 가 taxonomy 에서
> **81개**를 잡고, `test_taxonomy_and_diagnosis_agree` 는 통과한다.
> 실패하는 것은 `test_declared_counts_match_ssot` 하나여야 정상이다.

- [ ] **Step 3: 빌드 스크립트가 실측 수를 찍게 고친다**

`scripts/build_diagnosis_rules.py` 에서 헤더의 `71패턴 전수` 하드코딩을 찾아 실측값 삽입으로 바꾼다. 파싱한 엔트리 리스트를 `entries` 라 할 때:

```python
    # 헤더의 패턴 수는 손으로 적지 않는다 — 파싱한 실물 수를 찍는다.
    # (v2.6 에서 10건 늘었는데 "71" 이 남아 문서가 3곳에서 틀렸다.)
    header = header.replace("{PATTERN_COUNT}", str(len(entries)))
```

그리고 `skills/humanize-korean/references/` 의 헤더 템플릿(또는 스크립트 내 헤더 문자열)에서 `**71패턴 전수**` 를 `**{PATTERN_COUNT}패턴 전수**` 로 바꾼다.

- [ ] **Step 4: 산출물을 재생성하고 문서 3곳을 고친다**

```bash
python3 scripts/build_diagnosis_rules.py
```

`CLAUDE.md` — 프로젝트 개요 절:
- `10대 카테고리 70개 AI 티 패턴(+A-17 hold 1건)` → `10대 카테고리 활성 81 패턴`
- 에이전트 구성 절의 `10대분류 × 활성 70 패턴` → `10대분류 × 활성 81 패턴`

`skills/humanize-korean/SKILL.md` frontmatter `description`:
- `10대 카테고리 70개 AI 티 패턴을` → `10대 카테고리 81개 AI 티 패턴을`

> `description` 은 frontmatter 안이지만 `version:` 줄이 아니므로 `test_version_sync.py` 에 영향이 없다. 버전은 올리지 않는다.

- [ ] **Step 5: 테스트와 빌드 체크를 통과시킨다**

Run: `python3 -m pytest tests/test_pattern_count_sync.py -v && python3 scripts/build_diagnosis_rules.py --check && python3 scripts/build_quick_rules.py --check`
Expected: 3 passed · 두 `--check` 모두 exit 0

- [ ] **Step 6: 커밋**

```bash
git add tests/test_pattern_count_sync.py CLAUDE.md skills/humanize-korean/SKILL.md scripts/build_diagnosis_rules.py skills/humanize-korean/references/diagnosis-rules.md
git commit -m "fix(docs): 패턴 수 70/71 → 81 정정 + 카운트 drift 가드"
```

---

### Task 3: E-1 재framing — 불변량은 '장문 부재'가 아니라 '분산 부족'

Reinhart et al. 2025 (PNAS) 는 LLM 문장이 인간보다 **더 길다**고 보고하면서 동시에 **변이는 적다**고 한다. 버스티니스 문헌도 같다. 즉 언어 불변 축은 **dispersion** 이고, "장문 부재" 는 한국어에서의 발현형이다. 스파이크 영어 실측도 같았다(AI 에세이 stdev 6.7~6.8 vs 대조 16.3~18.8). 이 구분이 없으면 영어팩이 "장문을 늘려라"는 잘못된 처방을 물려받는다.

**Files:**
- Modify: `skills/humanize-korean/references/ai-tell-taxonomy.md` (E-1 항목)
- Modify: `skills/humanize-korean/references/diagnosis-rules.md` (재생성)
- Modify: `skills/humanize-korean/references/quick-rules.md` (재생성 — E-1 이 quick 이면)
- Create: `tests/test_e1_framing.py`

**Interfaces:**
- Consumes: `tests/test_pattern_count_sync.py::ssot_pattern_ids`
- Produces: 없음 (문서 변경)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_e1_framing.py`:

```python
"""E-1 의 실체 서술 회귀 — 언어 불변 축은 분산이지 장문 수가 아니다.

근거: Reinhart et al. 2025 (PNAS, arXiv:2410.16107) — LLM 문장은 인간보다
길면서 변이는 작다. 한국어의 "장문 부재"(G2=60.9)는 그 발현형이다.
영어팩이 "장문을 늘려라"는 잘못된 처방을 물려받지 않도록 서술을 못박는다.
"""
from __future__ import annotations

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_TAXONOMY = os.path.join(
    _ROOT, "skills", "humanize-korean", "references", "ai-tell-taxonomy.md"
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _e1_section(text: str) -> str:
    """E-1 헤딩부터 다음 E-2 헤딩 직전까지."""
    start = re.search(r"^#{3,4}\s+\*{0,2}E-1\b", text, re.M)
    assert start, "taxonomy 에서 E-1 헤딩을 찾지 못함"
    tail = text[start.start():]
    end = re.search(r"^#{3,4}\s+\*{0,2}E-2\b", tail, re.M)
    return tail[: end.start()] if end else tail


class E1FramingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.section = _e1_section(_read(_TAXONOMY))

    def test_names_dispersion_as_the_invariant(self) -> None:
        self.assertIn(
            "분산",
            self.section,
            "E-1 이 불변량으로서의 '분산'을 명시하지 않는다",
        )

    def test_marks_long_sentence_absence_as_korean_manifestation(self) -> None:
        """장문 부재는 유지하되, 한국어 발현형임이 드러나야 한다."""
        self.assertIn("장문", self.section)
        self.assertRegex(
            self.section,
            r"한국어[^\n]{0,40}발현|발현[^\n]{0,40}한국어",
            "장문 부재가 '한국어 발현형'으로 한정되지 않았다",
        )

    def test_cites_cross_language_evidence(self) -> None:
        self.assertIn(
            "Reinhart",
            self.section,
            "교차언어 근거(Reinhart 2025) 인용이 없다",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_e1_framing.py -v`
Expected: 3개 중 최소 2개 FAIL — `'분산'` 없음, `Reinhart` 없음.

- [ ] **Step 3: taxonomy 의 E-1 항목을 고친다**

`ai-tell-taxonomy.md:461` 의 현행 헤딩은 `### E-1. 문장 길이 표준편차 낮음 — 특히 장문 부재` 다.
헤딩 형식 `### {ID}. {제목} [{심각도}]` 는 **하우스 스타일이므로 유지한다** — 빌드 스크립트가 이 형식을 파싱한다.
**기존 근거 수치(G²=60.9, 인간 91.3 vs AI 8.1/1k)와 `_quick:` 메타는 그대로 둔다.**

```markdown
### E-1. 문장 길이 분산 부족 — 한국어 발현: 장문 부재 [S2]

- 패턴: 언어 불변 축은 **분산(dispersion)** 이다. AI 문장은 중앙값 부근에 몰려
  메트로놈처럼 균일하고, 사람은 짧은 평서문에 긴 절 문장을 섞어 "터진다".
- **'균일'이 아니라 '분산 부족'으로 읽어야 하는 이유**: Reinhart et al. 2025(PNAS,
  arXiv:2410.16107)는 LLM 문장이 인간보다 **더 길면서 변이는 작다**고 보고한다.
  즉 평균 길이는 방향이 언어·모델마다 뒤집힐 수 있고, 안정적인 것은 분산 쪽이다.
- **한국어에서의 발현형은 '장문 부재'** — 자체 실측에서 100자+ 문장이 사람 91.3 vs
  AI 8.1/1000문장(G²=60.9)으로 갈렸다. 처방도 이 발현형을 따른다.
- 영어 실측(스파이크 2026-09-02): AI 에세이 문장길이 표준편차 6.7~6.8 vs
  대조 16.3~18.8. 같은 축이 다른 발현형으로 재현됐다.
- 처방: 인접 문장 잇기로 장문을 회복한다. **내용 추가는 금지** — 없는 것을
  지어내는 처방은 철칙 #1 을 깬다(`core/principles.md` 결핍 신호 정책).
```

- [ ] **Step 4: 빌드 산출물을 재생성한다**

```bash
python3 scripts/build_diagnosis_rules.py && python3 scripts/build_quick_rules.py
```

- [ ] **Step 5: 전체 회귀를 통과시킨다**

Run: `python3 -m pytest tests/test_e1_framing.py tests/test_pattern_count_sync.py tests/test_diagnosis_rules_build.py tests/test_quick_rules_build.py -v && python3 scripts/build_diagnosis_rules.py --check && python3 scripts/build_quick_rules.py --check`
Expected: 전부 passed · 두 `--check` exit 0

- [ ] **Step 6: 커밋**

```bash
git add tests/test_e1_framing.py skills/humanize-korean/references/ai-tell-taxonomy.md skills/humanize-korean/references/diagnosis-rules.md skills/humanize-korean/references/quick-rules.md
git commit -m "fix(taxonomy): E-1 불변량을 분산으로 — 장문 부재는 한국어 발현형"
```

---

### Task 4: `change_rate` 를 `core/` 로 분리 — 언어 결합 해제

`scripts/verify_change_rate.py` 는 `skills/humanize-korean/references` 를 `sys.path` 에 넣어 `metrics_v2` 를 import 한다. 정작 쓰는 함수 `change_rate()` 는 문자 diff 라 언어와 무관하다 — 스파이크에서 영어에 무수정으로 돌아 12.8%·exit 0 을 냈다. 지금 구조로는 영어팩이 **한국어 스킬 디렉터리에 의존해야** 게이트를 쓸 수 있다.

**Files:**
- Create: `core/change_rate.py`
- Create: `tests/test_core_change_rate.py`
- Modify: `skills/humanize-korean/references/metrics_v2.py:642-694` (해당 블록을 재수출로 교체)
- Modify: `scripts/verify_change_rate.py:36-46` (import 경로)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `core/change_rate.py::change_rate(before: str, after: str, ignore_markup: bool = False) -> float`
  - `core/change_rate.py::CHANGE_RATE_WARN: float = 0.30`
  - `core/change_rate.py::CHANGE_RATE_ABORT: float = 0.50`
  - `metrics_v2` 는 위 셋을 재수출해 기존 import 를 전부 유지한다.
  - Task 5 와 R2 가 `core.change_rate` 를 직접 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_core_change_rate.py`:

```python
"""core/change_rate.py — 언어 무관 변경률. 한국어 스킬 디렉터리 없이 동작해야 한다.

배경: verify_change_rate.py 가 skills/humanize-korean/references 를 sys.path 에
넣어 metrics_v2 를 import 했다. 정작 쓰는 change_rate() 는 문자 diff 라
언어와 무관하다(영어 스파이크에서 무수정 동작 확인). 영어팩이 한국어 디렉터리에
의존하지 않도록 커널로 분리한다.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_CORE = os.path.join(_ROOT, "core", "change_rate.py")


def _load():
    spec = importlib.util.spec_from_file_location("_core_change_rate", _CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreChangeRateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_CORE), f"core/change_rate.py 가 없다: {_CORE}")
        self.m = _load()

    def test_identical_text_is_zero(self) -> None:
        self.assertEqual(self.m.change_rate("같은 글이다.", "같은 글이다."), 0.0)

    def test_english_input_works(self) -> None:
        """영어에서도 동작한다 — 스파이크가 실증한 언어 무관성."""
        before = "The office was the organizing principle of urban life."
        after = "The office organized urban life."
        rate = self.m.change_rate(before, after)
        self.assertGreater(rate, 0.0)
        self.assertLess(rate, 1.0)

    def test_korean_input_works(self) -> None:
        rate = self.m.change_rate(
            "이 문제에 있어서 중요한 것은 속도이다.", "이 문제에서 중요한 건 속도다."
        )
        self.assertGreater(rate, 0.0)
        self.assertLess(rate, 1.0)

    def test_thresholds_exported(self) -> None:
        self.assertEqual(self.m.CHANGE_RATE_WARN, 0.30)
        self.assertEqual(self.m.CHANGE_RATE_ABORT, 0.50)

    def test_ignore_markup_strips_structure(self) -> None:
        """마크업만 다른 두 글의 변경률은 무시 모드에서 0 이다."""
        before = "# 제목\n\n본문 한 줄."
        after = "## 제목\n\n본문 한 줄."
        self.assertEqual(self.m.change_rate(before, after, ignore_markup=True), 0.0)

    def test_no_korean_skill_dependency(self) -> None:
        """한국어 스킬 디렉터리가 sys.path 에 없어도 import 된다."""
        code = (
            "import importlib.util, sys;"
            f"spec = importlib.util.spec_from_file_location('m', {_CORE!r});"
            "m = importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(m);"
            "print(m.change_rate('a b c', 'a b d'))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class MetricsV2BackCompatTests(unittest.TestCase):
    """기존 import 경로가 그대로 살아 있어야 한다."""

    def test_metrics_v2_still_exports(self) -> None:
        refs = os.path.join(_ROOT, "skills", "humanize-korean", "references")
        if refs not in sys.path:
            sys.path.insert(0, refs)
        import metrics_v2  # noqa: PLC0415

        self.assertEqual(metrics_v2.CHANGE_RATE_WARN, 0.30)
        self.assertEqual(metrics_v2.CHANGE_RATE_ABORT, 0.50)
        self.assertEqual(metrics_v2.change_rate("가나다", "가나다"), 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_core_change_rate.py -v`
Expected: `CoreChangeRateTests` 전부 FAIL (`core/change_rate.py 가 없다`), `MetricsV2BackCompatTests` PASS.

- [ ] **Step 3: `core/change_rate.py` 를 만든다**

`skills/humanize-korean/references/metrics_v2.py` 의 642~694행(`CHANGE_RATE_WARN` 부터 `change_rate()` 끝까지)을 **그대로 옮긴다.** 로직은 한 글자도 바꾸지 않는다 — 이번 태스크는 이동이지 개선이 아니다.

```python
#!/usr/bin/env python3
"""변경률 — 철칙 #4 의 계측. 언어 무관(문자 diff).

metrics_v2.py 에서 분리했다. 영어 스파이크(2026-09-02)에서 이 함수가 무수정으로
영어에 동작함이 확인됐고(12.8%, gate exit 0), 언어팩이 한국어 스킬 디렉터리에
의존하지 않도록 커널로 올린다. metrics_v2 는 하위 호환을 위해 재수출한다.
"""
from __future__ import annotations

import difflib
import re

CHANGE_RATE_WARN = 0.30   # 30% 초과 — 경고, 과윤문 점검
CHANGE_RATE_ABORT = 0.50  # 50% 초과 — 강제 중단

# (이하 metrics_v2.py 642~694행의 _MARKUP_ONLY_LINE_RE, _MARKUP_PREFIX_RE,
#  _strip_markup(), change_rate() 를 그대로 옮긴다.)
```

> 옮길 정확한 범위는 `sed -n '642,694p' skills/humanize-korean/references/metrics_v2.py` 로 확인한다. 상수 2개 + 정규식 2개 + 함수 2개다.

- [ ] **Step 4: `metrics_v2.py` 를 재수출로 바꾼다**

옮긴 블록 자리에 넣는다:

```python
# 변경률은 언어 무관이라 core/ 로 올렸다(2026-09-02, 다국어 R1).
# 기존 import 경로를 깨지 않기 위해 재수출한다.
import os as _os
import sys as _sys

_CORE_DIR = _os.path.abspath(
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "..", "core")
)
if _CORE_DIR not in _sys.path:
    _sys.path.insert(0, _CORE_DIR)

from change_rate import (  # noqa: E402,F401
    CHANGE_RATE_ABORT,
    CHANGE_RATE_WARN,
    change_rate,
)
```

- [ ] **Step 5: `verify_change_rate.py` 가 커널을 쓰게 한다**

`scripts/verify_change_rate.py` 의 `_REFS` 블록(36~46행)을 교체한다:

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.abspath(os.path.join(_HERE, "..", "core"))
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

import change_rate as _m  # noqa: E402  (sys.path mutation is intentional)
```

`_m.change_rate(...)`·`_m.CHANGE_RATE_WARN`·`_m.CHANGE_RATE_ABORT` 호출부는 이름이 같으므로 수정 불필요하다. 파일 안에서 `_m.` 로 시작하는 다른 참조가 있는지 확인한다:

```bash
grep -n "_m\." scripts/verify_change_rate.py
```

`change_rate`·`CHANGE_RATE_WARN`·`CHANGE_RATE_ABORT` 외의 이름이 나오면 그 심볼도 `core/change_rate.py` 로 함께 옮긴다.

- [ ] **Step 6: 테스트와 실제 게이트 동작을 확인한다**

```bash
python3 -m pytest tests/test_core_change_rate.py tests/test_metrics_v2.py tests/test_metrics_v2_import.py tests/test_runtime_boundary.py -v
printf 'The office was the organizing principle of urban life.\n' > /tmp/a.txt
printf 'The office organized urban life.\n' > /tmp/b.txt
python3 scripts/verify_change_rate.py --before /tmp/a.txt --after /tmp/b.txt; echo "exit=$?"
```
Expected: 테스트 전부 passed · 게이트가 변경률 한 줄과 판정을 출력하고 exit 0~2 중 하나(3 이면 실행 오류다)

- [ ] **Step 7: 커밋**

```bash
git add core/change_rate.py tests/test_core_change_rate.py skills/humanize-korean/references/metrics_v2.py scripts/verify_change_rate.py
git commit -m "refactor(core): change_rate 를 커널로 분리 — 게이트의 한국어 결합 해제"
```

---

### Task 5: `core/metrics_universal.py` — 언어 무관 계측 지표

스파이크에서 가장 잘 분리한 것이 계측형 지표였다(AI 에세이 stdev 6.7~6.8 vs 대조 16.3~18.8). 산술이라 언어를 타지 않는다. 영어팩의 `route_hint` 는 이 층만으로 돌아간다 — 정규식이 못 잡는 것은 원래 LLM 몫이므로.

**Files:**
- Create: `core/metrics_universal.py`
- Create: `tests/test_metrics_universal.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `sentence_length_dispersion(text: str, unit: str = "tokens") -> float` — 문장 길이 모표준편차
  - `long_sentence_rate(text: str, threshold: int, unit: str = "tokens") -> float` — 임계 이상 문장 비율(%)
  - `comma_inclusion_rate(text: str) -> float` — 쉼표 1개 이상 포함 문장 비율(%)
  - `comma_segment_length(text: str) -> float` — 쉼표 분절 절의 평균 토큰 수
  - `compute_universal(text: str, *, long_threshold: int, unit: str) -> dict[str, float]`
  - R2 의 `metrics_en.py` 가 `compute_universal` 을 호출한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_metrics_universal.py`:

```python
"""core/metrics_universal.py — 언어 무관 계측 지표.

근거: 영어 스파이크(2026-09-02)에서 계측형 지표만이 깨끗하게 분리했다
(AI 에세이 문장길이 stdev 6.7~6.8 vs 대조 16.3~18.8). 산술이라 언어를 안 탄다.
한국어는 unit='chars'(100자 임계), 영어는 unit='tokens'(35어 임계)로 같은 축을 잰다.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "metrics_universal.py")

EN_UNIFORM = (
    "The office was the principle. "
    "The streets were laid out. "
    "The systems grew around it. "
    "That arrangement is now gone."
)
EN_BURSTY = (
    "It ended. "
    "For more than a century the office building was the organizing principle of "
    "urban life, and streets were laid out to carry workers toward it in the "
    "morning and away from it at night, while restaurants and transit systems and "
    "entire neighborhoods grew around the rhythm of that daily commute. "
    "Nobody planned it."
)


def _load():
    spec = importlib.util.spec_from_file_location("_metrics_universal", _MOD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DispersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"core/metrics_universal.py 가 없다: {_MOD}")
        self.m = _load()

    def test_uniform_text_has_low_dispersion(self) -> None:
        self.assertLess(self.m.sentence_length_dispersion(EN_UNIFORM), 3.0)

    def test_bursty_text_has_higher_dispersion(self) -> None:
        """스파이크가 실측한 방향 — 사람 글이 AI 글보다 분산이 크다."""
        self.assertGreater(
            self.m.sentence_length_dispersion(EN_BURSTY),
            self.m.sentence_length_dispersion(EN_UNIFORM),
        )

    def test_korean_chars_unit(self) -> None:
        """한국어는 문자 단위로 잰다 — 어절 수가 아니라 100자 임계가 SSOT다."""
        text = "짧다. " + "가" * 120 + ". 또 짧다."
        self.assertGreater(
            self.m.long_sentence_rate(text, threshold=100, unit="chars"), 0.0
        )

    def test_long_sentence_rate_zero_when_all_short(self) -> None:
        self.assertEqual(
            self.m.long_sentence_rate(EN_UNIFORM, threshold=35, unit="tokens"), 0.0
        )

    def test_comma_inclusion_rate(self) -> None:
        text = "One, two. Three. Four, five."
        self.assertAlmostEqual(self.m.comma_inclusion_rate(text), 200 / 3, places=1)

    def test_comma_segment_length(self) -> None:
        text = "a b c, d e f."
        self.assertAlmostEqual(self.m.comma_segment_length(text), 3.0, places=1)

    def test_compute_universal_returns_all_keys(self) -> None:
        out = self.m.compute_universal(EN_BURSTY, long_threshold=35, unit="tokens")
        for key in (
            "sentence_length_dispersion",
            "long_sentence_rate",
            "comma_inclusion_rate",
            "comma_segment_length",
            "sentences",
            "tokens",
        ):
            self.assertIn(key, out)

    def test_empty_text_does_not_crash(self) -> None:
        out = self.m.compute_universal("", long_threshold=35, unit="tokens")
        self.assertEqual(out["sentences"], 0)
        self.assertEqual(out["sentence_length_dispersion"], 0.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_metrics_universal.py -v`
Expected: 전부 FAIL — `core/metrics_universal.py 가 없다`.

- [ ] **Step 3: 구현한다**

`core/metrics_universal.py`:

```python
#!/usr/bin/env python3
"""언어 무관 계측 지표 — 분산·쉼표·길이 분포.

왜 커널인가: 영어 스파이크(2026-09-02)에서 어휘·정규식형 지표는 이식에 실패했으나
(C-8 첫 정규식 재현율 0/6) 계측형은 코드 수정 0으로 넘어갔고 가장 잘 분리했다
(AI 에세이 문장길이 stdev 6.7~6.8 vs 대조 16.3~18.8).

E-1 의 불변량은 '장문 부재'가 아니라 '분산 부족'이다(Reinhart et al. 2025, PNAS).
언어별 발현형은 unit 과 threshold 로 흡수한다 — 한국어 chars/100, 영어 tokens/35.

표준 라이브러리만. 형태소 분석 없음.
"""
from __future__ import annotations

import re
import statistics

# 마침표·물음표·느낌표 + 한중일 종지부. 뒤따르는 닫는 따옴표·괄호까지 문장에 포함.
_SENT_END_RE = re.compile(r'(?<=[.!?。！？…])[\'"”’」』)\]]*\s+')

# 어절/단어 = 공백 분리. 한국어 어절과 영어 word 를 같은 규칙으로 센다
# (metrics.py 의 _EOJEOL_SPLIT_RE 와 동일 관례). 공백 없는 표기 체계
# (중국어·일본어)는 이 함수의 사정거리 밖이다.
_WS_RE = re.compile(r"\s+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_END_RE.split(text) if s.strip()]


def _size(sentence: str, unit: str) -> int:
    if unit == "chars":
        return len(sentence)
    if unit == "tokens":
        return len([t for t in _WS_RE.split(sentence) if t])
    raise ValueError(f"unit 은 'chars' 또는 'tokens' — 받은 값: {unit!r}")


def sentence_length_dispersion(text: str, unit: str = "tokens") -> float:
    """문장 길이의 모표준편차. 낮을수록 메트로놈처럼 균일(AI 방향)."""
    sizes = [_size(s, unit) for s in split_sentences(text)]
    if len(sizes) < 2:
        return 0.0
    return round(statistics.pstdev(sizes), 2)


def long_sentence_rate(text: str, threshold: int, unit: str = "tokens") -> float:
    """임계 이상 문장의 비율(%). 한국어 chars/100, 영어 tokens/35 가 기본 대응."""
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if _size(s, unit) >= threshold)
    return round(hits / len(sentences) * 100, 2)


def comma_inclusion_rate(text: str) -> float:
    """쉼표를 1개 이상 포함한 문장의 비율(%). KatFish 인간 26% / LLM 61% 축."""
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if "," in s or "，" in s)
    return round(hits / len(sentences) * 100, 2)


def comma_segment_length(text: str) -> float:
    """쉼표로 분절된 절의 평균 토큰 수."""
    segments = []
    for sentence in split_sentences(text):
        for piece in re.split(r"[,，]", sentence):
            tokens = [t for t in _WS_RE.split(piece) if t]
            if tokens:
                segments.append(len(tokens))
    if not segments:
        return 0.0
    return round(statistics.mean(segments), 2)


def compute_universal(
    text: str, *, long_threshold: int, unit: str = "tokens"
) -> dict[str, float]:
    """전 지표를 한 번에. shim 이 route_hint 를 낼 때 쓰는 진입점."""
    sentences = split_sentences(text)
    tokens = [t for t in _WS_RE.split(text) if t]
    return {
        "sentences": len(sentences),
        "tokens": len(tokens),
        "sentence_length_dispersion": sentence_length_dispersion(text, unit),
        "long_sentence_rate": long_sentence_rate(text, long_threshold, unit),
        "comma_inclusion_rate": comma_inclusion_rate(text),
        "comma_segment_length": comma_segment_length(text),
    }
```

- [ ] **Step 4: 테스트 통과를 확인한다**

Run: `python3 -m pytest tests/test_metrics_universal.py -v`
Expected: 8 passed

- [ ] **Step 5: 스파이크 실측을 재현해 방향이 맞는지 확인한다**

```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('m', 'core/metrics_universal.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import pathlib
for f in ['README.en.md', 'docs/en/integration.md']:
    t = pathlib.Path(f).read_text(encoding='utf-8')
    print(f, m.compute_universal(t, long_threshold=35, unit='tokens'))
"
```
Expected: 두 파일 모두 `sentence_length_dispersion` 이 10 이상 (스파이크 측정 16.3~18.8 과 같은 자릿수). 마크다운 표를 걸러내지 않으므로 정확히 일치하지는 않는다 — **자릿수만 확인**한다.

- [ ] **Step 6: 커밋**

```bash
git add core/metrics_universal.py tests/test_metrics_universal.py
git commit -m "feat(core): 언어 무관 계측 지표 — 분산·장문율·쉼표 계열"
```

---

### Task 6: 전체 회귀 + CLAUDE.md 디렉터리 구조 갱신

**Files:**
- Modify: `CLAUDE.md` (디렉터리 구조 절 · 참고 절)

**Interfaces:**
- Consumes: Task 1~5 의 산출물 전부
- Produces: 없음 (R1 종료)

- [ ] **Step 1: CI 전체를 로컬에서 돌린다**

```bash
python3 -m pytest tests/ -v
python3 scripts/build_quick_rules.py --check
python3 scripts/build_diagnosis_rules.py --check
bash tests/test_install_flags.sh
```
Expected: 전부 통과. 실패가 나오면 그 태스크로 돌아가 고친다 — **여기서 테스트를 느슨하게 만들지 않는다.**

- [ ] **Step 2: `CLAUDE.md` 디렉터리 구조에 `core/` 를 넣는다**

디렉터리 구조 코드블록에서 `├── scripts/` 바로 위에 추가:

```
├── core/                          # 언어 무관 커널 (다국어 R1)
│   ├── principles.md              # 철칙 6 + 증거 기준 G1(전 모델 생존)·G2(과업 통제)·G3(역주입 금지)
│   ├── change_rate.py             # 변경률 — 문자 diff, metrics_v2 에서 분리
│   └── metrics_universal.py       # 분산·장문율·쉼표 계열 — 산술 지표
```

`## 참고` 절 맨 앞에 추가:

```markdown
- 언어 무관 원리·증거 기준: `core/principles.md`
- 다국어 확장 설계: `docs/superpowers/specs/2026-09-02-multilingual-design.md`
```

- [ ] **Step 3: 문서 변경 후 회귀를 다시 확인한다**

Run: `python3 -m pytest tests/test_pattern_count_sync.py tests/test_principles_contract.py -v`
Expected: passed (CLAUDE.md 를 고쳤으므로 카운트 가드가 여전히 통과하는지 확인)

- [ ] **Step 4: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs(claude): core/ 커널 디렉터리 반영"
```

---

## R1 자체 점검

- **Spec coverage** — 설계 §2.2(증거 기준 G1·G2·G3) → Task 1. §2.1 이식 가치 순위 → Task 1 문서에 수록. §1.4(E-1 재framing) → Task 3. §R1 부수 정정(패턴 수) → Task 2. §2.3 `core/` 디렉터리 중 `principles.md`·`change_rate.py`·`metrics_universal.py` → Task 1·4·5. **미포함**: §2.4 탐지 어댑터·§2.5 영어 baseline·§2.6 규칙 출발 세트 — 전부 R2 소관(아래 예고 참조).
- **타입 정합** — `change_rate(before, after, ignore_markup=False)` 는 Task 4 정의 그대로 Task 5 이후·R2 에서 쓰인다. `compute_universal(text, *, long_threshold, unit)` 은 Task 5 정의가 R2 `metrics_en.py` 의 유일한 진입점이다.
- **의도적 제외** — R1 은 버전을 올리지 않는다. 매니페스트 3종·`install.sh` 는 손대지 않는다(새 배포물이 없으므로). 버전 승급은 R2 에서 새 스킬과 함께 한다.

---

## 다음 계획 예고 — R2 (영어 스킬 신설)

**이 계획에 포함하지 않는 이유:** R2 의 태스크 분해는 R1 이 만든 `core/` 경계가 실제로 어떤 모양인지에 달려 있다. 우리가 D1-C 이래 계속 적용해온 원칙과 같다 — 두 번째 사례를 만들기 전에 경계를 상상으로 긋지 않는다. R1 이 머지된 뒤 `writing-plans` 를 다시 돌려 태스크마다 실제 코드를 채운다.

예상 태스크 (분해만, 코드는 R2 계획에서):

1. `skills/humanize-english/SKILL.md` — light/standard 2경로만. heavy·finalize 는 닫는다(증적을 주장할 근거가 아직 얕다)
2. `skills/humanize-english/references/ai-tell-taxonomy.md` — Tier A(C-8·F-7·E-1 dispersion·F-4·G-1/G-2·A-9) + Tier B(구조·서식 7종). 각 항목 `evidence:` 라벨 필수
3. `skills/humanize-english/references/baseline.json` — 발표 수치 인용(Kobak 291 excess words · Reinhart Biber 방향 · SlopDetector em dash). em dash 는 **G1 미통과로 관측 지표 전용** 표기
4. `metrics_en.py` — `core.metrics_universal.compute_universal` 호출 + Kobak lexicon 히트. 정규식은 어휘 단위만, 통사 프레임은 LLM 콜에 위임
5. `prepare_monolith_input.py --lang en` 배선 + 유니코드 스크립트 비율 기반 언어 감지
6. `install.sh`·매니페스트 3종·버전 승급 + `test_plugin_manifests.py`·`test_version_sync.py` 확장
7. 영어 golden 픽스처 + G3(역주입) 회귀 — 스파이크에서 em dash 2→5 를 잡아낸 그 검사를 자동화
