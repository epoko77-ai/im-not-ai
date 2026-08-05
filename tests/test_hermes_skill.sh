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

python3 - "$CANONICAL_RULES" "$BUNDLED_RULES" <<'PY'
import sys
from pathlib import Path


def pattern_body(path: str) -> str:
    content = Path(path).read_text(encoding="utf-8")
    start = content.index("## A. ")
    end = content.index("## 자체검증", start)
    return content[start:end].rstrip()


if pattern_body(sys.argv[1]) != pattern_body(sys.argv[2]):
    raise SystemExit("Hermes A-J rule body drifted from the canonical rules")
PY

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

required_intervals = {
    "`0% <= change_rate <= 30%`",
    "`30% < change_rate <= 50%`",
    "`change_rate > 50%`",
}
missing_intervals = {interval for interval in required_intervals if interval not in content}
if missing_intervals:
    raise SystemExit(f"SKILL.md is missing unambiguous change-rate intervals: {sorted(missing_intervals)}")

ref_pattern = re.compile(r"(?:references|templates|scripts|assets|examples)/[^\s)`\"'<>]+")
pending_files = [skill_md]
seen_files = set()
support_docs = {}
referenced_files = set()

while pending_files:
    support_file = pending_files.pop()
    resolved_file = support_file.resolve()
    if resolved_file in seen_files:
        continue
    seen_files.add(resolved_file)
    try:
        file_content = support_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if resolved_file != skill_md.resolve():
        support_docs[str(support_file.relative_to(skill_dir))] = file_content

    for raw_rel in sorted(set(ref_pattern.findall(file_content))):
        rel = raw_rel.rstrip(".,;:")
        candidate = skill_dir / rel
        resolved_candidate = candidate.resolve()
        if skill_dir not in resolved_candidate.parents:
            raise SystemExit(f"support file escapes skill directory: {rel}")
        if not candidate.is_file():
            raise SystemExit(f"missing recursively referenced support file: {rel}")
        if candidate.is_symlink():
            raise SystemExit(f"referenced support file must not be a symlink: {rel}")
        referenced_files.add(rel)
        pending_files.append(candidate)

if not referenced_files:
    raise SystemExit("SKILL.md must reference at least one bundled support file")

forbidden_runtime_markers = (
    "humanize-monolith",
    "오케스트레이터 Phase 2.5",
    "verify_change_rate.py",
    "strict 모드",
)
for rel, doc_content in support_docs.items():
    for marker in forbidden_runtime_markers:
        if marker in doc_content:
            raise SystemExit(f"Hermes support file {rel} contains unavailable runtime marker: {marker}")
    for line in doc_content.splitlines():
        if "변경률" in line and re.search(r"(?:30|50)%\s*(?:이상|초과|이하|미만)", line):
            raise SystemExit(
                f"Hermes support file {rel} duplicates the SKILL.md change-rate boundary: {line}"
            )
PY

echo "Hermes skill bundle tests passed"
