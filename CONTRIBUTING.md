# Contributing to agent-caster

感谢你的贡献！本文档面向人类贡献者，说明参与开发的基本流程。

## 开发环境

```bash
git clone https://github.com/zrr1999/agent-caster.git
cd agent-caster
just install   # 安装依赖
just ci        # 完整 CI 流程（format + lint + check + test）
```

## 提交流程

- 小步提交，确保每个提交聚焦单一主题
- 提交前确保本地 CI 通过（format + lint + check + test）

## Commit message 规范

格式统一为：

```
<emoji> <type>(<scope>): <subject>
```

`scope` 为可选项，用于标注影响的模块。

### 推荐 type

| emoji | type | 使用场景 |
|-------|------|----------|
| ✨ | `feat` | 新增功能 |
| 🐛 | `fix` | 修复 bug |
| ♻️ | `refactor` | 重构（不改变外部行为） |
| 📝 | `docs` | 文档调整 |
| ✅ | `test` | 测试相关 |
| 🔧 | `chore` | 构建、CI、依赖等杂项 |
| 🎨 | `style` | 代码风格/格式化 |
| 🚀 | `deploy` | 部署相关 |
| 🔥 | `remove` | 删除代码或文件 |

### 示例

```
✨ feat(adapter): add Cursor adapter
🐛 fix(loader): handle missing frontmatter gracefully
♻️ refactor: rename compiler to caster
📝 docs: add README and AGENTS.md
✅ test(opencode): add snapshot tests for permission block
🔧 chore: upgrade CI to Python 3.14
```

## PR 标题规范

- 与提交规范保持一致
- 描述要更宏观，概括 PR 整体变更
- CI 会自动检查 PR 标题是否符合规范

### 示例

```
✨ feat(adapter): add Cursor adapter support
🐛 fix(loader): handle missing frontmatter gracefully
🔧 chore: upgrade CI to Python 3.14
```

## 代码审查约定

- 新功能需附带测试
- 避免单次 PR 修改过多不相关文件
- 回复 review 意见时，已修复的注释通过 resolve thread 标记关闭

## 添加新适配器

1. 在 `src/agent_caster/adapters/` 下创建新模块，继承 `BaseAdapter`
2. 在 `adapters/__init__.py` 的 `_REGISTRY` 中注册
3. 在 `pyproject.toml` 的 `[project.entry-points."agent_caster.adapters"]` 中注册
4. 在 `tests/` 下添加对应的 snapshot 测试

## 版本管理

版本号遵循 [Semantic Versioning](https://semver.org/)：

- `MAJOR` — 不兼容的 API 变更
- `MINOR` — 向后兼容的新功能
- `PATCH` — 向后兼容的 bug 修复
