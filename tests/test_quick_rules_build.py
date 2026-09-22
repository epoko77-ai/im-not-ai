"""quick-rules.md 가 taxonomy(SSOT)에서 재생성 가능하고 최신인지 검증한다.

fast 룰북을 손으로 동기화하다 ID 드리프트가 생긴 사고(D-3·G-1/G-2·J-3)의
재발 방지. CI에서 --check 가 실패하면 누군가 quick-rules.md 를 손으로 고쳤거나
taxonomy 를 고치고 재생성을 안 한 것이다.

pytest / unittest 양쪽에서 실행된다.
"""

from __future__ import annotations

import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def _load_builder():
    path = os.path.join(SCRIPTS, "build_quick_rules.py")
    spec = importlib.util.spec_from_file_location("build_quick_rules", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class QuickRulesBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = _load_builder()

    def test_every_pattern_has_quick_meta(self) -> None:
        """모든 패턴에 _quick 메타가 있어야 빌드가 성립한다(누락 = 실패)."""
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            patterns = self.builder.parse_taxonomy(f.read())
        missing = [p["id"] for p in patterns if p["quick"] is None]
        self.assertEqual(missing, [], f"quick 메타 누락: {missing}")

    def test_quick_rules_is_up_to_date(self) -> None:
        """quick-rules.md 가 SSOT 재생성 결과와 일치해야 한다."""
        rendered, _ = self.builder.build()
        with open(self.builder._OUT, encoding="utf-8") as f:
            existing = f.read()
        self.assertEqual(
            existing.rstrip(),
            rendered.rstrip(),
            "quick-rules.md 가 taxonomy와 어긋난다. "
            "`python3 scripts/build_quick_rules.py` 로 재생성하라.",
        )

    def test_generated_ids_are_subset_of_taxonomy(self) -> None:
        """생성물의 모든 ID가 taxonomy에 실재해야 한다(1:1 매칭)."""
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            patterns = self.builder.parse_taxonomy(f.read())
        taxo_ids = {p["id"] for p in patterns}
        quick_ids = {p["id"] for p in patterns if p["quick"] is True}
        self.assertTrue(quick_ids)
        self.assertTrue(quick_ids <= taxo_ids)


class OrphanQuickMetaTests(unittest.TestCase):
    """`_quick:` 메타가 패턴에 귀속되지 않고 버려지는 것을 막는다 (2026-09-22).

    `## J-1. 과도한 **볼드**` 가 `###` 대신 `##` 로 적혀 있어 파서에 헤딩으로
    보이지 않았다. 그 결과 J-1 의 `_quick: true` 줄이 어느 패턴에도 귀속되지
    못하고 조용히 버려져, **J-1 이 quick-rules.md·diagnosis-rules.md 양쪽에서
    통째로 빠진 상태로 배포되고 있었다.** 손 동기화 드리프트를 막으려고 생성기를
    도입했는데, 생성기 자체가 입력을 조용히 흘리면 같은 사고가 난다.

    원문의 `_quick:` 메타 줄 수와 파서가 귀속시킨 수가 같아야 한다.
    """

    def setUp(self) -> None:
        self.builder = _load_builder()
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            self.taxonomy = f.read()

    def test_every_quick_meta_line_is_attributed(self) -> None:
        raw = [
            ln
            for ln in self.taxonomy.splitlines()
            if self.builder._QUICK_RE.search(ln)
        ]
        patterns = self.builder.parse_taxonomy(self.taxonomy)
        attributed = [p for p in patterns if p["quick"] is not None]
        self.assertEqual(
            len(raw),
            len(attributed),
            f"_quick 메타 {len(raw)}줄 중 {len(attributed)}건만 패턴에 귀속됐다. "
            "헤딩이 `### <ID>.` 형식인지 확인하라 — `##` 로 적으면 파서가 "
            "패턴으로 인식하지 못하고 그 규칙이 룰북에서 조용히 사라진다.",
        )

    def test_every_pattern_heading_uses_three_hashes(self) -> None:
        """`## X-N.` 형태의 헤딩이 없어야 한다(패턴은 항상 `###`)."""
        bad = [
            ln.strip()
            for ln in self.taxonomy.splitlines()
            if re.match(r"^##\s+[A-J]-\d+\.", ln)
        ]
        self.assertEqual(bad, [], f"패턴 헤딩이 `##` 로 적혔다: {bad}")


class QuickBudgetTests(unittest.TestCase):
    """fast 토큰 예산 가드 (2026-09-22 신규).

    `quick-rules.md` 는 fast 경로 매 호출에 통째로 주입되므로 건수가 곧 비용이다.
    drift 검사만 있고 건수 검사가 없던 동안 quick:true 가 50 → 61건까지 새어
    상한(60)을 넘겼다. 8건 강등 후 이 가드를 넣었고, 여기서 회귀를 막는다.
    """

    def setUp(self) -> None:
        self.builder = _load_builder()
        with open(self.builder._TAXONOMY, encoding="utf-8") as f:
            self.taxonomy = f.read()

    def test_current_count_is_within_budget(self) -> None:
        """현행 quick:true 건수가 상한 이내여야 한다."""
        patterns = self.builder.parse_taxonomy(self.taxonomy)
        n_true = sum(1 for p in patterns if p["quick"] is True)
        self.assertLessEqual(
            n_true,
            self.builder.QUICK_BUDGET_MAX,
            f"fast 토큰 예산 초과 — quick: true {n_true}건 "
            f"(상한 {self.builder.QUICK_BUDGET_MAX}). 신규 패턴의 기본값은 "
            "`quick: false` 이고, true 가 필요하면 실측 판별력이 약한 기존 "
            "항목을 먼저 강등하라.",
        )

    def test_guard_matches_taxonomy_policy(self) -> None:
        """가드 상수가 taxonomy 머리말의 정책 문장과 일치해야 한다.

        정책을 문서에서만 고치고 가드는 그대로 두는(또는 그 반대) 드리프트 방지.
        이 레포가 반복해 밟은 사고 유형이라 양방향으로 묶어 둔다.
        """
        target, tol = self.builder.budget_policy_from_taxonomy(self.taxonomy)
        self.assertEqual(
            (target, tol),
            (
                self.builder.QUICK_BUDGET_TARGET,
                self.builder.QUICK_BUDGET_TOLERANCE_PCT,
            ),
            "taxonomy 머리말의 quick 예산 정책과 build_quick_rules.py 상수가 "
            "어긋난다. 한쪽만 고쳤다.",
        )

    def test_ceiling_derives_from_policy(self) -> None:
        """상한이 목표 ±허용오차에서 파생돼야 한다(수를 손으로 박지 않는다)."""
        self.assertEqual(
            self.builder.QUICK_BUDGET_MAX,
            self.builder.QUICK_BUDGET_TARGET
            * (100 + self.builder.QUICK_BUDGET_TOLERANCE_PCT)
            // 100,
        )

    def test_policy_parser_rejects_missing_sentence(self) -> None:
        """정책 문장이 사라지면 조용히 통과하지 말고 ParseError 를 내야 한다."""
        with self.assertRaises(self.builder.ParseError):
            self.builder.budget_policy_from_taxonomy("정책 문장이 없는 본문")


if __name__ == "__main__":
    unittest.main()
