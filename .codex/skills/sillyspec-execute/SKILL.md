---
name: sillyspec:execute
description: 用于按 plan 执行代码实现。适合用户说"开始写代码、执行任务、跑 execute、开干"。按 plan.md 中的 Wave 和 Task 逐步实现，遵循 design.md 和模块文档。
---

## 多变更说明

如果项目有多个活跃变更（`.sillyspec/changes/` 下有多个目录），所有 `sillyspec run` 命令需要加 `--change <变更名>`。只有一个变更时可省略（CLI 自动检测）。

## 执行

**你必须使用 exec 工具（shell）执行以下命令，不要自己编造流程：**

1. 运行 `sillyspec run execute` — 读取输出的步骤 prompt
2. 按照输出的 prompt **严格执行**，不要跳过或自行添加步骤
3. 步骤完成后，运行 `sillyspec run execute --done --output "你的摘要"`
4. 重复 2-3 直到阶段完成
5. **禁止**在没有运行 CLI 的情况下自行决定流程

## 用户指令
$ARGUMENTS
