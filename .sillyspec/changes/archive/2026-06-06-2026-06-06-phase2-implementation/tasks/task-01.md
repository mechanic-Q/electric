---
id: task-01
title: 创建 price_loader.py — 加载 ZionLuo xlsx，标准化列名，返回标准 DataFrame
author: lmr
created_at: 2026-06-06T19:36:10+08:00
priority: P0
estimated_hours: 2
depends_on: []
blocks: [task-03]
allowed_paths:
  - ellectric/pipeline/price_loader.py
---

# task-01: 创建 price_loader.py — 加载 ZionLuo xlsx，标准化列名，返回标准 DataFrame

## 修改文件

| 操作 | 文件 |
|------|------|
| 新建 | `ellectric/pipeline/price_loader.py` |

## 实现要求

1. **不继承 DataLoader ABC** — 设计文档明确"电价数据格式与负荷数据差异大，不适合复用 DataLoader"
2. **遵循 Phase 1 设计惯例**：模块级 docstring（设计理念 + 架构图 + 模块职责）、`_safe_float` 工具函数、`get_metadata()` 方法、UTC 时区统一、logger 配置
3. **读取 ZionLuo xlsx 文件**（7 列）：timestamp, price_da, price_rt, load_mw, wind_mw, solar_mw, tie_line_mw
4. **列名标准化**：中文列名（如"日前价格"、"统调负荷"）→ 英文标准名
5. **工厂函数**：`create_price_loader()`

## 接口定义

### PriceDataLoader 类

```python
class PriceDataLoader:
    def __init__(self, data_path: str) -> None: ...

    def load_data(self) -> pd.DataFrame:
        """
        加载 xlsx -> 标准化列名 -> UTC 时区 -> 排序后返回

        Returns:
            DataFrame with columns:
              - timestamp:   datetime64[ns, UTC]
              - price_da:    float64  日前价格 (元/MWh)
              - price_rt:    float64  实时价格 (元/MWh)
              - load_mw:     float64  统调负荷 (MW)
              - wind_mw:     float64  风电出力 (MW)
              - solar_mw:    float64  光伏出力 (MW)
              - tie_line_mw: float64  省间联络线功率 (MW)
        """

    def get_metadata(self) -> dict:
        """
        Returns:
            source, data_version, rows, start, end, frequency,
            以及 price_da_stats, price_rt_stats, load_stats
        """
```

### 列名标准化映射

| 中文/别名 | 标准名 |
|-----------|--------|
| 时间, 日期, Datetime, time | timestamp |
| 日前价格, 日前, dam, day_ahead_price | price_da |
| 实时价格, 实时, rt, real_time_price | price_rt |
| 负荷, 统调负荷, 用电负荷, load | load_mw |
| 风电, 风电出力, wind | wind_mw |
| 光伏, 光伏出力, solar, PV, 光 | solar_mw |
| 联络线, 省间联络线, tie_line, 省间 | tie_line_mw |

### 工厂函数

```python
def create_price_loader(data_path: str = "data/price_data.xlsx") -> PriceDataLoader:
    """创建 PriceDataLoader 实例。"""
```

## 边界处理

| # | 场景 | 处理方法 |
|---|------|----------|
| 1 | xlsx 文件不存在 | `raise FileNotFoundError`，提示用户从 ZionLuo 仓库下载 |
| 2 | xlsx 中列名不匹配任何已知别名 | 保留原列名，`logger.warning` 输出未识别列 |
| 3 | 某列全部为空 | `logger.warning` 提醒，仍返回 DataFrame |
| 4 | 时间戳解析失败（非标准日期格式） | `pd.to_datetime(..., errors='coerce')`，丢弃无法解析的行并 `logger.warning` |
| 5 | 数值列含非数字字符 | `pd.to_numeric(..., errors='coerce')`，`logger.warning` 统计损坏比例 |
| 6 | 数据频率不固定（非严格小时级） | 仅基于存在性检测频率，不强制重采样 |
| 7 | 多 sheet 的 xlsx | 默认读取第一个 sheet，`logger.info` 告知 sheet 名称 |
| 8 | 空数据集（无有效行） | 返回空 DataFrame，`logger.warning` |

## 非目标

- 不支持 load_data(start/end) 参数（Wave 1 不要求时间过滤）
- 不继承 `DataLoader` ABC
- 不做数据清洗（缺失填充、异常检测）
- 不做重采样或频率转换
- 不自动下载文件（用户手动从 ZionLuo/Electricity-Price-Forecasting 下载）

## 参考

- Phase 1 `data_loader.py`：模块 docstring 格式、`_safe_float`、`_standardize_columns` 模式
- Phase 2 `design.md § Wave 1 详细设计 > 新增模块：price_loader.py`
- Phase 2 `plan.md § Wave 1` + 全局验收标准第 2 条

## TDD 步骤

```
1. [NEW] tests/pipeline/test_price_loader.py + test_price_loader_init (构造函数)
2. [NEW] test_price_loader_load (加载真实 xlsx，验证 7 列)
3. [NEW] test_price_loader_column_standardization (中/英列名→标准)
4. [NEW] test_price_loader_timezone (timestamp 是 UTC)
5. [NEW] test_price_loader_metadata (get_metadata 返回正确结构)
6. [NEW] test_price_loader_file_not_found (异常路径)
7. [NEW] test_create_price_loader (工厂函数)
```

## 验收标准

| # | 检查项 | 验证方式 |
|---|--------|----------|
| 1 | `from ellectric.pipeline import PriceDataLoader` 可导入 | `pytest tests/pipeline/test_price_loader.py::test_price_loader_init` 通过 |
| 2 | `PriceDataLoader("data/price_data.xlsx").load_data()` 返回 7 列 DataFrame | 测试验证列名精确匹配 |
| 3 | 返回 DataFrame 的 timestamp 列为 `datetime64[ns, UTC]` | `df["timestamp"].dtype` 含 `UTC` |
| 4 | 中/英列名混合的 xlsx 都能正确标准化 | 测试用 mock 数据验证 |
| 5 | `get_metadata()` 返回含 source, rows, start, end 等键的 dict | `assert "source" in meta` |
| 6 | 文件不存在时抛出 `FileNotFoundError` | `pytest.raises(FileNotFoundError)` |
| 7 | `create_price_loader()` 返回 `PriceDataLoader` 实例 | `isinstance(loader, PriceDataLoader)` |
