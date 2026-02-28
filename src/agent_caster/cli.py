"""CLI entry point for agent-caster."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from agent_caster import __version__
from agent_caster.log import logger

DEFAULT_REFIT_TOML = """\
[project]
agents_dir = ".agents/roles"

[targets.opencode]
enabled = true
output_dir = "."

[targets.opencode.model_map]
reasoning = "github-copilot/claude-opus-4.6"
coding = "github-copilot/gpt-5.2-codex"

[targets.claude]
enabled = true
output_dir = "."

[targets.claude.model_map]
reasoning = "claude-opus-4.6"
coding = "claude-sonnet-4"
"""


def _version_callback(value: bool) -> None:
    if value:
        logger.info(f"agent-caster {__version__}")
        raise typer.Exit()


app = typer.Typer(help="agent-caster: Cross-platform AI coding agent definition caster.")


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """agent-caster: Cross-platform AI coding agent definition caster."""


@app.command()
def init(
    directory: Annotated[str, typer.Option("--dir", help="Project directory")] = ".",
) -> None:
    """Initialize a new agent-caster project."""
    project = Path(directory).resolve()

    agents_dir = project / ".agents" / "roles"
    agents_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created {agents_dir}")

    config_path = project / "refit.toml"
    if config_path.exists():
        logger.info(f"refit.toml already exists at {config_path}, skipping")
    else:
        config_path.write_text(DEFAULT_REFIT_TOML, encoding="utf-8")
        logger.info(f"Created {config_path}")

    logger.info("\nNext steps:")
    logger.info("  1. Add agent definitions to .agents/roles/")
    logger.info("  2. Configure targets in refit.toml")
    logger.info("  3. Run: agent-caster cast")


@app.command("cast")
def cast_cmd(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s) to cast")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview output without writing")
    ] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Cast canonical agent definitions to platform configs."""
    from agent_caster.caster import cast_agents, write_outputs

    root = Path(project_dir).resolve() if project_dir else None
    targets_list = list(target) if target else None

    try:
        result, config, project_root = cast_agents(project_root=root, targets=targets_list)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(1) from e

    if dry_run:
        for target_name, files in result.outputs.items():
            logger.info(f"\n=== Target: {target_name} ({len(files)} files) ===")
            for f in files:
                logger.info(f"\n-- {f.path} --")
                lines = f.content.split("\n")
                preview = "\n".join(lines[:40])
                logger.info(preview)
                if len(lines) > 40:
                    logger.info(f"  ... ({len(lines) - 40} more lines)")
    else:
        written = write_outputs(result, project_root, config)
        logger.info(f"Cast {len(written)} files:")
        for p in written:
            try:
                logger.info(f"  {p.relative_to(project_root)}")
            except ValueError:
                logger.info(f"  {p}")


@app.command("list")
def list_agents(
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """List all agent definitions."""
    from agent_caster.config import find_config, load_config
    from agent_caster.loader import load_agents

    if project_dir:
        root = Path(project_dir).resolve()
        config = load_config(root / "refit.toml")
    else:
        config_path = find_config()
        root = config_path.parent
        config = load_config(config_path)

    agents = load_agents(root / config.agents_dir)

    logger.info(f"{'AGENT':<25} {'ROLE':<10} {'TIER':<12} {'TEMP':<6}")
    logger.info("-" * 55)
    for agent in agents:
        temp = str(agent.model.temperature) if agent.model.temperature is not None else "-"
        logger.info(f"{agent.name:<25} {agent.role:<10} {agent.model.tier:<12} {temp:<6}")

    logger.info(f"\n{len(agents)} agents found in {config.agents_dir}")
