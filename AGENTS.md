# agent-caster 开发指南

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
src/agent_caster/
├── cli.py          # CLI 入口（init / cast / list）
├── config.py       # refit.toml 解析
├── loader.py       # Agent 定义加载（YAML frontmatter + Markdown）
├── models.py       # Pydantic 数据模型
├── groups.py       # Capability group 和 bash policy 定义
├── caster.py       # Cast 编译管线
└── adapters/       # 平台适配器
    ├── base.py     # Adapter Protocol
    ├── claude.py   # Claude Code 适配器
    └── opencode.py # OpenCode 适配器
```

## 添加新适配器

1. 在 `src/agent_caster/adapters/` 下创建新模块，实现 `Adapter` Protocol
2. 在 `adapters/__init__.py` 的 `_REGISTRY` 中注册
3. 在 `pyproject.toml` 的 `[project.entry-points."agent_caster.adapters"]` 中注册
4. 在 `tests/` 下添加对应的 snapshot 测试

## Cursor Cloud specific instructions

- **No services to run.** This is a pure Python CLI tool with no long-running processes, databases, or Docker dependencies.
- **System deps:** `uv` (Python package manager) and `just` (task runner) must be on `$PATH`. Both install to `~/.local/bin`.
- **Git hooks caveat:** `uvx prek install` (run by `just install`) may fail if `core.hooksPath` is already set in git config. Fix with `git config --unset-all --local core.hooksPath` before running `just install`.
- **Interactive prompts:** The `agent-caster cast --target cursor` command prompts interactively for model config when no model mapping exists. For non-interactive testing, use `--target claude` or `--target opencode` instead.
- All dev commands (`just lint`, `just check`, `just test`, `just ci`) are documented in the "开发命令" section above.
