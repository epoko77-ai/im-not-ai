"""live 러너가 **이 레포**를 테스트하는지 — 결정적 계약(LLM 호출 없음).

실사고(2026-09-05): 러너 docstring 은 "레포 루트에서 실행하면 레포 스킬이 탐색된다"
고 적었지만 Claude Code 는 cwd 의 임의 `skills/` 를 보지 않는다. 이 머신의 개인
스킬이 2026-06 설치된 **v1.5.0** 이었고, live 스위트는 몇 달째 레포가 아니라 그
사본을 재고 있었다. `fx_guard_overedit` 3건이 브랜치와 무관하게 늘 실패한 이유다 —
레포 스킬(v2.4.0)을 실제로 로드하자 같은 픽스처가 통과했다.

이 테스트는 그 회귀를 코드로 막는다.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_RUNNER = os.path.join(_ROOT, "tests", "humanize_runner.py")


def _load():
    spec = importlib.util.spec_from_file_location("_runner", _RUNNER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class RunnerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = _load()
        with open(_RUNNER, encoding="utf-8") as f:
            self.src = f.read()

    def test_loads_repo_as_plugin(self) -> None:
        """전역 설치본이 아니라 레포를 로드해야 한다."""
        self.assertIn('"--plugin-dir"', self.src)

    def test_repo_skill_version_matches_manifest(self) -> None:
        """러너가 대사하는 기준값이 배포 매니페스트와 같은 값인지."""
        with open(os.path.join(_ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            manifest = json.load(f)["version"]
        self.assertEqual(self.m.repo_skill_version(), manifest)

    def test_prompt_requests_version_tag(self) -> None:
        """어느 사본이 응답했는지 출력으로 확인할 수 있어야 한다."""
        prompt = self.m._prompt("텍스트", False)
        self.assertIn("<<<V>>>", prompt)
        self.assertIn("version", prompt)

    def test_version_mismatch_is_not_silently_accepted(self) -> None:
        """버전이 어긋나면 통과가 아니라 '테스트 못 했다'로 끝나야 한다."""
        self.assertIn("SkillUnavailable", self.src)
        self.assertRegex(self.src, r"!=\s*레포 v|다른 사본이 응답했다")
        self.assertIsNotNone(self.m._VERSION_TAG.search("<<<V>>>2.4.0<<</V>>>"))
        self.assertIsNone(self.m._VERSION_TAG.search("버전 없음"))


class LiveGuardContractTests(unittest.TestCase):
    """live 테스트 클래스는 **전부** CLI 부재 시 skip 가드를 달아야 한다.

    실사고(2026-09-05): 영어 파이프라인 테스트에 가드를 빠뜨려, claude CLI 가 없는
    CI 에서 SKIP 대신 FAIL 이 났다. 로컬에서는 CLI 가 있어 보이지 않는 결함이다.
    """

    def test_every_live_testcase_has_a_skip_guard(self) -> None:
        import ast
        import glob

        checked = 0
        for path in glob.glob(os.path.join(_ROOT, "tests", "test_*.py")):
            if os.path.samefile(path, __file__):
                continue  # 이 계약 자체는 러너를 부르지 않는다(문자열만 검사)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                body = ast.unparse(node)
                # **파일 이름이 아니라 실제 호출로 판정한다.** 러너를 부르는
                # 클래스만 CLI 가 필요하다.
                if "run_humanize" not in body:
                    continue
                checked += 1
                decorators = [ast.unparse(d) for d in node.decorator_list]
                self.assertTrue(
                    any("skipIf" in d and "CLAUDE_BIN" in d for d in decorators),
                    f"{os.path.basename(path)}::{node.name} 에 CLI 부재 skip 가드가 없다",
                )
        self.assertGreaterEqual(checked, 2, "live 클래스를 하나도 못 찾았다 — 탐지가 깨졌다")

if __name__ == "__main__":
    unittest.main()
