# Product Specs — 产品规格（PRD）

本目录承载**产品规格 / 需求 / 用户场景 / 验收标准**（Product Requirement Documents, PRD）。由**用户**按需建立；AI 不主动搬。

## 何时写 PRD

- 新功能方向未明，需要先约束"做什么 / 给谁 / 凭什么算做对"
- 某产品决策跨多次实施（跨多个 plan）需要一份稳定参考
- 需要和团队 / 外部干系人对齐需求 / 验收

## 何时**不**在这里写

- 技术方案 / 模块设计 → `.ai/topics/<slug>/design.md`
- 单次实施流程 → `.ai/superpowers/plans/active/<slug>.md`
- 外部第三方协议 / 部署约束 → `docs/references/`
- 用户给 AI 的反馈原料 → `.ai/feedback/<YYYYMMDD>_<slug>/`

## 创建方式

```bash
cp docs/product-specs/_template.md docs/product-specs/<slug>.md
```

## 文件命名

- 一个 PRD 一份文件：`<slug>.md`（示例：`data-export.md` / `admin-audit-log.md`）
- 不分 active/archive；过时直接 `git mv` 搬到 `docs/archive/product-specs/`

## 与其它承载位的分工

| 位置 | 视角 | 内容 |
|------|------|------|
| `docs/product-specs/<slug>.md` | **做什么** | 产品视角，用户 + 团队对齐 |
| `.ai/topics/<slug>/design.md` | **怎么做** | 技术方案、模块设计 |
| `.ai/superpowers/plans/active/<slug>.md` | **这轮做哪一部分** | 单次实施拆解（gitignored） |
| `docs/references/<topic>.md` | **外部约束** | 第三方协议、部署依赖 |

## 文档边界

`docs/product-specs/` 只承载产品视角的需求和验收，不承载架构规则、协作流程或执行计划。
