"""CLI entry point for role-forge."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from loguru import logger

from role_forge import __version__
from role_forge.adapters import list_adapters

# Default: only WARNING and above so INFO/DEBUG are hidden unless configured elsewhere.
logger.remove()
logger.add(sys.stderr, level="WARNING")

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
    typer.echo(_style(message, fg=typer.colors.CYAN))


def _success(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.GREEN, bold=True))


def _warn(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.YELLOW, bold=True))


def _error(message: str) -> None:
    # Errors are printed to stdout so that Typer's CliRunner (and users) can always see them.
    typer.echo(_style(message, fg=typer.colors.RED, bold=True))


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
    source_project: Path | None = None,
):
    """TargetConfig: source repo toml > project toml > adapter defaults. No model prompt."""
    from role_forge.config import find_config, load_config
    from role_forge.models import TargetConfig

    def _is_within_root(root: Path, candidate: Path) -> bool:
        try:
            candidate.relative_to(root)
            return True
        except ValueError:
            return False

    def _validate_output_dir(cfg: TargetConfig, *, root: Path) -> TargetConfig:
        if Path(cfg.output_dir).is_absolute():
            _error(f"Target '{target_name}' output_dir must be project-relative: {cfg.output_dir}")
            raise typer.Exit(1)
        output_path = (root / cfg.output_dir).resolve()
        if not _is_within_root(root.resolve(), output_path):
            _error(
                f"Target '{target_name}' output_dir points outside the project: {cfg.output_dir}"
            )
            raise typer.Exit(1)
        return cfg

    def _accept_config(cfg: TargetConfig, *, root: Path) -> TargetConfig | None:
        if adapter.requires_model_map and not cfg.model_map:
            return None
        return _validate_output_dir(cfg, root=root)

    # Prefer source repo roles.toml when rendering after add/update
    if source_project is not None:
        src_config_path = find_config(source_project)
        if src_config_path is not None:
            src_config = load_config(src_config_path)
            if target_name in src_config.targets:
                cfg = src_config.targets[target_name]
                accepted = _accept_config(cfg, root=project)
                if accepted is not None:
                    return accepted

    config_path = find_config(project)
    if config_path is not None:
        project_config = load_config(config_path)
        if target_name in project_config.targets:
            cfg = project_config.targets[target_name]
            accepted = _accept_config(cfg, root=project)
            if accepted is not None:
                return accepted

    if adapter.default_model_map:
        return _validate_output_dir(
            TargetConfig(
                name=target_name,
                enabled=True,
                output_dir=".",
                model_map=adapter.default_model_map,
            ),
            root=project,
        )

    if not adapter.requires_model_map:
        return _validate_output_dir(
            TargetConfig(name=target_name, enabled=True, output_dir="."),
            root=project,
        )

    _error(
        f"No model_map for '{target_name}'. Add [targets.{target_name}.model_map] to roles.toml "
        f"(in the source repo or current project)."
    )
    raise typer.Exit(1)


def _resolve_project(project_dir: str | None) -> Path:
    return Path(project_dir).resolve() if project_dir else Path.cwd()


def _resolve_roles_dir(project: Path) -> Path:
    from role_forge.config import resolve_roles_dir

    return resolve_roles_dir(project)


def _resolve_scope(global_scope: bool) -> Scope:
    return "user" if global_scope else "project"


def _prompt_scope(prompt: str = "Install to (p)roject or (g)lobal?") -> Scope:
    """Interactively ask for project vs user (global) scope. Default project."""
    raw = typer.prompt(prompt, default="p").strip().lower()
    if raw in ("g", "global"):
        return "user"
    return "project"


def _scope_label(scope: Scope) -> str:
    return "user" if scope == "user" else "project"


def _roles_not_found_message(scope: Scope, roles_dir: Path) -> str:
    return f"No roles found in {_scope_label(scope)} scope: {roles_dir}"


def _load_agents_in_scope(project: Path, scope: Scope):
    from role_forge.loader import load_agents_in_scope

    try:
        roles_dir, agents = load_agents_in_scope(project, scope=scope)
    except Exception as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc
    if agents:
        return roles_dir, agents

    _error(_roles_not_found_message(scope, roles_dir))
    raise typer.Exit(1)


def _load_merged_agents(project: Path):
    from role_forge.loader import load_merged_agents

    try:
        agents = load_merged_agents(project)
    except Exception as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc
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
    source_project: Path | None = None,
) -> None:
    from role_forge.adapters import get_adapter
    from role_forge.topology import TopologyError

    for target_name in target_names:
        try:
            adapter = get_adapter(target_name)
        except ValueError as e:
            _error(str(e))
            continue

        config = _resolve_target_config(
            target_name, adapter, project, interactive=interactive, source_project=source_project
        )

        try:
            outputs = adapter.cast(agents, config)
        except TopologyError as e:
            _error(str(e))
            raise typer.Exit(1) from e

        outputs_to_write = _confirm_render_overwrite(
            project, config.output_dir, outputs, interactive
        )
        if outputs_to_write:
            _write_outputs(project, outputs_to_write, config.output_dir)
        _success(f"Rendered {len(outputs)} roles -> {target_name}")


def _confirm_render_overwrite(project: Path, output_dir: str, outputs, interactive: bool):
    """If interactive and some paths exist, prompt once. Return list to write (filtered or all)."""
    out_dir_path = project / output_dir
    existing = [o for o in outputs if (out_dir_path / o.path).exists()]
    if not existing or not interactive:
        return list(outputs)
    n = len(existing)
    display_dir = output_dir if output_dir != "." else str(project)
    if not typer.confirm(f"Overwrite {n} existing file(s) in {display_dir}?", default=True):
        existing_paths = {(out_dir_path / o.path).resolve() for o in existing}
        return [o for o in outputs if (out_dir_path / o.path).resolve() not in existing_paths]
    return list(outputs)


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


def _filter_agents_by_role(agents, role_patterns: list[str] | None):
    """Keep agents whose name or canonical_id matches any pattern (substring, case-insensitive)."""
    if not role_patterns:
        return list(agents)
    lower_patterns = [p.lower() for p in role_patterns]
    return [
        a
        for a in agents
        if any(pat in a.name.lower() or pat in a.canonical_id.lower() for pat in lower_patterns)
    ]


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


def _confirm_install(plan: InstallPlan, scope: Scope, yes: bool) -> bool:
    """Return True to include overwrites, False to install only new. Raises Exit on cancel."""
    _info("Install plan")
    logger.info(_bullet("target", str(plan.install_dir)))
    logger.info(_bullet("scope", _scope_label(scope)))
    logger.info(_bullet("new", str(len(plan.new_agents))))
    logger.info(_bullet("overwrite", str(len(plan.overwrite_agents))))

    if yes:
        return True
    if not plan.overwrite_agents:
        return True
    n = len(plan.overwrite_agents)
    if not typer.confirm(f"Overwrite {n} existing role(s)?", default=True):
        _warn("Skipping overwrites; only new roles will be installed.")
        return False
    return True


def _copy_agents(plan: InstallPlan, yes: bool, include_overwrites: bool) -> list[Any]:
    agents_to_copy = plan.new_agents + (plan.overwrite_agents if include_overwrites else [])
    installed = []
    for agent in agents_to_copy:
        assert agent.source_path is not None
        destination = plan.install_dir / agent.install_relative_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent.source_path, destination)
        installed.append(agent)
        logger.info(_bullet("installed", agent.canonical_id))
    return installed


def _resolve_render_targets(
    project: Path,
    target: list[str] | None,
    source_default_targets: list[str] | None,
) -> list[str]:
    """Resolve render targets in priority order:

    1. Explicit --target
    2. Targets from the source repo's roles.toml (if any)
    3. Fallback: current project roles.toml / auto-detected platforms
    """
    from role_forge.platform import resolve_targets

    if target:
        return list(target)
    if source_default_targets:
        return list(source_default_targets)
    return resolve_targets(project)


def _render_after_add(
    project: Path,
    target: list[str] | None,
    source_default_targets: list[str] | None,
    interactive: bool,
    no_render: bool,
    source_project: Path | None = None,
    global_install: bool = False,
) -> None:
    """Render after add/update; toml default. Use --no-render to skip or confirm if interactive."""
    if no_render:
        return
    default_targets = _resolve_render_targets(project, target, source_default_targets)
    if not default_targets:
        _info("Installed canonical roles. No render target detected in this project.")
        return
    if interactive and not typer.confirm(
        f"Render to {', '.join(default_targets)}?",
        default=True,
    ):
        _info("Skipped rendering. Run 'role-forge render' when needed.")
        return
    # Global install: render into home so ~/.opencode/agents etc. are populated
    render_root = Path.home() if global_install else project
    agents = _load_merged_agents(render_root)
    _render_agents_to_targets(
        render_root,
        agents,
        default_targets,
        interactive=interactive,
        source_project=source_project,
    )


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Source: org/repo[@ref] or local path")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Install to ~/.agents/roles/")
    ] = False,
    target: Annotated[
        list[str] | None,
        typer.Option("--target", "-t", help="Render to these targets (default: toml or auto)"),
    ] = None,
    no_render: Annotated[
        bool,
        typer.Option("--no-render", help="Skip render after install"),
    ] = False,
    role: Annotated[
        list[str] | None,
        typer.Option("--role", "-r", help="Install only roles matching (substring of name/id)"),
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Add agent definitions from a source. Renders to targets by default (toml or -t)."""
    from role_forge.config import USER_ROLES_DIR, find_config, load_config
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

    # Resolve default targets from the source repo's roles.toml (if present)
    source_default_targets: list[str] | None = None
    config_path = find_config(repo_path)
    if config_path is not None:
        project_config = load_config(config_path)
        enabled_targets = [name for name, cfg in project_config.targets.items() if cfg.enabled]
        if enabled_targets:
            source_default_targets = enabled_targets

    try:
        agents = load_agents(roles_dir, strict=True)
    except Exception as e:
        _error(str(e))
        raise typer.Exit(1) from e
    if not agents:
        _error("No role definitions found in source.")
        raise typer.Exit(1)

    try:
        validate_agents(agents)
    except TopologyError as e:
        _error(str(e))
        raise typer.Exit(1) from e

    agents = _filter_agents_by_role(agents, role)
    if not agents:
        _error("No roles match the given --role filter.")
        raise typer.Exit(1)

    _show_agent_table(agents)

    project = _resolve_project(project_dir)
    if yes:
        scope = _resolve_scope(global_install)
    elif global_install:
        scope = "user"
    else:
        scope = _prompt_scope()
        global_install = scope == "user"
    install_dir = USER_ROLES_DIR if global_install else _resolve_roles_dir(project)
    install_dir.mkdir(parents=True, exist_ok=True)

    plan = _build_install_plan(install_dir, agents)
    include_overwrites = _confirm_install(plan, scope, yes)
    if not include_overwrites and not plan.new_agents:
        _warn("Install cancelled.")
        raise typer.Exit(1)

    # Prune orphaned files when doing full update from remote (agent removed upstream)
    # Skip prune when --role filter is used (partial update)
    if not parsed.is_local and role is None:
        from role_forge.manifest import prune_orphaned, update_manifest_for_source

        current_paths = {a.install_relative_path() for a in agents}
        pruned = prune_orphaned(install_dir, parsed.cache_key, current_paths)
        for p in pruned:
            logger.info(_bullet("pruned", str(p.relative_to(install_dir))))

    installed_agents = _copy_agents(plan, yes, include_overwrites)

    # Update manifest for remote sources so future updates can prune correctly
    if not parsed.is_local:
        from role_forge.manifest import update_manifest_for_source

        # Merge with existing manifest when --role filter used (partial update)
        if role is not None:
            from role_forge.manifest import load_manifest, paths_for_source

            existing = set(paths_for_source(load_manifest(install_dir), parsed.cache_key))
            new_paths = existing | {a.install_relative_path() for a in agents}
            update_manifest_for_source(install_dir, parsed.cache_key, sorted(new_paths))
        else:
            update_manifest_for_source(
                install_dir, parsed.cache_key, [a.install_relative_path() for a in agents]
            )

    if not installed_agents:
        _warn("No roles were installed.")
        return

    _success(f"Installed {len(installed_agents)} role(s)")
    logger.info(_bullet("location", str(install_dir)))
    _render_after_add(
        project,
        target,
        source_default_targets,
        interactive=not yes,
        no_render=no_render,
        source_project=repo_path,
        global_install=global_install,
    )


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
    try:
        roles_dir, agents = load_agents_in_scope(project, scope=scope)
    except Exception as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc

    if json_output:
        typer.echo(json.dumps([_serialize_agent(agent, scope=scope) for agent in agents], indent=2))
        return

    if not agents:
        _error(_roles_not_found_message(scope, roles_dir))
        raise typer.Exit(1)

    _info(f"Roles in {_scope_label(scope)} scope")
    typer.echo(_dim(f"  {roles_dir}"))
    typer.echo(f"{'AGENT':<25} {'ID':<25} {'ROLE':<10} {'TIER':<12} {'TEMP':<6}")
    typer.echo(_dim("-" * 82))
    for agent in agents:
        temp = str(agent.model.temperature) if agent.model.temperature is not None else "-"
        typer.echo(
            f"{agent.name:<25} {agent.canonical_id:<25} {agent.role:<10} "
            f"{agent.model.tier:<12} {temp:<6}"
        )

    _success(f"{len(agents)} role(s) found in {_scope_label(scope)} scope")


def _render_command(
    target: list[str] | None,
    project_dir: str | None,
    role: list[str] | None = None,
    yes: bool = False,
) -> None:
    """Render installed roles to platform configs; optional --role filter (per-role)."""
    from role_forge.platform import resolve_targets
    from role_forge.topology import TopologyError, validate_agents

    project = _resolve_project(project_dir)
    agents = _load_merged_agents(project)
    agents = _filter_agents_by_role(agents, role)
    if not agents:
        _error("No roles to render (empty or no match for --role).")
        raise typer.Exit(1)
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

    _render_agents_to_targets(project, agents, cast_targets, interactive=not yes)


@app.command()
def render(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s)")
    ] = None,
    role: Annotated[
        list[str] | None,
        typer.Option("--role", "-r", help="Render only roles matching (substring of name/id)"),
    ] = None,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip overwrite prompt for output files")
    ] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Render installed role definitions to platform configs (optionally filter by --role)."""
    _render_command(target=target, project_dir=project_dir, role=role, yes=yes)


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
    rel_path = agent.install_relative_path()
    agent_file.unlink()
    from role_forge.manifest import remove_path_from_manifest

    remove_path_from_manifest(roles_dir, rel_path)
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
        typer.echo(json.dumps(payload, indent=2))
        return

    if not issues:
        _success(f"No unmanaged files found in {_scope_label(scope)} scope")
        typer.echo(_dim(f"  {roles_dir}"))
        return

    _warn(f"Found {len(issues)} unmanaged file(s) in {_scope_label(scope)} scope")
    typer.echo(_dim(f"  {roles_dir}"))
    for issue in issues:
        relative_path = issue.path.relative_to(roles_dir).as_posix()
        typer.echo(_bullet(relative_path, issue.reason))


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
        typer.echo(_dim(f"  {roles_dir}"))
        return

    heading = "Would remove" if dry_run else "Removing"
    _warn(f"{heading} {len(issues)} unmanaged file(s) from {_scope_label(scope)} scope")
    typer.echo(_dim(f"  {roles_dir}"))
    for issue in issues:
        relative_path = issue.path.relative_to(roles_dir).as_posix()
        typer.echo(_bullet(relative_path, issue.reason))

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
        list[str] | None,
        typer.Option("--target", "-t", help="Render to these targets (default: toml or auto)"),
    ] = None,
    no_render: Annotated[
        bool,
        typer.Option("--no-render", help="Skip render after update"),
    ] = False,
    role: Annotated[
        list[str] | None,
        typer.Option("--role", "-r", help="Update only roles matching (substring of name/id)"),
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Update from a previously added source. Renders to targets by default (toml or -t)."""
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
        no_render=no_render,
        role=role,
        project_dir=project_dir,
    )
