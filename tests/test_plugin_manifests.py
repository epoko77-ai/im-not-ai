"""The Copilot plugin exposes the single-call skill and shared references."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def test_copilot_plugin_exposes_single_call_skill_and_references() -> None:
    manifest = _load(ROOT / "plugin.json")
    skill_root = (ROOT / manifest["skills"][0]).resolve()
    skill = skill_root / "humanize-korean"

    assert manifest["name"] == "humanize-korean"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "references" / "quick-rules.md").is_file()
    assert (skill / "references" / "ai-tell-taxonomy.md").is_file()
    assert (skill / "references" / "rewriting-playbook.md").is_file()
