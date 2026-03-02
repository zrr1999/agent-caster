"""Adapter protocol for platform-specific casting."""

from __future__ import annotations

from typing import Protocol

from agent_caster.models import AgentDef, OutputFile, TargetConfig


class Adapter(Protocol):
    """Protocol that all platform adapters must implement."""

    name: str
    default_model_map: dict[str, str]

    def cast(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]: ...
