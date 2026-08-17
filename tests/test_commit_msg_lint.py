"""scripts/commit_msg_lint.py 회귀 테스트.

이 스크립트는 `.githooks/commit-msg`가 커밋마다 실행하는 유일한 게이트라
(exit code는 훅에서 무시되지만) 패턴 검출·스킵 로직 자체가 깨지면 아무도
경고를 못 받는다. golden_commit 게이트(tests/test_golden_commit.py)는
"윤문 결과가 원문을 훼손하지 않았는가"를 보고, 이 테스트는 "린터가 실제로
lexicon §1~5 패턴을 잡아내는가"를 본다 — 대상이 다르다.

pytest / unittest 양쪽에서 실행된다.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def _load_linter():
    path = os.path.join(SCRIPTS, "commit_msg_lint.py")
    spec = importlib.util.spec_from_file_location("commit_msg_lint", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    # dataclasses(3.12)가 __module__ 해석 시 sys.modules를 조회한다 —
    # exec 전에 등록해야 `@dataclass` 클래스(Finding)가 깨지지 않는다.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class ScanPatternTests(unittest.TestCase):
    """lexicon §1~5의 각 패턴이 실제로 검출되는지 — 코드 단위로 하나씩."""

    def setUp(self) -> None:
        self.linter = _load_linter()

    def test_bureaucratic_verb_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("fix: 재시도 로직을 진행함")}
        self.assertIn("bureaucratic_verb", codes)

    def test_wordy_completion_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("fix: 버그 수정 작업을 완료함")}
        self.assertIn("wordy_completion", codes)

    def test_over_polite_ending_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("docs: 오탈자를 수정하였습니다")}
        self.assertIn("over_polite_ending", codes)

    def test_double_passive_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("fix: 설정값이 검증되어지는 로직 추가")}
        self.assertIn("double_passive", codes)

    def test_by_passive_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("fix: 사용자에 의해 트리거되는 버그 수정")}
        self.assertIn("by_passive", codes)

    def test_have_literal_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("feat: 새 캐시 레이어를 가지도록 구조 변경")}
        self.assertIn("have_literal", codes)

    def test_automated_passive_detected(self) -> None:
        codes = {f.code for f in self.linter.scan("fix: 테스트가 실패하게 되는 원인 제거")}
        self.assertIn("automated_passive", codes)

    def test_clean_message_no_findings(self) -> None:
        self.assertEqual(self.linter.scan("fix(auth): 재시도 로직 추가"), [])

    def test_multiple_patterns_all_reported(self) -> None:
        codes = {
            f.code
            for f in self.linter.scan("fix: 버그 수정 작업을 완료하였습니다")
        }
        self.assertIn("wordy_completion", codes)
        self.assertIn("over_polite_ending", codes)


class SkipLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.linter = _load_linter()

    def test_skip_marker_in_message(self) -> None:
        self.assertTrue(
            self.linter.should_skip("fix: 버그 수정을 진행함 [skip-commit-ko]")
        )

    def test_env_var_skip(self) -> None:
        os.environ[self.linter.SKIP_ENV] = "1"
        try:
            self.assertTrue(self.linter.should_skip("fix: 버그 수정을 진행함"))
        finally:
            del os.environ[self.linter.SKIP_ENV]

    def test_merge_commit_auto_skipped(self) -> None:
        self.assertTrue(
            self.linter.should_skip("Merge pull request #1 from x/y\n\n버그 수정을 진행함")
        )

    def test_revert_commit_auto_skipped(self) -> None:
        self.assertTrue(self.linter.should_skip('Revert "fix: 버그 수정을 진행함"'))

    def test_fixup_commit_auto_skipped(self) -> None:
        self.assertTrue(self.linter.should_skip("fixup! fix: 버그 수정을 진행함"))

    def test_squash_commit_auto_skipped(self) -> None:
        self.assertTrue(self.linter.should_skip("squash! fix: 버그 수정을 진행함"))

    def test_normal_commit_not_skipped(self) -> None:
        self.assertFalse(self.linter.should_skip("fix: 버그 수정을 진행함"))

    def test_skip_short_circuits_scan(self) -> None:
        self.assertEqual(
            self.linter.scan("fix: 버그 수정을 진행함 [skip-commit-ko]"), []
        )


class CommentStripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.linter = _load_linter()

    def test_comment_lines_ignored(self) -> None:
        text = "fix: 버그 수정을 진행함\n# Please enter the commit message...\n# 진행함"
        codes = {f.code for f in self.linter.scan(text)}
        self.assertIn("bureaucratic_verb", codes)
        self.assertEqual(len(codes), 1)


class MainCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.linter = _load_linter()

    def _write(self, text: str) -> str:
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_main_returns_1_on_findings(self) -> None:
        path = self._write("fix: 버그 수정을 진행함")
        self.assertEqual(self.linter.main(["prog", path]), 1)

    def test_main_returns_0_on_clean_message(self) -> None:
        path = self._write("fix(auth): 재시도 로직 추가")
        self.assertEqual(self.linter.main(["prog", path]), 0)

    def test_main_returns_2_on_bad_usage(self) -> None:
        self.assertEqual(self.linter.main(["prog"]), 2)


if __name__ == "__main__":
    unittest.main()
