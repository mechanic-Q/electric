---
schema_version: 1
doc_type: module-card
module_id: grafana-dashboard
---
# grafana-dashboard
## 定位
Grafana 仪表板可视化 — ASSUME 仿真结果展示
## 契约摘要
- 数据源: TimescaleDB (PostgreSQL)
- 5 面板: 出清价格, 调度量, 联络线, 利润, 消纳率
## 关键逻辑
- Provisioning 自动加载 (datasource + dashboard)
- 查询使用 $__timeFilter Grafana 宏
## 注意事项
- 需要 `docker compose up -d` 启动服务
- 需要 ASSUME 仿真先写数据到 TimescaleDB
