from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_FIXTURE_PATHS = (
    ".claude/skills/humanize-korean",
    "agents",
    "plugins/im-not-ai-codex/skills/humanize-korean",
    "install.sh",
    "uninstall.sh",
)


def _copy_install_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative in INSTALL_FIXTURE_PATHS:
        source = ROOT / relative
        target = repo / relative
        if source.is_dir():
            shutil.copytree(source, target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return repo


def _env_without_codex(codex_home: Path) -> dict[str, str]:
    return os.environ | {
        "CODEX_HOME": str(codex_home),
        "PATH": "/usr/bin:/bin",
    }


def test_codex_only_installs_without_codex_binary(tmp_path: Path) -> None:
    repo = _copy_install_fixture(tmp_path)
    codex_home = tmp_path / "codex-home"
    installed = codex_home / "skills" / "humanize-korean"

    subprocess.run(
        ["bash", "install.sh", "--codex-only"],
        cwd=repo,
        env=_env_without_codex(codex_home),
        check=True,
    )

    assert installed.is_symlink()
    assert installed.readlink() == repo / "plugins" / "im-not-ai-codex" / "skills" / "humanize-korean"


def test_codex_auto_detects_existing_home_without_codex_binary(tmp_path: Path) -> None:
    repo = _copy_install_fixture(tmp_path)
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    installed = codex_home / "skills" / "humanize-korean"

    subprocess.run(
        ["bash", "install.sh"],
        cwd=repo,
        env=_env_without_codex(codex_home),
        check=True,
    )

    assert installed.is_symlink()
    assert installed.readlink() == repo / "plugins" / "im-not-ai-codex" / "skills" / "humanize-korean"


def test_codex_uninstall_removes_packaged_plugin_symlink(tmp_path: Path) -> None:
    repo = _copy_install_fixture(tmp_path)
    codex_home = tmp_path / "codex-home"
    installed = codex_home / "skills" / "humanize-korean"
    env = _env_without_codex(codex_home)

    subprocess.run(["bash", "install.sh", "--codex-only"], cwd=repo, env=env, check=True)
    subprocess.run(["bash", "uninstall.sh"], cwd=repo, env=env, check=True)

    assert not installed.exists()
