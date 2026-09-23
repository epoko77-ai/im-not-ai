"""PR #94가 지적한 잔여 결함 3건의 회귀 테스트 (2026-09-24).

#94는 저영향 국소 결함 11건을 한 PR에 묶었다. 그중 T2a 합성 피동(#150)과
quick-rules 심각도 태그(#146)는 이미 반영됐고, 아래 3건은 이 회차에 고쳤다.
셋 다 "측정이 조용히 틀려서 게이트·판정이 엉뚱한 곳을 가리키는" 유형이다.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def _load(name: str, relpath: str):
    """파일 경로로 모듈을 적재한다.

    `sys.modules` 에 먼저 등록해야 한다 — Python 3.12+ 의 `@dataclass` 가 어노테이션
    해석을 위해 모듈을 그 표에서 되찾는다. 등록 없이 `exec_module` 하면
    `AttributeError: 'NoneType' object has no attribute '__dict__'` 로 죽는다
    (`scripts/checks.py` 가 dataclass 를 쓴다).
    """
    path = os.path.join(ROOT, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ThousandsSeparatorTests(unittest.TestCase):
    """천 단위 콤마가 쉼표 문체 지표에 섞이던 것.

    "1,200억"·"12,000명"의 콤마를 세면 숫자가 많은 문서(경제·통계 기사)가 쉼표
    지표에서 최상위로 뜬다. 그 문서가 S1 앵커로 뽑히면 윤문할 쉼표가 애초에
    없으므로 게이트가 영구 미달한다.
    """

    def setUp(self) -> None:
        self.m = _load("metrics", "skills/humanize-korean/references/metrics.py")

    def test_digit_commas_are_not_style_commas(self) -> None:
        text = "매출은 1,200억 원이고 비용은 3,400만 원이다. 인원은 12,000명이다."
        for fn in ("comma_inclusion_rate", "comma_usage_rate", "ending_comma_rate"):
            with self.subTest(metric=fn):
                self.assertEqual(getattr(self.m, fn)(text), 0.0, fn)

    def test_style_commas_still_counted_alongside_numbers(self) -> None:
        text = "정책은 확대되고, 예산은 늘었고, 인원은 1,200명이다."
        self.assertEqual(self.m.comma_inclusion_rate(text), 1.0)
        self.assertEqual(self.m.comma_usage_rate(text), 2.0)


class NounYoEndingTests(unittest.TestCase):
    """`요`로 끝나는 한자 명사를 해요체 구어 종결로 오인하던 것.

    "보완 필요."·"추진 개요." 같은 개조식 종결을 구어 종결로 세면
    `colloquial_erased`가 발동해 **올바른 윤문 결과를 롤백**시킨다.
    """

    def setUp(self) -> None:
        self.c = _load("checks", "scripts/checks.py")

    def test_noun_endings_are_not_colloquial(self) -> None:
        for text in (
            "보완 필요.",
            "추진 개요.",
            "시장 수요.",
            "이건 중요.",
            "조치가 소요.",
            "정책 강요.",
            "여론 동요.",
        ):
            with self.subTest(text=text):
                self.assertEqual(len(self.c.YO_ENDING_RE.findall(text)), 0, text)

    def test_real_haeyo_endings_still_counted(self) -> None:
        """진짜 해요체는 그대로 잡아야 한다 — 특히 `하고요`(목록에 `고` 미포함)."""
        for text in (
            "이건 제가 했어요.",
            "하면 되거든요.",
            "왜 그런지 아세요?",
            "같이 가요.",
            "그렇게 하고요.",
            "정말 그런가요?",
            "맞아요!",
            "그렇네요.",
        ):
            with self.subTest(text=text):
                self.assertEqual(len(self.c.YO_ENDING_RE.findall(text)), 1, text)


class SimplificationAxisMarkerTests(unittest.TestCase):
    """단순화 축 지표의 z 마커가 거꾸로 붙던 것.

    baseline이 `"interpretation": "low = AI-like (repetition)"`이라고 직접 적어
    두는데도 마커는 z를 부호 그대로 읽어, **가장 어휘가 풍부한(= 가장 사람다운)
    글에 "★ S1 트리거"**를 붙였다. 모델은 그 표기를 보고 손댈 곳을 찾는다.
    """

    def setUp(self) -> None:
        self.p = _load("shim", "scripts/prepare_monolith_input.py")

    def test_interference_axis_unchanged(self) -> None:
        self.assertIn("★", self.p._z_marker(2.0, "by_passive_count"))
        self.assertEqual(self.p._z_marker(-2.0, "by_passive_count"), "")

    def test_simplification_axis_inverted(self) -> None:
        for key in ("lexical_diversity", "lexical_density", "ending_diversity"):
            with self.subTest(metric=key):
                self.assertEqual(
                    self.p._z_marker(2.0, key), "", f"{key}: 높은 다양성에 마커"
                )
                self.assertIn("★", self.p._z_marker(-2.0, key))

    def test_marker_without_key_keeps_legacy_behaviour(self) -> None:
        self.assertIn("★", self.p._z_marker(2.0))


if __name__ == "__main__":
    unittest.main()
