"""Data models for agent-caster."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class ModelConfig(BaseModel, frozen=True):
    """Model configuration from agent frontmatter."""

    tier: Literal["reasoning", "coding"] = "reasoning"
    temperature: float | None = None


class AgentDef(BaseModel, frozen=True):
    """Parsed canonical agent definition.

    Capabilities are stored as raw data -- expansion is the adapter's job.
    """

    name: str
    description: str = ""
    role: Literal["primary", "subagent"] = "subagent"
    model: ModelConfig = ModelConfig()
    skills: list[str] = []
    capabilities: list[str | dict[str, Any]] = []
    prompt_content: str = ""
    prompt_file: str | None = None
    source_path: Path | None = None


class TargetConfig(BaseModel, frozen=True):
    """Per-target configuration from refit.toml."""

    name: str
    enabled: bool = True
    output_dir: str = "."
    model_map: dict[str, str] = {}
    capability_map: dict[str, dict[str, bool]] = {}


class ProjectConfig(BaseModel, frozen=True):
    """Full parsed refit.toml configuration."""

    agents_dir: str = ".agents/roles"
    targets: dict[str, TargetConfig] = {}


class OutputFile(BaseModel, frozen=True):
    """A file to be written by the caster."""

    path: str  # relative to output_dir
    content: str
