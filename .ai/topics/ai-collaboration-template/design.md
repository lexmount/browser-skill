# AI Collaboration Template Design

## Goal

提供一个可直接创建新 Python 仓库的模板，同时允许已有仓库手动按需复制协作骨架。模板要优先简单：少概念、少同步机制、少隐式依赖，让人和 agent 都能解释清楚。

## Core Model

模板由两层组成：

- **Project scaffold**：Python 工程基础、依赖声明、环境样例、文档入口。
- **AI collaboration scaffold**：跨 agent 规则、skills、feedback、topics、superpowers 本地执行承载位。

模板不是 runtime dependency，不通过 submodule 复用。创建新仓库用 GitHub template；已有仓库升级时按需复制文件，并在目标仓库把项目事实改成本仓库自己的事实。

## AI Collaboration Packaging

`ai-collaboration-workflow` 是 AI 协作骨架的可移植入口，不只是单个 `SKILL.md`。它的安装契约直接放在 `SKILL.md`，不单独维护 skill README，避免同一 contract 出现两份正文。面向开源发布时，它应作为 scaffold skill 携带安装说明或模板资产，用来在目标仓库创建运行时 `.ai/` 结构：

- `.ai/skills/ai-collaboration-workflow/SKILL.md`
- `.ai/feedback/README.md`
- `.ai/superpowers/specs/` 和 `.ai/superpowers/plans/active/`
- `.ai/topics/`
- `AGENTS.md` / `CLAUDE.md` 等 agent 入口片段

安装后的运行时真相源仍是仓库根目录路径。skill 包可以定义这些文件如何生成、复制或升级，但目标仓库不应为了使用协作流程而依赖整个 `ai-template-py` 仓库。

协作规则正文、coding agent 行为约束和质量闸门都放在 `ai-collaboration-workflow/SKILL.md`，避免仓库入口依赖多份强制规则正文。

## Constitution In Workflow Skill

`ai-collaboration-workflow` 是协作骨架的独立发布单元，因此把基础宪章和质量闸门放入该 skill 的 `SKILL.md`：

- `SKILL.md` 承载 Iron Laws、AI-first 原则、裁决规则、验证、范围、worktree、不可逆动作和架构闸门。
- 人机协作流程规则已并入 `SKILL.md`。
- 入口文件要求加载 workflow skill，并拥有启动要求、导航地图与认知姿态段落；这些入口专属正文不在其它文件重复。

这个结构避免把规则分散到模板仓库根路径，也避免强依赖一个额外 mandatory reference。`SKILL.md` 同时承担可发现入口和规则正文；`references/` 只保留可选重型资料。

## Progressive Skill Loading

`ai-collaboration-workflow/SKILL.md` 必须直接包含入口协议、统一决策协议、执行闭环、承载位、质量与范围闸门和收尾交接。mandatory 规则不再放入 `references/constitution.md`。

使用 `references/` 的标准是可选性和材料重量，不是重要性。若一段规则是 agent 开工必须知道的入口判断或质量闸门，留在 `SKILL.md`；只有背景资料、示例资产或任务专用长参考才进入 `references/`。

## Language Boundary

当前 PR 阶段，`ai-collaboration-workflow/SKILL.md` 使用中文正文，只保留必要英文术语，例如 `skill`、`AI-first`、`coding agent`、`PR`、`topic`、`worktree`、`review`、`commit`、`push`。这样便于当前团队 review 和维护。

正式对外发布时，再从中文真相源整理英文版。英文版不在本 PR 里提前维护，避免中英文两份正文形成同步负担；发布前需要重新校对术语、触发条件和 skill frontmatter。

## File Count Discipline

默认先合成一个 owner 清晰的文件，等内容真的膨胀、读者不同或维护节奏分裂时再拆。新增文件不是“分类更细”就成立；它必须带来明确收益，例如：

- 读者不同：项目架构读者和 Python 代码 review 读者不同，因此 `project-overview.md` 与 `python-code-style.md` 分开。
- 生命周期不同：PR body 是本 PR 的交付摘要，topic design 是长期主题边界背景，不能混成同一文件。
- 真相源层级不同：workflow rule 进 `ai-collaboration-workflow/SKILL.md`，项目 runtime 命令进 `project-overview.md`。
- 维护节奏不同：频繁变化的执行计划留在本地 active plan，稳定设计结论再上提到 tracked topic。

如果只是为了“看起来更有结构”而拆文件，通常会增加同步成本、路径迁移成本和 agent 漏读概率。Agent 新增文档前要先指出可吸收它的现有承载位，并说明为什么现有承载位不足；说不清楚时，先合并进现有文件，后续爆炸再拆。

## Worktree Location

默认 linked worktree 承载位只在 agent 入口文件的启动 / worktree 硬闸门里写具体路径，避免 workflow skill、topic 和入口文件各维护一份。这里仅保留设计理由：默认使用仓库旁侧 worktree，避免 IDE、搜索、测试和格式化工具误扫嵌套 worktree；只有用户或仓库规则明确指定时，才使用其它路径。

## Skill Discipline

`ai-collaboration-workflow` 是仓库入口和人机协作开发主流程；Superpowers 是具体任务执行体系。Workflow 弥补 Superpowers 不覆盖的仓库级治理：用户意图澄清、HIL、topic / roadmap、任务拆解、工作区、承载位、知识收口、PR 发布和最终交接。

调用和返回规则：

1. **Workflow owns context**：会话第一轮先加载 `ai-collaboration-workflow`，确认当前任务、承载位、topic / roadmap 和 HIL 状态。
2. **Superpowers executes tasks**：当 workflow 拆出具体任务，或需要 brainstorm、planning、TDD、debug、review、skill writing 等执行方法时，调用 `using-superpowers` 或对应 Superpowers skill。
3. **Return to workflow**：每次 Superpowers 执行完成后，由 workflow 接回结果，继续处理 topic / roadmap、工作区、承载位、验证、知识收口、发布边界和最终交接。
4. **Multiple rounds are normal**：一个仓库任务可以多次往返。例如 workflow 先建 topic 和 roadmap，再把子任务交给 Superpowers；执行中发现需求不清，回到 workflow 判断是否 HIL；澄清后再交给 Superpowers 继续实现。

`ai-collaboration-workflow` 不复制 Superpowers 的执行方法；它只定义何时把具体任务交给 Superpowers，以及执行结果如何回到仓库级闭环。

handoff 是行为切换点，不是阅读记录。Agent 必须能说明当前是 workflow 层判断，还是 Superpowers 层执行；例如 review feedback 交给 review 接收类 skill，规则 / skill 正文修改交给 skill 写作类 skill，失败验证交给 debug 类 skill。若没有下游 skill 适用，也要说明理由。

用户反馈、用户指令、PR comment、review、CI、工具输出和 agent 建议都不是自动 todo。处理前先分类为接受执行、用户明确要求、过期 / 错误、有效但不在范围、与用户方向冲突、或不确定。冲突和不确定项先问用户； automated review 和外部 reviewer 的建议必须先和当前代码、PR 范围及用户方向核对。

工作目录也是 discipline 的一部分。任何会产生修改的行为之前，都必须确认当前路径、branch 和 worktree 属于本任务；若已有目标 worktree，只能在那里写入。其它 checkout 只允许只读定位，否则旧分支上下文会把已完成的改动和本轮判断混在一起。

Claude slash commands 不再作为模板机制保留。`/plan-status` 和 `/resume-work` 只是把 agent 应自动完成的状态感知与恢复包装成用户命令，和 AI-first 方向冲突，也增加了 Claude 专属文件面。Claude 适配层只保留 hooks、agents、settings 和 skills 符号链接。

## Collaboration Data Flow

1. **PRD**：用户在 `docs/product-specs/` 写"做什么 / 给谁 / 凭什么算做对"。
2. **Decision routing**：写产物或对外发布前应用 `ai-collaboration-workflow` 的统一决策协议，先确定意图、输入判定、HIL、范围、工作区、工件承载位、文件数量、skill handoff、验证证据和发布边界；协作铁律与质量 / 范围闸门由该 skill 的 `SKILL.md` 裁决。
3. **Superpowers execution**：统一决策协议判断需要具体执行方法时，把任务交给 `using-superpowers` 或对应 Superpowers skill；workflow skill 不复制下游执行流程，也不干涉下游 skill 内部步骤。
4. **Spec / Topic design**：需要设计时，AI 产出本地 spec 或直接更新 topic design；应成为团队可见长期真相源的稳定结论同步到 `.ai/topics/<slug>/design.md`。
5. **Task / issue**：单次执行可由本地 plan、GitHub issue、PR comment 或 chat 承载；长期方向回写 topic roadmap。
6. **Superpowers execution**：AI 按当前任务真实需要调用 skills、修改文件、验证结果并记录证据。
7. **PR**：PR description 记录本次 Goal / Design / Validation / Risk。
8. **Comments**：review comments 回流到同一个 superpowers execution 节点继续处理；需要长期保留的设计结论回写 topic。
9. **Commit**：commit 是本轮实现证据；topic `roadmap.md` 的 Done 项应能回到 commit / PR 或对应任务承载位。

## Testing Boundary

自动化测试只服务代码和可执行行为：Python 模块、脚本入口、配置解析、命令行为、外部依赖 mock 边界。文档、规则和 skill 文案不写字符串断言测试；这些内容用 review、diff、链接检查或格式解析来保证质量。

## Project Style Boundary

`ai-collaboration-workflow/SKILL.md` 只保留可移植协作规则、协作铁律和质量 / 范围闸门，不承载项目 runtime 命令或语言栈细节。Python 模板偏好（例如 `uv`、Notebook 支持、`orjson`、`polars`）放在 `docs/references/python-code-style.md`，默认沟通语言放在 `docs/references/project-overview.md`。业务仓库可替换或删除这些项目文档，不需要修改 workflow skill。

`docs/references/project-overview.md` 是当前 `ai-template-py` 仓库的项目事实真相源：系统目标、架构分层、运行命令、依赖策略、目录边界和默认沟通语言都放这里。`ai-collaboration-workflow/SKILL.md` 说明本模板当前默认路径，同时允许消费仓库在入口文件和项目总览中替换这些路径。

## Concept Boundary

Collaboration rules, skills, constitution files, topics, local specs / plans, PR bodies, and comments are separated by carrier role. The detailed taxonomy and placement tests live in `concept-boundaries.md`.

## External Systems

模板不预设外部系统。`.env.example` 可以放模板内置 skill 的可选变量示例，例如 Notion reader 的 `NOTION_ACCESS_TOKEN`，但必须标注为可选、局部使用，不代表所有新仓库默认接入该系统。

## Reference Models

- Git `worktree`：官方文档定义 linked worktree 可让同一仓库同时 checkout 多个分支；本仓库采用它承载独立 PR / 高风险 / 长任务的隔离工作区。参考：https://git-scm.com/docs/git-worktree.html
- GitHub Spec Kit：以 constitution、spec、plan、tasks、implement 组织 spec-driven development；本仓库借鉴其“先原则和设计，再计划和任务”的阶段化思想，但保留 `.ai/topics/` 作为长期主题层。参考：https://github.com/github/spec-kit
- OpenSpec：区分当前 specs 和 proposed changes，并用 proposal / design / tasks 等 artifact 组织变更；本仓库借鉴其“稳定真相源 + 单次变更工件”的分层，但用 `.ai/topics/`、`.ai/superpowers/` 和 PR 描述适配现有协作流。参考：https://github.com/Fission-AI/OpenSpec 与 https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md

## Provenance

- 2026-05-09：根据 ai-template feedback round4 建立本 topic，补齐 worktree、文档测试边界、GitHub template 和后续数据流设计。
- 2026-05-11：补强 Lifecycle Gate，并记录参考来源；协作流程和协作规则正文由 `ai-collaboration-workflow` skill 承载。
- 2026-05-12：明确 `ai-collaboration-workflow` 的开源发布形态是 scaffold skill：它定义目标仓库的 `.ai/` 运行时骨架，但使用者不需要安装整个模板仓库。
- 2026-05-12：在 Modify 前增加 `using-superpowers` handoff，避免 workflow skill 复制或干涉 Superpowers 内部路由。
- 2026-05-12：明确默认本地 worktree 容器由入口文件承载，并将基础宪章和质量闸门并入 `ai-collaboration-workflow/references/`。
- 2026-05-13：保持官方来源 skills 正文不改，默认 worktree cleanup 归属只在协作层映射；项目 Python 偏好由入口文件指向 `docs/references/python-style.md`，不从 portable references 反向引用项目文档。
- 2026-05-13：`ai-collaboration-workflow` 开源发布契约完善——`quality-gates.md` 的 `## 代码硬闸门` 全段改写为跨语言可复用（Python 细节移入 `docs/references/python-style.md`），portable references 不再出现 `docs/references/project-overview.md` 等项目内路径；skill 自身新增 `README.md`（对外安装指引）；`SKILL.md` Runtime Scaffold contract 对齐实际依赖清单。同轮撤掉上轮在 Development Flow 表加的 candidate-skill 列，恢复本 design 中"不维护下游 Superpowers skill routing 表"的定位。
- 2026-05-13：冷启动协议调整为先加载 workflow skill，再由 workflow skill 交接给 `using-superpowers`；该表达体现入口和交接关系。
- 2026-05-13：文档收敛——`docs/references/python-style.md` 整段并入 `docs/references/project-overview.md` §11；`docs/faq/*` 4 个小问题并入 `docs/README.md` 的"常见问题"段；`docs/references/README.md` 删除（自述内容已包含在 `docs/README.md` 的 Documentation Map）。一个项目特化真相源（`project-overview.md`）+ 一个项目知识索引（`docs/README.md`）。
- 2026-05-13：review 后继续收敛 portable skill 边界：入口文件模板不再随 skill 发布，入口文件改为消费仓库拥有；`quality-gates.md` 不再固化 pytest/mypy/ruff 或默认 worktree 承载位，这些由消费仓库 project overview / entry files / worktree policy 承载；`constitution.md` 明确用户表达不确定或希望探讨时先澄清对齐再实施。
- 2026-05-13：继续按 review 收敛：`quality-gates.md` 合并进 `constitution.md` 后删除，Python 代码开发 / review 偏好移到 `docs/references/python-code-style.md`；`docs/references/project-overview.md` 吸收 `ARCHITECTURE.md`，让仓库特化事实只保留一个入口。
- 2026-05-13：继续按 review 检查重复正文：入口文件只保留启动索引和 agent 专属实现；`ai-collaboration-workflow` 删除单独 README，安装契约回到 `SKILL.md`；收尾交接细则只在 `constitution.md` 写正文。
- 2026-05-13：按 review 将 `references/constitution.md` 正文合入 `ai-collaboration-workflow/SKILL.md`，删除 mandatory reference；`CLAUDE.md` / `AGENTS.md` 保留入口专属高优先级段落，保证入口文件性能。
- 2026-05-13：入口文件共同段调整为“入口 skill 必须加载 + 其它资源按场景导航”，恢复 AI-first、工件承载位、主题层、团队可见工件等关键导航词；`CLAUDE.md` 与 `AGENTS.md` 共同段保持同步。
- 2026-05-13：抽象本轮文件合并经验：默认少文件、清晰 owner，只有读者 / 生命周期 / 真相源层级 / 权限边界 / 维护节奏明显不同时才拆文件；该规则写回 `ai-collaboration-workflow/SKILL.md` 的 Iron Laws 和决策协议。
- 2026-05-13：按 review 将 `ai-collaboration-workflow/SKILL.md` 正文改为中文，只保留必要英文术语；英文版作为正式对外发布前的整理任务，不在本 PR 维护双语正文。
- 2026-05-13：根据实际执行偏差补强规则：review comment 先判定再处理，用户表达不确定时先对齐，Modify 阶段 handoff 不是“读过 skill”的同义词，任何会产生修改的行为前都必须确认 worktree 隔离。
- 2026-05-13：删除 `.claude/commands/`。状态感知和恢复工作由 agent 入口 skill、hooks 提醒和 workflow 决策协议承载，不再用 slash commands 作为兜底。
- 2026-05-13：彻底重构 `ai-collaboration-workflow/SKILL.md`，去掉重复段落和 review 专属窄化，把 review comment 判定合入覆盖所有用户反馈、指令、评论、CI、工具输出和 agent 建议的统一决策协议。
- 2026-05-13：按跨仓库 / 当前仓库边界再次去重：`ai-collaboration-workflow/SKILL.md` 去掉本仓库 project overview / Python style 具体路径，`docs/references/project-overview.md` 承担这些当前仓库路径和职责边界。
- 2026-05-13：明确 workflow 与 Superpowers 的分层：workflow 管整个人机协作开发流程、topic / roadmap、任务编排、HIL、承载位、验证、发布和收尾；Superpowers 管具体任务执行。两者可多轮往返，每次执行完成都回到 workflow。

### Path Migration Map（供历史 review 评论回溯）

历史 PR 评论可能指向已迁移路径，等价路径如下：

| 历史路径 | 当前承载位 |
|----------|-----------|
| `.ai/constitution/constitution.md` | `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `.ai/constitution/collaboration-rules.md` | 已合并进 `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `.ai/constitution/quality-gates.md` | 已合并进 `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `.ai/skills/ai-collaboration-workflow/references/constitution.md` | 已合并进 `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `.ai/skills/ai-collaboration-workflow/references/collaboration-rules.md` | 已合并进 `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `.ai/skills/ai-collaboration-workflow/references/quality-gates.md` | 已合并进 `.ai/skills/ai-collaboration-workflow/SKILL.md` |
| `docs/references/python-style.md` | `docs/references/python-code-style.md` |
| `ARCHITECTURE.md` | `docs/references/project-overview.md` |
| `docs/faq/<topic>.md` | `docs/README.md` "常见问题" 段 |
| `docs/references/README.md` | `docs/README.md` Documentation Map |
