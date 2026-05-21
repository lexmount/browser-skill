# [Feature Name] Design

> **本文件是单次任务的本地设计 spec**。
> 实施 plan 见 `.ai/superpowers/plans/active/<slug>.md`；跨多轮长期主题见 `.ai/topics/<slug>/`。

**Topic:** `.ai/topics/<slug>/`（若本 spec 属某长期主题）
**Created:** YYYY-MM-DD
**Status:** draft / approved / superseded-by-<newer-spec>
**Source:** `.ai/feedback/<group>/round<N>.md` / PR comment / user request

---

## Overview

<1–2 段：本 spec 在解决什么问题、交付什么价值。>

## Architecture

<整体架构，2–3 段或一张 mermaid 图。>

## Components

<模块划分 + 职责 + 接口。按复杂度伸缩：简单项目几句话，复杂项目详细列表。>

### Component A

- **Responsibility:**
- **Interface:**
- **Dependencies:**

### Component B

- **Responsibility:**
- **Interface:**
- **Dependencies:**

## Data Flow

<数据 / 事件在 components 间如何流动。适合 mermaid sequence diagram。>

## Error Handling

<失败模式 + 兜底策略 + fail-fast 边界。>

## Testing

<测试策略：单测 / 集成 / 验收；哪些不能测 / 为什么。>

## Scope

### Included

- ...

### Not Included (Non-Goals)

> 显式列出**不做**什么，防止范围蔓延。

- ...（理由）
- ...（理由）

## Success Criteria

> 每条标准都应可通过测试 / 验证 / 用户演示核对。

- SC1 ...
- SC2 ...
- SC3 ...

## Related

- Feedback：`.ai/feedback/<group>/round<N>.md`
- Topic (跨多轮长期主题，若属于)：`.ai/topics/<slug>/`
- Design (长期权威技术真相源)：`.ai/topics/<slug>/design.md`
- Implementation plan (产出后)：`.ai/superpowers/plans/active/<slug>.md`
- 前序 spec (若本 spec 替代或扩展)：`.ai/superpowers/specs/<prev-spec>.md`

## History

- YYYY-MM-DD: Created
- YYYY-MM-DD: Approved
- YYYY-MM-DD: Superseded by `<newer-spec>`
