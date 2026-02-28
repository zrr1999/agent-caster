# Task Plan: Implement agent-caster v0.1 MVP

## Goal

Build `agent-caster` — a cross-platform AI coding agent definition compiler that reads canonical `.agents/roles/*.md` definitions and compiles them to platform-specific configs (OpenCode, Claude Code), with CLI commands `init`, `compile`, `list`, and PyPI-ready packaging.

## Current Phase

Phase 1

## Phases

### Phase 1: Project Scaffolding & Data Models
- [ ] Initialize Python project with `pyproject.toml` (hatchling, click, pyyaml, tomli)
- [ ] Create `src/agent_caster/__init__.py`
- [ ] Implement `models.py` — `AgentDef`, `TargetConfig`, `OutputFile` dataclasses
- [ ] Implement `config.py` — `refit.toml` parser (using tomllib/tomli)
- [ ] Implement `loader.py` — YAML frontmatter parser for `.agents/roles/*.md`
- [ ] Write tests for models, config, loader
- **Status:** pending

### Phase 2: Adapter Architecture & OpenCode Adapter
- [ ] Implement `adapters/base.py` — `Adapter` Protocol
- [ ] Implement `adapters/opencode.py` — migrated from `precision-alignment-agent/adapters/opencode/generate.py`
- [ ] Ensure capability group expansion, model tier mapping, permission generation
- [ ] Write tests: compile a sample agent set, verify output matches expected
- **Status:** pending

### Phase 3: Claude Code Adapter
- [ ] Implement `adapters/claude.py` — generates `CLAUDE.md` + `.claude/agents/*.md`
- [ ] Map capabilities to Claude Code tools (Read, Glob, Grep, Write, Edit, Bash, Task, WebFetch)
- [ ] Handle bash allowedCommands and delegate/Task permissions
- [ ] Write tests for Claude Code output
- **Status:** pending

### Phase 4: Compiler Dispatcher & CLI
- [ ] Implement `compiler.py` — loads config + agents, dispatches to enabled adapters
- [ ] Implement `cli.py` with click:
  - `agent-caster init` — scaffold `.agents/roles/` + `refit.toml`
  - `agent-caster compile [--target T] [--dry-run] [--diff]`
  - `agent-caster list` — tabular listing of agents
- [ ] Register `console_scripts` entry point in `pyproject.toml`
- [ ] Write CLI integration tests
- **Status:** pending

### Phase 5: Validation Against Real Data
- [ ] Copy `precision-alignment-agent/agents/*.md` into a test fixture as `.agents/roles/`
- [ ] Create a matching `refit.toml` with opencode target config
- [ ] Run `agent-caster compile --target opencode` and diff against existing `.opencode/agents/`
- [ ] Verify output is equivalent (or document intentional improvements)
- [ ] Run `agent-caster compile --target claude` and review Claude Code output
- **Status:** pending

### Phase 6: Packaging & Delivery
- [ ] Finalize `pyproject.toml` metadata (name, version, description, license, URLs)
- [ ] Verify `uvx agent-caster compile` works (console_scripts entry point)
- [ ] Add a README.md
- [ ] Git init + initial commit
- **Status:** pending

## Key Questions

1. Should the canonical format stay as `agents/*.md` (current PAA convention) or move to `.agents/roles/*.md` (design doc)? — **Answer: `.agents/roles/` per design doc**
2. What Python version minimum? — **Answer: 3.10+ (use tomllib when available, tomli fallback)**
3. Should we implement `--diff` in v0.1 or defer? — **TBD, defer if scope grows**
4. How to handle `prompt_file` resolution (relative to what)? — **Relative to the agent definition file**

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use click (not typer) | Design doc specifies click; lighter dependency |
| hatchling for build | Modern Python standard, design doc specified |
| tomli + tomllib | tomllib is stdlib in 3.11+; tomli for 3.10 compat |
| Migrate existing generate.py logic | Proven code from PAA, tested in production |
| `.agents/roles/` as canonical dir | Design doc convention, separates from platform-specific dirs |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | — | — |

## Notes

- The existing `precision-alignment-agent/adapters/opencode/generate.py` (248 lines) is the reference implementation to migrate
- 8 agent definitions in PAA serve as the primary test fixture
- The design doc is at `docs/plans/2026-02-27-agent-refit-design.md` (624 lines, comprehensive)
