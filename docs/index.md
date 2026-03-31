# role-forge

Canonical role-definition toolkit for coding agents.

## Why it exists

Different coding tools want different agent formats. `role-forge` keeps one canonical role source and renders it into tool-specific outputs, so teams do not duplicate prompts, capabilities, model tiers, or delegation policy in each tool.

## What it does

- fetches reusable role definitions from GitHub repos or local paths
- keeps project-authored canonical roles in `roles/` and fetched repos in the global repo cache
- generates Claude Code, OpenCode, Cursor, and Windsurf files directly from source repos or repo cache
- validates hierarchy, delegation rules, and output layout collisions before writing files
- lets third-party adapters extend the render pipeline through entry points

## Start here

- new to the project: read `docs/reference/cli.md`
- writing canonical roles: read `docs/reference/canonical-role-definition.md`
- configuring targets: read `docs/reference/configuration.md`
- extending outputs: read `docs/reference/adapters.md`
- understanding architecture: read `docs/architecture/system-overview.md`
- contributing: read `docs/development/contributing.md`
