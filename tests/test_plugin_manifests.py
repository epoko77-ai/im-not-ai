"""The Copilot plugin exposes the single-call skill and shared references."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def test_copilot_plugin_exposes_dedicated_single_call_skill() -> None:
    manifest = _load(ROOT / "plugin.json")
    skill_root = (ROOT / manifest["skills"][0]).resolve()
    skill = skill_root / "humanize-korean"
    shared = ROOT / "skills" / "humanize-korean" / "references"

    assert manifest["name"] == "humanize-korean"
    assert (skill / "SKILL.md").is_file()
    assert skill_root == (ROOT / "copilot" / "skills").resolve()
    contract = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert "Single-call Path (GitHub Copilot CLI)" in contract
    assert "light·standard·heavy" not in contract
    assert "../../../skills/humanize-korean/references/quick-rules.md" in contract
    assert (shared / "quick-rules.md").is_file()
    assert (shared / "ai-tell-taxonomy.md").is_file()
    assert (shared / "rewriting-playbook.md").is_file()
