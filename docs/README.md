# Docs — 项目知识

本目录是**人读的项目知识**：外部第三方约束、产品规格和项目速读。与 [`../.ai/`](../.ai/) 分工明确：**规则 / 流程 / 工件 / 原料走 `.ai/`，人读知识走 `docs/`**。

## 新人必读

1. [`../README.md`](../README.md) — 项目一句话 + 使用入口
2. [`references/project-overview.md`](references/project-overview.md) — 项目特化一站式入口
3. [`references/python-code-style.md`](references/python-code-style.md) — Python 模板偏好
4. [`../CLAUDE.md`](../CLAUDE.md) — Claude Code 入口 / [`../AGENTS.md`](../AGENTS.md) — Codex 等其它 agent 入口
5. [`../.ai/README.md`](../.ai/README.md) — AI 协作骨架全景

**给 AI 提反馈 / 新需求的推荐方式**：写到 `../.ai/feedback/<YYYYMMDD>_<slug>/round<N>.md`，聊天框只敲 `完成 @<路径>`。详见 [`../.ai/feedback/README.md`](../.ai/feedback/README.md)。

## Documentation Map

| 目录 | 是什么 | 何时读 | 何时产出 | 怎么改 |
|-----|-------|--------|---------|--------|
| [`references/`](references/) | 外部资料 / 第三方约束 / 语言栈偏好 | 找第三方约束 / 部署指南 / Python 代码风格 | 用户按需触发 AI 写 | 保持一题一文；项目总览只改 `project-overview.md` |
| [`product-specs/`](product-specs/) | PRD、产品规格、验收标准 | 找需求真相源 | 用户按需从 `_template.md` 开始 | 从 `_template.md` 复制后填真实需求 |

项目自身速读、架构边界和运行入口在 `docs/references/project-overview.md`；`references/` 同时承载外部约束和语言栈偏好。`docs/` 不再单设 `faq/` 子目录——跨 change 的协作小共识直接收进本文末段的"常见问题"。

## 不在 `docs/` 下的相关目录

| 路径 | 用途 | 追踪状态 |
|------|------|---------|
| [`../.ai/feedback/`](../.ai/feedback/) | 用户给 coding agent 的反馈原料 / 驱动文档 | **gitignored** 本地 |
| [`../.ai/topics/`](../.ai/topics/) | 跨多轮任务的长期主题 | **tracked**（无归档） |
| [`../.ai/superpowers/specs/`](../.ai/superpowers/specs/) | 本地设计工件 | **gitignored**（README + template 例外 tracked） |
| [`../.ai/superpowers/plans/`](../.ai/superpowers/plans/) | 本地执行计划与验证记录 | **gitignored**（README + template 例外 tracked） |
| [`../.ai/skills/ai-collaboration-workflow/`](../.ai/skills/ai-collaboration-workflow/) | 人机协作流程 + coding agent 行为约束 + 质量闸门 | tracked |

## 放哪里

- 用户给的需求原料 → `.ai/feedback/<group>/`
- 外部约束 / 第三方资料 → `docs/references/`
- 项目特化入口 → `docs/references/project-overview.md`
- 语言栈偏好 → `docs/references/python-code-style.md`
- 产品规格 / 验收标准 → `docs/product-specs/`
- 跨任务长期技术主题 → `.ai/topics/<slug>/`
- 单次实施跟踪 → `.ai/superpowers/plans/active/<slug>.md`
- 协作骨架修改 → `.ai/skills/ai-collaboration-workflow/` / `CLAUDE.md` / `AGENTS.md` / `docs/references/project-overview.md`

## 常见问题

**Q1: 为什么用 `.ai/` 而不是 `.claude/` / `docs/`？**
协作骨架是**工具中立**的：`.ai/` 不绑定单一 AI 客户端（Claude Code / Codex / Gemini CLI 都读同一份）。`.claude/` 专属于 Claude Code（hooks / agents / skills 符号链接），`docs/` 是人读的项目知识。三者分工不同，不混放。完整结构见 [`../.ai/README.md`](../.ai/README.md)。

**Q2: plan / spec / topic / feedback 分别放哪？**

| 工件 | 路径 | Tracked? | 谁产出 |
|------|------|---------|-------|
| 单次实施 plan | `.ai/superpowers/plans/active/<slug>.md` | **gitignored** | coding agent |
| 本地设计 spec | `.ai/superpowers/specs/<date>-<topic>-design.md` | **gitignored** | coding agent |
| 跨多轮长期主题 | `.ai/topics/<slug>/{README,design,roadmap,decisions}.md` | tracked（无归档） | coding agent 按需 |
| 用户反馈 | `.ai/feedback/<YYYYMMDD>_<slug>/round<N>.md` | **gitignored**（扁平） | 用户 |
| 外部第三方约束 | `docs/references/<topic>.md` | tracked | 用户按需触发 |
| 产品规格（PRD） | `docs/product-specs/<slug>.md` | tracked | 用户 |

**Q3: 新文档该放 `.ai/` 还是 `docs/`？**
**规则 / 流程 / 长期主题 / 本地工件** → `.ai/`；**人读的稳定项目知识**（外部约束 / 产品规格 / 历史归档）→ `docs/`。一句话检验：内容主要是 **coding agent + 人协作过程产物** 放 `.ai/`；**面向人读的成品资料** 放 `docs/`。

**Q4: `permissions.allow` 写哪个 settings 文件？**
**只能** `.claude/settings.local.json`（本机私有，gitignored）。**禁止**写进 `.claude/settings.json`（团队共享；只存 hook 注册 + schema + 破坏性 deny 规则）。理由：个人偏好 / 本机路径 / 实验性规则因人而异，共享到 team 会互相干扰。想让某条 allow 规则上升为团队规则时，**人手工**拷贝到 `.claude/settings.json`，coding agent 不主动升级。
