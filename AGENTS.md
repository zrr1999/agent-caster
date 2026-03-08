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
just cov           # 测试 + 覆盖率
just ci            # 完整 CI 流程（format + lint + check + test）
just pre-commit    # 运行 pre-commit 钩子
```

## 项目结构

```
src/role_forge/
├── cli.py          # CLI 入口（add / update / render / list / remove）
├── config.py       # roles.toml / refit.toml 解析
├── loader.py       # Role 定义加载（YAML frontmatter + Markdown）
├── models.py       # Pydantic 数据模型
├── groups.py       # Capability group 和 bash policy 定义
├── registry.py     # GitHub source 获取和 roles_dir 发现
├── platform.py     # 平台检测
├── topology.py     # hierarchy / delegation / output layout 校验
└── adapters/       # 平台适配器和 entry point 注册
```

## 添加新适配器

1. 在 `src/role_forge/adapters/` 下创建新模块，继承 `BaseAdapter`
2. 在 `adapters/__init__.py` 的内置 registry 中注册，或通过 entry point 提供第三方 adapter
3. 在 `pyproject.toml` 的 `[project.entry-points."role_forge.adapters"]` 中注册
4. 在 `tests/` 下添加对应的 snapshot 测试
