# Development

`role-forge` keeps user-facing reference docs in `docs/` and design history in `docs/plans/`.

Formal architecture and system documentation lives in `docs/architecture/`.

## Local workflow

```bash
just install
just ci
```

## Documentation workflow

```bash
uv add --dev zensical
zensical serve
zensical build
```

Use `zensical serve` for preview and keep the README short, with the durable detail moved into this documentation tree.

- Vercel deployment details: `docs/development/deployment.md`
- toolchain details: `docs/development/toolchain.md`
