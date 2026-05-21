# AGENTS.md

本文件是 **Codex / 其它非-Claude-Code AI coding agent** 的仓库入口。`CLAUDE.md` 与本文件允许保留必要重复：入口 skill、第一性原则和工作姿态必须在入口文件里直接可见。

## 协作模式

**AI-first**：AI 引导开发流程和下一步；用户只提供 context 与关键判断。AI 负责理解、澄清、实施、验证和收尾，并减少非必要 HIL。

**入口 skill（必须）**：会话第一轮先加载 `.ai/skills/ai-collaboration-workflow/SKILL.md`。该 skill 持有整个人机协作开发流程：澄清、HIL、topic / roadmap、任务拆解、承载位、验证、发布和收尾；Superpowers 只负责具体任务执行流程。每次 Superpowers 执行结束后，控制权回到 workflow skill 做仓库级判断。

**启动 / worktree 硬闸门**：开始工作先确认当前 branch 与远程 upstream 同步，并检查相对主分支是否落后；若落后，默认先同步再改。任何会产生修改的行为之前，必须确认当前路径 / branch / worktree 属于本任务；若已有目标 worktree，只有目标 worktree 可以写入，其它工作区只允许只读定位。默认 linked worktree 承载位是仓库旁侧 `../worktrees/<repo>-<slug>`。

## 导航地图

- **项目总览 / 架构**：`docs/references/project-overview.md`。需要命令、入口、架构、环境、部署、依赖或默认沟通语言时读取；这是本模板的项目总览与架构真相源。
- **Python 代码风格**：`docs/references/python-code-style.md`。涉及 Python 代码、脚本、测试或 review 时读取。
- **工件承载位**：`.ai/superpowers/specs/` 放本地设计工件；`.ai/superpowers/plans/active/` 放单次实施计划。开 session 先扫 active plans。
- **主题层**：长期主题放在 `.ai/topics/<slug>/`。任务跨多轮、改变稳定边界或需要沉淀设计结论时读取 / 更新。
- **反馈入口**：用户给出 `.ai/feedback/<YYYYMMDD>_<slug>/round<N>.md` 或 `完成 @<路径>` 时读取对应反馈。
- **团队可见工件（不是规则层级）**：PR description 四段 Goal / Design / Validation / Risk；长期协作设计进入 `.ai/topics/<slug>/design.md`；项目事实进入 `docs/references/project-overview.md`。

`ai-collaboration-workflow/SKILL.md` 是最高优先级协作规则和 coding agent 行为约束正文。其它文件提供项目事实、代码风格、执行工件或长期设计上下文，按任务需要加载。

## 第一性原则

以第一性原理：从原始需求和问题本质出发，不从惯例或模板出发。

1. 不要假设用户清楚自己想要什么。动机或目标不清晰时，停下来讨论。
2. 目标清晰但路径不是最短的，直接说明并建议更好的办法。
3. 遇到问题追根因，不打补丁。每个决策都要能回答“为什么”。
4. 输出说重点，砍掉一切不改变决策的信息。

## 工作姿态

来源：参考 [multica-ai/andrej-karpathy-skills 的 CLAUDE.md](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md)，并按本仓库 AI-first 协作规则本地化。

1. **Think Before Coding**：开工前陈述关键假设；有多重解读就明列；用户表达不确定、征询判断或希望共同探讨时，先澄清 / 对齐再实施。
2. **Simplicity First**：最小解决问题；不加未请求的特性、单次用抽象或没人要的配置项。
3. **Surgical Changes**：每一行改动都能追溯到当前任务；不顺手改邻居代码、格式或注释；匹配现有风格。
4. **Loop Until Verified**：把模糊诉求翻译成可验证的成功判据；完成声明必须有当轮新产生的验证证据。

## Codex 适配

- Plan / spec 路径统一使用 `.ai/superpowers/`；开 session 先扫 `.ai/superpowers/plans/active/`。
- Codex 没有本仓库的 Stop hook / slash command 兜底，完成前必须自检活跃 plan 的 `## Validation` 段、未勾 checkbox 和本轮验证证据。
- 2+ 独立子任务可并行时，积极使用当前环境允许的并发机制；若某种机制受当前 agent 系统策略限制，使用其它并行方式。
