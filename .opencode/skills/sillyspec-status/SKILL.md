---
name: sillyspec:status
description: 用于查看 SillySpec 当前进度和状态。适合用户说"看下状态、当前进度、status"。显示当前阶段、步骤完成度、活跃变更。
---

## 多变更说明

如果项目有多个活跃变更（`.sillyspec/changes/` 下有多个目录），所有 `sillyspec run` 命令需要加 `--change <变更名>`。只有一个变更时可省略（CLI 自动检测）。

## 执行

**你必须使用 exec 工具（shell）执行以下命令，不要自己编造流程：**

1. 运行 `sillyspec run status` — 读取输出的步骤 prompt
2. 按照输出的 prompt **严格执行**，不要跳过或自行添加步骤
3. 步骤完成后，运行 `sillyspec run status --done --output "你的摘要"`
4. 重复 2-3 直到阶段完成
5. **禁止**在没有运行 CLI 的情况下自行决定流程

## 用户指令
$ARGUMENTS
