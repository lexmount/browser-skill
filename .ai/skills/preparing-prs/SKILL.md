---
name: preparing-prs
description: Use when creating or updating GitHub pull request titles and bodies, especially when the current PR text is empty, vague, commit-driven, or inconsistent with the established PR structure
---

# Preparing PRs

## Overview

PR 文案应当是"变更摘要"，不是"提交记录翻译"。正文按本 SKILL 约定的三段式组织，信息密度以"能让 reviewer 快速抓住主题与风险边界"为准。标题默认使用英文。

## When to Use

- 新建 PR，需要整理标题和正文
- 修改已有 PR，发现当前标题或正文质量不够
- 同一 `head/base` 已经存在 PR，需要更新而不是重复创建
- 用户明确要求整理或规范化 PR 文案

不要在这些场景使用：

- 只做本地提交，不准备提 PR
- 只处理 merge / cleanup，不改 PR 文案
- 只需要跑验证，不需要整理 PR 标题正文

## Decide Whether to Open a PR First

本 SKILL 只承担"已决定要出 PR"之后的文案整理，不承担"要不要出 PR"的选型。如果用户还没明确，要先走 `finishing-a-development-branch`（或同等的"分支完结"流程），让用户在"本地 merge / push 并开 PR / 保留分支 / 丢弃"中选定后再回到本 SKILL。

可以直接进入后续步骤的场景：

- 用户明确说"提 PR / 开 PR / 创建 PR / 更新 PR"
- 分支已存在对应 PR（走后面的 "Existing PR Rule"）
- 用户要求整理或规范化 PR 文案

## Branch & Commit Confirmation

开始为新 PR 起草标题/正文之前，必须先和用户对齐分支范围与提交清单，不得直接假设 `main` / 当前分支是目标：

- **先问 head 和 base**：显式向用户确认"这个 PR 从哪个分支提到哪个分支"，即使当前 checkout 的分支看起来显然
- **列出两侧最新状态给用户审核**：
  - `head` 分支 tip 的短 SHA 和 commit message
  - `base` 分支 tip 的短 SHA 和 commit message（先 `git fetch origin <base>`，以远端为准，不信任本地可能落后的引用）
  - `base..head` 的全部未合入提交，标注其中哪些是 merge commit、哪些是空 message 等异常 commit
  - 如有 squash-merge 过的历史遗留（SHA 在 head 但 patch 已在 base 上），用 `git cherry -v <base> <head>` 或净 `git diff --stat <base>..<head>` 对比说明，避免用户误解规模
- 用户明确确认 head、base、提交范围后，再进入起草阶段

## Core Rules

### 1. 先读真实变更，再写 PR

写 PR 文案前至少读取：

- 当前分支相对 base 的全部未合入提交
- 当前分支相对 base 的实际 diff
- 若仓库维护了设计文档、执行计划、决策记录（例如 `docs/`、`design/`、`adr/`、`rfcs/` 等目录）且与本次改动相关，一并读取
- 当前会话里真实跑过的验证结果

不要只看其中一个提交，也不要直接把 commit message 拼成 PR 文案。标题和正文都必须覆盖"当前分支相对 base 仍未合入"的完整变更范围。

### 2. 标题规则

- 标题默认使用英文
- 以fix或feat为开头
- 标题以动词开头，使用祈使/现在时（`Add X`、`Fix Y`、`Refactor Z`、`Support …`），避免过去式/完成时（`Added X`、`Fixed Y`、`X has been fixed`）
- 标题总结"这一组未合入改动的主题"，不是重复单个 commit message
- 如果分支包含几类相关改动，选一个 umbrella title，把细节放到正文

### 3. 正文固定结构

正文默认使用以下三段（section 名按仓库正文语言选用对应翻译，例如中文仓库用 `变更概述 / 主要改动 / 影响说明`）：

```
### Summary
### Changes
### Impact
```

另有两段 **optional** 小节，默认启动`links`而不启动`Approach`（但可以询问用户后启用），并保持固定顺序：

- `### Approach`（放在 `### Changes` 之前）—— 当本 PR 含技术选型争议、非显然的方案权衡或推翻了上一轮设计时启用；只记决策与 tradeoff，不复述"改了哪些代码"。典型触发：reviewer 之后会问"为什么选 A 不选 B"
- `### Links`（放在 `### Impact` 之后，即正文最末）—— 当本 PR 引用外部资料（设计文档 / issue / Slack thread / Wiki 等）≥ 2 条时启用；单条引用直接内联在 `Summary` 里即可，不必单列一段

要求：

- `Changes` 拆成 2-4 个 `#### 1.` / `#### 2.` 主题小节
- 每个小节只讲一类改动，不做文件清单堆砌
- `Impact` 讲行为、边界、风险变化，不重复"改了哪些文件"
- `Approach`（若启用）按"方案 / 替代方案 / 取舍原因"组织，不超过 3-5 句；**不要**复述 `Changes` 的内容
- `Links`（若启用）用标准 Markdown 列表 `- [标题](url)`；单行一条，不加长段描述（原因放回 `Summary` 或 `Approach`）
- 验证段落（如 `Verification`）不是默认必填；只有用户明确要求，或当前 PR 特别需要强调验证边界时才单列出来
- 如果需要写验证段落，必须使用标准 Markdown checklist：完成项写 `- [x]`，未完成/阻塞项写 `- [ ]`，不要使用 `- [√]`
- 为了让结果更醒目，每个 checklist 项后面要补一行结果标识，并与 checklist 项之间保留一个空行；通过写 `✅ passed: ...`，失败写 `❌ failed: ...`，阻塞写 `❌ blocked: ...`（语言跟随正文）

### 4. 正文写法

- 正文语言跟随当前仓库已有 PR 的惯例；若无明显惯例默认中文，不要中英文混写
- 先写整体摘要，再写分组细节
- 摘要和分组必须覆盖当前分支相对 base 的全部未合入提交，不能只挑其中一部分
- 适度引用关键路径或模块名，使用实际受影响的具体文件路径
- 只写和这次 PR 相关的事实，不补无依据推断

## Edge Cases

- 分支只有一个 commit：仍然用三段式结构写正文，不可直接复制 commit message 当标题。单个 commit 的标题也应总结变更主题而非用 commit message 原文
- 多人协作分支（多人 commit 混合）：标题用 umbrella title 概括全部改动，正文 `Changes` 按主题（而非按人）分组，尽量归纳为 2–4 个主题小节
- 纯文档 / 配置变更（无代码逻辑改动）：同样遵循三段式结构，`Impact` 可简写为"无行为变化"或"仅文档更新"
- 紧急修复 / hotfix：三段式仍然适用，但此时 `Impact` 应特别强调风险和回滚策略

## Existing PR Rule

如果同一 `head/base` 已经存在 PR：

- 更新已有 PR
- 不创建重复 PR
- 如果本地分支内容变了，先同步分支，再改 PR 标题和正文

## GitHub CLI Workflow

优先使用下面的稳定命令序列，减少无效尝试：

1. **定位仓库与 PR**
   - `gh repo view --json nameWithOwner -q .nameWithOwner`
   - `gh pr list --head <head> --base <base> --json number,title,url,state`
   - `gh pr view <number> --json number,title,url,state,headRefName,baseRefName,commits`
2. **读取评论**
   - 普通评论 / review summary：`gh pr view <number> --comments --json comments,reviews`
   - inline review comments：`gh api repos/<owner>/<repo>/pulls/<number>/comments --paginate`
3. **创建 / 更新 PR**
   - 创建：`gh pr create --base <base> --head <head> --title "<title>" --body-file <file>`
   - 更新正文：`gh pr edit <number> --body-file <file>`
   - 提交修复说明：`gh pr comment <number> --body "<summary>"`
4. **回复 inline comment**
   - `gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment_id>/replies -f body="<reply>"`
   - 不要使用 `repos/<owner>/<repo>/pulls/comments/<comment_id>/replies`；该路径会 404。

PR body 草稿仍写到 `.git/pr_body_<slug>.md` 或同等本地临时文件，避免 shell quoting 破坏 Markdown。

## Review Feedback Workflow

当用户要求"根据 PR 评论继续修改"或同等意思时：

1. 读取普通评论、review summary、inline review comments。
2. 对每条评论做技术判断：正确就修；不正确或与用户先前决策冲突就用技术理由回复。
3. 修复后重新运行相关验证。
4. 提交并推送当前 PR 分支。
5. 按需更新现有 PR body 中的变更和验证结果。
6. 提交一个 top-level PR comment，总结本轮修复与验证。
7. 回复已处理的 inline comment 线程。

### Review follow-up 优先级

用户明确要求处理 PR review（例如"根据评论继续修改"）时，这条指令已经授权本轮必要的 PR 维护动作：推送修复、更新现有 PR body、发布处理摘要、回复 inline thread。此时不再套用下面的草稿确认流程。

仍需单独确认的动作：merge、close PR、force push、删除分支、发布版本、对外通知等不可逆或高风险动作。

## Draft Confirmation

本节适用于新建 PR，或用户单独要求整理 / 改写 PR 文案但尚未授权提交。`gh pr create` / `gh pr edit` 执行前，必须先把拟定的标题和正文写成 `.git` 下的临时文件，并将路径贴给用户，待用户确认并明确同意后再实际提交：

- 若用户要求修改，先改草稿并再次写入临时文件，寻求用户确认和同意后再提交，不要边改边提交
- 未得到用户明确同意（例如"可以"、"提交"、"就这样"）前，不得执行 `gh pr create` / `gh pr edit`
- 仅当用户在当前会话明确授权"直接提交无需再确认"，或任务属于上面的 review follow-up，才可跳过此步

## Template

最小版（只有必选段）：

```md
### Summary

This PR ...

### Changes

#### 1. ...

- ...

#### 2. ...

- ...

### Impact

- ...
```

含 optional 段的完整版（只在触发条件满足时加）：

```md
### Summary

This PR ...

### Approach

- 为什么选 A 而不是 B：...
- 主要 tradeoff：...

### Changes

#### 1. ...

- ...

#### 2. ...

- ...

### Impact

- ...

### Links

- [设计文档](url)
- [Issue](url)
```

## Common Mistakes

- 用 commit message 直接当 PR 标题
- 无视仓库已有 PR 惯例，机械添加或强制去掉前缀
- body 只写远端已推送的一小段改动，漏掉当前分支其他未合入提交
- 机械补一个验证段落，但里面没有任何必要信息
- 正文为空，或者只有一句话
- 分支已经有 PR，却又重复创建一个新的
- 标题或正文残留 `Co-Authored-By: Claude`、`🤖 Generated with Claude Code`、`Generated with Claude Code` 等 AI 署名或工具标记

## Verification Checklist

PR 提交前，必须对本次 PR 涉及的所有 commit 执行对应的验证（例如单元测试、lint、类型检查），并在 PR 评论或输出中显式报告结果。若正文包含 `Verification` 小节，使用标准 Markdown checklist，并在每项下方补结果标识：

```md
- [x] `<项目对应的测试/验证命令>`

  `✅ passed: 34 tests passed`
- [ ] `<其他验证命令>`

  `❌ blocked: ModuleNotFoundError: ...`
```

要求：

1. 列出当前 PR 所有 commit 涉及的代码文件和模块
2. 根据仓库的测试约定定位对应的测试文件或命令（例如 pytest、jest、cargo test、go test、`npm test` 等）
3. 逐个运行相关验证命令，记录结果（`- [x]` / `- [ ]` + 下一行结果标识和原因）
4. 如果某模块没有现有测试覆盖，标注为 `- [ ] no existing tests`，并补 `❌ blocked: no reusable tests`
5. 验证全部通过后方可提交 PR；存在失败需先修复或在 PR 中说明原因
