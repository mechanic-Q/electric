---
author: lmr
created_at: 2026-06-25T00:30:00+08:00
---

# Proposal — 山东 Shandong 15min MVP 数据切换

## 动机

前置调研 `2026-06-24-tuji-data-granularity` 已验证：
1. 山西公开数据 = 50 月月度典型日参考曲线（非逐日真实历史），等效 50 天独立样本，不能做逐日回测
2. 海数据平台有逐日 15min 真实历史但需付费

用户提供了 **山东 15min 完整数据**：`山东_2024-2026_15min.csv`，745 天 × 96 点 = 71520 行，21 字段，真实日前/实时出清价 + 新能源实际出力 + 负荷。这份数据让项目从"管道能通、结果不可信"变成"可验证原型"。

**决策：Electric 项目彻底切换到山东为 MVP**。

## 变更范围

### 新增
- `ellectric/pipeline/shandong_loader.py` — ShandongDataLoader 类（继承 DataLoader ABC）
- `ellectric/fetch/weather.py` — WeatherFetcher，Open-Meteo 气象数据抓取
- `ellectric/data/shandong/` — 数据目录
- `ellectric/data/shandong/README.md` — 数据资产说明

### 修改
- `ellectric/pipeline/data_loader.py` — create_loader() 加 `shandong` source key
- `ellectric/config.py` — TimeConfig 默认值改为 points_per_day=96, points_per_week=672, freq="15min"
- `ellectric/pipeline/features.py` — 适配扩展 schema（可选用新能源/日历列）
- `ellectric/pipeline/price_forecaster.py` — 适配价格列重命名
- `ellectric/pipeline/trading_env.py` — 适配 15min，观测空间可选气象特征
- `ellectric/notebooks/01-*.ipynb` ~ `ellectric/notebooks/11-*.ipynb` — 全部重写，数据源切山东
- `ellectric/README.md` — 项目定位从"OWID+山西"改为"山东15min"
- `CLAUDE.md` — 更新数据源和常用命令描述

### 删除
- `ellectric/pipeline/shanxi_loader.py` — 山西 loader 模块
- `ellectric/data/raw/shanxi/` — 山西原始 JSON（约 1948 个文件）
- `ellectric/fetch/shanxi.py` — 山西抓取器
- `ellectric/scripts/fetch_shanxi.py` — 山西抓取 CLI 壳
- `ellectric/scripts/verify_shanxi_loader.py` — 山西验证脚本

### 不在范围内
- ❌ 不改 ASSUME 仿真配置
- ❌ 不改 API/CLI/LLM 接口层
- ❌ 不做多省
- ❌ 不做准实时调度
- ❌ 不接海数据付费数据集
- ❌ 不修改 service/handlers.py 业务逻辑

## 决策记录

| ID | 决策 | 理由 |
|---|---|---|
| D-001@v1 | ShandongDataLoader 继承 DataLoader ABC，扩展 schema（21 列全保留）| 工厂统一性 + 下游按需取列 |
| D-002@v1 | 删除山西 shanxi_loader.py + data/raw/shanxi/ + fetch/shanxi.py | 山西数据是参考价，山东是真实出清，不能混用 |
| D-003@v1 | Notebook 原地覆盖（git 历史可回溯旧版）| 避免 archive/ 目录碎片 |
| D-004@v1 | 本期一并接入 Open-Meteo 气象 | 山东数据已有新能源出力，气象做特征增强 |
| D-005@v1 | TimeConfig 默认值切到 96/672/"15min" | 小时级项目已成为过去，切 15min 为唯一模式 |
| D-006@v1 | 日前价格 75% null → features 和 trading 优先用实时价格 | 日前价每小时 1 点，实时价 15min 完整 |
| D-007@v1 | 不修改 existing DataLoader contract | `load_mw` 列仍保留为合同要求列 |

## 成功标准

1. `create_loader("shandong")` 返回 ShandongDataLoader 实例
2. `load_data()` 返回 71520 行，columns 含 timestamp / load_mw / rt_price / wind_actual / solar_actual 等
3. 11 个 notebook 全部可运行且无 Markdown 残留 OWID/山西引用
4. TimeConfig.points_per_day = 96，所有 pipeline 模块无需手动改配置即使用 15min 模式
5. WeatherFetcher 可 import 并返回山东气象历史数据
6. 现有 CLI 命令（forecast / simulate / backtest）在 shandong 源下可运行
7. 不引入新 Python 依赖（Open-Meteo 使用 urllib，weather 模块纯标准库）
