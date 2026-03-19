"""Tests for CLI commands."""

from __future__ import annotations

import json

from typer.testing import CliRunner

import role_forge.config as config_module
from role_forge.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "role-forge" in result.output


# -- add command ---------------------------------------------------------------


def test_add_from_local(tmp_path):
    """add from a local path should confirm and install roles."""
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


def test_add_yes_skips_install_confirmation(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text("---\nname: explorer\n---\n# Explorer\n")
    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        ["add", str(source), "--yes", "--project-dir", str(project)],
    )

    assert result.exit_code == 0, result.output
    assert "Continue with install?" not in result.output


def test_add_without_yes_can_cancel_install(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text("---\nname: explorer\n---\n# Explorer\n")
    project = tmp_path / "project"
    project.mkdir()
    target_file = project / ".agents" / "roles" / "explorer.md"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("---\nname: explorer\n---\n# Existing\n")

    result = runner.invoke(
        app,
        ["add", str(source), "--project-dir", str(project)],
        input="p\nn\n",  # scope: project, then cancel overwrite
    )

    assert result.exit_code == 1
    assert target_file.read_text() == "---\nname: explorer\n---\n# Existing\n"


def test_add_without_yes_prompts_before_overwrite(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text("---\nname: explorer\n---\n# New Explorer\n")
    project_roles = tmp_path / "project" / ".agents" / "roles"
    project_roles.mkdir(parents=True)
    existing = project_roles / "explorer.md"
    existing.write_text("---\nname: explorer\n---\n# Old Explorer\n")

    # One overwrite prompt: n = skip overwrites, no new roles -> cancel (exit 1)
    result = runner.invoke(
        app,
        ["add", str(source), "--project-dir", str(tmp_path / "project")],
        input="p\nn\n",  # scope: project, skip overwrites
    )
    assert result.exit_code == 1, result.output
    assert existing.read_text() == "---\nname: explorer\n---\n# Old Explorer\n"

    # One overwrite prompt: y = overwrite all
    result2 = runner.invoke(
        app,
        ["add", str(source), "--project-dir", str(tmp_path / "project")],
        input="p\ny\n",  # scope: project, allow overwrite
    )
    assert result2.exit_code == 0, result2.output
    assert existing.read_text() == "---\nname: explorer\n---\n# New Explorer\n"


def test_add_with_auto_cast(tmp_path):
    """add should auto-cast when platform is detected."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
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


def test_add_no_render_skips_render(tmp_path):
    """add --no-render installs roles but does not render to targets."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude").mkdir()

    result = runner.invoke(
        app,
        ["add", str(source), "--yes", "--no-render", "--project-dir", str(project)],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".agents" / "roles" / "explorer.md").is_file()
    assert not (project / ".claude" / "agents" / "explorer.md").exists()


def test_add_role_filter_installs_only_matching(tmp_path):
    """add --role installs only roles whose name/id match (substring)."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    for name in ("explorer", "writer", "aligner"):
        (roles / f"{name}.md").write_text(
            "---\nname: " + name + "\ndescription: x\nrole: subagent\n"
            "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# x\n"
        )
    project = tmp_path / "project"
    project.mkdir()
    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--yes",
            "--no-render",
            "--role",
            "explorer",
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".agents" / "roles" / "explorer.md").is_file()
    assert not (project / ".agents" / "roles" / "writer.md").exists()
    assert not (project / ".agents" / "roles" / "aligner.md").exists()


def test_add_with_explicit_target(tmp_path):
    """add --target should cast to specified platform only."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
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


def test_add_fails_when_source_contains_invalid_role(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "good.md").write_text("---\nname: good\n---\n# Good\n")
    (roles / "bad.md").write_text("not valid frontmatter\n")

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        ["add", str(source), "--yes", "--no-render", "--project-dir", str(project)],
    )

    assert result.exit_code == 1
    assert "bad.md" in result.output
    assert not (project / ".agents" / "roles" / "good.md").exists()


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
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\n---\n# Explorer\n"
    )
    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "explorer" in result.output


def test_list_global_reads_only_user_scope(tmp_path, monkeypatch):
    project_roles = tmp_path / "project" / ".agents" / "roles"
    user_roles = tmp_path / "user-roles"
    project_roles.mkdir(parents=True)
    user_roles.mkdir(parents=True)
    (project_roles / "project.md").write_text("---\nname: project\n---\n# Project")
    (user_roles / "user.md").write_text("---\nname: user\n---\n# User")
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)

    result = runner.invoke(app, ["list", "-g", "--project-dir", str(tmp_path / "project")])

    assert result.exit_code == 0
    assert "user" in result.output
    assert "project" not in result.output


def test_list_json_outputs_machine_readable_roles(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# Explorer")

    result = runner.invoke(app, ["list", "--json", "--project-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == [
        {
            "name": "explorer",
            "canonical_id": "explorer",
            "role": "subagent",
            "tier": "reasoning",
            "temperature": None,
            "relative_path": "explorer.md",
            "source_path": str((roles_dir / "explorer.md").resolve()),
            "scope": "project",
        }
    ]


def test_list_no_agents(tmp_path):
    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1


def test_list_fails_when_any_installed_role_is_invalid(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "good.md").write_text("---\nname: good\n---\n# Good\n")
    (roles_dir / "bad.md").write_text("not valid frontmatter\n")

    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "bad.md" in result.output


# -- render command ------------------------------------------------------------


def test_render_with_target(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
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


def test_render_cursor_respects_target_config_without_model_map(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# Explorer\n")
    (tmp_path / "roles.toml").write_text("[targets.cursor]\nenabled = true\n")

    result = runner.invoke(
        app,
        ["render", "--target", "cursor", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    agent_file = tmp_path / ".cursor" / "agents" / "explorer.mdc"
    assert agent_file.is_file()
    assert "model:" not in agent_file.read_text()


def test_render_windsurf_succeeds_without_model_map(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\n---\n# Explorer\n"
    )

    result = runner.invoke(
        app,
        ["render", "--target", "windsurf", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    agent_file = tmp_path / ".windsurf" / "rules" / "explorer.md"
    assert agent_file.is_file()
    assert "model:" not in agent_file.read_text()


def test_render_fails_when_any_installed_role_is_invalid(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "good.md").write_text("---\nname: good\n---\n# Good\n")
    (roles_dir / "bad.md").write_text("not valid frontmatter\n")

    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "bad.md" in result.output
    assert not (tmp_path / ".claude" / "agents" / "good.md").exists()


def test_render_merges_user_and_project_agents(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project_roles = project / ".agents" / "roles"
    user_roles = tmp_path / "user-roles"
    project_roles.mkdir(parents=True)
    user_roles.mkdir(parents=True)
    (project / ".claude").mkdir(parents=True)

    (user_roles / "user-only.md").write_text(
        "---\nname: user-only\ndescription: User\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# User\n"
    )
    (user_roles / "shared.md").write_text(
        "---\nname: shared\ndescription: User shared\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# User shared\n"
    )
    (project_roles / "shared.md").write_text(
        "---\nname: shared\ndescription: Project shared\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - read\n---\n# Project shared\n"
    )
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)

    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--project-dir", str(project)],
    )

    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "user-only.md").is_file()
    shared_content = (project / ".claude" / "agents" / "shared.md").read_text()
    assert "Project shared" in shared_content
    assert "claude-sonnet-4" in shared_content


def test_render_fails_when_user_scope_contains_invalid_role(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project_roles = project / ".agents" / "roles"
    user_roles = tmp_path / "user-roles"
    project_roles.mkdir(parents=True)
    user_roles.mkdir(parents=True)
    (project_roles / "good.md").write_text("---\nname: good\n---\n# Good\n")
    (user_roles / "bad.md").write_text("not valid frontmatter\n")
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)

    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--project-dir", str(project)],
    )

    assert result.exit_code == 1
    assert "bad.md" in result.output


def test_render_fails_when_project_scope_contains_invalid_role_with_valid_user_scope(
    tmp_path, monkeypatch
):
    project = tmp_path / "project"
    project_roles = project / ".agents" / "roles"
    user_roles = tmp_path / "user-roles"
    project_roles.mkdir(parents=True)
    user_roles.mkdir(parents=True)
    (project_roles / "bad.md").write_text("not valid frontmatter\n")
    (user_roles / "good.md").write_text("---\nname: good\n---\n# Good\n")
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)

    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--project-dir", str(project)],
    )

    assert result.exit_code == 1
    assert "bad.md" in result.output


def test_render_no_agents(tmp_path, monkeypatch):
    """Render with no roles in project or user scope must exit 1."""
    empty_user_roles = tmp_path / "user_roles"
    empty_user_roles.mkdir()
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", empty_user_roles)
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
    assert result.exit_code == 1


def test_render_role_filter_renders_only_matching(tmp_path):
    """render --role outputs only roles matching (substring of name/id)."""
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    for name in ("explorer", "writer"):
        (roles_dir / f"{name}.md").write_text(
            "---\nname: " + name + "\ndescription: x\nrole: subagent\n"
            "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# x\n"
        )
    (tmp_path / ".claude").mkdir()
    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--role", "explorer", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "agents" / "explorer.md").is_file()
    assert not (tmp_path / ".claude" / "agents" / "writer.md").exists()


# -- remove command ------------------------------------------------------------


def test_remove_agent(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# E")
    result = runner.invoke(
        app,
        [
            "remove",
            "explorer",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (roles_dir / "explorer.md").exists()


def test_remove_nested_agent_by_canonical_id(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles" / "l2"
    roles_dir.mkdir(parents=True)
    (roles_dir / "worker.md").write_text("---\nname: worker\n---\n# E")

    result = runner.invoke(
        app,
        [
            "remove",
            "l2/worker",
            "--project-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    assert not (roles_dir / "worker.md").exists()


def test_remove_global_only_deletes_user_scope(tmp_path, monkeypatch):
    project_roles = tmp_path / "project" / ".agents" / "roles"
    user_roles = tmp_path / "user-roles"
    project_roles.mkdir(parents=True)
    user_roles.mkdir(parents=True)
    (project_roles / "shared.md").write_text("---\nname: shared\n---\n# Project")
    (user_roles / "shared.md").write_text("---\nname: shared\n---\n# User")
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)

    result = runner.invoke(
        app,
        ["remove", "shared", "-g", "--project-dir", str(tmp_path / "project")],
    )

    assert result.exit_code == 0
    assert not (user_roles / "shared.md").exists()
    assert (project_roles / "shared.md").exists()


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
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
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


def test_render_uses_roles_toml_targets_without_flag(tmp_path):
    """render without --target should use targets from roles.toml, not filesystem detection."""
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )

    # Create filesystem markers for claude AND cursor
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cursor").mkdir()

    # But only configure opencode and claude in roles.toml
    (tmp_path / "roles.toml").write_text(
        "[targets.opencode]\n"
        "enabled = true\n"
        "[targets.opencode.model_map]\n"
        'reasoning = "r"\ncoding = "c"\n'
        "[targets.claude]\n"
        "enabled = true\n"
        "[targets.claude.model_map]\n"
        'reasoning = "opus"\ncoding = "sonnet"\n'
    )

    result = runner.invoke(
        app,
        ["render", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    # Should render opencode and claude (from roles.toml), NOT cursor (filesystem only)
    assert (tmp_path / ".claude" / "agents" / "explorer.md").is_file()
    assert (tmp_path / ".opencode" / "agents" / "explorer.md").is_file()
    assert not (tmp_path / ".cursor" / "agents" / "explorer.mdc").exists()


def test_update_rejects_local():
    result = runner.invoke(app, ["update", "./local/path"])
    assert result.exit_code == 1
    assert "Cannot update a local source" in result.output


def test_add_missing_roles_dir_message_is_actionable(monkeypatch, tmp_path):
    source_root = tmp_path / "cache"
    source_root.mkdir()

    monkeypatch.setattr("role_forge.registry.fetch_source", lambda parsed: source_root)

    result = runner.invoke(app, ["add", "PFCCLab/precision-agents", "--project-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert (
        "Fetched source 'PFCCLab/precision-agents', but no role definitions were found"
        in result.output
    )
    assert "'roles/' directory or [project].roles_dir in roles.toml" in result.output


def test_update_global_passes_scope(monkeypatch, tmp_path):
    calls: list[dict[str, object]] = []

    def fake_add(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("role_forge.cli.add", fake_add)

    result = runner.invoke(
        app,
        ["update", "PFCCLab/precision-agents", "-g", "--yes", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert calls == [
        {
            "source": "PFCCLab/precision-agents",
            "yes": True,
            "global_install": True,
            "target": None,
            "no_render": False,
            "role": None,
            "project_dir": str(tmp_path),
        }
    ]


def test_update_prunes_orphaned_agents(monkeypatch, tmp_path):
    """When update runs and source has removed an agent, the orphaned file is pruned."""
    cache = tmp_path / "cache"
    cache.mkdir()
    roles = cache / "roles"
    roles.mkdir()
    (roles / "a.md").write_text("---\nname: a\n---\n# A")
    (roles / "b.md").write_text("---\nname: b\n---\n# B")

    def fetch_source(parsed):
        return cache

    monkeypatch.setattr("role_forge.registry.fetch_source", fetch_source)
    user_roles = tmp_path / ".agents" / "roles"
    monkeypatch.setattr(config_module, "USER_ROLES_DIR", user_roles)
    user_roles.mkdir(parents=True)

    result = runner.invoke(
        app,
        ["add", "org/repo", "-g", "--yes", "--no-render", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (user_roles / "a.md").exists()
    assert (user_roles / "b.md").exists()

    (roles / "b.md").unlink()

    result2 = runner.invoke(
        app,
        ["update", "org/repo", "-g", "--yes", "--no-render", "--project-dir", str(tmp_path)],
    )
    assert result2.exit_code == 0, result2.output
    assert (user_roles / "a.md").exists()
    assert not (user_roles / "b.md").exists()

    result3 = runner.invoke(app, ["list", "-g", "--project-dir", str(tmp_path)])
    assert result3.exit_code == 0
    assert "2 role" not in result3.output
    assert "1 role" in result3.output


def test_doctor_reports_unmanaged_files(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "good.md").write_text("---\nname: good\n---\n# Good")
    (roles_dir / "bad.md").write_text("oops")
    (roles_dir / "notes.txt").write_text("notes")

    result = runner.invoke(app, ["doctor", "--project-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "bad.md" in result.output
    assert "notes.txt" in result.output


def test_doctor_json_outputs_findings(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "bad.md").write_text("oops")

    result = runner.invoke(app, ["doctor", "--json", "--project-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["scope"] == "project"
    assert payload["issue_count"] == 1
    assert payload["issues"][0]["relative_path"] == "bad.md"


def test_clean_dry_run_keeps_unmanaged_files(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    bad_file = roles_dir / "bad.md"
    bad_file.write_text("oops")

    result = runner.invoke(app, ["clean", "--dry-run", "--project-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert bad_file.exists()
    assert "Would remove" in result.output


def test_clean_yes_removes_only_unmanaged_files(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    good_file = roles_dir / "good.md"
    bad_file = roles_dir / "bad.md"
    txt_file = roles_dir / "notes.txt"
    good_file.write_text("---\nname: good\n---\n# Good")
    bad_file.write_text("oops")
    txt_file.write_text("notes")

    result = runner.invoke(app, ["clean", "-y", "--project-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert good_file.exists()
    assert not bad_file.exists()
    assert not txt_file.exists()


# -- integration ---------------------------------------------------------------


def test_add_uses_roles_toml_config(tmp_path):
    """add should use model_map from roles.toml (canonical name) when present."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
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


def test_render_uses_roles_toml_config(tmp_path):
    """render should use model_map from roles.toml (canonical name) when present."""
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - read\n---\n# Explorer\n"
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
            "render",
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


def test_render_namespace_layout_avoids_nested_name_collisions(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    (roles_dir / "l2").mkdir(parents=True)
    (roles_dir / "l3").mkdir(parents=True)
    (roles_dir / "l2" / "worker.md").write_text(
        "---\nname: worker\ndescription: L2 worker\n---\n# L2 Worker\n"
    )
    (roles_dir / "l3" / "worker.md").write_text(
        "---\nname: worker\ndescription: L3 worker\n---\n# L3 Worker\n"
    )
    (tmp_path / "roles.toml").write_text(
        '[targets.claude]\n[targets.claude.model_map]\nreasoning = "opus"\ncoding = "sonnet"\n'
    )

    result = runner.invoke(
        app,
        ["render", "--target", "claude", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "agents" / "l2" / "worker.md").is_file()
    assert (tmp_path / ".claude" / "agents" / "l3" / "worker.md").is_file()


def test_add_opencode_uses_source_repo_model_map(tmp_path):
    """add with opencode target uses model_map from source repo's roles.toml (no prompt)."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (source / "roles.toml").write_text(
        '[project]\nroles_dir = "roles"\n\n'
        "[targets.opencode]\nenabled = true\n\n"
        "[targets.opencode.model_map]\n"
        'reasoning = "my-reasoning-model"\ncoding = "my-coding-model"\n'
    )
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        [
            "add",
            str(source),
            "--target",
            "opencode",
            "--project-dir",
            str(project),
        ],
        input="p\ny\n",  # scope: project, confirm render
    )
    assert result.exit_code == 0, result.output
    agent_file = project / ".opencode" / "agents" / "explorer.md"
    assert agent_file.is_file()
    content = agent_file.read_text()
    assert "my-reasoning-model" in content


def test_add_cursor_uses_source_repo_target_config_without_model_map(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (source / "roles.toml").write_text(
        '[project]\nroles_dir = "roles"\n\n[targets.cursor]\nenabled = true\n'
    )
    (roles / "explorer.md").write_text("---\nname: explorer\n---\n# Explorer\n")

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        ["add", str(source), "--yes", "--project-dir", str(project)],
    )

    assert result.exit_code == 0, result.output
    agent_file = project / ".cursor" / "agents" / "explorer.mdc"
    assert agent_file.is_file()
    assert "model:" not in agent_file.read_text()


def test_full_workflow_add_list_render_remove(tmp_path):
    """Full workflow: add -> list -> render -> remove."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )
    (roles / "aligner.md").write_text(
        "---\nname: aligner\ndescription: Aligner\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - write\n---\n# Aligner\n"
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
    assert "2 role(s) found in project scope" in result.output

    # render (files already exist from add; --yes skips overwrite prompt)
    result = runner.invoke(
        app,
        [
            "render",
            "--target",
            "claude",
            "--yes",
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
            "--project-dir",
            str(project),
        ],
    )
    assert result.exit_code == 0
    assert not (project / ".agents" / "roles" / "explorer.md").exists()

    # list again
    result = runner.invoke(app, ["list", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert "1 role(s) found in project scope" in result.output
