# `<Topic Name>` — <一句话范围>

**Status:** active | dormant | superseded-by-<slug>
**Owner surface:** <模块 / 用户流程 / 外部系统>
**Started:** <YYYY-MM>
**Last updated:** <YYYY-MM-DD>

## 读者先看

用 5-8 行说明这个 topic 当前最重要的事实：

- 这个主题解决什么长期问题。
- 当前方案是否已经在真实环境跑通。
- 哪些证据是可信证据，哪些只是辅助观察。
- 当前最大的风险 / 缺口是什么。
- 下一轮工作应该从哪里开始。

## 范围

**包含：**

- <代码路径、配置、外部集成、用户流程>

**不包含：**

- <容易混淆但不属于本 topic 的边界>

## 当前态

写成可交接的状态摘要，而不是模板占位：

- **已完成：** <可复现结果 + commit / PR>
- **进行中：** <当前 plan / branch / PR>
- **待验证：** <还没有真实证据的假设>
- **已知风险：** <失败模式、环境依赖、安全边界>

## 关键证据

| 日期 | 证据 | 结论 | 链接 / 路径 |
|------|------|------|-------------|
| YYYY-MM-DD | <测试命令 / live run / PR review> | <证明了什么> | `<path>` / PR #N |

## 关联执行历史

| 日期 | plan | 概要 | commit |
|------|------|------|--------|
| YYYY-MM-DD | `<plan-slug>` | <一句话> | `<sha>` |

## 关联 PR / issue

- <GitHub PR / issue 链接>

## 相关 topic / 共识

- `.ai/topics/<other-slug>/` — <关联点>
- `docs/README.md` "常见问题" 段 — <共识点>
