---
id: task-03
title: 实现 ShanxiSpotDaLoader 子类
priority: P0
depends_on: [task-02]
blocks: []
requirement_ids: [FR-004]
decision_ids: [D-002@v1]
author: lmr
created_at: 2026-06-23T15:10:00+08:00
allowed_paths:
  - ellectric/pipeline/shanxi_loader.py
---

# task-03: 实现 ShanxiSpotDaLoader 子类

## 修改文件 (必填)
- `ellectric/pipeline/shanxi_loader.py` (在 task-02 已建立 ShanxiBaseLoader 之后追加,不新建文件)

## 覆盖来源
- Requirements: FR-004 — `create_loader("shanxi_spot_da").load_data(start="2022-04", end="2026-05")` 必须返回含 `timestamp`/`da_price_a`/`da_price_b`/`load_mw`/`province`/`source`/`granularity` 列的 DataFrame,行数 ≈ 4800
- Decisions: D-002@v1 — `record1` → `da_price_a`,`record2` → `da_price_b`(推断为日前出清价价区 A/B,元/MWh,推断置信度)

## 实现要求

`ShanxiSpotDaLoader` 继承 task-02 提供的 `ShanxiBaseLoader`:

- `__init__(data_dir: str | None = None)`:调用 `super().__init__(data_prefix="spot_da", data_dir=data_dir)`,之后覆盖 `self._metadata_source = "shanxi-spot-da"`,`self._metadata_version = "spot_da/local-json/v1"`
- `_standardize(records: list[dict], year_month: str) -> pd.DataFrame`:实现父类抽象方法,字段映射如下:
  - `endPointTime` (字符串,如 `"08:15"` 或 `"24:00"`) → `timestamp`(UTC 时区,15min 时段结束时间);通过父类 `_make_timestamp(year_month, end_point_time)` 处理,其中跨日 `24:00` 转换为次日 `00:00`
  - `record1` → `da_price_a` (float64,日前出清价价区 A,元/MWh,**inferred**)
  - `record2` → `da_price_b` (float64,日前出清价价区 B,元/MWh,**inferred**)
- 额外注入(三个常量列):
  - `province` = `"shanxi"`
  - `source` = `"pxf-phbsx-shop"`
  - `granularity` = `"15min"`
- `load_mw`:**纯价格类**,设为 `float("nan")`(满足 `DataLoader` 抽象合约,但不携带负荷信息;NaN 由下游忽略)
- 返回的列顺序固定为: `[timestamp, da_price_a, da_price_b, load_mw, province, source, granularity]`(便于下游/测试断言)

## 接口定义 (代码类任务必填,task-01 README 类填字段表)

```python
class ShanxiSpotDaLoader(ShanxiBaseLoader):
    """
    山西日前现货出清价 loader (15min × 96 点 × 50 月)。

    字段映射 (D-002@v1, inferred):
    - endPointTime → timestamp (UTC)
    - record1      → da_price_a  (日前出清价 A,元/MWh)
    - record2      → da_price_b  (日前出清价 B,元/MWh)
    - load_mw      → NaN         (价格类数据无负荷等效)
    """

    _metadata_source = "shanxi-spot-da"
    _metadata_version = "spot_da/local-json/v1"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="spot_da", data_dir=data_dir)

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        # 控制流伪代码:
        # 1. if not records: return self._empty_frame()    # 空响应优雅退化(基础列结构由父类提供 _empty_frame)
        # 2. rows: list[dict] = []
        # 3. for rec in records:
        #      end_point = rec.get("endPointTime")
        #      if end_point is None: continue (warn)
        #      try:
        #          ts = self._make_timestamp(year_month, end_point)
        #      except ValueError as e:
        #          logger.warning("跳过非法时间 %s/%s: %s", year_month, end_point, e)
        #          continue
        #      rows.append({
        #          "timestamp":  ts,
        #          "da_price_a": _safe_float(rec.get("record1")),
        #          "da_price_b": _safe_float(rec.get("record2")),
        #      })
        # 4. df = pd.DataFrame(rows)
        # 5. if df.empty: return self._empty_frame()
        # 6. df["load_mw"]     = float("nan")
        # 7. df["province"]    = "shanxi"
        # 8. df["source"]      = "pxf-phbsx-shop"
        # 9. df["granularity"] = "15min"
        # 10. return df[["timestamp", "da_price_a", "da_price_b", "load_mw",
        #                "province", "source", "granularity"]]
        ...
```

字段类型与样例:

| 列名 | dtype | 样例 | 来源 JSON 字段 |
|---|---|---|---|
| `timestamp` | datetime64[ns, UTC] | `2022-04-01 00:15:00+00:00` | `endPointTime` + year_month |
| `da_price_a` | float64 | `345.67` | `record1` |
| `da_price_b` | float64 | `352.10` | `record2` |
| `load_mw` | float64 | `NaN` | — (恒 NaN) |
| `province` | object/str | `"shanxi"` | — (常量) |
| `source` | object/str | `"pxf-phbsx-shop"` | — (常量) |
| `granularity` | object/str | `"15min"` | — (常量) |

## 边界处理 (至少 5 条)

1. **空 records 列表**:某月份 JSON 的 `data` 字段为空数组(常见于 2022-04 之前)→ 直接返回 `self._empty_frame()`(由父类提供的含 7 列基础结构的空 DataFrame),不抛异常,记录 INFO 日志
2. **缺失文件**:由父类 `load_data()` 在扫描阶段处理,本子类 `_standardize` 不直接关心;若被传入空 records 走第 1 条
3. **null 字段值**:`record1` 或 `record2` 为 `None`/缺失键 → 用 `_safe_float()` 转换为 `NaN`(沿用 `data_loader.py` 已存在的工具函数),**不丢行**(保留 timestamp,价格 NaN)
4. **24:00 边界**:`endPointTime == "24:00"` → 父类 `_make_timestamp` 已规约为次日 `00:00`(UTC),本子类不重复实现
5. **非法时间字符串**:`endPointTime` 不符合 `HH:MM` 格式 → `_make_timestamp` 抛 `ValueError`,本子类 `try/except` 捕获后**跳过该行 + WARNING 日志**,不污染整个月数据
6. **兼容旧 API 行为**:`OWIDChinaLoader` / `ChineseDataLoader` / `EmberLoader` / `create_loader("owid"|"manual"|"ember")` 完全不动(本任务只新增类,不改动既有代码)
7. **异常不静默**:JSON 解析失败、文件 IO 失败由父类负责;子类 `_standardize` 内部仅捕获**单行级别**的 `ValueError`(跳过坏行),其他 Exception 透传
8. **不修改传参/全局状态**:`records` 参数 read-only,不 `pop`/`del`;不修改 `year_month`;不写任何模块级变量;`_metadata_*` 仅在 `__init__` 写一次

## 非目标 (本任务不做的事)

- 不实现 `ShanxiBaseLoader` 基类(归属 task-02)
- 不实现 `ShanxiSpotRtLoader` / `ShanxiMonthSettleLoader`(归属 task-04 / task-05)
- 不修改 `data_loader.py` 的 `create_loader()` 工厂(归属 task-06)
- 不写验证脚本(归属 task-07)
- 不做单位换算(元/MWh 直传,不转 元/kWh)
- 不做缺失值插值/异常值清洗(属于下游 `clean_data` 的职责)
- 不做小时级聚合(留给 `time-resolution-param` 后续变更)
- 不接入 FastAPI/CLI/LLM

## 参考

- 参考 `OWIDChinaLoader` / `ChineseDataLoader` / `EmberLoader` 模式 (`ellectric/pipeline/data_loader.py`,延迟导入 + 工厂分支)
- 参考 `_safe_float()` 工具函数 (`ellectric/pipeline/data_loader.py:525-532`),可在 `shanxi_loader.py` 顶部 `from ellectric.pipeline.data_loader import _safe_float` 复用
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` 编码规范(中英双语 docstring、`logger = logging.getLogger(__name__)`、`# ═════` 顶级分界、`# ── ── ──` 子级分界、类型标注、`_` 前缀内部方法)
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` 章节:
  - III. 字段映射 → spot_da 子表
  - IV. 工厂扩展 → source key 命名约定
  - V. 时间限制 → 2022-04 ~ 2026-05 有效范围
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/decisions.md` D-002@v1 的 `inferred` 置信度声明

## TDD 步骤 (代码类任务,文档类任务跳过)

1. 在 task-02 完成的 `shanxi_loader.py` 末尾追加 `class ShanxiSpotDaLoader(ShanxiBaseLoader):`,只放 `__init__`,运行 `python -c "from ellectric.pipeline.shanxi_loader import ShanxiSpotDaLoader; ShanxiSpotDaLoader()"` 确认可实例化
2. 实现 `_standardize` 最小 happy path:取一条真实 record(从 `ellectric/data/raw/shanxi/spot_da_2024-01.json` 的 `data[0]` 拷贝),手工构造 `records=[...]` 调用 `loader._standardize(records, "2024-01")`,断言列名 7 列、行数 1
3. 调用 `loader.load_data(start="2024-01", end="2024-01")`,断言返回 96 行(单月 96 点),`load_mw.isna().all()` 为 True
4. 完善边界处理:构造含 `endPointTime="24:00"` 的 record、含 `record1=None` 的 record、含非法时间字符串的 record,逐项验证 2-7 条行为
5. 调用 `loader.load_data(start="2022-04", end="2026-05")` 全量,断言行数在 4700 ~ 4900 之间(允许部分月份 data=[]),验证 5 秒内完成(NFR-001)

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `from ellectric.pipeline.shanxi_loader import ShanxiSpotDaLoader; loader = ShanxiSpotDaLoader(); df = loader.load_data(start="2022-04", end="2026-05")` | `df` 是 `pd.DataFrame`,`len(df)` ∈ [4700, 4900],退出码 0 |
| AC-02 | `set(df.columns) >= {"timestamp", "da_price_a", "da_price_b", "load_mw", "province", "source", "granularity"}` | 7 列全部存在,顺序与接口定义一致 |
| AC-03 | `df["timestamp"].dt.tz` 等于 `datetime.timezone.utc` 或等价的 `pytz.UTC` | dtype 是 `datetime64[ns, UTC]`,无 naive 时间戳 |
| AC-04 | `df["load_mw"].isna().all()` | 所有行 `load_mw` 均为 NaN(纯价格 loader) |
| AC-05 | `df["province"].unique().tolist() == ["shanxi"]` 且 `df["source"].unique().tolist() == ["pxf-phbsx-shop"]` 且 `df["granularity"].unique().tolist() == ["15min"]` | 三常量列单一值,无脏值 |
| AC-06 | `loader.get_metadata()` | 返回 dict 含 `source="shanxi-spot-da"`,`rows == len(df)`,`start`/`end` 字符串非空 |
| AC-07 | `loader.load_data(start="2010-01", end="2010-12")` (超范围) | 返回空 DataFrame(`len == 0`),含 7 列基础结构,日志包含 WARNING,**不抛异常** |
| AC-08 | `df["da_price_a"].dtype == "float64"` 且 `df["da_price_b"].dtype == "float64"` | dtype 校验通过 |
| AC-09 | 计时 `import time; t=time.time(); loader.load_data(start="2022-04", end="2026-05"); assert time.time()-t < 5` | 5 秒内完成,满足 NFR-001 |
| AC-10 | `git diff ellectric/pipeline/data_loader.py` | 输出为空(本任务不改 data_loader.py) |
