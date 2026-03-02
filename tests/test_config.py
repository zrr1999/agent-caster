"""Tests for config.py."""

from agent_caster.config import load_config


def test_load_config_from_fixtures(fixtures_dir):
    config = load_config(fixtures_dir / "refit.toml")
    assert config.agents_dir == ".agents/roles"
    assert "opencode" in config.targets
    assert "claude" in config.targets


def test_opencode_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "refit.toml")
    oc = config.targets["opencode"]
    assert oc.enabled is True
    assert oc.output_dir == "."
    assert oc.model_map["reasoning"] == "github-copilot/claude-opus-4.6"
    assert oc.model_map["coding"] == "github-copilot/gpt-5.2-codex"


def test_capability_map_parsed(fixtures_dir):
    config = load_config(fixtures_dir / "refit.toml")
    oc = config.targets["opencode"]
    assert "context7" in oc.capability_map
    assert oc.capability_map["context7"] == {"context7": True}


def test_claude_target_config(fixtures_dir):
    config = load_config(fixtures_dir / "refit.toml")
    cl = config.targets["claude"]
    assert cl.model_map["reasoning"] == "opus"
    assert cl.model_map["coding"] == "sonnet"
