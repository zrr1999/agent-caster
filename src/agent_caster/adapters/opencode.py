"""OpenCode adapter — generates .opencode/agents/*.md.

Migrated from precision-alignment-agent/adapters/opencode/generate.py.
"""

from __future__ import annotations

from agent_caster.groups import BASH_POLICIES, TOOL_GROUPS
from agent_caster.models import AgentDef, BaseAdapter, ModelConfig, OutputFile, TargetConfig
from agent_caster.topology import build_output_path, validate_agents, validate_output_layout


class OpenCodeAdapter(BaseAdapter):
    name = "opencode"

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
            path = build_output_path(
                agent, base_dir=".opencode/agents", suffix=".md", config=config
            )
            outputs.append(OutputFile(path=path, content=content))
        return outputs

    def _expand_capabilities(
        self,
        capabilities: list[str | dict],
        capability_map: dict[str, dict[str, bool]],
    ) -> tuple[dict[str, bool], list[str], list[str]]:
        """Expand raw capabilities into OpenCode tools, bash patterns, delegates.

        Bash policy groups (safe-bash, readonly-bash) and explicit ``bash: [...]``
        entries are **merged** — the final whitelist is the union of all patterns.
        """
        tools: dict[str, bool] = {}
        bash_allowed: list[str] = []
        delegates: list[str] = []

        for cap in capabilities:
            if isinstance(cap, str):
                # Bash policy group
                if cap in BASH_POLICIES:
                    bash_allowed.extend(BASH_POLICIES[cap])
                    tools["bash"] = True
                # Built-in tool group
                elif cap in TOOL_GROUPS:
                    for tool_id in TOOL_GROUPS[cap]:
                        tools[tool_id] = True
                # User-defined capability_map from refit.toml
                elif cap in capability_map:
                    tools.update(capability_map[cap])
                else:
                    # Pass through as-is — the platform may support it natively
                    tools[cap] = True
            elif isinstance(cap, dict):
                if "bash" in cap:
                    bash_allowed.extend(cap["bash"] or [])
                    tools["bash"] = True
                if "delegate" in cap:
                    delegates = cap["delegate"] or []
                    if delegates:
                        tools["task"] = True

        # Deduplicate bash patterns while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for p in bash_allowed:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        bash_allowed = deduped

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

    def _generate_agent_md(
        self, agent: AgentDef, config: TargetConfig, delegates: list[str]
    ) -> str:
        tools, bash_allowed, _ = self._expand_capabilities(
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
