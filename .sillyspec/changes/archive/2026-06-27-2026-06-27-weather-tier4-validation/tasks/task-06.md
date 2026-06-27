---
author: lmr
created_at: 2026-06-28 01:11:57
id: task-06
title: 更新 feature-engineer 模块文档（覆盖：FR-01, FR-05, D-003@v1）
priority: P1
estimated_hours: 0.5
depends_on: [task-01, task-04]
blocks: [task-07]
requirement_ids: [FR-01, FR-05]
decision_ids: [D-003@v1]
allowed_paths:
  - docs/Ellectric/modules/feature-engineer.md
---

## 修改文件

`docs/Ellectric/modules/feature-engineer.md` — 在 `## 注意事项` 后追加一段 Weather Tier4 验证脚本说明，保留现有 frontmatter、契约摘要、关键逻辑、人工备注。

## 覆盖来源

- **FR-01**：验证脚本可复现运行，模块文档记录入口
- **FR-05**：模块文档记录验证产物路径
- **D-003@v1**：采用方案B（可复现脚本 + 报告产物），文档作为入口指引

## 实现要求

1. 在 `## 注意事项` 末尾（`人工备注` 之前）追加验证脚本说明。
2. 包含验证入口：`python ellectric/scripts/validate_weather_tier4.py`。
3. 包含报告产物路径：`ellectric/reports/weather_tier4/weather_tier4_validation.json` 和 `weather_tier4_validation.md`。
4. 明确报告式语义（report-only），无硬性精度提升门槛。
5. 不改前端 matter、不改契约摘要、不改关键逻辑、不改人工备注。
6. 不改任何 Python 代码 API。

## 接口定义

无新接口。仅文档补充，读者可通过`## 注意事项`新段落找到验证入口和报告路径。

## 边界处理

- 文档追加后不破坏现有章节结构、不引入重复。
- 若后续验证脚本路径变更，需同步更新此段。
- 报告产物为脚本运行后生成，不检入 git；文档仅记录路径，不引用具体内容。
- 报告式语义意味着不因 weather 精度未提升而判失败，文档需体现这一设计。
- 不要求设置硬性阈值（`hard_threshold_applied=false`），文档对应说明。
- 若未来 Weather Tier4 从可选增强变为默认特征，文档需重新评估入口指引方式。

## 非目标

- 不重写整个模块卡片。
- 不修改或不新增 Python 函数签名。
- 不补充模型效果、实验数据或报告内容。
- 不新增 notebook 或 CLI 入口指引。
- 不删除或修改现有 `人工备注` 块。

## 参考

- `design.md:97-103` — 文件变更清单
- `design.md:53-58` — 脚本与报告产物路径
- `design.md:221-225` — hard_threshold_applied 语义
- `plan.md:28` — task-06 定义
- `plan.md:42` — AC-09 验收标准

## TDD 步骤

| 步骤 | 操作 | 预期 |
|------|------|------|
| 1 | 读取当前 `feature-engineer.md` | 确认 frontmatter、契约、注意事项、人工备注内容 |
| 2 | 追加 Weather Tier4 验证段落 | 段落出现在 `## 注意事项` 末尾、`## 人工备注` 之前 |
| 3 | 确认段落包含验证脚本入口 | `python ellectric/scripts/validate_weather_tier4.py` 存在 |
| 4 | 确认段落包含报告产物路径 | JSON 和 Markdown 路径均提及 |
| 5 | 确认报告式语义 | 段落中出现 "report-only" 或 "无硬性门槛" 等效表述 |
| 6 | 确认不变区域 | frontmatter、契约摘要、关键逻辑、人工备注无修改 |
| 7 | 重新读取完整文件 | 结构完整，无重复，无引入错误 |

## 验收标准

| ID | 标准 | 验证方式 |
|----|------|----------|
| AC-09-01 | `feature-engineer.md` 包含验证脚本入口 | grep `validate_weather_tier4.py` |
| AC-09-02 | 文档包含 JSON 和 Markdown 报告产物路径 | grep `weather_tier4_validation.json` 和 `weather_tier4_validation.md` |
| AC-09-03 | 文档体现 report-only / 无硬性门槛语义 | grep -i `report.only\|hard_threshold\|无硬性` |
| AC-09-04 | frontmatter 未被修改 | diff 仅新增段落，其他行不变 |
| AC-09-05 | 人工备注块未被修改 | `MANUAL_NOTES_START` / `MANUAL_NOTES_END` 内容不变 |
| AC-09-06 | 无 Python 代码变更 | 确认 `ellectric/` 和 `tests/` 下文件未被修改 |
