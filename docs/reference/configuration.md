# Configuration

Project configuration lives in `roles.toml`.

## Example

```toml
[project]
roles_dir = "roles"

[targets.claude]

[targets.claude.model_map]
reasoning = "claude-opus-4-6"
coding = "claude-sonnet-4"
```

## Project keys

- `roles_dir`: role definitions directory in the **source** repository (used by `find_roles_dir` during `add`)

## Runtime state

- fetched GitHub repos are cached under `~/.config/role-forge/repos`
- the global cache index lives at `~/.config/role-forge/manifest.json`
- per-project generated-output ownership lives at `.role-forge/outputs.json`
- no role store is maintained; outputs are generated directly from the source repo or repo cache

## Local sources

- local installs use `role-forge add ./path` or `role-forge add /absolute/path`
- local sources are read directly from disk and are not copied into a separate store

## Target keys

- `enabled`: target toggle, default `true`
- `model_map`: logical model tiers to target-specific identifiers
- `capability_map`: project-defined capability expansion for adapters that support it

## Source repository discovery

When reading a source repository, `role-forge` resolves role files in this order:

1. `roles.toml` with `project.roles_dir`
2. fallback `roles/`

## Output layout

Each adapter defines its own output layout:

- Claude and Copilot default to `namespace` (e.g. `directors__bug-fix.md`)
- Other adapters default to `preserve` (e.g. `directors/bug-fix.md`)

`role-forge` validates layout collisions before writing files.
