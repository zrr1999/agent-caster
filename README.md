# agent-caster

Install canonical role definitions and render them across coding agent tools.

## Why

AI coding agent 工具（Claude Code、OpenCode、Cursor、Codex、Windsurf、Aider...）各有自己的 agent 配置格式。团队维护多工具 agent 定义面临配置碎片化、工具锁定和安全配置重复维护等问题。

**agent-caster** 让你从 GitHub 安装可复用的 role definitions，并把同一份 canonical source render 成各工具需要的格式。

| 能力 | 支持 |
|------|:---:|
| 从 GitHub 安装 role definitions | ✅ |
| 多工具输出（Claude Code / OpenCode / ...） | ✅ |
| Model tier 抽象（reasoning / coding） | ✅ |
| Capability group 展开 | ✅ |
| 权限 / 委派建模 | ✅ |
| 第三方 adapter 扩展 | ✅ |

## Installation

```bash
uv tool install agent-caster
```

## Quick Start

```bash
# 从 GitHub 安装 role definitions（交互式选择）
agent-caster add PFCCLab/precision-agents

# 跳过交互，安装全部并自动 cast
agent-caster add PFCCLab/precision-agents -y

# 安装到全局
agent-caster add PFCCLab/precision-agents -y --global

# 从本地路径安装
agent-caster add ./my-agents

# 指定 render 目标
agent-caster add PFCCLab/precision-agents -y --target claude

# 列出已安装的 agent
agent-caster list

# 重新 render 到平台格式
agent-caster render --target claude

# 更新已安装的 agent
agent-caster update PFCCLab/precision-agents

# 移除 agent
agent-caster remove explorer
```

## Canonical Role Definition

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

`read-code` / `write-code` 仍然兼容，但新的 canonical capability 名称推荐使用 `read` / `write`。
```

## Source Repo Convention

agent-caster 从源仓库中查找 role definitions：

1. 有 `roles.toml` 且指定 `roles_dir`（或兼容旧字段 `agents_dir`）→ 使用该路径
2. 否则有 `refit.toml` 且指定 `roles_dir` / `agents_dir` → 使用该路径
2. 否则 → 默认 `roles/*.md`

`roles.toml` 的 target 现在也支持 `output_layout = "preserve" | "namespace" | "flatten"`，
可用于保留嵌套 `roles/` 的路径语义或显式启用扁平化输出。

## Supported Tools

| Tool | Adapter | Output |
|------|---------|--------|
| Claude Code | `claude` | `.claude/agents/*.md` |
| OpenCode | `opencode` | `.opencode/agents/*.md` |
| Cursor | `cursor` | `.cursor/agents/*.mdc` |

更多工具适配器开发中。

## Terminology

- `role definition`: 平台无关的 canonical source
- `render`: 将 canonical source 输出到某个工具的目标格式
- `adapter`: 一个具体工具的 render backend

CLI 中 `cast` 仍可用，但 `render` 是推荐名称。

## Development

```bash
just install   # 安装依赖
just ci        # 完整 CI 流程（format + lint + check + test）
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

MIT
