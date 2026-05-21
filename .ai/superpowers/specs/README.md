# `.ai/superpowers/specs/` — 本地设计工件

本目录保存单次任务的本地 spec。`*.md` 全部 gitignored，只有 `README.md` + `_template.md` tracked。

## 定位

**spec = validated design document**：需要较完整设计时产生的本地设计文档。本地执行工件，不参与冲突裁决。

**文件名**：`YYYY-MM-DD-<topic>-design.md`（官方硬格式，带日期 + `-design` 后缀）

**内容要点**：Architecture / Components / Data flow / Error handling / Testing；每节篇幅按复杂度缩放。

## 路径 override

本仓库 spec 路径固定为 `.ai/superpowers/specs/`；已安装的 `brainstorming` skill 已按该路径调整。

## 创建方式

优先让当前工作流按需写入本目录。手动创建：

```bash
cp .ai/superpowers/specs/_template.md \
   .ai/superpowers/specs/$(date +%Y-%m-%d)-<topic>-design.md
```

## spec vs plan vs topic design

| | **spec** | **plan** | **topic design** |
|--|--|--|--|
| 定位 | 本地设计 doc | 单次 implementation plan | 跨 change 长期权威技术真相源 |
| 追踪状态 | gitignored | gitignored | tracked |
| 生命周期 | 产出后保留原状（需求变更走新 spec） | 完成搬到 `completed/` | 长期维护；被多个 spec/plan 贡献 |
| 裁决 | 不参与 | 不参与 | `docs/references/project-overview.md` 之下的主题权威 |

**铁律**：topic design 内容禁止 "见 spec X §Y" 这种 pointer 形式——design 自给自足；spec 只是产生 design 内容的来源，不是 design 依赖。

## 归档

spec 写出后留原位（本地 gitignored，保留当时设计记录）。需求被新 spec 替代时可选移到 `archive/`（按需建）；或直接保留。
