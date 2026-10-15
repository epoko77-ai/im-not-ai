"""계층3 (live integration) — 실제 스킬을 돌려 갓 나온 출력에 판정.

**스킬 회귀를 실제로 잡는 유일한 층.** test_humanize_e2e.py(얼린 fixture)와 달리
매번 스킬을 새로 실행하므로, 스킬/룰이 망가지면 여기서 실패한다.

- `claude` CLI 없으면 전체 skip → 바닐라 CI(크레덴셜 없음)에서도 안전.
- CLI 가 있어도 호출이 타임아웃하면 skip — 판정 불가를 회귀로 오인하지 않는다.
  단 **출력 계약 위반(센티넬 파싱 실패)은 skip 하지 않고 실패**로 남긴다
  (`hr.SkillOutputInvalid`). 스킬이 깨진 것을 환경 탓으로 넘기지 않기 위함.
- 비결정적 출력이라 문자열 정답 비교 대신 **하드 불변식·변경률 상한·시그널 델타**만 단언.
- 느림(호출당 수십 초). 기본 fixture당 3회(전원 통과 요구).
    - HUMANIZE_LIVE_K=1      빠른 단발 확인이 필요할 때만 반복 수를 낮춤
    - HUMANIZE_LIVE_IDS=fx_b_heavy,fx_pat_c11_ending_comma   부분 실행(빠른 검증)

실행: python3 -m unittest test_humanize_live
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import humanize_asserts as ha  # noqa: E402
import humanize_runner as hr  # noqa: E402

with open(os.path.join(_HERE, "fixtures.json"), encoding="utf-8") as _f:
    _FIXTURES = json.load(_f)["fixtures"]

_ONLY = {s for s in os.environ.get("HUMANIZE_LIVE_IDS", "").split(",") if s}
_K = int(os.environ.get("HUMANIZE_LIVE_K", "3"))


@unittest.skipIf(hr.CLAUDE_BIN is None, "claude CLI 없음 — live 통합 테스트 skip")
class HumanizeLiveTests(unittest.TestCase):
    def _assert_output(self, fx: dict, out: str) -> None:
        src = fx["input_text"]
        # 하드 불변식: 고유명사·수치·리터럴 인용은 100% 생존해야
        miss = ha.missing_protected_tokens(out, fx.get("protected_tokens", []))
        self.assertEqual(miss, [], f"[{fx['id']}] 보호 토큰 유실: {miss}")
        # 과윤문 상한(가드) — live에서 특히 중요
        band = fx.get("change_rate") or {}
        if "max" in band:
            cr = ha.change_rate(src, out)
            self.assertLessEqual(cr, band["max"], f"[{fx['id']}] 변경률 {cr:.3f} > max {band['max']}")
        # 패턴 탐지 재현율
        sd = fx.get("signal_drop")
        if sd:
            drop = ha.signal(src, sd["name"]) - ha.signal(out, sd["name"])
            self.assertGreaterEqual(
                drop, sd["min_drop"], f"[{fx['id']}] {sd['name']} 하락 {drop:.3f} < {sd['min_drop']}"
            )

    def test_live_fixtures(self) -> None:
        targets = [fx for fx in _FIXTURES if not _ONLY or fx["id"] in _ONLY]
        self.assertTrue(targets, "실행할 fixture 없음 (HUMANIZE_LIVE_IDS 확인)")
        for fx in targets:
            for i in range(_K):
                # 프롬프트에 fixture 의 정답(protected_tokens·change_rate 상한)을
                # 넣지 않는다. 넣으면 이 테스트는 "스킬이 내용을 지키는가"가 아니라
                # "모델이 지시를 따르는가"를 재게 되어 계측이 무효가 된다.
                # 내용 보존은 런타임 계약(anchor_ledger)이 책임지고, 여기서는
                # 아무 힌트 없이 나온 결과만 채점한다.
                #
                # 호출은 subTest 밖에서 한다 — 하네스가 못 돌면 남은 fixture 도
                # 같은 이유로 못 돌기 때문에, subTest 안에서 skip 하면 fixture 수
                # × K 만큼 타임아웃을 반복해 기다리게 된다.
                try:
                    out = hr.run_humanize(fx["input_text"], strict=False)
                except hr.SkillOutputInvalid:
                    # 스킬이 돌았는데 출력 계약이 깨진 것 — 회귀다. 숨기지 않는다.
                    raise
                except hr.SkillUnavailable as exc:
                    # CLI 부재는 클래스 데코레이터가 이미 걸러낸다. 여기 오는 건
                    # 타임아웃 등 실행 자체가 불가능한 환경 — 판정 불가라 skip.
                    self.skipTest(f"[{fx['id']}] 스킬 실행 불가 — {exc}")
                with self.subTest(fixture=fx["id"], run=i):
                    self._assert_output(fx, out)


if __name__ == "__main__":
    unittest.main()
