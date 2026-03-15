# CLI

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
role-forge add ./my-agents -g
```

### Render to a specific target

```bash
role-forge render --target claude
```

### List installed roles

```bash
role-forge list
role-forge list -g
role-forge list --json
```

### Check unmanaged files

```bash
role-forge doctor
role-forge doctor -g --json
```

### Clean unmanaged files

```bash
role-forge clean --dry-run
role-forge clean -y
```

### Update a GitHub source

```bash
role-forge update PFCCLab/precision-agents
role-forge update PFCCLab/precision-agents -g -y
```

### Remove a role

```bash
role-forge remove explorer
role-forge remove l2/worker
```

## Command model

- `add` fetches a source, validates role topology, installs canonical files, and auto-renders when targets are explicit or detectable
- `add` is interactive by default; `--yes` skips install and overwrite prompts
- `render` regenerates target outputs from merged canonical roles, with project scope overriding user scope
- `list` shows installed roles for one scope at a time; use `-g` for user scope and `--json` for machine-readable output
- `remove` deletes the canonical file from one scope; target outputs can then be regenerated with `render`
- `doctor` reports unmanaged files in the selected roles directory
- `clean` removes unmanaged files from the selected roles directory
- `update` reuses the `add` flow for non-local sources and also supports `-g`

## Target detection

When `--target` is omitted, `role-forge` detects supported tools from project markers:

- Claude Code: `.claude/` or `CLAUDE.md`
- OpenCode: `.opencode/` or `opencode.json`
- Cursor: `.cursor/` or `.cursorrules`
- Windsurf: `.windsurf/` or `.windsurfrules`
