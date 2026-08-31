"""run 디렉터리 배정의 동시성 회귀 테스트.

배경: `_next_run_dir` 이 `exists()` 로 빈 자리를 확인만 하고 실제 생성은 호출부가
나중에 했다. 그 틈에 다른 프로세스가 같은 이름을 잡으면 두 실행이 한 디렉터리를
공유하고, 뒤에 온 쪽이 앞선 쪽의 `01_input.txt` 를 덮어쓴다. 그러면 게이트가
*남의 원문과 내 윤문본*을 비교해 있지도 않은 제목·인용이 사라졌다며 ABORT 를 낸다.

Runs under pytest OR `python -m unittest`.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from prepare_monolith_input import _next_run_dir  # noqa: E402


class NextRunDirTests(unittest.TestCase):
    def test_sequential_allocation_increments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "_workspace"
            today = date.today().isoformat()
            first = _next_run_dir(ws)
            second = _next_run_dir(ws)
            self.assertEqual(first.name, f"{today}-001")
            self.assertEqual(second.name, f"{today}-002")

    def test_allocation_creates_the_directory(self) -> None:
        """배정과 동시에 실물 디렉터리가 있어야 한다 — 확인·생성 사이의 틈을 없앤다."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "_workspace"
            self.assertTrue(_next_run_dir(ws).is_dir())

    def test_concurrent_allocation_never_collides(self) -> None:
        """동시 배정 N건 → 서로 다른 디렉터리 N개. 옛 로직은 전부 -001 을 받았다."""
        workers = 16
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "_workspace"
            ws.mkdir(parents=True, exist_ok=True)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                dirs = list(pool.map(lambda _: _next_run_dir(ws), range(workers)))
            self.assertEqual(len(dirs), workers)
            self.assertEqual(len({d.name for d in dirs}), workers)

    def test_session_tag_keeps_sessions_apart(self) -> None:
        """세션 태그가 다르면 같은 NNN 이어도 서로 다른 디렉터리다."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "_workspace"
            today = date.today().isoformat()
            a = _next_run_dir(ws, "a3f9")
            b = _next_run_dir(ws, "b7c2")
            self.assertEqual(a.name, f"{today}-001-a3f9")
            self.assertEqual(b.name, f"{today}-001-b7c2")
            self.assertNotEqual(a, b)

    def test_tagged_and_untagged_do_not_clash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "_workspace"
            today = date.today().isoformat()
            plain = _next_run_dir(ws)
            tagged = _next_run_dir(ws, "a3f9")
            self.assertEqual(plain.name, f"{today}-001")
            self.assertEqual(tagged.name, f"{today}-001-a3f9")


if __name__ == "__main__":
    unittest.main()
