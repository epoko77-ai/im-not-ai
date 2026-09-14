"""--run-dir·--diagnosis 상대경로가 **cwd 기준**으로 풀리는지 검증 (#71).

배경: 예전에는 PROJECT_ROOT(설치 저장소 루트) 기준이었다. SKILL.md 는 "모든 경로는
cwd 기준"이라 지시하는데 스크립트는 저장소 루트에서 찾으니, 심링크로 설치해 사용자
작업 디렉터리에서 스킬을 부르는 정상 흐름이 첫 실행부터 실패했다. 저장소 루트에서
돌릴 때는 cwd == PROJECT_ROOT 라 아무도 눈치채지 못했다 — 그래서 회귀 테스트는
반드시 **저장소 밖 cwd** 에서 돌려야 의미가 있다.

실행: python3 -m pytest tests/test_run_dir_resolution.py -q
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SHIM = _ROOT / "scripts" / "prepare_monolith_input.py"

SAMPLE = "이것은 시험용 문장입니다. 첫째, 확인이 필요합니다. 둘째, 검증이 필요합니다."


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SHIM), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )


class RunDirResolutionTests(unittest.TestCase):
    def test_relative_run_dir_resolves_against_cwd(self) -> None:
        """저장소 밖 cwd 에서 상대 --run-dir 이 그 cwd 기준으로 풀려야 한다."""
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            run = work / "_workspace" / "2026-08-17-001"
            run.mkdir(parents=True)
            (run / "01_input.txt").write_text(SAMPLE, encoding="utf-8")

            proc = _run(["--run-dir", "_workspace/2026-08-17-001"], cwd=work)
            self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr}")
            # 결합 파일이 **사용자 작업 디렉터리** 아래 생겨야 한다
            self.assertTrue((run / "01_input_with_metrics.txt").is_file())
            self.assertIn(str(run), proc.stdout)

    def test_missing_run_dir_does_not_create_empty_dir(self) -> None:
        """존재하지 않는 run-dir 은 만들지 않고 실패해야 한다.

        예전에는 존재 확인 전에 mkdir 을 해서, 실패할 때마다 설치 위치에 빈
        `_workspace/{run_id}/` 가 쌓였다.
        """
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            proc = _run(["--run-dir", "_workspace/없는폴더"], cwd=work)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((work / "_workspace" / "없는폴더").exists())
            # 설치 저장소에도 남기지 않는다
            self.assertFalse((_ROOT / "_workspace" / "없는폴더").exists())

    def test_text_arg_creates_run_dir_under_cwd(self) -> None:
        """--text 는 cwd 아래에 새 run 디렉터리를 만든다."""
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            proc = _run(["--text", SAMPLE], cwd=work)
            self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr}")
            made = list((work / "_workspace").glob("*/01_input_with_metrics.txt"))
            self.assertEqual(len(made), 1, "cwd 아래에 run 디렉터리가 하나 생겨야 함")

    def test_relative_diagnosis_resolves_against_cwd(self) -> None:
        """--diagnosis 도 --run-dir 과 같은 기준(cwd)이어야 한다."""
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            run = work / "_workspace" / "2026-08-17-002"
            run.mkdir(parents=True)
            (run / "01_input.txt").write_text(SAMPLE, encoding="utf-8")
            diag = run / "02_diagnosis.md"
            diag.write_text("## 진단\n- C-8 대구 과잉\n", encoding="utf-8")

            proc = _run(
                [
                    "--run-dir",
                    "_workspace/2026-08-17-002",
                    "--diagnosis",
                    "_workspace/2026-08-17-002/02_diagnosis.md",
                ],
                cwd=work,
            )
            self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr}")
            combined = (run / "01_input_with_metrics.txt").read_text(encoding="utf-8")
            self.assertIn("C-8 대구 과잉", combined, "진단이 결합 파일에 실려야 함")

    def test_absolute_run_dir_still_works(self) -> None:
        """절대 경로는 그대로 쓴다 (기존 동작 보존)."""
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            run = work / "abs_run"
            run.mkdir()
            (run / "01_input.txt").write_text(SAMPLE, encoding="utf-8")
            # cwd 를 저장소 루트로 둬도 절대경로가 이겨야 한다
            proc = _run(["--run-dir", str(run)], cwd=_ROOT)
            self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr}")
            self.assertTrue((run / "01_input_with_metrics.txt").is_file())


if __name__ == "__main__":
    unittest.main()
