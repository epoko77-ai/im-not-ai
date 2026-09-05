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

# EN-* 는 한국어 대응물이 없는 영어 고유 규칙이다.
# 실물 기준(2026-09-03). E-1 은 G1 미통과로 제외됨.
TIER_A = ("C-8", "F-7", "F-4", "EN-1", "EN-2", "EN-3", "C-12b", "C-12", "E-5")
TIER_B = ("C-1", "C-2", "C-3", "C-5", "C-6", "C-9", "C-10")
# A-9·G-1·G-2 는 v0.2 에서 철회·반전됐다 — 규칙 표에 있으면 안 된다.
# E-1 은 2026-09-03 G1 미통과로 강등(opus 0.59 vs haiku 0.05 — 방향이 갈린다).
EXCLUDED = ("J-3", "H-1", "H-3", "G-3", "D-4", "A-9", "G-1", "G-2", "E-1")

# ID 는 문자 접미사를 가질 수 있다(C-12b). 접미사를 빼면 그 규칙이
# 목록에서 조용히 사라져 존재 검사가 무력해진다.
_RULE_ROW = re.compile(r"^\|\s*\*\*([A-Z]{1,2}-\d+[a-z]?)\*\*")


def _read() -> str:
    with open(_RULEBOOK, encoding="utf-8") as f:
        return f.read()


class EnRulebookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isfile(_RULEBOOK), f"없다: {_RULEBOOK}")
        self.text = _read()
        self.rows = [ln for ln in self.text.splitlines() if _RULE_ROW.match(ln)]
        self.ids = {_RULE_ROW.match(ln).group(1) for ln in self.rows}

    def test_tier_a_present(self) -> None:
        for rid in TIER_A:
            self.assertIn(rid, self.ids, f"Tier A 규칙 누락: {rid}")

    def test_tier_b_present(self) -> None:
        for rid in TIER_B:
            self.assertIn(rid, self.ids, f"Tier B 규칙 누락: {rid}")

    def test_excluded_rules_absent(self) -> None:
        """G1 미통과·근거 흔들림 항목은 **규칙 표**에 있으면 안 된다.

        `_RULE_ROW` 는 `| **ID** |` 형태만 잡으므로, 제외 표의
        `| **E-1 문장길이 분산** |` 같은 서술형 행은 여기 안 걸린다.
        """
        for rid in EXCLUDED:
            self.assertNotIn(
                rid, self.ids, f"{rid} 는 규칙에서 제외돼야 한다(근거 미달)"
            )

    def test_protected_features_documented(self) -> None:
        """LLM 이 과소 사용하는 것 — 제거하면 역효과다. v0.2 최대 정정."""
        self.assertIn("건드리면 안 되는 것", self.text)
        for feat in ("hedges", "agentless passive", "contraction"):
            self.assertIn(feat, self.text, f"보호 대상 누락: {feat}")

    def test_dispersion_demoted_with_g1_evidence(self) -> None:
        """E-1 분산은 G1 미통과 — 규칙 표에 없고, 제외 사유가 기록돼야 한다."""
        self.assertNotIn("E-1", self.ids, "E-1 이 규칙 표에 남아 있다")
        self.assertIn("G1 미통과", self.text)
        self.assertRegex(self.text, r"opus 0\.59|opus 는 인간보다 분산이")

    def test_links_scholarship(self) -> None:
        self.assertIn("scholarship.md", self.text)

    def test_every_rule_has_evidence_grade(self) -> None:
        self.assertGreaterEqual(len(self.rows), 12)
        for row in self.rows:
            self.assertRegex(row, r"E[1-4]\b", f"근거 등급 없음: {row[:70]}")

    def test_states_no_e1_evidence(self) -> None:
        """영어에 E1 이 없다는 사실과 그 귀결(heavy·finalize 미개방)이 적혀야 한다."""
        self.assertIn("E1", self.text)
        self.assertRegex(self.text, r"finalize")
        self.assertRegex(self.text, r"heavy")

    def test_em_dash_documented_as_observation_only(self) -> None:
        """em dash 는 규칙이 아니라 관측 지표임이 본문에 남아야 한다."""
        self.assertIn("em dash", self.text)
        self.assertIn("관측", self.text)

    def test_en3_states_the_syntactic_frame(self) -> None:
        """EN-3 은 어휘 목록이 아니라 `A, B, and C` 프레임이어야 한다.

        이 저장소는 표면 예시를 인코딩하고 프레임을 놓친 실패를 세 번 했다
        (C-8 재현율 0/6 · 렉시콘 전수 오발화 · EN-1 초판 0.00).
        """
        row = next(r for r in self.rows if r.startswith("| **EN-3**"))
        self.assertIn("A, B, and C", row)
        self.assertIn("프레임", row)
        self.assertRegex(row, r"E1")

    def test_c8_lists_multiple_syntactic_frames(self) -> None:
        """C-8 은 프레임 하나만 적으면 첫 정규식처럼 재현율이 무너진다(0/6)."""
        c8_rows = [r for r in self.rows if _RULE_ROW.match(r).group(1) == "C-8"]
        body = " ".join(c8_rows)
        for frame in ("not", "but", "neither", "rather than"):
            self.assertIn(frame, body.lower(), f"C-8 프레임 누락: {frame}")

    def test_no_new_tells_rule_present(self) -> None:
        """철칙 #6 — 영어 윤문이 em dash 를 심었던 실사고의 재발 방지."""
        self.assertRegex(self.text, r"No New Tells|철칙 #6")


if __name__ == "__main__":
    unittest.main()
