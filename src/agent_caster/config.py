"""roles.toml configuration parser."""

from __future__ import annotations

import tomllib
from pathlib import Path

from agent_caster.log import logger
from agent_caster.models import ProjectConfig, TargetConfig

#: Canonical config filename (since v0.2).
CONFIG_FILENAME = "roles.toml"
#: Legacy filename — still supported but triggers a deprecation warning.
LEGACY_CONFIG_FILENAME = "refit.toml"


class ConfigError(Exception):
    """Raised when roles.toml is invalid or missing."""


def find_config(project: Path) -> Path | None:
    """Return the config file path, preferring *roles.toml* over the legacy *refit.toml*.

    If *refit.toml* is found without *roles.toml*, a deprecation warning is logged and
    the caller should prompt the user to rename the file.
    """
    canonical = project / CONFIG_FILENAME
    if canonical.is_file():
        return canonical

    legacy = project / LEGACY_CONFIG_FILENAME
    if legacy.is_file():
        logger.warning(
            f"'{LEGACY_CONFIG_FILENAME}' is deprecated — please rename it to '{CONFIG_FILENAME}'. "
            "Support for the old name will be removed in a future release."
        )
        return legacy

    return None


def load_config(config_path: Path) -> ProjectConfig:
    """Parse roles.toml (or legacy refit.toml) and return ProjectConfig."""
    logger.debug(f"Loading config from {config_path}")
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    agents_dir = project.get("agents_dir", ".agents/roles")

    raw_targets = data.get("targets", {})
    targets = {}
    for name, raw in raw_targets.items():
        targets[name] = _parse_target(name, raw)

    return ProjectConfig(agents_dir=agents_dir, targets=targets)


def _parse_target(name: str, raw: dict) -> TargetConfig:
    """Parse a single [targets.<name>] section."""
    return TargetConfig(
        name=name,
        enabled=raw.get("enabled", True),
        output_dir=raw.get("output_dir", "."),
        output_layout=raw.get("output_layout", "preserve"),
        model_map=raw.get("model_map", {}),
        capability_map=raw.get("capability_map", {}),
    )
