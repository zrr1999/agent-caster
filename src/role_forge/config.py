"""roles.toml configuration parser."""

from __future__ import annotations

import tomllib
from pathlib import Path

from loguru import logger

from role_forge.models import ProjectConfig, TargetConfig

CONFIG_FILENAME = "roles.toml"
USER_ROLES_DIR = Path.home() / ".agents" / "roles"


class ConfigError(Exception):
    """Raised when roles.toml is invalid or missing."""


def resolve_roles_dir(project: Path) -> Path:
    """Return the canonical roles directory for a project."""
    config_path = find_config(project)
    if config_path is None:
        return project / ".agents" / "roles"
    return project / load_config(config_path).roles_dir


def find_config(project: Path) -> Path | None:
    """Return the canonical project config file path."""
    canonical = project / CONFIG_FILENAME
    if canonical.is_file():
        return canonical
    return None


def load_config(config_path: Path) -> ProjectConfig:
    """Parse roles.toml and return ProjectConfig."""
    logger.debug(f"Loading config from {config_path}")
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    roles_dir = project.get("roles_dir", ".agents/roles")

    raw_targets = data.get("targets", {})
    targets = {}
    for name, raw in raw_targets.items():
        targets[name] = _parse_target(name, raw)

    return ProjectConfig(roles_dir=roles_dir, targets=targets)


def _parse_target(name: str, raw: dict) -> TargetConfig:
    """Parse a single [targets.<name>] section."""
    return TargetConfig(
        name=name,
        enabled=raw.get("enabled", True),
        output_dir=raw.get("output_dir", "."),
        output_layout=raw.get("output_layout"),
        model_map=raw.get("model_map", {}),
        capability_map=raw.get("capability_map", {}),
    )
