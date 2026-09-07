# R2a — 영어 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 영어 텍스트를 넣으면 shim 이 `route_hint` 를 내고, 영어 룰북으로 윤문한 결과를 결정적 게이트가 판정하는 **동작하는 경로**를 만든다.

**Architecture:** 스킬을 새로 만들지 않는다(그건 R2b 배관). 저장소 루트 `lang/en/` 에 데이터(렉시콘·룰북)와 `metrics_en.py` 를 두고, 기존 shim 에 `--lang` 을 단다. 영어 route_hint 는 **정규식이 아니라 `core/metrics_universal.py`(분산·쉼표) + 렉시콘 히트**로 낸다 — 스파이크에서 영어 정규식 재현율이 0/6 이었고 계측형만 이식됐기 때문이다. 이 작업이 R1 에서 만든 `metrics_universal` 의 **첫 실사용처**다(현재 호출자 0곳).

**Tech Stack:** Python 3.11+ 표준 라이브러리만. 새 의존성 금지(spaCy·pybiber 도입하지 않는다 — 설계 §2.4).

**Spec:** `docs/superpowers/specs/2026-09-02-multilingual-design.md`
**선행:** `docs/spikes/2026-09-02-en-transplant.md` · `core/principles.md`

## Global Constraints

- **stdlib only.** CI 의 유일한 설치 의존성은 pytest 다.
- **한국어 경로 무변경.** `--lang` 기본값은 `ko` 이고, 미지정 시 현행 동작과 **바이트 단위로 동일**해야 한다. 회귀는 `tests/test_route_hint.py` 가 지킨다.
- **근거 등급 표기 필수.** 영어 규칙·수치는 `core/principles.md` 「근거 등급 (E1~E4)」에 따라 등급을 단다. **영어에는 E1 이 하나도 없다** — 그래서 heavy·finalize 경로를 열지 않는다.
- **수치를 지어내지 않는다.** Kobak 어휘 목록은 공개 저장소에서 받아온다. 기억으로 채우지 않는다(Task 1 Step 1 참조).
- **런타임 경계.** `lang/` 은 프로덕션 런타임이다 — `tests/test_runtime_boundary.py` 의 배포 서브셋에 포함시킨다(`core/` 를 넣었던 것과 같은 이유).
- 로컬 검증 명령(이 머신엔 pytest 가 없다): `python3 -m unittest tests.<module>`
- CI 재현: `python3 -m unittest discover -s tests -p 'test_*.py'` + `build_quick_rules.py --check` + `build_diagnosis_rules.py --check` + `bash tests/test_install_flags.sh`

## 범위 밖 (R2b 로 미룸)

새 스킬 디렉터리 · `.claude-plugin/*.json`·`plugin.json`·marketplace 갱신 · `install.sh` ·
버전 승급 · `test_plugin_manifests.py`/`test_version_sync.py` 확장. 전부 배관이며
엔진이 도는 것을 확인한 뒤에 한다.

---

### Task 1: 영어 렉시콘 — Kobak 초과 어휘 (실제 목록 확보)

영어 어휘 티의 근거는 Kobak et al. 2025 (Science Advances) 다. **2024 초과 어휘의 66% 가 동사**라는 발견이 한국어 F-7(범용 동사 수렴 3.4배)과 같은 모양이라 교차언어 확인이 된 항목이다. 목록은 반드시 공개 저장소에서 받는다.

**Files:**
- Create: `lang/en/lexicon.json`
- Create: `tests/test_en_lexicon.py`

**Interfaces:**
- Produces: `lang/en/lexicon.json` — 최상위 키 `version`·`source`·`evidence`·`entries`.
  `entries` 는 `{"word": str, "family": str, "pos": str｜null, "ratio": float｜null}` 배열.
  `family` 는 본진 ID(`F-7`·`D-4`·`F-1` 등) 또는 `unclassified`.
  Task 2 의 `metrics_en.py` 가 이 파일을 읽는다.

- [ ] **Step 1: 실제 목록을 받아온다 (기억으로 채우지 않는다)**

```bash
mkdir -p lang/en
curl -sSL -o /tmp/kobak_repo.txt \
  "https://api.github.com/repos/berenslab/llm-excess-vocab/git/trees/main?recursive=1"
python3 -c "import json;print('\n'.join(p['path'] for p in json.load(open('/tmp/kobak_repo.txt'))['tree'] if p['path'].endswith(('.csv','.json','.txt'))))"
```

받은 목록에서 style words 파일(예: `data/` 아래 excess-vocabulary CSV)을 찾아 내려받는다.
**받아지지 않으면 여기서 멈추고 사람에게 알린다** — 목록을 추측으로 만들면 이 저장소의
증거 기준(E1~E4)을 정면으로 어긴다. 대안은 논문 본문 Fig. S6 확인이다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_en_lexicon.py`:

```python
"""lang/en/lexicon.json 계약 — 영어 어휘 티 사전.

근거: Kobak et al. 2025 (Science Advances), PubMed 초록 15M편 2010–2024 의
excess vocabulary. 2024 초과 어휘의 66%가 동사로, 한국어 F-7(범용 동사 수렴)과
같은 모양이다. 등급 E2(본문 표 미확인 — 공개 저장소 목록 사용).
"""
from __future__ import annotations

import json
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_LEXICON = os.path.join(_ROOT, "lang", "en", "lexicon.json")

_ALLOWED_FAMILIES = {
    "F-7", "D-4", "F-1", "A-15", "D-2", "G-1", "B-2", "unclassified",
}


def _load() -> dict:
    with open(_LEXICON, encoding="utf-8") as f:
        return json.load(f)


class EnLexiconTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_LEXICON), f"없다: {_LEXICON}")
        self.data = _load()

    def test_has_provenance(self) -> None:
        """출처와 근거 등급이 파일 안에 있어야 한다 — 나중에 누가 등급을 물어본다."""
        self.assertIn("source", self.data)
        self.assertIn("Kobak", self.data["source"])
        self.assertRegex(self.data["evidence"], r"^E[1-4]\b")

    def test_entries_are_wellformed(self) -> None:
        entries = self.data["entries"]
        self.assertGreaterEqual(len(entries), 40, "표본이 너무 적다")
        seen = set()
        for e in entries:
            self.assertIn("word", e)
            self.assertNotIn(e["word"], seen, f"중복 표제어: {e['word']}")
            seen.add(e["word"])
            self.assertEqual(e["word"], e["word"].lower(), "표제어는 소문자")
            self.assertIn(e["family"], _ALLOWED_FAMILIES, f"미정의 family: {e}")

    def test_known_markers_present(self) -> None:
        """논문이 명시적으로 든 대표 초과어가 들어 있어야 한다."""
        words = {e["word"] for e in self.data["entries"]}
        for w in ("delve", "underscore", "showcase", "intricate", "pivotal"):
            self.assertIn(w, words, f"대표 초과어 누락: {w}")

    def test_verb_majority(self) -> None:
        """Kobak 의 핵심 발견 — 초과 어휘는 동사가 다수다(2024 기준 66%)."""
        pos = [e.get("pos") for e in self.data["entries"] if e.get("pos")]
        self.assertGreaterEqual(len(pos), 20, "pos 태깅이 너무 적다")
        verbs = sum(1 for p in pos if p == "verb")
        self.assertGreater(verbs / len(pos), 0.4, f"동사 비율 {verbs}/{len(pos)}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 실패를 확인한다**

Run: `python3 -m unittest tests.test_en_lexicon -v`
Expected: `setUp` 에서 `없다: .../lang/en/lexicon.json`.

- [ ] **Step 4: `lang/en/lexicon.json` 을 만든다**

Step 1 에서 받은 목록을 스키마로 변환한다. 표제어는 **원형(lemma)** 으로 넣고
(`delves`→`delve`), 어미 변형은 Task 2 의 매처가 접미사로 흡수한다.
`family` 배정 기준:

| family | 무엇 | 예 |
|---|---|---|
| `F-7` | 범용 동사 수렴 (한국어 F-7 과 동형) | delve, underscore, showcase, leverage, foster |
| `D-4` | hype 형용사 | groundbreaking, revolutionary, unprecedented |
| `F-1` | 정도부사·강조 | meticulously, remarkably, profoundly |
| `A-15` | 추상 주어 + 만능 동사 | highlight, reflect, exemplify |
| `unclassified` | 본진 대응이 불분명 | realm, tapestry |

```json
{
  "version": "0.1",
  "source": "Kobak et al. 2025, Delving into LLM-assisted writing in biomedical publications through excess vocabulary (Science Advances). 목록: github.com/berenslab/llm-excess-vocab",
  "evidence": "E2 — 동료심사 발표, 본문 표는 미확인(공개 저장소 목록 사용). core/principles.md 「근거 등급」 참조",
  "caveat": "코퍼스가 생의학 초록이다. 논설·에세이 장르의 임계가 아니라 방향 근거로만 쓴다.",
  "entries": [
    {"word": "delve", "family": "F-7", "pos": "verb", "ratio": 28.0},
    {"word": "underscore", "family": "F-7", "pos": "verb", "ratio": 13.8},
    {"word": "showcase", "family": "F-7", "pos": "verb", "ratio": 10.7}
  ]
}
```

(위는 스키마 예시다. `entries` 는 Step 1 에서 받은 전체 목록으로 채운다.)

- [ ] **Step 5: 테스트를 통과시킨다**

Run: `python3 -m unittest tests.test_en_lexicon -v`
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add lang/en/lexicon.json tests/test_en_lexicon.py
git commit -m "feat(lang/en): Kobak 초과 어휘 렉시콘 — 근거 등급 E2 명시"
```

---

### Task 2: `lang/en/metrics_en.py` — 영어 route_hint

`core/metrics_universal.py` 의 **첫 실사용처**다. 영어 route_hint 는 정규식 티 카운트가 아니라 계측형 지표 + 렉시콘 히트로 낸다.

**Files:**
- Create: `lang/en/metrics_en.py`
- Create: `tests/test_metrics_en.py`

**Interfaces:**
- Consumes: `core.metrics_universal.compute_universal(text, long_threshold=35, unit="tokens")` · `lang/en/lexicon.json`
- Produces:
  - `lexicon_hits(text: str, lexicon: dict) -> tuple[int, dict[str, int]]` — (총합, family별)
  - `compute_all_en(text: str, lexicon_path: str | None = None) -> dict` — `char_count`·`universal`·`lexicon`·`route_hint`·`route_reason`·`route_signals` 를 담은 dict
  - Task 3 의 shim 이 `compute_all_en` 만 호출한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_metrics_en.py`:

```python
"""lang/en/metrics_en.py — 영어 route_hint.

영어는 정규식 티 탐지가 이식되지 않는다(스파이크 C-8 첫 재현율 0/6).
따라서 route_hint 는 계측형(분산·쉼표) + 렉시콘 히트로 낸다.
계측형은 스파이크에서 유일하게 깨끗하게 분리한 축이다
(AI 에세이 stdev 6.7~6.8 vs 대조 16.3~18.8).
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "lang", "en", "metrics_en.py")

# 균일 + 렉시콘 다수 = AI 슬롭
SLOP = (
    "This underscores a pivotal shift. It delves into the intricate landscape. "
    "The findings showcase remarkable potential. This is crucial for the realm. "
    "It highlights meticulously curated insights. The results are groundbreaking."
)
# 분산 크고 렉시콘 0 = 사람 글
HUMAN = (
    "It ended. "
    "For more than a century the office building was the organizing principle of "
    "urban life, and streets were laid out to carry workers toward it in the "
    "morning and away from it at night, while restaurants and transit systems and "
    "entire neighborhoods grew around the rhythm of that daily commute. "
    "Nobody planned it that way."
)


def _load():
    spec = importlib.util.spec_from_file_location("_metrics_en", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class MetricsEnTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def test_lexicon_hits_counts_inflections(self) -> None:
        """표제어는 원형이지만 굴절형도 잡아야 한다(delve/delves/delving)."""
        lex = self.m.load_lexicon()
        total, per = self.m.lexicon_hits("It delves and is delving and delved.", lex)
        self.assertGreaterEqual(total, 3, f"굴절형 누락: {per}")

    def test_lexicon_does_not_match_substrings(self) -> None:
        """'underscore' 가 'thunderscored' 같은 부분문자열을 잡으면 안 된다."""
        lex = self.m.load_lexicon()
        total, _ = self.m.lexicon_hits("The delvedelve xdelve thunderscore.", lex)
        self.assertEqual(total, 0)

    def test_slop_and_human_differ(self) -> None:
        slop = self.m.compute_all_en(SLOP)
        human = self.m.compute_all_en(HUMAN)
        self.assertGreater(slop["lexicon"]["total"], human["lexicon"]["total"])
        self.assertGreater(
            human["universal"]["sentence_length_dispersion"],
            slop["universal"]["sentence_length_dispersion"],
        )

    def test_route_hint_is_valid_value(self) -> None:
        for text in (SLOP, HUMAN, "", "One short line."):
            hint = self.m.compute_all_en(text)["route_hint"]
            self.assertIn(hint, ("light", "standard", "heavy"))

    def test_heavy_never_from_length_alone(self) -> None:
        """한국어와 같은 규약 — 15,000자 초과만 길이로 heavy."""
        out = self.m.compute_all_en("This is a plain sentence. " * 200)
        self.assertNotEqual(out["route_hint"], "heavy")

    def test_long_input_goes_heavy(self) -> None:
        out = self.m.compute_all_en("This is a plain sentence. " * 700)
        self.assertGreater(out["char_count"], 15000)
        self.assertEqual(out["route_hint"], "heavy")

    def test_signals_are_reported(self) -> None:
        out = self.m.compute_all_en(SLOP)
        for key in ("lexicon_total", "dispersion", "comma_inclusion_rate", "char_count"):
            self.assertIn(key, out["route_signals"])

    def test_empty_text_does_not_crash(self) -> None:
        out = self.m.compute_all_en("")
        self.assertEqual(out["char_count"], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m unittest tests.test_metrics_en -v`
Expected: 8개 전부 FAIL (`없다: .../lang/en/metrics_en.py`).

- [ ] **Step 3: 구현한다**

`lang/en/metrics_en.py`:

```python
#!/usr/bin/env python3
"""영어 정량 지표 + route_hint.

한국어와 다른 점: 정규식 티 탐지에 기대지 않는다. 영어 스파이크(2026-09-02)에서
C-8 대구 정규식의 첫 재현율이 0/6 이었다 — 한국어는 교착어라 티가 형태소에
고정되지만 영어는 같은 수사를 여러 통사 프레임으로 흩뿌린다. 그래서 결정적
사전 채점은 **계측형 + 렉시콘**만 하고, 통사 프레임 탐지는 윤문 콜에 맡긴다.

근거 등급: 렉시콘 E2(Kobak) · 계측 임계 E3(자체 스파이크 1회). E1 없음 —
그래서 heavy 는 길이로만 나오고, finalize 경로는 열지 않는다.

표준 라이브러리만.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.abspath(os.path.join(_HERE, "..", "..", "core"))
if _CORE not in sys.path:
    sys.path.insert(0, _CORE)

from metrics_universal import compute_universal  # noqa: E402

# 영어 장문 임계 — 35 단어. 한국어 100자에 대응하는 발현형 임계다
# (E-1 의 불변량은 분산이고 임계는 언어별, taxonomy E-1 참조).
LONG_SENTENCE_TOKENS = 35

# 한국어 shim 과 같은 규약 — 길이로 heavy 가 되는 유일한 조건.
ROUTE_HEAVY_MIN_CHARS = 15000

# 렉시콘 히트 임계(/1000 tokens). E3 — 자체 스파이크 1회에서 나온 잠정값이다.
# 스파이크 AI 에세이의 F-7 계열이 5.14/1k, 사람 검수 문서가 0.00/1k 였다.
LIGHT_MAX_LEXICON_PER_1K = 1.5
HEAVY_MIN_LEXICON_PER_1K = 6.0

# 분산 임계. 스파이크: AI 에세이 6.7~6.8 vs 대조 16.3~18.8.
# 보수적으로 8.0 을 "균일하다"의 경계로 둔다(중간대는 standard 로 흘린다).
UNIFORM_DISPERSION_MAX = 8.0

# 굴절 접미사 — 형태소 분석기 없이 원형 표제어로 굴절형을 잡는다.
# ponytail: 규칙 기반 근사. 불규칙 동사가 필요해지면 그때 사전을 붙인다.
_SUFFIXES = ("", "s", "es", "d", "ed", "ing", "ly", "ness", "ment")


def load_lexicon(path: str | None = None) -> dict:
    with open(path or os.path.join(_HERE, "lexicon.json"), encoding="utf-8") as f:
        return json.load(f)


def _build_matcher(lexicon: dict) -> re.Pattern:
    stems = sorted(
        {e["word"] for e in lexicon["entries"]}, key=len, reverse=True
    )
    # 어간 + 굴절 접미사, 단어 경계로 감싼다(부분문자열 오탐 차단).
    alt = "|".join(re.escape(s) for s in stems)
    suf = "|".join(sorted(set(_SUFFIXES), key=len, reverse=True))
    return re.compile(rf"\b(?:{alt})(?:{suf})\b", re.I)


def lexicon_hits(text: str, lexicon: dict) -> tuple[int, dict[str, int]]:
    """총 히트 수와 family 별 분해."""
    fam_of = {e["word"]: e["family"] for e in lexicon["entries"]}
    matcher = _build_matcher(lexicon)
    per: dict[str, int] = {}
    total = 0
    for m in matcher.finditer(text):
        token = m.group(0).lower()
        stem = next(
            (w for w in sorted(fam_of, key=len, reverse=True) if token.startswith(w)),
            None,
        )
        fam = fam_of.get(stem, "unclassified") if stem else "unclassified"
        per[fam] = per.get(fam, 0) + 1
        total += 1
    return total, per


def compute_all_en(text: str, lexicon_path: str | None = None) -> dict:
    """영어 정량 점수 + route_hint. shim 의 유일한 진입점."""
    universal = compute_universal(
        text, long_threshold=LONG_SENTENCE_TOKENS, unit="tokens"
    )
    lexicon = load_lexicon(lexicon_path)
    total, per = lexicon_hits(text, lexicon)
    tokens = universal["tokens"] or 1
    per_1k = round(total / tokens * 1000, 2)
    chars = len(text)
    dispersion = universal["sentence_length_dispersion"]

    if chars > ROUTE_HEAVY_MIN_CHARS:
        hint = "heavy"
        reason = f"{chars:,} chars (>{ROUTE_HEAVY_MIN_CHARS:,}) — 초장문"
    elif per_1k >= HEAVY_MIN_LEXICON_PER_1K and dispersion <= UNIFORM_DISPERSION_MAX:
        hint = "heavy"
        reason = (
            f"렉시콘 {per_1k}/1k + 분산 {dispersion} — 어휘 티 밀집 + 리듬 균일"
        )
    elif per_1k <= LIGHT_MAX_LEXICON_PER_1K and dispersion > UNIFORM_DISPERSION_MAX:
        hint = "light"
        reason = f"렉시콘 {per_1k}/1k · 분산 {dispersion} — 이미 잘 쓴 글"
    else:
        hint = "standard"
        reason = f"렉시콘 {per_1k}/1k · 분산 {dispersion} — 진단 + 단일 윤문"

    return {
        "lang": "en",
        "char_count": chars,
        "universal": universal,
        "lexicon": {"total": total, "per_1k": per_1k, "by_family": per},
        "route_hint": hint,
        "route_reason": reason,
        "route_signals": {
            "lexicon_total": total,
            "lexicon_per_1k": per_1k,
            "dispersion": dispersion,
            "long_sentence_rate": universal["long_sentence_rate"],
            "comma_inclusion_rate": universal["comma_inclusion_rate"],
            "char_count": chars,
        },
        "evidence_note": (
            "렉시콘 E2(Kobak, 생의학 초록) · 임계 E3(자체 스파이크 1회). "
            "E1 없음 — heavy 는 길이 기준에서만 신뢰한다."
        ),
    }
```

- [ ] **Step 4: 테스트를 통과시킨다**

Run: `python3 -m unittest tests.test_metrics_en -v`
Expected: 8 passed.
`test_heavy_never_from_length_alone` 이 실패하면 임계가 너무 공격적인 것이다 —
**테스트를 느슨하게 하지 말고** `HEAVY_MIN_LEXICON_PER_1K` 를 올린다.

- [ ] **Step 5: 스파이크 표본으로 방향을 확인한다**

```bash
python3 -c "
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location('m','lang/en/metrics_en.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for f in ['README.en.md','docs/en/integration.md']:
    o = m.compute_all_en(pathlib.Path(f).read_text(encoding='utf-8'))
    print(f, o['route_hint'], o['route_signals'])
"
```
Expected: 사람이 검수한 기술 문서이므로 `heavy` 가 나오면 안 된다. 나오면 임계를 재조정하고 그 근거를 `evidence_note` 에 적는다.

- [ ] **Step 6: 커밋**

```bash
git add lang/en/metrics_en.py tests/test_metrics_en.py
git commit -m "feat(lang/en): 영어 route_hint — 계측형 + 렉시콘 (정규식 비의존)"
```

---

### Task 3: shim `--lang` 배선 + 언어 자동 감지

**Files:**
- Create: `core/detect_language.py`
- Create: `tests/test_detect_language.py`
- Modify: `scripts/prepare_monolith_input.py` (argparse `--lang` 추가 · `main()` 분기)
- Modify: `tests/test_runtime_boundary.py` (배포 서브셋에 `lang/` 추가)

**Interfaces:**
- Consumes: `lang/en/metrics_en.compute_all_en`
- Produces:
  - `core/detect_language.py::detect_language(text: str) -> str` — `"ko"` | `"en"` | `"unknown"`
  - shim CLI 인자 `--lang {auto,ko,en}` (기본 `auto`)
  - `00_metrics.json` 에 `lang` 필드 추가

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_detect_language.py`:

```python
"""core/detect_language.py — 유니코드 스크립트 비율 기반 언어 감지.

형태소 분석도 통계 모델도 쓰지 않는다. 한글 음절 블록과 라틴 문자의 비율만
보면 ko/en 은 갈린다. 셋째 언어가 필요해지면 그때 확장한다(ponytail).
"""
from __future__ import annotations

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "detect_language.py")


def _load():
    spec = importlib.util.spec_from_file_location("_detect_language", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DetectLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.d = _load().detect_language

    def test_korean(self) -> None:
        self.assertEqual(self.d("이 문제에서 중요한 건 속도다."), "ko")

    def test_english(self) -> None:
        self.assertEqual(self.d("The office organized urban life."), "en")

    def test_korean_with_english_terms_is_korean(self) -> None:
        """전문용어 병기가 많아도 한국어다 — B-1 이 잡는 그 문체."""
        text = (
            "소버린 AI(Sovereign AI)는 데이터 주권(data sovereignty)과 "
            "컴퓨팅 인프라(computing infrastructure)를 함께 요구한다."
        )
        self.assertEqual(self.d(text), "ko")

    def test_english_with_quoted_korean_is_english(self) -> None:
        text = (
            "The Korean term is 번역투, and it describes syntax carried over "
            "from another language into Korean prose by a literal translation."
        )
        self.assertEqual(self.d(text), "en")

    def test_empty_is_unknown(self) -> None:
        self.assertEqual(self.d(""), "unknown")

    def test_digits_and_punctuation_only_is_unknown(self) -> None:
        self.assertEqual(self.d("1234 5678 ... ---"), "unknown")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m unittest tests.test_detect_language -v`
Expected: 6 FAIL (`없다`).

- [ ] **Step 3: `core/detect_language.py` 를 만든다**

```python
#!/usr/bin/env python3
"""언어 감지 — 유니코드 스크립트 비율.

통계 모델도 의존성도 쓰지 않는다. 한글 음절 블록 대 라틴 문자의 비율만으로
ko/en 은 갈린다. 한국어 글은 전문용어 병기(B-1)로 라틴 문자가 섞이므로
"한글이 조금이라도 유의하게 있으면 한국어"로 판정한다 — 반대 방향(영어 글에
한국어 인용)은 비율이 훨씬 낮게 나온다.

셋째 언어가 필요해지면 그때 확장한다.
"""
from __future__ import annotations

import re

_HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_LATIN_RE = re.compile(r"[A-Za-z]")

# 한글 비율이 이 값을 넘으면 한국어. 병기가 많은 한국어 글에서도
# 한글은 보통 40% 이상이고, 한국어를 인용하는 영어 글은 5% 미만이다.
KO_MIN_RATIO = 0.15


def detect_language(text: str) -> str:
    hangul = len(_HANGUL_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    total = hangul + latin
    if total == 0:
        return "unknown"
    if hangul / total >= KO_MIN_RATIO:
        return "ko"
    if latin:
        return "en"
    return "unknown"
```

- [ ] **Step 4: 테스트를 통과시킨다**

Run: `python3 -m unittest tests.test_detect_language -v`
Expected: 6 passed

- [ ] **Step 5: shim 에 `--lang` 을 단다**

`scripts/prepare_monolith_input.py` 의 argparse 에 추가:

```python
    ap.add_argument(
        "--lang",
        choices=("auto", "ko", "en"),
        default="auto",
        help="입력 언어. auto 는 유니코드 스크립트 비율로 감지(기본). "
             "ko 는 현행 한국어 경로와 완전히 동일하게 동작한다.",
    )
```

`main()` 에서 metrics 계산 직전에 분기한다. **`ko` 경로는 한 줄도 바꾸지 않는다:**

```python
    lang = args.lang
    if lang == "auto":
        sys.path.insert(0, str(PROJECT_ROOT / "core"))
        from detect_language import detect_language  # noqa: PLC0415
        lang = detect_language(text)
        if lang == "unknown":
            lang = "ko"  # 판정 불가 시 현행 동작 유지 — 회귀 없음

    if lang == "en":
        sys.path.insert(0, str(PROJECT_ROOT / "lang" / "en"))
        from metrics_en import compute_all_en  # noqa: PLC0415
        metrics_obj = compute_all_en(text)
        metrics_obj["lang"] = "en"
    else:
        # (기존 한국어 경로 — 변경 없음)
        ...
        metrics_obj["lang"] = "ko"
```

- [ ] **Step 6: `lang/` 을 배포 서브셋에 넣는다**

`tests/test_runtime_boundary.py` 의 `test_verify_gates_runs_without_tests_dir` 에서
`core/` 를 복사하는 블록 바로 뒤에 추가:

```python
            # lang/ 도 프로덕션 런타임이다(R2a) — core/ 와 같은 이유.
            for sub in ("en",):
                lang_dst = d / "lang" / sub
                lang_dst.mkdir(parents=True)
                for f in (_ROOT / "lang" / sub).iterdir():
                    if f.is_file():
                        (lang_dst / f.name).write_bytes(f.read_bytes())
```

- [ ] **Step 7: 한국어 무회귀 + 영어 동작을 함께 확인한다**

```bash
python3 -m unittest tests.test_route_hint tests.test_run_dir_resolution \
  tests.test_chunking tests.test_detect_language tests.test_runtime_boundary -v 2>&1 | tail -5

mkdir -p /tmp/enrun && printf 'This underscores a pivotal shift. It delves into the intricate landscape. The findings showcase remarkable potential.\n' > /tmp/enrun/01_input.txt
python3 scripts/prepare_monolith_input.py --run-dir /tmp/enrun --genre column
python3 -c "import json;d=json.load(open('/tmp/enrun/00_metrics.json'));print(d['lang'], d['route_hint'], d['route_reason'])"
```
Expected: 한국어 테스트 전부 통과 · 영어 입력이 `en` 으로 감지되고 route_hint 가 나온다.

- [ ] **Step 8: 커밋**

```bash
git add core/detect_language.py tests/test_detect_language.py scripts/prepare_monolith_input.py tests/test_runtime_boundary.py
git commit -m "feat(shim): --lang + 언어 자동 감지 — 영어 입력이 route_hint 를 받는다"
```

---

### Task 4: `lang/en/quick-rules.md` — 영어 룰북 (Tier A + B)

**Files:**
- Create: `lang/en/quick-rules.md`
- Create: `tests/test_en_rulebook.py`

**Interfaces:**
- Produces: 규칙마다 `evidence:` 줄이 달린 마크다운 룰북. 윤문 콜의 `quick_rules_path` 로 넘긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_en_rulebook.py`:

```python
"""lang/en/quick-rules.md 계약 — 영어 룰북.

설계 §2.6: Tier A(외부 근거 + ko 실측 양쪽) + Tier B(구조·서식).
**제외 대상이 실제로 빠져 있는지**가 핵심 — em dash 는 G1 미통과이고,
H-1·H-3·G-3·D-4 는 한국어에서도 근거가 흔들린다.
"""
from __future__ import annotations

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_RULEBOOK = os.path.join(_ROOT, "lang", "en", "quick-rules.md")

TIER_A = ("C-8", "F-7", "E-1", "F-4", "G-1", "G-2", "A-9")
TIER_B = ("C-1", "C-2", "C-3", "C-5", "C-6", "C-9", "C-10")
EXCLUDED = ("J-3", "H-1", "H-3", "G-3", "D-4")


def _read() -> str:
    with open(_RULEBOOK, encoding="utf-8") as f:
        return f.read()


class EnRulebookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_RULEBOOK), f"없다: {_RULEBOOK}")
        self.text = _read()
        self.ids = set(re.findall(r"^\|\s*\*\*([A-J]-\d+)\*\*", self.text, re.M))

    def test_tier_a_present(self) -> None:
        for rid in TIER_A:
            self.assertIn(rid, self.ids, f"Tier A 규칙 누락: {rid}")

    def test_tier_b_present(self) -> None:
        for rid in TIER_B:
            self.assertIn(rid, self.ids, f"Tier B 규칙 누락: {rid}")

    def test_excluded_rules_absent(self) -> None:
        """G1 미통과·근거 흔들림 항목은 규칙이 되면 안 된다."""
        for rid in EXCLUDED:
            self.assertNotIn(
                rid, self.ids, f"{rid} 는 규칙에서 제외돼야 한다(근거 미달)"
            )

    def test_every_rule_has_evidence_grade(self) -> None:
        rows = [ln for ln in self.text.splitlines() if re.match(r"^\|\s*\*\*[A-J]-\d+", ln)]
        self.assertGreaterEqual(len(rows), 12)
        for row in rows:
            self.assertRegex(row, r"E[1-4]\b", f"근거 등급 없음: {row[:60]}")

    def test_states_no_e1_evidence(self) -> None:
        """영어에 E1 이 없다는 사실과 그 귀결(heavy·finalize 미개방)이 적혀야 한다."""
        self.assertIn("E1", self.text)
        self.assertRegex(self.text, r"finalize|heavy")

    def test_em_dash_documented_as_observation_only(self) -> None:
        """em dash 는 규칙이 아니라 관측 지표임이 본문에 남아야 한다."""
        self.assertIn("em dash", self.text)
        self.assertRegex(self.text, r"관측|observation")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m unittest tests.test_en_rulebook -v`
Expected: 6 FAIL (`없다`).

- [ ] **Step 3: 룰북을 쓴다**

`lang/en/quick-rules.md` — 각 행은 `| **ID** | 트리거 | 처방 | 근거등급 |` 형식.
Tier A 7개 + Tier B 7개, 그리고 제외 목록과 그 이유를 본문에 남긴다.
C-8 은 스파이크가 밝힌 대로 **여러 통사 프레임**을 전부 적는다
(`not X but Y` / `neither X nor Y` / `less about X than Y` / `is not whether … but` /
`rather than X, Y`) — 하나만 적으면 첫 정규식이 그랬듯 재현율이 무너진다.

문서 앞머리에 반드시 넣는다:

```markdown
> **근거 상태.** 이 룰북의 규칙 중 **E1(자체 대조 코퍼스 실측)은 하나도 없다.**
> 한국어 실측이 이식된 것(E1→추정)과 외부 발표(E2)·자체 스파이크(E3)뿐이다.
> 그래서 영어 경로는 **light/standard 만 열고 heavy·finalize 는 닫는다** —
> 증적을 주장할 근거가 없는 것을 증적처럼 내놓지 않는다.
> em dash 는 G1(전 모델 생존) 미통과라 **규칙이 아니라 관측 지표**다
> (Gemini 3.53·Llama 0.00 이 인간 4.76 이하). `core/principles.md` 참조.
```

- [ ] **Step 4: 테스트를 통과시킨다**

Run: `python3 -m unittest tests.test_en_rulebook -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add lang/en/quick-rules.md tests/test_en_rulebook.py
git commit -m "feat(lang/en): 영어 룰북 Tier A+B — 근거 등급 표기, G1 미통과분 제외"
```

---

### Task 5: G3 역주입 게이트 — 전후 재측정

`core/principles.md` 의 G3 를 **문서에서 코드로** 옮긴다. 스파이크에서 이 검사가 있었다면 em dash 2→5 를 자동으로 잡았다. 언어 무관이므로 한국어도 즉시 이득을 본다.

**Files:**
- Create: `core/reinjection.py`
- Create: `tests/test_reinjection.py`

**Interfaces:**
- Consumes: `core.metrics_universal.compute_universal`
- Produces: `check_reinjection(before: str, after: str, counters: dict[str, Callable[[str], int]], *, unit: str, long_threshold: int) -> dict`
  — `{"failed": bool, "risen": {name: (before_n, after_n)}, "note": str}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_reinjection.py`:

```python
"""core/reinjection.py — G3 역주입 게이트.

근거: 스파이크 윤문에서 목표 지표는 전부 0 으로 내려갔는데 em dash 가
2→5(9.33/1k)로 늘었다. 발표된 Claude Opus 4.6 = 9.09/1k 와 거의 일치 —
윤문 콜이 자기 모델의 개인어를 심은 것이다. 한국어에서도 D-9 가 '결국' 을
역주입해 2→4 로 늘었던 같은 실패 모드다.

밀도가 아니라 **원시 건수**로 판정한다 — 스파이크에서 I-4 3.42→3.73 의
상승은 역주입이 아니라 본문이 짧아진 artifact 였다(건수 2→2 불변).
"""
from __future__ import annotations

import importlib.util
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_MOD = os.path.join(_ROOT, "core", "reinjection.py")

COUNTERS = {
    "em_dash": lambda t: len(re.findall(r"—", t)),
    "deontic": lambda t: len(re.findall(r"\b(?:must|should|need to)\b", t, re.I)),
}


def _load():
    spec = importlib.util.spec_from_file_location("_reinjection", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ReinjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_MOD), f"없다: {_MOD}")
        self.m = _load()

    def _check(self, before, after):
        return self.m.check_reinjection(
            before, after, COUNTERS, unit="tokens", long_threshold=35
        )

    def test_spike_case_is_caught(self) -> None:
        """실제 스파이크 사례 — em dash 2 → 5."""
        before = "One thing. Two thing—here. Three—here."
        after = "One thing—joined. Two—here. Three—here. Four—more. Five—last."
        out = self._check(before, after)
        self.assertTrue(out["failed"])
        self.assertIn("em_dash", out["risen"])
        self.assertEqual(out["risen"]["em_dash"], (2, 5))

    def test_removal_only_passes(self) -> None:
        before = "It must be done—now. We should go—soon."
        after = "Do it now. Go soon."
        out = self._check(before, after)
        self.assertFalse(out["failed"], out)

    def test_unchanged_counts_pass(self) -> None:
        out = self._check("A—b. Must go.", "A—b. Must go.")
        self.assertFalse(out["failed"])

    def test_shorter_text_with_same_raw_count_passes(self) -> None:
        """분모 축소로 밀도만 오르는 경우는 역주입이 아니다."""
        before = "Must go. " + "Filler sentence here. " * 20
        after = "Must go. Filler sentence here."
        out = self._check(before, after)
        self.assertFalse(out["failed"], out)

    def test_dispersion_improvement_is_reported(self) -> None:
        """분산 개선은 실패가 아니라 보고 항목이다."""
        out = self._check("A b. C d. E f.", "A b. " + "C d e f g h i j k l m n. ")
        self.assertIn("dispersion", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m unittest tests.test_reinjection -v`
Expected: 5 FAIL (`없다`).

- [ ] **Step 3: 구현한다**

`core/reinjection.py`:

```python
#!/usr/bin/env python3
"""G3 역주입 게이트 — 윤문 전후를 같은 지표로 재측정한다.

철칙 #6(No New Tells)의 코드화. 지우기로 한 티가 줄었어도 다른 지표가
새로 올랐으면 실패다. 윤문 콜은 티를 지우면서 자기 모델의 개인어를 심는다.

**원시 건수로 판정한다.** 밀도로 보면 본문이 짧아진 것만으로 상승이 잡혀
오탐이 난다(스파이크 I-4 3.42→3.73, 건수는 2→2 불변).

언어 무관 — counters 를 호출자가 주입한다.
"""
from __future__ import annotations

import os
import sys
from typing import Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from metrics_universal import compute_universal  # noqa: E402


def check_reinjection(
    before: str,
    after: str,
    counters: dict[str, Callable[[str], int]],
    *,
    unit: str = "tokens",
    long_threshold: int = 35,
) -> dict:
    risen: dict[str, tuple[int, int]] = {}
    for name, fn in counters.items():
        b, a = fn(before), fn(after)
        if a > b:
            risen[name] = (b, a)

    bu = compute_universal(before, long_threshold=long_threshold, unit=unit)
    au = compute_universal(after, long_threshold=long_threshold, unit=unit)

    return {
        "failed": bool(risen),
        "risen": risen,
        "dispersion": (
            bu["sentence_length_dispersion"],
            au["sentence_length_dispersion"],
        ),
        "note": (
            "역주입 없음 — 티는 줄기만 했다"
            if not risen
            else "역주입 감지: " + ", ".join(
                f"{k} {b}→{a}" for k, (b, a) in risen.items()
            )
        ),
    }
```

- [ ] **Step 4: 테스트를 통과시킨다**

Run: `python3 -m unittest tests.test_reinjection -v`
Expected: 5 passed

- [ ] **Step 5: 스파이크 실물로 재현한다**

```bash
python3 -c "
import importlib.util, re, pathlib
spec = importlib.util.spec_from_file_location('m','core/reinjection.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c = {'em_dash': lambda t: len(re.findall(r'—', t))}
b = pathlib.Path('/tmp/enspike/ai_essay_01.txt')
a = pathlib.Path('/tmp/enspike/ai_essay_01_rewritten.txt')
if b.exists() and a.exists():
    print(m.check_reinjection(b.read_text(), a.read_text(), c)['note'])
else:
    print('스파이크 파일 없음(/tmp 는 폐기 대상) — 단위 테스트로 충분')
"
```
Expected: 파일이 남아 있으면 `역주입 감지: em_dash 2→5`.

- [ ] **Step 6: 커밋**

```bash
git add core/reinjection.py tests/test_reinjection.py
git commit -m "feat(core): G3 역주입 게이트 — 철칙 #6 을 문서에서 코드로"
```

---

### Task 6: 엔드투엔드 확인 + 문서 갱신

**Files:**
- Modify: `CLAUDE.md` (디렉터리 구조에 `lang/` 추가)
- Modify: `docs/superpowers/specs/2026-09-02-multilingual-design.md` (R2 를 R2a/R2b 로 분할 반영)

- [ ] **Step 1: 전체 회귀**

```bash
python3 -m unittest discover -s tests -p 'test_*.py' 2>&1 | grep -E "^(Ran|OK|FAILED)"
python3 scripts/build_quick_rules.py --check
python3 scripts/build_diagnosis_rules.py --check
bash tests/test_install_flags.sh
```
Expected: 전부 통과.

- [ ] **Step 2: 영어 입력 엔드투엔드**

```bash
rm -rf /tmp/enrun && mkdir -p /tmp/enrun
cat > /tmp/enrun/01_input.txt <<'EOF'
This underscores a pivotal shift in how we think about work. It delves into the
intricate landscape of remote labor. The findings showcase remarkable potential.
This is not merely a change, but a transformation. What matters is the outcome.
EOF
python3 scripts/prepare_monolith_input.py --run-dir /tmp/enrun --genre column
python3 -c "import json;d=json.load(open('/tmp/enrun/00_metrics.json'));print('lang=',d['lang'],'hint=',d['route_hint']);print(d['route_reason'])"
head -20 /tmp/enrun/01_input_with_metrics.txt
```
Expected: `lang= en`, route_hint 산출, 결합 파일에 점수 블록이 들어간다.

- [ ] **Step 3: 한국어 무회귀 확인**

```bash
rm -rf /tmp/korun && mkdir -p /tmp/korun
printf '이 문제에 있어서 중요한 것은 속도이다. 결론적으로 혁신이 필요하다.\n' > /tmp/korun/01_input.txt
python3 scripts/prepare_monolith_input.py --run-dir /tmp/korun --genre column
python3 -c "import json;d=json.load(open('/tmp/korun/00_metrics.json'));print('lang=',d['lang'],'hint=',d['route_hint'])"
```
Expected: `lang= ko`, 현행과 동일한 route_hint.

- [ ] **Step 4: 문서 갱신 후 커밋**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-09-02-multilingual-design.md
git commit -m "docs: lang/ 디렉터리 반영 + R2 를 R2a(엔진)/R2b(패키징)로 분할"
```

---

## 자체 점검

- **Spec coverage** — §2.4 탐지 어댑터(계측형+렉시콘, 의존성 없음) → Task 2. §2.5 영어 baseline 발표 수치 인용 → Task 1·4. §2.6 Tier A+B·제외 목록 → Task 4. G3 코드화 → Task 5. 언어 라우팅 → Task 3.
- **미포함(R2b)** — 스킬 디렉터리·매니페스트·install.sh·버전 승급.
- **타입 정합** — `compute_all_en(text, lexicon_path=None) -> dict` 는 Task 2 정의를 Task 3 shim 이 그대로 호출한다. `check_reinjection` 의 `counters` 는 호출자 주입이라 언어별 카운터를 R2b 에서 붙인다.
- **가장 큰 위험** — Task 1 의 Kobak 목록을 못 받아오는 경우. 그때는 **멈추고 보고한다.** 목록을 기억으로 채우면 이 저장소의 증거 기준을 어긴다.
