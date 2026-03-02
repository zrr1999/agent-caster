"""Tests for CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from agent_caster.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agent-caster" in result.output


# -- add command ---------------------------------------------------------------


def test_add_from_local(tmp_path):
    """add from a local path with --yes should copy agents and skip interaction."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".agents" / "roles" / "explorer.md").is_file()


def test_add_with_auto_cast(tmp_path):
    """add should auto-cast when platform is detected."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude").mkdir()

    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "explorer.md").is_file()


def test_add_with_explicit_target(tmp_path):
    """add --target should cast to specified platform only."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--target",
            "claude",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "explorer.md").is_file()


# -- list command --------------------------------------------------------------


def test_list_agents(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\n---\n# Explorer\n"
    )
    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "explorer" in result.output


def test_list_no_agents(tmp_path):
    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1


# -- cast command --------------------------------------------------------------


def test_cast_with_target(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )
    result = runner.invoke(
        app,
        [
            "cast",
            "--target",
            "claude",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "agents" / "explorer.md").is_file()


def test_cast_no_agents(tmp_path):
    result = runner.invoke(
        app,
        [
            "cast",
            "--target",
            "claude",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


# -- remove command ------------------------------------------------------------


def test_remove_agent(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text("---\nname: explorer\n---\n# E")
    result = runner.invoke(
        app,
        [
            "remove",
            "explorer",
            "--yes",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (agents_dir / "explorer.md").exists()


def test_remove_nonexistent(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    result = runner.invoke(
        app,
        [
            "remove",
            "nonexistent",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1


# -- update command ------------------------------------------------------------


def test_update_rejects_local():
    result = runner.invoke(app, ["update", "./local/path"])
    assert result.exit_code == 1
    assert "Cannot update a local source" in result.output


# -- integration ---------------------------------------------------------------


def test_full_workflow_add_list_cast_remove(tmp_path):
    """Full workflow: add -> list -> cast -> remove."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )
    (roles / "aligner.md").write_text(
        "---\nname: aligner\ndescription: Aligner\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - write-code\n---\n# Aligner\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    # add
    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--target",
            "claude",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0
    assert (project / ".agents" / "roles" / "explorer.md").is_file()
    assert (project / ".claude" / "agents" / "explorer.md").is_file()
    assert (project / ".claude" / "agents" / "aligner.md").is_file()

    # list
    result = runner.invoke(app, ["list", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert "explorer" in result.output
    assert "aligner" in result.output
    assert "2 agents found" in result.output

    # cast
    result = runner.invoke(
        app,
        [
            "cast",
            "--target",
            "claude",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0

    # remove
    result = runner.invoke(
        app,
        [
            "remove",
            "explorer",
            "--yes",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0
    assert not (project / ".agents" / "roles" / "explorer.md").exists()

    # list again
    result = runner.invoke(app, ["list", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert "1 agents found" in result.output
