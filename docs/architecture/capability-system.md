# 能力系统设计文档

## 概述

本文档定义 role-forge 的**能力系统**的完整设计：从 canonical role 中的 `capabilities` 声明，到平台无关的中间表示，再到各 target adapter 的渲染策略。目标是让“能力”具备单一、可验证、可扩展的语义，避免逻辑分散在适配器或配置中。

能力系统负责表达：

- **抽象能力组**：如 `basic`、`read`、`web-access`
- **平台工具展开**：统一工具 ID 与各平台工具名的映射
- **权限语义**：在支持权限的平台上，从能力推导 allow/deny 策略
- **特殊能力**：`bash` / `safe-bash` / `bash: [...]`、`delegate` / `delegate: [...]`、`all`
- **扩展点**：`capability_map` 与第三方 adapter 可复用的公共规则

---

## 目标与范围

### 目标

- **Canonical first**：canonical 中写的 capability 具有明确、平台无关的语义；adapter 只做“翻译”，不重新发明语义。
- **Expand once, render many**：raw capabilities 先归一化为统一中间表示，再交给各 adapter 渲染，避免每个 adapter 从零解释。
- **Tools vs permissions**：显式区分“可用工具集合”与“权限策略”；同一工具在不同平台的权限表达可不同，但 canonical 语义一致。
- **作者体验**：role 作者仍可写简单列表与少量结构化项，无需 target-specific DSL。

### 范围

- 本设计覆盖：capability 的**数据模型**、**词汇表**、**展开算法**、**与 topology 的交互**、**adapter 契约**。
- 不覆盖：hierarchy/topology 系统本身、target config 整体结构、Cursor/Windsurf 的最小输出策略变更。

---

## 现状与问题

### 能力定义分散

- 基础能力组在 `src/role_forge/groups.py`（`TOOL_GROUPS`、`BASH_POLICIES`、`ALL_TOOL_IDS`）。
- `all` 等聚合能力由 `capabilities.py` 的 `expand_capabilities` 理解，但 adapter 仍可能对 `full_access` 做额外解释。
- `TargetConfig.capability_map` 允许 target 注入一套额外映射。

结果：“canonical capability 的真实语义”分布在多处，难以推断和做一致性测试。

### 工具与权限未统一建模

- Claude 关心 `tools`（含 `Bash(...)`、`Task(...)`）。
- OpenCode 关心 `tools` + `permission`（bash/task/edit/read 等）。
- Cursor/Windsurf 基本不表达细粒度 capability。

同一 capability 在不同 adapter 是否“等价”难以形式化。

### 特殊能力语义不够明确

- `safe-bash`、`bash: [...]`、`delegate`、`delegate: [...]`、`all` 既影响工具集合，又可能影响权限与 topology 校验。
- 当前没有单一数据结构同时表达“工具 + bash 策略 + 委派目标 + 是否全量权限”。

### 扩展性不足

- 新增 `basic` 或平台特有 capability alias 时，逻辑容易继续堆在 adapter 或 `capability_map`，导致分叉。

---

## 术语

| 术语 | 含义 |
|------|------|
| **Raw capability** | Role 文件中 `capabilities` 列表的一项：字符串或结构化对象（如 `{ "delegate": [...] }`）。 |
| **Capability value** | 类型为 `str \| dict[str, Any]`，即 raw 的一项。 |
| **Tool id** | 平台无关的语义工具标识，如 `read`、`glob`、`bash`、`task`。 |
| **Capability group** | 映射到若干 tool id 的命名组，如 `read` → `[read, glob, grep]`。 |
| **Expansion** | 将 raw capabilities 列表归一化为 `CapabilitySpec` 的过程。 |
| **CapabilitySpec** | 展开后的中间表示：tool_ids、bash_patterns、delegates、full_access。 |
| **Adapter** | 将 `CapabilitySpec` + `AgentDef` + `TargetConfig` 渲染为平台特定格式的组件。 |
| **capability_map** | `roles.toml` 中 per-target 的扩展映射：别名 → `{ tool_id: bool }`。 |

---

## 设计原则

1. **Canonical first**：canonical 能力语义由能力系统唯一定义；adapter 仅做映射与格式化。
2. **Expand once, render many**：展开在 adapter 之外完成，adapter 只消费 `CapabilitySpec`。
3. **Tools and permissions are related but different**：中间表示区分“有哪些工具”与“是否全量权限”；具体权限形态由 adapter 按平台决定。
4. **Preserve simple authoring**：支持 `- basic`、`- safe-bash`、`- delegate`、`- delegate: [nested/worker]` 等写法，不引入 target-specific DSL。

---

## 核心设计

### 数据模型

#### 中间表示：CapabilitySpec

展开后的结果用不可变结构表示：

```python
@dataclass(frozen=True)
class CapabilitySpec:
    tool_ids: tuple[str, ...]       # 平台无关工具 ID 集合（去重）
    bash_patterns: tuple[str, ...]  # bash 允许列表（glob 模式）；空且含 bash 时表示无限制
    delegates: tuple[str, ...]      # 委派目标引用（canonical id 或 output_layout 下的 id）
    full_access: bool               # 是否表示“全部内置能力”的语义（如 all）
```

- **tool_ids**：adapter 据此映射为平台工具名（如 Claude 的 Read、Bash、Task(id)）。
- **bash_patterns**：空序列且 `"bash" in tool_ids` 表示 unrestricted bash；非空表示仅允许匹配模式的命令。
- **delegates**：与 topology 校验配合；adapter 用于生成 `Task(delegate_id)` 或 permission 中的 task 允许列表。
- **full_access**：在支持权限的平台上可映射为“所有内置权限开放”；不改变 tool_ids 的并集，但可影响 adapter 的权限输出（如 OpenCode 的 `question: allow` 可由 adapter 在 full_access 时自行加上）。

#### Raw capability 格式（YAML）

Role 文件中支持的两种形态：

- **字符串**：`"basic"`、`"read"`、`"safe-bash"`、`"all"`、`"delegate"` 等。
- **结构化对象**（单 key）：
  - `bash: [ "pattern1", "pattern2" ]` — 启用 bash 并追加允许模式。
  - `delegate: [ "id1", "id2" ]` — 启用 task 并声明可委派目标。

列表顺序有意义：按声明顺序依次展开并合并；同名字符串或同类型结构化项可多次出现（合并/去重由展开算法定义）。

#### 默认行为

- **空列表**：`capabilities: []` 或未写 `capabilities` 时，视为 `["basic"]`，即默认展开为 read + write + web-access，不含 bash/delegate。

### 能力词汇表

#### 内置工具组（TOOL_GROUPS）

| 名称 | 展开为 tool ids |
|------|------------------|
| `basic` | read, glob, grep, write, edit, webfetch, websearch |
| `read` | read, glob, grep |
| `write` | write, edit |
| `web-access` | webfetch, websearch |
| `delegate` | task（不自动添加任何 delegate 目标） |

#### 内置工具全集（ALL_TOOL_IDS）

用于 `all` 及 adapter 的“全量”判断，顺序可固定为：

read, glob, grep, write, edit, webfetch, websearch, bash, task

#### Bash 相关

| 名称 | 行为 |
|------|------|
| `bash` | 添加 tool id `bash`，不追加 `bash_patterns`（表示无限制 bash）。 |
| `safe-bash` | 添加 tool id `bash`，并追加内置 `SAFE_BASH_PATTERNS`。 |
| `bash: [ "p1", "p2" ]` | 添加 tool id `bash`，并追加 `p1`、`p2`。 |

多种 bash 能力可同时出现；最终 `bash_patterns` 为所有追加模式的并集去重。若同时出现无限制 `bash` 与带模式的项，语义上可解释为“无限制”（实现上可保留所有 pattern 供 adapter 判断，或约定无限制优先）。

#### 聚合能力

| 名称 | 行为 |
|------|------|
| `all` | 设置 `full_access=True`，并将 `ALL_TOOL_IDS` 加入 `tool_ids`。不改变 `bash_patterns` 与 `delegates` 的已有合并结果。 |

#### 平台扩展：capability_map

- 来源：`roles.toml` 中 `[targets.<name>]` 的 `capability_map`。
- 类型：`dict[str, dict[str, bool]]`，即 `alias_name -> { tool_id: enabled }`。
- 当 raw 项为字符串且不在内置词汇表（TOOL_GROUPS、BASH_POLICIES、`all`、`bash`）中时，若该字符串在 `capability_map` 中存在，则展开为对应 `enabled=True` 的 tool_id 列表。
- 若字符串既不在内置词汇表也不在 `capability_map`，则视为**未知能力**：当前实现将其当作单个 tool_id 原样加入（便于向后兼容与调试）；设计上可保留此行为并建议在文档中说明“仅内置与 capability_map 为稳定语义”。

### 展开算法

**输入**：`capabilities: list[CapabilityValue]`，`capability_map: dict[str, dict[str, bool]]`。

**输出**：`CapabilitySpec`。

**步骤**：

1. 若 `capabilities` 为空，设为 `["basic"]`。
2. 初始化：`tool_ids = []`，`bash_patterns = []`，`delegates = []`，`full_access = False`。
3. 顺序遍历每一项 `cap`：
   - **字符串**：
     - `all` → `full_access = True`，将 `ALL_TOOL_IDS` 加入 `tool_ids`。
     - `bash` → 将 `"bash"` 加入 `tool_ids`（不加入 bash_patterns）。
     - 在 `BASH_POLICIES` 中（如 `safe-bash`）→ 将 `"bash"` 加入 `tool_ids`，将对应 pattern 列表加入 `bash_patterns`。
     - 在 `TOOL_GROUPS` 中 → 将组内 tool id 列表加入 `tool_ids`。
     - 在 `capability_map` 中 → 将映射中 `enabled=True` 的 tool_id 加入 `tool_ids`。
     - 否则 → 将 `cap` 作为单个 tool_id 加入（未知能力）。
   - **字典**：
     - 若存在 key `bash` → 将 `"bash"` 加入 `tool_ids`，将 `cap["bash"]` 中元素加入 `bash_patterns`。
     - 若存在 key `delegate` → 将 `"task"` 加入 `tool_ids`，将 `cap["delegate"]` 中非空引用加入 `delegates`。
4. 去重：`tool_ids`、`bash_patterns`、`delegates` 各自保持顺序并去重（首次出现优先）。
5. 返回 `CapabilitySpec(tool_ids=..., bash_patterns=..., delegates=..., full_access=...)`。

**合并与冲突**：

- 多个 `delegate: [...]` 或多次 `delegate` 字符串：所有目标合并、去重。
- 多个 bash 相关项：所有 pattern 合并、去重；若曾出现裸 `bash`，bash_patterns 仍可非空（adapter 可约定：有 `bash` 且无 pattern 时视为无限制，有 pattern 时按 allowlist 处理）。
- `all` 与其它能力共存：`full_access` 为 True，tool_ids 仍包含所有显式与 all 展开的并集。

### 与 Topology 的交互

- **delegate 引用**：`CapabilitySpec.delegates` 来自 raw 中的 `delegate: [refs]`；这些 ref 在 topology 校验前为“原始引用”，校验时通过 `resolve_delegate_targets(agent, by_id, by_name)` 解析为具体 `AgentDef`。
- **数据流**：loader 解析出 `AgentDef.capabilities`；topology 使用 `agent.declared_delegate_refs()`（直接从 raw capabilities 解析）；render 时 adapter 使用 `expand_capabilities(agent.capabilities, config.capability_map)` 得到 `CapabilitySpec`，再根据 `output_layout` 将 delegate 引用解析为 target 侧 id（如 preserve 用 canonical_id，flatten 用 name 等）。
- **单一事实来源**：delegate 目标列表的唯一声明处是 raw capabilities 中的 `delegate: [...]`；展开结果中的 `delegates` 仅做传递，不改变 topology 的校验逻辑。

### Adapter 契约

- **输入**：adapter 的 render 逻辑接收 `AgentDef`、`TargetConfig`、以及由 caster 预先解析好的 `delegates: list[str]`（已按 output_layout 解析的 target 侧 id）。Adapter 内部应使用 `expand_capabilities(agent.capabilities, config.capability_map)` 得到 `CapabilitySpec`，或由 caster 统一展开后传入（由实现选择）。
- **工具映射**：adapter 将 `spec.tool_ids` 映射为平台工具名/列表；对 `bash` 与 `task` 按平台约定处理（如 Claude 的 `Bash`/`Bash(pattern)`、`Task(id)`）。
- **权限**：若平台支持权限（如 OpenCode），adapter 根据 `spec.tool_flags()`、`spec.bash_patterns`、`spec.delegates`、`spec.full_access` 以及 `agent.role` 等生成 permission 结构；`full_access` 可映射为“所有内置权限允许”，包括平台特有项（如 `question`）由 adapter 自行决定是否在 full_access 时开放。
- **只读**：adapter 不修改 `CapabilitySpec`，不依赖未在本文档或 `CapabilitySpec` 中声明的字段。

---

## 边界情况与设计决策

### `all` 与 `question`

- **决策**：`all` 在 canonical 层仅表示“全部内置工具 + full_access 语义”；不包含平台特有概念 `question`。
- **OpenCode**：若需“all 时权限全开”，由 adapter 在 `full_access=True` 时额外写入 `question: allow`，不把 `question` 纳入 canonical 能力词汇表。

### `delegate` 无目标

- **决策**：仅写 `delegate`（字符串）时，只展开出 tool id `task`，不添加任何 `delegates` 目标；实际可委派目标必须通过 `delegate: [refs]` 声明。不为“无目标的 delegate”引入字符串别名（如 `delegate: allow_any`），避免 topology 与权限语义模糊。

### `capability_map` 的定位

- **短期**：保留为平台扩展与第三方 adapter 的兼容层；允许将别名映射为一组 `tool_id: bool`。
- **长期**：不鼓励用其替代内置词汇表；文档中明确“稳定语义仅限内置 + 本 target 的 capability_map”，避免各 target 定义互相冲突的语义。

### 未知能力字符串

- 当前行为：当作单个 tool_id 加入，便于与未来新 tool 或调试兼容。
- 可选：后续可增加严格模式（如配置或环境变量），未知能力报错或警告。

### Bash：无限制 vs 有 pattern

- 若列表中同时出现 `bash` 与 `safe-bash` 或 `bash: [...]`：实现上合并所有 pattern；adapter 可约定“只要存在任何 pattern 就按 allowlist 处理，否则按无限制”。建议在 adapter 文档中写清各平台的策略。

---

## 测试策略

- **Capability 展开单测**：对 `expand_capabilities` 的输入/输出做全覆盖（空列表、basic、read、write、web-access、delegate、safe-bash、bash、bash: [...]、delegate: [...]、all、capability_map 别名、未知字符串、组合与去重）。
- **权限推导**：对依赖 `CapabilitySpec` 的 OpenCode permission 构建做针对性测试（full_access、仅 bash、仅 delegate、组合）。
- **Alias 与 capability_map**：验证 capability_map 与内置词汇表优先级及合并结果。
- **与 topology 的集成**：保留现有 delegate 解析与校验测试；确保 `declared_delegate_refs()` 与展开结果中的 `delegates` 一致（来源相同）。
- **Adapter snapshot**：继续用 snapshot 覆盖各 adapter 的最终输出，作为回归与文档；能力相关行为应同时有单元级断言，不单靠 snapshot。

---

## 实现与迁移（阶段建议）

1. **Phase 1**：巩固 capability 模块（`capabilities.py` + `groups.py`）— 明确词汇表与展开算法为单一日志源，补充/统一文档字符串与类型。
2. **Phase 2**：adapter 只消费 `CapabilitySpec`；移除 adapter 内对“all”、“bash 合并”等语义的重复实现；统一由 `expand_capabilities` 提供结果。
3. **Phase 3**：增加能力系统单测（见「测试策略」）；更新 `docs/reference/canonical-role-definition.md` 与 adapter 文档，使其与本文档一致。
4. **Phase 4**（可选）：严格模式与未知能力告警、或小范围重构 `capability_map` 结构（不改变对外行为）。

---

## 开放问题

- 是否在 `CapabilitySpec` 中显式区分“无限制 bash”与“有 pattern 的 bash”（例如单独布尔或枚举），以便 adapter 无需根据 `len(bash_patterns)` 推断。
- `capability_map` 是否允许嵌套或更复杂结构（当前为扁平 `alias -> { tool_id: bool }`）；若保持现状，是否在文档中明确“复杂别名请用多个 raw 项”。

---

## 非目标（本设计范围内不做）

- 不移除或重写 hierarchy/topology 系统。
- 不重写 target config 整体结构（仅明确 capability_map 的语义与定位）。
- 不引入 target-specific capability DSL（如平台专用 key）。
- 不改变 Cursor/Windsurf 当前对 capabilities 的最小输出策略。

---

## 成功标准

- 能力语义在单一模块（capabilities + groups）中定义，文档与代码一致。
- `all`、bash 策略、delegate 的展开与合并行为有独立单测，不依赖 adapter snapshot 才能验证。
- Adapter 中与 capability 相关的分支明显减少，仅做“Spec → 平台格式”的映射。
- `docs/reference/canonical-role-definition.md` 能清楚描述每个内置能力与结构化项的语义。
- 新增 adapter 时无需重新实现 expansion 逻辑，只需实现 Spec → 平台输出。
