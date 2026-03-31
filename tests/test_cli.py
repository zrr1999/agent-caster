"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from role_forge.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_global_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("role_forge.manifest.CACHE_ROOT", tmp_path / "global-state")


def _write_role(path: Path, name: str, *, tier: str = "reasoning", body: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    prompt = body or f"# {name}\n"
    path.write_text(
        "---\n"
        f"name: {name}\n"
        f"description: {name}\n"
        "role: subagent\n"
        "model:\n"
        f"  tier: {tier}\n"
        "capabilities:\n"
        "  - read\n"
        "---\n"
        f"{prompt}"
    )


def _write_source_config(path: Path, target_name: str = "claude") -> None:
    if target_name == "claude":
        path.write_text(
            '[project]\nroles_dir = "roles"\n\n'
            "[targets.claude]\nenabled = true\n"
            "[targets.claude.model_map]\n"
            'reasoning = "source-opus"\n'
            'coding = "source-sonnet"\n'
        )
        return

    path.write_text(
        '[project]\nroles_dir = "roles"\n\n'
        "[targets.opencode]\nenabled = true\n"
        "[targets.opencode.model_map]\n"
        'reasoning = "my-reasoning-model"\n'
        'coding = "my-coding-model"\n'
    )


def _remote_source(source_root: Path, *, target_name: str = "claude") -> Path:
    roles = source_root / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer")
    _write_source_config(source_root / "roles.toml", target_name=target_name)
    return source_root


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "role-forge" in result.output


def test_add_local_generates_outputs_and_manifest(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer")

    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)

    result = runner.invoke(app, ["add", str(source), "--yes", "--project-dir", str(project)])

    assert result.exit_code == 0, result.output
    agent_file = project / ".claude" / "agents" / "explorer.md"
    assert agent_file.is_file()
    outputs_manifest = json.loads((project / ".role-forge" / "outputs.json").read_text())
    source_entry = outputs_manifest["sources"][str(source.resolve())]
    assert source_entry["source"] == str(source.resolve())
    assert source_entry["targets"]["claude"]["selected_roles"] == ["explorer"]
    assert source_entry["targets"]["claude"]["files"] == [".claude/agents/explorer.md"]


def test_add_without_targets_only_validates_and_caches(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer")

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(app, ["add", str(source), "--yes", "--project-dir", str(project)])

    assert result.exit_code == 0, result.output
    assert "No target detected" in result.output
    assert not (project / ".role-forge" / "outputs.json").exists()


def test_add_uses_source_repo_target_config(tmp_path):
    source = _remote_source(tmp_path / "source", target_name="opencode")
    _write_role(source / "roles" / "explorer.md", "explorer", tier="reasoning")

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app,
        ["add", str(source), "--yes", "--target", "opencode", "--project-dir", str(project)],
    )

    assert result.exit_code == 0, result.output
    content = (project / ".opencode" / "agents" / "explorer.md").read_text()
    assert "my-reasoning-model" in content


def test_add_remote_updates_global_cache_manifest(tmp_path, monkeypatch):
    cache = _remote_source(tmp_path / "cache")
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)

    monkeypatch.setattr("role_forge.registry.fetch_source", lambda parsed: cache)
    monkeypatch.setattr("role_forge.registry.read_head_commit", lambda repo_dir: "abc123def456")

    result = runner.invoke(app, ["add", "org/repo", "--yes", "--project-dir", str(project)])

    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["list", "--sources", "--json", "--project-dir", str(project)])
    payload = json.loads(result.output)
    assert payload == [
        {
            "source_key": "org/repo",
            "cache_key": "org/repo",
            "cache_path": str(cache),
            "last_fetched_commit": "abc123def456",
        }
    ]


def test_list_project_outputs(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer")

    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    runner.invoke(app, ["add", str(source), "--yes", "--project-dir", str(project)])

    result = runner.invoke(app, ["list", "--project-dir", str(project)])

    assert result.exit_code == 0, result.output
    assert str(source.resolve()) in result.output
    assert "claude" in result.output


def test_list_project_outputs_json(tmp_path):
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer")

    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    runner.invoke(app, ["add", str(source), "--yes", "--project-dir", str(project)])

    result = runner.invoke(app, ["list", "--json", "--project-dir", str(project)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["source_key"] == str(source.resolve())
    assert payload[0]["role_ids"] == ["explorer"]
    assert payload[0]["files"] == [".claude/agents/explorer.md"]


def test_update_rejects_local():
    result = runner.invoke(app, ["update", "./local/path"])
    assert result.exit_code == 1
    assert "Cannot update a local source" in result.output


def test_update_preserves_previous_role_selection(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    roles = cache / "roles"
    roles.mkdir(parents=True)
    _write_role(roles / "explorer.md", "explorer", body="# Explorer v1\n")
    _write_role(roles / "writer.md", "writer", body="# Writer\n")
    _write_source_config(cache / "roles.toml")

    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)

    monkeypatch.setattr("role_forge.registry.fetch_source", lambda parsed: cache)
    monkeypatch.setattr("role_forge.registry.read_head_commit", lambda repo_dir: "abc123def456")

    result = runner.invoke(
        app,
        ["add", "org/repo", "--yes", "--role", "explorer", "--project-dir", str(project)],
    )
    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "explorer.md").is_file()
    assert not (project / ".claude" / "agents" / "writer.md").exists()

    _write_role(roles / "explorer.md", "explorer", body="# Explorer v2\n")

    result = runner.invoke(app, ["update", "org/repo", "--yes", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "# Explorer v2" in (project / ".claude" / "agents" / "explorer.md").read_text()
    assert not (project / ".claude" / "agents" / "writer.md").exists()


def test_remove_remote_cleans_outputs_and_cache(tmp_path, monkeypatch):
    cache = _remote_source(tmp_path / "cache")
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)

    monkeypatch.setattr("role_forge.registry.fetch_source", lambda parsed: cache)
    monkeypatch.setattr("role_forge.registry.read_head_commit", lambda repo_dir: "abc123def456")

    result = runner.invoke(app, ["add", "org/repo", "--yes", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["remove", "org/repo", "--yes", "--project-dir", str(project)])

    assert result.exit_code == 0, result.output
    assert not (project / ".claude" / "agents" / "explorer.md").exists()
    assert not cache.exists()


def test_remove_restores_colliding_remaining_source(tmp_path, monkeypatch):
    cache_a = tmp_path / "cache-a"
    cache_b = tmp_path / "cache-b"
    for cache, label in ((cache_a, "A"), (cache_b, "B")):
        roles = cache / "roles"
        roles.mkdir(parents=True)
        _write_role(roles / "explorer.md", "explorer", body=f"# Source {label}\n")
        _write_source_config(cache / "roles.toml")

    def fake_fetch_source(parsed):
        return {"org/a": cache_a, "org/b": cache_b}[parsed.cache_key]

    monkeypatch.setattr("role_forge.registry.fetch_source", fake_fetch_source)
    monkeypatch.setattr("role_forge.registry.read_head_commit", lambda repo_dir: "abc123def456")

    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)

    result = runner.invoke(app, ["add", "org/a", "--yes", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["add", "org/b", "--yes", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "# Source B" in (project / ".claude" / "agents" / "explorer.md").read_text()

    result = runner.invoke(app, ["remove", "org/b", "--yes", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "# Source A" in (project / ".claude" / "agents" / "explorer.md").read_text()


def test_remove_unknown_local_source_fails(tmp_path):
    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(
        app, ["remove", str(tmp_path / "missing-source"), "--project-dir", str(project)]
    )

    assert result.exit_code == 1
    assert "Source not recorded" in result.output


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
