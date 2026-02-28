# agent-caster: AI Coding Agent 跨平台定义编译器

> Write once, deploy everywhere.

## 1. 背景与动机

### 1.1 问题

AI coding agent 平台快速增长（Claude Code、Cursor、OpenCode、Codex、Windsurf、Aider、Gemini CLI、Kiro...），每个平台有自己的 agent/规则配置格式。团队维护多平台 agent 定义面临：

- **配置碎片化**：同一个 agent 的定义散落在 `.opencode/agents/`、`.cursor/rules/`、`.claude/` 等多处，内容重复且容易漂移
- **平台锁定**：agent 定义和特定平台格式耦合，迁移成本高
- **权限安全**：bash 命令白名单、工具权限、子 agent 委派等安全配置需要在每个平台独立维护

### 1.2 现有方案的不足

经过调研（Rulix、PRPM、Rulesify、Vibe CLI 等），现有开源工具全部聚焦在 **规则/编码规范的跨平台同步**，没有任何项目覆盖以下能力：

| 能力 | Rulix | PRPM | Rulesify | agent-caster |
|------|:---:|:---:|:---:|:---:|
| 单一真实来源 | Yes | Yes | Yes | **Yes** |
| 多平台输出 | 5 | 13+ | 4 | **可扩展** |
| Model tier 抽象 | No | No | No | **Yes** |
| Capability group 展开 | No | No | No | **Yes** |
| 权限/委派建模 | No | No | No | **Yes** |
| Agent 角色定义 | No | No | No | **Yes** |

### 1.3 定位

**agent-caster** 是一个 AI coding agent 定义的 **跨平台编译器 + 包管理器**：

- **编译器维度**：将抽象的 canonical agent 定义编译为各平台的具体配置格式
- **包管理维度**：从 GitHub 仓库安装/更新可复用的 agent 定义

类比：

| 领域 | 类比工具 | agent-caster |
|------|----------|-------------|
| 容器 | Dockerfile → docker build | `.agents/roles/*.md` → `agent-caster compile` |
| 前端 | TypeScript → tsc → JavaScript | Canonical agent def → adapter → Platform config |
| 包管理 | `bunx skills add` | `agent-caster add github:org/repo` |

---

## 2. 核心概念

### 2.1 术语

| 术语 | 含义 |
|------|------|
| **Canonical definition** | 平台无关的 agent 定义文件（`.agents/roles/*.md`），是唯一的真实来源 |
| **Adapter** | 编译器后端，将 canonical 定义转换为特定平台的配置格式 |
| **Target** | 编译目标平台（opencode、cursor、claude 等） |
| **Capability group** | 抽象能力组（如 `read-code`），由 adapter 展开为平台特定的工具标志 |
| **Model tier** | 抽象模型层级（`reasoning` / `coding`），由 adapter 映射为具体模型 ID |
| **Source** | 远程 agent 定义来源（GitHub 仓库） |

### 2.2 设计原则

1. **单一真实来源**：所有 agent 配置从 `.agents/roles/` 生成，禁止手动编辑生成产物
2. **抽象优于具体**：canonical 定义使用 `tier: reasoning` 而非 `model: claude-opus-4.6`
3. **安全默认**：deny-by-default 的权限模型，bash 白名单、委派白名单显式声明
4. **渐进式采用**：可以只用编译器，不用包管理；可以只适配一个平台
5. **可扩展**：adapter 通过 Python entry_points 注册，第三方可以开发新平台适配器

---

## 3. 项目结构

### 3.1 使用 agent-caster 的项目目录

```
my-project/
├── refit.toml                      # 工具配置：目标平台、模型映射、远程来源
├── .agents/
│   └── roles/                      # Canonical agent 定义（source of truth）
│       ├── explorer.md             #   YAML frontmatter + prompt body
│       ├── learner.md
│       ├── aligner.md
│       ├── diagnostician.md
│       ├── validator.md
│       ├── reviewer.md
│       └── precision-alignment.md  #   primary agent
│
│   # ── 以下为生成产物（应在 .gitignore 中忽略）──
│
├── .opencode/                      # ← compile --target opencode 生成
│   ├── agents/*.md
│   └── opencode.json
├── .cursor/                        # ← compile --target cursor 生成
│   └── rules/*.mdc
└── .claude/                        # ← compile --target claude 生成
    └── agents/*.md
```

### 3.2 agent-caster 自身的包结构

```
agent-caster/
├── pyproject.toml
├── src/
│   └── agent_caster/
│       ├── __init__.py
│       ├── cli.py                  # CLI 入口（click/typer）
│       ├── config.py               # refit.toml 解析
│       ├── models.py               # AgentDef, TargetConfig 等数据模型
│       ├── loader.py               # 加载 .agents/roles/*.md
│       ├── compiler.py             # 编译调度器
│       ├── package.py              # 包管理（add/update）
│       └── adapters/
│           ├── base.py             # Adapter 基类/协议
│           ├── opencode.py         # OpenCode 适配器
│           ├── claude.py           # Claude Code 适配器
│           └── cursor.py           # Cursor 适配器
└── tests/
```

---

## 4. Canonical Agent 定义格式

### 4.1 文件格式

YAML frontmatter + Markdown body，存放于 `.agents/roles/{name}.md`：

```markdown
---
name: explorer
description: >
  Code Explorer. Traces API execution paths from high-level API
  to CUDA/CPU kernels. Read-only; no code changes.
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
      - "bunx repomix@latest*"

prompt_file: ./prompts/explorer-detail.md   # 可选：外部 prompt 文件引用
---

# Explorer

Trace API execution paths from Python API down to CUDA/CPU kernels.
Produce a structured report for the Orchestrator.

## Required Inputs
- **Codebase path**: `paddle_path` or `pytorch_path`
- **Target**: `api_name` (e.g. `pow`)

## Constraints
- Read-only: no code changes, no spawning agents.
- One codebase per invocation.
```

### 4.2 Frontmatter Schema

```yaml
# 必填
name: string                # agent 唯一标识（用于文件名和引用）
description: string         # 简要描述
role: primary | subagent    # 角色

# 模型配置
model:
  tier: reasoning | coding  # 抽象模型层级
  temperature: float        # 0.0 - 1.0

# 可选
skills: list[string]        # 关联的 skills 名称
prompt_file: string         # 外部 prompt 文件路径（相对于当前文件）

# 能力声明
capabilities:
  - read-code               # 预定义能力组（string）
  - write-code
  - web-access
  - bash:                   # 结构化能力：bash 命令白名单
      - "pattern*"
  - delegate:               # 结构化能力：可委派的子 agent 列表
      - agent-name
```

### 4.3 内置能力组

| 能力组 | 语义 | 典型展开 |
|--------|------|----------|
| `read-code` | 读取代码/文件 | read, glob, grep |
| `write-code` | 编写/修改代码 | write, edit |
| `write-report` | 写入报告/文档 | write |
| `web-access` | 完整 web 访问 | webfetch, websearch |
| `web-read` | 只读 web 访问 | webfetch |

> 注意：具体展开结果因平台而异。`read-code` 在 OpenCode 中展开为 `{read: true, glob: true, grep: true}`，在 Cursor 中可能映射为不同的工具名。

### 4.4 用户自定义能力组

在 `refit.toml` 中扩展：

```toml
[capability_groups.context7]
description = "Context7 MCP tool access"

[capability_groups.gh-search]
description = "GitHub code search"
```

adapter 负责解释自定义能力组在对应平台的含义。

---

## 5. 配置文件：`refit.toml`

```toml
[project]
agents_dir = ".agents/roles"   # canonical 定义目录（默认值）

# ── 目标平台配置 ──

[targets.opencode]
enabled = true
output_dir = "."               # 在项目根目录输出 .opencode/ 和 opencode.json

[targets.opencode.model_map]
reasoning = "github-copilot/claude-opus-4.6"
coding = "github-copilot/gpt-5.2-codex"

[targets.opencode.capability_map]
# 覆盖/扩展默认的能力组映射
context7 = { context7 = true }
gh-search = { gh_grep = true }

[targets.claude]
enabled = true
output_dir = "."

[targets.claude.model_map]
reasoning = "claude-opus-4.6"
coding = "claude-sonnet-4"

[targets.cursor]
enabled = false                # 暂不启用
output_dir = "."

[targets.cursor.model_map]
reasoning = "claude-opus-4.6"
coding = "gpt-5.2-codex"

# ── 远程来源追踪（由 `add` 命令自动维护）──

[[sources]]
repo = "github:PFCCLab/precision-agents"
ref = "main"
agents = ["explorer", "learner"]
installed_at = "2026-02-27T10:00:00Z"
```

---

## 6. CLI 命令详细设计

### 6.1 `agent-caster init`

初始化项目。

```bash
uvx agent-caster init
```

行为：
1. 创建 `.agents/roles/` 目录
2. 生成默认 `refit.toml`（交互式选择目标平台）
3. 提示将生成目录（`.opencode/`、`.cursor/` 等）加入 `.gitignore`

### 6.2 `agent-caster compile`

编译 canonical 定义到目标平台。

```bash
uvx agent-caster compile                     # 编译到所有 enabled 的目标
uvx agent-caster compile --target opencode   # 只编译到 opencode
uvx agent-caster compile --target opencode --target claude  # 多目标
uvx agent-caster compile --dry-run           # 预览输出，不写入文件
uvx agent-caster compile --diff              # 显示与当前文件的差异
```

行为：
1. 加载 `refit.toml` 配置
2. 加载 `.agents/roles/*.md` 中所有 canonical 定义
3. 对每个 enabled 的目标平台，调用对应 adapter 的 `compile()` 方法
4. 写入生成文件（或 dry-run 打印）

### 6.3 `agent-caster add`

从远程 GitHub 仓库添加 agent 定义。

```bash
uvx agent-caster add github:PFCCLab/precision-agents
uvx agent-caster add github:PFCCLab/precision-agents --agents "explorer,learner"
uvx agent-caster add github:PFCCLab/precision-agents --ref v1.0
uvx agent-caster add ./path/to/local/agents  # 本地路径
```

行为：
1. 解析来源 URL（`github:owner/repo` → `https://github.com/owner/repo`）
2. 使用 `git archive` 或 sparse checkout 获取仓库中的 `.agents/roles/` 目录
3. 如果指定 `--agents`，只复制选中的 agent 定义文件
4. 复制到本地 `.agents/roles/`
5. 在 `refit.toml` 的 `[[sources]]` 中记录来源信息
6. 自动执行 `compile`

冲突处理：如果本地已有同名 agent，提示用户选择覆盖或跳过。

### 6.4 `agent-caster update`

更新已添加的远程 agent 定义。

```bash
uvx agent-caster update                              # 更新所有来源
uvx agent-caster update github:PFCCLab/precision-agents  # 更新指定来源
```

行为：
1. 遍历 `refit.toml` 中的 `[[sources]]`
2. 对每个来源，re-fetch 最新版本
3. 比较并更新本地 `.agents/roles/` 中对应的文件
4. 显示变更摘要
5. 自动执行 `compile`

### 6.5 `agent-caster list`

列出当前项目的所有 agent 定义。

```bash
uvx agent-caster list
```

输出示例：

```
AGENT                   ROLE      TIER       SOURCE
explorer                subagent  reasoning  github:PFCCLab/precision-agents
learner                 subagent  reasoning  github:PFCCLab/precision-agents
aligner                 subagent  coding     local
precision-alignment     primary   reasoning  local
```

### 6.6 `agent-caster inspect`

查看某个 agent 的详细信息和各平台编译结果预览。

```bash
uvx agent-caster inspect explorer
```

输出示例：

```
Agent: explorer
  Role: subagent
  Tier: reasoning (temperature: 0.05)
  Skills: repomix-explorer
  Capabilities: read-code, write-report, web-read, bash(2 patterns)
  Source: github:PFCCLab/precision-agents@main

  Compiled for opencode:
    Model: github-copilot/claude-opus-4.6
    Tools: read, glob, grep, write, webfetch, bash
    Bash whitelist: npx repomix@latest*, bunx repomix@latest*

  Compiled for claude:
    Model: claude-opus-4.6
    Tools: Read, Glob, Grep, Write, WebFetch, Bash
```

---

## 7. 适配器架构

### 7.1 Adapter Protocol

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass
class OutputFile:
    """一个待写入的输出文件。"""
    path: str       # 相对于 output_dir 的路径
    content: str    # 文件内容

@dataclass
class AgentDef:
    """解析后的 canonical agent 定义。"""
    name: str
    description: str
    role: str                       # "primary" | "subagent"
    model_tier: str                 # "reasoning" | "coding"
    temperature: float
    skills: list[str]
    capabilities: list[str]         # 简单能力组名
    bash_patterns: list[str]        # bash 命令白名单
    delegates: list[str]            # 可委派的子 agent
    prompt_content: str             # prompt 正文
    prompt_file: str | None         # 外部 prompt 文件路径
    source_file: str                # 源文件名

class Adapter(Protocol):
    """适配器协议。所有 adapter 必须实现此接口。"""

    name: str

    def compile(
        self,
        agents: list[AgentDef],
        config: TargetConfig,
    ) -> list[OutputFile]:
        """将 canonical agent 定义编译为平台特定的配置文件。"""
        ...
```

### 7.2 内置适配器

#### OpenCode Adapter

输出：
- `opencode.json` — primary agent 配置
- `.opencode/agents/{name}.md` — subagent 定义（YAML frontmatter + prompt）

编译逻辑：从现有 `adapters/opencode/generate.py` 迁移。

#### Claude Code Adapter

输出：
- `CLAUDE.md` — 包含 primary agent 的指令
- `.claude/agents/{name}.md` — subagent 定义

映射：
- `read-code` → Read, Glob, Grep tools
- `write-code` → Write, Edit tools
- `bash` → Bash tool with allowedCommands
- `delegate` → Task tool with allowedAgents

#### Cursor Adapter

输出：
- `.cursor/rules/{name}.mdc` — MDC 格式的规则文件

映射：
- Cursor 使用 MDC frontmatter（`description`、`globs`、`alwaysApply`）
- capabilities 映射为规则中的指令文本

### 7.3 第三方 Adapter 扩展

通过 Python entry_points 注册：

```toml
# 第三方 adapter 包的 pyproject.toml
[project.entry-points."agent_caster.adapters"]
windsurf = "agent_caster_windsurf:WindsurfAdapter"
```

agent-caster 通过 `importlib.metadata.entry_points()` 发现所有注册的 adapter。

---

## 8. 包管理设计

### 8.1 Git as Package

核心思路：**GitHub 仓库就是包，`.agents/roles/` 目录就是包的内容。**

包解析流程：

```
github:PFCCLab/precision-agents
    │
    ▼
https://github.com/PFCCLab/precision-agents
    │
    ▼ git archive / sparse checkout
    │
    ▼ 查找 .agents/roles/ 目录
    │
    ▼ 复制到本地 .agents/roles/
    │
    ▼ 记录到 refit.toml [[sources]]
```

### 8.2 仓库约定

要作为 agent-caster 包使用，仓库需要：

1. 在根目录或 `.agents/roles/` 下存放 canonical agent 定义文件（`*.md` 格式）
2. 查找优先级：`.agents/roles/` > `agents/` > 根目录 `*.md`

### 8.3 版本控制

- 使用 git ref（branch/tag/commit）作为版本标识
- `--ref` 参数指定版本
- 默认使用默认分支（通常为 `main`）

---

## 9. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| CLI 框架 | `click` | 成熟、广泛使用、比 typer 更轻量 |
| 配置解析 | `tomli` (Python 3.11+ 内置 `tomllib`) | TOML 是 Python 生态标准 |
| YAML 解析 | `pyyaml` | frontmatter 解析 |
| Git 操作 | subprocess 调用 `git` | 避免引入 gitpython 等重依赖 |
| 打包 | `hatchling` | 现代 Python 打包标准 |
| 测试 | `pytest` | Python 标准 |

### 依赖最小化

核心依赖仅 3 个：
- `click` — CLI
- `pyyaml` — YAML frontmatter
- `tomli` — TOML 配置（Python < 3.11）

---

## 10. 发布与使用

### 10.1 PyPI 发布

```
包名：agent-caster
入口：agent-caster (console_scripts)
```

### 10.2 使用方式

```bash
# 零安装运行（推荐）
uvx agent-caster init
uvx agent-caster compile

# 或全局安装
pip install agent-caster
agent-caster compile

# 或项目依赖
uv add --dev agent-caster
```

---

## 11. 实现路线图

### Phase 1: MVP（v0.1）

- [ ] 核心数据模型（AgentDef, TargetConfig）
- [ ] `.agents/roles/*.md` 加载器（YAML frontmatter 解析）
- [ ] `refit.toml` 配置解析
- [ ] OpenCode adapter（从现有 generate.py 迁移）
- [ ] Claude Code adapter
- [ ] CLI: `init`, `compile`, `compile --dry-run`, `list`
- [ ] PyPI 发布 + uvx 支持

### Phase 2: 包管理（v0.2）

- [ ] CLI: `add`, `update`, `inspect`
- [ ] GitHub 仓库解析和 sparse checkout
- [ ] `[[sources]]` 来源追踪
- [ ] Cursor adapter

### Phase 3: 生态（v0.3+）

- [ ] entry_points adapter 扩展机制
- [ ] `agent-caster validate` — 校验 canonical 定义的合法性
- [ ] `agent-caster diff` — 查看生成产物与当前文件的差异
- [ ] 更多内置 adapter（Aider、Windsurf、Codex 等）
- [ ] 可选的轻量 registry 索引

---

## 12. 从现有适配层迁移

现有项目 `precision-alignment-agent` 的迁移路径：

```
# 当前结构
agents/                    →  .agents/roles/
adapters/opencode/         →  由 agent-caster 内置 opencode adapter 替代

# 迁移步骤
1. uvx agent-caster init
2. mv agents/*.md .agents/roles/
3. 配置 refit.toml（model_map 等）
4. uvx agent-caster compile --target opencode
5. 验证生成结果与原有一致
6. 删除 adapters/ 目录
```

---

## 13. 竞品对比总结

| 特性 | Rulix | PRPM | Rulesify | **agent-caster** |
|------|:---:|:---:|:---:|:---:|
| **定位** | 规则同步 | 规则市场 | 规则同步 | **Agent 编译器** |
| **管理对象** | 编码规范 | 规则/提示 | 编码规范 | **Agent 完整定义** |
| **Model tier 抽象** | - | - | - | **Yes** |
| **Capability 展开** | - | - | - | **Yes** |
| **权限建模** | - | - | - | **Yes** |
| **Agent 角色系统** | - | - | - | **Yes** |
| **包管理** | - | npm-like | - | **Git as Package** |
| **实现语言** | TypeScript | TypeScript | Rust | **Python** |
| **运行方式** | npx | npm | cargo | **uvx** |
