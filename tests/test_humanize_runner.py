"""humanize_runner 센티넬 파싱 — LLM 없이 도는 단위 테스트."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import humanize_runner as hr  # noqa: E402


class SentinelTests(unittest.TestCase):
    def _parse(self, out: str) -> str | None:
        m = hr._SENTINEL.search(out)
        return m.group(1).strip() if m else None

    def test_exact_sentinel(self):
        self.assertEqual(self._parse("설명\n<<<H>>>\n본문이다.\n<<</H>>>\n끝"), "본문이다.")

    def test_short_closing_sentinel_seen_in_live_runs(self):
        # 실측: 모델이 닫는 표지를 `<</H>>>`로 썼다 — 본문은 멀쩡하다
        self.assertEqual(self._parse("<<<H>>>\n아 오늘 회의 길었다.\n<</H>>>\n"), "아 오늘 회의 길었다.")
        self.assertEqual(self._parse("<<<H>>>본문<<</H>>"), "본문")

    def test_no_stray_bracket_in_body(self):
        self.assertEqual(self._parse("<<<H>>>본문<<</H>>>"), "본문")

    def test_missing_closing_sentinel_still_fails(self):
        self.assertIsNone(self._parse("<<<H>>>\n본문만 있고 닫는 표지가 없다."))
        self.assertIsNone(self._parse("본문만 있다."))


if __name__ == "__main__":
    unittest.main()
