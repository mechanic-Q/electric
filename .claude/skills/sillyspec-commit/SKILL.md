---
name: sillyspec:commit
description: 智能提交 — 自动收集变更信息，生成 commit message
argument-hint: "[可选：自定义 commit message]"
version: "3.7.32"
---

## 交互规范
当需要用户从多个选项中做出选择时，必须使用 Claude Code 内置的 AskUserQuestion 工具，将选项以参数传入。

## 用法
- /sillyspec:commit — 智能提交：自动收集变更信息，生成 commit message
- /sillyspec:commit "自定义 message" — 使用指定 message 直接提交

## 任务
$ARGUMENTS

---

## 流程

### 1. 检查是否有未提交的修改
git diff --quiet 2>/dev/null; UNSTAGED=$?
git diff --cached --quiet 2>/dev/null; STAGED=$?

两者都为 0（无修改）→ 提示"没有需要提交的修改"，结束。

### 2. 暂存所有修改
git add -A

### 3. 收集变更语义信息
# 上次 commit 时间
LAST_COMMIT_TIME=$(git log -1 --format=%ci 2>/dev/null)

# 修改的文件列表
git diff --cached --stat

从以下来源收集语义信息（筛选时间戳 > LAST_COMMIT_TIME 的条目）：

来源 A — QUICKLOG（quick 产生的修改）：
USER=$(git config user.name 2>/dev/null || echo "default")
cat .sillyspec/quicklog/QUICKLOG-${USER}.md 2>/dev/null
# 同时扫描活跃变更目录下的归属 quicklog
for dir in .sillyspec/changes/*/quicklog/*.md; do [ -f "$dir" ] && cat "$dir"; done 2>/dev/null

来源 B — tasks.md（execute 产生的修改）：
LATEST=$(ls -d .sillyspec/changes/*/ 2>/dev/null | grep -v archive | tail -1)
cat "$LATEST/tasks.md" 2>/dev/null
筛选时间戳 > LAST_COMMIT_TIME 的已勾选 task。

来源 C — 阶段产出（scan/brainstorm/plan/archive 等）：
检查 .sillyspec/ 下新增或修改的文件，根据路径识别来源阶段：
- .sillyspec/docs/<project>/scan/*.md → scan 产出
- changes/<name>/design.md → brainstorm 产出
- changes/<name>/proposal.md → brainstorm 产出
- changes/<name>/tasks.md → plan 产出
- changes/<name>/plan.md → plan 产出
- changes/archive/ → archive 产出
- knowledge/*.md → 知识库更新

### 4. 自动生成 commit message

按 conventional commits 格式，根据来源生成 message：

| 来源 | type | 示例 |
|---|---|---|
| 只有 quick 条目 | fix/refactor | fix: 手机号校验修复（含正则修正） |
| 只有 execute 条目 | feat | feat(user): 用户模块 task 1~3 |
| 只有阶段产出 | docs | docs: sillyspec scan 完成 |
| 混合来源 | 取最主要的 type | body 里列出所有条目 |
| 无匹配来源 | — | 展示 diff stat，让用户自己写 |

**如果 $ARGUMENTS 非空**，直接使用用户指定的 message，跳过自动生成，但仍展示 diff stat。

多条 quick 合并规则：
- 2 条以内 → 逐条列出
- 3 条以上 → 摘要 + body 详情

### 5. 展示确认

用 AskUserQuestion 展示：
📝 建议的 commit message：
 fix: 手机号校验修复（含正则修正）

📁 修改文件（N 个）：
 src/UserService.java (+15 -3)
 src/PhoneValidator.java (+28 -0)

选择：确认提交 / 编辑 message / 取消

用户选择编辑 → 让用户输入新 message → 再次确认。

### 6. 执行提交
git commit -m "{确认后的 message}"

提交成功后展示 commit hash + 文件数 + 行数统计。

## 多项目
检查修改的文件分别属于哪个子项目：
- 修改集中在一个子项目 → 在该子项目目录中 commit
- 修改跨多个子项目 → 用 AskUserQuestion 让用户选择：分开提交（每个子项目一个 commit）/ 合并提交

## 绝对规则
- ❌ 不要自动提交，必须展示 message 让用户确认
- ❌ 不要丢弃用户的修改
- ✅ $ARGUMENTS 非空时展示 diff stat 后直接提交（不需手动确认）
