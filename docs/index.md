# role-forge

Canonical role-definition toolkit for coding agents.

## Why it exists

Different coding tools want different agent formats. `role-forge` keeps one canonical role source and renders it into tool-specific outputs, so teams do not duplicate prompts, capabilities, model tiers, or delegation policy in each tool.

## What it does

- installs reusable role definitions from GitHub repos or local paths
- stores a canonical source tree in `.agents/roles/`
- renders that source into Claude Code, OpenCode, Cursor, and Windsurf formats
- validates hierarchy, delegation rules, and output layout collisions before writing files
- lets third-party adapters extend the render pipeline through entry points

## Start here

- new to the project: read `docs/reference/cli.md`
- writing canonical roles: read `docs/reference/canonical-role-definition.md`
- configuring targets: read `docs/reference/configuration.md`
- extending outputs: read `docs/reference/adapters.md`
- understanding architecture: read `docs/architecture/system-overview.md`
- contributing: read `docs/development/contributing.md`
