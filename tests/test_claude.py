"""Tests for Claude Code adapter."""

from agent_caster.adapters.claude import ClaudeAdapter


def test_cast_aligner(sample_aligner, claude_config, snapshot):
    adapter = ClaudeAdapter()
    outputs = adapter.cast([sample_aligner], claude_config)
    assert len(outputs) == 1
    assert outputs[0].path == ".claude/agents/aligner.md"
    assert outputs[0].content == snapshot


def test_cast_explorer_with_bash(sample_explorer, claude_config, snapshot, capsys):
    """Explorer has 'context7' which is not in claude's capability_map — expect a warning."""
    adapter = ClaudeAdapter()
    outputs = adapter.cast([sample_explorer], claude_config)
    assert outputs[0].content == snapshot
    captured = capsys.readouterr()
    assert "context7" in captured.out


def test_cast_orchestrator_with_delegates(sample_orchestrator, claude_config, snapshot):
    adapter = ClaudeAdapter()
    outputs = adapter.cast([sample_orchestrator], claude_config)
    assert outputs[0].content == snapshot
