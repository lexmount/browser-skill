# Skills 版本 pin

`.ai/skills/` 同时包含 [`obra/superpowers`](https://github.com/obra/superpowers)（MIT）来源的流程 skill 和 lexmount 自研 skill。升级时按每行来源处理；lexmount 自研 skill 不从 superpowers 拉取。

## 仓库内路径与双向 symlink

- 真相源：`.ai/skills/<name>/`
- `.codex/skills` / `.claude/skills` → symlink 到 `.ai/skills`
- **不得**在 symlink 位置维护独立副本（编辑任一路径等同编辑真相源）

## Skill 快照（2026-05-08）

| Skill | 本仓库版本 | 来源 | 备注 |
|-------|------------|------|------|
| `brainstorming` | f2cbfbe | `obra/superpowers/skills/brainstorming` | Spec 承载位：`.ai/superpowers/specs/<slug>.md`，本地 gitignored |
| `writing-plans` | f2cbfbe | `obra/superpowers/skills/writing-plans` | Plan 承载位：`.ai/superpowers/plans/active/<slug>.md`，本地 gitignored |
| `executing-plans` | f2cbfbe | `obra/superpowers/skills/executing-plans` | 与 `subagent-driven-development` 二选一 |
| `subagent-driven-development` | f2cbfbe | `obra/superpowers/skills/subagent-driven-development` | 同上 |
| `test-driven-development` | f2cbfbe | `obra/superpowers/skills/test-driven-development` | Iron Law #3 配套 |
| `systematic-debugging` | f2cbfbe | `obra/superpowers/skills/systematic-debugging` | 故障定位 |
| `dispatching-parallel-agents` | f2cbfbe | `obra/superpowers/skills/dispatching-parallel-agents` | 2+ 独立子任务并发 |
| `using-git-worktrees` | f2cbfbe | `obra/superpowers/skills/using-git-worktrees` | |
| `verification-before-completion` | f2cbfbe | `obra/superpowers/skills/verification-before-completion` | Iron Law #3 强制 |
| `requesting-code-review` | f2cbfbe | `obra/superpowers/skills/requesting-code-review` | 触发条件：以 [`../../.claude/agents/reviewer.md`](../../.claude/agents/reviewer.md) "什么时候被调用" 为准 |
| `receiving-code-review` | f2cbfbe | `obra/superpowers/skills/receiving-code-review` | |
| `finishing-a-development-branch` | f2cbfbe | `obra/superpowers/skills/finishing-a-development-branch` | plan 归档时机由该 skill 判断（本仓库不自建平行规则） |
| `using-superpowers` | f2cbfbe | `obra/superpowers/skills/using-superpowers` | Iron Law #1 |
| `ai-collaboration-workflow` | 本仓库 | `lexmount/ai-template-py:.ai/skills/ai-collaboration-workflow` | AI-first 开发流程入口 |
| `writing-skills` | f2cbfbe | `obra/superpowers/skills/writing-skills` | 改 skill 时用 |
| `composing-data-insights` | 本仓库 | `lexmount/ai-template-py:.ai/skills/composing-data-insights` | 数据洞察与可视化报告 skill |
| `github-activity-report` | 本仓库 | `lexmount/ai-template-py:.ai/skills/github-activity-report` | GitHub activity 报告 skill |
| `preparing-prs` | 本仓库 | `lexmount/ai-template-py:.ai/skills/preparing-prs` | PR description 维护 skill |
| `notion-doc-reader` | 本仓库 | `lexmount/ai-template-py:.ai/skills/notion-doc-reader` | 通用 Notion 官方 API 只读文档读取 skill；随目录复制可迁移 |

## 升级流程

1. `obra/superpowers` 来源 skill：从对应来源拉新版本 SKILL.md diff 评估
2. 若仓库适配受影响（例如 plan 位置 / reviewer 触发条件），先改真相源（`plans/README.md` / `.claude/agents/reviewer.md`），再改 skill 文件
3. 升级完成后更新本表的 **本仓库版本**；来源路径 / 备注按需调整
4. 本表改动属协作骨架级变更——触发 `reviewer` subagent 必调（见 [`../../.claude/agents/reviewer.md`](../../.claude/agents/reviewer.md)）
