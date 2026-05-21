# `.ai/` — AI 协作骨架

**规则 / 流程 / 主题 / 本地工件在此**；[`docs/`](../docs/) 放人读的稳定知识。

协作基线 **AI-first**：AI 引导开发流程和下一步；用户只提供 context 与关键判断。可复用流程、协作规则和 coding agent 行为约束入口是 [`skills/ai-collaboration-workflow/`](skills/ai-collaboration-workflow/)。

反馈入口见 [`feedback/README.md`](feedback/README.md)：写到 `.ai/feedback/<YYYYMMDD>_<slug>/round<N>.md`，聊天框只敲 `完成 @路径`。

## 四块内容

| 子目录 | 是什么 | 追踪状态 | 规则定位 |
|-------|-------|---------|-------------|
| [`topics/`](topics/) | 跨多轮任务的长期主题 | tracked（不归档） | 长期设计 |
| [`superpowers/{specs,plans}/`](superpowers/) | 本地 spec / plan 工件 | gitignored | 本地执行 |
| [`feedback/`](feedback/) | 个人 × AI 的反馈 / 需求原料 | gitignored | 用户原料 |
| [`skills/`](skills/) | 已安装流程能力；`ai-collaboration-workflow/SKILL.md` 内含行为约束 | tracked | 流程与规则 |

项目专用 skills 不放在模板里。业务仓库确有需要时，可在自己的 `.ai/skills/<skill>/` 中维护，让 Claude Code / Codex 通过符号链接直接发现；面向 runtime 或产品平台的 skills 则放到该项目自己的目录和安装流程里。模板已经确认可复用的能力放在 `.ai/skills/`；根目录 [`../skills/`](../skills/) 仅保留未来候选能力的占位说明。

团队可见工件不是规则层级：项目事实进入 `docs/references/project-overview.md`；长期主题设计进入 `.ai/topics/<slug>/design.md`；当前 PR 交付摘要进入 PR description 四段 Goal/Design/Validation/Risk。

## 新人速读

- **干活** → 写 `feedback/<YYYYMMDD>_<slug>/round<N>.md`，聊天框 `完成 @路径`
- **流程入口** → [`skills/ai-collaboration-workflow/SKILL.md`](skills/ai-collaboration-workflow/SKILL.md)
- **协作流程 / 协作规则** → [`skills/ai-collaboration-workflow/`](skills/ai-collaboration-workflow/)
- **行为约束来源** → [`skills/ai-collaboration-workflow/SKILL.md`](skills/ai-collaboration-workflow/SKILL.md)
- **方案** → [`topics/<slug>/`](topics/)
- **PR 决策** → 对应 PR description 四段
- **本机 plan** → [`superpowers/plans/active/`](superpowers/plans/active/)
- **架构** → [`../docs/references/project-overview.md`](../docs/references/project-overview.md)
- **Python 模板偏好** → [`../docs/references/python-code-style.md`](../docs/references/python-code-style.md)
