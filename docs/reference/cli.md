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

### Add roles from a local path

```bash
role-forge add ./my-agents
```

### Render to a specific target

```bash
role-forge render --target claude
```

### List installed roles

```bash
role-forge list
```

### Update a GitHub source

```bash
role-forge update PFCCLab/precision-agents
```

### Remove a role

```bash
role-forge remove explorer
role-forge remove l2/worker
```

## Command model

- `add` fetches a source, validates role topology, installs canonical files, and auto-renders when targets are explicit or detectable
- `render` regenerates target outputs from installed canonical roles
- `cast` remains as a legacy alias of `render`
- `list` shows installed roles with canonical id, role type, and model tier
- `remove` deletes the canonical file; target outputs can then be regenerated with `render`
- `update` reuses the `add` flow for non-local sources

## Target detection

When `--target` is omitted, `role-forge` detects supported tools from project markers:

- Claude Code: `.claude/` or `CLAUDE.md`
- OpenCode: `.opencode/` or `opencode.json`
- Cursor: `.cursor/` or `.cursorrules`
- Windsurf: `.windsurf/` or `.windsurfrules`
