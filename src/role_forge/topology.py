"""Shared role topology helpers for layout and delegation validation."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import PurePosixPath

from role_forge.models import AgentDef, TargetConfig

_LEVEL_RE = re.compile(r"[Ll]?(\d+)$")


class TopologyError(ValueError):
    """Raised when role hierarchy or delegation metadata is invalid."""


def validate_agents(agents: list[AgentDef]) -> dict[str, list[AgentDef]]:
    """Validate role hierarchy/delegation metadata and return a resolved graph."""
    by_id = _build_id_index(agents)
    by_name = _build_name_index(agents)
    graph: dict[str, list[AgentDef]] = {}
    incoming: dict[str, list[AgentDef]] = defaultdict(list)

    for agent in agents:
        delegates = resolve_delegate_targets(agent, by_id=by_id, by_name=by_name)
        allowed_children = resolve_allowed_children(agent, by_id=by_id, by_name=by_name)
        _validate_agent_conflicts(agent, delegates, allowed_children)

        if allowed_children:
            allowed_ids = {child.canonical_id for child in allowed_children}
            for child in delegates:
                if child.canonical_id not in allowed_ids:
                    raise TopologyError(
                        f"Agent '{agent.canonical_id}' delegates to '{child.canonical_id}' "
                        "outside its allowed_children policy"
                    )

        for child in delegates:
            if not child.hierarchy.callable:
                raise TopologyError(
                    f"Agent '{agent.canonical_id}' delegates to non-callable role "
                    f"'{child.canonical_id}'"
                )
            if _is_upward_edge(agent, child):
                raise TopologyError(
                    f"Agent '{agent.canonical_id}' cannot delegate upward to '{child.canonical_id}'"
                )
            incoming[child.canonical_id].append(agent)

        graph[agent.canonical_id] = delegates

    _detect_cycles(graph)
    longest_paths = _longest_delegation_paths(graph)

    for agent in agents:
        if not agent.hierarchy.scheduled and not agent.hierarchy.callable:
            raise TopologyError(f"Agent '{agent.canonical_id}' is neither scheduled nor callable")

        if not agent.hierarchy.callable and incoming.get(agent.canonical_id):
            callers = ", ".join(parent.canonical_id for parent in incoming[agent.canonical_id])
            raise TopologyError(
                f"Agent '{agent.canonical_id}' is non-callable but is delegated to by {callers}"
            )

        max_depth = agent.hierarchy.max_delegate_depth
        if max_depth is not None and longest_paths[agent.canonical_id] > max_depth:
            raise TopologyError(
                f"Agent '{agent.canonical_id}' exceeds max_delegate_depth={max_depth}"
            )

    return graph


def validate_output_layout(agents: list[AgentDef], config: TargetConfig) -> None:
    """Ensure the selected output layout produces unique target identifiers."""
    seen: dict[str, str] = {}
    for agent in agents:
        output_id = agent.output_id(config.output_layout)
        existing = seen.get(output_id)
        if existing is not None:
            raise TopologyError(
                f"Output layout '{config.output_layout}' maps both '{existing}' and "
                f"'{agent.canonical_id}' to '{output_id}'"
            )
        seen[output_id] = agent.canonical_id


def resolve_delegate_targets(
    agent: AgentDef,
    *,
    by_id: dict[str, AgentDef],
    by_name: dict[str, list[AgentDef]],
) -> list[AgentDef]:
    """Resolve raw delegate references into concrete target agents."""
    return _resolve_refs(agent.declared_delegate_refs(), by_id=by_id, by_name=by_name)


def resolve_allowed_children(
    agent: AgentDef,
    *,
    by_id: dict[str, AgentDef],
    by_name: dict[str, list[AgentDef]],
) -> list[AgentDef]:
    """Resolve allowed_children into concrete target agents."""
    return _resolve_refs(agent.hierarchy.allowed_children, by_id=by_id, by_name=by_name)


def build_output_path(agent: AgentDef, *, base_dir: str, suffix: str, config: TargetConfig) -> str:
    """Return the target output path for an agent under the selected layout."""
    base_path = PurePosixPath(base_dir)
    if base_path.is_absolute() or ".." in base_path.parts:
        raise TopologyError(f"Output base directory '{base_dir}' escapes base directory bounds")

    output_id = agent.output_id(config.output_layout)
    if config.output_layout in ("preserve", None):
        return f"{base_dir}/{output_id}{suffix}"
    return f"{base_dir}/{PurePosixPath(output_id).name}{suffix}"


def _build_id_index(agents: list[AgentDef]) -> dict[str, AgentDef]:
    by_id: dict[str, AgentDef] = {}
    for agent in agents:
        existing = by_id.get(agent.canonical_id)
        if existing is not None:
            raise TopologyError(
                f"Duplicate canonical role id '{agent.canonical_id}' for "
                f"'{existing.name}' and '{agent.name}'"
            )
        by_id[agent.canonical_id] = agent
    return by_id


def _build_name_index(agents: list[AgentDef]) -> dict[str, list[AgentDef]]:
    by_name: dict[str, list[AgentDef]] = defaultdict(list)
    for agent in agents:
        by_name[agent.name].append(agent)
    return by_name


def _resolve_refs(
    refs: list[str],
    *,
    by_id: dict[str, AgentDef],
    by_name: dict[str, list[AgentDef]],
) -> list[AgentDef]:
    resolved: list[AgentDef] = []
    seen: set[str] = set()
    for ref in refs:
        target = _resolve_ref(ref, by_id=by_id, by_name=by_name)
        if target.canonical_id in seen:
            continue
        seen.add(target.canonical_id)
        resolved.append(target)
    return resolved


def _resolve_ref(
    ref: str,
    *,
    by_id: dict[str, AgentDef],
    by_name: dict[str, list[AgentDef]],
) -> AgentDef:
    normalized = str(PurePosixPath(ref.strip()).with_suffix(""))
    if normalized in by_id:
        return by_id[normalized]

    matches = by_name.get(normalized, [])
    if not matches:
        raise TopologyError(f"Unknown role reference '{ref}'")
    if len(matches) > 1:
        options = ", ".join(agent.canonical_id for agent in matches)
        raise TopologyError(f"Ambiguous role reference '{ref}'. Use one of: {options}")
    return matches[0]


def _validate_agent_conflicts(
    agent: AgentDef,
    delegates: list[AgentDef],
    allowed_children: list[AgentDef],
) -> None:
    if agent.hierarchy.role_class == "leaf" and (delegates or allowed_children):
        raise TopologyError(
            f"Leaf agent '{agent.canonical_id}' cannot declare delegates or allowed_children"
        )

    if agent.hierarchy.max_delegate_depth == 0 and delegates:
        raise TopologyError(
            f"Agent '{agent.canonical_id}' declares delegates but max_delegate_depth=0"
        )


def _is_upward_edge(parent: AgentDef, child: AgentDef) -> bool:
    parent_level = _parse_level(parent.hierarchy.level)
    child_level = _parse_level(child.hierarchy.level)
    if parent_level is None or child_level is None:
        return False
    return child_level <= parent_level


def _parse_level(level: str | int | None) -> int | None:
    if level is None:
        return None
    if isinstance(level, int):
        return level
    match = _LEVEL_RE.fullmatch(level.strip())
    if match:
        return int(match.group(1))
    return None


def _detect_cycles(graph: dict[str, list[AgentDef]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join([*trail, node])
            raise TopologyError(f"Delegation cycle detected: {cycle}")

        visiting.add(node)
        for child in graph.get(node, []):
            visit(child.canonical_id, [*trail, node])
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, [])


def _longest_delegation_paths(graph: dict[str, list[AgentDef]]) -> dict[str, int]:
    cache: dict[str, int] = {}

    def longest(node: str) -> int:
        if node in cache:
            return cache[node]
        children = graph.get(node, [])
        if not children:
            cache[node] = 0
            return 0
        depth = 1 + max(longest(child.canonical_id) for child in children)
        cache[node] = depth
        return depth

    return {node: longest(node) for node in graph}
