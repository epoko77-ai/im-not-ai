"""어휘 레이어(scripts/lexical_layer.py)와 사전(references/lexicon.json) 검사."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import lexical_layer as ll  # noqa: E402


class LexiconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = ll.load_lexicon()

    def test_entries_have_required_fields(self):
        self.assertGreaterEqual(len(self.lex["entries"]), 100)
        ids = set()
        for e in self.lex["entries"]:
            self.assertNotIn(e["id"], ids)
            ids.add(e["id"])
            self.assertIn(e["tier"], ("change", "conditional"))
            for k in ("change_when", "keep_when", "how"):
                self.assertEqual(set(e[k]), {"보고서", "논문", "일반"}, e["id"])
            self.assertEqual(e["restore"], e["tier"] == "change")

    def test_every_entry_hits_its_ai_example(self):
        for e in self.lex["entries"]:
            with self.subTest(id=e["id"]):
                self.assertTrue(ll._matches(e, e["test_positive"]), e["headword"])

    def test_detect_regex_catches_variants_and_spares_legit_uses(self):
        for e in self.lex["entries"]:
            for s in e.get("test_detect_pos") or []:
                with self.subTest(id=e["id"], pos=s):
                    self.assertTrue(ll._matches(e, s, detect=True), e["headword"])
            for s in e.get("test_detect_neg") or []:
                with self.subTest(id=e["id"], neg=s):
                    self.assertFalse(ll._matches(e, s, detect=True), e["headword"])

    def test_detect_is_superset_of_restore_on_ai_example(self):
        for e in self.lex["entries"]:
            with self.subTest(id=e["id"]):
                self.assertTrue(ll._matches(e, e["test_positive"], detect=True), e["headword"])

    def test_alternative_sentence_is_not_flagged(self):
        for e in self.lex["entries"]:
            if not e.get("test_negative"):
                continue
            with self.subTest(id=e["id"]):
                self.assertFalse(ll._matches(e, e["test_negative"]), e["headword"])


class HintTests(unittest.TestCase):
    def test_no_hits_no_block(self):
        self.assertEqual(ll.hint_block_for("오늘은 비가 왔다. 우산을 챙겼다.", "column"), "")

    def test_block_lists_only_found_items(self):
        text = "이 교육은 직원의 잠재력을 잠금 해제한다."
        block = ll.hint_block_for(text, "column")
        self.assertIn("[어휘 점검]", block)
        self.assertIn("잠재력을 잠금 해제", block)
        self.assertEqual(block.count("\n- ["), 1)

    def test_quoted_examples_are_not_hinted(self):
        # v2.4.1 회귀: AI 티를 설명하며 인용한 예문은 직접 인용(Do-NOT) — 힌트에서 뺀다
        text = '예를 들어 "이 교육은 직원의 잠재력을 잠금 해제한다." 같은 문장이 걸립니다.'
        self.assertEqual(ll.hint_block_for(text, "column"), "")
        for q in ("“두 렌즈를 섞지 말 것.”", "「두 렌즈를 섞지 말 것」", "'두 렌즈를 섞지 말 것'"):
            with self.subTest(q=q):
                self.assertEqual(ll.find_hits(f"이런 문장은 {q} 처럼 보입니다.", "column"), [])

    def test_same_word_outside_quotes_still_hinted(self):
        text = '"두 렌즈를 섞지 말 것"이라는 말도 있지만, 우리는 세 가지 렌즈로 이 시장을 본다.'
        hits = ll.find_hits(text, "column")
        self.assertEqual([h["headword"] for h in hits if h["headword"].startswith("렌즈")], ["렌즈"])
        self.assertEqual([h for h in hits if h["headword"].startswith("렌즈")][0]["count"], 1)

    def test_skip_genre_respected(self):
        lex = ll.load_lexicon()
        skipping = [e for e in lex["entries"] if "논문" in e.get("skip_genres", [])]
        if not skipping:
            self.skipTest("논문 생략 항목 없음")
        e = skipping[0]
        ids = {h["id"] for h in ll.find_hits(e["test_positive"], "abstract")}
        self.assertNotIn(e["id"], ids)

    def test_block_is_capped(self):
        lex = ll.load_lexicon()
        text = " ".join(e["test_positive"] for e in lex["entries"])
        block = ll.render_hint_block(ll.find_hits(text, "column"))
        self.assertLessEqual(block.count("\n- ["), ll.MAX_HINTS)
        self.assertIn("생략", block)


class RestoreTests(unittest.TestCase):
    BEFORE = "기존 규제에 새 의무가 하나 추가된다. 기업은 내년부터 보고서를 내야 한다."

    def test_new_change_word_sentence_restored(self):
        after = "기존 규제 위에 새 의무를 하나 얹는다. 기업은 내년부터 보고서를 내야 한다."
        fixed, restored, _ = ll.restore(self.BEFORE, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("추가된다", fixed)
        self.assertNotIn("얹는다", fixed)

    def test_word_already_in_source_untouched(self):
        before = "기존 규제 위에 새 의무를 얹는다. 기업은 내년부터 보고서를 내야 한다."
        after = "기존 규제 위에 새 의무를 얹는다. 기업은 내년부터 보고서를 꼭 내야 한다."
        fixed, restored, _ = ll.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(fixed, after)

    def test_no_restore_when_source_sentence_had_flagged_word(self):
        # 실측 회귀: 윤문이 '렌즈'를 '층위'로 바꿨을 때 되돌리면 '렌즈'가 부활한다 → 보류
        before = "두 렌즈를 섞지 말 것. 각각 따로 본다."
        after = "두 층위를 섞지 말 것. 각각 따로 본다."
        fixed, restored, skipped = ll.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(fixed, after)
        self.assertTrue(any("고치던 중" in s["reason"] for s in skipped))

    def test_summary_block_preserved(self):
        after = ("기존 규제 위에 새 의무를 하나 얹는다. 기업은 내년부터 보고서를 내야 한다.\n\n"
                 "<!-- HUMANIZE-SUMMARY\n원본: 얹는다\n-->\n")
        fixed, restored, _ = ll.restore(self.BEFORE, after)
        self.assertEqual(len(restored), 1)
        self.assertIn("<!-- HUMANIZE-SUMMARY", fixed)
        self.assertIn("원본: 얹는다", fixed)


class PrepareIntegrationTests(unittest.TestCase):
    def test_combined_input_carries_block_and_keeps_body(self):
        text = "이 교육은 직원의 잠재력을 잠금 해제한다. 꾸준히 기록하면 개인적인 성공을 달성할 수 있다.\n"
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "01_input.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "prepare_monolith_input.py"),
                            "--run-dir", d, "--genre", "column"], check=True, capture_output=True)
            combined = open(os.path.join(d, "01_input_with_metrics.txt"), encoding="utf-8").read()
        self.assertIn("[어휘 점검]", combined)
        self.assertLess(combined.index("[어휘 점검 끝]"), combined.index("[원문 시작]"))
        body = combined.split("[원문 시작]\n", 1)[1].split("\n[원문 끝]", 1)[0]
        self.assertEqual(body, text.rstrip("\n"))


if __name__ == "__main__":
    unittest.main()
