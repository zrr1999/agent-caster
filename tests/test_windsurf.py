"""Tests for Windsurf adapter."""

from role_forge.adapters.windsurf import WindsurfAdapter
from role_forge.models import AgentDef, ModelConfig, TargetConfig

WINDSURF_CONFIG = TargetConfig(
    name="windsurf",
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
            "read",
            "web-access",
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
