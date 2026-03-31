---
name: feature-lead
description: Nested lead fixture that exercises the `all` capability.
role: subagent

model:
  tier: coding
  temperature: 0.1

capabilities:
  - all
  - delegate:
      - nested/workers/impl-worker
      - nested/workers/qa-worker

hierarchy:
  level: L2
  class: lead
  scheduled: false
  callable: true
  max_delegate_depth: 1
  allowed_children:
    - nested/workers/impl-worker
    - nested/workers/qa-worker
---

# Feature Lead

Exercises full capability expansion in a nested fixture.
