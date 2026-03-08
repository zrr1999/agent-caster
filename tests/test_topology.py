"""Tests for shared role topology helpers."""

from __future__ import annotations

import importlib.util

import pytest

from role_forge.models import AgentDef, HierarchyConfig, ModelConfig, TargetConfig
from role_forge.topology import TopologyError, validate_agents, validate_output_layout

_HAS_PYTEST_CODSPEED = importlib.util.find_spec("pytest_codspeed") is not None


def _agent(
    name: str,
    *,
    level: int,
    delegates: list[str] | None = None,
) -> AgentDef:
    capabilities = []
    if delegates:
        capabilities.append({"delegate": delegates})

    return AgentDef(
        name=name,
        role="subagent",
        model=ModelConfig(tier="reasoning"),
        hierarchy=HierarchyConfig(level=level),
        capabilities=capabilities,
        prompt_content=f"# {name}\n",
        relative_path=f"team/{name}.md",
    )


def _balanced_tree_agents() -> list[AgentDef]:
    return [
        _agent("root", level=1, delegates=["branch-a", "branch-b", "branch-c"]),
        _agent("branch-a", level=2, delegates=["leaf-a1", "leaf-a2", "leaf-a3"]),
        _agent("branch-b", level=2, delegates=["leaf-b1", "leaf-b2", "leaf-b3"]),
        _agent("branch-c", level=2, delegates=["leaf-c1", "leaf-c2", "leaf-c3"]),
        _agent("leaf-a1", level=3),
        _agent("leaf-a2", level=3),
        _agent("leaf-a3", level=3),
        _agent("leaf-b1", level=3),
        _agent("leaf-b2", level=3),
        _agent("leaf-b3", level=3),
        _agent("leaf-c1", level=3),
        _agent("leaf-c2", level=3),
        _agent("leaf-c3", level=3),
    ]


def test_validate_agents_resolves_hierarchy_graph() -> None:
    agents = [
        AgentDef(
            name="orchestrator",
            relative_path="l1/orchestrator.md",
            hierarchy=HierarchyConfig.model_validate(
                {
                    "level": "L1",
                    "class": "main",
                    "scheduled": True,
                    "callable": True,
                    "max_delegate_depth": 2,
                    "allowed_children": ["l2/lead"],
                }
            ),
            capabilities=[{"delegate": ["lead"]}],
        ),
        AgentDef(
            name="lead",
            relative_path="l2/lead.md",
            hierarchy=HierarchyConfig.model_validate(
                {"level": "L2", "class": "lead", "max_delegate_depth": 1}
            ),
            capabilities=[{"delegate": ["l3/worker"]}],
        ),
        AgentDef(
            name="worker",
            relative_path="l3/worker.md",
            hierarchy=HierarchyConfig.model_validate(
                {"level": "L3", "class": "leaf", "max_delegate_depth": 0}
            ),
        ),
    ]

    graph = validate_agents(agents)
    assert [child.canonical_id for child in graph["l1/orchestrator"]] == ["l2/lead"]
    assert [child.canonical_id for child in graph["l2/lead"]] == ["l3/worker"]
    assert graph["l3/worker"] == []


def test_validate_agents_rejects_unknown_delegate() -> None:
    agent = AgentDef(
        name="lead",
        relative_path="l2/lead.md",
        hierarchy=HierarchyConfig(level="L2"),
        capabilities=[{"delegate": ["missing"]}],
    )

    with pytest.raises(TopologyError, match="Unknown role reference"):
        validate_agents([agent])


def test_validate_agents_rejects_upward_delegate() -> None:
    agents = [
        AgentDef(
            name="lead",
            relative_path="l2/lead.md",
            hierarchy=HierarchyConfig(level="L2"),
            capabilities=[{"delegate": ["l1/main"]}],
        ),
        AgentDef(
            name="main",
            relative_path="l1/main.md",
            hierarchy=HierarchyConfig(level="L1"),
        ),
    ]

    with pytest.raises(TopologyError, match="cannot delegate upward"):
        validate_agents(agents)


def test_validate_agents_rejects_cycles() -> None:
    agents = [
        AgentDef(
            name="a",
            relative_path="l1/a.md",
            capabilities=[{"delegate": ["l2/b"]}],
        ),
        AgentDef(
            name="b",
            relative_path="l2/b.md",
            capabilities=[{"delegate": ["l1/a"]}],
        ),
    ]

    with pytest.raises(TopologyError, match="Delegation cycle detected"):
        validate_agents(agents)


def test_validate_output_layout_rejects_flatten_collisions() -> None:
    agents = [
        AgentDef(name="worker", relative_path="l2/worker.md"),
        AgentDef(name="worker", relative_path="l3/worker.md"),
    ]
    config = TargetConfig(name="claude", output_layout="flatten")

    with pytest.raises(TopologyError, match="maps both"):
        validate_output_layout(agents, config)


def test_validate_agents_balanced_tree() -> None:
    graph = validate_agents(_balanced_tree_agents())

    assert len(graph["team/root"]) == 3
    assert len(graph["team/branch-a"]) == 3


if _HAS_PYTEST_CODSPEED:

    def test_validate_agents_balanced_tree_benchmark(benchmark) -> None:
        graph = benchmark(validate_agents, _balanced_tree_agents())

        assert len(graph["team/root"]) == 3
        assert len(graph["team/branch-a"]) == 3
