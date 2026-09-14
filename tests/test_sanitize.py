"""scripts/sanitize_text.py 회귀 테스트.

이 테스트 소스도 비가시 문자를 리터럴로 쓰지 않는다 — 전부 chr() 로 만든다.
imnotai-web/scripts/test-sanitize.ts 와 같은 케이스를 공유한다 (쌍둥이 구현 고정).

실행: python3 -m pytest tests/test_sanitize.py -q
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import sanitize_text as st  # noqa: E402

ZWSP = chr(0x200B)
BOM = chr(0xFEFF)
SHY = chr(0x00AD)
WJ = chr(0x2060)
NBSP = chr(0x00A0)
IDEO = chr(0x3000)
NARROW_NBSP = chr(0x202F)
RLO = chr(0x202E)
LRM = chr(0x200E)
ZWJ = chr(0x200D)
ZWNJ = chr(0x200C)
TAG_A = chr(0xE0061)
LINE_SEP = chr(0x2028)
PARA_SEP = chr(0x2029)


class SanitizeTests(unittest.TestCase):
    # ── 1. 정상 한국어는 건드리지 않는다 (가장 중요) ──────────────────
    def test_clean_korean_untouched(self):
        clean = "\n".join(
            [
                "AI가 쓴 글을 사람 글처럼 다듬습니다.",
                "",
                "첫째, 번역투를 걷어냅니다. 둘째, 리듬을 살립니다.",
                "가격은 1,200원이며 — 부가세 별도입니다.",
                '그는 "그렇게는 못 한다"고 잘라 말했다.',
                "이모지도 그대로: 👨" + ZWJ + "👩" + ZWJ + "👧 가족",
            ]
        )
        out, rep = st.sanitize(clean)
        self.assertEqual(out, clean)
        self.assertFalse(rep.changed)
        self.assertEqual(rep.summary, "")

    # ── 2. 제로폭·BOM·소프트하이픈·워드조이너 제거 ────────────────────
    def test_invisible_removed(self):
        dirty = "안" + ZWSP + "녕" + BOM + "하" + SHY + "세" + WJ + "요"
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "안녕하세요")
        self.assertEqual(rep.counts["invisible"], 4)
        self.assertLess(rep.after_chars, rep.before_chars)

    # ── 3. 이모지 ZWJ 보존 / 한글 사이 ZWJ 제거 ───────────────────────
    def test_emoji_zwj_preserved(self):
        emoji = "👨" + ZWJ + "👩" + ZWJ + "👧"
        out, _ = st.sanitize(emoji)
        self.assertEqual(out, emoji)

    def test_hangul_joiner_removed(self):
        dirty = "한" + ZWJ + "글" + ZWNJ + "테스트"
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "한글테스트")
        self.assertEqual(rep.counts["invisible"], 2)

    # ── 4. bidi 제어 문자 ─────────────────────────────────────────────
    def test_bidi_removed(self):
        dirty = "정상" + RLO + "뒤집기" + LRM + "끝"
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "정상뒤집기끝")
        self.assertEqual(rep.counts["bidi"], 2)

    # ── 5. 태그 문자(숨은 텍스트) ─────────────────────────────────────
    def test_tag_chars_removed(self):
        dirty = "본문" + TAG_A + TAG_A + "끝"
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "본문끝")
        self.assertEqual(rep.counts["tag_chars"], 2)

    # ── 6. 한글 NFD → NFC ─────────────────────────────────────────────
    def test_nfc_normalization(self):
        import unicodedata

        nfd = unicodedata.normalize("NFD", "한글 테스트")
        self.assertNotEqual(nfd, "한글 테스트")
        out, rep = st.sanitize(nfd)
        self.assertEqual(out, "한글 테스트")
        self.assertEqual(rep.counts["hangul_recomposed"], 5)  # 한·글·테·스·트

    # ── 7. 특수 공백 (전각공백은 기본 보존) ───────────────────────────
    def test_special_spaces(self):
        dirty = "가" + NBSP + "나" + IDEO + "다" + NARROW_NBSP + "라"
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "가 나" + IDEO + "다 라")
        self.assertEqual(rep.counts["special_spaces"], 2)
        self.assertIn(IDEO, out, "전각공백은 기본 보존")

    def test_ideographic_space_opt_in(self):
        out, rep = st.sanitize("가" + IDEO + "나", normalize_ideographic_space=True)
        self.assertEqual(out, "가 나")
        self.assertEqual(rep.counts["special_spaces"], 1)

    # ── 8. 줄바꿈·줄 끝 공백 (빈 줄은 기본 보존) ──────────────────────
    def test_line_normalization(self):
        dirty = (
            "첫 줄   \r\n둘째 줄" + LINE_SEP + "셋째 줄" + PARA_SEP + "\n\n\n\n넷째 줄"
        )
        out, rep = st.sanitize(dirty)
        self.assertEqual(out, "첫 줄\n둘째 줄\n셋째 줄\n\n\n\n\n넷째 줄")
        self.assertGreaterEqual(rep.counts["line_breaks"], 3)
        self.assertGreaterEqual(rep.counts["trailing_space_lines"], 1)

    def test_collapse_blank_lines_opt_in(self):
        self.assertEqual(st.sanitize("가\n\n\n\n나", collapse_blank_lines=True)[0], "가\n\n나")
        self.assertEqual(st.sanitize("가\n\n\n\n나")[0], "가\n\n\n\n나")

    # ── 9. 멱등성 ─────────────────────────────────────────────────────
    def test_idempotent(self):
        import unicodedata

        dirty = (
            "안" + ZWSP + "녕" + NBSP + "하세요" + RLO + "\r\n\r\n\r\n"
            + unicodedata.normalize("NFD", "둘째") + "   \n" + TAG_A
        )
        once, _ = st.sanitize(dirty)
        twice, rep2 = st.sanitize(once)
        self.assertEqual(twice, once)
        self.assertFalse(rep2.changed)

    # ── 10. 옵션 개별 off ─────────────────────────────────────────────
    def test_options(self):
        dirty = "가" + NBSP + "나" + ZWSP + "다"
        only_spaces, _ = st.sanitize(dirty, strip_invisible=False)
        self.assertIn(ZWSP, only_spaces)
        self.assertEqual(only_spaces, "가 나" + ZWSP + "다")

        only_invis, _ = st.sanitize(dirty, normalize_spaces=False)
        self.assertIn(NBSP, only_invis)

    # ── 11. 보호 대상 — 철칙 #1 (의미 불변) ───────────────────────────
    def test_protected_tokens_survive(self):
        src = (
            "2026년 8월 2일, EU AI Act 발효." + ZWSP + " 앤트로픽은 " + NBSP
            + '"별도 문자를 추가하지 않는다"고 밝혔다. 수치는 4,500개.'
        )
        out, _ = st.sanitize(src)
        for tok in [
            "2026",
            "8월 2일",
            "EU AI Act",
            "앤트로픽",
            "4,500",
            "별도 문자를 추가하지 않는다",
        ]:
            self.assertIn(tok, out, f"보호 토큰 유실: {tok}")

    # ── 12. inspect 는 원본을 바꾸지 않는다 ───────────────────────────
    def test_inspect_pure(self):
        dirty = "가" + ZWSP + "나"
        rep = st.inspect(dirty)
        self.assertTrue(rep.changed)
        self.assertTrue(rep.summary)

    # ── 13. 빈 입력 ───────────────────────────────────────────────────
    def test_empty(self):
        out, rep = st.sanitize("")
        self.assertEqual(out, "")
        self.assertFalse(rep.changed)
        self.assertEqual(st.sanitize("   \n  \n")[0], "\n\n")

    # ── 14. 소스 자체에 리터럴 비가시 문자가 없어야 한다 ──────────────
    def test_source_has_no_literal_invisibles(self):
        import unicodedata

        here = os.path.dirname(os.path.abspath(__file__))
        target = os.path.join(here, "..", "scripts", "sanitize_text.py")
        with open(target, encoding="utf-8") as f:
            src = f.read()
        bad = [
            (i, hex(ord(ch)))
            for i, ch in enumerate(src)
            if ch not in "\n\t"
            and (
                unicodedata.category(ch) in ("Cf", "Cc", "Co", "Cs")
                or ord(ch) in (0xA0, 0x3000, 0x2028, 0x2029)
                or 0x2000 <= ord(ch) <= 0x200F
            )
        ]
        self.assertEqual(bad, [], f"소스에 리터럴 비가시 문자: {bad[:10]}")


if __name__ == "__main__":
    unittest.main()
