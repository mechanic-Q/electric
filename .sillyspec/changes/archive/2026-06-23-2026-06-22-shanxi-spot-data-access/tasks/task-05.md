---
id: task-05
title: 实现 ShanxiMonthSettleLoader 子类
author: lmr
created_at: 2026-06-23T15:10:00+08:00
priority: P0
estimated_hours: 1
depends_on: [task-02]
blocks: []
requirement_ids: [FR-006]
decision_ids: [D-002@v1]
allowed_paths:
  - ellectric/pipeline/shanxi_loader.py
---

# task-05: 实现 ShanxiMonthSettleLoader 子类

## 修改文件 (必填)
- `ellectric/pipeline/shanxi_loader.py` (同 task-02 文件，在 task-02 完成后追加 `ShanxiMonthSettleLoader` 类定义)

## 覆盖来源
- Requirements: FR-006（ShanxiMonthSettleLoader 字段、行数、列结构）
- Decisions: D-002@v1（价格类字段标 `inferred` 置信度，禁止丢列）

## 实现要求

继承 `ShanxiBaseLoader`，针对 `month_settle_YYYY-MM.json` 文件提供逐日分时电价的标准化加载器。具体实现要点：

1. **类签名**：`class ShanxiMonthSettleLoader(ShanxiBaseLoader):`，写法、docstring、`_metadata_source` 字段三件齐全。
2. **构造函数**：`__init__(self, data_dir: str | None = None)`，仅一行 `super().__init__(data_prefix="month_settle", data_dir=data_dir)`，禁止覆盖父类已封装的扫描/筛选/UTC 化逻辑。
3. **元数据**：在类层设置类属性 `_metadata_source = "shanxi-month-settle"`（父类同名属性的覆盖），`_metadata_version` 由父类 `__init__` 写为 `"month_settle/local-json"`。
4. **实现 `_standardize`**：将 `records: list[dict]`（来自单个 JSON 文件的 `data` 字段）转为 DataFrame，遵守字段映射表与 `load_mw=NaN` 合约，注入 `province`/`source`/`granularity`/`load_mw` 基础列。
5. **空 records 优雅返回**：当 `records == []`（API 该月份无数据）时，返回带正确列名、零行数的 DataFrame，**保留全部列结构**（含 `timestamp`/`time_point`/`settle_day_price`/`settle_rt_price`/`load_mw`/`province`/`source`/`granularity`），不抛异常。
6. **时间解析**：`dataTime` 字段格式为 ISO 日期字符串 `"yyyy-MM-dd"`（参考 `month_settle_2026-05.json` 实际形如 `"2026-04-01"`）。使用 `pd.to_datetime(dataTime, utc=True)` 转为 `datetime64[ns, UTC]`。对极少数文件中可能出现的 `null`/空串，归一为 `pd.NaT` 并落入降级日志。
7. **`point` 字段编码**：原始 JSON 中 `point` 可能呈现两种形式（实测样例为 `"00:00"`/`"01:00"`/.../`"23:00"` 字符串）：
   - 若是 `"HH:MM"` 字符串：取冒号前部分整数化为 `0..23`。
   - 若已是整数（兼容历史/未来兼容）：直接转 `int64`。
   - 若值非法（None / 非数字）：归为 `pd.NA` 后整列保留 `Int64` nullable 类型（避免抛错）。
8. **`load_mw` 列**：纯填 `np.nan`（`float64`），与 D-002@v1 价格类数据语义一致；下游不会消费该列，但 `DataLoader` 合约要求其存在。
9. **基础列注入**：每条记录附加 `province="shanxi"` / `source="pxf-phbsx-shop"` / `granularity="daily-point"`。
10. **日志**：函数入口与 happy path 末尾使用 `logger.debug(...)` 报告 `year_month` 与转换后的行数，异常字段 `logger.warning(...)`；禁止 `print`。

## 接口定义 (代码类任务必填)

### 类签名

```python
class ShanxiMonthSettleLoader(ShanxiBaseLoader):
    """山西月度结算电价（逐日分时）加载器 — Monthly Settlement Price Loader.

    数据语义 (Data Semantics)
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    - 覆盖范围: 2018-01 ~ 2026-12（108 月）
    - 粒度: 逐日分时，单日 23-24 个时段（小时级，非 15min）
    - 单日典型时段编号: 0..23（来自原始 "00:00" ~ "23:00"）
    - 行数预估: 108 月 × ≈ 23.4 点 ≈ 2525 行
    """

    _metadata_source = "shanxi-month-settle"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="month_settle", data_dir=data_dir)

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        ...
```

### `_standardize(records, year_month)` 控制流伪代码

```text
INPUT:
    records: list[dict]   # 形如 [{"dataTime": "2026-04-01", "point": "00:00",
                          #        "dayPrice": 323.41, "realTimePrice": 363.24}, ...]
    year_month: str       # 来自父类，例如 "2026-04"，仅用于日志/降级

OUTPUT:
    pd.DataFrame with exact columns (in this order):
        timestamp           datetime64[ns, UTC]
        time_point          Int64  (nullable int64)
        settle_day_price    float64
        settle_rt_price     float64
        load_mw             float64  (全 NaN)
        province            object   ("shanxi")
        source              object   ("pxf-phbsx-shop")
        granularity         object   ("daily-point")

STEPS:
1. if not records:
       logger.debug("month_settle[%s] 无记录，返回空 DataFrame", year_month)
       return _empty_frame()       # 列结构齐全的 0 行 DataFrame

2. rows = []
   for r in records:
       dt_raw   = r.get("dataTime")
       pt_raw   = r.get("point")
       day_p    = r.get("dayPrice")
       rt_p     = r.get("realTimePrice")

       # ── 时间解析 ──
       ts = pd.to_datetime(dt_raw, errors="coerce", utc=True)
       if pd.isna(ts):
           logger.warning("month_settle[%s] 跳过无效 dataTime=%r", year_month, dt_raw)
           continue

       # ── point 编码：'HH:MM' / int / 非法 ──
       tp = _coerce_time_point(pt_raw)   # 返回 int 或 pd.NA

       rows.append({
           "timestamp":        ts,
           "time_point":       tp,
           "settle_day_price": _to_float(day_p),
           "settle_rt_price":  _to_float(rt_p),
       })

3. df = pd.DataFrame(rows)
   df["time_point"]   = df["time_point"].astype("Int64")
   df["load_mw"]      = float("nan")
   df["province"]     = "shanxi"
   df["source"]       = "pxf-phbsx-shop"
   df["granularity"]  = "daily-point"
   df = df[<canonical_column_order>]

4. logger.debug("month_settle[%s] standardize OK rows=%d", year_month, len(df))
   return df
```

### 辅助函数（同模块内私有）

```python
def _coerce_time_point(value: object) -> int | None:
    """'HH:MM' → int(HH)；已是 int → int；其它 → None。"""
    if value is None:
        return None
    if isinstance(value, bool):           # bool 是 int 子类，先排除
        return None
    if isinstance(value, int):
        return int(value)
    if isinstance(value, str):
        head = value.split(":", 1)[0].strip()
        return int(head) if head.isdigit() else None
    return None


def _to_float(value: object) -> float:
    """安全 float 转换，None/异常 → NaN。"""
    try:
        return float(value) if value is not None else float("nan")
    except (TypeError, ValueError):
        return float("nan")
```

### 字段映射表（必填，落地必须 100% 对齐）

| 原始 JSON key | DataFrame 列名     | dtype           | 来源置信度        |
|---------------|--------------------|-----------------|-------------------|
| `dataTime`    | `timestamp`        | datetime64[ns,UTC] | 确定（ISO 日期）|
| `point`       | `time_point`       | Int64 (nullable)| 确定（小时编号 0..23）|
| `dayPrice`    | `settle_day_price` | float64         | 高频（D-002@v1） |
| `realTimePrice` | `settle_rt_price`| float64         | 高频（D-002@v1） |
| —             | `load_mw`          | float64 (全 NaN)| 合约填充           |
| —             | `province`         | object          | 硬编 `"shanxi"`   |
| —             | `source`           | object          | 硬编 `"pxf-phbsx-shop"` |
| —             | `granularity`      | object          | 硬编 `"daily-point"`     |

## 边界处理 (至少 5 条)

1. **records 为空 `[]`（API 该月份无数据）**：返回 0 行但列结构齐全的 DataFrame，不抛异常，记录 `logger.debug`。
2. **缺失文件**：由父类 `ShanxiBaseLoader.load_data()` 统一处理（扫描时未发现匹配 `month_settle_YYYY-MM.json` 即跳过），本子类无需重复处理；超范围调用最终汇成空 DataFrame 由父类返回。
3. **兼容旧 API 行为**：`OWIDChinaLoader` / `ChineseDataLoader` / `EmberLoader` / `ShanxiSpotDaLoader` / `ShanxiSpotRtLoader` 完全不变；本子类仅追加在 `shanxi_loader.py` 末端，不调整模块顶部公共函数。
4. **异常不静默**：单条记录解析失败（`dataTime=None` / `point` 非法 / `dayPrice` 非数字）记录 `logger.warning` 后跳过该单条记录，不吞掉整月文件；如果同一文件所有记录均失败，返回 0 行 DataFrame 并 `logger.warning` 提示该月份完全降级。
5. **不修改传参/全局状态**：`records` 入参不被 `pop` / `del` / `clear`；模块级常量、`pd.options`、`logger` 配置均不修改。
6. **dtype 一致性**：跨月份 concat 时 `time_point` 必须为 nullable `Int64`（避免某月份某行 NA 导致整列回退到 `object`）；空 DataFrame 也需按 canonical dtype 初始化。
7. **顺序稳定**：返回的 DataFrame 行顺序与 records 列表中的输入顺序一致（不内部排序），由父类在 `load_data()` 拼接后整体排序 by `timestamp`。
8. **重复时间戳**：同一文件可能存在两条 `(dataTime, point)` 相同的记录（数据源历史 quirk）；本子类**不去重**，保留全部记录交由调用方处理，避免静默丢数据。

## 非目标 (本任务不做的事)

- ❌ 不实现 `ShanxiBaseLoader` 基类（task-02 负责）
- ❌ 不修改 `data_loader.py` 的 `create_loader()` 工厂（task-06 负责）
- ❌ 不写验证脚本（task-07 负责）
- ❌ 不做 24:00 跨日处理：`month_settle` 数据为日内 `00:00 ~ 23:00`，**不含** `24:00` 边界；24:00 处理逻辑由 `ShanxiSpotDaLoader` / `ShanxiSpotRtLoader` 在父类基础上使用，本子类无该路径。
- ❌ 不做单位转换（settle 价格为元/MWh 直读直出）
- ❌ 不做"逐日分时去重"、"按月聚合"等高阶语义处理
- ❌ 不实现 `_make_timestamp(date_str, time_str)` 复合时间合成（本数据源 `dataTime` 已是完整日期，只需 `pd.to_datetime`）

## 参考

- 参考 `OWIDChinaLoader` (`ellectric/pipeline/data_loader.py:161-280` 区域) / `ChineseDataLoader` 模式
- 参考 `EmberLoader` 的延迟导入风格（task-06 用，但本任务关注其字段标准化代码风格）
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md`：中英双语 docstring、`# ═══` 分隔符、`logger = logging.getLogger(__name__)`、`_` 前缀内部函数
- 参考 `.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` III. 字段映射 / IV. 工厂扩展
- 参考实际样例文件 `ellectric/data/raw/shanxi/month_settle_2018-01.json` 与 `month_settle_2026-05.json`（确认 `point` 字段实际为 `"HH:MM"` 字符串）

## TDD 步骤 (代码类任务)

1. 最小 import：在 `shanxi_loader.py` 末尾追加 `class ShanxiMonthSettleLoader(ShanxiBaseLoader): pass`，从外部 `python -c "from ellectric.pipeline.shanxi_loader import ShanxiMonthSettleLoader; print(ShanxiMonthSettleLoader)"` 能 import 即第 1 步通过。
2. 实现 `__init__` 和 `_metadata_source`，从外部实例化 `loader = ShanxiMonthSettleLoader()` 不抛错，断言 `loader.data_prefix == "month_settle"`。
3. 实现 `_standardize` 的 happy path（取 `month_settle_2018-01.json` 单文件 5 行测试）：
   ```python
   import json
   records = json.load(open("ellectric/data/raw/shanxi/month_settle_2018-01.json"))["data"][:5]
   df = loader._standardize(records, "2018-01")
   assert list(df.columns) == ["timestamp", "time_point", "settle_day_price", "settle_rt_price", "load_mw", "province", "source", "granularity"]
   assert len(df) == 5
   assert df["load_mw"].isna().all()
   ```
4. 补齐边界处理：空 records、`dataTime=None`、`point="garbage"`、`dayPrice=None` 各喂一条，断言不抛异常且记录数符合预期。
5. 全文件验证：`loader.load_data()` 返回行数 `2400 <= rows <= 2700`（设计预估 2525）；`df["timestamp"].dtype == "datetime64[ns, UTC]"`；`df["time_point"].dtype.name == "Int64"`。
6. 跨子类回归：与 task-03 / task-04 同步落盘后跑 `pytest -q` (若 task-07 已加测试) 或手工执行 `verify_shanxi_loader.py`。

## 验收标准

| #     | 验证步骤                                                                                                                                                 | 通过标准                                                                                                                          |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| AC-01 | `python -c "from ellectric.pipeline.shanxi_loader import ShanxiMonthSettleLoader; l=ShanxiMonthSettleLoader(); print(l.data_prefix, l._metadata_source)"` | 退出码 0，输出 `month_settle shanxi-month-settle`                                                                                  |
| AC-02 | `python -c "...; df = ShanxiMonthSettleLoader().load_data(); print(len(df), list(df.columns))"`                                                          | `len(df)` ∈ [2400, 2700]；columns 完全等于 `['timestamp','time_point','settle_day_price','settle_rt_price','load_mw','province','source','granularity']`，顺序一致 |
| AC-03 | `python -c "...; df=ShanxiMonthSettleLoader().load_data(); print(df['timestamp'].dtype, df['time_point'].dtype, df['load_mw'].isna().mean())"`             | `datetime64[ns, UTC]`、`Int64`、`load_mw` NaN 占比 = `1.0`                                                                          |
| AC-04 | `python -c "...; df=ShanxiMonthSettleLoader().load_data(start='2010-01', end='2010-12'); print(len(df))"`                                                | 退出码 0，输出 `0`（超范围优雅降级，对应 FR-009）                                                                                   |
| AC-05 | `python -c "...; df=ShanxiMonthSettleLoader().load_data(start='2018-01', end='2018-01'); print(df['province'].unique(), df['source'].unique(), df['granularity'].unique())"` | 输出分别为 `['shanxi']`、`['pxf-phbsx-shop']`、`['daily-point']`                                                                    |
| AC-06 | `time python -c "...; ShanxiMonthSettleLoader().load_data()"`                                                                                            | 实际墙钟时间 < 5 秒（NFR-001）                                                                                                    |
| AC-07 | `grep -c "^from ellectric.pipeline.shanxi_loader" ellectric/pipeline/data_loader.py`                                                                     | 输出 `0`（顶层未引入 shanxi_loader，确认 D-005@v1 文件隔离前提下 task-05 没污染 data_loader.py）                                   |
