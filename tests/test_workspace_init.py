"""Workspace init-workspace embed."""

from __future__ import annotations

import subprocess
from pathlib import Path

from neo_harness.workspace.init import init_workspace


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_init_workspace_creates_embed(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    _git_init(root)
    result = init_workspace(root, pack_id="demo")
    assert (root / "env.neo.example").is_file()
    assert (root / "requirements-neo.txt").is_file()
    assert (root / "jobs" / "smoke-mock.md").is_file()
    assert (root / "agents" / "demo" / "manifest.yml").is_file()
    assert (root / "agents" / "demo" / "prompts" / "plan.md").is_file()
    assert (root / "scripts" / "neo").is_file()
    assert (root / "scripts" / "neo").stat().st_mode & 0o111
    assert result.created
    # second run skips without force
    result2 = init_workspace(root, pack_id="demo")
    assert result2.skipped


def test_init_requires_git(tmp_path: Path) -> None:
    root = tmp_path / "nogit"
    root.mkdir()
    try:
        init_workspace(root)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "git" in str(exc).lower()
