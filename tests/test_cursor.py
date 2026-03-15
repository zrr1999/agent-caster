"""Tests for Cursor adapter."""

from role_forge.adapters.cursor import CursorAdapter
from role_forge.models import AgentDef, ModelConfig, TargetConfig

CURSOR_CONFIG = TargetConfig(
    name="cursor",
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
        capabilities=["read", "write"],
        prompt_content="# Aligner",
    )
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    assert len(outputs) == 1
    assert outputs[0].path == ".cursor/agents/aligner.mdc"
    assert outputs[0].content == snapshot


def test_cast_explorer(snapshot):
    agent = AgentDef(
        name="explorer",
        description="Code Explorer. Reads and analyzes source code.",
        role="subagent",
        model=ModelConfig(tier="reasoning", temperature=0.05),
        skills=["repomix-explorer"],
        capabilities=[
            "read",
            "web-access",
            {"bash": ["npx repomix@latest*"]},
        ],
        prompt_content="# Explorer\n\nRead-only code exploration agent.",
    )
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    assert outputs[0].path == ".cursor/agents/explorer.mdc"
    assert outputs[0].content == snapshot


def test_cast_agent_without_prompt():
    """Agent without prompt_content should produce frontmatter only."""
    agent = AgentDef(
        name="minimal",
        description="Minimal agent.",
        prompt_content="",
    )
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    content = outputs[0].content
    assert content.endswith("---")


def test_cast_agent_without_description():
    """Agent with empty description should not emit description field."""
    agent = AgentDef(
        name="nodesc",
        description="",
        prompt_content="# No description",
    )
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    content = outputs[0].content
    assert "description:" not in content


def test_output_path_uses_agent_name():
    agent = AgentDef(name="my-agent", description="Test")
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    assert outputs[0].path == ".cursor/agents/my-agent.mdc"


def test_output_path_preserves_relative_role_path():
    agent = AgentDef(name="worker", description="Test", relative_path="l3/worker.md")
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    assert outputs[0].path == ".cursor/agents/l3/worker.mdc"


def test_model_map_ignored():
    """Cursor adapter ignores model_map — Cursor selects model globally."""
    config_with_model = TargetConfig(
        name="cursor",
        model_map={"reasoning": "gpt-5", "coding": "gpt-4"},
    )
    agent = AgentDef(name="test", description="Test", prompt_content="prompt")
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], config_with_model)
    assert "model:" not in outputs[0].content


def test_cast_multiple_agents():
    agents = [
        AgentDef(name="alpha", description="Alpha agent", prompt_content="# Alpha"),
        AgentDef(name="beta", description="Beta agent", prompt_content="# Beta"),
    ]
    adapter = CursorAdapter()
    outputs = adapter.cast(agents, CURSOR_CONFIG)
    assert len(outputs) == 2
    paths = {o.path for o in outputs}
    assert ".cursor/agents/alpha.mdc" in paths
    assert ".cursor/agents/beta.mdc" in paths
