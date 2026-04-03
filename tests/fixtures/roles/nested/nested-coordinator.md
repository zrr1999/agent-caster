---
name: nested-coordinator
description: Nested test coordinator for recursive fixture coverage.
role: primary

model:
  tier: reasoning
  temperature: 0.2

capabilities:
  - read
  - write
  - delegate:
      - nested/feature-lead
      - nested/support/research-helper

hierarchy:
  level: L1
  class: main
  scheduled: true
  callable: true
  max_delegate_depth: 2
  allowed_children:
    - nested/feature-lead
    - nested/support/research-helper
---

# Nested Coordinator

Coordinates the nested test roles.
