"""영어 golden 픽스처 — 게이트가 알려진 실패 모드를 실제로 잡는지.

한국어는 `tests/golden/fixtures/` + `scripts/checks.py` 로 출력 품질 회귀를 막는데
영어에는 그게 없었다. 픽스처 넷은 **실측된 실패 모드**에서 왔다(2026-09-05 효능 측정):

- 01 서법 평탄화 — 룰북 팔 21%
- 02 내용 훼손 — 맨 프롬프트 팔 43%
- 03 역주입 — 맨 프롬프트 팔 79%
- 04 과소윤문 — 룰북 팔 21%

`good_output` 은 전 게이트를 통과해야 하고, `bad_output` 은 지목된 게이트에서
정확히 실패해야 한다. 방향성 게이트이지 정답 문자열 대조가 아니다.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_FIXTURES = sorted(glob.glob(os.path.join(_HERE, "golden", "fixtures_en", "*")))

# 게이트 코드 → (스크립트 경로, 추가 인자)
_GATES = {
    "content_preservation": (os.path.join(_ROOT, "core", "content_preservation.py"), []),
    "modality_loss": (os.path.join(_ROOT, "core", "modality_loss.py"), []),
    "reinjection": (os.path.join(_ROOT, "core", "reinjection.py"), ["--lang", "en"]),
    "underedit": (
        os.path.join(_ROOT, "core", "underedit.py"),
        ["--lang", "en", "--genre", "blog", "--route-hint", "standard"],
    ),
}


def _run(code: str, before: str, after: str) -> subprocess.CompletedProcess:
    script, extra = _GATES[code]
    return subprocess.run(
        [sys.executable, script, "--before", before, "--after", after] + extra,
        capture_output=True, text=True, timeout=120,
    )


class GoldenEnTests(unittest.TestCase):
    def test_fixtures_exist(self) -> None:
        self.assertGreaterEqual(len(_FIXTURES), 4, "영어 golden 픽스처가 없다")

    def test_good_output_passes_every_gate(self) -> None:
        for d in _FIXTURES:
            src = os.path.join(d, "input.txt")
            good = os.path.join(d, "good_output.txt")
            for code in _GATES:
                with self.subTest(fixture=os.path.basename(d), gate=code):
                    r = _run(code, src, good)
                    self.assertEqual(
                        r.returncode, 0,
                        f"good_output 이 {code} 에서 실패했다\n{r.stdout}{r.stderr}",
                    )

    def test_bad_output_fails_the_named_gate(self) -> None:
        for d in _FIXTURES:
            with open(os.path.join(d, "expected_failures.json"), encoding="utf-8") as f:
                spec = json.load(f)
            src = os.path.join(d, "input.txt")
            bad = os.path.join(d, "bad_output.txt")
            for code in spec["bad_must_fail"]:
                with self.subTest(fixture=os.path.basename(d), gate=code):
                    r = _run(code, src, bad)
                    self.assertEqual(
                        r.returncode, 1,
                        f"bad_output 을 {code} 가 잡지 못했다\n{r.stdout}{r.stderr}",
                    )


if __name__ == "__main__":
    unittest.main()
