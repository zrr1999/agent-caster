"""Tests for OpenCode adapter."""

from role_forge.adapters.opencode import OpenCodeAdapter
from role_forge.capabilities import CapabilitySpec
from role_forge.groups import SAFE_BASH_PATTERNS
from role_forge.models import AgentDef, ModelConfig, TargetConfig


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
    from role_forge.loader import load_agents

    agents = load_agents(fixtures_dir / ".agents" / "roles")
    adapter = OpenCodeAdapter()
    outputs = adapter.cast(agents, opencode_config)
    assert len(outputs) == 8
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
    spec = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    tools = spec.tool_flags()
    bash_allowed = spec.bash_patterns
    assert tools.get("bash") is True
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_allowed


def test_bash_capability_grants_unrestricted_bash(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["bash"],
    )
    adapter = OpenCodeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    assert spec.tool_flags() == {"bash": True}
    assert spec.bash_patterns == ()

    outputs = adapter.cast([agent], opencode_config)
    content = outputs[0].content
    assert '"bash": true' in content
    assert '"bash": allow' in content


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
    bash_allowed = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).bash_patterns
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
    bash_allowed = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).bash_patterns
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
    tools = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).tool_flags()
    assert tools == {"read": True, "glob": True, "grep": True}


def test_write_group_expands_tools(opencode_config):
    """'write' group should expand to write, edit tools."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["write"],
    )
    adapter = OpenCodeAdapter()
    tools = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).tool_flags()
    assert tools == {"write": True, "edit": True}


def test_basic_group_expands_tools(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["basic"],
    )
    adapter = OpenCodeAdapter()
    tools = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).tool_flags()
    assert tools == {
        "read": True,
        "glob": True,
        "grep": True,
        "write": True,
        "edit": True,
        "webfetch": True,
        "websearch": True,
    }


def test_empty_capabilities_default_to_basic(opencode_config):
    agent = AgentDef(name="test", description="Test", capabilities=[])
    adapter = OpenCodeAdapter()
    tools = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).tool_flags()
    assert tools == {
        "read": True,
        "glob": True,
        "grep": True,
        "write": True,
        "edit": True,
        "webfetch": True,
        "websearch": True,
    }


def test_delegate_group_enables_task(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["delegate"],
    )
    adapter = OpenCodeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    assert spec.tool_flags() == {"task": True}
    assert spec.delegates == ()


def test_web_access_group_expands_tools(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["web-access"],
    )
    adapter = OpenCodeAdapter()
    tools = adapter._expand_capabilities(
        agent.capabilities, opencode_config.capability_map
    ).tool_flags()
    assert tools == {"webfetch": True, "websearch": True}


def test_all_capability_expands_all_tools(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["all"],
    )
    adapter = OpenCodeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    tools = spec.tool_flags()
    bash_allowed = spec.bash_patterns
    delegates = spec.delegates
    assert tools == {
        "read": True,
        "glob": True,
        "grep": True,
        "write": True,
        "edit": True,
        "webfetch": True,
        "websearch": True,
        "bash": True,
        "task": True,
    }
    assert bash_allowed == ()
    assert delegates == ()


def test_expand_capabilities_returns_canonical_spec(opencode_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read", {"bash": ["git diff*"]}, {"delegate": ["worker"]}],
    )
    adapter = OpenCodeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, opencode_config.capability_map)
    assert spec == CapabilitySpec(
        tool_ids=("read", "glob", "grep", "bash", "task"),
        bash_patterns=("git diff*",),
        delegates=("worker",),
        full_access=False,
    )


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
