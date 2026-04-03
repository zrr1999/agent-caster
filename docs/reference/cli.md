# CLI

## Source format

- **GitHub**: `org/repo` or `org/repo@ref` (branch/tag). Resolved to the repository; `ref` is used for checkout.
- **Local**: `./path` or `/absolute/path`. Roles are read directly from that path; no git.

## Install

```bash
uv tool install role-forge
```

## Commands

### Add roles from GitHub

```bash
role-forge add PFCCLab/precision-agents -y
```

Without `--yes`, `add` and `update` ask before overwriting existing files.

### Add roles from a local path

```bash
role-forge add ./my-agents
```

### List generated project sources

```bash
role-forge list
role-forge list --json
```

### List cached sources

```bash
role-forge list --sources
role-forge list --sources --json
```

### Update a GitHub source

```bash
role-forge update PFCCLab/precision-agents
role-forge update PFCCLab/precision-agents -y
```

### Remove a source and its generated outputs

```bash
role-forge remove PFCCLab/precision-agents --yes
role-forge remove /absolute/path/to/local-roles --yes
```

## Command model

- `add` fetches a source, validates role topology, chooses targets, and generates output files directly
- `update` refreshes a GitHub source and regenerates the same targets and role selection unless overridden
- `list` shows project-generated sources by default; use `--sources` to inspect the global repo cache index
- `remove` deletes a source's generated files, removes cached remote repos, and rebuilds remaining recorded sources to restore collisions
- there is no standalone `render` command; regeneration flows through `add` and `update`

## Target detection

When `--target` is omitted, `role-forge` detects supported tools from project markers:

- Claude Code: `.claude/` or `CLAUDE.md`
- OpenCode: `.opencode/` or `opencode.json`
- Cursor: `.cursor/` or `.cursorrules`
- Windsurf: `.windsurf/` or `.windsurfrules`

## Behavior notes

- **Overwrite**: Without `--yes`, `add` and `update` prompt before overwriting existing output files.
- **Update**: Only non-local sources can be updated; local paths must be re-added.
- **Source config**: `roles.toml` is read from the source repo itself; target resolution falls back to adapter defaults or project marker detection when needed.
- **State files**: project output ownership is tracked in `.role-forge/outputs.json`; cached remote repos are indexed in `~/.config/role-forge/manifest.json`.
