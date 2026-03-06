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


def test_load_agents_skips_bad_file(tmp_path: Path) -> None:
    """One malformed file should be skipped while valid agents still load."""
    agents_dir = tmp_path / "roles"
    agents_dir.mkdir()

    # Write a valid agent
    (agents_dir / "good.md").write_text("---\nname: good-agent\ndescription: ok\n---\n# Good")
    # Write a file without frontmatter — this will raise LoadError
    (agents_dir / "bad.md").write_text("no frontmatter here\n")

    agents = load_agents(agents_dir)
    assert len(agents) == 1
    assert agents[0].name == "good-agent"


def test_load_agents_strict_raises_on_bad_file(tmp_path: Path) -> None:
    """strict=True should propagate the LoadError from the first bad file."""
    agents_dir = tmp_path / "roles"
    agents_dir.mkdir()
    (agents_dir / "bad.md").write_text("no frontmatter here\n")

    with pytest.raises(LoadError):
        load_agents(agents_dir, strict=True)


def test_load_agents_recursive(tmp_path: Path) -> None:
    """Agents in sub-directories are discovered and loaded."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()

    # Top-level agent
    (roles_dir / "root-agent.md").write_text(
        "---\nname: root-agent\ndescription: top level\n---\n# Root"
    )
    # Sub-directory agent
    subdir = roles_dir / "team-a"
    subdir.mkdir()
    (subdir / "scout.md").write_text(
        "---\nname: team-a-scout\ndescription: nested scout\n---\n# Scout"
    )
    # Deeper nesting
    deeper = subdir / "deep"
    deeper.mkdir()
    (deeper / "worker.md").write_text(
        "---\nname: deep-worker\ndescription: deeply nested\n---\n# Worker"
    )

    agents = load_agents(roles_dir)
    names = [a.name for a in agents]
    assert "root-agent" in names
    assert "team-a-scout" in names
    assert "deep-worker" in names
    assert len(agents) == 3


def test_load_agents_recursive_skips_bad_nested(tmp_path: Path) -> None:
    """A malformed file in a sub-directory is skipped; valid ones still load."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()

    (roles_dir / "good.md").write_text("---\nname: good-agent\ndescription: ok\n---\n# Good")
    subdir = roles_dir / "nested"
    subdir.mkdir()
    (subdir / "bad.md").write_text("no frontmatter here\n")

    agents = load_agents(roles_dir)
    assert len(agents) == 1
    assert agents[0].name == "good-agent"
