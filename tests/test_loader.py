"""Tests for loader.py."""

from pathlib import Path

import pytest

from agent_caster.loader import LoadError, _split_frontmatter, load_agents, parse_agent_file


def test_load_agents_from_fixtures(fixtures_dir):
    agents = load_agents(fixtures_dir / ".agents" / "roles")
    assert len(agents) == 3
    names = [a.name for a in agents]
    assert "explorer" in names
    assert "aligner" in names
    assert "orchestrator" in names


def test_parse_explorer(fixtures_dir):
    agent = parse_agent_file(fixtures_dir / ".agents" / "roles" / "explorer.md")
    assert agent.name == "explorer"
    assert agent.role == "subagent"
    assert agent.model.tier == "reasoning"
    assert agent.model.temperature == 0.05
    assert "repomix-explorer" in agent.skills
    assert "read-code" in agent.capabilities
    assert agent.prompt_content.startswith("# Explorer")


def test_parse_aligner_no_bash(fixtures_dir):
    agent = parse_agent_file(fixtures_dir / ".agents" / "roles" / "aligner.md")
    assert agent.name == "aligner"
    assert agent.model.tier == "coding"
    for cap in agent.capabilities:
        if isinstance(cap, dict):
            assert "bash" not in cap or not cap.get("bash")


def test_capabilities_stored_raw(fixtures_dir):
    agent = parse_agent_file(fixtures_dir / ".agents" / "roles" / "explorer.md")
    has_str = any(isinstance(c, str) for c in agent.capabilities)
    has_dict = any(isinstance(c, dict) for c in agent.capabilities)
    assert has_str
    assert has_dict


def test_split_frontmatter_valid():
    text = "---\nname: test\n---\n# Body"
    fm, body = _split_frontmatter(text)
    assert "name: test" in fm
    assert body == "# Body"


def test_split_frontmatter_no_opening():
    with pytest.raises(LoadError):
        _split_frontmatter("no frontmatter here")


def test_split_frontmatter_no_closing():
    with pytest.raises(LoadError):
        _split_frontmatter("---\nname: test\n# No closing")


def test_load_agents_missing_dir():
    with pytest.raises(LoadError):
        load_agents(Path("/nonexistent/dir"))
