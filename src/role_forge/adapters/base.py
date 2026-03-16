"""Shared adapter base class and casting helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from role_forge.models import AgentDef, ModelConfig, OutputFile, TargetConfig
from role_forge.topology import build_output_path, validate_agents, validate_output_layout


class BaseAdapter(ABC):
    """Base class for platform adapters."""

    name: ClassVar[str]
    base_dir: ClassVar[str]
    file_suffix: ClassVar[str]
    default_model_map: ClassVar[dict[str, str]] = {}
    requires_model_map: ClassVar[bool] = True
    prompt_separator: ClassVar[str] = "\n"

    def cast(self, agents: list[AgentDef], config: TargetConfig) -> list[OutputFile]:
        """Validate topology and render all agents for the target platform."""
        delegation_graph = validate_agents(agents)
        validate_output_layout(agents, config)

        outputs: list[OutputFile] = []
        for agent in agents:
            delegates = [
                target.output_id(config.output_layout)
                for target in delegation_graph.get(agent.canonical_id, [])
            ]
            outputs.append(
                OutputFile(
                    path=build_output_path(
                        agent,
                        base_dir=self.base_dir,
                        suffix=self.file_suffix,
                        config=config,
                    ),
                    content=self.render_agent(agent, config, delegates),
                )
            )
        return outputs

    @staticmethod
    def _resolve_model(model: ModelConfig, model_map: dict[str, str]) -> str:
        default = model_map.get("reasoning", "")
        return model_map.get(model.tier, default)

    def _compose_document(self, frontmatter: str, prompt: str) -> str:
        if not prompt:
            return frontmatter
        return f"{frontmatter}{self.prompt_separator}{prompt}"

    @abstractmethod
    def render_agent(
        self,
        agent: AgentDef,
        config: TargetConfig,
        delegates: list[str],
    ) -> str: ...


Adapter = BaseAdapter
