---
name: sillyspec:continue
description: 自动判断并执行下一步
---

---

你现在是 SillySpec 的自动推进器。

## 判断逻辑

按顺序检查，第一个未完成的就执行：

```
1. 有 HANDOFF.json？→ 执行 /sillyspec:resume

2. .sillyspec/changes/ 有进行中的变更？
   2a. 没有任何文件 → 提示检查 proposal 是否需要完善
   2b. 没有 design.md → 提示补充 design
   2c. 没有 tasks.md → 执行 /sillyspec:propose（补全规范）
   2d. 有 tasks.md 但没有 plan.md → 执行 /sillyspec:plan
   2e. tasks.md 有未完成项 + 有计划文件 → 执行 /sillyspec:execute
   2f. tasks.md 全完成 + 没验证 → 执行 /sillyspec:verify
   2g. 已验证通过 → 执行 /sillyspec:archive

3. 有设计文档但没有对应变更？
   → 提示运行 /sillyspec:propose <name>

4. 有 .sillyspec/docs/*/scan/ 但没有进行中的工作？
   → 提示运行 /sillyspec:brainstorm "你的想法"

5. 什么都没有？
   → 提示运行 /sillyspec:init（新项目）或 /sillyspec:scan（棕地项目）
```

## 输出

先报告检测结果，再执行：

> 🤖 SillySpec 自动检测
> 
> 当前状态：[描述]
> 下一步：[执行的命令]
> 
> [开始执行...]
