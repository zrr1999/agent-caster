"""Shared tests for model-less adapters."""

from __future__ import annotations

import pytest

from role_forge.adapters.copilot import CopilotAdapter
from role_forge.adapters.cursor import CursorAdapter
from role_forge.adapters.windsurf import WindsurfAdapter
from role_forge.models import AgentDef, TargetConfig

ADAPTER_CASES = [
    pytest.param(CopilotAdapter, "copilot", ".github/agents", ".md", id="copilot"),
    pytest.param(CursorAdapter, "cursor", ".cursor/agents", ".mdc", id="cursor"),
    pytest.param(WindsurfAdapter, "windsurf", ".windsurf/rules", ".md", id="windsurf"),
]


def _config(name: str) -> TargetConfig:
    return TargetConfig(
        name=name,
        enabled=True,
        model_map={},
        capability_map={},
    )


@pytest.mark.parametrize(("adapter_cls", "target_name", "base_dir", "suffix"), ADAPTER_CASES)
def test_model_less_adapter_frontmatter_only_without_prompt(
    adapter_cls,
    target_name: str,
    base_dir: str,
    suffix: str,
):
    agent = AgentDef(
        name="minimal",
        description="Minimal agent.",
        prompt_content="",
    )

    outputs = adapter_cls().cast([agent], _config(target_name))

    assert outputs[0].path == f"{base_dir}/minimal{suffix}"
    assert outputs[0].content.endswith("---")


@pytest.mark.parametrize(("adapter_cls", "target_name", "_base_dir", "_suffix"), ADAPTER_CASES)
def test_model_less_adapter_omits_empty_description(
    adapter_cls, target_name: str, _base_dir: str, _suffix: str
):
    agent = AgentDef(
        name="nodesc",
        description="",
        prompt_content="# No description",
    )

    outputs = adapter_cls().cast([agent], _config(target_name))

    assert "description:" not in outputs[0].content


@pytest.mark.parametrize(("adapter_cls", "target_name", "base_dir", "suffix"), ADAPTER_CASES)
def test_model_less_adapter_nested_role_respects_default_layout(
    adapter_cls,
    target_name: str,
    base_dir: str,
    suffix: str,
):
    agent = AgentDef(name="worker", description="Test", relative_path="l3/worker.md")

    outputs = adapter_cls().cast([agent], _config(target_name))

    adapter = adapter_cls()
    if adapter.default_output_layout == "namespace":
        assert outputs[0].path == f"{base_dir}/l3__worker{suffix}"
    else:
        assert outputs[0].path == f"{base_dir}/l3/worker{suffix}"


@pytest.mark.parametrize(("adapter_cls", "target_name", "_base_dir", "_suffix"), ADAPTER_CASES)
def test_model_less_adapter_ignores_model_map(
    adapter_cls, target_name: str, _base_dir: str, _suffix: str
):
    config_with_model = TargetConfig(
        name=target_name,
        model_map={"reasoning": "gpt-5", "coding": "gpt-4"},
    )
    agent = AgentDef(name="test", description="Test", prompt_content="prompt")

    outputs = adapter_cls().cast([agent], config_with_model)

    assert "model:" not in outputs[0].content


@pytest.mark.parametrize(("adapter_cls", "target_name", "base_dir", "suffix"), ADAPTER_CASES)
def test_model_less_adapter_casts_multiple_agents(
    adapter_cls,
    target_name: str,
    base_dir: str,
    suffix: str,
):
    agents = [
        AgentDef(name="alpha", description="Alpha agent", prompt_content="# Alpha"),
        AgentDef(name="beta", description="Beta agent", prompt_content="# Beta"),
    ]

    outputs = adapter_cls().cast(agents, _config(target_name))

    assert len(outputs) == 2
    assert {output.path for output in outputs} == {
        f"{base_dir}/alpha{suffix}",
        f"{base_dir}/beta{suffix}",
    }
