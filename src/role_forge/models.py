"""Data models for role-forge."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel, frozen=True):
    """Model configuration from agent frontmatter.

    ``tier`` maps to an entry in the target's ``model_map`` inside
    ``refit.toml``.  Built-in values are ``"reasoning"`` and ``"coding"``,
    but any custom string is accepted so that projects can define their own
    tier vocabulary (e.g. ``"deep"``, ``"lite"``, ``"refit"``).  Unknown
    tiers fall back to the ``"reasoning"`` mapping at cast time.
    """

    tier: str = "reasoning"
    temperature: float | None = None


class HierarchyConfig(BaseModel, frozen=True):
    """Optional first-class hierarchy metadata for a role."""

    model_config = ConfigDict(populate_by_name=True)

    level: str | int | None = None
    role_class: str | None = Field(default=None, alias="class")
    scheduled: bool = False
    callable: bool = True
    max_delegate_depth: int | None = Field(default=None, ge=0)
    allowed_children: list[str] = Field(default_factory=list)


class AgentDef(BaseModel, frozen=True):
    """Parsed canonical agent definition.

    Capabilities are stored as raw data. Empty capability lists default to `basic`
    during centralized expansion.
    """

    name: str
    description: str = ""
    role: Literal["primary", "subagent", "all"] = "subagent"
    model: ModelConfig = ModelConfig()
    skills: list[str] = Field(default_factory=list)
    capabilities: list[str | dict[str, Any]] = Field(default_factory=list)
    hierarchy: HierarchyConfig = Field(default_factory=HierarchyConfig)
    prompt_content: str = ""
    prompt_file: str | None = None
    source_path: Path | None = None
    relative_path: str | None = None

    @property
    def canonical_id(self) -> str:
        """Stable role id derived from relative source path when available."""
        if self.relative_path:
            return str(PurePosixPath(self.relative_path).with_suffix(""))
        if self.source_path is not None:
            return self.source_path.stem
        return self.name

    @property
    def namespace(self) -> str:
        """Directory portion of the canonical id, if any."""
        canonical_path = PurePosixPath(self.canonical_id)
        return (
            canonical_path.parent.as_posix() if canonical_path.parent != PurePosixPath(".") else ""
        )

    def output_id(self, layout: Literal["preserve", "namespace", "flatten"]) -> str:
        """Target identifier used for output names and delegate references."""
        if layout == "flatten":
            return self.name
        if layout == "namespace":
            return self.canonical_id.replace("/", "__")
        return self.canonical_id

    def install_relative_path(self) -> str:
        """Canonical install path beneath `.agents/roles`."""
        if self.relative_path:
            return self.relative_path
        return f"{self.name}.md"

    def declared_delegate_refs(self) -> list[str]:
        """Return raw delegate references declared in capabilities."""
        delegates: list[str] = []
        seen: set[str] = set()
        for capability in self.capabilities:
            if not isinstance(capability, dict) or "delegate" not in capability:
                continue
            for ref in capability.get("delegate") or []:
                if ref and ref not in seen:
                    seen.add(ref)
                    delegates.append(ref)
        return delegates


class TargetConfig(BaseModel, frozen=True):
    """Per-target configuration from roles.toml."""

    name: str
    enabled: bool = True
    output_dir: str = "."
    output_layout: Literal["preserve", "namespace", "flatten"] = "preserve"
    model_map: dict[str, str] = Field(default_factory=dict)
    capability_map: dict[str, dict[str, bool]] = Field(default_factory=dict)


class ProjectConfig(BaseModel, frozen=True):
    """Full parsed roles.toml configuration."""

    model_config = ConfigDict(populate_by_name=True)

    roles_dir: str = Field(default=".agents/roles", alias="roles_dir")
    targets: dict[str, TargetConfig] = Field(default_factory=dict)

    @property
    def agents_dir(self) -> str:
        """Backward-compatible alias for legacy config terminology."""
        return self.roles_dir


class OutputFile(BaseModel, frozen=True):
    """A file to be written by the caster."""

    path: str  # relative to output_dir
    content: str
