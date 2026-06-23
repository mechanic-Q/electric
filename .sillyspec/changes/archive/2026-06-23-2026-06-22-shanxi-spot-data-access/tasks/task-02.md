---
id: task-02
title: 在 pipeline/shanxi_loader.py 实现 ShanxiBaseLoader 抽象基类
priority: P0
depends_on: []
blocks: [task-03, task-04, task-05, task-06]
requirement_ids: [FR-003, NFR-002, NFR-003]
decision_ids: [D-001@v1, D-005@v1]
author: lmr
created_at: 2026-06-23T15:10:00+08:00
allowed_paths:
  - ellectric/pipeline/shanxi_loader.py
---

# task-02: 在 pipeline/shanxi_loader.py 实现 ShanxiBaseLoader 抽象基类

## 修改文件 (必填)
- ellectric/pipeline/shanxi_loader.py (新增)

## 覆盖来源
- Requirements: FR-003 (ShanxiBaseLoader 抽象基类), NFR-002 (代码风格 — 中英双语 docstring/logger/类型标注), NFR-003 (依赖管理 — 不引入新依赖)
- Decisions: D-001@v1 (Loader 三子类继承架构 — 基类承载共性), D-005@v1 (拆独立 shanxi_loader.py 文件)

## 实现要求

在 `ellectric/pipeline/shanxi_loader.py` 实现抽象基类 `ShanxiBaseLoader`，继承自 `ellectric.pipeline.data_loader.DataLoader` (ABC)。基类必须封装如下能力：

1. **构造函数** `__init__(self, data_prefix: str, data_dir: str | Path | None = None)`：
   - `data_prefix` 必填，子类传入 (`"spot_da"` / `"spot_rt"` / `"month_settle"`)，用于 glob 匹配文件名
   - `data_dir` 可选，默认 `Path("ellectric/data/raw/shanxi")`
   - 设置 `self.data_prefix`、`self.data_dir`（统一转 `Path`）
   - 设置 `self._metadata_source`（子类可覆盖类属性，默认 `"shanxi-pxf-phbsx-shop"`）
   - 设置 `self._metadata_version = f"{data_prefix}/local-json"`

2. **核心方法** `load_data(self, start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame`：
   - 步骤 1：glob 匹配 `self.data_dir / f"{self.data_prefix}_*.json"`（不含 `_dict.json` 后缀的 wrapper 文件，正则或后缀过滤排除）
   - 步骤 2：对每个文件解析文件名末尾 `YYYY-MM`（regex `r"_(\d{4}-\d{2})\.json$"`），失败者 `logger.warning` 跳过
   - 步骤 3：用 `start` / `end` 对 `YYYY-MM` 做月份过滤（字符串比较即可，因为 `YYYY-MM` 字符序与时间序一致；接受 `"YYYY-MM"` 或 `"YYYY-MM-DD"` 输入，取前 7 字符）
   - 步骤 4：读 JSON 文件 → `data = json.load(f)`，从中取 `records: list[dict]`（兼容两种结构：顶层即 list；或 `{"data": [...]}` / `{"records": [...]}`，按子类需求由 `_records_from_json(raw)` hook 解析，默认实现尝试 `raw["data"]` → `raw["records"]` → `raw`）
   - 步骤 5：调用 `_standardize(records, year_month)`（抽象方法，子类实现）拿到月度 DataFrame
   - 步骤 6：用 `pd.concat([...], ignore_index=True)` 合并所有月度 DataFrame
   - 步骤 7：注入基础列 `province`、`source`、`granularity`（由子类类属性提供：`_province`、`_source`、`_granularity`）
   - 步骤 8：按 `timestamp` 升序排序、`reset_index(drop=True)`
   - 步骤 9：当全部 records 为空 → 返回带列名的空 DataFrame，并 `logger.warning` "未匹配到任何数据 (prefix=..., start=..., end=...)"
   - 步骤 10：返回 DataFrame

3. **抽象方法** `_standardize(self, records: list[dict], year_month: str) -> pd.DataFrame`：
   - 用 `@abstractmethod` 装饰
   - 子类必须实现，将原始 records 转为含 `timestamp` + 业务字段 + `load_mw` 的标准化 DataFrame
   - docstring 注明返回 DataFrame 不需含 `province`/`source`/`granularity`（基类负责注入）

4. **辅助方法** `_make_timestamp(self, date_str: str, time_str: Optional[str] = None) -> pd.Timestamp`：
   - 处理 `date_str` 形如 `"2024-05-01"` 或 `"2024-05"`，`time_str` 形如 `"08:15"` / `"24:00"` / `None`
   - 当 `time_str == "24:00"`：解析为 `date+1 天 00:00`（使用 `pd.Timedelta(days=1)`）
   - 标准化为 `pd.Timestamp(..., tz="UTC")`
   - 解析失败 → 抛 `ValueError(f"无法解析时间戳: date={date_str}, time={time_str}")`

5. **辅助方法** `_records_from_json(self, raw: dict | list) -> list[dict]`：
   - 默认实现：`if isinstance(raw, list): return raw; if isinstance(raw, dict): return raw.get("data") or raw.get("records") or []`
   - 子类可覆盖

6. **类属性**（基类提供默认值，子类覆盖）：
   - `_metadata_source: str = "shanxi-pxf-phbsx-shop"`
   - `_province: str = "shanxi"`
   - `_source: str = "pxf-phbsx-shop"`
   - `_granularity: str = "15min"`（子类 `ShanxiMonthSettleLoader` 覆盖为 `"daily-point"`）

7. **模块级要求** (NFR-002)：
   - 文件顶部模块级 docstring：中英双语，`====` 下划线分隔标题，`~~~~` 波浪线分隔段落，含 ASCII 类层次图
   - `logger = logging.getLogger(__name__)`
   - 全部函数/方法签名带完整类型标注
   - 段落分隔使用 `# ═══════════════` (顶级) / `# ── ... ──` (子级)
   - 仅导入 `abc`、`json`、`logging`、`re`、`pathlib`、`typing`、`pandas`、`ellectric.pipeline.data_loader.DataLoader` —— 不引入新第三方依赖 (NFR-003)

## 接口定义 (必填)

```python
"""
山西电力现货数据加载器 — 省级 15min 现货市场数据接入层
========================================================

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

本模块为山西电力交易中心(pmos.sx.sgcc.com.cn)零售商城公开 API
提供本地 JSON 归档数据的 loader 适配层。所有 loader 共享文件扫描、
月份过滤、UTC 时间标准化、24:00 边界处理等公共逻辑，由抽象基类
ShanxiBaseLoader 提供，子类只需实现 _standardize() 完成字段映射。

类层次 (Class Hierarchy)
~~~~~~~~~~~~~~~~~~~~~~~~

  DataLoader (ABC, data_loader.py)
       │
       └── ShanxiBaseLoader (本模块, 抽象基类)
              ├── ShanxiSpotDaLoader      (task-03)
              ├── ShanxiSpotRtLoader      (task-04)
              └── ShanxiMonthSettleLoader (task-05)
"""

from __future__ import annotations

import json
import logging
import re
from abc import abstractmethod
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ellectric.pipeline.data_loader import DataLoader

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════

_DEFAULT_DATA_DIR = Path("ellectric/data/raw/shanxi")
_YEAR_MONTH_RE = re.compile(r"_(\d{4}-\d{2})\.json$")


class ShanxiBaseLoader(DataLoader):
    """山西现货数据 loader 抽象基类，封装文件扫描 + 月份过滤 + UTC 化。"""

    _metadata_source: str = "shanxi-pxf-phbsx-shop"
    _province: str = "shanxi"
    _source: str = "pxf-phbsx-shop"
    _granularity: str = "15min"

    def __init__(self, data_prefix: str, data_dir: Optional[Union[str, Path]] = None) -> None:
        self.data_prefix: str = data_prefix
        self.data_dir: Path = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._metadata_version: str = f"{data_prefix}/local-json"

    # ── 公开接口 ──

    def load_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """扫描 prefix 匹配的 JSON 文件，按月份过滤并合并。"""
        # 1. glob 匹配
        # 2. 文件名解析 YYYY-MM
        # 3. 月份过滤
        # 4. 读 JSON / _records_from_json
        # 5. 调 _standardize → 月度 DataFrame
        # 6. concat + 注入基础列 + 排序
        ...

    # ── 子类钩子 ──

    @abstractmethod
    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        """子类实现：将原始 records 转为标准化 DataFrame（含 timestamp + load_mw + 业务列）。"""
        ...

    def _records_from_json(self, raw: Union[dict, list]) -> list[dict]:
        """从 JSON 顶层结构提取 records 列表，子类可覆盖。"""
        ...

    # ── 辅助方法 ──

    def _make_timestamp(self, date_str: str, time_str: Optional[str] = None) -> pd.Timestamp:
        """date_str + time_str → UTC pd.Timestamp，处理 24:00 跨日。"""
        ...

    def _filter_files_by_month(
        self,
        files: list[Path],
        start: Optional[str],
        end: Optional[str],
    ) -> list[tuple[Path, str]]:
        """从文件名抽取 YYYY-MM，按 [start, end] 过滤，返回 (path, ym) 列表。"""
        ...

    def _empty_frame(self) -> pd.DataFrame:
        """返回带 timestamp/load_mw/province/source/granularity 列的空 DataFrame。"""
        ...
```

控制流（伪代码）：

```
load_data(start, end):
    files = sorted(self.data_dir.glob(f"{self.data_prefix}_*.json"))
    files = [f for f in files if not f.name.endswith("_dict.json")]
    pairs = self._filter_files_by_month(files, start, end)
    if not pairs:
        logger.warning("未匹配到任何数据 ...")
        return self._empty_frame()

    parts: list[pd.DataFrame] = []
    for path, ym in pairs:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        records = self._records_from_json(raw)
        if not records:
            continue
        df_m = self._standardize(records, ym)
        if df_m.empty:
            continue
        parts.append(df_m)

    if not parts:
        return self._empty_frame()

    df = pd.concat(parts, ignore_index=True)
    df["province"] = self._province
    df["source"] = self._source
    df["granularity"] = self._granularity
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
```

## 边界处理 (≥ 5 条)

1. **空目录 / 无匹配文件**：`data_dir` 不存在或无匹配文件 → 返回 `_empty_frame()`（保持 5 列基础结构），`logger.warning` 包含 prefix/start/end，不抛异常 (FR-009)。
2. **`_dict.json` wrapper 文件**：必须用 `not name.endswith("_dict.json")` 过滤，避免误读山西原始数据集中存在的 66 个空 wrapper 文件。
3. **文件名 YYYY-MM 解析失败**：regex 不匹配的文件 `logger.warning("跳过文件: 无法解析年月 %s", path.name)` 后跳过，不中断整体扫描。
4. **start/end 入参兼容**：接受 `"YYYY-MM"` 或 `"YYYY-MM-DD"`（取前 7 字符做月份比较）；`None` 表示不限边界；`start > end` 时不抛异常，自然返回空（不做范围校验，由调用方负责）。
5. **24:00 时间点跨日**：`_make_timestamp(date, "24:00")` 必须解析为 `date + 1 天 00:00 UTC`，避免 `pd.Timestamp` 抛 `ValueError`。
6. **JSON 顶层结构歧义**：`_records_from_json` 默认支持 list / `{"data": [...]}` / `{"records": [...]}`；无法识别时返回 `[]`（不抛异常），由月度循环自动跳过。
7. **单月 records 为空但文件存在**：`_standardize` 返回空 DataFrame → 跳过该月不加入 `parts`，不污染最终结果。
8. **不修改传参 / 全局状态**：所有方法纯函数式（除写 `self.*` 实例属性外不修改外部对象），不修改 `records` 入参 list 元素，不缓存到模块级变量。
9. **异常不静默**：`_standardize` 内部的 `KeyError` / `ValueError`（字段缺失、时间解析失败）不在基类捕获，由调用方/子类自行处理；基类只对 "文件不存在 / JSON 解析失败 / 整体无数据" 这类输入层异常做 warning 降级。

## 非目标 (本任务不做的事)

- 不实现 3 个具体子类 `ShanxiSpotDaLoader` / `ShanxiSpotRtLoader` / `ShanxiMonthSettleLoader`（分别归 task-03/04/05）。
- 不修改 `ellectric/pipeline/data_loader.py`（`create_loader()` 工厂扩展归 task-06）。
- 不实现验证脚本（归 task-07）。
- 不做小时级聚合 / 不做下游 features.py / forecaster.py 修改（详见 design.md 非目标）。
- 不读 raw JSON 之外的 Excel/CSV/parquet（基类只处理 JSON 文件）。
- 不引入新第三方依赖（NFR-003）。

## 参考

- 参考 `ellectric/pipeline/data_loader.py::DataLoader` 抽象基类签名与 `get_metadata()` 默认实现
- 参考 `ellectric/pipeline/data_loader.py::OWIDChinaLoader` 多级回退 + 缓存 + logger + 类属性 `_metadata_source/_metadata_version` 模式
- 参考 `ellectric/pipeline/data_loader.py::ChineseDataLoader` 文件路径解析 + UTC 化模式
- 参考 `ellectric/pipeline/ember_loader.py`（如存在）省级特化 loader 的延迟导入模式
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` 模块级 docstring/分隔符/类型标注/日志规范
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` 第 II 节（Loader 架构）与第 III 节（字段映射 — 子类 schema）
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` 第 IV 节（工厂扩展）了解 source key 与子类的对应（本任务不实现工厂，但需保证基类接口可被 task-06 安全延迟导入）

## TDD 步骤

1. 写文件骨架：模块 docstring + import + `logger` + `class ShanxiBaseLoader(DataLoader)` 空壳；`python -c "from ellectric.pipeline.shanxi_loader import ShanxiBaseLoader"` 成功。
2. 实现 `__init__` + 类属性，构造一个匿名子类（提供 `_standardize` 返回空 DataFrame）→ 验证可实例化 + `get_metadata()` 不抛错（依赖 `load_data` 的空路径分支）。
3. 实现 `_make_timestamp`：用 `python -c "..."` 单测 `"2024-05-01" + "08:15"` 与 `"2024-05-01" + "24:00"` 两个 case，结果分别为 `2024-05-01 08:15:00+00:00` 与 `2024-05-02 00:00:00+00:00`。
4. 实现 `_records_from_json` + `_filter_files_by_month` + `_empty_frame`，对 `_DEFAULT_DATA_DIR` 中真实文件 glob 一遍，确认 `_dict.json` 被过滤、`YYYY-MM` 解析正确。
5. 实现 `load_data` 主流程；构造一个 mock 子类（`_standardize` 返回 `pd.DataFrame({"timestamp": [...], "load_mw": [...]})`）跑 spot_da 前缀，确认行数 / 列名 / 排序 / 基础列注入 / 空文件回退全部正确。
6. 加边界测试：`start="2010-01"`（超下界）、`end="2030-12"`（超上界）、`data_dir=Path("/tmp/nonexistent")`（目录缺失）— 三种 case 必须返回空 DataFrame + WARNING 日志、退出码 0。
7. 对照 NFR-002：检查模块 docstring 双语、类型标注完整、`logger = logging.getLogger(__name__)`、段落分隔符存在。

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python -c "from ellectric.pipeline.shanxi_loader import ShanxiBaseLoader; from ellectric.pipeline.data_loader import DataLoader; assert issubclass(ShanxiBaseLoader, DataLoader); print('OK')"` | 退出码 0，输出 `OK`；ShanxiBaseLoader 是 DataLoader 的子类 |
| AC-02 | `python -c "from ellectric.pipeline.shanxi_loader import ShanxiBaseLoader; ShanxiBaseLoader('spot_da')"` | 抛 `TypeError: Can't instantiate abstract class ShanxiBaseLoader with abstract method _standardize`（@abstractmethod 强制子类实现） |
| AC-03 | 临时子类实例化：构造 `Dummy(ShanxiBaseLoader)` 实现 `_standardize` 返回空 DF；`d = Dummy("spot_da"); df = d.load_data(start="2010-01", end="2010-12")` | `len(df) == 0`，但 `set(df.columns) >= {"timestamp", "load_mw", "province", "source", "granularity"}`；stderr/log 含 `WARNING` "未匹配到任何数据" |
| AC-04 | `python -c "from ellectric.pipeline.shanxi_loader import ShanxiBaseLoader; import inspect; src = inspect.getsource(ShanxiBaseLoader); assert '_make_timestamp' in src and '_records_from_json' in src and '_filter_files_by_month' in src"` | 退出码 0；基类含所有约定的辅助方法 |
| AC-05 | 单测 `_make_timestamp`：实例化 dummy 子类，调 `_make_timestamp("2024-05-01", "24:00")` | 返回 `pd.Timestamp("2024-05-02 00:00:00", tz="UTC")`；调 `_make_timestamp("2024-05-01", "08:15")` 返回 `pd.Timestamp("2024-05-01 08:15:00", tz="UTC")` |
| AC-06 | `wc -l ellectric/pipeline/shanxi_loader.py` | ≥ 120 行 且 ≤ 350 行（包含文档+实现，符合 D-005@v1 拆分目的） |
| AC-07 | `grep -E "^logger = logging.getLogger" ellectric/pipeline/shanxi_loader.py` & `grep -E "@abstractmethod" ellectric/pipeline/shanxi_loader.py` | 两条命令均匹配到至少 1 行；满足 NFR-002 模块 logger 与 D-001@v1 抽象方法约束 |
| AC-08 | `python -c "import ast, sys; tree = ast.parse(open('ellectric/pipeline/shanxi_loader.py').read()); third_party = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}; assert third_party <= {'abc','json','logging','re','pathlib','typing','pandas','ellectric.pipeline.data_loader','__future__'}, third_party"` | 退出码 0；NFR-003 — 无新依赖 |
| AC-09 | 单测 `_filter_files_by_month`：在 tmp 目录构造 `spot_da_2024-01.json`、`spot_da_2024-06.json`、`spot_da_2025-03.json`、`spot_da_invalid.json`、`spot_da_2024-02_dict.json` 五个文件；调 `_filter_files_by_month(files, "2024-02", "2024-12")` | 返回 1 项 `(spot_da_2024-06.json, "2024-06")`；`_dict.json` 与无 YYYY-MM 的文件被排除 |
