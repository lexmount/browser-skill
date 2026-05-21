---
name: ai-collaboration-workflow
description: 仓库会话入口 skill。仓库会话第一轮、续修 PR、处理反馈、调整协作规则，或判断 specs、plans、topics、验证证据承载位时使用。
---

# AI 协作工作流

## 定位

本 skill 是仓库级人机协作开发流程和 agent 行为规则正文，负责把一次自然语言请求推进到理解、澄清、计划、执行、验证、沉淀、发布和收尾。

协作流程图在 `assets/collaboration-flow.svg`。README 可以引用该图，但规则正文以本文件为准。

## 分工

| 对象 | 负责 | 不负责 |
|------|------|--------|
| 本 skill | 人机协作主流程、agent 行为规则、HIL、topic / roadmap、任务拆解、承载位、worktree、验证证据、发布边界、最终交接 | 项目 runtime 命令、具体语言风格、复制 Superpowers 执行细节 |
| Superpowers / `using-superpowers` | 具体任务执行方法，例如 brainstorm、writing plans、TDD、debug、review、skill writing、finishing branch | 仓库级真相源、项目事实、PR 发布策略、长期知识承载位裁决 |
| 项目文档 | 当前仓库事实、架构、命令、依赖、部署、默认沟通语言 | 跨仓库协作规则或执行方法 |
| 团队可见工件 | PR description、topic design、project overview 等协作输出 | 最高优先级 agent 行为规则 |

## 入口流程

仓库会话第一轮先加载本 skill。它是主流程；Superpowers 是具体任务执行体系。

启动顺序：

1. 读取本 skill，建立仓库工作流上下文。
2. 读取当前任务需要的仓库上下文。
3. 按统一决策协议判断是否需要 HIL、plan、topic、worktree 或具体执行 skill。
4. 进入具体任务执行时，交给 `using-superpowers` 或对应 Superpowers skill。
5. Superpowers 执行结束或遇到疑问后，控制权回到本 skill，继续做仓库级判断。

返回规则：任何 Superpowers 执行结束后，都回到本 skill 继续处理用户对齐、工作区、承载位、topic / roadmap、验证、知识收口、发布和最终交接。一个仓库任务可能多次往返：例如先用 workflow 建 topic 和 roadmap，再把 roadmap 子任务交给 Superpowers 执行，执行中若发现需求不清再回到 workflow 做 HIL 判断，随后继续下一批子任务。

具体项目文档路径由消费仓库入口文件或项目总览指定。本模板当前默认路径是：

- `AGENTS.md` / `CLAUDE.md`：agent 入口、导航地图和 agent 专属适配。
- `docs/references/project-overview.md`：项目边界、架构、运行命令、依赖策略、部署和默认沟通语言。
- `docs/references/python-code-style.md`：Python 代码、脚本、测试和 review 偏好。
- `.ai/superpowers/plans/active/`：本地单次执行计划。
- `.ai/superpowers/specs/`：本地设计草稿。
- `.ai/topics/<slug>/`：跨轮长期主题。
- `.ai/feedback/<slug>/round<N>.md`：用户反馈原料。

复制到其它仓库时，入口文件和项目总览可以替换这些路径；本 skill 的职责不变。

## 铁律

以下规则不可绕过。不要把它们混进“质量闸门”里；质量闸门只负责验证、范围、风险和代码质量。

1. **AI-first**：AI 引导流程和下一步；用户提供 context 与关键判断。不要让用户手工驱动 agent 本该恢复、判断和推进的流程。
2. **先判断再行动**：用户表达不确定、征询判断或希望共同探讨时，先给判断和取舍；方向明确、改动可逆且不锁定设计时才直接执行。
3. **输入不是自动 todo**：用户反馈、PR comment、review、CI、工具输出和 agent 建议都要先判定正确性、时效、范围和用户方向。
4. **非琐碎工作必须有 plan**：多文件、跨模块、协作骨架、规则语义或高风险变更，动手前建立本地 active plan；纯 typo / 路径引用 / 格式小修可不建。
5. **写入前必须确认 worktree 隔离**：任何会产生修改的行为之前，先确认当前路径、branch 和 worktree 属于本任务。已有目标 worktree 时，只能在该 worktree 修改。非目标 worktree 只允许只读排查；如果发现自己已经写错位置，立刻停止新改动，把自己的误改迁回目标 worktree，并清理误改工作区。
6. **完成声明前必须验证**：没有本轮新证据，不说完成、已修复、通过或 done。
7. **少文件和单一真相源**：默认合并到现有 owner 清晰的文件；只有读者、生命周期、真相源、权限边界或维护节奏明显不同时才拆文件。同一规则只保留一份正文。
8. **反特例化 / 先搬业界再自造**：新增或修改长期规则、hook、agent、command、skill 时，先查成熟开源方案和官方 docs，优先采用通用抽象；现有方案不满足时才自建。规则必须是 framework 级抽象，不能只覆盖本次症状、句式或关键词。
9. **文档只保存最新状态**：规范、README、project overview、skill 正文只描述当前状态，不写“原本 X 现在 Y”或“第 N 轮新增”。演进历史交给 git、PR、roadmap、Provenance 或 decision log 承载。

## 统一决策协议

写代码、文档、topic、本地草稿、测试、commit、push、PR body 或回复评论前，先完成一次决策。只读搜索可以先做；任何会改变仓库、外部状态或团队认知的动作都要过本协议。

| 判断项 | 必须回答 |
|--------|----------|
| 意图 | 用户是在下命令、表达偏好、提出不确定想法，还是要求共同判断？ |
| 输入判定 | 输入是否正确、当前、在范围内、与用户方向一致？是接受执行、用户已明确要求、过期 / 错误、有效但不在范围、与用户方向冲突，还是不确定？ |
| HIL | 能否用现有文档、topic、PR/git 历史和代码自解？只有语义会实质影响交付物、业务取舍无法解出、需要凭据/外部访问、不可逆或高风险时才停下来问用户。 |
| 范围 | 小形式修正、同 PR follow-up、独立 PR、长期规则 / 架构变更、bug fix、review fix，还是高风险变更？是否需要 active plan？ |
| 工作区 | 当前路径 / branch / worktree 是否属于本任务？不属于时只能执行只读定位，先切到正确 worktree；禁止在非目标 worktree 写文件。 |
| 承载位 | 结论应留在 chat、PR body / comment、project overview、reference doc、tracked topic，还是本地 plan / spec？ |
| 文件数 | 现有文件能否承载？只有读者、生命周期、真相源层级、权限边界或维护节奏明显不同时才新建文件。 |
| 执行交接 | 是否进入具体任务执行？该交给哪个 Superpowers skill / 执行流程？执行结束后要回写哪些 workflow 承载位？ |
| 验证 | 本轮什么新证据能证明改动？ |
| 发布 | commit、push、PR 更新、外部通知或破坏性动作是否已有当前范围授权？ |

用户出现“我感觉”“可能”“你觉得呢”“一起看看”“不确定”等探讨信号时，先给判断和取舍；只有方向明确、改动可逆且不锁定设计时才直接执行。

## Superpowers 交接

交给 Superpowers 前，workflow 要说清：

- 任务边界：解决什么，不解决什么。
- 可用上下文：项目文档、topic、plan、PR 评论或反馈路径。
- 期望产物：代码、计划、验证证据、review findings、调试结论等。
- 回传条件：执行完成、发现需求歧义、遇到技术阻塞、命中不可逆动作。

Superpowers 解决不了的问题不要直接甩给用户。先回到 workflow：

1. 查项目文档、topic、PR/git 历史、代码和本 skill。
2. 能自解就继续推进，并把判断写进 plan Decisions 或相关 topic。
3. 解不出且会实质影响交付物，才向用户提出具体问题。

常见往返：

- 需求不清或需要设计：workflow 先判断是否要 HIL / topic，再交给 brainstorming 或 planning。
- roadmap 子任务明确：workflow 选定子任务边界，再交给 executing plans、TDD 或 subagent 流程。
- 反馈 / review / PR comment：workflow 先用统一决策协议判定，再交给 review 接收类 skill 做技术核对。
- bug、失败检查或异常：workflow 保持范围和承载位，交给 debug 类 skill 定位根因。
- skill 或规则正文：workflow 判断规则归属和文件边界，交给 skill 写作类 skill 做结构和触发条件检查。

## 执行闭环

| 阶段 | 要做什么 | 典型承载位 |
|------|----------|------------|
| 理解 | 确认目标、范围、风险、工作区、承载位、验证和发布边界 | chat、feedback、PR comment |
| 修改 | 在统一决策协议和必要 handoff 后做最小正确改动 | code、docs、config |
| 验证 | 运行能证明本轮改动的检查，不复用旧结果 | command output、CI、browser/runtime evidence |
| 收口 | merge 前保存稳定结论，避免只留在 chat、本地 plan 或 comment | topic docs、PR body、reference docs |
| 发布 | 在授权范围内 commit、push、更新 PR、回复 thread | git、GitHub |
| 交接 | 明确当前状态、证据、风险和用户下一步；无需用户动作时也要说清 | final response、PR comment |

修复、验证和必要收口完成前，不回复“已修复”，不更新 PR body 声称完成。

## 承载位

| 名称 | 路径 | 追踪 | 用途 |
|------|------|------|------|
| Topic | `.ai/topics/<slug>/` | 是 | 跨 session / PR 的长期主题 |
| Topic design | `.ai/topics/<slug>/design.md` | 是 | 稳定设计、边界和取舍 |
| Topic roadmap | `.ai/topics/<slug>/roadmap.md` | 是 | Done / in-progress / TODO |
| Execution plan | `.ai/superpowers/plans/active/<slug>.md` | 否 | 单次执行 checklist 和验证记录 |
| Local spec | `.ai/superpowers/specs/<slug>.md` | 否 | 本地设计草稿 |
| PR body | GitHub PR | 是 | 当前 PR 的 Goal / Design / Validation / Risk |

稳定结论不能只留在本地 plan / spec。若 topic 决策升级为项目架构真相，先更新消费仓库指定的项目总览或架构文档。

放置边界：

- 协作流程和 agent 行为规则：本 skill。
- 项目事实、架构、命令、依赖、部署、默认沟通语言：项目总览或入口文件指定的架构文档。
- 语言 / 框架风格：项目总览或专门的 language style reference。
- 长期主题设计：`.ai/topics/<slug>/design.md`。
- 单次执行 checklist 和验证记录：`.ai/superpowers/plans/active/<slug>.md`。
- 当前 PR 的交付摘要：PR description 的 Goal / Design / Validation / Risk。

发生冲突时，先按本 skill 的 agent 行为规则判断；项目事实以消费仓库指定的项目总览 / 架构文档为准；当前 PR 的特殊决策只在本 PR 范围内生效。

## 质量与范围闸门

质量闸门不是铁律本身；它们是声明完成前必须满足的检查口径。

- **验证**：测试、lint、type check、运行验证、diff review、frontmatter / Markdown 解析、链接检查等，按改动类型选择。文档措辞不写脆弱字符串测试。
- **范围**：优先最小正确改动；不做未授权的大范围 refactor、跨模块 rename、投机抽象或无关清理。
- **Fail-fast**：不要吞错，不要用默认值替代必填字段，不要在必经流程周围加“缺失就跳过”。防御性处理只属于输入校验、cleanup、cancellation 或兼容 shim。
- **删除**：被替换文件能删就删；只有稳定外部引用合同时才保留薄跳转。
- **完成声明**：最终回复必须说明当前状态、验证证据和用户下一步；真的无事可做时明确说无需用户操作。

### HIL

默认不打断用户。能用现有文档、topic、PR/git 历史、代码和当前指令自解的，agent 继续推进并在最终交接里说明判断。尤其这些情况不需要 HIL：

- 用户方向明确，改动可逆，且不会锁定设计。
- 同一 PR 的 review follow-up、PR body 更新、review thread 回复或普通 PR comment，已在当前任务范围内授权。
- review / CI / 工具输出经过核对后确认为正确、当前、在范围内。
- 只是同步入口表述、路径引用、文档归属、格式或低风险 wording。
- 执行环境弹出常规 sandbox / 网络 / 写入审批，但动作本身已在任务范围内；此时按工具审批流程申请，不把工具权限摩擦升级成产品 HIL。

可以在交接中提醒用户开启适合仓库工作的 auto / auto-approve 模式，让常规文件写入、测试、PR 维护等低风险动作自动通过。

### Worktree

任何会产生修改的行为之前，都必须检查入口文件要求的启动 / worktree 硬闸门，确认当前路径、branch、远程同步状态和 worktree 属于本任务。会产生修改的行为包括但不限于：编辑文件、格式化、生成文件、删除文件、安装依赖写 lock/cache、stage、commit、push、PR body 更新和评论回复。

独立 PR、高风险工作或长任务使用 linked worktree；同一任务 / 同一 PR follow-up 复用已有目标 worktree。

若当前 shell 不在目标 worktree：

1. 只允许运行只读定位命令，例如 `git status`、`git worktree list`、`git branch --show-current`、`git log`。
2. 切到目标 worktree 后再写文件、运行格式化、生成文件、stage、commit、push 或对 PR 产生状态变更。
3. 如果已经在错误工作区产生修改，先停止继续编辑；确认这些修改是 agent 本轮误改后，迁移到目标 worktree，并清理错误工作区。

## 收尾交接

仓库工作的最终回复必须包含：

- 当前状态：commit、push、PR body / comments，以及相关时的 worktree 干净状态。
- 本轮验证证据。
- 用户的具体下一步；或明确说明无需用户操作，以及下一步由哪个系统 / 人承载。

交接不是礼貌性结尾，而是流程的一部分。每轮完成后都要把下一步说成可执行动作，例如“刷新 PR 看 Files changed”“等 CI 完成”“确认这个讨论项后我再搬目录”“无需操作，下一步由 reviewer / CI 承载”。不要只说“完成”。

## 常见错误

- 把最高优先级协作规则误解成团队工件层级，又把 PR body、topic design、project overview 当成规则正文。
- 把铁律混进质量闸门，导致“必须怎样协作”和“怎样证明做完”混在一起。
- “项目文档由消费仓库指定”之后只列抽象类别，不告诉当前仓库实际路径。
- Superpowers 一遇到疑问就问用户，没有先回到 workflow 查项目文档、topic、PR/git 历史和代码。
- 把输入判定、review 判定和决策协议拆成多套重复流程。
- 新建文件只是为了显得分类清楚，没有证明读者、生命周期、真相源、权限边界或维护节奏确实不同。
- 没有先确认 worktree 隔离，就在当前 shell 里编辑、格式化、生成文件、stage、commit、push 或回复 PR。
