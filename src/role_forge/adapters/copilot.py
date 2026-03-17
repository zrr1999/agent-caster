"""Copilot adapter — generates .github/agents/*.md.

GitHub Copilot supports custom agents stored in ``.github/agents/``.  Each
file is a Markdown document with an optional YAML frontmatter block.

Copilot agent frontmatter format::

    ---
    description: <natural-language description shown in the agent picker>
    ---
    <agent system prompt>

Agent definitions are mapped to Copilot agents as follows:

* Each agent becomes one ``.github/agents/<name>.md`` file.
* The agent's ``description`` is used in the frontmatter.
* ``prompt_content`` becomes the system prompt body.

Notes:

* Copilot does not support per-agent model selection in agent files; the
  model is chosen by the user in the Copilot UI, so ``model_map`` is
  ignored.
* Copilot's built-in tools are always available; fine-grained
  ``capabilities`` are not expressed in the output file.  Include
  capability requirements in the agent's system-prompt body if needed.
"""

from __future__ import annotations

from role_forge.adapters.base import BaseAdapter
from role_forge.models import AgentDef, TargetConfig


class CopilotAdapter(BaseAdapter):
    name = "copilot"
    base_dir = ".github/agents"
    file_suffix = ".md"
    requires_model_map = False

    def _serialize_frontmatter(self, description: str) -> str:
        """Emit Copilot agent frontmatter."""
        lines = ["---"]
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
        fm = self._serialize_frontmatter(agent.description)
        return self._compose_document(fm, agent.prompt_content)
