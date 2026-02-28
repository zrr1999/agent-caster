"""Tests for CLI commands."""

from typer.testing import CliRunner

from agent_caster.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agent-caster" in result.output


def test_init(tmp_path):
    result = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".agents" / "roles").is_dir()
    assert (tmp_path / "refit.toml").is_file()


def test_init_existing_config(tmp_path):
    (tmp_path / "refit.toml").write_text("existing")
    result = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "already exists" in result.output
    assert (tmp_path / "refit.toml").read_text() == "existing"


def test_list_agents(fixtures_dir):
    result = runner.invoke(app, ["list", "--project-dir", str(fixtures_dir)])
    assert result.exit_code == 0
    assert "explorer" in result.output
    assert "aligner" in result.output
    assert "3 agents found" in result.output


def test_cast_dry_run(fixtures_dir):
    result = runner.invoke(
        app, ["cast", "--dry-run", "--target", "opencode", "--project-dir", str(fixtures_dir)]
    )
    assert result.exit_code == 0
    assert "Target: opencode" in result.output
    assert ".opencode/agents/explorer.md" in result.output


def test_cast_writes_files(fixtures_dir, tmp_path):
    """Cast to a temp dir and verify files are created."""
    import shutil

    shutil.copytree(fixtures_dir, tmp_path / "project", dirs_exist_ok=True)
    project = tmp_path / "project"

    result = runner.invoke(app, ["cast", "--target", "opencode", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert (project / ".opencode" / "agents" / "explorer.md").is_file()
