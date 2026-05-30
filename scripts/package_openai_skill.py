#!/usr/bin/env python3
"""Package the OpenAI Agent Skill upload zip for ChatGPT/Codex.

The archive root contains SKILL.md, agents/openai.yaml, and references/.
That keeps the zip directly uploadable as a single skill.
"""

from __future__ import annotations

import argparse
import os
import zipfile
from pathlib import Path


DEFAULT_SKILL_DIR = Path(".agents") / "skills" / "im-not-ai"
DEFAULT_OUTPUT = Path("dist") / "im-not-ai.skill.zip"
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    if "__pycache__" in path.parts:
        return False
    return path.is_file()


def package_skill(skill_dir: Path, output: Path) -> int:
    skill_dir = skill_dir.resolve()
    output = output.resolve()

    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"SKILL.md not found in {skill_dir}")
    if not (skill_dir / "agents" / "openai.yaml").is_file():
        raise SystemExit(f"agents/openai.yaml not found in {skill_dir}")

    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(skill_dir):
            root_path = Path(root)
            for file_name in sorted(files):
                file_path = root_path / file_name
                if not should_include(file_path):
                    continue
                archive.write(file_path, file_path.relative_to(skill_dir))
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=DEFAULT_SKILL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    count = package_skill(args.skill_dir, args.output)
    print(f"Packaged {count} files into {args.output}")


if __name__ == "__main__":
    main()
