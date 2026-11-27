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

    @staticmethod
    def _how_pairs(how: str) -> list[tuple[str | None, str]]:
        """'방식' 문구의 (바꾸기 전, 예문) 쌍 — "A" → "B" 면 (A, B), 아니면 (None, 예문)."""
        import re

        seg = how.split("예)", 1)[1] if "예)" in how else ""
        out: list[tuple[str | None, str]] = []
        for part in seg.split(","):
            if "→" in part:
                left, right = part.split("→", 1)
                src = re.findall(r'"([^"]+)"', left)
                out += [(src[0] if src else None, t) for t in re.findall(r'"([^"]+)"', right)]
            else:
                out += [(None, t) for t in re.findall(r'"([^"]+)"', part)]
        return out

    @classmethod
    def _how_targets(cls, how: str) -> list[str]:
        return [t for _, t in cls._how_pairs(how)]

    def test_how_examples_do_not_inject_other_tells(self):
        """'방식' 예문이 AI 원문(test_positive)에 없던 다른 AI 티를 만들지 않는다.

        [어휘 점검] 블록은 전 경로 윤문 입력에 실리므로 예문이 곧 실행 지시다. 회귀 방지:
        L-53 예문 "규제는 더는 선택이 아니라는 뜻이다"가 C-8 대구와 I-3 결말을 새로 만들었다.
        AI 원문에 이미 있던 구조(예: INJ-14의 "자료가 아니라 직관에")는 물려받은 것이라 세지 않는다.
        """
        import re

        sys.path.insert(0, os.path.join(_ROOT, "skills", "humanize-korean", "references"))
        import metrics_v2 as m

        i3 = re.compile(r"[다라]는\s*(?:뜻|것)이다")

        def tells(t: str) -> tuple[set, int, int, int]:
            return ({h["id"] for h in ll.find_hits(t)}, m.antithesis_count(t),
                    t.count("결국"), len(i3.findall(t)))

        from verify_gates import count_modality

        for e in self.lex["entries"]:
            words0, anti0, gyeol0, i30 = tells(e["test_positive"])
            for genre, how in e["how"].items():
                for src, t in self._how_pairs(how):
                    with self.subTest(id=e["id"], genre=genre, example=t):
                        words, anti, gyeol, i3n = tells(t)
                        self.assertEqual(words - words0 - {e["id"]}, set(), "다른 사전 낱말")
                        self.assertLessEqual(anti, anti0, "C-8 대구 주입")
                        self.assertLessEqual(gyeol, gyeol0, "'결국' 주입(D-9)")
                        self.assertLessEqual(i3n, i30, "I-3 '~다는 뜻이다' 주입")
                        # 주장 강도 — 당위·완곡 표지 수가 바뀌면 서법이 바뀐 것이다(철칙: 강도 보존).
                        # P5 는 감소만 잡으므로 증가(강도 상향)는 여기서 막는다.
                        if e["id"] in self.MODALITY_DIFF_UNDER_REVIEW:
                            continue
                        base = src if src is not None else e["test_positive"]
                        self.assertEqual(count_modality(t), count_modality(base), "서법 표지 수 변경")

    # 예문이 AI 원문과 서법 표지 수가 다른 기존 항목 — 메인테이너 검토 대기(2026-11-27 정밀 검토).
    # 일부는 실제 강도 변경(L-04·L-06 '해야 한다' 추가, L-33 '수 있다' 추가)이고, 일부는 사전
    # 판정의 한계('알 수 있다'를 완곡으로 셈, 명사구 조각 예문)다. 새 항목은 이 목록에 넣지 않는다.
    MODALITY_DIFF_UNDER_REVIEW = frozenset({
        "AST-36", "AST-37", "AST-44", "AST-61",
        "L-04", "L-06", "L-13", "L-33", "L-51", "X-09",
    })

    def test_how_keeps_strength_and_conclusion_markers(self):
        """'방식'이 권고를 명령·청유로 올리거나 다른 귀결 표지로 바꿔 끼우라고 하지 않는다.

        회귀 방지: X-16 이 "~하는 편이 좋습니다" → "~하십시오"/"~하세요·~하자"(강도·register
        상향, 철칙 #5)를, L-78 이 "궁극적으로" → "결국"(D-9 주입 금지 위반)을 지시했다.
        """
        import re

        by_id = {e["id"]: e for e in self.lex["entries"]}
        for genre, how in by_id["X-16"]["how"].items():
            for t in self._how_targets(how):
                with self.subTest(genre=genre, example=t):
                    self.assertNotRegex(t, r"(?:하십시오|하세요|하자)$")
            self.assertNotIn('"~하세요", "~하자"처럼 직접 말한다', how)
        for genre, how in by_id["L-78"]["how"].items():
            with self.subTest(genre=genre):
                self.assertNotIn('"결국"으로', how)


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

    def test_no_restore_when_sentence_was_split(self):
        # 원문 한 문장이 둘로 쪼개진 경우 — 되돌리면 나머지 조각과 명제가 중복된다 → 보류
        before = "규제 비용이 늘면서 중소기업의 부담이 커졌다는 점이 분명히 드러난다."
        after = "규제 비용 위에 새 의무가 얹히면서 중소기업 부담이 커졌다. 이 점이 분명히 드러난다."
        fixed, restored, skipped = ll.restore(before, after)
        self.assertEqual(restored, [])
        self.assertEqual(fixed, after)
        self.assertTrue(any("분할" in s["reason"] for s in skipped), skipped)

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
