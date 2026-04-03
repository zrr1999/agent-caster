# System Overview

## Positioning

`role-forge` is a canonical role-definition manager and multi-platform renderer for coding agents.

It is not a compiler in the traditional sense. It does three practical jobs:

- manages canonical role definitions in one source format
- validates role topology and output constraints before writing files
- renders platform-specific agent files for supported tools

## Core model

The product revolves around one source of truth:

- canonical role files stored as Markdown with YAML frontmatter
- logical model tiers such as `reasoning` and `coding`
- abstract capability groups such as `read`, `write`, and `web-access`
- optional hierarchy and delegation metadata

Platform adapters interpret that source into target-specific files without changing the canonical definitions themselves.

## Runtime flow

Typical project flow:

1. fetch or refresh a canonical role source from a GitHub repository or local path
2. resolve role definitions from the source repo itself (`roles/` or `project.roles_dir`)
3. resolve target configuration from the source repo's `roles.toml`, then fall back to adapter defaults or project marker detection
4. validate hierarchy, delegation, and output layout safety
5. generate platform outputs such as `.claude/agents/*.md`

## Design goals

- one canonical source instead of duplicated platform prompts
- explicit validation before file generation
- platform adapters isolated behind a shared render pipeline
- incremental adoption for projects that only need one target
- extension through Python entry points for third-party adapters

## Design principles

- **Single source of truth**: All platform outputs are generated from canonical roles; generated files are not edited by hand.
- **Abstract over concrete**: Canonical definitions use logical tiers (e.g. `reasoning` / `coding`) and capability groups (e.g. `read`), mapped to platform-specific models and tools by adapters.
- **Safe defaults**: Deny-by-default for permissions; bash whitelists and delegation are explicit in role definitions.
- **Extensibility**: Adapters register via Python entry points; third parties can add new targets without changing core code.
