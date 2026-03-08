"""Tests for registry.py — source parsing and git operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from role_forge.registry import (
    CACHE_DIR,  # noqa: F401
    fetch_source,
    find_roles_dir,
    parse_source,
)


def test_parse_org_repo():
    src = parse_source("PFCCLab/precision-agents")
    assert src.org == "PFCCLab"
    assert src.repo == "precision-agents"
    assert src.ref is None
    assert src.is_local is False
    assert src.github_url == "https://github.com/PFCCLab/precision-agents"


def test_parse_org_repo_with_ref():
    src = parse_source("PFCCLab/precision-agents@v1.0")
    assert src.org == "PFCCLab"
    assert src.repo == "precision-agents"
    assert src.ref == "v1.0"


def test_parse_org_repo_with_branch_ref():
    src = parse_source("PFCCLab/precision-agents@main")
    assert src.ref == "main"


def test_parse_local_relative():
    src = parse_source("./my/agents")
    assert src.is_local is True
    assert src.local_path == "./my/agents"
    assert src.org is None
    assert src.repo is None


def test_parse_local_absolute():
    src = parse_source("/tmp/my-agents")
    assert src.is_local is True
    assert src.local_path == "/tmp/my-agents"


def test_parse_invalid_no_slash():
    with pytest.raises(ValueError, match="Invalid source"):
        parse_source("just-a-name")


def test_parse_empty():
    with pytest.raises(ValueError, match="Invalid source"):
        parse_source("")


# --- fetch_source tests ---


def test_fetch_local_source(tmp_path):
    """Local source returns the path directly, no git."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# E")

    src = parse_source(str(tmp_path))
    result = fetch_source(src)
    assert result == Path(str(tmp_path)).resolve()


def test_fetch_local_source_not_found():
    src = parse_source("/nonexistent/path/to/agents")
    with pytest.raises(FileNotFoundError):
        fetch_source(src)


@patch("role_forge.registry.subprocess.run")
def test_fetch_github_clones_to_cache(mock_run, tmp_path):
    """First fetch should git clone to cache dir."""
    mock_run.return_value = MagicMock(returncode=0)

    src = parse_source("PFCCLab/precision-agents@main")
    result = fetch_source(src, cache_root=tmp_path)

    expected_dir = tmp_path / "PFCCLab" / "precision-agents"
    assert result == expected_dir
    assert mock_run.call_count >= 1
    clone_call = mock_run.call_args_list[0]
    assert "clone" in clone_call.args[0]


@patch("role_forge.registry.subprocess.run")
def test_fetch_github_pulls_existing_cache(mock_run, tmp_path):
    """If cache exists, should git fetch + checkout instead of clone."""
    mock_run.return_value = MagicMock(returncode=0)

    cache_dir = tmp_path / "PFCCLab" / "precision-agents"
    cache_dir.mkdir(parents=True)
    (cache_dir / ".git").mkdir()

    src = parse_source("PFCCLab/precision-agents@v1.0")
    result = fetch_source(src, cache_root=tmp_path)

    assert result == cache_dir
    calls_str = str(mock_run.call_args_list)
    assert "fetch" in calls_str


# --- find_roles_dir tests ---


def test_find_roles_dir_with_roles_toml(tmp_path):
    """roles.toml roles_dir is honoured (canonical name)."""
    (tmp_path / "roles.toml").write_text('[project]\nroles_dir = "my-agents"')
    agents = tmp_path / "my-agents"
    agents.mkdir()
    (agents / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == agents


def test_find_roles_dir_with_legacy_roles_dir_key(tmp_path):
    """roles.toml roles_dir remains supported for backward compatibility."""
    (tmp_path / "roles.toml").write_text('[project]\nroles_dir = "my-agents"')
    agents = tmp_path / "my-agents"
    agents.mkdir()
    (agents / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == agents


def test_find_roles_dir_default_roles(tmp_path):
    """Without any config file, falls back to roles/."""
    roles = tmp_path / "roles"
    roles.mkdir()
    (roles / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == roles


def test_find_roles_dir_none_found(tmp_path):
    """No config file and no roles/ should raise."""
    with pytest.raises(FileNotFoundError, match="No agent definitions found"):
        find_roles_dir(tmp_path)
