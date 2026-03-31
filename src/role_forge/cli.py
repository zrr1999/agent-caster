"""CLI entry point for role-forge."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from loguru import logger

from role_forge import __version__

logger.remove()
logger.add(sys.stderr, level="WARNING")

app = typer.Typer(
    help=("role-forge: fetch canonical role sources and generate platform-specific agent files.")
)


@dataclass(frozen=True)
class SourceBundle:
    source_key: str
    source_ref: str
    parsed: Any
    repo_path: Path
    config: Any | None
    agents: list[Any]


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
    """role-forge: fetch canonical role sources and generate platform-specific agent files."""


def _style(text: str, *, fg: str | None = None, bold: bool = False) -> str:
    return typer.style(text, fg=fg, bold=bold)


def _info(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.CYAN))


def _success(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.GREEN, bold=True))


def _warn(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.YELLOW, bold=True))


def _error(message: str) -> None:
    typer.echo(_style(message, fg=typer.colors.RED, bold=True))


def _dim(text: str) -> str:
    return typer.style(text, fg=typer.colors.BRIGHT_BLACK)


def _bullet(label: str, value: str = "") -> str:
    if value:
        return f"  {_style('•', fg=typer.colors.BLUE)} {label}: {value}"
    return f"  {_style('•', fg=typer.colors.BLUE)} {label}"


def _resolve_project(project_dir: str | None) -> Path:
    return Path(project_dir).resolve() if project_dir else Path.cwd()


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
        "  expected: 'roles/' directory or [project].roles_dir in roles.toml"
    )


def _normalize_source_ref(parsed) -> str:
    if parsed.is_local:
        return str(Path(parsed.local_path).resolve())
    return parsed.cache_key


def _filter_agents_by_role_patterns(agents, role_patterns: list[str] | None):
    if not role_patterns:
        return list(agents)
    lower_patterns = [pattern.lower() for pattern in role_patterns]
    return [
        agent
        for agent in agents
        if any(
            pattern in agent.name.lower() or pattern in agent.canonical_id.lower()
            for pattern in lower_patterns
        )
    ]


def _filter_agents_by_ids(agents, selected_role_ids: list[str]):
    wanted = set(selected_role_ids)
    filtered = [agent for agent in agents if agent.canonical_id in wanted]
    missing = sorted(wanted - {agent.canonical_id for agent in filtered})
    if missing:
        _error(f"Stored role selection no longer exists in source: {', '.join(missing)}")
        raise typer.Exit(1)
    return filtered


def _show_agent_table(agents) -> None:
    _info(f"Found {len(agents)} role(s):")
    for agent in agents:
        logger.info(_bullet(agent.canonical_id, f"role={agent.role}, tier={agent.model.tier}"))


def _load_source_bundle(
    source: str,
    *,
    role_patterns: list[str] | None = None,
    selected_role_ids: list[str] | None = None,
    fetch: bool = True,
) -> SourceBundle:
    from role_forge.config import find_config, load_config
    from role_forge.loader import load_agents
    from role_forge.manifest import source_entry
    from role_forge.registry import (
        cache_path_for_source,
        fetch_source,
        find_roles_dir,
        parse_source,
    )
    from role_forge.topology import TopologyError, validate_agents

    parsed = parse_source(source)
    if fetch:
        try:
            repo_path = fetch_source(parsed)
        except Exception as exc:
            _error(_format_source_error(exc, source))
            raise typer.Exit(1) from exc
    elif parsed.is_local:
        repo_path = Path(source).resolve()
    else:
        cache = source_entry(parsed.cache_key)
        repo_path = (
            Path(cache["cache_path"])
            if cache is not None and "cache_path" in cache
            else cache_path_for_source(parsed)
        )
        if not repo_path.is_dir():
            _error(f"Cached source not found: {parsed.cache_key}")
            raise typer.Exit(1)

    try:
        roles_dir = find_roles_dir(repo_path)
    except FileNotFoundError as exc:
        _error(_format_roles_dir_error(source, repo_path))
        raise typer.Exit(1) from exc

    config_path = find_config(repo_path)
    source_config = load_config(config_path) if config_path is not None else None

    try:
        agents = load_agents(roles_dir, strict=True)
    except Exception as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc
    if not agents:
        _error("No role definitions found in source.")
        raise typer.Exit(1)

    try:
        validate_agents(agents)
    except TopologyError as exc:
        _error(str(exc))
        raise typer.Exit(1) from exc

    if role_patterns is not None:
        agents = _filter_agents_by_role_patterns(agents, role_patterns)
    elif selected_role_ids is not None:
        agents = _filter_agents_by_ids(agents, selected_role_ids)

    if not agents:
        _error("No roles match the requested selection.")
        raise typer.Exit(1)

    return SourceBundle(
        source_key=_normalize_source_ref(parsed),
        source_ref=_normalize_source_ref(parsed),
        parsed=parsed,
        repo_path=repo_path,
        config=source_config,
        agents=agents,
    )


def _resolve_target_config(target_name: str, adapter, source_config):
    from role_forge.models import TargetConfig

    def _accept(cfg: TargetConfig) -> TargetConfig | None:
        if adapter.requires_model_map and not cfg.model_map:
            return None
        return cfg

    if source_config is not None and target_name in source_config.targets:
        accepted = _accept(source_config.targets[target_name])
        if accepted is not None:
            return accepted

    if adapter.default_model_map:
        return TargetConfig(name=target_name, enabled=True, model_map=adapter.default_model_map)

    if not adapter.requires_model_map:
        return TargetConfig(name=target_name, enabled=True)

    _error(
        f"No model_map for '{target_name}' in the source repo. "
        f"Add [targets.{target_name}.model_map] to roles.toml."
    )
    raise typer.Exit(1)


def _source_default_targets(source_config) -> list[str]:
    if source_config is None:
        return []
    return [name for name, cfg in source_config.targets.items() if cfg.enabled]


def _resolve_target_names(
    project: Path,
    *,
    explicit_targets: list[str] | None,
    previous_entry: dict[str, Any] | None,
    source_config,
) -> list[str]:
    from role_forge.platform import resolve_targets

    if explicit_targets:
        return list(explicit_targets)
    if previous_entry is not None:
        previous_targets = list(previous_entry.get("targets", {}))
        if previous_targets:
            return previous_targets
    source_targets = _source_default_targets(source_config)
    if source_targets:
        return source_targets
    return resolve_targets(project)


def _confirm_target_overwrite(project: Path, target_name: str, outputs, interactive: bool):
    existing = [output for output in outputs if (project / output.path).exists()]
    if not existing or not interactive:
        return list(outputs)

    if not typer.confirm(
        f"Overwrite {len(existing)} existing file(s) for {target_name} in {project}?",
        default=True,
    ):
        _warn(f"Skipped {target_name}.")
        return None

    return list(outputs)


def _write_outputs(project: Path, outputs) -> list[str]:
    written_paths: list[str] = []
    for output in outputs:
        full_path = (project / output.path).resolve()
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(output.content, encoding="utf-8")
        written_paths.append(output.path)
    return written_paths


def _render_source(
    project: Path,
    bundle: SourceBundle,
    target_names: list[str],
    *,
    interactive: bool,
) -> dict[str, dict[str, list[str]]]:
    from role_forge.adapters import get_adapter
    from role_forge.topology import TopologyError

    target_outputs: dict[str, dict[str, list[str]]] = {}
    selected_roles = [agent.canonical_id for agent in bundle.agents]

    for target_name in target_names:
        try:
            adapter = get_adapter(target_name)
        except ValueError as exc:
            _error(str(exc))
            raise typer.Exit(1) from exc

        config = _resolve_target_config(target_name, adapter, bundle.config)
        try:
            outputs = adapter.cast(bundle.agents, config)
        except TopologyError as exc:
            _error(str(exc))
            raise typer.Exit(1) from exc

        confirmed_outputs = _confirm_target_overwrite(project, target_name, outputs, interactive)
        if confirmed_outputs is None:
            continue

        written_paths = _write_outputs(project, confirmed_outputs)
        target_outputs[target_name] = {
            "selected_roles": list(selected_roles),
            "files": written_paths,
        }
        _success(f"Generated {len(written_paths)} file(s) -> {target_name}")

    return target_outputs


def _record_cached_source(bundle: SourceBundle) -> None:
    from role_forge.manifest import update_source
    from role_forge.registry import read_head_commit

    if bundle.parsed.is_local:
        return

    update_source(
        bundle.source_key,
        cache_key=bundle.parsed.cache_key,
        cache_path=bundle.repo_path,
        last_fetched_commit=read_head_commit(bundle.repo_path),
    )


def _cached_sources_payload() -> list[dict[str, str]]:
    from role_forge.manifest import load_manifest

    manifest = load_manifest()
    return [{"source_key": source_key, **entry} for source_key, entry in manifest.items()]


def _project_outputs_payload(project: Path) -> list[dict[str, Any]]:
    from role_forge.outputs import load_output_manifest

    entries = load_output_manifest(project)
    payload: list[dict[str, Any]] = []
    for source_key, entry in entries.items():
        targets = entry.get("targets", {})
        role_ids = sorted(
            {role for target in targets.values() for role in target.get("selected_roles", [])}
        )
        files = sorted({path for target in targets.values() for path in target.get("files", [])})
        payload.append(
            {
                "source_key": source_key,
                "source": entry["source"],
                "targets": sorted(targets),
                "role_ids": role_ids,
                "file_count": len(files),
                "files": files,
            }
        )
    return payload


def _delete_cached_source(source_key: str) -> None:
    from role_forge.manifest import remove_source, source_entry

    entry = source_entry(source_key)
    if entry is None:
        return

    cache_path = entry.get("cache_path")
    if cache_path:
        path = Path(cache_path)
        if path.is_dir():
            shutil.rmtree(path)
    remove_source(source_key)


def _rebuild_remaining_outputs(project: Path, entries: OrderedDict[str, dict[str, Any]]) -> None:
    from role_forge.outputs import save_output_manifest, update_source_outputs

    save_output_manifest(project, OrderedDict())
    for source_key, entry in entries.items():
        source_ref = entry["source"]
        target_selections = entry.get("targets", {})
        rebuilt_targets: dict[str, dict[str, list[str]]] = {}
        for target_name, target_entry in target_selections.items():
            selected_roles = target_entry.get("selected_roles", [])
            bundle = _load_source_bundle(
                source_ref,
                selected_role_ids=selected_roles,
                fetch=False,
            )
            rendered = _render_source(project, bundle, [target_name], interactive=False)
            if target_name in rendered:
                rebuilt_targets[target_name] = rendered[target_name]
        if rebuilt_targets:
            update_source_outputs(
                project,
                source_key=source_key,
                source=source_ref,
                targets=rebuilt_targets,
            )


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Source: org/repo[@ref] or local path")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip overwrite prompts")] = False,
    target: Annotated[
        list[str] | None,
        typer.Option(
            "--target", "-t", help="Generate these targets (default: source config or auto)"
        ),
    ] = None,
    role: Annotated[
        list[str] | None,
        typer.Option("--role", "-r", help="Generate only roles matching (substring of name/id)"),
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Fetch a source and generate project outputs."""
    from role_forge.outputs import load_output_manifest, update_source_outputs
    from role_forge.registry import parse_source

    project = _resolve_project(project_dir)
    parsed = parse_source(source)
    previous_entry = load_output_manifest(project).get(_normalize_source_ref(parsed))

    selected_role_ids = None
    if role is None and previous_entry is not None:
        previous_roles = {
            role_id
            for target_entry in previous_entry.get("targets", {}).values()
            for role_id in target_entry.get("selected_roles", [])
        }
        if previous_roles:
            selected_role_ids = sorted(previous_roles)

    bundle = _load_source_bundle(source, role_patterns=role, selected_role_ids=selected_role_ids)
    _show_agent_table(bundle.agents)
    _record_cached_source(bundle)

    target_names = _resolve_target_names(
        project,
        explicit_targets=target,
        previous_entry=previous_entry,
        source_config=bundle.config,
    )
    if not target_names:
        _success("Source fetched and validated. No target detected, so no files were generated.")
        _info(f"Use `role-forge add {source} --target <name>` to generate outputs later.")
        return

    target_outputs = _render_source(project, bundle, target_names, interactive=not yes)
    if not target_outputs:
        _warn("No files were generated.")
        return

    update_source_outputs(
        project,
        source_key=bundle.source_key,
        source=bundle.source_ref,
        targets=target_outputs,
    )
    _success(f"Updated source {bundle.source_key}")


@app.command("list")
def list_agents(
    sources: Annotated[
        bool,
        typer.Option("--sources", help="List cached sources instead of project-generated outputs"),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """List cached sources or project-generated outputs."""
    project = _resolve_project(project_dir)

    if sources:
        payload = _cached_sources_payload()
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
            return
        if not payload:
            _error("No cached sources found.")
            raise typer.Exit(1)

        _info("Cached sources")
        typer.echo(f"{'SOURCE':<35} {'COMMIT':<12} {'CACHE PATH'}")
        typer.echo(_dim("-" * 90))
        for entry in payload:
            typer.echo(
                f"{entry['source_key']:<35} "
                f"{entry.get('last_fetched_commit', '-')[:12]:<12} "
                f"{entry.get('cache_path', '-')}"
            )
        _success(f"{len(payload)} cached source(s)")
        return

    payload = _project_outputs_payload(project)
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if not payload:
        _error("No generated sources recorded in this project.")
        raise typer.Exit(1)

    _info("Project-generated sources")
    typer.echo(f"{'SOURCE':<35} {'TARGETS':<20} {'ROLES':<6} {'FILES':<6}")
    typer.echo(_dim("-" * 78))
    for entry in payload:
        typer.echo(
            f"{entry['source_key']:<35} "
            f"{', '.join(entry['targets']):<20} "
            f"{len(entry['role_ids']):<6} "
            f"{entry['file_count']:<6}"
        )
    _success(f"{len(payload)} source(s) recorded in this project")


@app.command()
def remove(
    source: Annotated[str, typer.Argument(help="Source to remove: org/repo[@ref] or local path")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Remove a source, clean generated outputs, and clear cached state."""
    from role_forge.outputs import (
        delete_recorded_files,
        load_output_manifest,
        remove_source_outputs,
    )
    from role_forge.registry import parse_source

    project = _resolve_project(project_dir)
    parsed = parse_source(source)
    source_key = _normalize_source_ref(parsed)

    entries = load_output_manifest(project)
    entry = entries.get(source_key)
    if entry is None and parsed.is_local:
        _error(f"Source not recorded in this project: {source_key}")
        raise typer.Exit(1)

    if not yes and not typer.confirm(
        f"Remove source {source_key} and clean generated outputs?", default=True
    ):
        _warn("Remove cancelled.")
        raise typer.Exit(1)

    deleted_count = 0
    if entry is not None:
        deleted_count = len(delete_recorded_files(project, entry))
        remaining_entries = remove_source_outputs(project, source_key)
    else:
        remaining_entries = entries

    if not parsed.is_local:
        _delete_cached_source(source_key)

    if remaining_entries:
        _rebuild_remaining_outputs(project, remaining_entries)

    _success(f"Removed source {source_key}")
    _info(f"Deleted {deleted_count} generated file(s).")


@app.command()
def update(
    source: Annotated[str, typer.Argument(help="GitHub source to refresh: org/repo[@ref]")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip overwrite prompts")] = False,
    target: Annotated[
        list[str] | None,
        typer.Option(
            "--target", "-t", help="Generate these targets (default: previous/source/auto)"
        ),
    ] = None,
    role: Annotated[
        list[str] | None,
        typer.Option("--role", "-r", help="Generate only roles matching (substring of name/id)"),
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Refresh a remote source and regenerate its outputs."""
    from role_forge.registry import parse_source

    parsed = parse_source(source)
    if parsed.is_local:
        _error("Cannot update a local source. Use 'add' again instead.")
        raise typer.Exit(1)

    add(
        source=source,
        yes=yes,
        target=target,
        role=role,
        project_dir=project_dir,
    )
