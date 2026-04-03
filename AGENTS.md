# role-forge 开发指南

提交和 PR 规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 提交前

运行 `just ci` 确保格式、lint、类型检查和测试通过。

## 开发命令

```bash
just install       # 安装依赖
just format        # 格式化代码
just lint          # Lint 检查
just check         # 类型检查
just test          # 运行测试
uv build           # 构建发布产物
uv publish         # 发布到 PyPI
just cov           # 测试 + 覆盖率
just ci            # 完整 CI 流程（format + lint + check + test）
just pre-commit    # 运行 pre-commit 钩子
```

## 项目结构

```
src/role_forge/
├── cli.py          # CLI 入口（add / update / list / remove）
├── config.py       # roles.toml 解析
├── loader.py       # Role 定义加载（YAML frontmatter + Markdown）
├── outputs.py      # 项目级 output ownership manifest
├── models.py       # Pydantic 数据模型
├── groups.py       # Capability group 和 bash policy 定义
├── registry.py     # GitHub source 获取、repo cache 与 roles_dir 发现
├── platform.py     # 平台检测
├── topology.py     # hierarchy / delegation / output layout 校验
└── adapters/       # 平台适配器和 entry point 注册
```

## 当前 CLI 语义

- `roles.toml` 是 source repo 内语义配置，`add` / `update` 直接从本地 repo 或 repo cache 解析并生成目标文件
- 全局 repo cache 位于 `~/.config/role-forge/repos`，索引位于 `~/.config/role-forge/manifest.json`
- 项目级输出归属记录位于 `.role-forge/outputs.json`，用于 `remove` 精准清理和重建剩余 source 输出
- `add` / `update` 默认会对覆盖操作做确认；`--yes` 跳过覆盖提示
- `roles.toml` 只支持 `project.roles_dir`，不再兼容 `project.agents_dir`
- 没有独立 `render` 命令；重新生成由 `add` / `update` 驱动
- `remove` 以 source 为单位删除 cache 与已生成文件，并重建剩余 source 的冲突输出

## 添加新适配器

1. 在 `src/role_forge/adapters/` 下创建新模块，继承 `BaseAdapter`
2. 在 `adapters/__init__.py` 的内置 registry 中注册，或通过 entry point 提供第三方 adapter
3. 在 `pyproject.toml` 的 `[project.entry-points."role_forge.adapters"]` 中注册
4. 在 `tests/` 下添加对应的 snapshot 测试
