"""핵심 내용 명사·개념어 보존 계약의 배포 경로 정합을 검증한다.

내용 앵커 보존은 **런타임 계약**이 책임진다 — 윤문 콜이 편집 전에 핵심 내용
명사·개념어를 잡아 두고(anchor_ledger), 앵커가 사라지는 edit 은 롤백한다.
이 테스트는 그 계약 문구가 **배포되는 모든 경로**에 실제로 실려 있는지만 본다.
경로 하나라도 빠지면 그 경로로 설치한 사용자만 조용히 보호를 못 받는다
(2026-08-03 C-1 회귀에서 STRUCTURAL_GUIDE 누락으로 정밀 모드만 안 고쳐진 것과 같은 사고).

결정적 검사라 LLM 호출이 없다. 계약이 실제로 지켜지는지(=출력에 앵커가 남는지)는
tests/test_humanize_live.py 가 **아무 힌트 없이** 재는 몫이다 — 그쪽 프롬프트에
보호 토큰을 넣지 않는 이유가 여기 있다.
"""

from __future__ import annotations

import os
import unittest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 윤문 계약이 실려야 하는 배포 경로 전수.
_CONTRACT_PATHS = (
    "skills/humanize-korean/SKILL.md",
    "agents/humanize-monolith.md",
    "agents/humanize-finalizer.md",
    "skills/humanize-korean/references/quick-rules.header.md",
    "skills/humanize-korean/references/quick-rules.footer.md",
)


def _read(relative: str) -> str:
    with open(os.path.join(_ROOT, relative), encoding="utf-8") as f:
        return f.read()


class ContentAnchorContractTests(unittest.TestCase):
    def test_runtime_contracts_preserve_content_anchors(self) -> None:
        for path in _CONTRACT_PATHS:
            with self.subTest(path=path):
                text = _read(path)
                self.assertIn("핵심 내용 명사·개념어", text)
                self.assertIn("원형", text)

    def test_live_runner_does_not_leak_fixture_answers(self) -> None:
        """라이브 러너 프롬프트에 fixture 의 정답이 섞이지 않아야 한다.

        보호 토큰·변경률 상한을 프롬프트에 넣으면 라이브 테스트는 "스킬이 내용을
        지키는가"가 아니라 "모델이 지시를 따르는가"를 재게 된다. 그러면 #74 같은
        결함이 고쳐진 것처럼 보이면서 실제로는 남는다. 이 회귀를 막는다.
        """
        import humanize_runner  # noqa: PLC0415 — tests/ 를 sys.path 로 쓰는 기존 관례

        prompt = humanize_runner._prompt("패러다임을 설명합니다.", strict=False)
        for leaked in ("보호 토큰", "변경률", "protected", "%"):
            self.assertNotIn(
                leaked, prompt, f"라이브 프롬프트에 채점 기준이 새어 들어감: {leaked!r}"
            )


if __name__ == "__main__":
    unittest.main()
