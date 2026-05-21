# AI Collaboration Template Roadmap

## Done

- 2026-05-09  明确模板复用策略：GitHub template / 普通 clone 创建新仓库，已有仓库按需复制；不推荐 submodule。
- 2026-05-09  去掉 `docs/topics`、`.ai/templates` 等平行概念，长期主题统一到 `.ai/topics/<slug>/`。
- 2026-05-09  将项目专用 skills 从模板边界中排除，只保留通用流程 skills。
- 2026-05-09  依赖安装回到 `pyproject.toml` + `uv pip install`，模板不提交、不依赖 `uv.lock`。
- 2026-05-09  增加薄入口 skill `ai-collaboration-workflow`，并将 topic 的长期路线文件从 `plan.md` 改为 `roadmap.md`。
- 2026-05-09  将人机协作流程定义和 SVG 图沉到 `ai-collaboration-workflow` skill，README / 入口文件只保留指针和图片引用。
- 2026-05-09  明确 `ai-collaboration-workflow` 是 AI 协作入口，不耦合 Superpowers 内部逻辑；收尾阶段定义为 merge 前知识收尾。
- 2026-05-09  精简入口、架构、topic、spec 文档，删除过度解释和具体 skill 产物绑定。
- 2026-05-09  统一 worktree 粒度规则，并将 plan/spec 路径 override 直接写入本仓库会调用的 Superpowers skills。
- 2026-05-09  重画人机协作流程图，主线回到人给输入、AI 判断承载位、执行验证、PR 维护、review 回流和确认合入。
- 2026-05-11  补强 Lifecycle Gate，防止工作区、结论承载位、验证证据和发布边界漂移；参考来源记录到 design.md。
- 2026-05-11  收敛收尾规则：repository work 默认给出下一步，纯问答且无后续动作时不制造空流程。
- 2026-05-12  将 AI-first 操作流程、artifact vocabulary、知识收口 checklist、协作规则、coding agent 行为约束和 quality gates 合并进 `ai-collaboration-workflow` skill。
- 2026-05-12  新增 `concept-boundaries.md`，专题澄清 collaboration rules、skills、constitution、topics、local specs / plans、PR body / comments 的分类和管控边界。
- 2026-05-12  明确 `ai-collaboration-workflow` 的可移植形态：skill 包定义目标仓库 `.ai/` scaffold，安装后运行时真相源仍在仓库根目录。
- 2026-05-12  在 `ai-collaboration-workflow` 增加 Modify 前 `using-superpowers` handoff，避免 workflow skill 指定下游 Superpowers skill。
- 2026-05-12  明确默认 linked worktree 容器由入口文件承载，并补充 `SKILL.md` / `references/` 的渐进加载和裁决边界。
- 2026-05-13  收敛 development-doc audit：finish cleanup 识别入口文件指定的默认 worktree 承载位，拆清 `using-superpowers` session / Modify 两个触发点，收窄最新状态规则，并把 Python 模板偏好移出 `quality-gates.md`。
- 2026-05-13  按 review 收回对官方来源 `finishing-a-development-branch` 正文的修改；默认 worktree cleanup 归属只保留在协作层映射，Python 模板偏好由入口文件要求读取。
- 2026-05-13  继续压缩 portable skill：移除入口文件模板资产，`quality-gates.md` 不再固化 Python 工具名或默认 worktree 容器；`constitution.md` 增加"用户表达不确定 / 希望探讨时先澄清"的 HIL 条件。
- 2026-05-13  将 `quality-gates.md` 合并进 `constitution.md`，把 Python 代码开发 / review 偏好移到 `docs/references/python-code-style.md`，并让 `docs/references/project-overview.md` 吸收 `ARCHITECTURE.md`。
- 2026-05-13  补强 repository work 收尾交接：最终回复必须说明当前状态、验证证据和用户下一步，避免提交 / push 后不指引后续动作。
- 2026-05-13  按 review 继续去重：入口文件降为启动索引 + agent 适配，`ai-collaboration-workflow` 删除单独 README，收尾交接正文只保留在 constitution。
- 2026-05-13  按最新 review 调整：`references/constitution.md` 合入 `ai-collaboration-workflow/SKILL.md` 后删除；`CLAUDE.md` / `AGENTS.md` 恢复共同高优先级原则和必须加载清单。
- 2026-05-13  按后续 review 收敛：入口文件专属段落不在 workflow skill 重复；AGENTS 并行规则改回积极使用可用并发机制；`CC_STOP_MAX=0` 明确为禁用 Stop hook。
- 2026-05-13  按入口文件 review 调整：`CLAUDE.md` / `AGENTS.md` 共同段保持同步；后续进一步收敛为 `ai-collaboration-workflow` 持有仓库主流程，`using-superpowers` 由 workflow 按需调用。
- 2026-05-13  抽象文件合并经验：默认少文件、清晰 owner，只有读者、生命周期、真相源层级、权限边界或维护节奏明显不同时才拆文件；规则已进入 workflow skill 和 topic boundary。
- 2026-05-13  将 `ai-collaboration-workflow/SKILL.md` 正文中文化，只保留必要英文术语，便于当前 PR review；英文版留到正式对外发布前再整理。
- 2026-05-13  补强执行偏差防线：review comment 先分类判定，不确定或冲突项先问用户；Modify 阶段 `using-superpowers` handoff 必须作为行为切换点；任何会产生修改的行为前先确认当前 worktree / branch 属于本任务。
- 2026-05-13  删除 `.claude/commands/`，不再保留 `/plan-status` 和 `/resume-work` 兜底；状态感知和恢复由 agent 自动执行，Claude 侧只保留 hooks / agents / settings / skills 符号链接。
- 2026-05-13  重构 `ai-collaboration-workflow/SKILL.md`：删除重复段落和窄化的 review 判定，把所有反馈、指令、评论、CI、工具输出和 agent 建议统一纳入决策协议。
- 2026-05-13  按跨仓库 / 当前仓库边界去重：workflow skill 不再硬编码本仓库 project overview / Python style 路径；这些当前仓库事实由 `docs/references/project-overview.md` 承载。
- 2026-05-13  调整 workflow / Superpowers 分层：workflow 管整个人机协作开发流程、topic / roadmap、任务编排、HIL、承载位、验证、发布和收尾；Superpowers 管具体任务执行，完成后回到 workflow。

## In-progress

- PR #1：把 lex-rpa 中沉淀出的 Python 模板骨架同步到 `ai-template-py`，并根据 review 继续压缩概念和规则。

## TODO

- 梳理协作数据流的每个对象：PRD、spec、task / issue、code、PR、comments、commit，明确它们的输入、输出、保存位置和回写规则。
- 评估 GitHub issue 是否应成为 task 的团队可见承载位；如果引入，必须避免和本地执行工件形成双真相源。
- 给"已有仓库按需复制模板更新"写一份最小操作清单：复制哪些目录、哪些必须手改、哪些绝不能覆盖。
- 补一份 GitHub template 创建新仓库后的首轮初始化 checklist，包括包名、架构、项目 overview、环境变量和 CI。
- 设计 `ai-collaboration-workflow` 独立开源发布包的安装资产：`.ai/feedback/README.md`、`.ai/superpowers/` 目录、`.ai/topics/` 模板，以及消费仓库如何自建 agent 入口文件的说明。
- 正式对外发布 `ai-collaboration-workflow` 前，从中文真相源整理英文版 `SKILL.md`，并统一术语、触发条件和 frontmatter。
- 继续审视 `.ai/topics/` 是否只保留模板文件，还是允许模板仓库自身保留少量维护 topic；原则是能解释清楚才保留。
