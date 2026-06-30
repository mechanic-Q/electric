---
schema_version: 1
doc_type: module-card
module_id: service-api
author: lmr
created_at: 2026-06-30 22:16:05
---

# service-api

## 定位

服务层和 CLI 接口模块，负责把 Pydantic 请求/响应 schema 映射到数据加载、预测、回测、解释等 pipeline 能力。FastAPI、CLI、LLM tools 共用同一批 service handlers。

## 契约摘要

- `ForecastRequest(model_type, horizon=24, data_source='shandong')`
- `ForecastResponse(timestamps, predictions, metrics)`
- `run_forecast(req: ForecastRequest) -> ForecastResponse`
- `python -m ellectric.cli.main forecast <model> <horizon>`
- 支持 `model_type`: `load`, `price`, `wind`, `solar`, `price_dnn`

## 关键逻辑

- `price` 默认分派到 LEAR 电价预测器
- `price_dnn` 是显式 opt-in，分派到 PyTorch DNN 电价预测器
- `load` / `wind` / `solar` 保持既有模型路径
- CLI help 文案解释 `price_dnn=PyTorch DNN 电价预测`
- Schema 层只声明可选模型类型，不改变真实交易或下单行为

## 注意事项

- `price_dnn` 需要已训练/可加载 DNN 模型，否则 handler 会返回明确错误
- 默认 price forecast 仍为 LEAR，避免破坏现有 API/CLI 行为
- 当前模块卡由 archive 同步补充，`_module-map.yaml` 标记 needs_review=true，建议后续 scan 完整重建 service/CLI 模块索引

## 人工备注

<!-- MANUAL_NOTES_START -->

<!-- MANUAL_NOTES_END -->
