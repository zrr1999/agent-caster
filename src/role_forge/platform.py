"""Detect AI coding tools installed in a project."""

from __future__ import annotations

from pathlib import Path

# (marker_files_or_dirs, adapter_name)
_DETECTORS: list[tuple[list[str], str]] = [
    ([".claude", "CLAUDE.md"], "claude"),
    ([".opencode", "opencode.json"], "opencode"),
    ([".github/copilot-instructions.md", ".github/agents"], "copilot"),
    ([".cursor", ".cursorrules"], "cursor"),
    ([".windsurf", ".windsurfrules"], "windsurf"),
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


def resolve_targets(project_dir: Path) -> list[str]:
    """Determine which targets to render for a project.

    Priority:
    1. Enabled targets from ``roles.toml`` (if the file exists and has targets).
    2. Auto-detected platforms via filesystem markers.
    """
    from role_forge.config import find_config, load_config

    config_path = find_config(project_dir)
    if config_path is not None:
        project_config = load_config(config_path)
        configured = [name for name, cfg in project_config.targets.items() if cfg.enabled]
        if configured:
            return configured

    return detect_platforms(project_dir)
