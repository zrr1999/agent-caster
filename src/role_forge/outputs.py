"""Project-local generated output ownership manifest."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from role_forge.config import resolve_output_manifest_path


def _normalize_target_entry(raw_entry: Any) -> dict[str, list[str]] | None:
    if not isinstance(raw_entry, dict):
        return None

    files = raw_entry.get("files", [])
    selected_roles = raw_entry.get("selected_roles", [])
    if not isinstance(files, list) or not isinstance(selected_roles, list):
        return None

    normalized = {
        "files": [str(path) for path in files if isinstance(path, str)],
        "selected_roles": [str(role) for role in selected_roles if isinstance(role, str)],
    }
    if not normalized["files"]:
        return None
    return normalized


def _normalize_targets(raw_targets: Any) -> dict[str, dict[str, list[str]]]:
    if not isinstance(raw_targets, dict):
        return {}

    normalized: dict[str, dict[str, list[str]]] = {}
    for target_name, raw_entry in raw_targets.items():
        entry = _normalize_target_entry(raw_entry)
        if entry is not None:
            normalized[str(target_name)] = entry
    return normalized


def _normalize_sources(raw_sources: Any) -> OrderedDict[str, dict[str, Any]]:
    normalized: OrderedDict[str, dict[str, Any]] = OrderedDict()
    if not isinstance(raw_sources, dict):
        return normalized

    for source_key, raw_entry in raw_sources.items():
        if not isinstance(raw_entry, dict):
            continue

        source = raw_entry.get("source")
        targets = _normalize_targets(raw_entry.get("targets", {}))
        if not isinstance(source, str) or not source or not targets:
            continue

        normalized[str(source_key)] = {
            "source": source,
            "targets": targets,
        }

    return normalized


def load_output_manifest(project: Path) -> OrderedDict[str, dict[str, Any]]:
    """Load the project-local output manifest."""
    path = resolve_output_manifest_path(project)
    if not path.is_file():
        return OrderedDict()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return OrderedDict()

    raw_sources = data.get("sources", data)
    return _normalize_sources(raw_sources)


def save_output_manifest(project: Path, sources: OrderedDict[str, dict[str, Any]]) -> None:
    """Persist the project-local output manifest."""
    path = resolve_output_manifest_path(project)
    if not sources:
        if path.exists():
            path.unlink()
        _prune_empty_dirs(path.parent, project)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "sources": _normalize_sources(sources)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def update_source_outputs(
    project: Path,
    *,
    source_key: str,
    source: str,
    targets: dict[str, dict[str, list[str]]],
) -> OrderedDict[str, dict[str, Any]]:
    """Upsert one source entry and move it to the end for precedence."""
    sources = load_output_manifest(project)
    existing_targets = {}
    if source_key in sources:
        existing_targets = dict(sources[source_key].get("targets", {}))
        del sources[source_key]

    merged_targets = dict(existing_targets)
    merged_targets.update(targets)
    sources[source_key] = {
        "source": source,
        "targets": {
            target_name: {
                "selected_roles": list(entry["selected_roles"]),
                "files": sorted(entry["files"]),
            }
            for target_name, entry in merged_targets.items()
        },
    }
    save_output_manifest(project, sources)
    return sources


def remove_source_outputs(project: Path, source_key: str) -> OrderedDict[str, dict[str, Any]]:
    """Remove one source entry from the project output manifest."""
    sources = load_output_manifest(project)
    if source_key in sources:
        del sources[source_key]
    save_output_manifest(project, sources)
    return sources


def recorded_files(entry: dict[str, Any]) -> list[str]:
    """Return all recorded output files for one source entry."""
    targets = entry.get("targets", {})
    files: list[str] = []
    for target_entry in targets.values():
        files.extend(str(path) for path in target_entry.get("files", []))
    return files


def delete_recorded_files(project: Path, entry: dict[str, Any]) -> list[Path]:
    """Delete files recorded for one source entry and prune empty directories."""
    deleted: list[Path] = []
    for relative_path in recorded_files(entry):
        path = project / relative_path
        if path.is_file():
            path.unlink()
            deleted.append(path)
            _prune_empty_dirs(path.parent, project)
    return deleted


def _prune_empty_dirs(path: Path, project: Path) -> None:
    current = path
    project_root = project.resolve()
    while current.exists() and current.is_dir():
        if current.resolve() == project_root:
            return
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
