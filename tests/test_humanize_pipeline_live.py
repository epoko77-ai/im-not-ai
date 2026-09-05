"""제품 경로 live 테스트 — 스킬을 **파일 생성 허용**으로 정상 실행한다.

`test_humanize_live.py` 는 "파일은 만들지 마"라고 지시해서 shim·게이트가 빠진
경로를 잰다. 그 경로에서 `fx_guard_overedit` 이 변경률 0.55 로 상한을 넘는데,
제품은 그 상황을 `verify_change_rate.py`(50% 이상 기각)로 막는다 — 철칙 #4 가
"판정은 스크립트가 내린다, LLM 자가보고가 아니다"라고 못박은 지점이다.

여기서는 그 보장을 실제로 확인한다: 스킬을 정상 절차로 돌리고, 나온 산출물이
게이트를 통과하는지 결정적으로 잰다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
import humanize_asserts as ha  # noqa: E402
import humanize_runner as hr  # noqa: E402

with open(os.path.join(_HERE, "fixtures.json"), encoding="utf-8") as _f:
    _FIXTURES = {fx["id"]: fx for fx in json.load(_f)["fixtures"]}

_GUARD = "fx_guard_overedit"


@unittest.skipIf(hr.CLAUDE_BIN is None, "claude CLI 없음 — live 통합 테스트 skip")
class PipelineLiveTests(unittest.TestCase):
    def test_guard_fixture_survives_the_shipped_path(self) -> None:
        fx = _FIXTURES[_GUARD]
        try:
            out, run_dir = hr.run_humanize_pipeline(fx["input_text"])
        except hr.QuotaExhausted as exc:
            self.skipTest(f"사용량 한도 — 측정 불가: {exc}")

        miss = ha.missing_protected_tokens(out, fx.get("protected_tokens", []))
        self.assertEqual(miss, [], f"[{_GUARD}] 보호 토큰 유실: {miss}")

        gate = subprocess.run(
            [sys.executable, os.path.join(_ROOT, "scripts", "verify_change_rate.py"),
             "--before", os.path.join(run_dir, "01_input.txt"),
             "--after", os.path.join(run_dir, "final.md")],
            capture_output=True, text=True, timeout=120,
        )
        self.assertNotEqual(
            gate.returncode, 2,
            f"[{_GUARD}] 게이트가 ABORT 인 산출물이 그대로 남았다 — 제품 보장 실패\n"
            f"{gate.stdout}",
        )
        self.assertNotEqual(gate.returncode, 3, f"게이트 실행 오류: {gate.stderr}")


@unittest.skipIf(hr.CLAUDE_BIN is None, "claude CLI 없음 — live 통합 테스트 skip")
class EnglishPipelineLiveTests(unittest.TestCase):
    """영어 스킬을 실제로 호출한다.

    v2.4 까지 영어는 **스킬을 통한 end-to-end 실행이 한 번도 검증되지 않았다** —
    스크립트를 직접 돌린 것뿐이었다. 스킬이 shim 을 부르고 게이트 5종을 돌려
    final.md 를 남기는지, 그 산출물이 게이트를 통과하는지 여기서 본다.
    """

    SAMPLE = (
        "The old argument for shipping fast was about learning. You put something "
        "in front of users, you watch what breaks, and you adjust. That logic still "
        "holds, but it has been stretched to cover decisions it was never meant to "
        "cover. Teams now ship half-formed features, half-staffed migrations, and "
        "half-tested integrations, calling each one an experiment. An experiment "
        "has a hypothesis and a stopping rule. Most of what gets shipped under that "
        "banner has neither. It may be worth asking what we are actually buying "
        "with the speed, because the cost shows up later and lands on someone else."
    )

    def test_english_skill_runs_end_to_end(self) -> None:
        try:
            out, run_dir = hr.run_humanize_pipeline(self.SAMPLE, skill="humanize-english")
        except hr.QuotaExhausted as exc:
            self.skipTest(f"사용량 한도 — 측정 불가: {exc}")

        self.assertTrue(out.strip(), "final.md 가 비어 있다")
        # shim 이 실제로 돌았는지 — 점수 파일이 남아야 한다.
        self.assertTrue(
            os.path.isfile(os.path.join(run_dir, "00_metrics.json")),
            f"shim 산출물이 없다: {run_dir}",
        )
        with open(os.path.join(run_dir, "00_metrics.json"), encoding="utf-8") as f:
            metrics = json.load(f)
        self.assertEqual(metrics["lang"], "en")
        self.assertIn(metrics["route_hint"], ("light", "standard", "heavy"))
        self.assertIn(metrics["threshold_set"], ("abstract", "blog"))

        # 게이트 3종을 우리가 직접 다시 돌려 산출물을 판정한다.
        before = os.path.join(run_dir, "01_input.txt")
        after = os.path.join(run_dir, "final.md")
        for name, args in (
            ("verify_change_rate.py", []),
            ("../core/content_preservation.py", []),
            ("../core/modality_loss.py", []),
        ):
            path = os.path.normpath(os.path.join(_ROOT, "scripts", name))
            gate = subprocess.run(
                [sys.executable, path, "--before", before, "--after", after] + args,
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(
                gate.returncode, 0,
                f"[{os.path.basename(name)}] 게이트 실패\n{gate.stdout}{gate.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
