# Render Pipeline

## Input

The render pipeline starts from canonical role definitions loaded from disk.

Each role includes:

- identity and description
- prompt body
- logical model tier
- capability declarations
- optional hierarchy and delegation metadata

## Validation

Before any target file is written, `role-forge` validates:

- role hierarchy rules
- delegation reachability and allow-lists
- output-layout collisions such as duplicate flattened names

This prevents invalid or ambiguous outputs from being generated.

## Adapter execution

All built-in adapters share the same high-level flow:

1. receive validated `AgentDef` objects
2. derive delegate identifiers for the selected `output_layout`
3. compute target file paths
4. render target-specific frontmatter and prompt content
5. return `OutputFile` objects for writing

That shared pipeline keeps platform-specific code focused on format differences instead of filesystem and validation concerns.

## Output layouts

`role-forge` supports three layout strategies:

- `preserve`: keep nested paths
- `namespace`: flatten paths into namespaced identifiers such as `l2__worker`
- `flatten`: use bare names and reject collisions

## Why this matters

The pipeline separates concerns cleanly:

- canonical roles describe intent
- configuration describes target policy
- adapters describe output format
- the renderer enforces safety before writing files
