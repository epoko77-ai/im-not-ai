"""R2 블로그 셀 인코더 계약 — 표면 예시가 아니라 통사 프레임인지.

이 저장소는 같은 실패를 세 번 했다(C-8 재현율 0/6, 렉시콘 전수 오발화,
EN-1 초판 0.00): **표면 예시를 인코딩하고 프레임을 놓쳤다.** 그리고 R2 에서
두 가지를 더 배웠다 — 결말 공식은 발췌 구간에 원리적으로 없고(위치가 본질),
본문 추출 실패 시 페이지 전체로 폴백하면 사이드바가 코퍼스에 들어간다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_MOD = os.path.join(_ROOT, "scripts", "build_en_blog_r2.py")


def _load():
    spec = importlib.util.spec_from_file_location("_r2", _MOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class EncoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()

    def test_tricolon_matches_frame_not_examples(self) -> None:
        """3항 등위는 어휘가 아니라 `A, B, and C` 프레임이다."""
        rx = self.m._CAND["tricolon"]
        for hit in ("we shipped fast, learned, and adjusted",
                    "careers, products, and strategy",
                    "reasoning under uncertainty, existential risk, and the rest"):
            self.assertTrue(rx.search(hit), hit)
        for miss in ("we shipped fast and learned",       # 2항
                     "careers and products"):
            self.assertFalse(rx.search(miss), miss)

    def test_vague_source_needs_subject_and_verb(self) -> None:
        rx = self.m._CAND["vague_source"]
        self.assertTrue(rx.search("Studies show that sleep matters."))
        self.assertTrue(rx.search("Many argue the opposite."))
        self.assertFalse(rx.search("The study of sleep is old."))

    def test_closing_formula_reads_the_tail_not_the_body(self) -> None:
        """결말 공식은 **위치가 본질**이다 — 발췌 구간에는 원리적으로 없다."""
        body = "Some body text in the middle of the essay."
        self.assertEqual(self.m._metrics(body, "One thing is clear: it works.")
                         ["closing_formula"], 1.0)
        self.assertEqual(self.m._metrics(body, "and then we went home.")
                         ["closing_formula"], 0.0)
        # tail 이 없으면 0 — 본문에서 억지로 세지 않는다.
        self.assertEqual(self.m._metrics("One thing is clear.")["closing_formula"], 0.0)

    def test_nav_junk_is_rejected(self) -> None:
        """사이드바 아카이브 목록이 본문으로 새면 버린다."""
        junk = "August 2016 July 2016 June 2016 " + "word " * 600
        self.assertFalse(self.m._ok(junk))
        self.assertTrue(self.m._ok("clean prose " * 400))

    def test_ssc_has_no_whole_page_fallback(self) -> None:
        """본문 컨테이너를 못 찾으면 폐기한다 — 통째 폴백은 조용한 오염이다."""
        src = open(_MOD, encoding="utf-8").read()
        self.assertIn("본문 컨테이너를 못 찾으면 버린다", src)
        self.assertNotIn("if body else page", src)

    def test_excerpt_skips_the_opening(self) -> None:
        words = " ".join(str(i) for i in range(600))
        got = self.m._excerpt(words).split()
        self.assertEqual(got[0], str(self.m._SKIP_WORDS))
        self.assertEqual(len(got), self.m._TAKE_WORDS)


class CorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()
        self.path = os.path.join(_ROOT, "_workspace", "en_blog_r2", "human.json")
        if not os.path.exists(self.path):
            self.skipTest("R2 코퍼스 미수집")

    def test_human_corpus_is_pre_chatgpt_and_multi_source(self) -> None:
        rows = json.load(open(self.path, encoding="utf-8"))
        self.assertGreaterEqual(len({r["source"] for r in rows}), 3)
        for r in rows:
            self.assertTrue(self.m._ok(r["text"] + " x" * self.m._MIN_SOURCE_WORDS))
            self.assertNotIn("2022", r["published"][:4])
            self.assertNotIn("2023", r["published"][:4])


if __name__ == "__main__":
    unittest.main()
