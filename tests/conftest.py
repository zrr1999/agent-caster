"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_caster.models import AgentDef, ModelConfig, TargetConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_explorer() -> AgentDef:
    return AgentDef(
        name="explorer",
        description="Code Explorer. Reads and analyzes source code.",
        role="subagent",
        model=ModelConfig(tier="reasoning", temperature=0.05),
        skills=["repomix-explorer"],
        capabilities=[
            "read-code",
            "write-report",
            "web-read",
            "context7",
            {"bash": ["npx repomix@latest*", "bunx repomix@latest*"]},
        ],
        prompt_content="# Explorer\n\nRead-only code exploration agent.",
    )


@pytest.fixture
def sample_aligner() -> AgentDef:
    return AgentDef(
        name="aligner",
        description="Precision Aligner. Makes targeted code changes.",
        role="subagent",
        model=ModelConfig(tier="coding", temperature=0.1),
        skills=[],
        capabilities=["read-code", "write-code"],
        prompt_content="# Aligner",
    )


@pytest.fixture
def sample_orchestrator() -> AgentDef:
    return AgentDef(
        name="orchestrator",
        description="Orchestrator. Coordinates sub-agents.",
        role="primary",
        model=ModelConfig(tier="reasoning", temperature=0.2),
        skills=[],
        capabilities=[
            "read-code",
            "write-report",
            {"bash": ["ls*", "cat*", "git status*"]},
            {"delegate": ["explorer", "aligner"]},
        ],
        prompt_content="# Orchestrator",
    )


@pytest.fixture
def opencode_config() -> TargetConfig:
    return TargetConfig(
        name="opencode",
        enabled=True,
        output_dir=".",
        model_map={
            "reasoning": "github-copilot/claude-opus-4.6",
            "coding": "github-copilot/gpt-5.2-codex",
        },
        capability_map={
            "context7": {"context7": True},
            "gh-search": {"gh_grep": True},
        },
    )


@pytest.fixture
def claude_config() -> TargetConfig:
    return TargetConfig(
        name="claude",
        enabled=True,
        output_dir=".",
        model_map={
            "reasoning": "opus",
            "coding": "sonnet",
        },
        capability_map={},
    )
