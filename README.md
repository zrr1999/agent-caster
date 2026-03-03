# agent-caster

AI coding agent definition manager. Fetch, install, and cast across tools.

## Why

AI coding agent 工具（Claude Code、OpenCode、Cursor、Codex、Windsurf、Aider...）各有自己的 agent 配置格式。团队维护多工具 agent 定义面临配置碎片化、工具锁定和安全配置重复维护等问题。

**agent-caster** 让你从 GitHub 安装可复用的 agent 定义，并自动适配到各工具的配置格式。

| 能力 | 支持 |
|------|:---:|
| 从 GitHub 安装 agent 定义 | ✅ |
| 多工具输出（Claude Code / OpenCode / ...） | ✅ |
| Model tier 抽象（reasoning / coding） | ✅ |
| Capability group 展开 | ✅ |
| 权限 / 委派建模 | ✅ |

## Installation

```bash
uv tool install agent-caster
```

## Quick Start

```bash
# 从 GitHub 安装 agent 定义（交互式选择）
agent-caster add PFCCLab/precision-agents

# 跳过交互，安装全部并自动 cast
agent-caster add PFCCLab/precision-agents -y

# 安装到全局
agent-caster add PFCCLab/precision-agents -y --global

# 从本地路径安装
agent-caster add ./my-agents

# 指定 cast 目标
agent-caster add PFCCLab/precision-agents -y --target claude

# 列出已安装的 agent
agent-caster list

# 重新 cast 到平台格式
agent-caster cast --target claude

# 更新已安装的 agent
agent-caster update PFCCLab/precision-agents

# 移除 agent
agent-caster remove explorer
```

## Canonical Agent Definition

在 `roles/` 下使用 YAML frontmatter + Markdown 编写 agent 定义：

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
  - read-code
  - write-report
  - web-read
  - bash:
      - "npx repomix@latest*"
---

# Explorer

Read-only code exploration agent. Traces execution paths and produces reports.
```

## Source Repo Convention

agent-caster 从源仓库中查找 agent 定义：

1. 有 `refit.toml` 且指定 `agents_dir` → 使用该路径
2. 否则 → 默认 `roles/*.md`

## Supported Tools

| Tool | Adapter | Output |
|------|---------|--------|
| Claude Code | `claude` | `.claude/agents/*.md` |
| OpenCode | `opencode` | `.opencode/agents/*.md` |
| Cursor | `cursor` | `.cursor/agents/*.mdc` |

更多工具适配器开发中。

## Development

```bash
# 安装依赖
just install

# 格式化
just format

# Lint
just lint

# 类型检查
just check

# 测试
just test

# 测试 + 覆盖率
just cov

# 完整 CI 流程
just ci
```

## License

MIT
