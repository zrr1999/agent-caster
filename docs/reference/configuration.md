# Configuration

Project configuration lives in `roles.toml`.

## Example

```toml
[project]
roles_dir = ".agents/roles"

[targets.claude]

[targets.claude.model_map]
reasoning = "claude-opus-4-6"
coding = "claude-sonnet-4"
```

## Project keys

- `roles_dir`: role definitions directory in the **source** repository (used by `find_roles_dir` during `add`)

## Install scopes

- project scope is the default install target, always `.agents/roles`
- user scope uses `~/.agents/roles` and is selected with `-g` or `--global`
- render operates on the installed scope; `add` only renders roles from the scope that was just installed
- list and remove operate on one scope at a time: default project, `-g` for user

## Local sources

- local installs use `role-forge add ./path` or `role-forge add /absolute/path`
- local sources are copied into the selected install scope; symlink installs are not supported
- if source and destination are the same file, the copy is skipped

## Hygiene commands

- `doctor` reports unmanaged files in the selected roles directory
- unmanaged files are non-`.md` files or `.md` files that fail role parsing
- `clean` removes unmanaged files and supports `--dry-run`, `-y`, and `-g`

## Target keys

- `enabled`: target toggle, default `true`
- `model_map`: logical model tiers to target-specific identifiers
- `capability_map`: project-defined capability expansion for adapters that support it

## Source repository discovery

When reading a source repository, `role-forge` resolves role files in this order:

1. `roles.toml` with `project.roles_dir`
2. `.agents/roles/` directory
3. fallback `roles/`

## Output layout

Each adapter defines its own output layout:

- Claude and Copilot default to `namespace` (e.g. `directors__bug-fix.md`)
- Other adapters default to `preserve` (e.g. `directors/bug-fix.md`)

`role-forge` validates layout collisions before writing files.
