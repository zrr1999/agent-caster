# Configuration

Project configuration lives in `roles.toml`.

## Example

```toml
[project]
roles_dir = ".agents/roles"

[targets.claude]
output_layout = "preserve"

[targets.claude.model_map]
reasoning = "claude-opus-4-6"
coding = "claude-sonnet-4"
```

## Project keys

- `roles_dir`: canonical role install directory inside the project

## Install scopes

- project scope is the default install target and resolves from `roles.toml` or `.agents/roles`
- user scope uses `~/.agents/roles` and is selected with `-g` or `--global`
- render merges user and project roles by canonical id, with project roles overriding user roles
- list and remove operate on one scope at a time: default project, `-g` for user

## Local sources

- local installs use `role-forge add ./path` or `role-forge add /absolute/path`
- local sources are copied into the selected install scope; symlink installs are not supported

## Hygiene commands

- `doctor` reports unmanaged files in the selected roles directory
- unmanaged files are non-`.md` files or `.md` files that fail role parsing
- `clean` removes unmanaged files and supports `--dry-run`, `-y`, and `-g`

## Target keys

- `enabled`: target toggle, default `true`
- `output_dir`: base output directory, default `.`
- `output_layout`: `preserve`, `namespace`, or `flatten`
- `model_map`: logical model tiers to target-specific identifiers
- `capability_map`: project-defined capability expansion for adapters that support it

## Source repository discovery

When reading a source repository, `role-forge` resolves role files in this order:

1. `roles.toml` with `project.roles_dir`
2. fallback `roles/`

## Output layout modes

- `preserve`: keep nested paths such as `l2/worker`
- `namespace`: flatten path separators into names like `l2__worker`
- `flatten`: use bare `name`, rejecting collisions

`role-forge` validates layout collisions before writing files.
