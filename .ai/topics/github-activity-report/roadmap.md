# GitHub Activity Report — Roadmap

> topic 级 roadmap 记录 GitHub 活动报告能力的长期进展。它不是单次执行计划；每个条目都要能回到 design / PR / commit 证据。

## Outcome

本 topic 完成后，系统应具备：

- 可复用的 `composing-data-insights` 共享数据洞察和报告渲染 skill。
- 可复用的 `github-activity-report` skill，支持 GitHub Projects v2、issue、PR、review、commit activity 的只读报告。
- 两个报告 skill 默认安装在 `.ai/skills/`，可被本地 coding agent 渐进式发现和按需加载。
- Markdown 和 HTML 报告输出，包含项目进展、风险、人员活动趋势、工程效能和数据覆盖说明。
- fixture-first 验证，覆盖 Projects v2 字段冲突、redacted item、draft issue、权限缺口和个人指标安全边界。

## Done

| 日期 | 结果 | 证据 | 同步到 design |
|------|------|------|---------------|
| 2026-05-11 | 明确首版边界：Projects v2 核心、Markdown/HTML 输出、默认管理/交付视角、按需工程效能视角、个人代码量只作活动信号 | 本 topic 需求摘要 | §设计原则 |
| 2026-05-11 | 明确复用策略：复制并完善 `composing-data-insights`，GitHub skill 不重复建设通用报告能力 | 本 topic 复用原则 | §架构 |
| 2026-05-11 | 纠正流程：建立隔离 worktree 并创建 tracked topic | worktree `feature/github-activity-report-skill` | §Provenance |
| 2026-05-11 | 复制 `composing-data-insights`，新增 `github-activity-report` skill、references、采集脚本、归一化脚本、渲染脚本和 fixture-first 测试 | source commit `b33e7aa4d51e7d1deb02d6003018f57dd360fcb8`；本分支 diff；skill-specific pytest | §组件 / §验收证据 |
| 2026-05-14 | 将 `composing-data-insights` 和 `github-activity-report` 移入默认 `.ai/skills/`，并把 pytest 默认收集路径同步到 `.ai/skills` | PR review follow-up；`make check` | §设计原则 / §验收证据 |
| 2026-05-13 | 修复 review 发现：无效 period fail-fast、PR stats 保留到模型、HTML completed work 链回 GitHub evidence；首版 scope 明确为显式 Projects v2 owner + number | commit pending；targeted pytest / full checks | §设计原则 / §数据流 |

## In-progress

| plan / PR | 当前目标 | 阻塞点 | 下一步验证 |
|-----------|----------|--------|------------|
| `.ai/superpowers/plans/active/2026-05-github-activity-report-skill.md` | 首版 skill 与离线 fixture 验证已完成；等待 PR / review | 无 | `make check` 和 skill-specific pytest 已通过 |

## TODO

- [x] 从源项目复制 `composing-data-insights` 到 `.ai/skills/composing-data-insights/`，并在实现 PR 中记录源仓库和 commit — 验收：原 smoke 文档和脚本存在，HTML-only smoke 可离线运行或有明确验证命令。
- [x] 完善 `composing-data-insights` 以支持上游 report model 作为输入 — 验收：GitHub report model 能复用 four-bucket analysis 和 HTML 模板。
- [x] 新增 `.ai/skills/github-activity-report/` — 验收：SKILL.md、references、scripts、smoke fixtures 存在。
- [x] 更新默认安装边界 — 验收：两个 report skills 位于 `.ai/skills/`，`skills/README.md` 仅保留未来候选能力说明。
- [x] 实现 GitHub Projects v2 只读采集 — 验收：mock `gh api graphql` 测试覆盖 project metadata、field values、reviews、commits、redacted item。
- [x] 实现 GitHub raw JSON 归一化 — 验收：fixture 测试覆盖 issue、PR、draft issue、redacted item、字段冲突。
- [x] 实现 Markdown / HTML 渲染 — 验收：生成报告包含 summary、progress、completed work、risks、people activity、coverage caveats。
- [ ] 实现 org / team / repo / person 到 Projects v2 候选列表的 discovery 查询 — 验收：多个候选时列出并要求用户确认，不静默选择。
- [ ] 回填用户反馈入口状态 — 验收：对应反馈项完成后将待办更新为已完成。

## 风险与回滚

- GitHub Projects v2 API 和权限模型变化会影响 live smoke；核心验证必须依赖 fixture，live smoke 只作补充。
- 复制 `composing-data-insights` 后若与模板仓库 skill 约定冲突，应优先调整 optional skill 的路径和触发描述，不改变其“不负责数据采集”的边界。
- 如果后续废弃 GitHub report 方向，应删除 `.ai/skills/github-activity-report/` 和本 topic；`composing-data-insights` 若已成为通用报告能力则可独立保留。

## 同步规则

- 每次相关工作完成或 PR 合并时，更新 `Done`；commit sha 可在可用后补。
- 行为或边界改变时，同步 `design.md`。
- 架构级取舍变更时，补 `decisions.md`。
