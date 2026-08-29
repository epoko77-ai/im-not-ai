"""Codex skill packaging and standalone-copy regression tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex" / "skills" / "humanize-korean"


class CodexPackageTests(unittest.TestCase):
    def test_required_package_files_exist(self) -> None:
        required = [
            "SKILL.md",
            "agents/openai.yaml",
            "scripts/prepare_monolith_input.py",
            "scripts/reassemble_chunks.py",
            "scripts/verify_change_rate.py",
            "scripts/verify_gates.py",
            "references/quick-rules.md",
            "references/diagnosis-rules.md",
            "references/roles/diagnostician.md",
            "references/roles/monolith.md",
            "references/roles/finalizer.md",
        ]
        for relative in required:
            self.assertTrue((SKILL / relative).is_file(), relative)

        contract = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("단일 청크에서도 이 단계를 생략하지 않는다", contract)
        self.assertIn("summary가 없으므로 finalizer", contract)
        self.assertIn('SKILL_ROOT="$(cd -P', contract)
        self.assertNotIn("$SKILL_DIR/scripts/", contract)
        self.assertGreaterEqual(contract.count("${SKILL_ROOT}/scripts/"), 5)

    def test_source_wrapper_runs_from_foreign_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            run_dir.mkdir()
            (run_dir / "01_input.txt").write_text("테스트 문장입니다.", encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(SKILL / "scripts" / "prepare_monolith_input.py"),
                    "--run-dir",
                    str(run_dir),
                    "--genre",
                    "essay",
                ],
                cwd=td,
                check=True,
                capture_output=True,
                text=True,
            )
            metrics = json.loads((run_dir / "00_metrics.json").read_text(encoding="utf-8"))
            self.assertIn(metrics["route_hint"], {"light", "standard", "heavy"})

    def test_copy_install_is_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            codex_home.mkdir(parents=True)
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--copy"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = codex_home / "skills" / "humanize-korean"
            self.assertFalse((installed / "references").is_symlink())
            self.assertIn("METRICS_DIR", (installed / "scripts" / "prepare_monolith_input.py").read_text())
            self.assertTrue((installed / "scripts" / "checks.py").is_file())
            self.assertTrue((installed / "scripts" / "console.py").is_file())
            run_dir = Path(td) / "outside" / "run"
            run_dir.mkdir(parents=True)
            (run_dir / "01_input.txt").write_text("복사 설치 테스트입니다.", encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(installed / "scripts" / "prepare_monolith_input.py"),
                    "--run-dir",
                    str(run_dir),
                    "--genre",
                    "essay",
                ],
                cwd=run_dir.parent,
                check=True,
                capture_output=True,
                text=True,
            )
            shutil.copy(run_dir / "01_input.txt", run_dir / "final.md")
            gate = subprocess.run(
                [
                    "python3",
                    str(installed / "scripts" / "verify_gates.py"),
                    "--before",
                    str(run_dir / "01_input.txt"),
                    "--after",
                    str(run_dir / "final.md"),
                    "--genre",
                    "essay",
                ],
                cwd=run_dir.parent,
                capture_output=True,
                text=True,
            )
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)

    def test_copy_install_backs_up_existing_symlink_outside_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            installed = codex_home / "skills" / "humanize-korean"
            installed.parent.mkdir(parents=True)
            installed.symlink_to(SKILL)
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--copy"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(installed.is_dir())
            self.assertFalse(installed.is_symlink())
            self.assertEqual(list(installed.parent.glob("humanize-korean*")), [installed])
            backups = list((codex_home / "backups").glob("*/skills/humanize-korean"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].is_symlink())

    def test_force_install_backs_up_directory_outside_skills(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td) / "home"
            codex_home = fake_home / ".codex"
            installed = codex_home / "skills" / "humanize-korean"
            installed.mkdir(parents=True)
            (installed / "sentinel.txt").write_text("keep me", encoding="utf-8")
            env = os.environ.copy()
            env.update({"HOME": str(fake_home), "CODEX_HOME": str(codex_home)})
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), "--codex-only", "--force"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(installed.is_symlink())
            self.assertEqual(list(installed.parent.glob("humanize-korean*")), [installed])
            backups = list((codex_home / "backups").glob("*/skills/humanize-korean"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(
                (backups[0] / "sentinel.txt").read_text(encoding="utf-8"), "keep me"
            )


if __name__ == "__main__":
    unittest.main()
