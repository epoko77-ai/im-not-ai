"""에이전트 인벤토리 정합 — SKILL.md의 서술이 `agents/` 실물과 맞는지.

SKILL.md는 오케스트레이터가 실행 중 읽는 문서다. 여기 적힌 에이전트 개수·경로가
실물과 어긋나면 사람이 레포를 잘못 이해하고, 은퇴·신규 회차에서 그 오차가 누적된다.

`build_quick_rules.py --check`가 룰북 drift를 막듯, 이 테스트가 문서 drift를 막는다.
stdlib only, claude CLI 불필요 — CI에서 항상 실행된다.
"""
from __future__ import annotations

import glob
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_AGENTS_DIR = os.path.join(_ROOT, "agents")
_SKILL = os.path.join(_ROOT, "skills", "humanize-korean", "SKILL.md")

# SKILL.md "에이전트 호출 규칙" 절이 선언하는 총 개수. 문구를 바꾸더라도
# `agents/`에 N종` 형태만 유지하면 이 테스트가 계속 따라간다.
_DECLARED_COUNT_RE = re.compile(r"`agents/`\s*에\s*(\d+)\s*종")

# 전역 설치 대상 `~/.claude/agents/` — 실재하는 경로라 레포 경로 검사에서 뺀다.
_GLOBAL_AGENT_DIR_RE = re.compile(r"~/\.claude/agents")

# SKILL.md가 이름으로 호명하는 에이전트 — 실물이 없으면 런타임이 로드 실패한다.
RUNTIME_AGENTS = (
    "humanize-monolith",
    "humanize-diagnostician",
    "humanize-finalizer",
)
MAINTENANCE_AGENTS = ("korean-ai-tell-taxonomist",)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def agent_files() -> list[str]:
    return sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(_AGENTS_DIR, "*.md"))
    )


class AgentInventoryTests(unittest.TestCase):
    def test_declared_count_matches_files(self) -> None:
        actual = agent_files()
        text = _read(_SKILL)
        declared = _DECLARED_COUNT_RE.search(text)
        self.assertIsNotNone(
            declared, "SKILL.md에서 '`agents/`에 N종' 선언을 찾지 못함"
        )
        self.assertEqual(
            int(declared.group(1)),
            len(actual),
            f"SKILL.md 선언({declared.group(1)}종) != agents/ 실물({len(actual)}개): {actual}",
        )

    def test_named_agents_exist(self) -> None:
        actual = set(agent_files())
        for name in RUNTIME_AGENTS + MAINTENANCE_AGENTS:
            with self.subTest(agent=name):
                self.assertIn(name, actual, f"SKILL.md가 호명하는 {name}.md 가 agents/에 없음")

    def test_skill_does_not_reference_missing_agent_dir(self) -> None:
        """이 레포는 에이전트를 플러그인 컨벤션대로 루트 `agents/`에 둔다.

        레포 안에 `.claude/agents/`는 없으므로, 그 경로를 안내하면 독자가
        빈 디렉토리를 찾게 된다. 전역 설치 대상인 `~/.claude/agents/`는
        실재하는 별개 경로이므로 검사에서 제외한다.
        """
        self.assertFalse(
            os.path.isdir(os.path.join(_ROOT, ".claude", "agents")),
            "`.claude/agents/`가 생겼다면 이 테스트와 SKILL.md 서술을 함께 갱신할 것",
        )
        # assertNotIn은 실패 시 haystack(SKILL.md 전문)을 통째로 덤프하므로
        # 줄 번호만 모아 보고한다.
        hits = [
            i
            for i, line in enumerate(_read(_SKILL).splitlines(), 1)
            if ".claude/agents" in _GLOBAL_AGENT_DIR_RE.sub("", line)
        ]
        self.assertEqual(
            hits, [], f"SKILL.md가 레포에 없는 `.claude/agents/`를 안내함 (줄 {hits})"
        )


if __name__ == "__main__":
    unittest.main()
