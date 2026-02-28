"""Cast pipeline — loads config + agents, dispatches to adapters."""

from __future__ import annotations

from pathlib import Path

from agent_caster.adapters import get_adapter
from agent_caster.config import find_config, load_config
from agent_caster.loader import load_agents
from agent_caster.log import logger
from agent_caster.models import OutputFile, ProjectConfig


class CastResult:
    """Result of a cast run."""

    def __init__(self) -> None:
        self.outputs: dict[str, list[OutputFile]] = {}

    @property
    def total_files(self) -> int:
        return sum(len(files) for files in self.outputs.values())


def cast_agents(
    project_root: Path | None = None,
    targets: list[str] | None = None,
) -> tuple[CastResult, ProjectConfig, Path]:
    """Run the full cast pipeline.

    Returns (result, config, project_root).
    """
    if project_root is None:
        config_path = find_config()
        project_root = config_path.parent
    else:
        project_root = project_root.resolve()
        config_path = project_root / "refit.toml"

    config = load_config(config_path)
    agents_dir = project_root / config.agents_dir
    agents = load_agents(agents_dir)

    if targets:
        active_targets = {name: cfg for name, cfg in config.targets.items() if name in targets}
        missing = set(targets) - set(active_targets)
        if missing:
            raise ValueError(f"Unknown targets: {missing}")
    else:
        active_targets = {name: cfg for name, cfg in config.targets.items() if cfg.enabled}

    result = CastResult()
    for target_name, target_config in active_targets.items():
        adapter = get_adapter(target_name)
        logger.debug(f"Casting target: {target_name}")
        outputs = adapter.cast(agents, target_config)
        result.outputs[target_name] = outputs

    logger.debug(f"Cast complete: {result.total_files} file(s) generated")
    return result, config, project_root


def write_outputs(
    result: CastResult,
    project_root: Path,
    config: ProjectConfig,
) -> list[Path]:
    """Write CastResult to disk. Returns list of paths written."""
    written: list[Path] = []
    for target_name, files in result.outputs.items():
        target_config = config.targets[target_name]
        output_base = project_root / target_config.output_dir
        for output_file in files:
            full_path = output_base / output_file.path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(output_file.content, encoding="utf-8")
            logger.debug(f"Wrote {full_path}")
            written.append(full_path)
    return written
