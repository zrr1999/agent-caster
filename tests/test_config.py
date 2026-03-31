"""Tests for config.py."""

from role_forge.config import (
    CONFIG_FILENAME,
    find_config,
    load_config,
    resolve_output_manifest_path,
    resolve_source_roles_dir,
)


def test_load_config_from_fixtures(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    assert "opencode" in config.targets
    assert "claude" in config.targets


def test_target_config_parsed(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    assert config.targets["opencode"].model_map["reasoning"] == "github-copilot/claude-opus-4.6"
    assert config.targets["claude"].model_map["coding"] == "sonnet"


def test_find_config_returns_roles_toml(tmp_path):
    cfg = tmp_path / CONFIG_FILENAME
    cfg.write_text("[project]\n")
    assert find_config(tmp_path) == cfg


def test_find_config_returns_none_when_absent(tmp_path):
    assert find_config(tmp_path) is None


def test_resolve_source_roles_dir_defaults_when_config_absent(tmp_path):
    assert resolve_source_roles_dir(tmp_path) == tmp_path / "roles"


def test_resolve_source_roles_dir_uses_roles_toml(tmp_path):
    (tmp_path / "roles.toml").write_text('[project]\nroles_dir = "my-roles"\n')
    assert resolve_source_roles_dir(tmp_path) == tmp_path / "my-roles"


def test_resolve_output_manifest_path(tmp_path):
    assert resolve_output_manifest_path(tmp_path) == tmp_path / ".role-forge" / "outputs.json"
