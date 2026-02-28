"""Tests for config.py."""

from pathlib import Path

import pytest

from agent_caster.config import ConfigError, find_config, load_config


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


def test_find_config_from_subdir(fixtures_dir, tmp_path):
    (tmp_path / "refit.toml").write_text('[project]\nagents_dir = ".agents/roles"\n')
    subdir = tmp_path / "a" / "b"
    subdir.mkdir(parents=True)
    found = find_config(subdir)
    assert found == tmp_path / "refit.toml"


def test_find_config_not_found():
    with pytest.raises(ConfigError):
        find_config(Path("/tmp/nonexistent_dir_for_test"))
