"""Tests for config.py."""

from role_forge.config import (
    CONFIG_FILENAME,
    find_config,
    load_config,
    resolve_roles_dir,
)


def test_load_config_from_fixtures(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    assert config.roles_dir == ".agents/roles"
    assert config.roles_dir == ".agents/roles"
    assert "opencode" in config.targets
    assert "claude" in config.targets


def test_opencode_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    oc = config.targets["opencode"]
    assert oc.enabled is True
    assert oc.output_dir == "."
    assert oc.output_layout == "preserve"
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


def test_target_output_layout_parsed(tmp_path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text(
        "[targets.claude]\n"
        'output_layout = "namespace"\n'
        "[targets.claude.model_map]\n"
        'reasoning = "opus"\n'
        'coding = "sonnet"\n'
    )

    config = load_config(config_path)
    assert config.targets["claude"].output_layout == "namespace"


def test_roles_dir_preferred_over_agents_dir(tmp_path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text('[project]\nroles_dir = "roles"\nagents_dir = ".agents/roles"\n')

    config = load_config(config_path)
    assert config.roles_dir == "roles"


def test_agents_dir_supported_as_legacy_alias(tmp_path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text('[project]\nagents_dir = "roles"\n')

    config = load_config(config_path)
    assert config.roles_dir == "roles"
    assert config.agents_dir == "roles"


def test_resolve_roles_dir_defaults_when_config_absent(tmp_path):
    assert resolve_roles_dir(tmp_path) == tmp_path / ".agents" / "roles"


def test_resolve_roles_dir_uses_roles_toml(tmp_path):
    config_path = tmp_path / CONFIG_FILENAME
    config_path.write_text('[project]\nroles_dir = "roles"\n')

    assert resolve_roles_dir(tmp_path) == tmp_path / "roles"
