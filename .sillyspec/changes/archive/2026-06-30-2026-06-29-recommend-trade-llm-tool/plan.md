---
plan_level: full
author: lmr
created_at: 2026-06-30 04:10:00
---

# 实现计划：LLM 交易建议工具

## 来源

来自 `design.md`：新增 `/recommend` 能力，service 产出结构化交易动作，LLM 只负责中文解释；动作 schema 为 buy/sell/hold + price_limit + quantity_mwh + reason + confidence。

## Spike 前置验证

| Spike | 验证内容 | 不通过后果 |
|---|---|---|
| spike-01 | 确认现有 service handlers 可被 recommend handler 组合调用 | 若耦合过强，先实现 mock evidence 聚合版本 |
| spike-02 | 确认 LangChain agent 工具注册方式稳定 | 若不稳定，先交付 API/CLI，LLM tool 后置 |

## Wave 1（schema/service）

- [x] task-01: 新增 recommend request/response schema（覆盖：FR-01, FR-02, FR-03, D-001@v1, D-002@v1）
- [x] task-02: 实现 `run_recommend_trade()` service handler（覆盖：FR-04, FR-06, FR-07, D-003@v1, D-004@v1）
- [x] task-03: 新增 recommend handler 单元测试（覆盖：FR-01~FR-08）

## Wave 2（interfaces）

- [x] task-04: 新增 `/recommend` FastAPI endpoint（覆盖：FR-05）
- [x] task-05: 新增 CLI `recommend` 子命令（覆盖：FR-05）
- [x] task-06: 新增 LangChain `recommend_trade` tool 并注册到 agent（覆盖：FR-05, D-003@v1）

## Wave 3（evidence/docs）

- [x] task-07: 生成 sample output 与模块文档（覆盖：FR-07）

## 验收

- `rtk pytest tests/test_recommend_handler.py` 通过。
- `POST /recommend` 返回固定 schema。
- `python -m ellectric.cli.main recommend 2026-01-15 --horizon 24` 可运行。
- LangChain `recommend_trade` tool 可调用 `/recommend`。
- low confidence 输出保守建议与 disclaimer。
- 旧 forecast/backtest/explain 行为不变。

## 覆盖矩阵

| ID | 覆盖任务 | 验收证据 |
|---|---|---|
| D-001@v1 | task-01, task-02 | response schema + tests |
| D-002@v1 | task-01 | TradeAction schema tests |
| D-003@v1 | task-02, task-06 | service evidence + LLM tool tests |
| D-004@v1 | task-02, task-03 | low confidence guard tests |

## Wave 可行性校验

- Wave 1 建立 schema/service 核心，避免接口层先依赖空实现。
- Wave 2 并行接 API/CLI/LLM 三通道。
- Wave 3 生成样例输出和文档。
- 无循环依赖。

## 自检

✓ 输出明确标注 plan_level: full
✓ 有 spike、wave、验收、覆盖矩阵
✓ 所有 D-xxx@vN 在计划中可追踪
✓ task 使用 checkbox 格式
✓ 未引入真实交易下单或实时调度
