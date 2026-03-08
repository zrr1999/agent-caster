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

1. install or update canonical roles from a GitHub repository or local path
2. store those roles under `.agents/roles/` or a configured `roles_dir`
3. resolve target configuration from `roles.toml`
4. validate hierarchy, delegation, and output layout safety
5. render platform outputs such as `.claude/agents/*.md`

## Design goals

- one canonical source instead of duplicated platform prompts
- explicit validation before file generation
- platform adapters isolated behind a shared render pipeline
- incremental adoption for projects that only need one target
- extension through Python entry points for third-party adapters
