"""Copilot adapter — generates .github/agents/*.md.

GitHub Copilot supports custom agents stored in ``.github/agents/``.  Each
file is a Markdown document with an optional YAML frontmatter block.

Copilot agent frontmatter format::

    ---
    description: <natural-language description shown in the agent picker>
    model: <model-id>
    tools:
      - read
      - edit
      - execute
    ---
    <agent system prompt>

Agent definitions are mapped to Copilot agents as follows:

* Each agent becomes one ``.github/agents/<name>.md`` file.
* The agent's ``description`` is used in the frontmatter.
* ``model`` is resolved via the target's ``model_map`` in ``roles.toml``.
* ``tools`` are derived from the agent's ``capabilities`` and mapped to
  Copilot tool aliases (``read``, ``edit``, ``search``, ``execute``,
  ``web``, ``agent``).
* ``prompt_content`` becomes the system prompt body.

Copilot tool alias mapping (from semantic tool ids)::

    read      → read
    glob      → search
    grep      → search
    write     → edit
    edit      → edit
    bash      → execute
    webfetch  → web
    websearch → web
    task      → agent
"""

from __future__ import annotations

from typing import ClassVar

from role_forge.adapters.base import BaseAdapter, _yaml_quote
from role_forge.capabilities import CapabilitySpec, expand_capabilities
from role_forge.groups import ALL_TOOL_IDS
from role_forge.models import AgentDef, TargetConfig

# Semantic tool id → Copilot tool alias
_TOOL_NAME_MAP: dict[str, str] = {
    "read": "read",
    "glob": "search",
    "grep": "search",
    "write": "edit",
    "edit": "edit",
    "bash": "execute",
    "webfetch": "web",
    "websearch": "web",
    "task": "agent",
}

_ALL_COPILOT_TOOLS: list[str] = sorted(
    {alias for tool_id in ALL_TOOL_IDS if (alias := _TOOL_NAME_MAP.get(tool_id))}
)


class CopilotAdapter(BaseAdapter):
    name = "copilot"
    base_dir = ".github/agents"
    file_suffix = ".md"
    default_output_layout = "namespace"
    default_model_map: ClassVar[dict[str, str]] = {
        "reasoning": "claude-sonnet-4-5",
        "coding": "claude-sonnet-4",
    }

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> CapabilitySpec:
        return expand_capabilities(capabilities, capability_map)

    def _map_tool_ids(self, spec: CapabilitySpec) -> list[str]:
        """Map expanded semantic tool ids to Copilot tool aliases."""
        tools: set[str] = set()
        for tool_id in spec.tool_ids:
            alias = _TOOL_NAME_MAP.get(tool_id)
            if alias:
                tools.add(alias)
                continue
            tools.add(tool_id)

        if spec.full_access:
            tools.update(_ALL_COPILOT_TOOLS)

        return sorted(tools)

    def _serialize_frontmatter(
        self,
        description: str,
        model: str,
        tools: list[str],
    ) -> str:
        """Emit Copilot agent frontmatter."""
        lines = ["---"]
        if description:
            lines.append(f"description: {_yaml_quote(description)}")
        if model:
            lines.append(f"model: {model}")
        if tools:
            lines.append("tools:")
            for tool in tools:
                lines.append(f"  - {tool}")
        lines.append("---")
        return "\n".join(lines)

    def render_agent(
        self,
        agent: AgentDef,
        config: TargetConfig,
        delegates: list[str],
    ) -> str:
        spec = self._expand_capabilities(agent.capabilities, config.capability_map)
        tools = self._map_tool_ids(spec)
        model = self._resolve_model(agent.model, config.model_map)

        fm = self._serialize_frontmatter(agent.description, model, tools)
        return self._compose_document(fm, agent.prompt_content)
