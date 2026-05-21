# `.ai/topics/` — 跨多轮任务的主题层

本目录承载**大粒度、跨多轮任务的长期技术主题**。每个主题是一份**跨 change 的长期知识资产**：设计方案、roadmap、决策日志。**AI 产出 + 维护**，团队 tracked，人读但很少直接写。

## 定位

- **是什么**：跨 change 长期主题（某子系统 / 某集成 / 某长期能力）的知识资产
- **粒度**：**大于单次执行计划**（一个 plan = 一次实施；一个 topic = 会被多个 plan 反复更新的领域）
- **生命周期**：**不归档、不分 active/completed**（长期多轮跨时间维度修改）；被彻底废弃的 topic 才 `git rm`（Iron Law #5），保留在 git 历史
- **规则边界**：不承载行为约束、质量闸门或架构规则；topic 与这些规则不一致时，更新 topic
- **谁产出**：AI 主导；用户可在 feedback 或 plan Decisions 里驱动方案变化，AI 同步到 topic

## 为什么需要 topic

单次 plan 是本地执行态，适合记录"这轮怎么做"；topic 是团队可见态，适合记录"这个长期方向现在是什么状态"：

- 同一主题会跨多个 plan / PR 反复演进
- 设计边界、已完成事项和下一步需要有 tracked 载体
- plan / spec 默认 gitignored，不能作为长期团队记忆

每个 topic 用 `README.md` 导读，`design.md` 记录当前方案，`roadmap.md` 跟踪完成项与下一步；大主题再按需补 `decisions.md`。

参考最佳实践：
- **OpenSpec**（Fission-AI）：`specs/<capability>/` 含 spec.md，变更走 `changes/<change-id>/`——把能力（capability）作为长期载体
- **GitHub Spec-Kit**：`specs/<feature>/` 含 spec.md + plan.md + tasks.md——feature 粒度载体
- **Linear initiative**：跨 project 的长期目标
- **PARA Areas**：没有固定截止日的持续领域

本仓库的 `topic` 接近 "OpenSpec capability + Linear initiative + PARA area" 的合流：tech-native + long-lived + 多粒度混合（设计 / roadmap / 决策）。

## 目录结构

```
.ai/topics/
├── README.md              # 本文件
├── _template/             # 新 topic 创建模板
│   ├── README.md
│   ├── design.md
│   ├── roadmap.md
│   └── decisions.md
└── <topic-slug>/
    ├── README.md          # topic 导读：范围 / 当前 status / 关联执行历史
    ├── design.md          # 当前主题技术方案
    ├── roadmap.md         # topic 级路线图：Done / In-progress / TODO
    └── decisions.md       # ADR 决策日志（可选；大主题才有）
```

**全部 tracked**。

## 什么时候建 topic

开始非琐碎任务时，AI 先快速看是否已有相关 topic。没有匹配时按下面规则判断：

| 情况 | 动作 |
|------|------|
| 有匹配主题 | 按需更新 topic 的 `roadmap.md` / `design.md` |
| 无匹配主题 + 预计跨多轮 / 跨 PR / 未来会复用 | 新建 topic 骨架 |
| 无匹配主题 + 一次性小变更 | 不建 topic |

没达到就**不建**——避免一次性变更建空壳 topic 稀释真相源。

## 文件必选 vs 可选

| 文件 | 状态 | 内容 |
|------|------|------|
| `README.md` | 必需 | topic 导读：目的 / 范围 / 当前 status / 关联 superpowers 历史；首屏给读者定位 |
| `design.md` | 必需 | 当前最新技术方案本体（Architecture / Components / Data Flow / Error Handling / Provenance）。正文写当前状态；Provenance 可记录演进来源 |
| `roadmap.md` | 必需 | topic 级路线图：`## Done`（已完成 items；带 plan / PR / commit 等可用证据）/ `## In-progress` / `## TODO` |
| `decisions.md` | 可选 | ADR 决策日志；大主题才有（3+ 架构级决策时建）；小主题留在 design.md Provenance 段即可 |

## 和 superpowers 的结合（触发流程）

```
用户给新需求
  ↓
AI grep .ai/topics/ 找相关主题
  ├── 有 → 按需更新 topic → 进入执行流程
  └── 无 → 判"够大"？
        ├── 是 → 建 topic 骨架（cp _template）→ 进入执行流程
        └── 否 → 不建 topic

知识收尾时
  ↓
topic/roadmap.md Done 段加条目：`- 2026-XX-XX  <summary>（plan / PR / commit，哪个已可用就写哪个）`
```

## design 更新规则

需要稳定方案时，AI 在执行前创建或更新 `design.md`。执行中发现方案偏离，必须在同一轮改动里同步 `design.md`；收尾时再检查 design 是否仍代表当前状态。

## 和其它承载位的关系

| 位置 | tracked? | 粒度 | 职责 |
|------|---------|------|------|
| `.ai/topics/<slug>/` | ✅ | 跨 change 长期主题 | 方案 + roadmap + 决策 |
| `.ai/superpowers/specs/*.md` | ❌ gitignored | 单次本地设计工件 | 稳定结论按需同步到 topic |
| `.ai/superpowers/plans/active/` | ❌ gitignored | 单次实施 | 本地执行工件；知识收尾时按需同步到 topic/roadmap.md |
| `docs/README.md` "常见问题" 段 | ✅ | 跨 change 共识 QA | topic 里的争议 / 澄清沉淀 |
| PR description 四段 | ✅ | 本次 PR | 本次具体改动记录 |

完整放置规则见 [`../../docs/README.md`](../../docs/README.md) 的"放哪里"段。

## 反例

- ❌ 一次性的小改动建 topic（比如改个配置、修个 typo）—— 违反"够大"判据
- ❌ topic 分 active/completed 子目录 —— 明示不归档
- ❌ design.md 里 "`## Architecture` → 见 spec X §Y" —— 违反 design 自给自足铁律
- ❌ roadmap.md 只写 TODO 不写 Done —— Done 是"回看已做什么"的关键，必写
- ❌ 把旧 `.ai/design/` 风格的单文件再放 `.ai/topics/<slug>.md`（没子目录）—— 必须子目录，留 roadmap/decisions/README 扩展位
