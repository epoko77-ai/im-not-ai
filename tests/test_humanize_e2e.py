"""계층2(behavioral) E2E — fixtures.json의 (원문, 윤문본) 쌍을 불변식/밴드/지표델타로 검증.

output_text가 null인 fixture(아직 스킬 미실행)는 skip한다.
새 윤문본을 만들려면: 스킬(`/humanize` 또는 humanize-monolith 에이전트)에 input_text를
넣고, 결과를 해당 fixture의 output_text에 채운 뒤 재실행한다.

`python3 -m unittest` 또는 pytest 양쪽에서 동작.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import humanize_asserts as ha  # noqa: E402

with open(os.path.join(_HERE, "fixtures.json"), encoding="utf-8") as _f:
    _MANIFEST = json.load(_f)


class HumanizeE2ETests(unittest.TestCase):
    def test_fixtures_with_outputs(self) -> None:
        processed = 0
        pending: list[str] = []

        for fx in _MANIFEST["fixtures"]:
            out = fx.get("output_text")
            if not out:
                pending.append(fx["id"])
                continue
            src = fx["input_text"]

            with self.subTest(fixture=fx["id"]):
                # T1 — 의미 불변 (보호 토큰 100% 생존)
                miss = ha.missing_protected_tokens(out, fx.get("protected_tokens", []))
                self.assertEqual(miss, [], f"[{fx['id']}] 보호 토큰 유실: {miss}")

                # T2/T3 — 변경률 밴드 (과윤문 가드 포함)
                cr = ha.change_rate(src, out)
                band = fx.get("change_rate") or {}
                if "min" in band:
                    self.assertGreaterEqual(cr, band["min"], f"[{fx['id']}] 변경률 {cr:.3f} < min {band['min']}")
                if "max" in band:
                    self.assertLessEqual(cr, band["max"], f"[{fx['id']}] 변경률 {cr:.3f} > max {band['max']}")

                # T5 — register/장르 보존
                if fx.get("register"):
                    self.assertEqual(ha.register_of(out), fx["register"], f"[{fx['id']}] register 이탈")

                # T6 — 패턴 탐지 재현율 (시그널 하락)
                sd = fx.get("signal_drop")
                if sd:
                    drop = ha.signal(src, sd["name"]) - ha.signal(out, sd["name"])
                    self.assertGreaterEqual(
                        drop, sd["min_drop"], f"[{fx['id']}] {sd['name']} 하락 {drop:.3f} < {sd['min_drop']}"
                    )

            processed += 1

        if processed == 0:
            self.skipTest("아직 생성된 fixture 출력이 없음")
        print(f"\n[e2e] 검증 완료 {processed}건 · 출력 대기 {len(pending)}건: {pending}")


if __name__ == "__main__":
    unittest.main()
