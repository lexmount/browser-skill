# AI Collaboration Template

本 topic 追踪 `ai-template-py` 自身的长期演进。它不是业务仓库的样例 topic，而是模板维护者用来回答："这个 Python 仓库模板下一步应该怎么变得更容易创建、复制、理解和维护？"

## 范围

- Python 仓库基础模板：`pyproject.toml`、`Makefile`、`.gitignore`、`.env.example`
- AI 协作骨架：`AGENTS.md`、`CLAUDE.md`、`.ai/`、`.claude/`、`.codex/`
- 新仓库创建路径：GitHub template、普通 clone、已有仓库按需复制
- 协作数据流：PRD → spec → task / issue → code → PR → comments → commit

## 当前状态

- 已明确模板不作为 runtime dependency，也不推荐作为 submodule。
- 已把通用流程 skills 放在 `.ai/skills/`，项目专用 skills 留给业务仓库。
- 已把长期主题统一到 `.ai/topics/<slug>/`，去掉 `docs/topics` 与 `.ai/templates` 这类平行概念。
- 已按 worktree 粒度规则确认工作位置：独立 PR / 高风险 / 长任务默认使用入口文件指定的 linked worktree 承载位，同一 PR 续修改复用现有任务分支或 worktree。

## 关联文件

- [design.md](design.md) — 当前模板设计
- [roadmap.md](roadmap.md) — 后续路线图
- [`../../skills/ai-collaboration-workflow/`](../../skills/ai-collaboration-workflow/) — 人机协作流程与协作规则
- [`../../skills/ai-collaboration-workflow/SKILL.md`](../../skills/ai-collaboration-workflow/SKILL.md) — coding agent 行为约束
- [`../../../README.md`](../../../README.md) — 使用入口
