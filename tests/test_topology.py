"""Tests for shared role topology helpers."""

from __future__ import annotations

import pytest

from agent_caster.models import AgentDef, HierarchyConfig, TargetConfig
from agent_caster.topology import TopologyError, validate_agents, validate_output_layout


def test_validate_agents_resolves_hierarchy_graph() -> None:
    agents = [
        AgentDef(
            name="orchestrator",
            relative_path="l1/orchestrator.md",
            hierarchy=HierarchyConfig(
                level="L1",
                role_class="main",
                scheduled=True,
                callable=True,
                max_delegate_depth=2,
                allowed_children=["l2/lead"],
            ),
            capabilities=[{"delegate": ["lead"]}],
        ),
        AgentDef(
            name="lead",
            relative_path="l2/lead.md",
            hierarchy=HierarchyConfig(level="L2", role_class="lead", max_delegate_depth=1),
            capabilities=[{"delegate": ["l3/worker"]}],
        ),
        AgentDef(
            name="worker",
            relative_path="l3/worker.md",
            hierarchy=HierarchyConfig(level="L3", role_class="leaf", max_delegate_depth=0),
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
