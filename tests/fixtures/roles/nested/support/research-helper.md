---
name: research-helper
description: Nested research helper fixture.
role: subagent

model:
  tier: reasoning
  temperature: 0.05

capabilities:
  - read
  - web-access

hierarchy:
  level: L3
  class: leaf
  scheduled: false
  callable: true
  max_delegate_depth: 0
---

# Research Helper

Collects supporting context for nested fixture tests.
