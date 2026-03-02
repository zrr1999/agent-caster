# agent-caster CLI 重设计：从编译器到包管理器

> 2026-03-02

## 1. 定位转变

agent-caster 从 **编译器** 转变为 **包管理器 + 编译器**：

- **核心动作**：`add` — 从 GitHub 拉取 agent 定义到本地
- **辅助动作**：`cast` — 将 canonical 定义转换为平台特定格式（桥接过渡期）
- **标准推广**：`.agents/roles/` 是 canonical agent 定义标准，未来各平台应直接支持

## 2. CLI 命令体系

```bash
# 核心
agent-caster add <org/repo[@ref]|local-path> [-y] [-g] [-t target,...]
agent-caster update <org/repo>
agent-caster list
agent-caster remove <agent-name>

# 辅助
agent-caster cast [-t target,...]
agent-caster --version
```

### 2.1 `add` 流程

```
agent-caster add PFCCLab/precision-agents
```

```
⠋ Fetching PFCCLab/precision-agents...
✓ Found 5 agents in PFCCLab/precision-agents

  Available agents:
  ┌───┬─────────────────────┬──────────┬───────────┐
  │   │ Agent               │ Role     │ Tier      │
  ├───┼─────────────────────┼──────────┼───────────┤
  │ ✓ │ explorer            │ subagent │ reasoning │
  │ ✓ │ learner             │ subagent │ reasoning │
  │ ✓ │ aligner             │ subagent │ coding    │
  │ ✓ │ reviewer            │ subagent │ reasoning │
  │ ✓ │ precision-alignment │ primary  │ reasoning │
  └───┴─────────────────────┴──────────┴───────────┘

? Select agents to install: (space to toggle, enter to confirm)

? Install to:
  ● Project (./.agents/roles/)
  ○ Global  (~/.agents/roles/)

✓ Installed 5 agents to .agents/roles/

? Detected platforms in project: claude, opencode
  Cast agents to these platforms? [Y/n]

✓ Cast 5 agents → .claude/agents/
✓ Cast 5 agents → .opencode/agents/

Done! 5 agents installed and cast to 2 platforms.
```

- `-y`：跳过所有交互（全选 agent，project-level，自动 cast 到检测到的平台）
- `-g` / `--global`：安装到 `~/.agents/roles/`，不自动 cast
- `-t` / `--target`：显式指定 cast 目标，跳过检测

### 2.2 `update`

```bash
agent-caster update PFCCLab/precision-agents    # re-fetch 并重新安装
```

从 `~/.config/agent-caster/repos/` 缓存得知之前 clone 过的 repo，git pull 后重新安装。

### 2.3 `list`

列出当前项目 `.agents/roles/` 中的所有 agent 定义。

### 2.4 `remove`

删除 `.agents/roles/` 中指定的 agent 文件。提示用户手动清理平台产物或重新 `cast`。

### 2.5 `cast`

```bash
agent-caster cast                      # 读 .agents/roles/，cast 到检测到的平台
agent-caster cast --target claude      # 只 cast 到 claude
```

独立于 `add`，用于重新生成或切换平台。

## 3. 来源解析

### 3.1 格式

```
PFCCLab/precision-agents                → github.com/PFCCLab/precision-agents
PFCCLab/precision-agents@v1.0           → github.com/PFCCLab/precision-agents (ref: v1.0)
./path/to/local                         → 本地路径
/absolute/path/to/local                 → 本地路径
```

解析规则：
1. 以 `./` 或 `/` 开头 → 本地路径
2. 包含 `/` → `org/repo[@ref]`，映射到 GitHub

### 3.2 源 repo 约定

查找 agent 定义：
1. 有 `refit.toml` 且指定 `agents_dir` → 用该路径
2. 否则 → 默认 `roles/*.md`

### 3.3 工具缓存

```
~/.config/agent-caster/
  repos/                                  # clone 缓存
    PFCCLab/precision-agents/
    zrr1999/my-agents/
```

无 lockfile。缓存仅用于加速 fetch。

## 4. 安装目标

| 模式 | Agent 定义位置 |
|------|--------------|
| Project（默认） | `./.agents/roles/` |
| Global（`--global`） | `~/.agents/roles/` |

## 5. Cast 联动

### 5.1 平台检测

| 条件 | 目标 adapter |
|------|-------------|
| 存在 `.claude/` 或 `CLAUDE.md` | claude |
| 存在 `.opencode/` 或 `opencode.json` | opencode |
| 都没检测到 | 交互询问或 `--target` 指定 |

### 5.2 Model map

去掉用户侧 `refit.toml` 后，model_map 来源：
1. 源 repo `refit.toml` 中的 model_map（优先）
2. adapter 内置默认值

```python
# claude adapter 默认
{"reasoning": "claude-opus-4-6", "coding": "claude-sonnet-4"}

# opencode adapter 默认
{"reasoning": "anthropic:claude-opus-4-6", "coding": "anthropic:claude-sonnet-4"}
```

## 6. 代码结构

```
src/agent_caster/
├── cli.py              # CLI 入口：add / update / list / remove / cast
├── config.py           # refit.toml 解析（读源 repo 的配置）
├── loader.py           # roles/*.md 加载
├── models.py           # 数据模型
├── groups.py           # capability groups
├── caster.py           # cast 管线
├── registry.py         # 新增：来源解析、clone/fetch、缓存管理
├── platform.py         # 新增：平台检测逻辑
└── adapters/
    ├── base.py         # Adapter Protocol
    ├── claude.py       # Claude adapter
    └── opencode.py     # OpenCode adapter
```

主要变更：
- **新增 `registry.py`**：来源解析（`org/repo@ref`）、git clone/fetch、缓存管理
- **新增 `platform.py`**：检测项目中已有平台目录
- **改造 `cli.py`**：去掉 `init`，新增 `add` / `update` / `remove`，保留 `cast` 和 `list`
- **简化 `caster.py`**：cast 不再依赖用户 refit.toml，model_map 由 adapter 默认值 + 源 repo 配置提供
- **`config.py`**：只读源 repo 的 refit.toml

## 7. 边界情况

| 场景 | 行为 |
|------|------|
| 本地已有同名 agent | 交互提示覆盖/跳过，`-y` 默认覆盖 |
| 源 repo 无 agent 定义 | 报错：`No agent definitions found` |
| git 未安装 | 报错：`git is required` |
| GitHub 仓库不存在 | 报错：`Repository not found: PFCCLab/xxx` |
| `--global` + `--target` | 允许：安装到全局，但在当前项目 cast |
| `cast` 时无 `.agents/roles/` | 报错提示先 `add` |
| `remove` 的 agent 被平台引用 | 只删 canonical 定义，提示清理或重新 `cast` |

## 8. YAGNI

- 不做 agent 依赖解析
- 不做 registry 索引服务
- 不做 `init`（`add` 自动创建目录）
- 不做 `inspect`（`list` 足够）
- 不做 `refit.lock`
