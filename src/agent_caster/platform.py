"""Detect AI coding tools installed in a project."""

from __future__ import annotations

from pathlib import Path

# (marker_files_or_dirs, adapter_name)
_DETECTORS: list[tuple[list[str], str]] = [
    ([".claude", "CLAUDE.md"], "claude"),
    ([".opencode", "opencode.json"], "opencode"),
]


def detect_platforms(project_dir: Path) -> list[str]:
    """Detect AI coding tool platforms present in project_dir.

    Returns list of adapter names (e.g. ["claude", "opencode"]).
    """
    found: list[str] = []
    for markers, name in _DETECTORS:
        if any((project_dir / m).exists() for m in markers):
            found.append(name)
    return found
