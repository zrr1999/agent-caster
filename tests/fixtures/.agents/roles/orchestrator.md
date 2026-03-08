---
name: orchestrator
description: Orchestrator. Coordinates sub-agents.
role: primary

model:
  tier: reasoning
  temperature: 0.2

skills: []

capabilities:
  - read
  - write
  - bash:
      - "ls*"
      - "cat*"
      - "git status*"
  - delegate:
      - explorer
      - aligner
---

# Orchestrator

Coordinates exploration and alignment sub-agents.
