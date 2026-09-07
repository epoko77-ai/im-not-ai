"""영어 파이프라인 end-to-end 스모크 — shim 부터 게이트 5종까지 실제로 도는지.

2026-09-05 이전까지 **영어 파이프라인은 통째로 돌아본 적이 없었다.** 단위
테스트는 전부 통과하는데 `_workspace` 에 영어 런이 하나도 없었고, 첫 수동 런에서
곧바로 결함이 나왔다(결합 파일이 한국어 규칙을 지시). LLM 없이 결정적으로
같은 경로를 밟는다 — 윤문 콜만 저장된 픽스처로 대체한다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_FIX = os.path.join(_ROOT, "tests", "fixtures", "en_pipeline")


def _sh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=180)


class PipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.mkdtemp(prefix="en_smoke_")
        for name in ("01_input.txt", "final.md"):
            shutil.copy(os.path.join(_FIX, name), os.path.join(cls.tmp, name))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _p(self, name: str) -> str:
        return os.path.join(self.tmp, name)

    def test_01_shim_produces_english_metrics(self) -> None:
        r = _sh(os.path.join(_ROOT, "scripts", "prepare_monolith_input.py"),
                "--run-dir", self.tmp, "--lang", "en")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self._p("00_metrics.json"), encoding="utf-8") as f:
            metrics = json.load(f)
        self.assertEqual(metrics["lang"], "en")
        self.assertIn(metrics["route_hint"], ("light", "standard", "heavy"))
        self.assertIn(metrics["threshold_set"], ("abstract", "blog"))

    def test_02_all_five_gates_pass(self) -> None:
        """게이트는 **파이프 없이** 종료코드를 받는다 — 파이프를 쓰면 tail 의 값을 읽는다."""
        gates = (
            (os.path.join(_ROOT, "scripts", "verify_change_rate.py"), []),
            (os.path.join(_ROOT, "core", "content_preservation.py"), []),
            (os.path.join(_ROOT, "core", "modality_loss.py"), []),
            (os.path.join(_ROOT, "core", "reinjection.py"), ["--lang", "en"]),
            (os.path.join(_ROOT, "core", "underedit.py"),
             ["--lang", "en", "--route-hint", "standard"]),
        )
        for gate, extra in gates:
            r = _sh(gate, "--before", self._p("01_input.txt"),
                    "--after", self._p("final.md"), *extra)
            self.assertEqual(r.returncode, 0,
                             f"{os.path.basename(gate)}: {r.stdout}{r.stderr}")

    def test_03_rewrite_moves_toward_human_range(self) -> None:
        """윤문본이 원문보다 사람 쪽으로 갔는지 — 라우터 재측정으로 본다."""
        sys.path[:0] = [os.path.join(_ROOT, "lang", "en"), os.path.join(_ROOT, "core")]
        from metrics_en import compute_all_en  # noqa: PLC0415

        order = {"light": 0, "standard": 1, "heavy": 2}
        with open(self._p("01_input.txt"), encoding="utf-8") as f:
            before = compute_all_en(f.read())
        with open(self._p("final.md"), encoding="utf-8") as f:
            after = compute_all_en(f.read())
        self.assertLess(order[after["route_hint"]], order[before["route_hint"]],
                        f"{before['route_hint']} → {after['route_hint']}")


if __name__ == "__main__":
    unittest.main()
