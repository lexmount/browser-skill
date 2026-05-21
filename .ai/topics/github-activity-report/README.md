# GitHub Activity Report — GitHub 活动报告通用 Skill

**Status:** active
**Owner surface:** `.ai/skills/composing-data-insights/`、`.ai/skills/github-activity-report/`
**Started:** 2026-05
**Last updated:** 2026-05-14

## 读者先看

本 topic 记录一个长期可复用能力：根据 GitHub 组织、团队、仓库、Project v2 或个人范围生成日报、周报和历史活动报告。当前方向不是新建一套通用报告系统，而是把 `composing-data-insights` 作为默认安装 skill 完善为共享洞察/渲染基础，再新增默认安装的 `github-activity-report` 负责 GitHub 数据采集、Projects v2 归一化和范围确认。首版以 Markdown / HTML 输出为目标，Notion 和图片报告是后续扩展。最大风险是 GitHub Projects v2 权限、字段差异和个人活动指标误读；这些必须在报告 caveats 和 skill 规则里显式处理。

## 范围

**包含：**

- `.ai/skills/composing-data-insights/` 作为共享数据洞察和报告渲染 skill
- `.ai/skills/github-activity-report/` 作为 GitHub 专用采集、归一化和报告编排 skill
- `skills/README.md` 仅保留未来候选 skill 的占位说明
- GitHub Projects v2、issue、pull request、review、commit activity 的只读采集
- Markdown 和自包含 HTML 报告
- 管理/交付视角和工程效能视角
- 个人活动量信号，但不做个人能力或绩效排名

**不包含：**

- 首版不写入 GitHub Projects、issue、pull request 或 repository
- 首版不创建 Notion 页面
- 首版不生成图片报告
- 不把代码行数、commit 数或 PR 数解释为个人绩效结论

## 当前态

- **已完成：** 需求边界已内联到本 topic：首版使用 Skill + 轻量脚本工具箱；Projects v2 是核心能力；自动发现 project 后必须让用户确认；默认管理/交付视角，按需切工程效能视角；个人代码量指标只能作为活动量信号。
- **已完成：** `composing-data-insights` 和 `github-activity-report` 已移入默认 `.ai/skills/`；references、归一化脚本、渲染脚本和 fixture-first 测试已完成。
- **待验证：** 真实 GitHub live smoke 需要可访问 Projects v2 和 `read:project` scope；图片 / Notion 输出仍是后续扩展。
- **已知风险：** GitHub Projects v2 需要 `read:project` scope；私有仓库 activity 需要额外 repo 权限；Project v2 field 名称在不同团队中可能不一致。

## 关键证据

| 日期 | 证据 | 结论 | 链接 / 路径 |
|------|------|------|-------------|
| 2026-05-11 | 需求摘要 | 需要 GitHub report 通用 skill，并强调不能重复建设通用报告能力 | 本 topic `design.md` |
| 2026-05-11 | 流程纠偏 | 需要 worktree 隔离和 tracked topic，不能只依赖 gitignored spec | `.ai/topics/ai-collaboration-template/design.md` |
| 2026-05-11 | GitHub 官方文档 | Projects v2 通过 GraphQL/`gh api graphql` 读取，读权限需要 `read:project` | https://docs.github.com/en/graphql/reference/objects#projectv2 |
| 2026-05-11 | 源 skill 复制 | `composing-data-insights` 复制自 `lex-rpa` 的原始 skill 目录，当前安装在 `.ai/skills/composing-data-insights` | source commit `b33e7aa4d51e7d1deb02d6003018f57dd360fcb8` |

## 关联执行历史

| 日期 | plan | 概要 | commit |
|------|------|------|--------|
| 2026-05-11 | `.ai/superpowers/plans/active/2026-05-github-activity-report-skill.md` | 复制并完善 `composing-data-insights`，新增 GitHub 活动报告 skill | pending commit |

## 相关 topic / FAQ

- `.ai/topics/ai-collaboration-template/` — AI-first 流程和 topic / plan 分层规则
