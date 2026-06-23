---
id: task-04
title: 实现 ShanxiSpotRtLoader 子类
priority: P0
depends_on: [task-02]
blocks: []
requirement_ids: [FR-005]
decision_ids: [D-003@v1]
allowed_paths:
  - ellectric/pipeline/shanxi_loader.py
author: lmr
created_at: 2026-06-23T15:10:00+08:00
---

# task-04: 实现 ShanxiSpotRtLoader 子类

## 修改文件 (必填)
- `ellectric/pipeline/shanxi_loader.py`（同 task-02 文件 — 在已有的 `ShanxiBaseLoader` 和 `ShanxiSpotDaLoader` 之后追加）

## 覆盖来源
- **Requirements**: FR-005 — ShanxiSpotRtLoader 子类，返回 rt_energy_demand/rt_energy_supply 及等效 load_mw
- **Decisions**: D-003@v1 — rqRecord→rt_energy_demand, ssRecord→rt_energy_supply, load_mw=rt_energy_demand

## 实现要求

### 类定义

```python
class ShanxiSpotRtLoader(ShanxiBaseLoader):
    """
    山西实时现货(spot_rt)数据加载器。

    从 data/raw/shanxi/spot_rt_YYYY-MM.json 文件中加载 15min 级实时电量数据。
    原始字段 rqRecord/ssRecord 映射为语义化 rt_energy_demand/rt_energy_supply。

    字段推断说明 (Field Inference Disclaimer)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - rqRecord → rt_energy_demand：推断为实时需求量/日前申报量，万 MWh，置信度：推断
    - ssRecord → rt_energy_supply：推断为实时供应量/出清量，万 MWh，置信度：推断
    - 精确业务含义未通过官方文档确认，下游使用方应自行交叉验证。
    """

    _metadata_source = "shanxi-spot-rt"

    def __init__(self, data_dir: str | None = None) -> None:
        super().__init__(data_prefix="spot_rt", data_dir=data_dir)

    def _standardize(self, records: list[dict], year_month: str) -> pd.DataFrame:
        """
        将原始 JSON records 转为标准化 DataFrame。

        流程:
        1. 逐 record 解析 dataTime (HH:MM)、rqRecord、ssRecord
        2. 用 super()._make_timestamp(date_str=year_month, time_str=dataTime) 生成 UTC 时间戳
        3. 构建标准化列：timestamp / rt_energy_demand / rt_energy_supply / load_mw / province / source / granularity

        Args:
            records: 从 JSON 文件 "data" 字段读到的 list[dict]，每个 dict 含 dataTime/rqRecord/ssRecord
            year_month: 格式 "YYYY-MM"，从文件名提取

        Returns:
            pd.DataFrame，列:
            - timestamp: datetime64[ns, UTC] — dataTime 转 UTC 时间戳
            - rt_energy_demand: float64 — rqRecord 值（万 MWh）
            - rt_energy_supply: float64 — ssRecord 值（万 MWh）
            - load_mw: float64 — 同 rt_energy_demand（作为等效负荷，注意量纲为万 MWh 非 MW）
            - province: str — "shanxi"
            - source: str — "pxf-phbsx-shop"
            - granularity: str — "15min"
        """
```

### 字段映射表

| 原始 JSON 字段 | DataFrame 列名 | 类型 | 映射方式 | 置信度 |
|---|---|---|---|---|
| `dataTime` (H:MM 字符串, 如 "00:15","24:00") | `timestamp` | datetime64[ns, UTC] | `_make_timestamp(year_month, dataTime)` + UTC 化 | 确定 |
| `rqRecord` (数值) | `rt_energy_demand` | float64 | 直接复制 | 推断 |
| `ssRecord` (数值) | `rt_energy_supply` | float64 | 直接复制 | 推断 |
| (衍生) | `load_mw` | float64 | 复制 `rt_energy_demand` | 推断 |
| (注入) | `province` | str | 常量 `"shanxi"` | — |
| (注入) | `source` | str | 常量 `"pxf-phbsx-shop"` | — |
| (注入) | `granularity` | str | 常量 `"15min"` | — |

### 数据事实

- 源文件：`data/raw/shanxi/spot_rt_YYYY-MM.json`，每文件 96 条 records（15min 间隔，00:15~24:00）
- 时间范围：2022-04 ~ 2026-05（有效数据），2022-04 之前文件存在但 data=[]（空数组）
- 总行数估算：50 月 × 96 点 = 4800 行
- 单位说明：rqRecord/ssRecord 原始值为万 MWh（前端渲染时 `/1e5` 转亿千瓦时）；`load_mw` 列直接复制 `rt_energy_demand`，量纲一致

## 边界处理（至少 5 条）

1. **dataTime="24:00" 跨日边界**：调用 base class `_make_timestamp` 将 "24:00" 解析为 `当日日期 + 24:00` → 自动转为次日 00:00（`pd.Timestamp` 行为），非 "23:59" 近似
2. **空 records 列表**：`_standardize` 接收到空 `[]` 时，返回包含标准列名和类型的空 DataFrame（`.columns` 含全部 7 列，`.dtypes` 正确赋值），而不是抛 `IndexError` 或返回空 dict
3. **缺失 rqRecord/ssRecord 键**：records 中某对象缺少 `rqRecord` 或 `ssRecord` 键（或值为 `None`），该 record 对应行的字段设为 `float("nan")`，不中断整体处理；日志记录 `logger.warning(f"spot_rt {year_month}: record at index {i} missing rqRecord/ssRecord")`
4. **非 96 条的异常月度文件**：某些月份可能只有少于 96 条 records（如 API 部分数据缺失），不要求严格等于 96，按实际数量返回；不抛 AssertionError
5. **JSON 解析失败/文件损坏**：`load_data` 基类内已捕获，子类 `_standardize` 不重复处理；`_standardize` 自身只假设 `records` 是 `list[dict]` 格式正确的数据
6. **_standardize 不修改传入 records**：不 `.pop()`、`.remove()` 或原地修改传入的 `records` 列表，创建新的 list/dict/DataFrame（避免副作用）

## 非目标（本任务不做的事）

- ❌ 不修改 `ShanxiBaseLoader.load_data()` 基类逻辑（文件扫描、月份筛选、UTC 化等全由基类完成）
- ❌ 不对 `rt_energy_demand`/`rt_energy_supply` 做单位换算（保持原始万 MWh，不做 MW 转义，下游使用时注意量纲）
- ❌ 不聚合为小时级（留在后续 `time-resolution-param` 变更）
- ❌ 不实现 SpotDaLoader/MonthSettleLoader（task-03 / task-05 独立完成）
- ❌ 不接入 ASK/CLI/LLM/FastAPI

## 参考

- 参考 `ShanxiSpotDaLoader` 的 `_standardize` 实现模式（task-03）— 两个子类结构完全对称，区别仅在于字段映射和 `data_prefix`/`_metadata_source`
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` 编码规范（中英双语 docstring、`logger = logging.getLogger(__name__)`、`_` 前缀内部方法、类型标注）
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` III. 字段映射（spot_rt 表）/ IV. 工厂扩展

## TDD 步骤（代码类任务，文档类任务跳过）

1. **写最小 import / 类定义**：在 `shanxi_loader.py` 中 `ShanxiSpotDaLoader` 之后追加 `ShanxiSpotRtLoader` 类骨架，确认 `python -c "from ellectric.pipeline.shanxi_loader import ShanxiSpotRtLoader; print('OK')"` 通过
2. **实现 `_standardize` 最小 happy path**：用模拟的 3 条 records（含 "24:00" 边界）调用 `_standardize`，确认输出 DataFrame 列名/类型/行数正确
3. **调用 verify 脚本看输出**：在 verify 脚本（task-07）中添加 `shanxi_spot_rt` 分支调用，打印行数、列名、时间范围，确认 ≈ 4800 行
4. **完善边界处理**：逐条实现空 records、缺失键、非 96 条、原地不修改等处理；单步测试
5. **全部 source 验证通过**：`python ellectric/scripts/verify_shanxi_loader.py` 退出码 0，所有 3 个 source 输出正常

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python -c "from ellectric.pipeline.shanxi_loader import ShanxiSpotRtLoader; loader = ShanxiSpotRtLoader(); df = loader.load_data(start='2022-04', end='2026-05'); print(len(df), list(df.columns))"` | 行数 ≈ 4800（≥ 4600），列含 `timestamp`/`rt_energy_demand`/`rt_energy_supply`/`load_mw`/`province`/`source`/`granularity` |
| AC-02 | 对返回的 df，验证 `df['load_mw'].equals(df['rt_energy_demand'])` 为 True，且 `province`/`source`/`granularity` 列值分别为 `"shanxi"`/`"pxf-phbsx-shop"`/`"15min"` | 全部断言通过 |
| AC-03 | `df['timestamp'].dt.tz` 检查 | 时区为 `UTC`（`datetime.timezone.utc`），行 0 的 `timestamp` 包含年月日（来自文件名 YYYY-MM 和 dataTime HH:MM 合成） |
| AC-04 | `loader.load_data(start='2020-01', end='2020-03')`（有效范围外） | 返回列结构完整的空 DataFrame（len=0）+ `WARNING` 级别日志，无异常抛出 |
| AC-05 | 验证 `_standardize` 不修改传入的 `records` 列表（identity check: `id(orig) == id(after)`） | 传入列表对象引用不变，元素未被 `.pop()` 或原地修改 |