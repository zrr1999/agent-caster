# Canonical Role Definition

`role-forge` treats Markdown files with YAML frontmatter as the canonical role source.

## Layout

Store role files under `roles/` in a source repo, or under `.agents/roles/` after installation.

```text
roles/
  explorer.md
  l2/lead.md
  l3/worker.md
```

Nested paths are meaningful. They become canonical ids such as `l2/lead` and are preserved or transformed by target `output_layout`.

## Example

```markdown
---
name: explorer
description: Code Explorer. Reads and analyzes source code.
role: subagent

model:
  tier: reasoning
  temperature: 0.05

skills:
  - repomix-explorer

capabilities:
  - read
  - write-report
  - web-read
  - bash:
      - "npx repomix@latest*"

level: L3
class: leaf
callable: true
scheduled: false
max_delegate_depth: 0
---

# Explorer

Read-only code exploration role. Traces execution paths and produces reports.
```

## Core fields

- `name`: display name inside target tools
- `description`: short target-facing summary
- `role`: `primary` or `subagent`
- `model.tier`: logical tier resolved through target `model_map`
- `skills`: target-specific skill references preserved when supported
- `capabilities`: abstract tool groups, bash policies, custom flags, or delegation metadata
- `prompt_content`: Markdown body, or external content from `prompt_file`

## Hierarchy and delegation

Hierarchy can be declared either in a nested `hierarchy` object or through top-level compatibility fields.

- `level`: role level used to reject upward delegation
- `class`: semantic role class such as `leaf` or `lead`
- `callable`: whether another role may delegate to it
- `scheduled`: whether the role can run without delegation
- `max_delegate_depth`: longest allowed downstream path
- `allowed_children`: explicit allow-list for delegates

Delegation is expressed in `capabilities`:

```yaml
capabilities:
  - delegate:
      - l3/worker
```

## Capability vocabulary

Capabilities are expanded once into a shared, platform-agnostic model before any adapter renders them. That shared expansion tracks:

- tool ids
- bash allow-lists
- delegate targets
- whether a capability implies full built-in access

Preferred canonical names:

- `read`
- `write`
- `write-report`
- `web-read`
- `web-access`
- `all`
- `safe-bash`
- `readonly-bash`

Legacy aliases such as `read-code` and `write-code` still load, but new definitions should use the canonical names.

`all` expands to every built-in capability the target adapter knows how to express. For adapters with permission maps, it also grants full access for those built-in permissions.

Structured capability entries remain available for cases that need parameters:

```yaml
capabilities:
  - safe-bash
  - bash:
      - "git diff*"
  - delegate:
      - nested/workers/impl-worker
```
