"""Tests for Copilot adapter."""

from role_forge.adapters.copilot import CopilotAdapter
from role_forge.models import AgentDef, ModelConfig, TargetConfig

COPILOT_CONFIG = TargetConfig(
    name="copilot",
    enabled=True,
    model_map={"reasoning": "claude-sonnet-4-5", "coding": "gpt-4o"},
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
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert len(outputs) == 1
    assert outputs[0].path == ".github/agents/aligner.md"
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
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert outputs[0].path == ".github/agents/explorer.md"
    assert outputs[0].content == snapshot


def test_cast_orchestrator_with_delegates(snapshot):
    orchestrator = AgentDef(
        name="orchestrator",
        description="Orchestrator. Coordinates sub-agents.",
        role="primary",
        model=ModelConfig(tier="reasoning"),
        capabilities=[
            "read",
            "write",
            {"bash": ["ls*", "cat*", "git status*"]},
            {"delegate": ["explorer", "aligner"]},
        ],
        prompt_content="# Orchestrator",
    )
    adapter = CopilotAdapter()
    outputs = adapter.cast(
        [
            orchestrator,
            AgentDef(name="explorer", description="Explorer"),
            AgentDef(name="aligner", description="Aligner"),
        ],
        COPILOT_CONFIG,
    )
    assert outputs[0].content == snapshot


def test_output_path_uses_agent_name():
    agent = AgentDef(name="my-agent", description="Test")
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert outputs[0].path == ".github/agents/my-agent.md"


def test_read_group_maps_to_copilot_tools():
    agent = AgentDef(name="test", description="Test", capabilities=["read"])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"read", "search"}


def test_basic_group_maps_to_copilot_tools():
    agent = AgentDef(name="test", description="Test", capabilities=["basic"])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"edit", "read", "search", "web"}


def test_empty_capabilities_default_to_basic():
    agent = AgentDef(name="test", description="Test", capabilities=[])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"edit", "read", "search", "web"}


def test_all_capability_maps_to_all_copilot_tools():
    agent = AgentDef(name="test", description="Test", capabilities=["all"])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"agent", "edit", "execute", "read", "search", "web"}


def test_web_access_group_maps_to_web():
    agent = AgentDef(name="test", description="Test", capabilities=["web-access"])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"web"}


def test_delegate_group_maps_to_agent():
    agent = AgentDef(name="test", description="Test", capabilities=["delegate"])
    adapter = CopilotAdapter()
    spec = adapter._expand_capabilities(agent.capabilities, COPILOT_CONFIG.capability_map)
    tools = adapter._map_tool_ids(spec)
    assert set(tools) == {"agent"}


def test_model_resolved_from_model_map():
    agent = AgentDef(
        name="test",
        description="Test",
        model=ModelConfig(tier="coding"),
        prompt_content="prompt",
    )
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert "model: gpt-4o" in outputs[0].content


def test_omits_empty_description():
    agent = AgentDef(name="test", description="", prompt_content="# Prompt")
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert "description:" not in outputs[0].content


def test_frontmatter_only_without_prompt():
    agent = AgentDef(name="minimal", description="Minimal.", prompt_content="")
    adapter = CopilotAdapter()
    outputs = adapter.cast([agent], COPILOT_CONFIG)
    assert outputs[0].content.endswith("---")


def test_default_model_map_used_when_config_empty():
    """Adapter provides default model_map so render still works without roles.toml."""
    adapter = CopilotAdapter()
    assert adapter.default_model_map
    assert "reasoning" in adapter.default_model_map
