"""Tests for config.py."""

from pathlib import Path

from role_forge.config import (
    CONFIG_FILENAME,
    USER_ROLES_DIR,
    find_config,
    load_config,
    resolve_roles_dir,
)


def test_load_config_from_fixtures(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    assert "opencode" in config.targets
    assert "claude" in config.targets


def test_opencode_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    oc = config.targets["opencode"]
    assert oc.enabled is True
    assert oc.model_map["reasoning"] == "github-copilot/claude-opus-4.6"
    assert oc.model_map["coding"] == "github-copilot/gpt-5.2-codex"


def test_capability_map_parsed(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    oc = config.targets["opencode"]
    assert "context7" in oc.capability_map
    assert oc.capability_map["context7"] == {"context7": True}


def test_claude_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    cl = config.targets["claude"]
    assert cl.model_map["reasoning"] == "opus"
    assert cl.model_map["coding"] == "sonnet"


# --- find_config tests ---


def test_find_config_returns_roles_toml(tmp_path):
    """find_config returns roles.toml when present."""
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("[project]\n")

    result = find_config(tmp_path)
    assert result == cfg


def test_find_config_returns_none_when_absent(tmp_path):
    """find_config returns None if neither config file exists."""
    assert find_config(tmp_path) is None


def test_resolve_roles_dir_defaults_when_config_absent(tmp_path):
    assert resolve_roles_dir(tmp_path) == tmp_path / ".agents" / "roles"


def test_user_roles_dir_constant_matches_home() -> None:
    assert Path.home() / ".agents" / "roles" == USER_ROLES_DIR
