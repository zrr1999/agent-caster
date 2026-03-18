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
    default_output_layout: ClassVar[str] = "preserve"
    requires_model_map: ClassVar[bool] = True
    prompt_separator: ClassVar[str] = "\n"

    def _effective_config(self, config: TargetConfig) -> TargetConfig:
        """Apply adapter defaults to the target configuration.

        When the caller has not explicitly set ``output_layout`` (i.e. it is
        ``None``), the adapter's own ``default_output_layout`` takes
        precedence.
        """
        if config.output_layout is None:
            return config.model_copy(update={"output_layout": self.default_output_layout})
        return config

    def cast(self, agents: list[AgentDef], config: TargetConfig) -> list[OutputFile]:
        """Validate topology and render all agents for the target platform."""
        config = self._effective_config(config)
        delegation_graph = validate_agents(agents)
        validate_output_layout(agents, config)

        outputs: list[OutputFile] = []
        for agent in agents:
            delegates = [
                self._delegate_ref(target, config)
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

    def _delegate_ref(self, target: AgentDef, config: TargetConfig) -> str:
        """Build the delegate reference string for rendered output.

        Override in subclasses when the target platform resolves agents by
        name rather than by output path.
        """
        return target.output_id(config.output_layout)

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
