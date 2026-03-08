"""Tests for Windsurf adapter."""

from agent_caster.adapters.windsurf import WindsurfAdapter
from agent_caster.models import AgentDef, ModelConfig, TargetConfig

WINDSURF_CONFIG = TargetConfig(
    name="windsurf",
    enabled=True,
    output_dir=".",
    model_map={},
    capability_map={},
)


def test_cast_aligner(snapshot):
    agent = AgentDef(
        name="aligner",
        description="Precision Aligner. Makes targeted code changes.",
        role="subagent",
        model=ModelConfig(tier="coding", temperature=0.1),
        capabilities=["read-code", "write-code"],
        prompt_content="# Aligner",
    )
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    assert len(outputs) == 1
    assert outputs[0].path == ".windsurf/rules/aligner.md"
    assert outputs[0].content == snapshot


def test_cast_explorer(snapshot):
    agent = AgentDef(
        name="explorer",
        description="Code Explorer. Reads and analyzes source code.",
        role="subagent",
        model=ModelConfig(tier="reasoning", temperature=0.05),
        skills=["repomix-explorer"],
        capabilities=[
            "read-code",
            "web-read",
            {"bash": ["npx repomix@latest*"]},
        ],
        prompt_content="# Explorer\n\nRead-only code exploration agent.",
    )
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    assert outputs[0].path == ".windsurf/rules/explorer.md"
    assert outputs[0].content == snapshot


def test_output_path_uses_agent_name():
    agent = AgentDef(name="my-agent", description="Test")
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    assert outputs[0].path == ".windsurf/rules/my-agent.md"


def test_output_path_preserves_relative_role_path():
    agent = AgentDef(name="worker", description="Test", relative_path="l3/worker.md")
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    assert outputs[0].path == ".windsurf/rules/l3/worker.md"


def test_default_trigger_is_model_decision():
    """Default activation trigger should be model_decision."""
    agent = AgentDef(
        name="test-agent",
        description="Test agent.",
        prompt_content="# Test",
    )
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    content = outputs[0].content
    assert "trigger: model_decision" in content
    assert "description: Test agent." in content


def test_cast_agent_without_prompt():
    """Agent without prompt_content should produce frontmatter only."""
    agent = AgentDef(
        name="minimal",
        description="Minimal agent.",
        prompt_content="",
    )
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    content = outputs[0].content
    assert "trigger: model_decision" in content
    assert content.endswith("---")


def test_cast_agent_without_description():
    """Agent with empty description should omit description field."""
    agent = AgentDef(
        name="nodesc",
        description="",
        prompt_content="# No description",
    )
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], WINDSURF_CONFIG)
    content = outputs[0].content
    assert "description:" not in content
    assert "trigger: model_decision" in content


def test_model_map_ignored():
    """Windsurf adapter ignores model_map — Windsurf selects model globally."""
    config_with_model = TargetConfig(
        name="windsurf",
        model_map={"reasoning": "gpt-5", "coding": "gpt-4"},
    )
    agent = AgentDef(name="test", description="Test", prompt_content="prompt")
    adapter = WindsurfAdapter()
    outputs = adapter.cast([agent], config_with_model)
    # model info should NOT appear in the output
    assert "model:" not in outputs[0].content
    assert "gpt-5" not in outputs[0].content


def test_default_model_map_is_empty():
    adapter = WindsurfAdapter()
    assert adapter.default_model_map == {}


def test_cast_multiple_agents():
    agents = [
        AgentDef(name="alpha", description="Alpha agent", prompt_content="# Alpha"),
        AgentDef(name="beta", description="Beta agent", prompt_content="# Beta"),
    ]
    adapter = WindsurfAdapter()
    outputs = adapter.cast(agents, WINDSURF_CONFIG)
    assert len(outputs) == 2
    paths = {o.path for o in outputs}
    assert ".windsurf/rules/alpha.md" in paths
    assert ".windsurf/rules/beta.md" in paths
