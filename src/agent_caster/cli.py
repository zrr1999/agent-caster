"""CLI entry point for agent-caster."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer

from agent_caster import __version__
from agent_caster.adapters import list_adapters
from agent_caster.log import logger

app = typer.Typer(
    help=("agent-caster: install canonical role definitions and render them across coding tools.")
)


def _version_callback(value: bool) -> None:
    if value:
        logger.info(f"agent-caster {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """agent-caster: install canonical role definitions and render them across tools."""


def _resolve_target_config(
    target_name: str,
    adapter,
    project: Path,
    interactive: bool = True,
):
    """Build TargetConfig: roles.toml > adapter defaults > interactive prompt."""
    from agent_caster.config import find_config, load_config
    from agent_caster.models import TargetConfig

    # 1. Try roles.toml (or legacy refit.toml with deprecation warning)
    config_path = find_config(project)
    if config_path is not None:
        project_config = load_config(config_path)
        if target_name in project_config.targets:
            cfg = project_config.targets[target_name]
            if cfg.model_map:
                return cfg

    # 2. Adapter has defaults → use them
    if adapter.default_model_map:
        return TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map=adapter.default_model_map,
        )

    # 3. No defaults, no config → prompt user
    if interactive:
        logger.info(f"\nNo model config found for '{target_name}'. Please specify:")
        reasoning = typer.prompt("  reasoning model")
        coding = typer.prompt("  coding model")
        return TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map={"reasoning": reasoning, "coding": coding},
        )

    logger.error(
        f"No model_map for '{target_name}'. Add [targets.{target_name}.model_map] to roles.toml."
    )
    raise typer.Exit(1)


def _render_agents_to_targets(project: Path, agents, target_names: list[str]) -> None:
    from agent_caster.adapters import get_adapter
    from agent_caster.topology import TopologyError

    for target_name in target_names:
        try:
            adapter = get_adapter(target_name)
        except ValueError as e:
            logger.error(str(e))
            continue

        config = _resolve_target_config(target_name, adapter, project)

        try:
            outputs = adapter.cast(agents, config)
        except TopologyError as e:
            logger.error(str(e))
            raise typer.Exit(1) from e

        _write_outputs(project, outputs, config.output_dir)
        logger.info(f"Rendered {len(outputs)} roles -> {target_name}")


def _write_outputs(project: Path, outputs, output_dir: str) -> None:
    """Write cast outputs beneath the configured output_dir."""
    for out in outputs:
        full_path = (project / output_dir / out.path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(out.content, encoding="utf-8")


def _resolve_remove_target(agents, ref: str):
    """Resolve a remove reference by canonical id first, then by unique name."""
    by_id = {agent.canonical_id: agent for agent in agents}
    if ref in by_id:
        return by_id[ref]

    matches = [agent for agent in agents if agent.name == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        choices = ", ".join(agent.canonical_id for agent in matches)
        logger.error(f"Ambiguous agent name '{ref}'. Use one of: {choices}")
        raise typer.Exit(1)

    logger.error(f"Agent not found: {ref}")
    raise typer.Exit(1)


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Source: org/repo[@ref] or local path")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Install to ~/.agents/roles/")
    ] = False,
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Cast target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Add agent definitions from a source."""
    from agent_caster.loader import load_agents
    from agent_caster.platform import detect_platforms
    from agent_caster.registry import fetch_source, find_agents_dir, parse_source
    from agent_caster.topology import TopologyError, validate_agents

    parsed = parse_source(source)

    try:
        repo_path = fetch_source(parsed)
    except Exception as e:
        logger.error(f"Error fetching source: {e}")
        raise typer.Exit(1) from e

    try:
        agents_dir = find_agents_dir(repo_path)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from e

    agents = load_agents(agents_dir)
    if not agents:
        logger.error("No agent definitions found in source.")
        raise typer.Exit(1)
    try:
        validate_agents(agents)
    except TopologyError as e:
        logger.error(str(e))
        raise typer.Exit(1) from e

    logger.info(f"Found {len(agents)} agents:")
    for a in agents:
        logger.info(f"  {a.canonical_id:<25} {a.role:<10} {a.model.tier}")

    # Determine install target
    if global_install:
        install_dir = Path.home() / ".agents" / "roles"
    else:
        project = Path(project_dir).resolve() if project_dir else Path.cwd()
        install_dir = project / ".agents" / "roles"

    install_dir.mkdir(parents=True, exist_ok=True)

    # Copy agent files
    for a in agents:
        if a.source_path:
            dest = install_dir / a.install_relative_path()
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.source_path, dest)
            logger.info(f"  Installed {a.canonical_id}")

    logger.info(f"\nInstalled {len(agents)} agents to {install_dir}")

    # Auto-cast
    if global_install and not target:
        return

    project = Path(project_dir).resolve() if project_dir else Path.cwd()

    cast_targets = list(target) if target else detect_platforms(project)

    if not cast_targets:
        return

    installed_agents = load_agents(install_dir)
    for target_name in cast_targets:
        _render_agents_to_targets(project, installed_agents, [target_name])


@app.command("list")
def list_agents(
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """List all installed agent definitions."""
    from agent_caster.loader import load_agents

    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    agents_dir = project / ".agents" / "roles"

    if not agents_dir.is_dir():
        logger.error("No agents found. Run 'agent-caster add' first.")
        raise typer.Exit(1)

    agents = load_agents(agents_dir)

    logger.info(f"{'AGENT':<25} {'ID':<25} {'ROLE':<10} {'TIER':<12} {'TEMP':<6}")
    logger.info("-" * 82)
    for agent in agents:
        temp = str(agent.model.temperature) if agent.model.temperature is not None else "-"
        logger.info(
            f"{agent.name:<25} {agent.canonical_id:<25} {agent.role:<10} "
            f"{agent.model.tier:<12} {temp:<6}"
        )

    logger.info(f"\n{len(agents)} agents found")


def _render_command(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Render installed role definitions to platform-specific configs."""
    from agent_caster.loader import load_agents
    from agent_caster.platform import detect_platforms
    from agent_caster.topology import TopologyError, validate_agents

    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    agents_dir = project / ".agents" / "roles"

    if not agents_dir.is_dir():
        logger.error("No agents found. Run 'agent-caster add' first.")
        raise typer.Exit(1)

    agents = load_agents(agents_dir)
    try:
        validate_agents(agents)
    except TopologyError as e:
        logger.error(str(e))
        raise typer.Exit(1) from e
    cast_targets = list(target) if target else detect_platforms(project)

    if not cast_targets:
        logger.error(
            f"No platforms detected. Use --target to specify one of: {', '.join(list_adapters())}"
        )
        raise typer.Exit(1)

    _render_agents_to_targets(project, agents, cast_targets)


@app.command()
def render(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Render installed role definitions to platform-specific configs."""
    _render_command(target=target, project_dir=project_dir)


@app.command()
def cast(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Legacy alias for `render`."""
    _render_command(target=target, project_dir=project_dir)


@app.command()
def remove(
    agent_name: Annotated[str, typer.Argument(help="Agent canonical id or unique name to remove")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Remove an installed agent definition."""
    from agent_caster.loader import load_agents

    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    agents_dir = project / ".agents" / "roles"
    if not agents_dir.is_dir():
        logger.error("No agents found. Run 'agent-caster add' first.")
        raise typer.Exit(1)

    agent = _resolve_remove_target(load_agents(agents_dir), agent_name)
    agent_file = agents_dir / agent.install_relative_path()
    agent_file.unlink()
    logger.info(f"Removed {agent.canonical_id}")
    logger.info(
        "Note: platform-specific files may still exist. Run 'agent-caster render' to regenerate."
    )


@app.command()
def update(
    source: Annotated[str, typer.Argument(help="Source to update: org/repo")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Cast target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Update agent definitions from a previously added source."""
    from agent_caster.registry import parse_source

    parsed = parse_source(source)
    if parsed.is_local:
        logger.error("Cannot update a local source. Use 'add' instead.")
        raise typer.Exit(1)

    # Re-use add logic — fetch_source will git pull if cached
    add(source=source, yes=yes, global_install=False, target=target, project_dir=project_dir)
