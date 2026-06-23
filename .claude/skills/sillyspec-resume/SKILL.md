---
name: sillyspec:resume
description: 恢复工作 — 从中断处继续
---

## 交互规范

**当需要用户从多个选项中做出选择时，必须使用 Claude Code 内置的 AskUserQuestion 工具，将选项传入。**

不要用编号列表让用户手动输入数字。
如果需要自由输入，在 AskUserQuestion 的选项中加入"Other（自定义输入）"。

---

你现在是 SillySpec 的恢复管理器。

## 流程

### 1. 读取进度

```bash
sillyspec progress show
```

### 2. 如果有 progress.json

从 progress.json 中提取并展示当前状态，使用 `sillyspec progress show` 查看。

然后问用户：
   1. 直接继续执行下一步
   2. 查看更多细节

### 3. 如果没有 progress.json 或变更目录

自动探测项目状态：

```bash
# 检查活跃变更
ls -d .sillyspec/changes/*/ | grep -v archive 2>/dev/null

# 检查大需求拆分
ls .sillyspec/changes/*/MASTER.md 2>/dev/null

# 检查扫描文档
ls .sillyspec/docs/*/scan/ 2>/dev/null | wc -l

# 检查需求/路线图
cat .sillyspec/REQUIREMENTS.md 2>/dev/null
cat .sillyspec/ROADMAP.md 2>/dev/null
```

根据探测结果推断：

| 探测到的文件 | 推断阶段 | 建议操作 |
|---|---|---|
| 无任何 .sillyspec/ 内容 | 未开始 | `/sillyspec:init` 或 `/sillyspec:scan` |
| 有 docs/ 但缺失文档 | 扫描中断 | `/sillyspec:scan`（断点续扫） |
| 有 docs/ 7 份齐全但无 changes/ | 已扫描，未开始需求 | `/sillyspec:brainstorm "想法"` |
| 有 REQUIREMENTS.md 但无 changes/ | 绿地项目，已有需求 | `/sillyspec:brainstorm "想法"` |
| changes/ 下有 proposal + design，无 plan.md | 已有规范，待计划 | `/sillyspec:plan` |
| changes/ 下有 plan.md，tasks 有未完成项 | 执行中 | `/sillyspec:execute` |
| tasks.md / plan.md 全部 checkbox 已勾选 | 待验证 | `/sillyspec:verify` |
| 已验证通过 | 待归档 | `/sillyspec:archive` |

### 4. 关键原则

- progress.json 是唯一的恢复数据源（存储在 `.sillyspec/changes/<name>/progress.json` 或旧版 `.sillyspec/.runtime/progress.json`）
- progress.json 随 `sillyspec run <stage> --done` 自动更新，不需要手动保存
