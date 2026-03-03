"""Cursor adapter — generates .cursor/agents/*.mdc.

Cursor uses MDC (Markdown Component) files with a minimal YAML frontmatter.
Agent files live in `.cursor/agents/` and are loaded as project agents.

Cursor MDC format:
  ---
  name: <display name>
  description: <short description shown in UI>
  ---
  <system prompt body>

Notes:
- Cursor does not support per-agent model selection in agent files; the
  model is chosen globally in Cursor settings, so `model_map` is ignored.
- Cursor's built-in tools (read, write, terminal, web, search) are always
  available to agents; fine-grained `capabilities` are not expressed in the
  output file. The agent system prompt should describe what the agent is
  allowed to do instead.
- The `alwaysApply` frontmatter key (bool) is omitted by default; add it
  via the prompt body or a custom refit.toml override if needed.
"""

from __future__ import annotations

from agent_caster.models import AgentDef, OutputFile, TargetConfig

DEFAULT_MODEL_MAP: dict[str, str] = {}  # Cursor doesn't support per-agent model


class CursorAdapter:
    name: str = "cursor"
    default_model_map: dict[str, str] = DEFAULT_MODEL_MAP

    def cast(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]:
        outputs = []
        for agent in agents:
            content = self._generate_agent_mdc(agent)
            path = f".cursor/agents/{agent.name}.mdc"
            outputs.append(OutputFile(path=path, content=content))
        return outputs

    def _serialize_frontmatter(self, name: str, description: str) -> str:
        """Emit minimal Cursor MDC frontmatter."""
        lines = ["---"]
        lines.append(f"name: {name}")
        if description:
            lines.append(f"description: {description}")
        lines.append("---")
        return "\n".join(lines)

    def _generate_agent_mdc(self, agent: AgentDef) -> str:
        fm = self._serialize_frontmatter(agent.name, agent.description)
        prompt = agent.prompt_content
        return f"{fm}\n{prompt}" if prompt else fm
