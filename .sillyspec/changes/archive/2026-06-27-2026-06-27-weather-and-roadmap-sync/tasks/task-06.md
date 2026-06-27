---
author: lmr
created_at: 2026-06-27 19:12:11
id: task-06
title: 更新 README、ROADMAP、REQUIREMENTS 状态
priority: P1
depends_on:
  - task-03
blocks:
  - task-07
  - task-10
requirement_ids:
  - FR-005
decision_ids:
  - D-001@v1
  - D-002@v1
  - D-003@v1
  - D-004@v1
  - D-005@v1
allowed_paths:
  - "ellectric/README.md"
  - ".planning/ROADMAP.md"
  - ".planning/REQUIREMENTS.md"
---

# 更新 README、ROADMAP、REQUIREMENTS 状态

## 修改文件

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `ellectric/README.md` | 更新 Phase 4 持续改进 todo，标记 weather features 已接入/待验证，记录四个 out-of-scope |
| 修改 | `.planning/ROADMAP.md` | 对齐 Phase 4 状态（Not started→In progress），增加 Weather Tier4 完成项，更新 Progress 表格 |
| 修改 | `.planning/REQUIREMENTS.md` | 更新可追溯性表格中 Phase 1 已结项状态，阶段状态列从"待开始"→"已完成"，标注集成需求对应状态 |

## 覆盖来源

- `design.md`: FR-005（仓库文档对齐 Phase 4 状态）
- `plan.md`: task-06 定义，Wave 2，W2/P1，依赖 task-03
- `requirements.md`: FR-005 的 Given/When/Then 描述，D-001@v1~D-005@v1 覆盖矩阵
- `decisions.md`: D-001@v1（不做准实时）、D-002@v1（不做中长期合约）、D-003@v1（单省山东）、D-004@v1（不做真实交易/付费数据源）、D-005@v1（本轮范围选项 B）

## 实现要求

### 1. `ellectric/README.md` 变更

**Phase 4 持续改进段（当前第 129-132 行）：**

- `WeatherFetcher 气象特征集成到 features` 从 `[ ]` 改为 `[x]`，行末标注 `（已接入，验证待完成）`
- 在持续改进列表下方增加一段 out-of-scope 说明，引用四个决策：

  ```
  **本轮显式排除：**
  - 准实时 T+15min 调度 — 不引入 cron/daemon/queue
  - 中长期合约串 pipeline — 增强项，当前不做
  - 多省/多节点市场覆盖 — MVP 保持单省山东
  - 真实交易/付费数据源 — 学习原型不涉及真实资金
  ```

- 保持现有四阶段结构（Phase 1-3 + Phase 4 持续改进）不变，不重新编号。

### 2. `.planning/ROADMAP.md` 变更

**Phase 4 标题行（第 12 行）：**

- 阶段状态从 `[ ]` 改为 `[~]`（进行中），行末追加说明 `（主线基本完成，持续改进阶段）`

**Phase 4 详情段参数（第 79-93 行）：**

- `Plans:` 项从空改为 `1 plan`
- 在 Success Criteria 下方新增子段：

  ```
  **已完成：**
  - FastAPI 三层接口 (REST API + SSE Web Chat)
  - CLI 命令行框架
  - SHAP 模型可解释性
  - WeatherFetcher Tier4 特征集成（待最终验证）
  
  **持续改进项（优先级排序）：**
  1. Weather 特征验证与精度评估
  2. 完整 96 维 RL training on full dataset
  3. 中长期合约/新能源预测特征探索
  
  **显式排除：**
  - 准实时 T+15min 调度
  - 中长期合约串 pipeline
  - 多省/多节点市场覆盖
  - 真实交易/付费数据源
  ```

**Progress 表格（第 96-103 行）：**

- Phase 4 状态栏：`Not started` → `In progress`，`Completed` 列保持 `-` 不变

### 3. `.planning/REQUIREMENTS.md` 变更

**可追溯性表格（第 88-114 行）：**

- Phase 1 对应需求（ENV-01~ENV-04, DATA-01~DATA-04, PRED-01, VIZ-01）状态从"待开始"→"已完成"
- Phase 2/3/4 需求保持"待开始"（分别由对应 Phase 覆盖）
- 表格末尾添加标注：

  ```
  *注：REQUIREMENTS.md 仅记录各 Phase 原始需求启动状态。实际阶段状态以 ROADMAP.md 和 README.md 中 Phase 4 进展描述为准。*
  ```

**不在范围内表格（第 69-82 行）：**

- 追加两行（保持现有表格风格）：

  ```
  | 准实时 T+15min 数据调度 | 不引入 cron/daemon/queue 依赖 |
  | 中长期合约串 pipeline | 增强项，当前 Phase 不做 |
  ```

**页脚（第 122 行）：**

- `最后更新:` 日期从 `2026-05-20 初始定义后` 改为 `2026-06-27（Phase 4 持续改进口径对齐）`

## 接口定义

N/A。本文档任务不涉及代码接口变更。三份文档使用既有 Markdown 格式，无新增 API/CLI/函数签名。

## 边界处理

1. **READEME Phase 4 与 ROADMAP Phase 4 编号/描述冲突** — README 使用"持续改进"命名，ROADMAP 使用原始"Integration + LLM Interface"描述。统一口径：ROADMAP 保留原始四阶段编号（1-4），在 Phase 4 内说明"主线基本完成，进入持续改进"；READEME 保持自己的"持续改进"命名但不再独立编号。不改变 ROADMAP 的阶段编号体系。

2. **REQUIREMENTS 原状态全为"待开始"** — 仅将 Phase 1（已由 ROADMAP 标注为 Shipped）对应需求更新为"已完成"。Phase 2/3/4 需求保持"待开始"，不做推测性更新。新增脚注说明 REQUIREMENTS 仅记录原始需求启动状态。

3. **ROADMAP 显示 Phase 2/3 状态为"Shipped"但 Plans 为 0/TBD** — 保持现有结构，不修改 Phase 2/3 的 Plans 数或状态。Phase 2/3 的 Plans 空缺属于历史记录，本轮不做编造填充。

4. **READEME 的 Phase 3 包含 FastAPI/CLI/LLM/WebChat/SHAP 但实际上已完成** — 保持 README Phases 1-3 的 `[x]` 现状不变。在 ROADMAP Phase 4 的"已完成"列表中新增记录这些已实现项，确保两处文档均反映真实代码状态，但不删除任何已有标记。

5. **Weather 特征标记为"已接入/待验证"而非"已完成"** — 因为 task-09（验证测试与旧 API 兼容检查）尚未执行。三份文档统一使用"已接入，验证待完成"口径，不提前断言可交付。

6. **ROADMAP 的 Notes 段与 README 的 notebook 学习顺序编号冲突（Phase 2/3 编号）** — 不修改 Notes 段内容。Notes 是历史记录，本变更只对齐 Phase 4 状态。

## 非目标

- 不修改代码文件或测试文件（`*.py`, `test_*.py`）
- 不修改 scan 架构文档（属于 task-05）
- 不修改模块文档或 module-map（属于 task-04）
- 不修改 LLM Wiki 文件（属于 task-07/task-08）
- 不重新组织结构或重写阶段描述
- 不新增 Markdown 文件
- 不删除既有内容或历史判断——只做增量状态标记和追加说明
- 不改变 notebook 学习顺序、路径编号或命名规则

## 参考

| 来源 | 内容 | 用途 |
|------|------|------|
| `design.md:FR-005` | 仓库文档对齐 Phase 4 状态 | 实现要求 1-3 |
| `design.md:82-98` | 文件变更清单中三份文档操作 | 确认修改范围 |
| `design.md:172-177` | D-001@v1~D-005@v1 决策描述 | out-of-scope 文案依据 |
| `plan.md:19` | task-06 在 plan 中的定义 | 确认覆盖 FR/D 与依赖关系 |
| `plan.md:40` | 任务依赖与优先级 | task-03→task-06→task-07/task-10 |
| `requirements.md:70-76` | FR-005 的验收条件 | 三段文档变更的验收依据 |
| `ellectric/README.md:110-132` | 当前 Phase 4 持续改进段 | 待修改的准确行号范围 |
| `.planning/ROADMAP.md:1-106` | 当前路线图全文 | 待修改的准确内容 |
| `.planning/REQUIREMENTS.md:1-123` | 当前需求文档全文 | 待修改的准确内容 |

## TDD 步骤

本文档任务无法运行传统自动化测试。验证方式为人工对照检查和 grep 命令。

1. **变更前基线：** 对三份文件运行 `git diff` 记录当前未提交变更，确认 task-06 之外的文件无预期外修改。
2. **修改 README.md：** 更新 Phase 4 段落、out-of-scope 区块。
3. **逐行验证 README：** 确认原有 Phase 1-3 标记不被误改，`[ ]` / `[x]` / `[~]` 状态标记正确。
4. **修改 ROADMAP.md：** 更新 Phase 4 状态、Progress 表格。
5. **逐行验证 ROADMAP：** 确认 Phase 1-3 状态与 Plans 数不变，Notes 段不变。
6. **修改 REQUIREMENTS.md：** 更新可追溯性表格、不在范围内表格、页脚日期。
7. **逐行验证 REQUIREMENTS：** 确认 Phase 2/3/4 需求状态不变，仅 Phase 1 更新。
8. **交叉检查统一口径：** 用 `rg` 确认四个 out-of-scope 项在三份文档中描述一致。
9. **最终 Diff 检查：** `git diff --stat` 确认只修改了三份文件，无代码文件修改。

## 验收标准

| # | 标准 | 验证方式 | 对应 FR/D |
|---|------|----------|-----------|
| AC-1 | README Phase 4 Weather 行标记 `[x]` 并注明"已接入，验证待完成" | 肉眼确认 | FR-005 |
| AC-2 | README 包含四个 out-of-scope 决策说明（准实时/中长期合约/多省/真实交易） | grep 确认四个短语存在于 README | D-001@v1, D-002@v1, D-003@v1, D-004@v1 |
| AC-3 | ROADMAP Phase 4 状态为 `[~]`（进行中）或等同标记，非 `[ ]` 非 `[x]` | 肉眼确认 | FR-005 |
| AC-4 | ROADMAP Progress 表格 Phase 4 状态改为 `In progress` | 肉眼确认 | FR-005 |
| AC-5 | REQUIREMENTS 可追溯性表格中 Phase 1 需求状态已改为"已完成" | 逐行确认 | FR-005 |
| AC-6 | REQUIREMENTS 不在范围内表格新增准实时和中长期合约两行 | 肉眼确认 | D-001@v1, D-002@v1 |
| AC-7 | REQUIREMENTS 页脚更新日期为 2026-06-27 | 肉眼确认 | FR-005 |
| AC-8 | 三份文档 out-of-scope 描述语义一致，无矛盾 | 交叉 grep 对比 | D-001@v1~D-004@v1 |
| AC-9 | 仅修改三份文件，无代码文件、测试文件、其他文档被误改 | `git diff --stat` 确认 | FR-005 |
| AC-10 | README Phase 1-3 的 `[x]` 标记保持不变 | `grep '\[x\]' README.md` 确认 | FR-005 |
| AC-11 | ROADMAP Phase 2/3 的 Plans 数与 Status 不变 | 肉眼确认 | FR-005 |
| AC-12 | REQUIREMENTS Phase 2/3/4 需求保持"待开始"，仅有 Phase 1 变更 | 逐行确认 | FR-005 |
