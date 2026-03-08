# Capability System Redesign

Date: 2026-03-08
Status: Draft

## Goal

把当前“字符串 capability + 适配器各自展开”的实现整理成一个更清晰、可验证、可扩展的能力系统，让 canonical role definition 能稳定表达：

- 抽象能力组
- 平台工具展开
- 权限语义
- bash / delegate 这类特殊能力
- 后续第三方 adapter 可复用的公共规则

## Current Problems

### 1. 能力定义分散

- 基础能力组在 `src/role_forge/groups.py`
- `all` 之类聚合能力目前靠适配器自行理解
- `capability_map` 又允许 target config 注入一套额外映射

结果是“canonical capability 的真实语义”分散在多个地方，不容易推断，也不容易做一致性测试。

### 2. 工具和权限没有统一模型

当前实现里，“工具可用”与“权限如何表达”混在 adapter 内部：

- Claude 关心 `tools: ...`
- OpenCode 关心 `tools` + `permission`
- Cursor / Windsurf 又基本忽略细粒度 capability

这导致同一个 capability 在不同 adapter 里难以判断是否真正等价。

### 3. 特殊能力语义不够明确

以下能力都属于“不是简单工具组”的类型：

- `safe-bash`
- `bash: [...]`
- `delegate: [...]`
- `all`

这些能力既影响工具集合，也影响权限集合，还可能影响 topology 校验，但当前没有统一的数据结构来表示。

### 4. 扩展性不足

后续如果要支持：

- `basic`
- 平台特有 capability alias

现在的实现容易继续把逻辑堆进 adapter，增加分叉。

## Design Principles

### 1. Canonical first

canonical role file 里写的 capability 必须有明确、平台无关的语义，adapter 只负责“翻译”，不负责重新发明语义。

### 2. Expand once, render many

先把 role 的 raw capabilities 归一化成统一的中间表示，再交给各 adapter 渲染，而不是每个 adapter 从零解释一遍。

### 3. Tools and permissions are related but different

要显式区分：

- capability 展开出的“可用工具”
- capability 展开出的“权限策略”

同一个工具在不同平台的权限表达方式可以不同，但 canonical 语义应统一。

### 4. Preserve simple authoring

role 作者仍应能写：

```yaml
capabilities:
  - basic
  - safe-bash
  - delegate
  - delegate:
      - nested/worker
```

不要把 canonical 格式搞成 target-specific DSL。

## Proposed Capability Model

引入一个统一的“展开结果”概念，例如：

```python
CapabilitySpec(
    tools={"read", "glob", "grep", "write", "edit"},
    bash_patterns=["git diff*"],
    delegates=["nested/worker"],
    full_access=False,
)
```

其中：

- `tools`: 平台无关工具 id 集合
- `bash_patterns`: bash allowlist；空数组且 bash 开启时可表示 unrestricted bash
- `delegates`: 原始 delegate target refs 或解析后的 canonical ids
- `full_access`: 像 `all` 这种聚合能力可直接声明“全部内置能力”语义

## Capability Vocabulary

### Stable built-ins

- `read` -> `read`, `glob`, `grep`
- `write` -> `write`, `edit`
- `web-access` -> `webfetch`, `websearch`
- `basic` -> `read`, `write`, `web-access`
- `delegate` -> `task`
- `bash` -> unrestricted bash
- `safe-bash` -> `bash` + safe allowlist
- `all` -> 全部内置 tools，并在支持权限映射的平台上给予全部内置权限

### Structured entries

- `bash: [...]` -> 追加 bash allowlist
- `delegate: [...]` -> 声明可委派目标

## Proposed Refactor Scope

### Phase 1: Centralize expansion

在 `src/role_forge/` 新增一个专门的 capability 模块，例如：

- `capabilities.py`

职责：

- 定义内置 capability group
- 定义聚合 capability（如 `all`）
- 把 raw capability list 归一化为统一结构
- 处理 alias
- 处理 bash / delegate 的合并与去重

adapter 不再自己理解 `all`、alias、bash policy 合并规则。

### Phase 2: Separate render policy from expansion

每个 adapter 只接收统一展开结果，再把它映射为：

- Claude `tools` / `Bash(...)` / `Task(...)`
- OpenCode `tools` / `permission`
- Cursor / Windsurf 的说明性输出

### Phase 3: Improve validation

增加能力系统自己的测试层，而不是只通过 adapter snapshot 间接覆盖：

- capability expansion unit tests
- permission derivation tests
- alias compatibility tests
- `all` behavior tests

## Open Questions

### 1. `all` 是否包含 `question`

当前 `question` 更像 OpenCode primary-role 的交互特权，不完全属于 canonical capability。

建议：

- `all` 只表示全部内置工具能力
- `question` 继续保留为 adapter / role-specific policy
- OpenCode 若需要“all 时权限全开”，可以在 adapter 层额外映射出 `question: allow`

这样不会把一个 OpenCode 特有概念反向污染 canonical 模型。

### 2. `delegate` 是否应该有字符串别名

比如未来支持：

- `delegate` -> 仅开启 task 工具

当前不建议。因为没有目标列表的 delegate 几乎没有可执行语义，容易让 topology 和权限模型变模糊。

### 3. `capability_map` 的长期定位

当前 `TargetConfig.capability_map` 很实用，但也会让 target config 成为第二套 capability DSL。

建议长期限制它的角色为：

- 平台扩展映射
- 第三方 adapter 临时兼容层

不要让它替代 canonical built-ins。

## Fixture and Test Plan

测试 fixture 保持“像测试例子”的目录结构，不照搬真实生产 role tree。

建议固定保留一套轻量嵌套样例，例如：

```text
tests/fixtures/.agents/roles/
  nested/
    nested-coordinator.md
    feature-lead.md
    workers/
      impl-worker.md
      qa-worker.md
    support/
      research-helper.md
```

覆盖目标：

- 递归加载
- nested canonical id
- delegate 到嵌套 role
- `all` capability
- preserve / namespace layout 下的输出差异

## Implementation Plan

1. 新增 capability expansion 中间层模块
2. 把 `groups.py` 收敛为静态 capability definitions
3. 迁移 `claude.py` 和 `opencode.py` 到统一展开结果
4. 明确 `all` 的 canonical 语义与 adapter-specific 权限行为
5. 增加 capability 层单测，不只依赖 snapshot
6. 更新 `docs/reference/canonical-role-definition.md`
7. 视需要补充 `README.md` 和 adapter 文档

## Non-Goals

- 这一轮不移除 hierarchy / topology 系统
- 这一轮不重写 target config 结构
- 这一轮不引入 target-specific capability DSL
- 这一轮不改变 Cursor / Windsurf 的最小输出策略

## Success Criteria

- capability 语义在一个中心模块里定义
- `all`、bash policy、delegate 的行为有独立单测
- adapter 中 capability 相关分支明显减少
- canonical 文档能清楚解释每个 capability 的语义
- 新增 adapter 时不需要重新发明 capability expansion 逻辑
