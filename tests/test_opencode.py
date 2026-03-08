"""Tests for OpenCode adapter."""

from agent_caster.adapters.opencode import OpenCodeAdapter
from agent_caster.groups import SAFE_BASH_PATTERNS
from agent_caster.models import AgentDef, ModelConfig, TargetConfig


def test_cast_explorer(sample_explorer, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.cast([sample_explorer], opencode_config)
    assert len(outputs) == 1
    assert outputs[0].path == ".opencode/agents/explorer.md"
    assert outputs[0].content == snapshot


def test_cast_aligner_no_bash(sample_aligner, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.cast([sample_aligner], opencode_config)
    assert outputs[0].content == snapshot


def test_cast_orchestrator_with_delegates(sample_orchestrator, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.cast(
        [
            sample_orchestrator,
            AgentDef(name="explorer", description="Explorer"),
            AgentDef(name="aligner", description="Aligner"),
        ],
        opencode_config,
    )
    assert outputs[0].content == snapshot


def test_temperature_default_primary(opencode_config, snapshot):
    """Primary agent without explicit temp should default to 0.2."""
    agent = AgentDef(
        name="test",
        description="Test",
        role="primary",
        model=ModelConfig(tier="reasoning"),
    )
    adapter = OpenCodeAdapter()
    outputs = adapter.cast([agent], opencode_config)
    assert outputs[0].content == snapshot


def test_temperature_default_subagent(opencode_config, snapshot):
    """Subagent without explicit temp should default to 0.1."""
    agent = AgentDef(
        name="test",
        description="Test",
        role="subagent",
        model=ModelConfig(tier="coding"),
    )
    adapter = OpenCodeAdapter()
    outputs = adapter.cast([agent], opencode_config)
    assert outputs[0].content == snapshot


def test_cast_all_fixtures(fixtures_dir, opencode_config, snapshot):
    """Cast all fixture agents and verify output count and content."""
    from agent_caster.loader import load_agents

    agents = load_agents(fixtures_dir / ".agents" / "roles")
    adapter = OpenCodeAdapter()
    outputs = adapter.cast(agents, opencode_config)
    assert len(outputs) == 3
    contents = {o.path.split("/")[-1]: o.content for o in outputs}
    assert contents == snapshot


# -- Bash policy group tests ---------------------------------------------------


def test_safe_bash_expands_patterns(opencode_config):
    """safe-bash group should expand to SAFE_BASH_PATTERNS."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read", "safe-bash"],
    )
    adapter = OpenCodeAdapter()
    tools, bash_allowed, _ = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    )
    assert tools.get("bash") is True
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_allowed


def test_readonly_bash_is_superset_of_safe(opencode_config):
    """readonly-bash should contain all patterns from safe-bash plus extras."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["readonly-bash"],
    )
    adapter = OpenCodeAdapter()
    _, bash_allowed, _ = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    )
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_allowed
    assert len(bash_allowed) > len(SAFE_BASH_PATTERNS)


def test_bash_policy_merges_with_explicit_patterns(opencode_config):
    """safe-bash + explicit bash patterns should merge (union)."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=[
            "safe-bash",
            {"bash": ["npm test*", "cargo build*"]},
        ],
    )
    adapter = OpenCodeAdapter()
    _, bash_allowed, _ = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    )
    # Should contain safe-bash patterns
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_allowed
    # Plus explicit patterns
    assert "npm test*" in bash_allowed
    assert "cargo build*" in bash_allowed


def test_bash_policy_deduplicates(opencode_config):
    """Duplicate patterns across policy + explicit should be deduped."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=[
            "safe-bash",
            {"bash": ["echo *", "custom cmd*"]},  # "echo *" overlaps with safe-bash
        ],
    )
    adapter = OpenCodeAdapter()
    _, bash_allowed, _ = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    )
    assert bash_allowed.count("echo *") == 1
    assert "custom cmd*" in bash_allowed


def test_read_group_expands_tools(opencode_config):
    """'read' group should expand to read, glob, grep tools."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read"],
    )
    adapter = OpenCodeAdapter()
    tools, _, _ = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    assert tools == {"read": True, "glob": True, "grep": True}


def test_write_group_expands_tools(opencode_config):
    """'write' group should expand to write, edit tools."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["write"],
    )
    adapter = OpenCodeAdapter()
    tools, _, _ = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    assert tools == {"write": True, "edit": True}


def test_custom_tier_falls_back_to_reasoning(opencode_config):
    """An unknown custom tier should fall back to the 'reasoning' model map entry."""
    agent = AgentDef(
        name="deep-worker",
        description="Deep worker agent with custom tier.",
        role="primary",
        model=ModelConfig(tier="deep"),
    )
    adapter = OpenCodeAdapter()
    resolved = adapter._resolve_model(agent.model, opencode_config.model_map)
    assert resolved == opencode_config.model_map["reasoning"]


def test_custom_tier_overrides_if_in_model_map():
    """A custom tier explicitly listed in model_map should resolve to its value."""
    config = TargetConfig(
        name="opencode",
        model_map={
            "reasoning": "model-slow",
            "coding": "model-fast",
            "deep": "model-ultra",
        },
    )
    agent = AgentDef(
        name="refit",
        description="Meta-learning agent.",
        role="primary",
        model=ModelConfig(tier="deep"),
    )
    adapter = OpenCodeAdapter()
    resolved = adapter._resolve_model(agent.model, config.model_map)
    assert resolved == "model-ultra"


def test_cast_nested_agent_preserves_relative_path(opencode_config):
    agent = AgentDef(name="scout", description="Scout", relative_path="l2/scout.md")
    adapter = OpenCodeAdapter()
    outputs = adapter.cast([agent], opencode_config)
    assert outputs[0].path == ".opencode/agents/l2/scout.md"


def test_cast_namespace_layout_uses_namespaced_task_permissions() -> None:
    adapter = OpenCodeAdapter()
    config = TargetConfig(
        name="opencode",
        output_layout="namespace",
        model_map={"reasoning": "model-r", "coding": "model-c"},
    )
    agents = [
        AgentDef(
            name="orchestrator",
            description="Orchestrator",
            role="primary",
            relative_path="l1/orchestrator.md",
            capabilities=[{"delegate": ["worker"]}],
        ),
        AgentDef(name="worker", description="Worker", relative_path="l3/worker.md"),
    ]

    outputs = adapter.cast(agents, config)
    by_path = {output.path: output.content for output in outputs}
    assert ".opencode/agents/l1__orchestrator.md" in by_path
    assert '"l3__worker": allow' in by_path[".opencode/agents/l1__orchestrator.md"]
