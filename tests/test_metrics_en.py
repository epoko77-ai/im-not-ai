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
        self.lex = self.m.load_lexicon()

    def test_matches_measured_surface_forms(self) -> None:
        """원자료의 표면형을 그대로 잡는다 — 원형화·재확장 없음."""
        total, per = self.m.lexicon_hits("It delves. It is delving. They delve.", self.lex)
        self.assertEqual(total, 3, f"표면형 3개를 다 잡아야 한다: {per}")

    def test_does_not_match_substrings(self) -> None:
        """'delve' 가 'delvedelve'·'xdelve' 같은 부분문자열을 잡으면 안 된다."""
        total, _ = self.m.lexicon_hits("delvedelve xdelve thunderscores", self.lex)
        self.assertEqual(total, 0)

    def test_case_insensitive(self) -> None:
        total, _ = self.m.lexicon_hits("Delves and DELVES.", self.lex)
        self.assertEqual(total, 2)

    def test_family_breakdown(self) -> None:
        total, per = self.m.lexicon_hits("It delves into intricate work.", self.lex)
        self.assertEqual(per.get("F-7"), 1, per)   # delves = verb
        self.assertEqual(per.get("D-4"), 1, per)   # intricate = adjective

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
        out = self.m.compute_all_en("This is a plain plain sentence here. " * 200)
        self.assertNotEqual(out["route_hint"], "heavy", out["route_reason"])

    def test_long_input_goes_heavy(self) -> None:
        out = self.m.compute_all_en("This is a plain plain sentence here. " * 700)
        self.assertGreater(out["char_count"], 15000)
        self.assertEqual(out["route_hint"], "heavy")

    def test_signals_are_reported(self) -> None:
        out = self.m.compute_all_en(SLOP)
        for key in ("lexicon_total", "dispersion", "comma_inclusion_rate", "char_count"):
            self.assertIn(key, out["route_signals"])

    def test_evidence_note_present(self) -> None:
        """E1 이 없다는 사실이 산출물에 남아야 한다 — 나중에 등급을 물어본다."""
        self.assertIn("E1", self.m.compute_all_en(SLOP)["evidence_note"])

    def test_empty_text_does_not_crash(self) -> None:
        out = self.m.compute_all_en("")
        self.assertEqual(out["char_count"], 0)


if __name__ == "__main__":
    unittest.main()


class RouterLexiconScopeTests(unittest.TestCase):
    """라우터 렉시콘 범위 회귀 — 이 함정에 두 번 빠지지 않게.

    실사고(2026-09-02): Kobak 목록 407건 전수를 라우터에 쓰자
    "This is a plain sentence." 반복문이 142.86/1k 로 heavy 판정을 받았다.
    목록이 '2010-2021 기준선 대비 증가분'이라 this·across·between·however 같은
    초고빈도어를 포함하기 때문이다. 논문은 희귀·고비율(r)과 흔한·고격차(δ)를
    구분하지만 공개 저장소에 per-word r/δ 표가 없어 재현할 수 없다.
    """

    PLAIN_ENGLISH = "This is a plain plain sentence here. " * 50

    def setUp(self) -> None:
        self.m = _load()
        self.lex = self.m.load_lexicon()

    def test_plain_english_does_not_trigger_router(self) -> None:
        out = self.m.compute_all_en(self.PLAIN_ENGLISH)
        self.assertEqual(
            out["lexicon"]["total"], 0, f"평범한 영어가 발화: {out['lexicon']}"
        )
        self.assertNotEqual(out["route_hint"], "heavy", out["route_reason"])

    def test_full_list_would_have_fired(self) -> None:
        """전수 계수는 여전히 발화한다 — 그게 라우터에서 뺀 이유다."""
        full, _ = self.m.lexicon_hits(self.PLAIN_ENGLISH, self.lex, router_only=False)
        self.assertGreater(full, 0, "이 테스트의 전제가 깨졌다")

    def test_router_set_is_small_and_documented(self) -> None:
        eligible = [e for e in self.lex["entries"] if e.get("router_eligible")]
        self.assertLessEqual(
            len(eligible), 30, "라우터 렉시콘을 넓히려면 per-word r/δ 근거가 필요하다"
        )
        self.assertIn("router_policy", self.lex)
        self.assertIn("증가분", self.lex["router_policy"])

    def test_high_ratio_words_carry_their_ratio(self) -> None:
        """논문이 r 값을 보고한 셋은 그 값을 파일에 남긴다."""
        by = {e["word"]: e for e in self.lex["entries"]}
        self.assertAlmostEqual(by["delves"]["ratio"], 28.0)
        self.assertAlmostEqual(by["underscores"]["ratio"], 13.8)
        self.assertAlmostEqual(by["showcasing"]["ratio"], 10.7)


class DenominatorGuardTests(unittest.TestCase):
    """짧은 글에서 밀도 지표를 믿지 않는다.

    실사고(2026-09-02): 39토큰 영어 표본이 렉시콘 4건으로 102.56/1k 를 내
    heavy 판정을 받았다. 비율이 아니라 분모가 만든 수다.
    core/principles.md G3 의 "밀도 지표를 볼 때는 분모를 함께 본다" 가
    라우터 자신에게도 적용된다.
    """

    def setUp(self) -> None:
        self.m = _load()

    def test_short_slop_is_not_heavy(self) -> None:
        out = self.m.compute_all_en(SLOP)  # 40토큰 안팎
        self.assertLess(out["universal"]["tokens"], self.m.MIN_TOKENS_FOR_RATE)
        self.assertEqual(out["route_hint"], "standard", out["route_reason"])
        self.assertIn("밀도 판정 불가", out["route_reason"])

    def test_long_slop_still_goes_heavy(self) -> None:
        """분량이 충분하면 어휘 밀집은 여전히 heavy 다."""
        out = self.m.compute_all_en(SLOP * 12)
        self.assertGreaterEqual(out["universal"]["tokens"], self.m.MIN_TOKENS_FOR_RATE)
        self.assertEqual(out["route_hint"], "heavy", out["route_reason"])

    def test_long_human_prose_is_not_heavy(self) -> None:
        out = self.m.compute_all_en(HUMAN * 8)
        self.assertNotEqual(out["route_hint"], "heavy", out["route_reason"])


class GenreThresholdTests(unittest.TestCase):
    """장르별 임계 (R2 실측 2026-09-04).

    초록 보정 임계를 블로그에 그대로 쓰면 인간 중앙값이 통째로 AI 쪽에 떨어져
    라우터가 죽는다(분리도 0.29 → 블로그 보정 0.65).
    """

    def setUp(self) -> None:
        self.m = _load()

    def test_genre_selects_threshold_set(self) -> None:
        self.assertEqual(self.m.GENRE_TO_SET.get("abstract"), "abstract")
        self.assertEqual(self.m.DEFAULT_SET, "blog")
        for genre, want in (("abstract", "abstract"), ("essay", "blog"),
                            ("blog", "blog"), ("column", "blog")):
            out = self.m.compute_all_en("word " * 200, genre=genre)
            self.assertEqual(out["threshold_set"], want, genre)

    def test_blog_set_uses_tricolon_not_comma_usage(self) -> None:
        """쉼표 사용률·EN-2 는 이 장르에서 모델 개인어라 라우터에 없다."""
        text = ("We shipped fast, learned, and adjusted. " * 24) + ("A short line here. " * 24)
        out = self.m.compute_all_en(text, genre="blog")
        self.assertIn("3항 등위", out["route_reason"])
        self.assertNotIn("be동사", out["route_reason"])

    def test_tricolon_frame_not_two_item_list(self) -> None:
        rx = self.m._TRICOLON_RE
        self.assertTrue(rx.search("careers, products, and strategy"))
        self.assertFalse(rx.search("careers and products"))

    def test_threshold_sets_are_documented_with_separation(self) -> None:
        for name, cfg in self.m.THRESHOLD_SETS.items():
            self.assertIn("separation", cfg, name)
            self.assertIn("source", cfg, name)
