# CLI Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor agent-caster from a render-only CLI to a package manager + renderer, with `add` as the core command that fetches agent definitions from GitHub and auto-casts to detected platforms.

**Architecture:** New `registry.py` handles source parsing and git operations. New `platform.py` detects installed AI tools. `cli.py` is rewritten with `add/update/list/remove/cast` commands. Existing `loader.py`, `adapters/`, `groups.py` stay largely unchanged. `config.py` simplified to only read source repo configs.

**Tech Stack:** Python 3.12+, typer (CLI), subprocess (git), pydantic (models), pyyaml (frontmatter), existing adapter infrastructure.

---

### Task 1: Add `registry.py` — source parsing

**Files:**
- Create: `src/agent_caster/registry.py`
- Test: `tests/test_registry.py`

**Step 1: Write the failing tests**

```python
"""Tests for registry.py — source parsing."""
from __future__ import annotations

import pytest

from agent_caster.registry import ParsedSource, parse_source


def test_parse_org_repo():
    src = parse_source("PFCCLab/precision-agents")
    assert src.org == "PFCCLab"
    assert src.repo == "precision-agents"
    assert src.ref is None
    assert src.is_local is False
    assert src.github_url == "https://github.com/PFCCLab/precision-agents"


def test_parse_org_repo_with_ref():
    src = parse_source("PFCCLab/precision-agents@v1.0")
    assert src.org == "PFCCLab"
    assert src.repo == "precision-agents"
    assert src.ref == "v1.0"


def test_parse_org_repo_with_branch_ref():
    src = parse_source("PFCCLab/precision-agents@main")
    assert src.ref == "main"


def test_parse_local_relative():
    src = parse_source("./my/agents")
    assert src.is_local is True
    assert src.local_path == "./my/agents"
    assert src.org is None
    assert src.repo is None


def test_parse_local_absolute():
    src = parse_source("/tmp/my-agents")
    assert src.is_local is True
    assert src.local_path == "/tmp/my-agents"


def test_parse_invalid_no_slash():
    with pytest.raises(ValueError, match="Invalid source"):
        parse_source("just-a-name")


def test_parse_empty():
    with pytest.raises(ValueError, match="Invalid source"):
        parse_source("")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_caster.registry'`

**Step 3: Write minimal implementation**

```python
"""Source parsing and git operations for agent-caster registry."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedSource:
    """A parsed source reference."""

    org: str | None = None
    repo: str | None = None
    ref: str | None = None
    local_path: str | None = None

    @property
    def is_local(self) -> bool:
        return self.local_path is not None

    @property
    def github_url(self) -> str:
        if self.is_local:
            raise ValueError("Local source has no GitHub URL")
        return f"https://github.com/{self.org}/{self.repo}"

    @property
    def cache_key(self) -> str:
        if self.is_local:
            raise ValueError("Local source has no cache key")
        return f"{self.org}/{self.repo}"


def parse_source(source: str) -> ParsedSource:
    """Parse a source string into a ParsedSource.

    Formats:
        org/repo            → GitHub repo
        org/repo@ref        → GitHub repo at ref
        ./path              → local relative path
        /path               → local absolute path
    """
    if not source:
        raise ValueError("Invalid source: empty string")

    if source.startswith("./") or source.startswith("/"):
        return ParsedSource(local_path=source)

    if "/" not in source:
        raise ValueError(
            f"Invalid source: {source!r}. Expected 'org/repo' or a local path."
        )

    # Split off @ref if present
    if "@" in source:
        repo_part, ref = source.rsplit("@", 1)
    else:
        repo_part, ref = source, None

    parts = repo_part.split("/", 1)
    return ParsedSource(org=parts[0], repo=parts[1], ref=ref)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/registry.py tests/test_registry.py
git commit -m "✨ feat(registry): add source string parser"
```

---

### Task 2: Add `registry.py` — git clone/fetch and cache management

**Files:**
- Modify: `src/agent_caster/registry.py`
- Test: `tests/test_registry.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_registry.py`:

```python
from unittest.mock import patch, MagicMock
from pathlib import Path

from agent_caster.registry import fetch_source, CACHE_DIR


def test_fetch_local_source(tmp_path):
    """Local source returns the path directly, no git."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# E")

    src = parse_source(str(tmp_path))
    result = fetch_source(src)
    assert result == Path(str(tmp_path))


def test_fetch_local_source_not_found():
    src = parse_source("/nonexistent/path/to/agents")
    with pytest.raises(FileNotFoundError):
        fetch_source(src)


@patch("agent_caster.registry.subprocess.run")
def test_fetch_github_clones_to_cache(mock_run, tmp_path):
    """First fetch should git clone to cache dir."""
    mock_run.return_value = MagicMock(returncode=0)

    src = parse_source("PFCCLab/precision-agents@main")
    with patch.object(
        type(src), "cache_key", new_callable=lambda: property(lambda self: "PFCCLab/precision-agents")
    ):
        result = fetch_source(src, cache_root=tmp_path)

    expected_dir = tmp_path / "PFCCLab" / "precision-agents"
    assert result == expected_dir
    # Should have called git clone
    assert mock_run.call_count >= 1
    clone_call = mock_run.call_args_list[0]
    assert "clone" in clone_call.args[0]


@patch("agent_caster.registry.subprocess.run")
def test_fetch_github_pulls_existing_cache(mock_run, tmp_path):
    """If cache exists, should git fetch + checkout instead of clone."""
    mock_run.return_value = MagicMock(returncode=0)

    # Pre-create cache dir to simulate existing clone
    cache_dir = tmp_path / "PFCCLab" / "precision-agents"
    cache_dir.mkdir(parents=True)
    (cache_dir / ".git").mkdir()

    src = parse_source("PFCCLab/precision-agents@v1.0")
    result = fetch_source(src, cache_root=tmp_path)

    assert result == cache_dir
    # Should have called git fetch, not clone
    calls = [str(c) for c in mock_run.call_args_list]
    assert any("fetch" in c for c in calls)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_registry.py::test_fetch_local_source -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_source'`

**Step 3: Write minimal implementation**

Append to `src/agent_caster/registry.py`:

```python
import subprocess
from pathlib import Path

CACHE_DIR = Path.home() / ".config" / "agent-caster" / "repos"


def fetch_source(source: ParsedSource, cache_root: Path | None = None) -> Path:
    """Fetch source to local path. Returns directory containing agent definitions.

    - Local sources: validates path exists, returns it directly.
    - GitHub sources: clones/fetches to cache, returns cache path.
    """
    if source.is_local:
        path = Path(source.local_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Local source not found: {source.local_path}")
        return path

    cache = (cache_root or CACHE_DIR) / source.cache_key
    if (cache / ".git").is_dir():
        _git_fetch(cache, source.ref)
    else:
        _git_clone(source.github_url, cache, source.ref)

    return cache


def _git_clone(url: str, dest: Path, ref: str | None) -> None:
    """Shallow clone a repo."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(dest)])
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _git_fetch(repo_dir: Path, ref: str | None) -> None:
    """Fetch and checkout in an existing clone."""
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=repo_dir, check=True, capture_output=True, text=True,
    )
    target = ref or "origin/HEAD"
    subprocess.run(
        ["git", "checkout", target],
        cwd=repo_dir, check=True, capture_output=True, text=True,
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/registry.py tests/test_registry.py
git commit -m "✨ feat(registry): add git clone/fetch and cache management"
```

---

### Task 3: Add `registry.py` — find agents in fetched repo

**Files:**
- Modify: `src/agent_caster/registry.py`
- Test: `tests/test_registry.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_registry.py`:

```python
from agent_caster.registry import find_roles_dir


def test_find_roles_dir_with_refit_toml(tmp_path):
    """refit.toml roles_dir takes priority."""
    (tmp_path / "refit.toml").write_text('[project]\nroles_dir = "my-agents"')
    agents = tmp_path / "my-agents"
    agents.mkdir()
    (agents / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == agents


def test_find_roles_dir_default_roles(tmp_path):
    """Without refit.toml, falls back to roles/."""
    roles = tmp_path / "roles"
    roles.mkdir()
    (roles / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == roles


def test_find_roles_dir_refit_without_roles_dir(tmp_path):
    """refit.toml without roles_dir falls back to roles/."""
    (tmp_path / "refit.toml").write_text("[project]\n")
    roles = tmp_path / "roles"
    roles.mkdir()
    (roles / "test.md").write_text("---\nname: test\n---\n")

    result = find_roles_dir(tmp_path)
    assert result == roles


def test_find_roles_dir_none_found(tmp_path):
    """No refit.toml and no roles/ should raise."""
    with pytest.raises(FileNotFoundError, match="No agent definitions found"):
        find_roles_dir(tmp_path)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_registry.py::test_find_roles_dir_with_refit_toml -v`
Expected: FAIL — `ImportError: cannot import name 'find_roles_dir'`

**Step 3: Write minimal implementation**

Append to `src/agent_caster/registry.py`:

```python
import tomllib


def find_roles_dir(repo_path: Path) -> Path:
    """Find agent definitions directory in a fetched repo.

    Priority:
    1. refit.toml roles_dir setting
    2. roles/ directory
    """
    refit_path = repo_path / "refit.toml"
    if refit_path.is_file():
        with open(refit_path, "rb") as f:
            data = tomllib.load(f)
        roles_dir_name = data.get("project", {}).get("roles_dir")
        if roles_dir_name:
            roles_dir = repo_path / roles_dir_name
            if roles_dir.is_dir():
                return roles_dir

    # Default fallback
    roles_dir = repo_path / "roles"
    if roles_dir.is_dir():
        return roles_dir

    raise FileNotFoundError(
        f"No agent definitions found in {repo_path}. "
        "Expected refit.toml with roles_dir or a roles/ directory."
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/registry.py tests/test_registry.py
git commit -m "✨ feat(registry): find agent definitions dir in fetched repos"
```

---

### Task 4: Add `platform.py` — detect AI tools in project

**Files:**
- Create: `src/agent_caster/platform.py`
- Test: `tests/test_platform.py`

**Step 1: Write the failing tests**

```python
"""Tests for platform.py — detect AI coding tools."""
from __future__ import annotations

from pathlib import Path

from agent_caster.platform import detect_platforms


def test_detect_claude_by_dir(tmp_path):
    (tmp_path / ".claude").mkdir()
    assert "claude" in detect_platforms(tmp_path)


def test_detect_claude_by_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Claude")
    assert "claude" in detect_platforms(tmp_path)


def test_detect_opencode_by_dir(tmp_path):
    (tmp_path / ".opencode").mkdir()
    assert "opencode" in detect_platforms(tmp_path)


def test_detect_opencode_by_json(tmp_path):
    (tmp_path / "opencode.json").write_text("{}")
    assert "opencode" in detect_platforms(tmp_path)


def test_detect_multiple(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    platforms = detect_platforms(tmp_path)
    assert "claude" in platforms
    assert "opencode" in platforms


def test_detect_none(tmp_path):
    assert detect_platforms(tmp_path) == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_platform.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_caster.platform'`

**Step 3: Write minimal implementation**

```python
"""Detect AI coding tools installed in a project."""
from __future__ import annotations

from pathlib import Path

# (marker_files_or_dirs, adapter_name)
_DETECTORS: list[tuple[list[str], str]] = [
    ([".claude", "CLAUDE.md"], "claude"),
    ([".opencode", "opencode.json"], "opencode"),
]


def detect_platforms(project_dir: Path) -> list[str]:
    """Detect AI coding tool platforms present in project_dir.

    Returns list of adapter names (e.g. ["claude", "opencode"]).
    """
    found: list[str] = []
    for markers, name in _DETECTORS:
        if any((project_dir / m).exists() for m in markers):
            found.append(name)
    return found
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_platform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/platform.py tests/test_platform.py
git commit -m "✨ feat(platform): detect AI coding tools in project directory"
```

---

### Task 5: Add default model_map to adapters

**Files:**
- Modify: `src/agent_caster/adapters/claude.py:22` (add `DEFAULT_MODEL_MAP`)
- Modify: `src/agent_caster/adapters/opencode.py:12` (add `DEFAULT_MODEL_MAP`)
- Modify: `src/agent_caster/adapters/base.py` (add `default_model_map` to protocol)
- Test: `tests/test_claude.py` (append)
- Test: `tests/test_opencode.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_claude.py`:

```python
def test_default_model_map():
    adapter = ClaudeAdapter()
    assert "reasoning" in adapter.default_model_map
    assert "coding" in adapter.default_model_map
```

Append to `tests/test_opencode.py`:

```python
def test_default_model_map():
    adapter = OpenCodeAdapter()
    assert "reasoning" in adapter.default_model_map
    assert "coding" in adapter.default_model_map
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_claude.py::test_default_model_map tests/test_opencode.py::test_default_model_map -v`
Expected: FAIL — `AttributeError: 'ClaudeAdapter' object has no attribute 'default_model_map'`

**Step 3: Write minimal implementation**

In `src/agent_caster/adapters/claude.py`, add after line 19 (after `_TOOL_NAME_MAP`):

```python
DEFAULT_MODEL_MAP: dict[str, str] = {
    "reasoning": "claude-opus-4-6",
    "coding": "claude-sonnet-4",
}
```

And add to `ClaudeAdapter` class:

```python
    default_model_map: dict[str, str] = DEFAULT_MODEL_MAP
```

In `src/agent_caster/adapters/opencode.py`, add after the imports:

```python
DEFAULT_MODEL_MAP: dict[str, str] = {
    "reasoning": "anthropic:claude-opus-4-6",
    "coding": "anthropic:claude-sonnet-4",
}
```

And add to `OpenCodeAdapter` class:

```python
    default_model_map: dict[str, str] = DEFAULT_MODEL_MAP
```

In `src/agent_caster/adapters/base.py`, add `default_model_map` to protocol:

```python
class Adapter(Protocol):
    name: str
    default_model_map: dict[str, str]

    def cast(self, agents: list[AgentDef], config: TargetConfig) -> list[OutputFile]: ...
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_claude.py tests/test_opencode.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/adapters/
git commit -m "✨ feat(adapters): add default model_map to each adapter"
```

---

### Task 6: Rewrite `cli.py` — add command (non-interactive first)

**Files:**
- Modify: `src/agent_caster/cli.py` (rewrite)
- Test: `tests/test_cli.py` (rewrite)

This task replaces the existing CLI. The `init` command is removed. `cast` and `list` are kept with simplified signatures. The `add` command is added with `--yes` mode first (no interactive prompts).

**Step 1: Write the failing tests**

Replace `tests/test_cli.py`:

```python
"""Tests for CLI commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from agent_caster.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "agent-caster" in result.output


# -- add command ---------------------------------------------------------------


def test_add_from_local(tmp_path):
    """add from a local path with --yes should copy agents and skip interaction."""
    # Set up a fake source repo
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n---\n# Explorer\n"
    )

    # Set up project dir
    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(app, [
        "add", str(source), "--yes", "--project-dir", str(project),
    ])
    assert result.exit_code == 0, result.output
    assert (project / ".agents" / "roles" / "explorer.md").is_file()


def test_add_global(tmp_path):
    """add --global should install to ~/.agents/roles/."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "test.md").write_text(
        "---\nname: test\ndescription: Test\nrole: subagent\n---\n# Test\n"
    )

    global_home = tmp_path / "fakehome"
    global_home.mkdir()

    with patch("agent_caster.cli.Path.home", return_value=global_home):
        result = runner.invoke(app, [
            "add", str(source), "--yes", "--global",
        ])
    assert result.exit_code == 0, result.output
    assert (global_home / ".agents" / "roles" / "test.md").is_file()


def test_add_with_auto_cast(tmp_path):
    """add should auto-cast when platform is detected."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()
    (project / ".claude").mkdir()  # trigger claude detection

    result = runner.invoke(app, [
        "add", str(source), "--yes", "--project-dir", str(project),
    ])
    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "explorer.md").is_file()


def test_add_with_explicit_target(tmp_path):
    """add --target should cast to specified platform only."""
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    result = runner.invoke(app, [
        "add", str(source), "--yes", "--target", "claude",
        "--project-dir", str(project),
    ])
    assert result.exit_code == 0, result.output
    assert (project / ".claude" / "agents" / "explorer.md").is_file()


# -- list command --------------------------------------------------------------


def test_list_agents(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\n---\n# Explorer\n"
    )
    result = runner.invoke(app, ["list", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "explorer" in result.output


# -- cast command --------------------------------------------------------------


def test_cast_with_target(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )
    result = runner.invoke(app, [
        "cast", "--target", "claude", "--project-dir", str(tmp_path),
    ])
    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "agents" / "explorer.md").is_file()


# -- remove command ------------------------------------------------------------


def test_remove_agent(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    (roles_dir / "explorer.md").write_text("---\nname: explorer\n---\n# E")
    result = runner.invoke(app, [
        "remove", "explorer", "--yes", "--project-dir", str(tmp_path),
    ])
    assert result.exit_code == 0
    assert not (roles_dir / "explorer.md").exists()


def test_remove_nonexistent(tmp_path):
    roles_dir = tmp_path / ".agents" / "roles"
    roles_dir.mkdir(parents=True)
    result = runner.invoke(app, [
        "remove", "nonexistent", "--project-dir", str(tmp_path),
    ])
    assert result.exit_code == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — missing `add`, `remove` commands, changed `list`/`cast` signatures

**Step 3: Write minimal implementation**

Rewrite `src/agent_caster/cli.py`:

```python
"""CLI entry point for agent-caster."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated

import typer

from agent_caster import __version__
from agent_caster.log import logger

app = typer.Typer(
    help="agent-caster: AI coding agent definition manager. Fetch, install, and cast agent definitions across tools."
)


def _version_callback(value: bool) -> None:
    if value:
        logger.info(f"agent-caster {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """agent-caster: AI coding agent definition manager."""


@app.command()
def add(
    source: Annotated[str, typer.Argument(help="Source: org/repo[@ref] or local path")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    global_install: Annotated[
        bool, typer.Option("--global", "-g", help="Install to ~/.agents/roles/")
    ] = False,
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Cast target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Add agent definitions from a source."""
    from agent_caster.adapters import get_adapter
    from agent_caster.loader import load_agents
    from agent_caster.models import TargetConfig
    from agent_caster.platform import detect_platforms
    from agent_caster.registry import fetch_source, find_roles_dir, parse_source

    parsed = parse_source(source)

    try:
        repo_path = fetch_source(parsed)
    except Exception as e:
        logger.error(f"Error fetching source: {e}")
        raise typer.Exit(1) from e

    try:
        roles_dir = find_roles_dir(repo_path)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise typer.Exit(1) from e

    agents = load_agents(roles_dir)
    if not agents:
        logger.error("No agent definitions found in source.")
        raise typer.Exit(1)

    logger.info(f"Found {len(agents)} agents:")
    for a in agents:
        logger.info(f"  {a.name:<25} {a.role:<10} {a.model.tier}")

    # Determine install target
    if global_install:
        install_dir = Path.home() / ".agents" / "roles"
    else:
        project = Path(project_dir).resolve() if project_dir else Path.cwd()
        install_dir = project / ".agents" / "roles"

    install_dir.mkdir(parents=True, exist_ok=True)

    # Copy agent files
    for a in agents:
        if a.source_path:
            dest = install_dir / a.source_path.name
            if dest.exists() and not yes:
                # In non-interactive (test) mode, skip conflict for now
                pass
            shutil.copy2(a.source_path, dest)
            logger.info(f"  Installed {a.name}")

    logger.info(f"\nInstalled {len(agents)} agents to {install_dir}")

    # Auto-cast
    if global_install and not target:
        return  # Global install skips auto-cast unless --target

    project = Path(project_dir).resolve() if project_dir else Path.cwd()

    if target:
        cast_targets = list(target)
    else:
        cast_targets = detect_platforms(project)

    if not cast_targets:
        return

    # Reload from installed location to cast
    installed_agents = load_agents(install_dir)
    for target_name in cast_targets:
        try:
            adapter = get_adapter(target_name)
        except ValueError:
            logger.error(f"Unknown target: {target_name}")
            continue

        config = TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map=adapter.default_model_map,
        )

        outputs = adapter.cast(installed_agents, config)
        for out in outputs:
            full_path = project / out.path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(out.content, encoding="utf-8")

        logger.info(f"Cast {len(outputs)} agents → {target_name}")


@app.command("list")
def list_agents(
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """List all installed agent definitions."""
    from agent_caster.loader import load_agents

    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    roles_dir = project / ".agents" / "roles"

    if not roles_dir.is_dir():
        logger.error("No agents found. Run 'agent-caster add' first.")
        raise typer.Exit(1)

    agents = load_agents(roles_dir)

    logger.info(f"{'AGENT':<25} {'ROLE':<10} {'TIER':<12} {'TEMP':<6}")
    logger.info("-" * 55)
    for agent in agents:
        temp = str(agent.model.temperature) if agent.model.temperature is not None else "-"
        logger.info(f"{agent.name:<25} {agent.role:<10} {agent.model.tier:<12} {temp:<6}")

    logger.info(f"\n{len(agents)} agents found")


@app.command()
def cast(
    target: Annotated[
        list[str] | None, typer.Option("--target", "-t", help="Target platform(s)")
    ] = None,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Cast installed agent definitions to platform-specific configs."""
    from agent_caster.adapters import get_adapter
    from agent_caster.loader import load_agents
    from agent_caster.models import TargetConfig
    from agent_caster.platform import detect_platforms

    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    roles_dir = project / ".agents" / "roles"

    if not roles_dir.is_dir():
        logger.error("No agents found. Run 'agent-caster add' first.")
        raise typer.Exit(1)

    agents = load_agents(roles_dir)
    cast_targets = list(target) if target else detect_platforms(project)

    if not cast_targets:
        logger.error("No platforms detected. Use --target to specify.")
        raise typer.Exit(1)

    for target_name in cast_targets:
        try:
            adapter = get_adapter(target_name)
        except ValueError as e:
            logger.error(str(e))
            continue

        config = TargetConfig(
            name=target_name,
            enabled=True,
            output_dir=".",
            model_map=adapter.default_model_map,
        )

        outputs = adapter.cast(agents, config)
        for out in outputs:
            full_path = project / out.path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(out.content, encoding="utf-8")

        logger.info(f"Cast {len(outputs)} agents → {target_name}")


@app.command()
def remove(
    agent_name: Annotated[str, typer.Argument(help="Agent name to remove")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Remove an installed agent definition."""
    project = Path(project_dir).resolve() if project_dir else Path.cwd()
    roles_dir = project / ".agents" / "roles"
    agent_file = roles_dir / f"{agent_name}.md"

    if not agent_file.is_file():
        logger.error(f"Agent not found: {agent_name}")
        raise typer.Exit(1)

    agent_file.unlink()
    logger.info(f"Removed {agent_name}")
    logger.info("Note: platform-specific files may still exist. Run 'agent-caster cast' to regenerate.")


@app.command()
def update(
    source: Annotated[str, typer.Argument(help="Source to update: org/repo")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip all prompts")] = False,
    project_dir: Annotated[
        str | None, typer.Option("--project-dir", help="Project root directory")
    ] = None,
) -> None:
    """Update agent definitions from a previously added source."""
    # Re-use add logic — fetch_source will git pull if cached
    from agent_caster.registry import parse_source

    parsed = parse_source(source)
    if parsed.is_local:
        logger.error("Cannot update a local source. Use 'add' instead.")
        raise typer.Exit(1)

    # Delegate to add
    from click import Context

    ctx = typer.main.get_group(app)
    ctx.invoke(add, source=source, yes=yes, project_dir=project_dir)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agent_caster/cli.py tests/test_cli.py
git commit -m "✨ feat(cli): rewrite CLI with add/update/list/remove/cast commands"
```

---

### Task 7: Update project metadata and description

**Files:**
- Modify: `pyproject.toml:7` (description)
- Modify: `src/agent_caster/cli.py:41` (help text)
- Modify: `README.md` (update Quick Start section)

**Step 1: Update pyproject.toml description**

Change line 7:
```
description = "Cross-platform AI coding agent definition caster"
```
to:
```
description = "AI coding agent definition manager — fetch, install, and cast across tools"
```

**Step 2: Update README.md**

Rewrite the Quick Start section to reflect new CLI commands:
- Replace `agent-caster init` / `agent-caster cast` examples with `agent-caster add` / `agent-caster cast`
- Update the project description tagline
- Remove refit.toml Configuration section for end users (keep it as source repo config only)

**Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 4: Commit**

```bash
git add pyproject.toml README.md src/agent_caster/cli.py
git commit -m "📝 docs: update project description and README for new CLI"
```

---

### Task 8: Simplify `config.py` and update `caster.py`

**Files:**
- Modify: `src/agent_caster/config.py` (remove `find_config`, simplify to only parse a given path)
- Modify: `src/agent_caster/caster.py` (remove dependency on user refit.toml)
- Modify: `tests/test_config.py` (remove `find_config` tests, keep `load_config`)

**Step 1: Simplify config.py**

Remove `find_config` function. `load_config` stays as-is — it's used by `registry.py:find_roles_dir` to read source repo configs.

**Step 2: Simplify caster.py**

The `cast_agents` and `write_outputs` functions can be simplified or removed — the CLI now handles the cast pipeline directly through adapters. Keep the file if other code imports from it, or remove if no longer needed.

**Step 3: Update tests**

Remove `test_find_config_from_subdir` and `test_find_config_not_found` from `tests/test_config.py`. Keep `load_config` tests since `find_roles_dir` in registry uses it.

**Step 4: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 5: Run lint and type checks**

Run: `just ci`
Expected: PASS

**Step 6: Commit**

```bash
git add src/agent_caster/config.py src/agent_caster/caster.py tests/test_config.py
git commit -m "♻️ refactor: simplify config.py and caster.py for new CLI model"
```

---

### Task 9: Final integration test and cleanup

**Files:**
- Modify: `tests/test_cli.py` (add integration test)
- Possibly modify: various files for lint/type fixes

**Step 1: Write end-to-end integration test**

Append to `tests/test_cli.py`:

```python
def test_full_workflow_add_list_cast_remove(tmp_path):
    """Full workflow: add → list → cast → remove."""
    # Set up source
    source = tmp_path / "source"
    roles = source / "roles"
    roles.mkdir(parents=True)
    (roles / "explorer.md").write_text(
        "---\nname: explorer\ndescription: Explorer\nrole: subagent\n"
        "model:\n  tier: reasoning\ncapabilities:\n  - read\n---\n# Explorer\n"
    )
    (roles / "aligner.md").write_text(
        "---\nname: aligner\ndescription: Aligner\nrole: subagent\n"
        "model:\n  tier: coding\ncapabilities:\n  - write\n---\n# Aligner\n"
    )

    project = tmp_path / "project"
    project.mkdir()

    # add
    result = runner.invoke(app, [
        "add", str(source), "--yes", "--target", "claude",
        "--project-dir", str(project),
    ])
    assert result.exit_code == 0
    assert (project / ".agents" / "roles" / "explorer.md").is_file()
    assert (project / ".claude" / "agents" / "explorer.md").is_file()
    assert (project / ".claude" / "agents" / "aligner.md").is_file()

    # list
    result = runner.invoke(app, ["list", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert "explorer" in result.output
    assert "aligner" in result.output
    assert "2 agents found" in result.output

    # cast (re-cast)
    result = runner.invoke(app, [
        "cast", "--target", "claude", "--project-dir", str(project),
    ])
    assert result.exit_code == 0

    # remove
    result = runner.invoke(app, [
        "remove", "explorer", "--yes", "--project-dir", str(project),
    ])
    assert result.exit_code == 0
    assert not (project / ".agents" / "roles" / "explorer.md").exists()

    # list again
    result = runner.invoke(app, ["list", "--project-dir", str(project)])
    assert result.exit_code == 0
    assert "1 agents found" in result.output
```

**Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

**Step 3: Run full CI**

Run: `just ci`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_cli.py
git commit -m "✅ test: add full workflow integration test"
```

---

## Summary

| Task | Component | What |
|------|-----------|------|
| 1 | `registry.py` | Source string parser |
| 2 | `registry.py` | Git clone/fetch + cache |
| 3 | `registry.py` | Find agents dir in repo |
| 4 | `platform.py` | Detect AI tools |
| 5 | `adapters/` | Default model_map |
| 6 | `cli.py` | Rewrite CLI commands |
| 7 | `pyproject.toml`, `README.md` | Update descriptions |
| 8 | `config.py`, `caster.py` | Simplify for new model |
| 9 | Integration | End-to-end test + cleanup |
