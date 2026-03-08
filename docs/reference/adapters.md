# Adapters

Built-in adapters render the same canonical roles into tool-specific outputs.

## Built-in targets

| Target | Output path | Notes |
| --- | --- | --- |
| `claude` | `.claude/agents/*.md` | supports model mapping, tool allow-lists, and delegation |
| `opencode` | `.opencode/agents/*.md` | supports model mapping, permissions, bash allow-lists, and delegation |
| `cursor` | `.cursor/agents/*.mdc` | ignores per-role model selection |
| `windsurf` | `.windsurf/rules/*.md` | emits rule files with `model_decision` trigger |

## Shared adapter model

All adapters now share one render pipeline:

- validate hierarchy and delegation
- validate output layout uniqueness
- derive target delegate ids from the selected layout
- compute the final output path
- render one file per role

That keeps platform-specific code focused on frontmatter and permissions instead of repeating filesystem and validation logic.

Adapters also consume the same centralized capability expansion step. Built-in capability groups, aliases, bash policies, delegation metadata, and `all` are normalized before target-specific rendering begins.

## Third-party adapters

Register adapters through the `role_forge.adapters` entry point group.

```toml
[project.entry-points."role_forge.adapters"]
my-target = "my_package.adapters:MyAdapter"
```

The adapter class should inherit `BaseAdapter` from `role_forge.adapters.base` and implement `render_agent`.
