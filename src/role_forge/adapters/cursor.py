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
  via the prompt body or post-process the generated file if needed.
"""

from __future__ import annotations

from typing import ClassVar

from role_forge.adapters.base import BaseAdapter
from role_forge.models import AgentDef, TargetConfig


class CursorAdapter(BaseAdapter):
    name: ClassVar[str] = "cursor"
    base_dir = ".cursor/agents"
    file_suffix = ".mdc"
    requires_model_map = False
    # Cursor doesn't support per-agent model selection; default_model_map stays empty

    def _serialize_frontmatter(self, name: str, description: str) -> str:
        """Emit minimal Cursor MDC frontmatter."""
        lines = ["---"]
        lines.append(f"name: {name}")
        if description:
            lines.append(f"description: {description}")
        lines.append("---")
        return "\n".join(lines)

    def render_agent(
        self,
        agent: AgentDef,
        config: TargetConfig,
        delegates: list[str],
    ) -> str:
        del config, delegates
        fm = self._serialize_frontmatter(agent.name, agent.description)
        return self._compose_document(fm, agent.prompt_content)
