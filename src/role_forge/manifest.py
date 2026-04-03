"""Global cache manifest for fetched source repositories."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from role_forge.registry import CACHE_ROOT

MANIFEST_FILENAME = "manifest.json"


def manifest_path(root: Path | None = None) -> Path:
    """Return the global cache manifest path."""
    base = root or CACHE_ROOT
    return base / MANIFEST_FILENAME


def _normalize_manifest(data: Any) -> dict[str, dict[str, str]]:
    if not isinstance(data, dict):
        return {}

    raw_sources = data.get("sources", data)
    if not isinstance(raw_sources, dict):
        return {}

    normalized: dict[str, dict[str, str]] = {}
    for source_key, raw_entry in raw_sources.items():
        if not isinstance(raw_entry, dict):
            continue

        entry: dict[str, str] = {}
        for field in ("cache_key", "cache_path", "last_fetched_commit"):
            value = raw_entry.get(field)
            if isinstance(value, str) and value:
                entry[field] = value

        if entry:
            normalized[str(source_key)] = entry

    return normalized


def load_manifest(root: Path | None = None) -> dict[str, dict[str, str]]:
    """Load the global cache manifest."""
    path = manifest_path(root)
    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    return _normalize_manifest(data)


def save_manifest(manifest: dict[str, dict[str, str]], root: Path | None = None) -> None:
    """Write the global cache manifest."""
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "sources": _normalize_manifest(manifest)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def update_source(
    source_key: str,
    *,
    cache_key: str,
    cache_path: Path,
    last_fetched_commit: str,
    root: Path | None = None,
) -> None:
    """Upsert one cached source entry."""
    manifest = load_manifest(root)
    manifest[source_key] = {
        "cache_key": cache_key,
        "cache_path": str(cache_path),
        "last_fetched_commit": last_fetched_commit,
    }
    save_manifest(manifest, root)


def remove_source(source_key: str, root: Path | None = None) -> None:
    """Delete one cached source entry."""
    manifest = load_manifest(root)
    if source_key not in manifest:
        return
    del manifest[source_key]
    save_manifest(manifest, root)


def source_entry(source_key: str, root: Path | None = None) -> dict[str, str] | None:
    """Return one cached source entry."""
    return load_manifest(root).get(source_key)
