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

## Target keys

- `enabled`: target toggle, default `true`
- `output_dir`: base output directory, default `.`
- `output_layout`: `preserve`, `namespace`, or `flatten`
- `model_map`: logical model tiers to target-specific identifiers
- `capability_map`: project-defined capability expansion for adapters that support it

## Source repository discovery

When reading a source repository, `role-forge` resolves role files in this order:

1. `roles.toml` with `project.roles_dir` or legacy `project.agents_dir`
2. legacy `refit.toml` with the same keys
3. fallback `roles/`

## Output layout modes

- `preserve`: keep nested paths such as `l2/worker`
- `namespace`: flatten path separators into names like `l2__worker`
- `flatten`: use bare `name`, rejecting collisions

`role-forge` validates layout collisions before writing files.
