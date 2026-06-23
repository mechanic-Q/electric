---
name: sillyspec:state
description: 查看当前工作状态 — 显示 progress.json 内容
---

你现在是 SillySpec 的状态查看器。

## 流程

### 1. 读取 progress.json

```bash
sillyspec run state --status 2>/dev/null
```

### 2. 如果有 progress.json

格式化展示当前状态：

> 📊 当前状态
>
> **变更**：<名称>
> **阶段**：<当前阶段>
> **进度**：<具体进度>
> **下一步**：<命令>
>
> **阶段进度**（大模块）：
> （显示各阶段状态表）
>
> **关键决策**：
> - xxx
>
> **阻塞项**：
> - xxx（如无则省略）

### 3. 如果没有 progress.json

提示用户项目还没有开始，或 progress.json 尚未生成：

> 📊 还没有工作记录。
>
> 开始使用：
> - 新项目：`/sillyspec:init`
> - 已有项目：`/sillyspec:scan`
> - 恢复中断的工作：`/sillyspec:resume`
>
> progress.json 会在 `sillyspec init` 时自动创建。

### 注意

- 这是只读命令，**不修改任何文件**
- `/sillyspec:status` 查看项目整体进度（change 文件级别）
- `/sillyspec:state` 查看当前工作状态（progress.json 级别）
- 两者互补：status 看"有什么"，state 看"在做什么"
