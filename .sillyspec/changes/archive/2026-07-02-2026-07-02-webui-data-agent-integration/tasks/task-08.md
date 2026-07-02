---
id: task-08
title: 更新 Agent prompt 和工具注册
author: lmr
created_at: 2026-07-02 17:02:04
priority: P0
depends_on:
  - task-07
blocks:
  - task-13
requirement_ids:
  - FR-04
decision_ids:
  - D-002@v1
  - D-004@v1
  - D-005@v1
allowed_paths:
  - ellectric/llm/agent.py
---

## goal

在 `ellectric/llm/agent.py` 中导入 task-07 新增的四个 catalog/report tools，注册到 `create_agent_executor` 的工具列表，并更新系统 prompt 以覆盖全部项目能力和数据来源标注规则。

## implementation

1. 新增 imports：`query_capabilities`, `query_datasets`, `query_reports`, `read_report` — 来自 `ellectric.llm.tools`
2. 更新 `create_agent_executor` 中 `tools=[]` 列表，追加上述四个新工具
3. 扩展 `_SYSTEM_PROMPT`：
   - 能力描述增加电价预测、风光预测、Weather Tier4、RL 全量评估、离线报告查询、数据目录查询
   - 约束："不编造数字"，"回答需标注来源（实时 API 或离线报告）"；
     如果工具调用返回 `fallback_reason`，必须转述"根据XX离线报告"而非"实时预测显示"
4. 移除 `recommend_trade` 导入（如需减少未用工具），但保留导入和注册更稳妥

## acceptance

- Agent executor 创建不报 import 错误
- 新工具可被 LangChain agent invoke（通过单元测试或 smoke）
- 系统 prompt 中能力描述覆盖负荷/电价/风光/Weather/RL/回测/SHAP/交易建议/报告目录/数据集目录
- 系统 prompt 包含"不编造数字"和"标注来源"两条明确原则

## verify

```bash
python -m pytest tests/test_api_catalog.py -q
```

## constraints

- 仅修改 `ellectric/llm/agent.py`
- 不改变 LangChain `create_agent` 或 `ChatOpenAI` 的调用方式
- 不引入新依赖
- 系统 prompt 约束要求：不编造数字；所有数字需标注来源（实时 API 预测 / 离线报告 / 历史数据统计）；
  LLM 输出不能模糊化"根据实时数据"这种不透明的措辞，必须明确告知用户信息来源
