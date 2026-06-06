---
id: task-09
title: 运行 ASSUME 7 天仿真 + 验证输出结果
priority: P0
estimated_hours: 3
depends_on: [task-08]
author: lmr
created_at: 2026-06-06T19:36:10+08:00
blocks: [task-10]
allowed_paths:
  - ellectric/assume/run_simulation.py
  - ellectric/assume/verify_simulation.py
  - ellectric/notebooks/08_assume_results.ipynb
---

# Task-09: 运行 ASSUME 7 天仿真 + 验证输出结果

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `ellectric/assume/run_simulation.py` | 创建 | ASSUME 仿真启动脚本（Python CLI），加载 YAML 配置并执行 7 天仿真 |
| `ellectric/assume/verify_simulation.py` | 创建 | 仿真结果验证脚本（统计 + 完整性检查） |
| `ellectric/assume/README.md` | 创建 | ASSUME 仿真模块说明（可选，若模块目录已存在则追加） |

## 实现要求

1. **仿真启动脚本**：可 `python run_simulation.py --config <yaml_path> --output <dir>` 调用
   - 加载 ASSUME framework 和 YAML 配置
   - 运行 7 天逐小时出清仿真（168 个时段）
   - 将结果写入指定输出目录（默认 `outputs/simulations/<timestamp>/`）

2. **输出数据格式**：每个仿真运行产生 4 个输出文件
   - `clearing_prices.csv` — 逐小时出清价格（168 行 × [timestamp, price_元_per_mwh]）
   - `dispatch.csv` — 各机组逐小时调度量（168 行 × [timestamp, unit, dispatch_mw]）
   - `agent_profits.csv` — 各智能体逐小时利润（168 行 × [timestamp, agent, profit_元]）
   - `simulation_metadata.json` — 仿真元数据（配置摘要、运行时间、状态）

3. **验证脚本**：可 `python verify_simulation.py --input <output_dir>` 调用
   - 检查 4 个输出文件是否存在且非空
   - 检查价格范围在 [0, 1500] 内（中国省间报价限价）
   - 检查每个时段机组调度量总和 ≈ 总需求（供需平衡约束）
   - 打印统计摘要（均值、最大值、最小值、缺失率）
   - 返回退出码 0 表示通过，1 表示失败

4. **ASSUME 集成方式**：通过 Python API 调用（而非 subprocess CLI）
   ```python
   from assume import World
   world = World(yaml_config=config_path)
   world.run(duration_days=7, granularity="1h")
   results = world.get_results()  # 返回结构化结果对象
   ```

5. **结果可视化**：在验证脚本中内嵌 plotly 图表（可选参数 `--plot`）
   - 出清价格时序图（line chart）
   - 各机型调度量堆叠面积图（stacked area）
   - 各智能体累计利润对比（bar chart）

## 接口定义

### run_simulation.py CLI

```
usage: run_simulation.py [-h] --config CONFIG [--output OUTPUT] [--seed SEED]

Run ASSUME 7-day simulation with Chinese provincial market config.

options:
  --config CONFIG   Path to YAML config file (required)
  --output OUTPUT   Output directory (default: outputs/simulations/<timestamp>)
  --seed SEED       Random seed for reproducibility (default: 42)
```

### 输出文件格式

**clearing_prices.csv**:
```
timestamp,price_da_元_per_mwh
2023-07-01 00:00:00+00:00,342.15
2023-07-01 01:00:00+00:00,298.70
...
```

**dispatch.csv**:
```
timestamp,unit,dispatch_mw,fuel_type
2023-07-01 00:00:00+00:00,coal_1,42000,coal
2023-07-01 00:00:00+00:00,wind_1,8500,wind
...
```

**agent_profits.csv**:
```
timestamp,agent,profit_元,strategy
2023-07-01 00:00:00+00:00,learning_agent,123450,PPO
2023-07-01 00:00:00+00:00,naive_agent,98760,marginal_cost
...
```

**simulation_metadata.json**:
```json
{
  "config_file": "assume_china_config.yaml",
  "scenario": "baseline",
  "duration_days": 7,
  "total_hours": 168,
  "start_time": "2023-07-01T00:00:00Z",
  "end_time": "2023-07-07T23:00:00Z",
  "seed": 42,
  "status": "completed",
  "completed_at": "2026-06-07T12:34:56Z",
  "total_profit_元": 185000000.0,
  "average_clearing_price_元_per_mwh": 312.45
}
```

### verify_simulation.py CLI

```
usage: verify_simulation.py [-h] --input INPUT [--plot]

Verify ASSUME simulation output completeness and sanity.

options:
  --input INPUT   Simulation output directory (required)
  --plot          Generate plotly visualization (default: false)
```

### verify_simulation.py 返回结构

```python
{
    "passed": bool,           # 全部检查通过
    "files_exist": bool,      # 4 输出文件都存在
    "price_range_ok": bool,   # 价格在 [0, 1500]
    "balance_ok": bool,       # 供需平衡误差 < 5%
    "stats": {
        "total_profit_元": float,
        "avg_price_元_per_mwh": float,
        "max_price_元_per_mwh": float,
        "min_price_元_per_mwh": float,
        "renewable_share_pct": float,
    },
    "errors": [str],
}
```

## 边界处理

| # | 场景 | 处理方法 |
|---|------|----------|
| 1 | YAML 配置加载失败（语法错误/字段缺失） | 捕获 `yaml.YAMLError`/`KeyError`，输出具体错误行和字段名，退出码 1 |
| 2 | ASSUME World 初始化失败（无效参数组合） | 捕获 `RuntimeError`/`ValueError`，输出 ASSUME 原始错误信息，建议检查配置字段兼容性 |
| 3 | 仿真中断（异常/内存不足） | Signal handler 捕获 SIGINT/SIGTERM，确保部分结果写入 `output/partial/` 目录，不丢失已完成时段 |
| 4 | 输出目录已存在 | 追加时间戳后缀（`output_001`、`output_002`），不覆盖已有目录 |
| 5 | 某时段出清失败（无供需平衡解） | 该时段 price 设为 NaN，dispatch 设为 0，`logger.warning` 记录失败时段，最终验证脚本统计缺失率 |
| 6 | 验证脚本发现供需偏差 > 5% | 输出具体时段和偏差值，标记 `balance_ok=False`，不自动修复（需人工检查配置） |
| 7 | 结果文件中出现 ±inf 或 NaN | 验证脚本中 `pd.isna()` + `np.isinf()` 检测，统计异常值比例，超过 1% 则验证失败 |
| 8 | 种子不固定导致结果不可复现 | `--seed` 参数传递给 ASSUME World，未指定时默认 42。验证脚本输出 sha256 checksum 供重复性比对 |
| 9 | 验证脚本读取的 CSV 为空（0 行） | 视为验证失败，`errors` 列表添加 `"clearing_prices.csv is empty"` 等信息 |
| 10 | 多场景并行仿真 | 每个场景独立输出目录，通过 `--output` 区分。不允许同时写入同一目录 |

## 非目标

- 不实现 ASSUME 自定义 agent 或 reward function
- 不修改 ASSUME 框架源码
- 不创建 TimescaleDB/Grafana 集成（task-10 负责）
- 不实现批量仿真编排（仅单次 7 天仿真）
- 不进行性能优化或并行加速
- 不自动上传结果到任何外部系统

## 参考

- `design.md:129-181` — Wave 3 详细设计 / ASSUME 中国省间现货配置
- `design.md:169` — 3 种 agent 类型（learning/PPO, naive, strategic）
- `design.md:171-181` — Grafana 面板期望（出清价格、调度量、利润）
- `plan.md:39` — task-09 行：依赖 task-08，输出仿真结果
- `plan.md:61-66` — 关键路径（仿真路径：task-07 → task-08 → task-09 → task-10）
- ASSUME README/doc — `World` 类 API、`world.run()`、`world.get_results()` 方法
- task-08 YAML 配置 — 3 个场景文件的字段结构

## TDD 步骤

```
1. [NEW] tests/assume/test_run_simulation.py
   ├── test_simulation_launch         — 空 mock config: 验证 CLI 参数解析
   ├── test_simulation_output_structure — mock ASSUME World: 验证 4 输出文件写入
   ├── test_simulation_metadata       — 验证 simulation_metadata.json 字段完整性
   └── test_simulation_signal_handling — mock KeyboardInterrupt: 验证部分结果保存

2. [NEW] tests/assume/test_verify_simulation.py
   ├── test_verify_all_pass           — 模拟完整正确输出 → 验证 passed=True
   ├── test_verify_missing_file       — 删除某 CSV → 验证 passed=False + 错误信息
   ├── test_verify_price_out_of_range — 注入越界价格 → 验证 price_range_ok=False
   ├── test_verify_balance_error      — 注入供需不平衡 → 验证 balance_ok=False
   ├── test_verify_empty_csv          — 空文件 → 验证 passed=False + empty 错误
   └── test_verify_nan_in_data        — NaN 注入 → 验证异常值检测

3. 集成测试（不 mock，真 ASSUME + 真 YAML）
   ├── test_end_to_end_baseline       — 基准配置 7 天仿真 → 验证 4 文件 + 统计合理
   ├── test_end_to_end_wind_high      — 高风电场景 → 验证 renewable_share > 基准
   └── test_end_to_end_summer_peak    — 夏季高峰 → 验证 avg_price > 基准
```

## 验收标准

### CLI 与文件结构

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | `python ellectric/assume/run_simulation.py --help` 输出帮助信息 | 子进程调用，退出码 0 |
| 2 | 无参数调用时输出错误信息并退出码 2 | 子进程调用，`--config` missing |
| 3 | 完整仿真运行后在输出目录生成 4 个文件 | `os.path.isfile` 依次验证 |
| 4 | 4 个文件格式正确、能被 pandas 解析 | `pd.read_csv` 不抛异常 |
| 5 | `simulation_metadata.json` 包含所有必需字段 | `json.load` → key 完整性检查 |

### 仿真结果合理性

| # | 检查项 | 条件 | 预期 |
|---|--------|------|------|
| 6 | 出清价格范围 | 基准配置 7 天仿真 | 全部在 [0, 1500] 内 |
| 7 | 供需平衡误差 | 每个时段 | `\|总调度 - 总需求\| / 总需求 < 0.05` |
| 8 | 总时段数 | 7 天逐小时 | 168 行 |
| 9 | 各机组出力非负 | dispatch.csv | `all(dispatch_mw >= 0)` |
| 10 | 新能源出力比例 | 高风电场景 | wind + solar 占比 > 30% |

### 验证脚本正确性

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 11 | `python verify_simulation.py --input <dir>` 完整通过 | 退出码 0，输出 passed=True |
| 12 | 价格越界时验证失败 | 注入 1600 元/MWh → passed=False, price_range_ok=False |
| 13 | 缺失文件时验证失败 | 删除 dispatch.csv → passed=False, errors 含 dispatch |
| 14 | `--plot` 参数生成图表文件 | 检查 `plots/` 目录下 3 个 .html 文件 |
| 15 | 验证结果可 JSON 序列化 | `json.dumps(result)` 不抛异常 |

### 结果可复现性

| # | 检查项 | 条件 | 预期 |
|---|--------|------|------|
| 16 | 相同 seed 两次运行出清价格相同 | `--seed 42` 运行两次 | `clearing_prices.csv` 逐行一致 |
| 17 | 不同 seed 结果不同 | `--seed 42` vs `--seed 99` | 价格序列不完全一致 |
