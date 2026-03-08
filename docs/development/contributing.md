# Contributing

## Development environment

```bash
git clone https://github.com/zrr1999/role-forge.git
cd role-forge
just install
just ci
```

## Expectations

- keep changes focused
- add or update tests for behavioral changes
- avoid mixing unrelated refactors into one PR
- run `just ci` before submitting

## Commit message format

```text
<emoji> <type>(<scope>): <subject>
```

Recommended `type` values:

| emoji | type | use |
| --- | --- | --- |
| ✨ | `feat` | new feature |
| 🐛 | `fix` | bug fix |
| ♻️ | `refactor` | structural cleanup without behavior change |
| 📝 | `docs` | documentation updates |
| ✅ | `test` | tests |
| 🔧 | `chore` | tooling or CI |
| 🔥 | `remove` | deletions |

## Adding an adapter

1. create a module in `src/role_forge/adapters/`
2. inherit from `BaseAdapter`
3. register it in `src/role_forge/adapters/__init__.py` or via entry point
4. add snapshot or behavior tests under `tests/`
