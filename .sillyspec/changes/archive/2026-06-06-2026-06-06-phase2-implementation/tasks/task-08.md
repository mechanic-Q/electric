---
id: task-08
title: 创建中国省间市场 YAML 配置（3 个场景文件）
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 3
depends_on: [task-07]
blocks: [task-09]
allowed_paths:
  - ellectric/assume/configs/assume_china_config.yaml
  - ellectric/assume/configs/assume_china_wind_high.yaml
  - ellectric/assume/configs/assume_china_summer_peak.yaml
---

# Task-08: 创建中国省间市场 YAML 配置（3 个场景文件）

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `ellectric/assume/configs/assume_china_config.yaml` | 创建 | 基准中国省间现货配置 |
| `ellectric/assume/configs/assume_china_wind_high.yaml` | 创建 | 高风电场景（30GW 风 + 40GW 煤） |
| `ellectric/assume/configs/assume_china_summer_peak.yaml` | 创建 | 夏季高峰场景（96GW 需求 + 15GW 气） |

## 实现要求

1. **基准文件**（`assume_china_config.yaml`）需包含 AS 格式下的 5 大区块
   - `market`: 类型 zonal，出清 pay_as_clear，报价限价 [0, 1500]，偏差考核系数 0.1
   - `generation_mix`: 5 种机组（coal 50GW/300 元/MWh, wind 20GW/50, solar 15GW/30, gas 10GW/600, storage 5GW/100）
   - `demand`: china_summer_peak 轮廓，总需求 80GW
   - `agents`: 3 种类型（learning/PPO, naive, strategic）
   - `simulation`: 7 天、逐小时出清

2. **高风电文件**（`assume_china_wind_high.yaml`）在基准基础上覆盖：
   - wind.capacity_mw: 20000 → 30000
   - coal.capacity_mw: 50000 → 40000
   - 其余字段完全一致（用 YAML anchor/reference 或完整复制）

3. **夏季高峰文件**（`assume_china_summer_peak.yaml`）在基准基础上覆盖：
   - demand.total_demand_mw: 80000 → 96000（+20%）
   - gas.capacity_mw: 10000 → 15000
   - 其余字段完全一致

4. YAML 语法正确，能被 ASSUME `yaml.safe_load` 解析

5. 每个文件顶部包含中文注释说明场景用途

## 接口定义

```yaml
# 顶层结构（ASSUME 加载约定）
market:
  type: str              # "zonal" — 省间分区定价
  clearing_mechanism: str # "pay_as_clear" — 按统一出清价结算
  price_limits:
    min: float           # 报价下限（元/MWh）
    max: float           # 报价上限（元/MWh）
  deviation_penalty: float # 偏差考核系数

generation_mix:
  <fuel>:
    capacity_mw: int     # 装机容量（MW）
    marginal_cost: float # 边际成本（元/MWh）

demand:
  profile: str           # 需求曲线轮廓名称
  total_demand_mw: int   # 总需求（MW）

agents:
  - type: str            # "learning" / "naive" / "strategic"
    algorithm: str?      # learning agent 策略名（如 "PPO"）

simulation:
  duration_days: int     # 仿真天数
  granularity: str       # "1h" 逐小时出清
```

## 边界处理

1. **YAML 语法错误**: 每个文件写入后用 `yaml.safe_load()` 验证解析，不允许裸字符串、错误缩进
2. **字段完整性检查**: 基准文件必须包含全部 5 个顶层 key（market/generation_mix/demand/agents/simulation），缺一不可
3. **数值范围约束**: price_limits min >= 0, max <= 2000（中国省间规则上限）；capacity_mw 总和不应小于 demand
4. **场景文件泄漏**: wind_high 和 summer_peak 必须明确定义所有 key（或用 YAML anchor `<<:`），避免因解析顺序问题导致字段丢失
5. **agent 类型校验**: type 字段限 "learning"、"naive"、"strategic" 三者，algorithm 字段只在 type=learning 时出现
6. **重复 agent 注册**: 同一 YAML 中不允许出现 type 完全相同的两个 agent（防止 ASSUME runtime 冲突）
7. **profile 名称约定**: demand.profile 字符串必须匹配 ASSUME 预置 profile 列表，否则回退报错

## 非目标

- 不创建 ASSUME 仿真运行脚本（task-09 负责）
- 不修改 ASSUME 源码或默认配置加载逻辑
- 不生成 Grafana 仪表板面板（task-10 负责）
- 不涉及实际电力数据接入
- 不验证仿真启动/运行过程（仅验证 YAML 文件本身正确性）

## 参考

- `design.md:134-169` — ASSUME YAML 配置示例（基准配置三段式结构）
- `design.md:183-193` — 架构决策（省间现货规则选型原因）
- `plan.md:38-40` — task-08 行：文件路径、依赖（task-07 → task-08）
- ASSUME 文档 `config_template.yaml` — 官方配置模板（验证字段名约定）

## TDD 步骤

1. **Red**: 先写 3 个空 YAML 文件，写 pytest 验证文件存在且 `yaml.safe_load` 不抛异常
2. **Green**: 按设计文档实现 3 个配置文件的完整内容
3. **Refactor**: 提取重复字段到 YAML anchor（`assume_china_config.yaml` 作为锚定基准），wind_high 和 summer_peak 用 `<<:` 继承 + 覆盖

## 验收标准

### YAML 解析与字段完整性

| # | 验证项 | 条件 | 预期 |
|---|--------|------|------|
| 1 | `yaml.safe_load()` | 对 3 个文件分别调用 | 不抛异常，返回 dict |
| 2 | 基准文件 5 个顶层 key | `set(config.keys())` | `{"market", "generation_mix", "demand", "agents", "simulation"}` |
| 3 | market.price_limits | `config["market"]["price_limits"]` | `{"min": 0, "max": 1500}` |
| 4 | generation_mix 有机组数 | `len(config["generation_mix"])` | `5` |

### 场景值覆盖正确性

| # | 验证项 | 文件 | 预期值 |
|---|--------|------|--------|
| 5 | wind.capacity_mw | wind_high.yaml | `30000` |
| 6 | coal.capacity_mw | wind_high.yaml | `40000` |
| 7 | demand.total_demand_mw | summer_peak.yaml | `96000` |
| 8 | gas.capacity_mw | summer_peak.yaml | `15000` |
| 9 | wind.capacity_mw | summer_peak.yaml | 应等于基准值 `20000`（继承） |
| 10 | coal.capacity_mw | wind_high + summer_peak | 应分别等于 `40000` 和 `50000` |

### 场景间一致性

| # | 验证项 | 条件 | 预期 |
|---|--------|------|------|
| 11 | wind_high 与基准差异 | diff key set | 仅 capacity_mw 值不同，schema 完全一致 |
| 12 | summer_peak 与基准差异 | diff key set | 仅 demand + gas 值不同，schema 完全一致 |
| 13 | 报价限价跨场景一致 | 3 文件 price_limits | 全部 `{min: 0, max: 1500}` |
| 14 | agent 配置跨场景一致 | 3 文件 agents | agent 列表完全相同 |
