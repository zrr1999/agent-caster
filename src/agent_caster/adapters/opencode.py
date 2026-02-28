"""OpenCode adapter — generates .opencode/agents/*.md.

Migrated from precision-alignment-agent/adapters/opencode/generate.py.
"""

from __future__ import annotations

from agent_caster.log import logger
from agent_caster.models import AgentDef, ModelConfig, OutputFile, TargetConfig

# Built-in capability groups (default, overridable via capability_map)
BUILTIN_CAPABILITY_GROUPS: dict[str, dict[str, bool]] = {
    "read-code": {"read": True, "glob": True, "grep": True},
    "write-code": {"write": True, "edit": True},
    "write-report": {"write": True},
    "web-access": {"webfetch": True, "websearch": True},
    "web-read": {"webfetch": True},
}


class OpenCodeAdapter:
    name: str = "opencode"

    def compile(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]:
        outputs = []
        for agent in agents:
            content = self._generate_agent_md(agent, config)
            path = f".opencode/agents/{agent.name}.md"
            outputs.append(OutputFile(path=path, content=content))
        return outputs

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> tuple[dict[str, bool], list[str], list[str]]:
        """Expand raw capabilities into OpenCode tools, bash patterns, delegates."""
        all_groups = {**BUILTIN_CAPABILITY_GROUPS, **capability_map}

        tools: dict[str, bool] = {}
        bash_allowed: list[str] = []
        delegates: list[str] = []

        for cap in capabilities:
            if isinstance(cap, str):
                if cap in all_groups:
                    tools.update(all_groups[cap])
                else:
                    logger.warning(f"Unknown capability group: {cap!r}")
            elif isinstance(cap, dict):
                if "bash" in cap:
                    bash_allowed = cap["bash"] or []
                    tools["bash"] = bool(bash_allowed)
                if "delegate" in cap:
                    delegates = cap["delegate"] or []
                    if delegates:
                        tools["task"] = True

        return {k: v for k, v in tools.items() if v}, bash_allowed, delegates

    def _resolve_model(self, model: ModelConfig, model_map: dict[str, str]) -> str:
        default = model_map.get("reasoning", "")
        return model_map.get(model.tier, default)

    def _resolve_temperature(self, model: ModelConfig, role: str) -> float:
        if model.temperature is not None:
            return model.temperature
        return 0.2 if role == "primary" else 0.1

    def _build_permissions(
        self,
        bash_allowed: list[str],
        delegates: list[str],
        tools: dict[str, bool],
        role: str,
    ) -> dict:
        perm: dict = {}

        if bash_allowed:
            perm["bash"] = {"*": "deny"}
            for pattern in bash_allowed:
                perm["bash"][pattern] = "allow"

        if delegates:
            perm["task"] = {"*": "deny"}
            for d in delegates:
                perm["task"][d] = "allow"

        if tools.get("edit"):
            perm["edit"] = "allow"
        if tools.get("write"):
            perm["write"] = "allow"

        if role == "primary":
            perm["question"] = "allow"
        return perm

    def _serialize_frontmatter(
        self,
        description: str,
        mode: str,
        model: str,
        temperature: float,
        skills: list[str],
        tools: dict[str, bool],
        permission: dict,
    ) -> str:
        """Custom YAML serializer matching OpenCode's expected format."""
        lines = ["---"]
        lines.append(f"description: {description}")
        lines.append(f"mode: {mode}")
        lines.append(f"model: {model}")
        lines.append(f"temperature: {temperature}")

        if skills:
            lines.append("skills:")
            for s in skills:
                lines.append(f"  - {s}")

        if tools:
            lines.append("tools:")
            for k, v in tools.items():
                lines.append(f'  "{k}": {str(v).lower()}')

        if permission:
            lines.append("permission:")
            for section, val in permission.items():
                if isinstance(val, dict):
                    lines.append(f'  "{section}":')
                    for pk, pv in val.items():
                        lines.append(f'    "{pk}": {pv}')
                else:
                    lines.append(f'  "{section}": {val}')

        lines.append("---")
        return "\n".join(lines)

    def _generate_agent_md(self, agent: AgentDef, config: TargetConfig) -> str:
        tools, bash_allowed, delegates = self._expand_capabilities(
            agent.capabilities, config.capability_map
        )

        description = agent.description
        mode = agent.role
        model = self._resolve_model(agent.model, config.model_map)
        temperature = self._resolve_temperature(agent.model, agent.role)
        skills = [s for s in agent.skills if s]
        permission = self._build_permissions(bash_allowed, delegates, tools, agent.role)

        fm = self._serialize_frontmatter(
            description, mode, model, temperature, skills, tools, permission
        )
        prompt = agent.prompt_content
        return f"{fm}\n\n{prompt}" if prompt else fm
