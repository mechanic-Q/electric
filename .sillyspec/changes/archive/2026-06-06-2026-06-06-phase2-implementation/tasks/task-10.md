---
id: task-10
title: 配置 Grafana 仪表板面板 — 5 面板 + 数据源 + Docker Compose
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 2
depends_on: [task-09]
blocks: []
allowed_paths:
  - ellectric/docker-compose.yml
  - ellectric/assume/grafana/datasources/timescaledb.yml
  - ellectric/assume/grafana/dashboards/assume_simulation.yaml
  - ellectric/assume/grafana/dashboards/assume_simulation.json
---

# task-10: 配置 Grafana 仪表板面板

## 修改文件

| 操作 | 文件 |
|------|------|
| 修改 | `ellectric/docker-compose.yml`（取消注释 TimescaleDB + Grafana，添加 provisioning 挂载） |
| 新建 | `ellectric/assume/grafana/datasources/timescaledb.yml`（数据源配置） |
| 新建 | `ellectric/assume/grafana/dashboards/assume_simulation.yaml`（仪表板 provisioning） |
| 新建 | `ellectric/assume/grafana/dashboards/assume_simulation.json`（导出的仪表板 JSON） |

## 实现要求

1. **Docker Compose**: 取消注释 TimescaleDB + Grafana，添加 Grafana provisioning 卷挂载（datasources + dashboards），确保 `depends_on` 正确
2. **Grafana 数据源**: 通过 provisioning YAML 配置 TimescaleDB 数据源，host `timescaledb:5432`，database `assume`，user/pass `assume/assume`
3. **5 个仪表板面板**（从 ASSUME 的 TimescaleDB 表查询）:
   - 出清价格时序: 元/MWh，逐小时 line chart，查询 `market_results` 表
   - 各机组调度量: MW，堆叠面积图，查询 `dispatch_results` 表
   - 省间联络线功率: MW，line chart，查询 `tie_line_results` 表
   - 各智能体累计利润: 元，line chart，查询 `agent_profits` 表
   - 新能源消纳率: %，gauge + time series，查询 `renewable_curtailment` 表
4. **Provisioning 模式**: 通过 Grafana 的 provisioning 目录自动加载，无需手动导入
5. **导出格式**: `assume_simulation.json` 为 Grafana 原生 dashboard JSON model（`grafana-json-model` 格式）
6. **默认时间范围**: 最近 7 天，自动刷新每 60 秒

## 接口定义

### docker-compose.yml 最终结构

```yaml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: assume
      POSTGRES_USER: assume
      POSTGRES_PASSWORD: assume
    volumes:
      - timescale_data:/var/lib/postgresql/data

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - ./assume/grafana/datasources:/etc/grafana/provisioning/datasources
      - ./assume/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    depends_on:
      - timescaledb

volumes:
  timescale_data:
  grafana_data:
```

### Grafana 数据源 provisioning (`timescaledb.yml`)

```yaml
apiVersion: 1
datasources:
  - name: TimescaleDB
    type: postgres
    access: proxy
    url: timescaledb:5432
    database: assume
    user: assume
    secureJsonData:
      password: assume
    jsonData:
      sslmode: disable
      postgresVersion: 1600
      timescaledb: true
```

### Grafana 仪表板 provisioning (`assume_simulation.yaml`)

```yaml
apiVersion: 1
providers:
  - name: ASSUME Simulation
    folder: ASSUME
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

### 5 面板 SQL 查询（占位，根据 ASSUME 实际表结构调整）

| 面板 | 表名 | 查询模式 |
|------|------|----------|
| 出清价格时序 | `market_results` | `SELECT time, price FROM market_results WHERE type='clearing' ORDER BY time` |
| 各机组调度量 | `dispatch_results` | `SELECT time, unit, dispatch_mw FROM dispatch_results ORDER BY time` |
| 省间联络线功率 | `tie_line_results` | `SELECT time, tie_line_mw FROM tie_line_results ORDER BY time` |
| 各智能体累计利润 | `agent_profits` | `SELECT time, agent, cumulative_profit FROM agent_profits ORDER BY time` |
| 新能源消纳率 | `renewable_curtailment` | `SELECT time, curtailment_rate FROM renewable_curtailment ORDER BY time` |

## 边界处理

| # | 场景 | 处理方法 |
|---|------|----------|
| 1 | TimescaleDB 容器未就绪 Grafana 先启动 | Docker Compose `depends_on` 确保顺序；Grafana 启动后自动重连 TimescaleDB 数据源 |
| 2 | ASSUME 仿真未运行，TimescaleDB 中无数据 | 面板显示"No data"状态，不含 error；Grafana 会自动重试查询 |
| 3 | Docker 未安装或版本不兼容 | `docker-compose.yml` 头部注释说明最低版本要求（Docker Compose v2.20+） |
| 4 | 宿主端口 3000/5432 被占用 | `docker-compose.yml` 中暴露端口，文档提示用户检查端口冲突 |
| 5 | ASSUME 表结构与查询 SQL 不匹配 | 每个面板 SQL 使用 Grafana 宏（`$__timeFilter`），调整表名/列名时只需改 JSON 中的 query 字段 |
| 6 | provisioning 目录路径不正确 | 路径使用相对于 `docker-compose.yml` 的 `./assume/grafana/...` 格式，确保 Docker volume 挂载目标正确 |
| 7 | Grafana dashboard JSON 格式版本不兼容 | JSON 锁定 `schemaVersion` 为当前 Grafana 版本（latest 对应 v38+），标注兼容范围 |

## 非目标

- 不涉及 ASSUME 仿真本身的数据生成（task-09 负责）
- 不修改 ASSUME 源码或 TimescaleDB schema
- 不创建 Grafana 告警规则
- 不配置 Grafana 用户权限或团队
- 不覆盖 ASSUME 自带的 Grafana 配置（如果使用 ASSUME 内建 docker-compose）
- 不做面板国际化（面板标题使用中文，查询和数据标签保持英文）

## 参考

- Phase 2 `design.md § Grafana 仪表板`：5 面板定义
- Phase 2 `design.md § 架构决策记录`：Grafana 用于仿真仪表板
- Phase 2 `plan.md § 任务总表` + 全局验收标准"Grafana 显示出清价格、调度量、利润面板"
- [Grafana Provisioning 文档](https://grafana.com/docs/grafana/latest/administration/provisioning/)
- [Grafana Dashboard JSON Model](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/manage-version-format/)
- Docker Compose 当前状态：`ellectric/docker-compose.yml`（全部注释）

## TDD 步骤

```
1. [VALIDATE] docker-compose.yml 解析验证: `docker compose -f ellectric/docker-compose.yml config` 无报错
2. [MANUAL]   `docker compose up -d` 启动，验证 timescaledb + grafana 容器都 running
3. [CURL]     验证 Grafana API 可访问: `curl -u admin:admin http://localhost:3000/api/datasources`
4. [CURL]     验证数据源已自动配置: 上一步返回中包含 type=postgres, name=TimescaleDB
5. [CURL]     验证仪表板已自动加载: `curl -u admin:admin http://localhost:3000/api/search?folder=ASSUME`
6. [MANUAL]   打开浏览器 http://localhost:3000，验证 5 面板渲染（允许无数据状态）
7. [SIMULATE] 运行 task-09 ASSUME 仿真，验证面板显示真实数据
8. [CLEANUP]   `docker compose down -v` 清理
```

## 验收标准

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | `docker compose -f ellectric/docker-compose.yml config` 通过 | 命令返回无错误 |
| 2 | `docker compose up -d` 后 `timescaledb` 容器状态 healthy | `docker ps` 确认 |
| 3 | `docker compose up -d` 后 `grafana` 容器状态 running | `docker ps` 确认 |
| 4 | Grafana 数据源自动配置为 TimescaleDB | `curl -u admin:admin localhost:3000/api/datasources` 返回一个 type=postgres 的 datasource |
| 5 | 仪表板通过 provisioning 自动加载 | `curl -u admin:admin localhost:3000/api/search` 返回 1 个文件夹名为 ASSUME 的仪表板 |
| 6 | 仪表板包含 5 个面板 | JSON 中 `panels` 数组长度为 5（不含 Row 类型） |
| 7 | 面板 1 标题为"出清价格时序"，类型为 timeseries | `panel.title === "出清价格时序"`, `panel.type === "timeseries"` |
| 8 | 面板 2 标题为"各机组调度量"，类型为 timeseries，堆叠模式 | `panel.stack === true` |
| 9 | 面板 3 标题为"省间联络线功率"，类型为 timeseries | `panel.title === "省间联络线功率"` |
| 10 | 面板 4 标题为"各智能体累计利润"，类型为 timeseries | `panel.title === "各智能体累计利润"` |
| 11 | 面板 5 标题为"新能源消纳率"，类型为 gauge + timeseries | 两个 `panel` 或一个带双重 visualization 的 panel |
| 12 | `assume_simulation.json` 为有效 Grafana dashboard JSON | `json.loads()` 通过，含 `schemaVersion`、`title`、`panels` 字段 |
| 13 | `assume_simulation.yaml` 的 `path` 指向 `/etc/grafana/provisioning/dashboards` | YAML 解析验证 |
| 14 | `timescaledb.yml` 中 `timescaledb: true` | YAML `jsonData.timescaledb === true` |
| 15 | ASSUME 仿真运行后面板显示真实数据（非"No data"） | 人工打开 Grafana UI 确认 |
