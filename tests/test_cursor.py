"""Tests for Cursor adapter."""

from role_forge.adapters.cursor import CursorAdapter
from role_forge.models import AgentDef, ModelConfig, TargetConfig

CURSOR_CONFIG = TargetConfig(
    name="cursor",
    enabled=True,
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


def test_output_path_uses_agent_name():
    agent = AgentDef(name="my-agent", description="Test")
    adapter = CursorAdapter()
    outputs = adapter.cast([agent], CURSOR_CONFIG)
    assert outputs[0].path == ".cursor/agents/my-agent.mdc"
