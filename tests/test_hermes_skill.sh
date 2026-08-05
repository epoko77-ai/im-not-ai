#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$ROOT/hermes/skills/humanize-korean"
SKILL_MD="$SKILL_DIR/SKILL.md"
CANONICAL_RULES="$ROOT/.claude/skills/humanize-korean/references/quick-rules.md"
BUNDLED_RULES="$SKILL_DIR/references/quick-rules.md"

[ -f "$SKILL_MD" ] || { echo "missing Hermes SKILL.md" >&2; exit 1; }
[ ! -L "$SKILL_MD" ] || { echo "Hermes SKILL.md must be a regular file" >&2; exit 1; }
[ -f "$BUNDLED_RULES" ] || { echo "missing bundled quick-rules.md" >&2; exit 1; }
[ ! -L "$BUNDLED_RULES" ] || { echo "Hermes support files must not be symlinks" >&2; exit 1; }

cmp "$CANONICAL_RULES" "$BUNDLED_RULES" || {
  echo "Hermes quick-rules.md drifted from the canonical rules" >&2
  exit 1
}

python3 - "$SKILL_MD" "$SKILL_DIR" <<'PY'
import re
import sys
from pathlib import Path

skill_md = Path(sys.argv[1])
skill_dir = Path(sys.argv[2]).resolve()
content = skill_md.read_text(encoding="utf-8")

if not content.startswith("---\n"):
    raise SystemExit("SKILL.md must start with YAML frontmatter")
frontmatter_end = content.find("\n---\n", 4)
if frontmatter_end == -1:
    raise SystemExit("SKILL.md frontmatter must have a closing delimiter")
frontmatter = content[4:frontmatter_end]

if not re.search(r"^name:\s*humanize-korean\s*$", frontmatter, re.MULTILINE):
    raise SystemExit("SKILL.md must declare name: humanize-korean")
description_match = re.search(r"^description:\s*(\S.*?)\s*$", frontmatter, re.MULTILINE)
if not description_match:
    raise SystemExit("SKILL.md must declare a non-empty description")
if len(description_match.group(1)) > 60:
    raise SystemExit("SKILL.md description must be 60 characters or fewer")

hermes_match = re.search(
    r"^metadata:\s*\n  hermes:\s*\n(?P<body>(?:    .*\n?)*)",
    frontmatter,
    re.MULTILINE,
)
if not hermes_match:
    raise SystemExit("SKILL.md must declare metadata.hermes")
requires_match = re.search(
    r"^    requires_tools:\s*\[([^]]+)]\s*$",
    hermes_match.group("body"),
    re.MULTILINE,
)
if not requires_match:
    raise SystemExit("SKILL.md must declare metadata.hermes.requires_tools")
declared_tools = {item.strip() for item in requires_match.group(1).split(",")}
mandatory_tools = {"skill_view", "read_file", "write_file", "search_files", "execute_code"}
missing_tools = mandatory_tools - declared_tools
if missing_tools:
    raise SystemExit(f"SKILL.md is missing mandatory tools: {sorted(missing_tools)}")

support_refs = set(re.findall(
    r"(?:references|templates|scripts|assets|examples)/[^\s)`\"'<>]+",
    content,
))
if not support_refs:
    raise SystemExit("SKILL.md must reference at least one bundled support file")

for rel in sorted(support_refs):
    candidate = skill_dir / rel.rstrip(".,;:")
    if not candidate.is_file():
        raise SystemExit(f"missing referenced support file: {rel}")
    if candidate.is_symlink():
        raise SystemExit(f"referenced support file must not be a symlink: {rel}")
    if skill_dir not in candidate.resolve().parents:
        raise SystemExit(f"support file escapes skill directory: {rel}")
PY

echo "Hermes skill bundle tests passed"
