---
name: impl-worker
description: Nested implementation worker fixture.
role: subagent

model:
  tier: coding
  temperature: 0.1

capabilities:
  - read
  - write

hierarchy:
  level: L3
  class: leaf
  scheduled: false
  callable: true
  max_delegate_depth: 0
---

# Impl Worker

Implements changes in nested fixture tests.
