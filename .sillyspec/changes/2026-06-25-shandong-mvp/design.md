---
author: lmr
created_at: 2026-06-25T00:35:00+08:00
---
# 山东 15min MVP 数据切换 — 设计文档

## 背景

前置调研 `2026-06-24-tuji-data-granularity` 确认山西公开数据是月度典型日参考曲线，不足以做真实回测。用户提供山东 15min CSV 完整数据，项目切换到山东。

## 设计目标

1. ShandongDataLoader 继承 DataLoader ABC，保持工厂统一性
2. 21 列 schema 全部保留，下游按需取
3. TimeConfig 默认 96/672/"15min"
4. 删除山西模块
5. 接入 Open-Meteo 气象
6. 11 个 notebook 重写

## 设计概览

### 架构变化

```
Before:
  DataLoader ABC
    ├── OWIDChinaLoader
    ├── ChineseDataLoader  
    └── ShanxiSpotDaLoader / SpotRtLoader / MonthSettleLoader / ... (8 个)

After:
  DataLoader ABC
    ├── OWIDChinaLoader
    ├── ChineseDataLoader
    └── ShandongDataLoader         ← 新建，取代山西 8 个 loader

  + WeatherFetcher                  ← 新建，Open-Meteo 气象
```

### 文件清单

| 操作 | 路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/pipeline/shandong_loader.py` | ShandongDataLoader 类 (~200 行) |
| 新增 | `ellectric/fetch/weather.py` | WeatherFetcher 类 (~150 行) |
| 新增 | `ellectric/data/shandong/README.md` | 数据资产说明 |
| 修改 | `ellectric/pipeline/data_loader.py` | create_loader 加 shandong source key + 延迟导入 |
| 修改 | `ellectric/config.py` | TimeConfig 默认 96/672/15min |
| 修改 | `ellectric/pipeline/features.py` | 适配扩展列名（load_mw→直调负荷, wind→风电, solar→光伏） |
| 修改 | `ellectric/pipeline/trading_env.py` | docstring 更新，15min 已默认 |
| 修改 | `ellectric/pipeline/forecaster.py` | 适配 load_mw 列 |
| 修改 | `ellectric/pipeline/price_forecaster.py` | 适配价格列 (rt_price 替代 price_rt) |
| 修改 | `ellectric/notebooks/01_*.ipynb ~ 11_*.ipynb` | 数据源切换 |
| 修改 | `ellectric/README.md` | 定位更新 |
| 修改 | `CLAUDE.md` | 更新数据源描述 |
| 删除 | `ellectric/pipeline/shanxi_loader.py` | 山西 loader |
| 删除 | `ellectric/fetch/shanxi.py` | 山西 fetcher |
| 删除 | `ellectric/scripts/fetch_shanxi.py` | CLI 壳 |
| 删除 | `ellectric/scripts/verify_shanxi_loader.py` | 验证脚本 |
| 删除 | `ellectric/data/raw/shanxi/` | 原始 JSON (1948 个文件) |

### ShandongDataLoader 接口设计

```python
class ShandongDataLoader(DataLoader):
    """山东 15min 电力数据加载器。
    
    加载 山东_2024-2026_15min.csv → DataFrame。
    21 列全部保留，下游按需取。
    """

    REQUIRED_COLUMNS = {"timestamp", "load_mw"}  # 合约不变
    
    def __init__(self, data_path: str = "ellectric/data/shandong/山东_2024-2026_15min.csv"):
        ...

    def load_data(
        self, 
        start: str | None = None, 
        end: str | None = None
    ) -> pd.DataFrame:
        """
        Columns:
            timestamp          : datetime64[ns, UTC]
            load_mw            : float64 (→ 直调负荷(实际))
            rt_price           : float64 (实时价格, 元/MWh)
            da_price           : float64 (日前价格, 元/MWh, 75% null)
            wind_actual_mw     : float64
            solar_actual_mw    : float64
            nuclear_actual_mw  : float64
            captive_actual_mw  : float64 (自备机组)
            tie_line_actual_mw : float64 (联络线受电)
            pumped_actual_mw   : float64 (抽蓄)
            local_gen_actual_mw: float64 (地方电厂)
            is_holiday         : int (0/1)
            is_weekend         : int (0/1)
            province           : str ("shandong")
            source             : str
            granularity        : str ("15min")
            + 预测列 (可选，默认不映射，通过 include_forecasts=True 开启)
            
        Returns:
            DataFrame with 15min resolution, UTC timestamps
        """
```

### WeatherFetcher 接口设计

```python
class WeatherFetcher:
    """Open-Meteo 气象数据抓取器。
    
    免费，无 API key。覆盖济南/青岛历史气象。
    """

    SHANDONG_CITIES = {
        "jinan":   (36.65, 117.00),
        "qingdao": (36.07, 120.38),
    }

    def fetch_historical(
        self, 
        start: str = "2024-01-01", 
        end: str = "2026-01-14",
        variables: list[str] | None = None  # default: temperature, ghi, wind_speed, humidity
    ) -> pd.DataFrame:
        """
        Returns:
            DataFrame[timestamp, temp_jinan, temp_qingdao, ghi_jinan, ...
                       wind_speed_jinan, humidity_jinan, ...]
            hourly resolution, resampled to match Shandong data's 15min.
        """
```

## 数据合约更新

现有合约：
- `timestamp`: datetime64[ns, UTC]
- `load_mw`: float64 (MW)

扩展后（宽松附加）：
- `rt_price`: 实时出清价格 (元/MWh)
- `da_price`: 日前出清价格 (元/MWh，可能 null)
- `wind_actual_mw`, `solar_actual_mw`, `nuclear_actual_mw`
- `is_holiday`, `is_weekend`
- `province`, `source`, `granularity`

## 决策/方案选择

本变更 7 个技术决策详见 `decisions.md`，摘要：

| ID | 决策 | 备选 | 选择理由 |
|---|---|---|---|
| D-001@v1 | ShandongDataLoader 继承 ABC + 扩展 schema | 独立模块不继承 | 工厂统一，learn cost 最低 |
| D-002@v1 | 删除山西全量代码数据 | 保留归档 | 山西是参考价，混用有误导风险 |
| D-003@v1 | Notebook 原地覆盖 | 另存 archive | git 历史可回溯 |
| D-004@v1 | 本期接 Open-Meteo | 后续单独变更 | 边际成本低，气象特征立即可用 |
| D-005@v1 | TimeConfig 默认 96/672/15min | 保留小时+运行时切 | 项目已彻底 15min，不需小时级兼容 |
| D-006@v1 | 优先用实时价格 | 两项都做 | 日前价 75% null |
| D-007@v1 | 保留 load_mw 列名 | 改为 actual_load_mw | 下游模块都依赖此合约 |

## 自审

- 设计内部自洽：5 个新增 + 10 个修改 + 5 个删除
- 工厂统一性保持：create_loader("shandong") 与 owid/manual 一致
- 向下兼容：现有 load_mw 列仍存在，下游模块无需剧烈改动
- 气象集成轻量：WeatherFetcher 纯 HTTP，不依赖外部 SDK
- 风险：日前价格 75% null → 优先用实时价，已在 D-006 注明
