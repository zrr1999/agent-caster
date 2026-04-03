---
name: qa-worker
description: Nested QA worker fixture.
role: subagent

model:
  tier: reasoning
  temperature: 0.05

capabilities:
  - read
  - safe-bash

hierarchy:
  level: L3
  class: leaf
  scheduled: false
  callable: true
  max_delegate_depth: 0
---

# QA Worker

Verifies nested fixture behavior.
