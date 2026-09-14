"""패키징 매니페스트 버전 동기화 — 결정적, CI에서 항상 실행.

RELEASING.md는 "SKILL.md frontmatter가 런타임 SSOT"라고 못박고, 버전 문자열이
등장하는 위치를 §1 표로 전수 관리한다. Claude 배포 매니페스트
(`.claude-plugin/*.json`)와 Copilot 배포 매니페스트(`plugin.json`)가
런타임 SSOT와 어긋나지 않도록 함께 검증한다.

이 테스트는 그 누락을 사람의 체크리스트 대신 코드가 막는다 —
`build_quick_rules.py --check`가 룰북 drift를 막는 것과 같은 방식.

`python3 -m unittest` 또는 pytest 양쪽에서 동작.
"""
from __future__ import annotations

import json
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SKILL = os.path.join(_ROOT, "skills", "humanize-korean", "SKILL.md")
_CLAUDE_PLUGIN = os.path.join(_ROOT, ".claude-plugin", "plugin.json")
_COPILOT_PLUGIN = os.path.join(_ROOT, "plugin.json")
_MARKETPLACE = os.path.join(_ROOT, ".claude-plugin", "marketplace.json")

# frontmatter의 version 한 줄. PyYAML 의존을 만들지 않기 위해 직접 뽑는다
# (이 레포는 stdlib only).
_VERSION_RE = re.compile(r'^version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?\s*$', re.M)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def skill_version() -> str:
    """런타임 SSOT — SKILL.md frontmatter의 version."""
    head = _read(_SKILL).split("---", 2)[1]
    match = _VERSION_RE.search(head)
    if not match:
        raise AssertionError(f"SKILL.md frontmatter에서 version을 찾지 못함: {_SKILL}")
    return match.group(1)


class ManifestVersionSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected = skill_version()

    def test_claude_plugin_json_matches_skill(self) -> None:
        actual = json.loads(_read(_CLAUDE_PLUGIN))["version"]
        self.assertEqual(
            actual,
            self.expected,
            f".claude-plugin/plugin.json version={actual} != SKILL.md {self.expected} "
            f"— RELEASING.md §1 표대로 함께 갱신할 것",
        )

    def test_copilot_plugin_json_matches_skill(self) -> None:
        actual = json.loads(_read(_COPILOT_PLUGIN))["version"]
        self.assertEqual(
            actual,
            self.expected,
            f"root plugin.json version={actual} != SKILL.md {self.expected} "
            f"— RELEASING.md §1 표대로 함께 갱신할 것",
        )

    def test_marketplace_metadata_matches_skill(self) -> None:
        actual = json.loads(_read(_MARKETPLACE))["metadata"]["version"]
        self.assertEqual(
            actual,
            self.expected,
            f"marketplace.json metadata.version={actual} != SKILL.md {self.expected}",
        )

    def test_marketplace_entry_matches_skill(self) -> None:
        entries = json.loads(_read(_MARKETPLACE))["plugins"]
        for entry in entries:
            with self.subTest(plugin=entry["name"]):
                self.assertEqual(
                    entry["version"],
                    self.expected,
                    f"marketplace.json plugins[{entry['name']}].version="
                    f"{entry['version']} != SKILL.md {self.expected}",
                )


class ManifestDescriptionTests(unittest.TestCase):
    """은퇴한 아키텍처를 광고하고 있지 않은지 — 마켓플레이스 노출 문구 검사."""

    # v2.1에서 은퇴한 5인 파이프라인. 설치 사용자가 첫 화면에서 보는 문구라
    # 남아 있으면 실제 동작(route_hint 3경로)과 어긋난다.
    RETIRED_TERMS = ("5인 파이프라인", "strict 5인")

    def _descriptions(self) -> list[tuple[str, str]]:
        claude_plugin = json.loads(_read(_CLAUDE_PLUGIN))
        copilot_plugin = json.loads(_read(_COPILOT_PLUGIN))
        market = json.loads(_read(_MARKETPLACE))
        out = [
            (".claude-plugin/plugin.json", claude_plugin["description"]),
            ("plugin.json", copilot_plugin["description"]),
        ]
        out.append(("marketplace.json metadata", market["metadata"]["description"]))
        out += [(f"marketplace.json {e['name']}", e["description"]) for e in market["plugins"]]
        return out

    def test_no_retired_architecture_terms(self) -> None:
        for where, desc in self._descriptions():
            with self.subTest(manifest=where):
                hits = [t for t in self.RETIRED_TERMS if t in desc]
                self.assertEqual(hits, [], f"{where}에 은퇴한 구조 표기 잔존: {hits}")


if __name__ == "__main__":
    unittest.main()
