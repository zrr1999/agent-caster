"""Tests for config.py."""

from agent_caster.config import CONFIG_FILENAME, LEGACY_CONFIG_FILENAME, find_config, load_config


def test_load_config_from_fixtures(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    assert config.agents_dir == ".agents/roles"
    assert "opencode" in config.targets
    assert "claude" in config.targets


def test_opencode_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "roles.toml")
    oc = config.targets["opencode"]
    assert oc.enabled is True
    assert oc.output_dir == "."
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


def test_find_config_falls_back_to_legacy(tmp_path, capsys):
    """find_config returns refit.toml when roles.toml absent."""
    legacy = tmp_path / LEGACY_CONFIG_FILENAME
    legacy.write_text("[project]\n")

    result = find_config(tmp_path)
    assert result == legacy


def test_find_config_prefers_canonical_over_legacy(tmp_path):
    """roles.toml takes priority even when refit.toml also exists."""
    canonical = tmp_path / CONFIG_FILENAME
    canonical.write_text("[project]\nagents_dir = 'canonical'\n")
    (tmp_path / LEGACY_CONFIG_FILENAME).write_text("[project]\nagents_dir = 'legacy'\n")

    result = find_config(tmp_path)
    assert result == canonical


def test_find_config_returns_none_when_absent(tmp_path):
    """find_config returns None if neither config file exists."""
    assert find_config(tmp_path) is None
