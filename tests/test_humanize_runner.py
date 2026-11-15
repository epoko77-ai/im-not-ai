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


class GatedRunTests(unittest.TestCase):
    """Phase 2.5 강제 중단 분기 흉내 — LLM 대신 가짜 호출로 분기만 검증한다."""

    def setUp(self):
        self._orig = hr.run_humanize
        self.calls = []

    def tearDown(self):
        hr.run_humanize = self._orig

    def _fake(self, outputs):
        def fake(text, *, strict=False, timeout=300, model=None, rollback=False):
            self.calls.append(rollback)
            return outputs[len(self.calls) - 1]
        hr.run_humanize = fake

    def test_no_rollback_under_abort_threshold(self):
        src = "첫째 문장은 그대로 둔다. 둘째 문장도 거의 그대로다."
        self._fake(["첫째 문장은 그대로 둔다. 둘째 문장도 거의 같다."])
        out, rolled = hr.run_humanize_gated(src)
        self.assertFalse(rolled)
        self.assertEqual(self.calls, [False])

    def test_rollback_once_when_over_abort_threshold(self):
        src = "첫째 문장은 그대로 둔다. 둘째 문장도 거의 그대로다."
        self._fake(["완전히 다른 글이 나왔고 원문과 닮은 데가 하나도 없다.", "첫째 문장은 그대로 둔다. 둘째 문장도 거의 같다."])
        out, rolled = hr.run_humanize_gated(src)
        self.assertTrue(rolled)
        self.assertEqual(self.calls, [False, True])  # 두 번째 호출만 롤백 지시
        self.assertTrue(out.startswith("첫째 문장은"))

    def test_rollback_prompt_carries_no_fixture_answers(self):
        p = hr._prompt("본문", strict=False, rollback=True)
        self.assertIn("50%", p)  # 스킬 전역 상수(철칙 #4)만 — 픽스처별 상한·보호 토큰은 없다
        self.assertNotIn("protected", p)


@unittest.skipUnless(os.name == "posix", "가짜 CLI 를 sh 스크립트로 만든다")
class ExitCodeClassificationTests(unittest.TestCase):
    """CLI 종료 코드로 '실행 불가'와 '출력 계약 위반'을 가른다.

    실측: `claude` 가 깔려 있고 로그아웃된 환경에서 `claude -p` 는 stdout 에
    "Not logged in · Please run /login" 을 쓰고 exit 1 로 끝난다. 러너가 종료
    코드를 보지 않으면 이게 센티넬 파싱 실패 → SkillOutputInvalid(회귀)로
    분류돼 live 테스트가 skip 이 아니라 fail 로 끝난다.
    """

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_bin = hr.CLAUDE_BIN
        self.addCleanup(setattr, hr, "CLAUDE_BIN", self._orig_bin)

    def _fake_cli(self, stdout: str, code: int) -> None:
        path = os.path.join(self._tmp.name, "claude")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/sh\nprintf '%s\\n' '{stdout}'\nexit {code}\n")
        os.chmod(path, 0o755)
        hr.CLAUDE_BIN = path

    def test_logged_out_cli_is_unavailable_not_invalid(self):
        self._fake_cli("Not logged in · Please run /login", 1)
        with self.assertRaises(hr.SkillUnavailable) as cm:
            hr.run_humanize("문장입니다.")
        self.assertNotIsInstance(cm.exception, hr.SkillOutputInvalid)
        self.assertIn("Not logged in", str(cm.exception))

    def test_clean_exit_without_sentinel_is_still_invalid(self):
        # 정상 종료했는데 계약을 어긴 출력 — 회귀 신호는 그대로 실패로 남는다
        self._fake_cli("센티넬 없는 출력", 0)
        with self.assertRaises(hr.SkillOutputInvalid):
            hr.run_humanize("문장입니다.")

    def test_clean_exit_with_sentinel_returns_body(self):
        self._fake_cli("<<<H>>>본문<<</H>>>", 0)
        self.assertEqual(hr.run_humanize("문장입니다."), "본문")


if __name__ == "__main__":
    unittest.main()
