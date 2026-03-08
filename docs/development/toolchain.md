# Toolchain

## Goals

The development toolchain is designed to keep formatting, linting, type checks, tests, and documentation generation consistent across local work and CI.

## Primary commands

```bash
just format
just lint
just check
just test
just docs-build
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

The historical toolchain migration notes remain in `docs/plans/2026-03-02-toolchain-upgrade-design.md` for reference.
