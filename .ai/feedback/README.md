# `.ai/feedback/` — 用户给 AI 的反馈 / 需求 / 驱动原料

承载**用户给 AI 的反馈、指令、需求简报、设计原料**。反馈驱动开发的入口。

**承载位**：`.ai/feedback/<YYYYMMDD>_<slug>/round<N>.md`，扁平 + 全 gitignored。AI 处理完把 `- [ ]` 改成 `- [x]`，不搬不删。只有本 `README.md` + `_template/` tracked。

## 推荐写法

> **需求 / 反馈写到文档，聊天框只敲 `完成 @<path>`。**

长诉求放文档比塞聊天框效率高：一屏写完十条 AI 批量处理、markdown 语法更强、本机留存可回查、多轮可并行。

## 创建方式

```bash
# 新主题
cp -r .ai/feedback/_template .ai/feedback/<YYYYMMDD>_<slug>

# 同主题追加 round
cp .ai/feedback/_template/round1.md .ai/feedback/<YYYYMMDD>_<slug>/round<N>.md
```

## 何时**不**放这里

- 第三方官方约束 → `docs/references/`
- AI 写的 spec / plan → `.ai/superpowers/plans/active/`
- 跨 change 稳定技术方案 → `.ai/topics/<slug>/design.md`

## 消费规则

- AI 每轮处理完把 `- [ ]` 改 `- [x]`；打勾后不搬不删
