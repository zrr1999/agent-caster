# role-forge

Canonical role-definition toolkit for coding agents.

`role-forge` keeps one canonical role source and renders it into platform-specific agent formats for tools like Claude Code, OpenCode, Cursor, and Windsurf.

## Install

```bash
uv tool install role-forge
```

## Quick start

```bash
role-forge add PFCCLab/precision-agents -y
role-forge render --target claude
role-forge list
```

## Why this repo exists

- avoid maintaining the same role prompt in multiple tool-specific formats
- keep capabilities, delegation policy, and model tiers in one canonical source
- validate hierarchy and output layout before rendering
- support extension through adapter entry points

## Capability model

Canonical roles declare abstract capabilities such as `basic`, `read`, `write`, `web-access`, `delegate`, `bash`, `safe-bash`, and `all`. `role-forge` expands those once into a shared intermediate capability model, then each adapter renders the matching tools and permissions for its target. If a role omits capabilities entirely, `basic` is applied by default.

## Documentation

- live site: `https://role-forge.sixbones.dev`
- docs home: `docs/index.md`
- canonical role format: `docs/reference/canonical-role-definition.md`
- CLI reference: `docs/reference/cli.md`
- configuration: `docs/reference/configuration.md`
- adapters: `docs/reference/adapters.md`
- architecture: `docs/architecture/system-overview.md`
- development: `docs/development/contributing.md`
- deployment: `docs/development/deployment.md`

## Documentation site

This repo now includes a Zensical doc set inspired by the structure used in `volvox`.

```bash
uv add --dev zensical
zensical serve
```

## License

MIT
