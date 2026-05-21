# GitHub Activity Report — Design

**Status:** active
**Last updated:** 2026-05-14

## 问题背景

团队需要一个通用 GitHub 报告能力，用自然语言指定组织、团队、仓库、Project v2 或个人范围后，自动生成日报、周报和历史活动报告。报告需要覆盖项目进度、milestone 或 iteration 变化、完成内容、风险、个人活动变化和工程效能指标。该能力属于模板仓库的长期 skill 能力，应 tracked 到 topic，而不是只停留在本地临时 spec。

已有 `composing-data-insights` 能处理结构化数据洞察、风险 framing、HTML / 图片报告模板和敏感信息检查。GitHub report 不应重复建设通用报告 skill，而应复用并完善它；GitHub 专用 skill 只负责 GitHub 数据源、Projects v2 字段模型、范围确认和归一化。

## 设计原则

- **复用优先：** 通用洞察、报告结构、HTML 模板和未来图片生成能力归 `composing-data-insights`；GitHub skill 不复制同一套报告框架。
- **默认安装：** `composing-data-insights` 和 `github-activity-report` 已放入 `.ai/skills/` 默认发现路径；两者大概率被复用，且由渐进式 skill 加载控制实际 token 开销。
- **Projects v2 核心化：** 首版把 GitHub Projects v2 当核心输入，而不是可选增强。
- **显式范围优先：** 首版本地工具要求明确的 Projects v2 owner 和 project number；org/team/repo/person 候选发现留作后续扩展。
- **证据优先：** 报告里的事实必须能回到 GitHub 数据；解释和风险必须锚定事实。
- **个人指标谨慎：** PR、review、issue、commit、changed files、增删行只作为活动量信号，禁止直接推断个人能力、绩效或排名。
- **权限透明：** `REDACTED` items、私有仓库不可见、字段缺失和 scope 不足必须出现在 Data Coverage / Limitations。

## 架构

长期能力由两个 skill 协作：

- `.ai/skills/composing-data-insights/`：共享数据洞察和报告渲染基础。它接收用户提供或上游生成的结构化数据，按 facts / interpretation / risks / recommendations 组织洞察，并生成 Markdown、HTML 或后续图片报告。它不负责联网采集。
- `.ai/skills/github-activity-report/`：GitHub 专用入口。它检查 `gh` 认证和 scope，读取明确指定的 Projects v2，采集 issue / PR / review / commit activity，归一化成 report model，再调用 `composing-data-insights` 的分析框架和模板完成报告。

这两个 skill 是模板默认安装的可复用能力：`composing-data-insights` 提供通用报告生成基础，`github-activity-report` 提供 GitHub 场景入口。根目录 `skills/` 保留给未来尚未确认默认安装价值的候选 skill。

数据采集通过 `gh api graphql` 和必要 REST endpoint 完成。Projects v2 使用 GitHub GraphQL 模型：`ProjectV2Owner` 通过 `projectV2(number:)` 或 `projectsV2` 找项目；`ProjectV2` 暴露 items 和 field values；item content 可为 Issue、PullRequest 或 DraftIssue；不可见 item 可能返回 `REDACTED`。读取 Projects v2 至少需要 `read:project` scope，私有仓库活动还可能需要 repo 权限。

## 组件

| 组件 | 职责 | 输入 | 输出 | 失败模式 |
|------|------|------|------|----------|
| `composing-data-insights/SKILL.md` | 通用数据洞察和报告生成流程 | 结构化数据、报告模式、输出路径 | Markdown / HTML / 后续图片报告 | 输入含敏感信息、数据质量不足、图片网关缺失 |
| `github-activity-report/SKILL.md` | GitHub 报告触发、范围确认、视角选择和安全规则 | 用户自然语言、GitHub 范围、时间窗口 | 采集和报告执行流程 | 范围歧义、缺少 project 确认、个人指标误读 |
| `fetch_github_activity.py` | 只读采集 GitHub Projects v2 原始 JSON，并暴露嵌套连接覆盖缺口 | owner、project number、时间窗口 | raw JSON artifact | `gh` 未登录、scope 不足、rate limit、GraphQL 错误、嵌套连接只读到首屏 |
| `normalize_activity.py` | 按时间窗口归一化 GitHub 原始数据 | raw JSON、field mapping、时间窗口 | stable report model JSON | 字段冲突、redacted item、draft issue 缺 activity、历史活动被排除 |
| `render_report.py` | 渲染 Markdown / HTML | report model JSON、模板、输出模式 | `.md` 或 `.html` | 模板缺字段、HTML 不可解析 |
| `references/github-projects-v2.md` | GitHub Projects v2 查询和权限参考 | GitHub API 文档 | 查询模板和字段解释 | GitHub API 变更 |
| `references/report-model.md` | 稳定 report model schema | 设计约束 | JSON schema / 字段语义 | 实现字段漂移 |
| `references/report-templates.md` | GitHub 报告结构模板 | report model | 管理/交付和工程效能报告结构 | 与 composing 模板重复 |

## 数据流 / 控制流

1. 用户请求 GitHub 日报、周报、历史报告、项目进展、个人活动变化或工程效能分析。
2. `github-activity-report` 判断 Projects v2 owner 和 project number 是否明确。明确时直接进入采集；不明确时要求用户补充显式 project 范围。
3. skill 检查 `gh auth status`，并对 Projects v2 读取要求 `read:project` scope。
4. `fetch_github_activity.py` 通过 `gh api graphql` 读取 Projects v2、items、field values、linked issue / PR、review 和 commit activity。Project item 外层分页必须继续读取；assignees、labels、field values、Project user fields、PR reviews 和 commits 等嵌套首屏连接若未深分页，必须写入 coverage caveat。
5. `normalize_activity.py` 生成 stable report model：period、scope、projects、items、activities、people、metrics、caveats。timestamped activity、reviews 和 commits 按 period 做闭区间过滤；有时间戳且完全落在 period 外的 item 不进入窗口指标。
6. `github-activity-report` 选择报告视角：默认管理/交付；用户明确要求工程效能时切换。
7. `render_report.py` 复用 `composing-data-insights` 的分析框架和模板生成 Markdown 或 HTML。
8. 报告必须包含 Data Coverage / Limitations，列出权限缺口、redacted items、字段冲突和不可见 repo。
9. 当前 plan / topic 更新验证结果和后续 TODO。

## 错误处理与降级

- **用户可修复错误：** 未指定时间窗口或 project 范围时，skill 提供候选 project 列表和默认时间窗口建议。
- **环境错误：** `gh` 缺失、未登录或缺 `read:project` 时 fail fast，并给出需要的 `gh auth login --scopes read:project` 方向。
- **协议 / 数据形状错误：** GraphQL 查询失败、字段结构变化、Project v2 item 类型未知时保留错误上下文并停止对应采集步骤。
- **可接受降级：** 部分 repo 不可见、commit stats 缺失、draft issue 缺少 repository-backed activity、嵌套连接只读取首屏时继续生成报告，但 caveats 必须说明覆盖缺口。
- **不可接受降级：** 不允许静默跳过 inaccessible item；不允许把缺失 commit 数据当作 0；不允许将个人活动量信号写成绩效结论。

## 验收证据

| 验收项 | 命令 / 证据 | 通过标准 |
|--------|-------------|----------|
| `composing-data-insights` 被复制并可被发现 | `test -f .ai/skills/composing-data-insights/SKILL.md` | 文件存在，references/scripts/smoke 同步 |
| GitHub report skill 被创建 | `test -f .ai/skills/github-activity-report/SKILL.md` | skill frontmatter 和主体存在 |
| 可选 skill 占位说明存在 | `test -f skills/README.md` | 说明默认 skills 已进入 `.ai/skills/`，根目录仅放未来候选能力 |
| Projects v2 采集脚本通过 | `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_fetch_github_activity.py` | mock `gh api graphql` 输出可转成 raw payload |
| fixture 归一化通过 | `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_normalize_activity.py` | 覆盖 issue、PR、draft issue、redacted item、字段冲突 |
| report 渲染通过 | `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_render_report.py` | Markdown / HTML 结构存在，HTML 可解析 |
| 全仓基础检查通过 | `make check` | pytest、ruff、mypy 通过或明确记录不可达项 |

## 开放问题

- Notion 输出和图片报告不阻塞首版，后续通过 renderer 扩展进入。
- 真实 GitHub live smoke 需要可访问 Project v2 和 `read:project` scope；离线 fixture 测试是首版必需验证，live smoke 是环境允许时的补充证据。

## 参考来源

- GitHub GraphQL `ProjectV2` object: https://docs.github.com/en/graphql/reference/objects#projectv2
- GitHub GraphQL `ProjectV2Item` object: https://docs.github.com/en/graphql/reference/objects#projectv2item
- GitHub GraphQL `ProjectV2Owner` interface: https://docs.github.com/en/graphql/reference/interfaces#projectv2owner
- GitHub OAuth scopes: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
- GitHub CLI `gh api`: https://cli.github.com/manual/gh_api

## Provenance

- 2026-05-11：需求摘要和设计决策已内联到本 tracked topic；实现阶段需要在独立分支中复制并完善 `composing-data-insights`，再新增 GitHub 专用采集 skill。
