"""Codex standalone package regression tests.

The Codex skill is installed independently from the repository root.  Runtime
validation must therefore keep working after symlinks are materialized by
``install.sh --copy``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
_CODEX_SKILL = _ROOT / "codex" / "skills" / "humanize-korean"


class CodexRuntimePackageTests(unittest.TestCase):
    def _materialize_skill(self, destination: Path) -> Path:
        skill = destination / "humanize-korean"
        shutil.copytree(_CODEX_SKILL, skill, symlinks=False)
        return skill

    def test_change_rate_gate_runs_from_materialized_skill(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill = self._materialize_skill(root)

            self.assertFalse((skill / ".claude").exists())
            self.assertTrue((skill / "references" / "metrics_v2.py").is_file())
            gate = skill / "scripts" / "verify_change_rate.py"
            self.assertTrue(gate.is_file())
            self.assertTrue((skill / "scripts" / "console.py").is_file())

            before = root / "before.txt"
            after = root / "after.md"
            before.write_text(
                "운영 효율성을 가지고 있다. 처리 시간과 검토 절차는 유지한다.\n",
                encoding="utf-8",
            )
            after.write_text(
                "운영 효율성이 높다. 처리 시간과 검토 절차는 유지한다.\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    sys.executable,
                    str(gate),
                    "--before",
                    str(before),
                    "--after",
                    str(after),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("change_rate:", proc.stdout)
            self.assertIn("gate: OK", proc.stdout)
            self.assertNotIn("ModuleNotFoundError", proc.stderr)

    def test_codex_skill_requires_the_packaged_gate(self) -> None:
        text = (_CODEX_SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_workspace/{run_id}/01_input.txt", text)
        self.assertIn("$SKILL_DIR/scripts/verify_change_rate.py", text)
        self.assertIn("exit 0은 통과", text)
        self.assertIn("3은 검증 실패", text)


if __name__ == "__main__":
    unittest.main()
