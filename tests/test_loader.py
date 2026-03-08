"""Tests for loader.py."""

from pathlib import Path

import pytest

from role_forge.loader import LoadError, _split_frontmatter, load_agents, parse_agent_file


def test_load_agents_from_fixtures(fixtures_dir):
    agents = load_agents(fixtures_dir / ".agents" / "roles")
    assert len(agents) == 8
    names = [a.name for a in agents]
    assert "explorer" in names
    assert "aligner" in names
    assert "orchestrator" in names
    assert "nested-coordinator" in names
    assert "feature-lead" in names
    assert "impl-worker" in names
    assert "qa-worker" in names
    assert "research-helper" in names


def test_parse_explorer(fixtures_dir):
    agent = parse_agent_file(fixtures_dir / ".agents" / "roles" / "explorer.md")
    assert agent.name == "explorer"
    assert agent.role == "subagent"
    assert agent.model.tier == "reasoning"
    assert agent.model.temperature == 0.05
    assert agent.canonical_id == "explorer"
    assert "repomix-explorer" in agent.skills
    assert "read" in agent.capabilities
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
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()

    # Write a valid agent
    (roles_dir / "good.md").write_text("---\nname: good-agent\ndescription: ok\n---\n# Good")
    # Write a file without frontmatter — this will raise LoadError
    (roles_dir / "bad.md").write_text("no frontmatter here\n")

    agents = load_agents(roles_dir)
    assert len(agents) == 1
    assert agents[0].name == "good-agent"


def test_load_agents_strict_raises_on_bad_file(tmp_path: Path) -> None:
    """strict=True should propagate the LoadError from the first bad file."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "bad.md").write_text("no frontmatter here\n")

    with pytest.raises(LoadError):
        load_agents(roles_dir, strict=True)


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
    assert {a.canonical_id for a in agents} == {
        "root-agent",
        "team-a/scout",
        "team-a/deep/worker",
    }


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


def test_custom_tier_accepted(tmp_path: Path) -> None:
    """Any custom tier string should be accepted without validation errors."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "agent.md").write_text(
        "---\nname: deep-worker\ndescription: test\nmodel:\n  tier: deep\n---\n# Deep Worker\n"
    )
    agents = load_agents(roles_dir)
    assert len(agents) == 1
    assert agents[0].model.tier == "deep"


def test_parse_hierarchy_metadata(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    nested = roles_dir / "l2"
    nested.mkdir(parents=True)
    agent_file = nested / "lead.md"
    agent_file.write_text(
        "---\n"
        "name: lead\n"
        "level: L2\n"
        "class: lead\n"
        "scheduled: false\n"
        "callable: true\n"
        "max_delegate_depth: 1\n"
        "allowed_children:\n"
        "  - l3/worker\n"
        "---\n"
        "# Lead\n"
    )

    agent = parse_agent_file(agent_file, roles_dir=roles_dir)
    assert agent.canonical_id == "l2/lead"
    assert agent.relative_path == "l2/lead.md"
    assert agent.hierarchy.level == "L2"
    assert agent.hierarchy.role_class == "lead"
    assert agent.hierarchy.max_delegate_depth == 1
    assert agent.hierarchy.allowed_children == ["l3/worker"]


def test_load_nested_fixture_tree_preserves_canonical_ids(fixtures_dir) -> None:
    agents = load_agents(fixtures_dir / ".agents" / "roles")
    by_name = {agent.name: agent for agent in agents}

    assert by_name["nested-coordinator"].canonical_id == "nested/nested-coordinator"
    assert by_name["feature-lead"].canonical_id == "nested/feature-lead"
    assert by_name["impl-worker"].canonical_id == "nested/workers/impl-worker"
    assert by_name["qa-worker"].canonical_id == "nested/workers/qa-worker"
    assert by_name["research-helper"].canonical_id == "nested/support/research-helper"


def test_parse_nested_fixture_with_all_capability(fixtures_dir) -> None:
    agent = parse_agent_file(fixtures_dir / ".agents" / "roles" / "nested" / "feature-lead.md")
    assert agent.name == "feature-lead"
    assert "all" in agent.capabilities
    assert agent.hierarchy.level == "L2"
