"""skills/humanize-english/SKILL.md 계약 — 문서가 가리키는 것이 실재하는지.

`test_agent_inventory.py` 가 ko SKILL.md 의 서술과 실물을 대조하듯,
영어 스킬이 참조하는 스크립트·룰북·게이트가 전부 있는지 결정적으로 검사한다.
스킬은 런타임에 이 경로를 Bash 로 부르므로, 하나라도 없으면 조용히 실패한다.
"""
from __future__ import annotations

import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SKILL = os.path.join(_ROOT, "skills", "humanize-english", "SKILL.md")
_INSTALL = os.path.join(_ROOT, "install.sh")

# SKILL.md 가 ${SKILL_ROOT}/ 로 참조하는 런타임 자원 전수.
REFERENCED = (
    "scripts/prepare_monolith_input.py",
    "scripts/verify_change_rate.py",
    "core/reinjection.py",
    "core/underedit.py",
    "core/principles.md",
    "lang/en/quick-rules.md",
    "lang/en/lexicon.json",
    "lang/en/scholarship.md",
    "lang/en/candidate-pool.md",
)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class EnSkillContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_SKILL), f"없다: {_SKILL}")
        self.text = _read(_SKILL)

    def test_frontmatter_name_matches_directory(self) -> None:
        head = self.text.split("---", 2)[1]
        self.assertIn("name: humanize-english", head)
        self.assertRegex(head, r'version:\s*"\d+\.\d+\.\d+"')

    def test_referenced_runtime_paths_exist(self) -> None:
        for rel in REFERENCED:
            self.assertIn(rel, self.text, f"SKILL.md 가 {rel} 를 참조하지 않는다")
            self.assertTrue(
                os.path.exists(os.path.join(_ROOT, rel)),
                f"SKILL.md 가 가리키는 {rel} 가 실재하지 않는다",
            )

    def test_shim_called_with_lang_en(self) -> None:
        """--lang en 없이 부르면 한국어 지표가 영어에 적용된다."""
        self.assertRegex(self.text, r"prepare_monolith_input\.py[^\n]*--lang en")

    def test_reinjection_gate_called_with_lang_en(self) -> None:
        self.assertRegex(self.text, r"reinjection\.py[\s\S]{0,200}?--lang en")

    def test_underedit_gate_called(self) -> None:
        """과소윤문 게이트가 배선돼야 한다 — 실측에서 4회 중 1회가 새어나갔다."""
        self.assertRegex(self.text, r"underedit\.py[\s\S]{0,300}?--route-hint")

    def test_heavy_and_finalize_are_closed(self) -> None:
        """영어에는 E1 근거가 없다 — heavy·finalize 를 열면 안 된다."""
        self.assertRegex(self.text, r"heavy·finalize 는 닫는다|heavy.{0,10}닫는다")
        self.assertIn("standard 로 처리한다", self.text)

    def test_both_gate_exit_codes_documented(self) -> None:
        """게이트를 부르기만 하고 exit code 해석이 없으면 판정이 무시된다."""
        for code in ("exit 0", "exit 1", "exit 2", "exit 3"):
            self.assertIn(code, self.text, f"{code} 처리 규정 누락")

    def test_installed_by_install_sh(self) -> None:
        """설치 스크립트가 이 스킬을 심어야 사용자가 쓸 수 있다."""
        self.assertIn("humanize-english", _read(_INSTALL))


if __name__ == "__main__":
    unittest.main()
