---
name: sillyspec:auto
description: 自动模式 — 全流程自动推进（通用版）
argument-hint: "<需求描述>"
---

## 用法
- /sillyspec:auto 实现用户登录功能
- /sillyspec:auto 修复搜索结果的排序问题

## 任务
$ARGUMENTS

---

## 执行流程

你是全流程编排器，按 brainstorm → plan → execute → verify 顺序自动推进。

### 启动
1. 运行 `sillyspec run auto --input "<用户需求>"`
2. 读取 CLI 输出的 step prompt（包含你的角色描述）
3. 执行 prompt 中的操作
4. **记录 CLI 输出中显示的 Change 名称**（如 `Change: 2026-06-02-xxx`）

### 步骤循环
重复以下循环直到 CLI 输出"全部流程已完成"：

1. **读取 CLI 输出的 step prompt**
2. **判断是否需要用户确认：**
   - prompt 中包含"请用户选择""等待用户回答""展示给用户""用户确认" → **暂停，等用户回复**
   - 纯内部操作 → **直接执行**
3. **执行 prompt 要求的操作**
4. **完成后运行** `sillyspec run auto --done --output "<你的摘要>"`
   - ⚠️ **必须携带 --change <变更名>**，变更名来自启动时 CLI 输出的 `Change:` 字段
   - 示例：`sillyspec run auto --done --change 2026-06-02-spec-bootstrap-agent-stream-interaction --output "摘要"`
   - **绝不使用 `--change default`**，除非 CLI 启动时明确显示的 Change 名称就是 `default`
5. **读取 CLI 输出的下一步 prompt**，回到步骤 1

### 阶段审核门控

**brainstorm 完成后：**
评估需求复杂度（基于 design.md 中的模块拆分、批量操作、多角色交互等特征），根据复杂度决定：

| 复杂度 | 审核策略 |
|--------|---------|
| 简单（无拆分、无批量） | 不审核，直接进入 plan |
| 中等（有拆分或批量） | 启动 1 个审核子代理（QA 视角）审查 design.md |
| 复杂（拆分 + 批量/多角色） | 启动 2-3 个审核子代理多角度审查 |

多角度审核子代理分工：
- **架构师** — 审查设计合理性、技术选型 trade-off、模块划分
- **安全专家** — 审查安全隐患、权限设计、数据校验
- **QA 专家** — 审查需求覆盖率、边界场景遗漏、验收标准

审核流程：
1. 暂停，提示用户当前复杂度等级和建议审核策略
2. 用户确认后，启动审核子代理（读取 design.md + requirements.md + tasks.md）
3. 子代理输出问题清单
4. 汇总问题，询问用户"是否需要修改后再继续"
5. 需要修改 → 修复后重新审核；不需要 → 进入下一阶段

**plan 完成后：**
同样评估复杂度，启动审核子代理审查 plan.md：
- **项目经理** — 审查任务拆解粒度、依赖关系、优先级
- **工程师** — 审查任务可行性、工作量评估是否合理
- **QA** — 审查验收标准是否具体可测试

### 关键规则
- 不要跳过任何步骤
- 不要手动修改 progress.json
- 不要自动 commit，只 git add
- 不要使用 npx
- 不要编造不存在的 CLI 子命令
- 遇到命令报错 → 展示错误，暂停等用户介入
- **每次调用 `sillyspec run auto --done` 都必须携带 `--change <变更名>`**，变更名 = CLI 首次输出中显示的 Change 名称。如果 CLI 首次运行没有显示 Change 名称，从 progress 或用户输入中确认变更名后再调用

### 异常处理
- 命令执行失败 → 展示错误信息，暂停等待用户指示
- 用户说"停止"或"暂停" → 立即停止，报告当前进度

### 完成条件
CLI 输出"全部流程已完成"后，输出完整流程总结，提示用户提交改动。
