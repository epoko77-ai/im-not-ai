"""스크립트 사슬 통합 테스트 — LLM 없이 실제 픽스처로 결정적 단계를 끝까지 돌린다.

왜 필요한가: 라이브 층(test_humanize_live.py)은 `claude -p` 비대화형 실행이라 권한이
필요한 도구를 쓰지 않도록 "파일은 만들지 마"로 호출한다. 그래서 스킬의 스크립트 단계
(입력 shim·서법 복원·쉼표 역주입 제거·어휘 복원·구조 게이트)는 라이브 층에서 한 번도
돌지 않는다. v2.4 어휘 레이어를 검증하다 이 사각지대가 드러났다 — 스크립트 단계의
효과를 재려면 light 경로를 손으로 단계별 실행해야 했다.

이 테스트는 그 사슬을 SKILL.md 순서 그대로 돌린다:
  01_input.txt → prepare_monolith_input.py → (얼린 윤문본 = final.md)
  → restore_modality.py → strip_injected_commas.py → lexical_layer.py restore
  → verify_gates.py
모델 출력은 fixtures.json의 output_text(얼린 윤문본)로 대신한다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_S = os.path.join(_ROOT, "scripts")
sys.path.insert(0, _HERE)
import humanize_asserts as ha  # noqa: E402

with open(os.path.join(_HERE, "fixtures.json"), encoding="utf-8") as _f:
    _FIXTURES = [fx for fx in json.load(_f)["fixtures"] if fx.get("output_text")]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=120)


def _phase_24(d: str) -> None:
    """SKILL.md Phase 2.4 — 세 변형기를 순서대로. 셋 다 종료 코드 0(게이트가 아니다)."""
    for script, extra in (("restore_modality.py", []), ("strip_injected_commas.py", []),
                          ("lexical_layer.py", ["restore"])):
        p = _run([os.path.join(_S, script), *extra, "--before", os.path.join(d, "01_input.txt"),
                  "--after", os.path.join(d, "final.md"), "--out", os.path.join(d, "final.md")])
        assert p.returncode == 0, f"{script} 종료 코드 {p.returncode}: {p.stderr[-300:]}"


class PipelineScriptsTests(unittest.TestCase):
    def test_fixtures_flow_through_the_whole_script_chain(self):
        self.assertTrue(_FIXTURES, "output_text가 있는 픽스처가 없음")
        for fx in _FIXTURES:
            with self.subTest(fixture=fx["id"]), tempfile.TemporaryDirectory() as d:
                with open(os.path.join(d, "01_input.txt"), "w", encoding="utf-8") as f:
                    f.write(fx["input_text"])
                # Phase 1 — shim
                p = _run([os.path.join(_S, "prepare_monolith_input.py"), "--run-dir", d, "--genre", "essay"])
                self.assertEqual(p.returncode, 0, p.stderr[-300:])
                metrics = json.load(open(os.path.join(d, "00_metrics.json"), encoding="utf-8"))
                self.assertIn(metrics.get("route_hint"), ("light", "standard", "heavy"))
                combined = open(os.path.join(d, "01_input_with_metrics.txt"), encoding="utf-8").read()
                body = combined.split("[원문 시작]\n", 1)[1].split("\n[원문 끝]", 1)[0]
                src = open(os.path.join(d, "01_input.txt"), encoding="utf-8").read()  # shim 위생 후 원문
                self.assertEqual(body, src.rstrip("\n"), "결합 파일의 원문 본문이 바뀌었다")
                # 모델 출력 대신 얼린 윤문본
                with open(os.path.join(d, "final.md"), "w", encoding="utf-8") as f:
                    f.write(fx["output_text"] + "\n")
                _phase_24(d)
                final = open(os.path.join(d, "final.md"), encoding="utf-8").read()
                self.assertTrue(final.strip(), "Phase 2.4 이후 윤문본이 비었다")
                miss = ha.missing_protected_tokens(final, fx.get("protected_tokens", []))
                self.assertEqual(miss, [], f"보호 토큰 유실: {miss}")
                # Phase 2.5 — 게이트는 판정(0 수렴 / 1 경고)까지만 허용. 2(중단)·3(판정 불가)은 사슬 고장
                g = _run([os.path.join(_S, "verify_gates.py"), "--before", os.path.join(d, "01_input.txt"),
                          "--after", os.path.join(d, "final.md"), "--genre", "essay"])
                self.assertIn(g.returncode, (0, 1), f"게이트 exit {g.returncode}: {g.stdout[-400:]}")

    def test_lexical_injection_is_reverted_inside_the_chain(self):
        # 윤문이 원문에 없던 2점 낱말(렌즈)을 새로 만든 경우 — 사슬 안에서 되돌아와야 한다
        src = "이 시장을 세 가지 관점에서 살펴본다. 첫째는 가격이다. 둘째는 유통이다.\n"
        out = "이 시장을 세 가지 렌즈로 살펴본다. 첫째는 가격이다. 둘째는 유통이다.\n"
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "01_input.txt"), "w", encoding="utf-8").write(src)
            self.assertEqual(_run([os.path.join(_S, "prepare_monolith_input.py"), "--run-dir", d,
                                   "--genre", "report"]).returncode, 0)
            open(os.path.join(d, "final.md"), "w", encoding="utf-8").write(out)
            _phase_24(d)
            final = open(os.path.join(d, "final.md"), encoding="utf-8").read()
            self.assertNotIn("렌즈", final)
            self.assertIn("관점에서", final)


if __name__ == "__main__":
    unittest.main()
