"""Manifest tracking which source installed which role files for prune on update."""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST_FILENAME = ".role-forge-manifest.json"


def _manifest_path(roles_dir: Path) -> Path:
    return roles_dir / MANIFEST_FILENAME


def load_manifest(roles_dir: Path) -> dict[str, list[str]]:
    """Load manifest from roles_dir. Returns {source_key: [relative_path, ...]}."""
    path = _manifest_path(roles_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        result: dict[str, list[str]] = {}
        for k, v in data.items():
            if isinstance(v, list):
                result[str(k)] = [str(p) for p in v]
        return result
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(roles_dir: Path, manifest: dict[str, list[str]]) -> None:
    """Write manifest to roles_dir."""
    path = _manifest_path(roles_dir)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def paths_for_source(manifest: dict[str, list[str]], source_key: str) -> list[str]:
    """Return paths previously installed by this source."""
    return list(manifest.get(source_key, []))


def update_manifest_for_source(
    roles_dir: Path,
    source_key: str,
    installed_paths: list[str],
) -> None:
    """Update manifest: set source_key -> installed_paths, persist."""
    manifest = load_manifest(roles_dir)
    manifest[source_key] = sorted(installed_paths)
    save_manifest(roles_dir, manifest)


def prune_orphaned(
    roles_dir: Path,
    source_key: str,
    current_paths: set[str],
) -> list[Path]:
    """Remove files that were installed by source but no longer in current_paths.

    Returns list of paths that were deleted. Caller must update manifest after copy.
    """
    manifest = load_manifest(roles_dir)
    previous = set(paths_for_source(manifest, source_key))
    orphaned = previous - current_paths
    deleted: list[Path] = []
    for rel in orphaned:
        path = roles_dir / rel
        if path.is_file():
            path.unlink()
            deleted.append(path)
    return deleted


def remove_path_from_manifest(roles_dir: Path, relative_path: str) -> None:
    """Remove a path from all manifest entries (e.g. after manual remove)."""
    manifest = load_manifest(roles_dir)
    changed = False
    for key in list(manifest.keys()):
        if relative_path in manifest[key]:
            manifest[key] = [p for p in manifest[key] if p != relative_path]
            changed = True
            if not manifest[key]:
                del manifest[key]
    if changed:
        save_manifest(roles_dir, manifest)
