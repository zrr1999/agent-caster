"""Tests for loader.py."""

from pathlib import Path

import pytest

from role_forge.loader import (
    LoadError,
    _split_frontmatter,
    find_unmanaged_files,
    load_agents,
    parse_agent_file,
)


def test_load_agents_from_fixtures(fixtures_dir):
    agents = load_agents(fixtures_dir / "roles")
    assert len(agents) == 8
    assert {agent.name for agent in agents} >= {
        "explorer",
        "aligner",
        "orchestrator",
        "nested-coordinator",
    }


def test_parse_explorer(fixtures_dir):
    agent = parse_agent_file(fixtures_dir / "roles" / "explorer.md")
    assert agent.name == "explorer"
    assert agent.role == "subagent"
    assert agent.model.tier == "reasoning"
    assert agent.model.temperature == 0.05
    assert agent.canonical_id == "explorer"
    assert "repomix-explorer" in agent.skills
    assert agent.prompt_content.startswith("# Explorer")


def test_split_frontmatter_valid():
    fm, body = _split_frontmatter("---\nname: test\n---\n# Body")
    assert "name: test" in fm
    assert body == "# Body"


def test_split_frontmatter_invalid():
    with pytest.raises(LoadError):
        _split_frontmatter("no frontmatter here")


def test_load_agents_missing_dir():
    with pytest.raises(LoadError):
        load_agents(Path("/nonexistent/dir"))


def test_load_agents_skips_bad_file(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "good.md").write_text("---\nname: good-agent\ndescription: ok\n---\n# Good")
    (roles_dir / "bad.md").write_text("no frontmatter here\n")

    agents = load_agents(roles_dir)
    assert [agent.name for agent in agents] == ["good-agent"]


def test_load_agents_recursive(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    (roles_dir / "team-a" / "deep").mkdir(parents=True)
    (roles_dir / "root-agent.md").write_text("---\nname: root-agent\n---\n# Root")
    (roles_dir / "team-a" / "scout.md").write_text("---\nname: team-a-scout\n---\n# Scout")
    (roles_dir / "team-a" / "deep" / "worker.md").write_text(
        "---\nname: deep-worker\n---\n# Worker"
    )

    agents = load_agents(roles_dir)
    assert {agent.canonical_id for agent in agents} == {
        "root-agent",
        "team-a/scout",
        "team-a/deep/worker",
    }


def test_custom_tier_accepted(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "agent.md").write_text(
        "---\nname: deep-worker\ndescription: test\nmodel:\n  tier: deep\n---\n# Deep Worker\n"
    )
    agents = load_agents(roles_dir)
    assert agents[0].model.tier == "deep"


def test_parse_agent_file_missing_prompt_file_raises(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    agent_file = roles_dir / "agent.md"
    agent_file.write_text(
        "---\nname: agent\nprompt_file: prompts/missing.md\n---\n# Inline body should not be used\n"
    )

    with pytest.raises(LoadError, match="prompt_file"):
        parse_agent_file(agent_file, roles_dir=roles_dir)


def test_parse_hierarchy_metadata(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    agent_file = roles_dir / "l2" / "lead.md"
    agent_file.parent.mkdir(parents=True)
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
    assert agent.hierarchy.allowed_children == ["l3/worker"]


def test_find_unmanaged_files_reports_invalid_markdown_and_other_files(tmp_path: Path) -> None:
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "good.md").write_text("---\nname: good\n---\n# Good")
    (roles_dir / "bad.md").write_text("not frontmatter")
    (roles_dir / "notes.txt").write_text("oops")

    issues = find_unmanaged_files(roles_dir)
    assert [(issue.path.name, issue.reason) for issue in issues] == [
        ("bad.md", "File does not start with YAML frontmatter (---)"),
        ("notes.txt", "Non-Markdown file"),
    ]
