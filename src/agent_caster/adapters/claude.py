"""Claude Code adapter — generates .claude/agents/*.md."""

from __future__ import annotations

from agent_caster.log import logger
from agent_caster.models import AgentDef, ModelConfig, OutputFile, TargetConfig

# Built-in capability groups mapped to Claude Code tool names
BUILTIN_CAPABILITY_GROUPS: dict[str, list[str]] = {
    "read-code": ["Read", "Glob", "Grep"],
    "write-code": ["Write", "Edit"],
    "write-report": ["Write"],
    "web-access": ["WebFetch", "WebSearch"],
    "web-read": ["WebFetch"],
}

# OpenCode-style tool flags -> Claude tool names (for capability_map interpretation)
_TOOL_FLAG_MAP: dict[str, str] = {
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


class ClaudeAdapter:
    name: str = "claude"

    def compile(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]:
        outputs = []
        for agent in agents:
            content = self._generate_agent_md(agent, config)
            path = f".claude/agents/{agent.name}.md"
            outputs.append(OutputFile(path=path, content=content))
        return outputs

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> tuple[list[str], list[str], list[str]]:
        """Expand raw capabilities into Claude tool names, bash patterns, delegates."""
        tools: set[str] = set()
        bash_patterns: list[str] = []
        delegates: list[str] = []

        for cap in capabilities:
            if isinstance(cap, str):
                if cap in BUILTIN_CAPABILITY_GROUPS:
                    tools.update(BUILTIN_CAPABILITY_GROUPS[cap])
                elif cap in capability_map:
                    for flag in capability_map[cap]:
                        claude_name = _TOOL_FLAG_MAP.get(flag)
                        if claude_name:
                            tools.add(claude_name)
                else:
                    logger.warning(f"Unknown capability group for claude adapter: {cap!r}")
            elif isinstance(cap, dict):
                if "bash" in cap:
                    bash_patterns = cap["bash"] or []
                if "delegate" in cap:
                    delegates = cap["delegate"] or []

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
        description: str,
        model: str,
        allowed_tools: list[str],
    ) -> str:
        lines = ["---"]
        lines.append(f"description: {description}")
        lines.append(f"model: {model}")

        if allowed_tools:
            lines.append("allowed_tools:")
            for tool in allowed_tools:
                lines.append(f"  - {tool}")

        lines.append("---")
        return "\n".join(lines)

    def _generate_agent_md(self, agent: AgentDef, config: TargetConfig) -> str:
        tools, bash_patterns, delegates = self._expand_capabilities(
            agent.capabilities, config.capability_map
        )

        description = agent.description
        model = self._resolve_model(agent.model, config.model_map)
        allowed_tools = self._build_allowed_tools(tools, bash_patterns, delegates)

        fm = self._serialize_frontmatter(description, model, allowed_tools)
        prompt = agent.prompt_content
        return f"{fm}\n\n{prompt}" if prompt else fm
