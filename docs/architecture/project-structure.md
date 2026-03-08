# Project Structure

## Package layout

```text
src/role_forge/
  cli.py
  config.py
  loader.py
  models.py
  groups.py
  registry.py
  platform.py
  topology.py
  adapters/
```

## Module responsibilities

- `cli.py`: user-facing commands such as `add`, `render`, `list`, `remove`, and `update`
- `config.py`: `roles.toml` loading, legacy compatibility, and roles directory resolution
- `loader.py`: canonical role loading from Markdown plus YAML frontmatter
- `models.py`: shared Pydantic models for roles, hierarchy, targets, and outputs
- `groups.py`: capability-group and bash-policy definitions
- `registry.py`: source parsing, fetch/update logic, and source-repository role discovery
- `platform.py`: target platform detection from project markers
- `topology.py`: hierarchy, delegation, and output-layout validation
- `adapters/`: built-in renderers and adapter registry

## Extension model

Third-party targets plug in through the `role_forge.adapters` entry-point group.

Built-in adapters inherit the shared `BaseAdapter`, which centralizes validation-aware rendering flow while leaving formatting details to each target.
