"""humanize-scan 이 참조하는 패턴 ID 가 taxonomy 에서 사라지지 않았는지 검사.

quick-rules.md 는 build_quick_rules.py 가 생성해 ID 드리프트를 구조적으로 막지만,
humanize-scan/SKILL.md 는 실측 판별력 상위 6개만 손으로 고른 목록이라 생성물이
아니다. 그래서 taxonomy 에서 ID 가 은퇴·개명되면 조용히 죽은 규칙을 가리키게 된다.
이 테스트가 그 지점만 지킨다.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "skills" / "humanize-scan" / "SKILL.md"
_TAXONOMY = _ROOT / "skills" / "humanize-korean" / "references" / "ai-tell-taxonomy.md"

# SKILL.md "이 6개만 본다" 표의 ID. 늘리려면 empirical-validation.md 근거부터.
QUICK_SIX = ["C-8", "E-1", "C-11", "I-4", "E-2", "F-5"]


def _taxonomy_ids() -> set[str]:
    text = _TAXONOMY.read_text(encoding="utf-8")
    return set(re.findall(r"^### ([A-J]-\d+)\.", text, re.M))


def test_quick_six_exist_in_taxonomy() -> None:
    known = _taxonomy_ids()
    missing = [i for i in QUICK_SIX if i not in known]
    assert not missing, f"humanize-scan 이 taxonomy 에 없는 ID 를 가리킨다: {missing}"


def test_skill_table_matches_quick_six() -> None:
    """SKILL.md 표를 고치면서 이 테스트를 안 고치는 경우를 막는다."""
    body = _SKILL.read_text(encoding="utf-8").split("## 이 6개만 본다", 1)[1]
    table = body.split("## 이건 일부러 안 본다", 1)[0]
    listed = re.findall(r"\*\*([A-J]-\d+)\*\*", table)
    assert listed == QUICK_SIX, f"SKILL.md 표={listed} != QUICK_SIX={QUICK_SIX}"
