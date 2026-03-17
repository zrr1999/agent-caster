"""Tests for Claude Code adapter."""

from role_forge.adapters.claude import ClaudeAdapter
from role_forge.capabilities import CapabilitySpec
from role_forge.groups import SAFE_BASH_PATTERNS
from role_forge.models import AgentDef, TargetConfig


def test_cast_aligner(sample_aligner, claude_config, snapshot):
    adapter = ClaudeAdapter()
    outputs = adapter.cast([sample_aligner], claude_config)
    assert len(outputs) == 1
    assert outputs[0].path == ".claude/agents/aligner.md"
    assert outputs[0].content == snapshot


def test_cast_explorer_with_bash(sample_explorer, claude_config, snapshot):
    """Explorer has 'context7' which is not in claude's capability_map — silently skipped."""
    adapter = ClaudeAdapter()
    outputs = adapter.cast([sample_explorer], claude_config)
    assert outputs[0].content == snapshot


def test_cast_orchestrator_with_delegates(sample_orchestrator, claude_config, snapshot):
    adapter = ClaudeAdapter()
    outputs = adapter.cast(
        [
            sample_orchestrator,
            AgentDef(name="explorer", description="Explorer"),
            AgentDef(name="aligner", description="Aligner"),
        ],
        claude_config,
    )
    assert outputs[0].content == snapshot


# -- Bash policy group tests ---------------------------------------------------


def test_safe_bash_expands_to_bash_patterns(claude_config):
    """safe-bash should generate Bash(...) entries in allowed_tools."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read", "safe-bash"],
    )
    adapter = ClaudeAdapter()
    outputs = adapter.cast([agent], claude_config)
    content = outputs[0].content
    # Should contain Bash(...) entries for safe patterns
    assert "Bash(echo*)" in content
    assert "Bash(git log*)" in content


def test_bash_capability_renders_unrestricted_bash(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["bash"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    assert spec.tool_ids == ("bash",)
    assert spec.bash_patterns == ()

    outputs = adapter.cast([agent], claude_config)
    assert "tools: Bash" in outputs[0].content


def test_bash_policy_merge_with_explicit(claude_config):
    """safe-bash + explicit bash: [...] should merge."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=[
            "safe-bash",
            {"bash": ["npm test*", "cargo build*"]},
        ],
    )
    adapter = ClaudeAdapter()
    bash_patterns = adapter._expand_capabilities(
        agent.capabilities, claude_config.capability_map
    ).bash_patterns
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_patterns
    assert "npm test*" in bash_patterns
    assert "cargo build*" in bash_patterns


def test_read_group_maps_to_claude_tools(claude_config):
    """'read' group should map to Read, Glob, Grep."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"Glob", "Grep", "Read"}


def test_basic_group_maps_to_claude_tools(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["basic"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"Edit", "Glob", "Grep", "Read", "WebFetch", "WebSearch", "Write"}


def test_empty_capabilities_default_to_basic(claude_config):
    agent = AgentDef(name="test", description="Test", capabilities=[])
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"Edit", "Glob", "Grep", "Read", "WebFetch", "WebSearch", "Write"}


def test_delegate_group_maps_to_task_tool(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["delegate"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"Task"}
    assert spec.delegates == ()


def test_web_access_group_maps_to_claude_tools(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["web-access"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"WebFetch", "WebSearch"}


def test_all_capability_maps_to_all_claude_tools(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["all"],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    tools = adapter._map_tool_ids(spec)
    bash_patterns = spec.bash_patterns
    delegates = spec.delegates
    assert set(tools) == {
        "Bash",
        "Edit",
        "Glob",
        "Grep",
        "Read",
        "Task",
        "WebFetch",
        "WebSearch",
        "Write",
    }
    assert bash_patterns == ()
    assert delegates == ()


def test_expand_capabilities_returns_canonical_spec(claude_config):
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["read", {"bash": ["git diff*"]}, {"delegate": ["worker"]}],
    )
    adapter = ClaudeAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    assert spec == CapabilitySpec(
        tool_ids=("read", "glob", "grep", "bash", "task"),
        bash_patterns=("git diff*",),
        delegates=("worker",),
        full_access=False,
    )


def test_cast_nested_agent_preserves_relative_path(claude_config):
    agent = AgentDef(name="scout", description="Scout", relative_path="l2/scout.md")
    adapter = ClaudeAdapter()
    outputs = adapter.cast([agent], claude_config)
    assert outputs[0].path == ".claude/agents/l2/scout.md"


def test_cast_namespace_layout_uses_name_based_delegate_ids() -> None:
    """Claude resolves Task() by agent name, regardless of output layout."""
    adapter = ClaudeAdapter()
    config = TargetConfig(
        name="claude",
        output_layout="namespace",
        model_map={"reasoning": "opus", "coding": "sonnet"},
    )
    agents = [
        AgentDef(
            name="orchestrator",
            description="Orchestrator",
            role="primary",
            relative_path="l1/orchestrator.md",
            capabilities=[{"delegate": ["worker"]}],
        ),
        AgentDef(
            name="worker",
            description="Worker",
            relative_path="l3/worker.md",
        ),
    ]

    outputs = adapter.cast(agents, config)
    by_path = {output.path: output.content for output in outputs}
    assert ".claude/agents/l1__orchestrator.md" in by_path
    assert "Task(worker)" in by_path[".claude/agents/l1__orchestrator.md"]


def test_cast_preserve_layout_uses_name_based_delegate_ids() -> None:
    """Claude resolves Task() by agent name even with nested file paths."""
    adapter = ClaudeAdapter()
    config = TargetConfig(
        name="claude",
        output_layout="preserve",
        model_map={"reasoning": "opus", "coding": "sonnet"},
    )
    agents = [
        AgentDef(
            name="coordinator",
            description="Coordinator",
            role="primary",
            relative_path="directors/coordinator.md",
            capabilities=[{"delegate": ["directors/precision-alignment"]}],
        ),
        AgentDef(
            name="precision-alignment",
            description="Aligner",
            relative_path="directors/precision-alignment.md",
        ),
    ]

    outputs = adapter.cast(agents, config)
    by_path = {output.path: output.content for output in outputs}
    assert ".claude/agents/directors/coordinator.md" in by_path
    content = by_path[".claude/agents/directors/coordinator.md"]
    assert "Task(precision-alignment)" in content
    # Must NOT contain path-based reference
    assert "Task(directors/precision-alignment)" not in content
