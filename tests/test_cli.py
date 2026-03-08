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


def test_add_preserves_nested_role_paths_and_cast_output(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    (roles / "l2").mkdir(parents=True)
    (roles / "l3").mkdir(parents=True)
    (roles / "l2" / "lead.md").write_text(
        "---\nname: lead\ndescription: Lead\nrole: subagent\nlevel: L2\n---\n# Lead\n"
    )
    (roles / "l3" / "worker.md").write_text(
        "---\nname: worker\ndescription: Worker\nrole: subagent\nlevel: L3\n---\n# Worker\n"
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
    assert (project / ".agents" / "roles" / "l2" / "lead.md").is_file()
    assert (project / ".agents" / "roles" / "l3" / "worker.md").is_file()
    assert (project / ".claude" / "agents" / "l2" / "lead.md").is_file()
    assert (project / ".claude" / "agents" / "l3" / "worker.md").is_file()


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
    assert "ID" in result.output


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


def test_render_alias_with_target(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )
    result = runner.invoke(
        app,
        [
            "render",
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


def test_remove_nested_agent_by_canonical_id(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles" / "l2"
    agents_dir.mkdir(parents=True)
    (agents_dir / "worker.md").write_text("---\nname: worker\n---\n# E")

    result = runner.invoke(
        app,
        [
            "remove",
            "l2/worker",
            "--yes",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (agents_dir / "worker.md").exists()


def test_remove_ambiguous_name_requires_canonical_id(tmp_path):
    left = tmp_path / ".agents" / "roles" / "l2"
    right = tmp_path / ".agents" / "roles" / "l3"
    left.mkdir(parents=True)
    right.mkdir(parents=True)
    (left / "worker.md").write_text("---\nname: worker\n---\n# L2")
    (right / "worker.md").write_text("---\nname: worker\n---\n# L3")

    result = runner.invoke(
        app,
        [
            "remove",
            "worker",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 1
    assert "Ambiguous agent name" in result.output


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


def test_add_uses_roles_toml_config(tmp_path):
    """add should use model_map from roles.toml (canonical name) when present."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    # Write roles.toml (canonical name) with custom model_map for claude target
    (project / "roles.toml").write_text(
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "my-custom-reasoning"\n'
        'coding = "my-custom-coding"\n'
    )

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
    agent_file = project / ".claude" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "my-custom-reasoning" in content


def test_add_uses_refit_toml_config(tmp_path):
    """add should use model_map from refit.toml (legacy name) when roles.toml absent."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    # Write refit.toml (legacy name) with custom model_map for claude target
    (project / "refit.toml").write_text(
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "my-custom-reasoning"\n'
        'coding = "my-custom-coding"\n'
    )

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
    agent_file = project / ".claude" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "my-custom-reasoning" in content


def test_cast_uses_roles_toml_config(tmp_path):
    """cast should use model_map from roles.toml (canonical name) when present."""
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    # Write roles.toml with custom model_map for claude target
    (tmp_path / "roles.toml").write_text(
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "toml-reasoning"\n'
        'coding = "toml-coding"\n'
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
    assert result.exit_code == 0, result.output
    agent_file = tmp_path / ".claude" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "toml-coding" in content


def test_cast_uses_refit_toml_config(tmp_path):
    """cast should use model_map from refit.toml (legacy name) when roles.toml absent."""
    agents_dir = tmp_path / ".agents" / "roles"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    # Write refit.toml with custom model_map for claude target
    (tmp_path / "refit.toml").write_text(
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "toml-reasoning"\n'
        'coding = "toml-coding"\n'
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
    assert result.exit_code == 0, result.output
    agent_file = tmp_path / ".claude" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "toml-coding" in content


def test_cast_namespace_layout_avoids_nested_name_collisions(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    (agents_dir / "l2").mkdir(parents=True)
    (agents_dir / "l3").mkdir(parents=True)
    (agents_dir / "l2" / "worker.md").write_text(
        "---\nname: worker\ndescription: L2 worker\n---\n# L2 Worker\n"
    )
    (agents_dir / "l3" / "worker.md").write_text(
        "---\nname: worker\ndescription: L3 worker\n---\n# L3 Worker\n"
    )
    (tmp_path / "roles.toml").write_text(
        "[targets.claude]\n"
        'output_layout = "namespace"\n'
        "[targets.claude.model_map]\n"
        'reasoning = "opus"\n'
        'coding = "sonnet"\n'
    )

    result = runner.invoke(
        app,
        ["cast", "--target", "claude", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "agents" / "l2__worker.md").is_file()
    assert (tmp_path / ".claude" / "agents" / "l3__worker.md").is_file()


def test_cast_flatten_layout_rejects_nested_name_collisions(tmp_path):
    agents_dir = tmp_path / ".agents" / "roles"
    (agents_dir / "l2").mkdir(parents=True)
    (agents_dir / "l3").mkdir(parents=True)
    (agents_dir / "l2" / "worker.md").write_text("---\nname: worker\n---\n# L2 Worker\n")
    (agents_dir / "l3" / "worker.md").write_text("---\nname: worker\n---\n# L3 Worker\n")
    (tmp_path / "roles.toml").write_text(
        "[targets.claude]\n"
        'output_layout = "flatten"\n'
        "[targets.claude.model_map]\n"
        'reasoning = "opus"\n'
        'coding = "sonnet"\n'
    )

    result = runner.invoke(
        app,
        ["cast", "--target", "claude", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "maps both" in result.output


def test_add_opencode_prompts_for_model(tmp_path):
    """add with opencode target should prompt for model when no config exists."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read-code\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    # Simulate user typing model names at the prompt
    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--target",
            "opencode",
            "--project-dir",
            str(project),
        ],
        input="my-reasoning-model\nmy-coding-model\n",
    )
    assert result.exit_code == 0, result.output
    agent_file = project / ".opencode" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "my-reasoning-model" in content


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
