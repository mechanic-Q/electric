---
name: sillyspec:brainstorm
description: 用于正式开始开发前的需求澄清和技术方案设计。适合用户提出新功能、新模块、架构调整、复杂改造，或说"先做需求分析、输出技术方案、创建变更前先梳理、帮我设计下"。产出结构化方案，但不直接写代码。
---

# SillySpec Brainstorm — 需求探索

## 用法
用户触发此 skill 时，使用 `sillyspec run brainstorm` 逐步执行需求探索。

## 执行步骤

1. 确定变更名（格式：`YYYY-MM-DD-<简短描述>`，如 `2026-05-28-agent-log-streaming`）
2. 运行 `sillyspec run brainstorm --change <变更名>` 获取当前步骤指令
3. 按步骤指令执行（对话、分析需求、设计方案等）
4. 完成步骤后运行 `sillyspec run brainstorm --done --change <变更名> --output "步骤摘要"`
5. CLI 会自动输出下一步的指令，重复 3-4 直到阶段完成

## 示例

```bash
# 首次启动（推荐指定变更名）
sillyspec run brainstorm --change 2026-05-28-agent-log-streaming

# 不指定变更名时自动生成（格式：YYYY-MM-DD-new-change）
sillyspec run brainstorm

# 完成当前步骤
sillyspec run brainstorm --done --change 2026-05-28-agent-log-streaming --output "需求已澄清"

# 查看进度
sillyspec run brainstorm --status --change 2026-05-28-agent-log-streaming

# 重置阶段
sillyspec run brainstorm --reset --change 2026-05-28-agent-log-streaming
```

## 注意
- 推荐指定 `--change <变更名>`（格式：`YYYY-MM-DD-<简短描述>`），不指定时自动生成 `YYYY-MM-DD-new-change`
- 步骤 prompt 由 CLI 管理，不需要手动读取
- 依赖 scan 阶段完成，CLI 会自动提醒
- brainstorm 阶段末步会自动生成四件套（proposal.md + design.md + requirements.md + tasks.md）
- brainstorm 完成后，运行 `sillyspec run plan --change <变更名>` 进入实现计划
