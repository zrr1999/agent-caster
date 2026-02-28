"""Tests for OpenCode adapter."""

from agent_caster.adapters.opencode import OpenCodeAdapter
from agent_caster.models import AgentDef, ModelConfig


def test_compile_explorer(sample_explorer, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.compile([sample_explorer], opencode_config)
    assert len(outputs) == 1
    assert outputs[0].path == ".opencode/agents/explorer.md"
    assert outputs[0].content == snapshot


def test_compile_aligner_no_bash(sample_aligner, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.compile([sample_aligner], opencode_config)
    assert outputs[0].content == snapshot


def test_compile_orchestrator_with_delegates(sample_orchestrator, opencode_config, snapshot):
    adapter = OpenCodeAdapter()
    outputs = adapter.compile([sample_orchestrator], opencode_config)
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
    outputs = adapter.compile([agent], opencode_config)
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
    outputs = adapter.compile([agent], opencode_config)
    assert outputs[0].content == snapshot


def test_compile_all_fixtures(fixtures_dir, opencode_config, snapshot):
    """Compile all fixture agents and verify output count and content."""
    from agent_caster.loader import load_agents

    agents = load_agents(fixtures_dir / ".agents" / "roles")
    adapter = OpenCodeAdapter()
    outputs = adapter.compile(agents, opencode_config)
    assert len(outputs) == 3
    contents = {o.path.split("/")[-1]: o.content for o in outputs}
    assert contents == snapshot
