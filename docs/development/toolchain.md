# Toolchain

## Goals

The development toolchain is designed to keep formatting, linting, type checks, tests, and documentation generation consistent across local work and CI.

## Primary commands

```bash
just format
just lint
just check
just test
uv run zensical build
just ci
```

## Current stack

- dependency management: `uv`
- command runner: `just`
- formatting and linting: `ruff`
- type checking: `ty`
- tests: `pytest`
- documentation: `zensical`

## CI expectations

- static checks run in GitHub Actions
- tests run in GitHub Actions
- documentation is built in CI to catch broken navigation or invalid content before merge

## Conventions

- **Ruff**: `from __future__ import annotations` required; isort per-file-ignores for `__init__.py` and `tests/**` (I002); PGH003 and B008 allowed where appropriate.
- **Type checking**: `ty` checks `src/` only.
- **Just**: `install` runs `uv sync --all-groups`; `check` runs `uvx ty check src/`.
- **Publish**: tag-triggered workflow for PyPI.
