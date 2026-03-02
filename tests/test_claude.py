"""Tests for Claude Code adapter."""

from agent_caster.adapters.claude import ClaudeAdapter
from agent_caster.groups import SAFE_BASH_PATTERNS
from agent_caster.models import AgentDef


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
    outputs = adapter.cast([sample_orchestrator], claude_config)
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


def test_readonly_bash_superset(claude_config):
    """readonly-bash should include safe-bash patterns plus read-only extras."""
    agent = AgentDef(
        name="test",
        description="Test",
        capabilities=["readonly-bash"],
    )
    adapter = ClaudeAdapter()
    _, bash_patterns, _ = adapter._expand_capabilities(
        agent.capabilities, claude_config.capability_map
    )
    for p in SAFE_BASH_PATTERNS:
        assert p in bash_patterns
    assert "cat*" in bash_patterns
    assert "find*" in bash_patterns


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
    _, bash_patterns, _ = adapter._expand_capabilities(
        agent.capabilities, claude_config.capability_map
    )
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
    tools, _, _ = adapter._expand_capabilities(agent.capabilities, claude_config.capability_map)
    assert set(tools) == {"Glob", "Grep", "Read"}


def test_default_model_map():
    adapter = ClaudeAdapter()
    assert "reasoning" in adapter.default_model_map
    assert "coding" in adapter.default_model_map
