"""프로덕션 런타임이 tests/ 트리에 의존하지 않는지 검증 (#59).

배경: `scripts/verify_gates.py`(프로덕션 게이트)가 `tests/golden/checks.py` 를
런타임에 import 하고 있었다. 저장소 전체를 배포하는 Claude Code 설치에서는
동작하지만, 런타임 파일만 선별 배포하는 구조(포트·zip·심링크 부분 배포)에서는
**P3 golden 축이 통째로 죽는다**. 게이트가 조용히 한 축을 잃는 것이 가장 나쁘다.

checks.py 는 이름만 tests 아래 있었을 뿐 내용은 전부 프로덕션 검사 로직
(register·heading·footnote·number·quote)이라 `scripts/` 로 옮겼다.

이 테스트는 그 경계가 다시 무너지면 실패한다.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SCRIPTS = _ROOT / "scripts"

# 프로덕션 런타임에 해당하는 스크립트(스킬이 Bash 로 직접 부르는 것들)
_RUNTIME_SCRIPTS = [
    "verify_gates.py",
    "verify_change_rate.py",
    "prepare_monolith_input.py",
    "reassemble_chunks.py",
    "sanitize_text.py",
    "checks.py",
]


class RuntimeBoundaryTests(unittest.TestCase):
    def test_runtime_scripts_do_not_reference_tests_tree(self) -> None:
        """런타임 스크립트 소스에 tests/ 경로 조립이 없어야 한다."""
        offenders: list[str] = []
        for name in _RUNTIME_SCRIPTS:
            p = _SCRIPTS / name
            if not p.is_file():
                continue
            src = p.read_text(encoding="utf-8")
            for lineno, line in enumerate(src.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue  # 주석의 이력 서술은 허용
                if '"tests"' in line or "'tests'" in line or "tests/golden" in line:
                    offenders.append(f"{name}:{lineno}: {stripped[:90]}")
        self.assertEqual(offenders, [], "런타임이 tests/ 를 참조함:\n" + "\n".join(offenders))

    def test_checks_lives_in_scripts(self) -> None:
        """checks.py 는 프로덕션 위치에 있어야 한다."""
        self.assertTrue((_SCRIPTS / "checks.py").is_file(), "scripts/checks.py 가 없음")
        self.assertFalse(
            (_ROOT / "tests" / "golden" / "checks.py").is_file(),
            "tests/golden/checks.py 가 되살아남 — 프로덕션 구현은 scripts/ 에 둔다",
        )

    def test_verify_gates_runs_without_tests_dir(self) -> None:
        """tests/ 를 뺀 선별 배포에서도 게이트 전 축이 동작해야 한다 (#59 핵심)."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "scripts").mkdir()
            for f in _SCRIPTS.glob("*.py"):
                (d / "scripts" / f.name).write_bytes(f.read_bytes())
            refs_src = _ROOT / "skills" / "humanize-korean" / "references"
            refs_dst = d / "skills" / "humanize-korean" / "references"
            refs_dst.mkdir(parents=True)
            for f in refs_src.iterdir():
                if f.is_file():
                    (refs_dst / f.name).write_bytes(f.read_bytes())

            self.assertFalse((d / "tests").exists(), "tests/ 가 없어야 하는 조건")

            (d / "before.txt").write_text(
                "원문은 이러하다. 수치는 1,200명이다.", encoding="utf-8"
            )
            (d / "after.txt").write_text(
                "원문은 이렇다. 수치는 1,200명이다.", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, "scripts/verify_gates.py", "--before", "before.txt",
                 "--after", "after.txt"],
                cwd=d, capture_output=True, text=True, timeout=120,
            )
            self.assertIn("[P3 golden]", proc.stdout, f"golden 축 누락\n{proc.stdout}\n{proc.stderr}")
            self.assertNotIn("ModuleNotFoundError", proc.stderr)
            self.assertIn(proc.returncode, (0, 1), f"예상치 못한 종료: {proc.returncode}\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()


class FinalizeContractTests(unittest.TestCase):
    """Light 승급 시 diagnosis_path 계약 (#54).

    Light 는 02_diagnosis.md 를 만들지 않는데 승급 규칙은 전 경로 공통이라,
    finalizer 가 진단을 필수로 요구하면 Light 승급 경로가 실행 불가가 된다.
    """

    def test_finalizer_marks_diagnosis_optional(self) -> None:
        t = (_ROOT / "agents" / "humanize-finalizer.md").read_text(encoding="utf-8")
        self.assertIn("`diagnosis_path`(**선택**)", t, "diagnosis_path 가 선택으로 표기돼야 함")
        self.assertIn("Light 경로는 진단을 생략하므로", t)

    def test_skill_documents_light_escalation(self) -> None:
        t = (_ROOT / "skills" / "humanize-korean" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("진단 파일이 없을 때(Light 승급)", t)
        self.assertIn("`diagnosis_path` 없이", t)


class PluginLayoutTests(unittest.TestCase):
    """플러그인 스킬이 관례 위치에 있는지 검증.

    ## 배경

    공식 스펙: `skills/` 는 **플러그인 루트**에 있어야 하고, 로더는 그곳을 기본 스캔한다.
    `plugin.json` 의 `skills` 필드로 다른 경로를 가리킬 수 있지만 예외가 있다 —
    **marketplace 항목의 `source` 가 마켓플레이스 루트로 풀리면, 선언한 하위
    디렉터리가 기본 `skills/` 스캔을 대체한다.**

    우리 `marketplace.json` 의 `source` 는 `"./"` 라 정확히 그 예외에 해당했다.
    그래서 `.claude/skills/` 에 두고 매니페스트로 가리키던 구조에서는, 매니페스트를
    읽는 로더(Claude Code CLI)는 찾지만 관례 위치만 스캔하는 로더는 스킬을 하나도
    못 찾았다(Cowork 사용자 제보).

    에이전트는 같은 이유로 이미 루트 `agents/` 로 옮긴 적이 있다(#26). 스킬만
    남아 있었다.
    """

    def test_skills_live_at_plugin_root(self) -> None:
        self.assertTrue(
            (_ROOT / "skills").is_dir(),
            "스킬은 플러그인 루트 skills/ 에 있어야 한다 (로더 기본 스캔 위치)",
        )
        for name in ("humanize-korean", "humanize", "humanize-scan", "humanize-redo"):
            with self.subTest(skill=name):
                self.assertTrue((_ROOT / "skills" / name / "SKILL.md").is_file())

    def test_old_location_is_gone(self) -> None:
        self.assertFalse(
            (_ROOT / ".claude" / "skills").exists(),
            ".claude/skills/ 가 되살아남 — 두 곳에 있으면 로더마다 다른 사본을 읽는다",
        )

    def test_manifest_does_not_override_default_scan(self) -> None:
        """`skills` 필드를 다시 넣으면 기본 스캔이 대체돼 같은 사고가 재발한다."""
        import json  # noqa: PLC0415

        manifest = json.loads(
            (_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertNotIn(
            "skills", manifest,
            "plugin.json 에 skills 필드를 두지 않는다 — 루트 skills/ 기본 스캔에 맡긴다",
        )

    def test_skill_root_derivation_is_depth_independent(self) -> None:
        """SKILL.md 의 SKILL_ROOT 유도가 고정 깊이(../../..)를 쓰면 안 된다."""
        skill = (_ROOT / "skills" / "humanize-korean" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(".claude-plugin", skill, "마커 기반 탐색이 명시돼야 함")
        self.assertNotIn(
            "cd ../../..", skill,
            "고정 깊이 유도 잔존 — 레이아웃이 바뀌면 조용히 엉뚱한 곳을 가리킨다",
        )
