"""CLI entry point for role-forge."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import typer

from role_forge import __version__
from role_forge.adapters import list_adapters
from role_forge.log import logger

app = typer.Typer(
    help=("role-forge: install canonical role definitions and render them across coding tools.")
)

Scope = Literal["project", "user"]


@dataclass(frozen=True)
class InstallPlan:
    install_dir: Path
    new_agents: list[Any]
    overwrite_agents: list[Any]


def _version_callback(value: bool) -> None:
    if value:
        _info(f"role-forge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """role-forge: install canonical role definitions and render them across tools."""


def _style(text: str, *, fg: str | None = None, bold: bool = False) -> str:
    return typer.style(text, fg=fg, bold=bold)


def _info(message: str) -> None:
    logger.info(_style(message, fg=typer.colors.CYAN))


def _success(message: str) -> None:
    logger.info(_style(message, fg=typer.colors.GREEN, bold=True))


def _warn(message: str) -> None:
    logger.warning(_style(message, fg=typer.colors.YELLOW, bold=True))


def _error(message: str) -> None:
    logger.error(_style(message, fg=typer.colors.RED, bold=True))


def _dim(text: str) -> str:
    return typer.style(text, fg=typer.colors.BRIGHT_BLACK)


def _bullet(label: str, value: str = "") -> str:
    if value:
        return f"  {_style('•', fg=typer.colors.BLUE)} {label}: {value}"
    return f"  {_style('•', fg=typer.colors.BLUE)} {label}"


def _resolve_target_config(
    target_name: str,
    adapter,
    project: Path,
    interactive: bool = True,
):
    """Build TargetConfig: roles.toml > adapter defaults > interactive prompt."""
    from role_forge.config import find_config, load_config
    from role_forge.models import TargetConfig

    config_path = find_config(project)
    if config_path is not None:
        project_config = load_config(config_path)
        if target_name in project_config.targets:
            cfg = project_config.targets[target_name]
            if cfg.model_map:
                return cfg

    if adapter.default_model_map:
        return TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map=adapter.default_model_map,
        )

    if interactive:
        _info(f"No model config found for target '{target_name}'.")
        reasoning = typer.prompt("  reasoning model")
        coding = typer.prompt("  coding model")
        return TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map={"reasoning": reasoning, "coding": coding},
        )

    _error(
        f"No model_map for '{target_name}'. Add [targets.{target_name}.model_map] to roles.toml."
    )
    raise typer.Exit(1)


def _resolve_project(project_dir: str | None) -> Path:
    return Path(project_dir).resolve() if project_dir else Path.cwd()


def _resolve_roles_dir(project: Path) -> Path:
    from role_forge.config import resolve_roles_dir

    return resolve_roles_dir(project)


def _resolve_scope(global_scope: bool) -> Scope:
    return "user" if global_scope else "project"


def _scope_label(scope: Scope) -> str:
    return "user" if scope == "user" else "project"


def _roles_not_found_message(scope: Scope, roles_dir: Path) -> str:
    return f"No roles found in {_scope_label(scope)} scope: {roles_dir}"


def _load_agents_in_scope(project: Path, scope: Scope):
    from role_forge.loader import load_agents_in_scope

    roles_dir, agents = load_agents_in_scope(project, scope=scope)
    if agents:
        return roles_dir, agents

    _error(_roles_not_found_message(scope, roles_dir))
    raise typer.Exit(1)


def _load_merged_agents(project: Path):
    from role_forge.loader import load_merged_agents

    agents = load_merged_agents(project)
    if agents:
        return agents

    _error("No roles found in project or user scope. Run 'role-forge add' first.")
    raise typer.Exit(1)


def _serialize_agent(agent, *, scope: Scope) -> dict[str, Any]:
    return {
        "name": agent.name,
        "canonical_id": agent.canonical_id,
        "role": agent.role,
        "tier": agent.model.tier,
        "temperature": agent.model.temperature,
        "relative_path": agent.relative_path,
        "source_path": str(agent.source_path) if agent.source_path else None,
        "scope": scope,
    }


def _scan_unmanaged_files(project: Path, scope: Scope):
    from role_forge.config import USER_ROLES_DIR
    from role_forge.loader import find_unmanaged_files

    roles_dir = USER_ROLES_DIR if scope == "user" else _resolve_roles_dir(project)
    return roles_dir, find_unmanaged_files(roles_dir)


def _render_agents_to_targets(
    project: Path,
    agents,
    target_names: list[str],
    *,
    interactive: bool = True,
) -> None:
    from role_forge.adapters import get_adapter
    from role_forge.topology import TopologyError

    for target_name in target_names:
        try:
            adapter = get_adapter(target_name)
        except ValueError as e:
            _error(str(e))
            continue

        config = _resolve_target_config(target_name, adapter, project, interactive=interactive)

        try:
            outputs = adapter.cast(agents, config)
        except TopologyError as e:
            _error(str(e))
            raise typer.Exit(1) from e

        _write_outputs(project, outputs, config.output_dir)
        _success(f"Rendered {len(outputs)} roles -> {target_name}")


def _write_outputs(project: Path, outputs, output_dir: str) -> None:
    for out in outputs:
        full_path = (project / output_dir / out.path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(out.content, encoding="utf-8")


def _resolve_remove_target(agents, ref: str):
    by_id = {agent.canonical_id: agent for agent in agents}
    if ref in by_id:
        return by_id[ref]

    matches = [agent for agent in agents if agent.name == ref]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        choices = ", ".join(agent.canonical_id for agent in matches)
        _error(f"Ambiguous agent name '{ref}'. Use one of: {choices}")
        raise typer.Exit(1)

    _error(f"Agent not found: {ref}")
    raise typer.Exit(1)


def _format_source_error(exc: Exception, source: str) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        cmd = " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd)
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or str(exc)
        return f"Failed to fetch source '{source}'.\n  step: {cmd}\n  detail: {detail}"
    return f"Failed to fetch source '{source}'.\n  detail: {exc}"


def _format_roles_dir_error(source: str, repo_path: Path) -> str:
    return (
        f"Fetched source '{source}', but no role definitions were found.\n"
        f"  cache: {repo_path}\n"
        "  expected: a `roles.toml` with `project.roles_dir`, or a `roles/` directory"
    )


def _show_agent_table(agents) -> None:
    _info(f"Found {len(agents)} role(s):")
    for agent in agents:
        logger.info(
            _bullet(
                agent.canonical_id,
                f"role={agent.role}, tier={agent.model.tier}",
            )
        )


def _build_install_plan(install_dir: Path, agents) -> InstallPlan:
    new_agents = []
    overwrite_agents = []
    for agent in agents:
        destination = install_dir / agent.install_relative_path()
        if destination.exists():
            overwrite_agents.append(agent)
        else:
            new_agents.append(agent)
    return InstallPlan(
        install_dir=install_dir, new_agents=new_agents, overwrite_agents=overwrite_agents
    )


def _confirm_install(plan: InstallPlan, scope: Scope, yes: bool) -> None:
    _info("Install plan")
    logger.info(_bullet("target", str(plan.install_dir)))
    logger.info(_bullet("scope", _scope_label(scope)))
    logger.info(_bullet("new", str(len(plan.new_agents))))
    logger.info(_bullet("overwrite", str(len(plan.overwrite_agents))))

    if yes:
        return

    if not plan.overwrite_agents:
        return

    if not typer.confirm("Continue and allow overwrite prompts?", default=True):
        _warn("Install cancelled.")
        raise typer.Exit(1)


def _copy_agents(plan: InstallPlan, yes: bool) -> list[Any]:
    installed = []
    for agent in [*plan.new_agents, *plan.overwrite_agents]:
        assert agent.source_path is not None
        destination = plan.install_dir / agent.install_relative_path()
        if destination.exists() and not yes:
            should_overwrite = typer.confirm(f"Overwrite '{agent.canonical_id}'?", default=True)
            if not should_overwrite:
                _warn(f"Skipped {agent.canonical_id}")
                continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent.source_path, destination)
        installed.append(agent)
        logger.info(_bullet("installed", agent.canonical_id))
    return installed


def _render_after_add(
    project: Path,
    target: list[str] | None,
    global_install: bool,
    interactive: bool,
) -> None:
    from role_forge.platform import resolve_targets

    if global_install and not target:
        _info("Skipped rendering because this was a global install with no explicit targets.")
        return

    cast_targets = list(target) if target else resolve_targets(project)
    if not cast_targets:
        _info("Installed canonical roles. No render target detected in this project.")
        return

    agents = _load_merged_agents(project)
    _render_agents_to_targets(project, agents, cast_targets, interactive=interactive)


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
    from role_forge.config import USER_ROLES_DIR
    from role_forge.loader import load_agents
    from role_forge.registry import fetch_source, find_roles_dir, parse_source
    from role_forge.topology import TopologyError, validate_agents

    parsed = parse_source(source)
    try:
        repo_path = fetch_source(parsed)
    except Exception as e:
        _error(_format_source_error(e, source))
        raise typer.Exit(1) from e

    try:
        roles_dir = find_roles_dir(repo_path)
    except FileNotFoundError as e:
        _error(_format_roles_dir_error(source, repo_path))
        raise typer.Exit(1) from e

    agents = load_agents(roles_dir)
    if not agents:
        _error("No role definitions found in source.")
        raise typer.Exit(1)

    try:
        validate_agents(agents)
    except TopologyError as e:
        _error(str(e))
        raise typer.Exit(1) from e

    _show_agent_table(agents)

    project = _resolve_project(project_dir)
    scope = _resolve_scope(global_install)
    install_dir = USER_ROLES_DIR if global_install else _resolve_roles_dir(project)
    install_dir.mkdir(parents=True, exist_ok=True)

    plan = _build_install_plan(install_dir, agents)
    _confirm_install(plan, scope, yes)
    installed_agents = _copy_agents(plan, yes)

    if not installed_agents:
        _warn("No roles were installed.")
        return

    _success(f"Installed {len(installed_agents)} role(s)")
    logger.info(_bullet("location", str(install_dir)))
    _render_after_add(project, target, global_install, interactive=not yes)


@app.command("list")
def list_agents(
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="List roles from ~/.agents/roles/")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output roles as JSON")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """List installed agent definitions for one scope."""
    from role_forge.loader import load_agents_in_scope

    project = _resolve_project(project_dir)
    scope = _resolve_scope(global_install)
    roles_dir, agents = load_agents_in_scope(project, scope=scope)

    if json_output:
        logger.info(
            json.dumps([_serialize_agent(agent, scope=scope) for agent in agents], indent=2)
        )
        return

    if not agents:
        _error(_roles_not_found_message(scope, roles_dir))
        raise typer.Exit(1)

    _info(f"Roles in {_scope_label(scope)} scope")
    logger.info(_dim(f"  {roles_dir}"))
    logger.info(f"{'AGENT':<25} {'ID':<25} {'ROLE':<10} {'TIER':<12} {'TEMP':<6}")
    logger.info(_dim("-" * 82))
    for agent in agents:
        temp = str(agent.model.temperature) if agent.model.temperature is not None else "-"
        logger.info(
            f"{agent.name:<25} {agent.canonical_id:<25} {agent.role:<10} "
            f"{agent.model.tier:<12} {temp:<6}"
        )

    _success(f"{len(agents)} role(s) found in {_scope_label(scope)} scope")


def _render_command(
    target: list[str] | None,
    project_dir: str | None,
) -> None:
    from role_forge.platform import resolve_targets
    from role_forge.topology import TopologyError, validate_agents

    project = _resolve_project(project_dir)
    agents = _load_merged_agents(project)
    try:
        validate_agents(agents)
    except TopologyError as e:
        _error(str(e))
        raise typer.Exit(1) from e

    cast_targets = list(target) if target else resolve_targets(project)
    if not cast_targets:
        _error(
            "No render targets detected in this project.\n"
            f"  available: {', '.join(list_adapters())}\n"
            "  next step: rerun with `--target <name>`"
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
    """Removed compatibility alias. Use `render` instead."""
    _error("`cast` has been removed. Use `role-forge render` instead.")
    raise typer.Exit(1)


@app.command()
def remove(
    agent_name: Annotated[str, typer.Argument(help="Agent canonical id or unique name to remove")],
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Remove from ~/.agents/roles/")
    ] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Remove an installed agent definition from one scope."""
    project = _resolve_project(project_dir)
    roles_dir, agents = _load_agents_in_scope(project, _resolve_scope(global_install))
    agent = _resolve_remove_target(agents, agent_name)
    agent_file = agent.source_path or roles_dir / agent.install_relative_path()
    agent_file.unlink()
    _success(f"Removed {agent.canonical_id}")
    _info("If target files still reference it, run `role-forge render` to regenerate outputs.")


@app.command()
def doctor(
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Inspect ~/.agents/roles/")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output findings as JSON")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Inspect unmanaged files under the selected roles directory."""
    project = _resolve_project(project_dir)
    scope = _resolve_scope(global_install)
    roles_dir, issues = _scan_unmanaged_files(project, scope)

    payload = {
        "scope": scope,
        "roles_dir": str(roles_dir),
        "issue_count": len(issues),
        "issues": [
            {
                "path": str(issue.path),
                "relative_path": issue.path.relative_to(roles_dir).as_posix(),
                "reason": issue.reason,
            }
            for issue in issues
        ],
    }

    if json_output:
        logger.info(json.dumps(payload, indent=2))
        return

    if not issues:
        _success(f"No unmanaged files found in {_scope_label(scope)} scope")
        logger.info(_dim(f"  {roles_dir}"))
        return

    _warn(f"Found {len(issues)} unmanaged file(s) in {_scope_label(scope)} scope")
    logger.info(_dim(f"  {roles_dir}"))
    for issue in issues:
        relative_path = issue.path.relative_to(roles_dir).as_posix()
        logger.info(_bullet(relative_path, issue.reason))


@app.command()
def clean(
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Clean ~/.agents/roles/")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show unmanaged files without deleting")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Delete unmanaged files under the selected roles directory."""
    project = _resolve_project(project_dir)
    scope = _resolve_scope(global_install)
    roles_dir, issues = _scan_unmanaged_files(project, scope)

    if not issues:
        _success(f"No unmanaged files found in {_scope_label(scope)} scope")
        logger.info(_dim(f"  {roles_dir}"))
        return

    heading = "Would remove" if dry_run else "Removing"
    _warn(f"{heading} {len(issues)} unmanaged file(s) from {_scope_label(scope)} scope")
    logger.info(_dim(f"  {roles_dir}"))
    for issue in issues:
        relative_path = issue.path.relative_to(roles_dir).as_posix()
        logger.info(_bullet(relative_path, issue.reason))

    if dry_run:
        return

    if not yes and not typer.confirm(f"Remove {len(issues)} unmanaged file(s)?", default=False):
        _warn("Clean cancelled.")
        raise typer.Exit(1)

    for issue in issues:
        issue.path.unlink()

    _success(f"Removed {len(issues)} unmanaged file(s)")


@app.command()
def update(
    source: Annotated[str, typer.Argument(help="Source to update: org/repo")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Update ~/.agents/roles/")
    ] = False,
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Cast target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Update agent definitions from a previously added source."""
    from role_forge.registry import parse_source

    parsed = parse_source(source)
    if parsed.is_local:
        _error("Cannot update a local source. Use 'add' instead.")
        raise typer.Exit(1)

    add(
        source=source,
        yes=yes,
        global_install=global_install,
        target=target,
        project_dir=project_dir,
    )
