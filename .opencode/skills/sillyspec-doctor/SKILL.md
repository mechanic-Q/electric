---
name: sillyspec:doctor
description: 用于 SillySpec 自检和状态修复。适合用户说"检查下状态、修复 progress、doctor、状态不对"。全量扫描进度一致性，修复 progress.json 与实际产出不匹配的问题。
---

## 前置检查

**在执行任何检查之前，先确认 SillySpec CLI 是否可用：**

1. 运行 `sillyspec --version`
2. 如果失败：
   - 输出：❌ SillySpec CLI 未安装
   - 给出安装命令：`npm install -g sillyspec`
   - 停止，不要继续后续步骤

## 多变更说明

如果项目有多个活跃变更（`.sillyspec/changes/` 下有多个目录），所有 `sillyspec run` 命令需要加 `--change <变更名>`。只有一个变更时可省略（CLI 自动检测）。

## 执行

**CLI 可用后，使用 exec 工具（shell）执行以下命令，不要自己编造流程：**

1. 运行 `sillyspec run doctor` — 读取输出的步骤 prompt
2. 按照输出的 prompt **严格执行**，不要跳过或自行添加步骤
3. 步骤完成后，运行 `sillyspec run doctor --done --output "你的摘要"`
4. 重复 2-3 直到阶段完成
5. **禁止**在没有运行 CLI 的情况下自行决定流程

## 用户指令
$ARGUMENTS
