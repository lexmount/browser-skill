# `.ai/superpowers/plans/` — 本地执行工件承载位

本目录是 **Superpowers skills**（`writing-plans` / `executing-plans` / `subagent-driven-development` / `finishing-a-development-branch`）的 plan 路径。`active/*.md` + `completed/*.md` 由 `.gitignore` 自动排除（本地执行工件，不入 git 索引）；只有目录 README 是显式 tracked 占位。

## 定位

- **是什么**：单次实施计划的本地执行跟踪（跨 session 供自己用）
- **谁产出**：AI
- **何时读**：接手自己本机某工作 / 回顾本机历史
- **何时产出**：任何非琐碎工作开始前（Iron Law #2）；纯形式的小改动（无业务行为变化）不建；动手中发现范围扩大则立即补 plan
- **生命周期**：`active/` 只放仍需 AI 继续推进的本地工作；工作交给 PR / 合入 / 暂停 / follow-up 时，收口状态、验证和未完成项去向后移出 `active/`
- **追踪状态**：gitignored（个人执行工件，不入团队仓库）

**团队可见层**（plan 不参与裁决后的共享真相源）：
- `.ai/topics/<slug>/design.md`（跨 change 长期主题，按需；tracked）
- PR description 四段 Goal / Design / Validation / Risk（本 PR 独有决策；从 plan 的 `## PR Description Draft` 段复制）

## 路径 override

本仓库 plan 路径固定为：

- **active**：`.ai/superpowers/plans/active/<YYYY-MM>-<slug>.md`
- **completed**：`.ai/superpowers/plans/completed/<YYYY-MM>-<slug>.md`

已安装的 `writing-plans` skill 已按该路径调整。

## 创建方式

优先让 `writing-plans` skill 按当前任务生成 plan，并保存到：

- `.ai/superpowers/plans/active/<YYYY-MM>-<slug>.md`

不要维护第二套 plan 模板。plan 结构以当前安装的 Superpowers skill 为准；本仓库只规定保存路径。

## 归档

归档时机与方法交给 `finishing-a-development-branch` skill 官方判断（该 skill 给"合并主干 / 开 PR / 暂缓"三档选项，AI 按上下文选）。命令因 plan 默认 gitignored，用 shell `mv active/<slug>.md completed/<slug>.md`（非 `git mv`）。

**归档时建议补**：结果 / 偏差 / 后续遗留项（由 skill 引导）。

## 同主题续修 vs v2

- **未归档期间同议题 followup**：追加 `## Round N` 段到既有 active plan，前轮内容保持不改
- **已归档后同议题再做**：按 skill 建议新开 `<slug>-v2.md`

## 和其它承载位的关系

| 位置 | 用途 | 追踪状态 |
|------|------|---------|
| **本目录** `.ai/superpowers/plans/active/` | 任何非琐碎工作的本地执行跟踪 | gitignored |
| `.ai/superpowers/plans/completed/` | plan 归档保存 | gitignored |
| `.ai/superpowers/specs/` | 本地设计工件 | gitignored |
| `.ai/topics/<slug>/design.md` | 跨 change 长期主题权威技术方案 | tracked |
| `docs/product-specs/<slug>.md` | PRD（用户产出） | tracked |
| `docs/references/<topic>.md` | 外部第三方约束（用户按需触发） | tracked |
| PR description 四段 | 本 PR 独有决策 | team-visible via GitHub |

plan / spec **不参与**裁决（本地、可能过期）。
