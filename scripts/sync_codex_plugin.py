#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_REFS = ROOT / ".claude" / "skills" / "humanize-korean" / "references"
PLUGIN_SKILL = ROOT / "plugins" / "im-not-ai-codex" / "skills" / "humanize-korean"
LEGACY_CODEX_SKILL = ROOT / "codex" / "skills" / "humanize-korean"

REFERENCE_FILES = (
    "quick-rules.md",
    "ai-tell-taxonomy.md",
    "rewriting-playbook.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strip_trailing_line_space(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def reject_symlink_path(path: Path) -> None:
    current = ROOT
    for part in path.relative_to(ROOT).parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError(f"refusing to write through symlink: {current}")


def sync_pair(
    source: Path,
    target: Path,
    check: bool,
    verbose: bool,
    normalize_line_space: bool = False,
) -> bool:
    source_text = read_text(source)
    if normalize_line_space:
        source_text = strip_trailing_line_space(source_text)
    if not check:
        reject_symlink_path(target)
    target_text = read_text(target) if target.exists() else None
    matches = source_text == target_text

    if verbose:
        status = "ok" if matches else "drift"
        print(f"{status}: {target.relative_to(ROOT)} <= {source.relative_to(ROOT)}")

    if matches:
        return True

    if check:
        return False

    write_text(target, source_text)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize duplicated Codex plugin skill files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify files are synchronized without writing changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every checked path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ok = True

    try:
        for name in REFERENCE_FILES:
            ok &= sync_pair(
                CLAUDE_REFS / name,
                PLUGIN_SKILL / "references" / name,
                check=args.check,
                verbose=args.verbose,
                normalize_line_space=True,
            )

        ok &= sync_pair(
            PLUGIN_SKILL / "SKILL.md",
            LEGACY_CODEX_SKILL / "SKILL.md",
            check=args.check,
            verbose=args.verbose,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not ok:
        print("Codex plugin files are out of sync.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
