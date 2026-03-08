# Deployment

## CI

Documentation is verified in GitHub Actions by `/.github/workflows/ci-docs.yml`.

This workflow is build-only. It does not deploy, does not mutate the Vercel project, and runs with `contents: read` permissions only.

It runs:

```bash
uv sync --dev
just docs-build
```

## Vercel

This repo is configured for Vercel static deployment with `vercel.json`.

Production documentation is served at `https://role-forge.sixbones.dev`.

Configured build pipeline:

- install: `uv sync --dev`
- build: `uv run zensical build`
- output directory: `site`

Once you import the repo into Vercel, it should deploy as a plain static site without extra project-specific commands.

## Branch and domain behavior

The repository default branch is `main`, and the Vercel project is connected to `zrr1999/role-forge`.

With Vercel Git integration:

- pull requests get preview deployments on Vercel preview URLs
- pushes and merges to `main` produce production deployments
- the custom production domain follows the production deployment rather than each PR preview

That means the public docs domain stays aligned with `main`, while PRs can still be reviewed safely in isolated preview environments.

## Safety notes

- GitHub Actions does not hold deployment secrets for docs publishing
- the docs CI job only verifies that documentation builds successfully
- production changes to the public docs site come from Vercel production deployments, not from the PR validation workflow

## Recommended Vercel setup

If Vercel asks for project settings, use:

- Framework Preset: `Other`
- Root Directory: `.`
- Install Command: leave default from `vercel.json`
- Build Command: leave default from `vercel.json`
- Output Directory: leave default from `vercel.json`

## Local verification

```bash
just docs-build
```

That generates the static site into `site/`, which matches the Vercel output directory.
