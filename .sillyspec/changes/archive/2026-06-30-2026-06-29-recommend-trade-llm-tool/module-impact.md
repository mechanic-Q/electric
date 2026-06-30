---
author: lmr
created_at: 2026-06-30 23:50:00
---

# 模块影响分析

## 模块影响矩阵

| 模块 | 影响类型 | 相关文件 | 更新内容摘要 | needs_review |
|------|----------|----------|-------------|-------------|
| service.schemas | 数据结构变更 | `ellectric/service/schemas.py` | 新增 `TradeAction`, `RecommendRequest`, `RecommendResponse` 3 个 Pydantic v2 schema | false |
| service.handlers | 逻辑变更 | `ellectric/service/handlers.py` | 新增 `run_recommend_trade()` handler + `_determine_confidence`, `_generate_actions`, `_build_summary` 3 个 helper | false |
| api.server | 接口变更 | `ellectric/api/server.py` | 新增 `POST /recommend` 端点, 新增 schema/handler 导入 | false |
| cli.main | 接口变更 | `ellectric/cli/main.py` | 新增 `recommend` Typer 子命令, 新增 schema/handler 导入 | false |
| llm.tools | 接口变更 | `ellectric/llm/tools.py` | 新增 `recommend_trade` LangChain @tool | false |
| llm.agent | 逻辑变更 | `ellectric/llm/agent.py` | 注册 `recommend_trade` 到 tools 列表, 更新系统 prompt | false |

## 未匹配文件

| 文件 | 原因 |
|------|------|
| `.sillyspec/changes/.../plan.md` | 变更自身规范文件 |
| `ellectric/reports/weather_tier4/weather_tier4_validation.json` | 非本变更文件（预存 diff） |
| `ellectric/reports/weather_tier4/weather_tier4_validation.md` | 非本变更文件（预存 diff） |

## 注释

- 本变更未修改模块映射文件（`_module-map.yaml` 不存在）
- 建议后续运行 scan 生成模块映射
- 所有变更是纯新增，无现有模块逻辑修改
