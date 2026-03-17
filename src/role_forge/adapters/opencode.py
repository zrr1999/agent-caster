"""OpenCode adapter — generates .opencode/agents/*.md.

Migrated from precision-alignment-agent/adapters/opencode/generate.py.
"""

from __future__ import annotations

from role_forge.adapters.base import BaseAdapter
from role_forge.capabilities import CapabilitySpec, expand_capabilities
from role_forge.models import AgentDef, TargetConfig


class OpenCodeAdapter(BaseAdapter):
    name = "opencode"
    base_dir = ".opencode/agents"
    file_suffix = ".md"
    prompt_separator = "\n\n"

    def _delegate_ref(self, target: AgentDef, config: TargetConfig) -> str:
        """OpenCode resolves task permissions by the agent's name."""
        return target.name

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> CapabilitySpec:
        return expand_capabilities(capabilities, capability_map)

    def _resolve_temperature(self, agent: AgentDef) -> float:
        model = agent.model
        if model.temperature is not None:
            return model.temperature
        return 0.2 if agent.role == "primary" else 0.1

    def _build_permissions(
        self,
        bash_allowed: list[str],
        delegates: list[str],
        tools: dict[str, bool],
        role: str,
        *,
        full_access: bool = False,
    ) -> dict:
        if full_access:
            return {
                "bash": "allow",
                "task": "allow",
                "edit": "allow",
                "write": "allow",
                "read": "allow",
                "glob": "allow",
                "grep": "allow",
                "webfetch": "allow",
                "websearch": "allow",
                "question": "allow",
            }

        perm: dict = {}

        if bash_allowed:
            perm["bash"] = {"*": "deny"}
            for pattern in bash_allowed:
                perm["bash"][pattern] = "allow"

        if delegates:
            perm["task"] = {"*": "deny"}
            for d in delegates:
                perm["task"][d] = "allow"
        elif tools.get("task"):
            perm["task"] = "allow"

        if tools.get("bash") and not bash_allowed:
            perm["bash"] = "allow"

        if tools.get("edit"):
            perm["edit"] = "allow"
        if tools.get("write"):
            perm["write"] = "allow"

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

    def render_agent(
        self,
        agent: AgentDef,
        config: TargetConfig,
        delegates: list[str],
    ) -> str:
        spec = self._expand_capabilities(agent.capabilities, config.capability_map)
        tools = spec.tool_flags()
        bash_allowed = list(spec.bash_patterns)

        description = agent.description
        mode = agent.role
        model = self._resolve_model(agent.model, config.model_map)
        temperature = self._resolve_temperature(agent)
        skills = [s for s in agent.skills if s]
        permission = self._build_permissions(
            bash_allowed,
            delegates,
            tools,
            agent.role,
            full_access=spec.full_access,
        )

        fm = self._serialize_frontmatter(
            description, mode, model, temperature, skills, tools, permission
        )
        return self._compose_document(fm, agent.prompt_content)
