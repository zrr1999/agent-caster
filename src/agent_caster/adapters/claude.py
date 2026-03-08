"""Claude Code adapter — generates .claude/agents/*.md."""

from __future__ import annotations

from typing import ClassVar

from agent_caster.groups import BASH_POLICIES, TOOL_GROUPS
from agent_caster.models import AgentDef, BaseAdapter, ModelConfig, OutputFile, TargetConfig
from agent_caster.topology import build_output_path, validate_agents, validate_output_layout

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


class ClaudeAdapter(BaseAdapter):
    name = "claude"
    default_model_map: ClassVar[dict[str, str]] = {
        "reasoning": "claude-opus-4-6",
        "coding": "claude-sonnet-4",
    }

    def cast(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]:
        delegation_graph = validate_agents(agents)
        validate_output_layout(agents, config)

        outputs = []
        for agent in agents:
            delegates = [
                target.output_id(config.output_layout)
                for target in delegation_graph.get(agent.canonical_id, [])
            ]
            content = self._generate_agent_md(agent, config, delegates)
            path = build_output_path(agent, base_dir=".claude/agents", suffix=".md", config=config)
            outputs.append(OutputFile(path=path, content=content))
        return outputs

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> tuple[list[str], list[str], list[str]]:
        """Expand raw capabilities into Claude tool names, bash patterns, delegates.

        Bash policy groups (safe-bash, readonly-bash) and explicit ``bash: [...]``
        entries are **merged** — the final whitelist is the union of all patterns.
        """
        tools: set[str] = set()
        bash_patterns: list[str] = []
        delegates: list[str] = []

        for cap in capabilities:
            if isinstance(cap, str):
                # Bash policy group
                if cap in BASH_POLICIES:
                    bash_patterns.extend(BASH_POLICIES[cap])
                # Built-in tool group
                elif cap in TOOL_GROUPS:
                    for tool_id in TOOL_GROUPS[cap]:
                        claude_name = _TOOL_NAME_MAP.get(tool_id)
                        if claude_name:
                            tools.add(claude_name)
                # User-defined capability_map from refit.toml
                elif cap in capability_map:
                    for flag in capability_map[cap]:
                        claude_name = _TOOL_NAME_MAP.get(flag)
                        if claude_name:
                            tools.add(claude_name)
                else:
                    # Pass through as-is — the platform may support it natively
                    tools.add(cap)
            elif isinstance(cap, dict):
                if "bash" in cap:
                    bash_patterns.extend(cap["bash"] or [])
                if "delegate" in cap:
                    delegates = cap["delegate"] or []

        # Deduplicate bash patterns while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for p in bash_patterns:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        bash_patterns = deduped

        return sorted(tools), bash_patterns, delegates

    def _resolve_model(self, model: ModelConfig, model_map: dict[str, str]) -> str:
        default = model_map.get("reasoning", "")
        return model_map.get(model.tier, default)

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
                continue  # handled via patterns below
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

    def _generate_agent_md(
        self, agent: AgentDef, config: TargetConfig, delegates: list[str]
    ) -> str:
        tools, bash_patterns, _ = self._expand_capabilities(
            agent.capabilities, config.capability_map
        )

        name = agent.name
        description = agent.description
        model = self._resolve_model(agent.model, config.model_map)
        allowed_tools = self._build_allowed_tools(tools, bash_patterns, delegates)

        fm = self._serialize_frontmatter(name, description, model, allowed_tools)
        prompt = agent.prompt_content
        return f"{fm}\n{prompt}" if prompt else fm
