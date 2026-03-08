"""Claude Code adapter — generates .claude/agents/*.md."""

from __future__ import annotations

from typing import ClassVar

from role_forge.adapters.base import BaseAdapter
from role_forge.capabilities import CapabilitySpec, expand_capabilities
from role_forge.groups import ALL_TOOL_IDS
from role_forge.models import AgentDef, TargetConfig

# Semantic tool id -> Claude Code tool name
_TOOL_NAME_MAP: dict[str, str] = {
    "read": "Read",
    "glob": "Glob",
    "grep": "Grep",
    "write": "Write",
    "edit": "Edit",
    "bash": "Bash",
    "webfetch": "WebFetch",
    "websearch": "WebSearch",
    "task": "Task",
}

_ALL_CLAUDE_TOOLS: list[str] = sorted(
    {
        claude_name
        for tool_id in ALL_TOOL_IDS
        if (claude_name := _TOOL_NAME_MAP.get(tool_id)) and claude_name != "Bash"
    }
)


class ClaudeAdapter(BaseAdapter):
    name = "claude"
    base_dir = ".claude/agents"
    file_suffix = ".md"
    default_model_map: ClassVar[dict[str, str]] = {
        "reasoning": "claude-opus-4-6",
        "coding": "claude-sonnet-4",
    }

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> CapabilitySpec:
        return expand_capabilities(capabilities, capability_map)

    def _build_allowed_tools(
        self,
        tools: list[str],
        bash_patterns: list[str],
        delegates: list[str],
    ) -> list[str]:
        """Build the allowed_tools list for Claude Code frontmatter."""
        allowed: list[str] = []

        for tool in tools:
            if tool == "Bash":
                if not bash_patterns:
                    allowed.append(tool)
                continue  # handled via patterns below
            if tool == "Task" and delegates:
                continue  # handled via delegate-specific entries below
            allowed.append(tool)

        if bash_patterns:
            for pattern in bash_patterns:
                allowed.append(f"Bash({pattern})")

        for delegate in delegates:
            allowed.append(f"Task({delegate})")

        return sorted(allowed)

    def _serialize_frontmatter(
        self,
        name: str,
        description: str,
        model: str,
        tools: list[str],
    ) -> str:
        lines = ["---"]
        lines.append(f"name: {name}")
        lines.append(f"description: {description}")

        if tools:
            lines.append(f"tools: {', '.join(tools)}")

        lines.append(f"model: {model}")
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
        bash_patterns = list(spec.bash_patterns)

        name = agent.name
        description = agent.description
        model = self._resolve_model(agent.model, config.model_map)
        allowed_tools = self._build_allowed_tools(tools, bash_patterns, delegates)

        fm = self._serialize_frontmatter(name, description, model, allowed_tools)
        return self._compose_document(fm, agent.prompt_content)

    def _map_tool_ids(self, spec: CapabilitySpec) -> list[str]:
        tools: set[str] = set()
        for tool_id in spec.tool_ids:
            claude_name = _TOOL_NAME_MAP.get(tool_id)
            if claude_name:
                tools.add(claude_name)
                continue
            tools.add(tool_id)

        if spec.full_access:
            tools.update(_ALL_CLAUDE_TOOLS)
            tools.add("Bash")

        return sorted(tools)
