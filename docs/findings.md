# Findings & Decisions

## Requirements

- Cross-platform caster for AI coding agent definitions
- Single canonical format (YAML frontmatter + Markdown) in `.agents/roles/*.md`
- Casts to: OpenCode (`.opencode/agents/` + `opencode.json`), Claude Code (`CLAUDE.md` + `.claude/agents/`), Cursor (`.cursor/rules/*.mdc`, deferred)
- CLI: `init`, `cast`, `list` (v0.1); `add`, `update`, `inspect` (v0.2)
- Config via `refit.toml`
- PyPI package, runnable via `uvx agent-caster`
- Minimal dependencies: click, pyyaml, tomli

## Research Findings

### Existing PAA Adapter (generate.py)
- Location: `/workspace/precision-alignment-agent/adapters/opencode/generate.py`
- 248 lines, single-file OpenCode adapter
- Already implements: YAML frontmatter parsing, capability group expansion, model tier mapping, permission generation, .opencode/agents/*.md generation
- Key data flow: `load_agent_defs()` -> `expand_capabilities()` -> `generate_agent_md()` -> write files
- Model map: `reasoning -> github-copilot/claude-opus-4.6`, `coding -> github-copilot/gpt-5.2-codex`
- 7 capability groups: read-code, write-code, write-report, web-access, web-read, context7, gh-search
- Structured capabilities: `bash:` (command whitelist), `delegate:` (sub-agent list)

### Canonical Agent Definition Format
- YAML frontmatter fields: name, description, role (primary|subagent), model.tier, model.temperature, skills, capabilities, prompt_file
- Capabilities can be strings (group names) or dicts (bash/delegate with lists)
- prompt_file is relative to the agent file's location
- Body (after frontmatter) is the prompt content if no prompt_file

### PAA Agent Inventory (8 agents)
| Agent | Role | Tier | Temp | Capabilities |
|-------|------|------|------|-------------|
| precision-alignment | primary | reasoning | 0.2 | read-code, write-report, web-read, bash, delegate(6) |
| precision-analysis | primary | reasoning | 0.2 | read-code, write-report, web-read, bash, delegate(2) |
| explorer | subagent | reasoning | 0.05 | read-code, write-report, web-read, context7, bash(repomix) |
| learner | subagent | reasoning | 0.1 | read-code, write-report, web-access, context7, gh-search |
| aligner | subagent | coding | 0.1 | read-code, write-code |
| diagnostician | subagent | coding | 0.05 | read-code, write-code, bash(just/git/uv) |
| validator | subagent | coding | 0.05 | read-code, write-report, bash(just/uv) |
| reviewer | subagent | reasoning | 0.1 | read-code, write-code, web-read, bash(many) |

### refit.toml Format (from design doc)
- `[project]` section: `agents_dir` (default `.agents/roles`)
- `[targets.<name>]` section per platform: `enabled`, `output_dir`, `model_map`, `capability_map`
- `[[sources]]` array for package management (v0.2)

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Python 3.10+ | tomllib in 3.11, tomli fallback for 3.10 |
| AgentDef as dataclass | Clean, typed, matches design doc protocol |
| Adapter as Protocol | Duck typing, allows entry_points extension in v0.3 |
| Capability expansion in loader, not adapter | Consistent parsing, adapters only need to map |
| Actually: capability expansion in adapter | Each platform interprets capabilities differently; loader parses raw capabilities |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| (none yet) | — |

## Resources

- Design doc: `/workspace/agent-caster/docs/plans/2026-02-27-agent-refit-design.md`
- Reference adapter: `/workspace/precision-alignment-agent/adapters/opencode/generate.py`
- PAA agent defs: `/workspace/precision-alignment-agent/agents/*.md`
- PAA Justfile (workflow): `/workspace/precision-alignment-agent/Justfile`
