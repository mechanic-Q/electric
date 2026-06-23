---
id: task-07
title: 新增 ellectric/scripts/verify_shanxi_loader.py 验证脚本
priority: P0
depends_on: [task-06]
blocks: []
requirement_ids: [FR-009, NFR-001]
decision_ids: [D-001@v1, D-006@v1]
allowed_paths:
  - ellectric/scripts/verify_shanxi_loader.py
author: lmr
created_at: 2026-06-23T15:10:00+08:00
---

# task-07: 新增 ellectric/scripts/verify_shanxi_loader.py 验证脚本

## 修改文件 (必填)
- ellectric/scripts/verify_shanxi_loader.py (新增)

## 覆盖来源
- Requirements: FR-009（优雅降级）, NFR-001（性能 ≤ 5s/次）
- Decisions: D-001@v1（三子类继承架构）, D-006@v1（仅 3 个核心 API 接入）

## 实现要求

脚本是 task-02~task-06 落地后的端到端冒烟测试. 工作流程:

1. **依次调用** `create_loader("shanxi_spot_da")`/`create_loader("shanxi_spot_rt")`/`create_loader("shanxi_month_settle")`, 各自调 `load_data()`.
2. **对每个 source 打印**: 行数/列名列表/`timestamp` 的 `min`/`max`/`get_metadata()` 字典/`load_mw` 列前 3 个值（用 `head(3).tolist()`）.
3. **验证基础列存在**: 每个 DataFrame 必含 `timestamp` `load_mw` `province` `source` `granularity` 5 列, 缺一即 FAIL.
4. **优雅降级测试**: 调用 `loader.load_data(start="2010-01")` (远早于有效范围), 应返回空 DataFrame（`len(df) == 0`）且**有** WARNING 日志, 无异常.
5. **性能计时**: 用 `time.perf_counter()` 包裹单次 `load_data()`, 应 `< 5.0s`（NFR-001）.
6. **退出码**: 全部通过 `sys.exit(0)`, 任一 FAIL `sys.exit(1)`.

## 接口定义 (代码类任务必填)

```python
#!/usr/bin/env python3
"""
山西现货数据 Loader 验证脚本
============================

验证内容 (Verification Scope)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 3 个 source 经 create_loader 工厂返回正确子类实例
- 各 source load_data() 返回 DataFrame 含基础列
- 元数据 get_metadata() 字段完整
- 优雅降级: 超范围 start 返回空 DF + WARNING
- 性能: 单次 load_data() < 5s

Usage:
    python ellectric/scripts/verify_shanxi_loader.py
"""

import logging
import sys
import time
from typing import Any

import pandas as pd

# ── 配置 ──
REQUIRED_COLUMNS = {"timestamp", "load_mw", "province", "source", "granularity"}
SHANXI_SOURCES = [
    ("shanxi_spot_da", 4000),       # (source key, 最小预期行数)
    ("shanxi_spot_rt", 4000),
    ("shanxi_month_settle", 2000),
]
PERF_BUDGET_SEC = 5.0
DEGRADATION_START = "2010-01"   # 远早于有效范围

logger = logging.getLogger(__name__)


def verify_one_source(source: str, min_rows: int) -> dict[str, Any]:
    """
    验证单个 source 的 loader.

    Returns:
        dict with:
        - source: str
        - passed: bool
        - errors: list[str]
        - rows: int
        - columns: list[str]
        - elapsed_sec: float
        - metadata: dict
    """
    from ellectric.pipeline.data_loader import create_loader

    result: dict[str, Any] = {
        "source": source,
        "passed": False,
        "errors": [],
        "rows": 0,
        "columns": [],
        "elapsed_sec": 0.0,
        "metadata": {},
    }

    # 实例化
    try:
        loader = create_loader(source)
    except Exception as exc:
        result["errors"].append(f"create_loader 失败: {exc}")
        return result

    # 调用 + 计时
    t0 = time.perf_counter()
    try:
        df = loader.load_data()
    except Exception as exc:
        result["errors"].append(f"load_data 失败: {exc}")
        return result
    elapsed = time.perf_counter() - t0
    result["elapsed_sec"] = elapsed
    result["rows"] = len(df)
    result["columns"] = list(df.columns)

    # 列检查
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        result["errors"].append(f"缺少基础列: {missing}")

    # 行数检查
    if len(df) < min_rows:
        result["errors"].append(f"行数 {len(df)} < 期望 {min_rows}")

    # 性能检查
    if elapsed >= PERF_BUDGET_SEC:
        result["errors"].append(
            f"性能超预算: {elapsed:.2f}s >= {PERF_BUDGET_SEC}s"
        )

    # 元数据
    try:
        meta = loader.get_metadata()
        result["metadata"] = meta
        for key in ("source", "rows", "start", "end"):
            if not meta.get(key):
                result["errors"].append(f"metadata 缺少 {key}")
    except Exception as exc:
        result["errors"].append(f"get_metadata 失败: {exc}")

    # 打印摘要
    print(f"\n--- {source} ---")
    print(f"行数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    if "timestamp" in df.columns and len(df) > 0:
        print(f"时间范围: {df['timestamp'].min()} -> {df['timestamp'].max()}")
    if "load_mw" in df.columns:
        print(f"load_mw 前 3 值: {df['load_mw'].head(3).tolist()}")
    print(f"耗时: {elapsed:.2f}s")
    print(f"metadata: {result['metadata']}")

    # 优雅降级测试
    deg_ok = _verify_graceful_degradation(loader, result)
    if not deg_ok:
        result["errors"].append("优雅降级未通过")

    result["passed"] = len(result["errors"]) == 0
    return result


def _verify_graceful_degradation(loader, result: dict[str, Any]) -> bool:
    """
    调用 load_data(start=DEGRADATION_START) 应返回空 DataFrame 且记录 WARNING.

    使用 logging 捕获 + 异常拦截.
    """
    # 捕获 WARNING
    captured: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                captured.append(record)

    h = _Handler(level=logging.WARNING)
    root = logging.getLogger()
    root.addHandler(h)
    try:
        df = loader.load_data(start=DEGRADATION_START)
    except Exception as exc:
        result["errors"].append(f"优雅降级抛异常: {exc}")
        return False
    finally:
        root.removeHandler(h)

    if not isinstance(df, pd.DataFrame):
        result["errors"].append("优雅降级未返回 DataFrame")
        return False
    if len(df) != 0:
        result["errors"].append(f"优雅降级未返回空 DF, 行数 {len(df)}")
        return False
    if not captured:
        result["errors"].append("优雅降级未记录 WARNING")
        return False

    print(f"优雅降级 OK: 空 DF + {len(captured)} 条 WARNING")
    return True


def main() -> None:
    """主入口: 依次验证 3 个 source, 全部通过退出 0."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("  山西现货数据 Loader 验证报告")
    print("=" * 60)

    all_pass = True
    results: list[dict[str, Any]] = []
    for source, min_rows in SHANXI_SOURCES:
        r = verify_one_source(source, min_rows)
        results.append(r)
        if not r["passed"]:
            all_pass = False

    # 汇总
    print("\n" + "=" * 60)
    print("  汇总")
    print("=" * 60)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['source']}: rows={r['rows']}, "
              f"elapsed={r['elapsed_sec']:.2f}s")
        for err in r["errors"]:
            print(f"          ! {err}")

    print("\n状态:", "全部通过 ✓" if all_pass else "部分失败 ✗")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

## 边界处理 (至少 5 条)
1. **空 DataFrame**: `df["timestamp"].min()`/`max()` 在空 DF 上会报错, 因此打印时间范围前需 `if len(df) > 0` 守卫.
2. **缺失数据目录**: `create_loader("shanxi_spot_da")` 若 task-06 工厂未扩展会抛 `ValueError("未知数据源")`; 捕获后写入 `result["errors"]`, 不让整个脚本崩溃.
3. **兼容 task-02~task-06 接口**: 严格只调 `create_loader(source)` 和 `loader.load_data()` / `loader.get_metadata()`, 不依赖 loader 私有属性.
4. **异常不静默**: 任何子检查异常进 `result["errors"]` 并最终 `sys.exit(1)`; 不用 `except: pass`.
5. **不修改传参/全局状态**: 仅添加临时 logging.Handler 捕获 WARNING, finally 中 `removeHandler` 还原; 不改 `logging` root level 长期状态.
6. **load_mw 可能为 NaN**: `shanxi_spot_da` 和 `shanxi_month_settle` 的 `load_mw` 列为 NaN, `head(3).tolist()` 返回 `[nan, nan, nan]` 仍合法, 不当 FAIL.
7. **性能边界**: 计时只覆盖单次 `load_data()`, 不含 `create_loader` 和元数据调用; 用 `time.perf_counter()` 而非 `time.time()` 以规避时钟回拨.

## 非目标 (本任务不做的事)
- 不写 pytest 单元测试 (本项目无自动化测试套件)
- 不验证字段语义正确性 (D-002@v1/D-003@v1 标 `inferred`, 由 README 免责)
- 不测试 RL 训练/回测/API/CLI (out of scope)
- 不测试现有 OWIDChinaLoader/ChineseDataLoader/EmberLoader (FR-008 由 task-06 守护)
- 不验证 24:00 跨日边界算法细节 (task-02 自检)
- 不下载/校验原始 JSON 文件完整性 (T-001 已完成)

## 参考
- 参考 `ellectric/scripts/verify_assume.py` 的脚本结构 (check_*/main/exit code)
- 参考 `ellectric/pipeline/data_loader.py` 的 `create_loader()` 工厂签名
- 参考 `.sillyspec/docs/Ellectric/scan/CONVENTIONS.md` 编码规范 (中英双语 docstring/logger/类型标注)
- 参考 `/mnt/e/Electric/.sillyspec/changes/2026-06-22-shanxi-spot-data-access/design.md` III. 字段映射 / IV. 工厂扩展 章节
- 参考 plan.md 验收清单第 1-5 项

## TDD 步骤 (代码类任务)
1. 创建文件骨架: shebang + 模块 docstring + import + `REQUIRED_COLUMNS` 常量, `python ellectric/scripts/verify_shanxi_loader.py` 可启动
2. 写最小 `main()` 仅打印标题 + `sys.exit(0)`, 确认能跑
3. 实现 `verify_one_source()` happy path: 调用 loader + 打印行数/列名, 跑通 1 个 source
4. 添加列检查 + 行数检查 + 性能检查 + 元数据检查, 跑通 3 个 source
5. 实现 `_verify_graceful_degradation()`: 捕获 WARNING + 验空 DF
6. 添加汇总打印 + 退出码逻辑
7. 制造一次故意失败 (临时改 `min_rows=999999`) 验证 `sys.exit(1)` 路径
8. 还原后全部 PASS 即完成

## 验收标准

| # | 验证步骤 | 通过标准 |
|---|---|---|
| AC-01 | `python ellectric/scripts/verify_shanxi_loader.py` 端到端执行 | 退出码 = 0, 标准输出含 "全部通过 ✓" |
| AC-02 | 检视输出: 3 个 source 段落均含 `行数/列名/时间范围/load_mw 前 3 值/耗时/metadata` 6 项 | shanxi_spot_da 行数 ≥ 4000; shanxi_spot_rt 行数 ≥ 4000; shanxi_month_settle 行数 ≥ 2000 |
| AC-03 | 检视每段 `列名:` 行 | 必含 `timestamp` `load_mw` `province` `source` `granularity` 5 列 (顺序不限) |
| AC-04 | 检视每段 `耗时:` 行 | 单次 load_data < 5.0s (NFR-001) |
| AC-05 | 检视每段 `优雅降级 OK` 行 | 出现 3 次 (每 source 一次), 即 `len(df)==0` 且 WARNING 计数 ≥ 1 (FR-009) |
| AC-06 | 检视每段 `metadata:` 行 | dict 必含非空 `source` `rows` `start` `end` 4 键 |
| AC-07 | 故意改 `min_rows=999999` 重跑 | 退出码 = 1, 输出含 "部分失败 ✗" 及 `! 行数 X < 期望 999999` |
| AC-08 | grep 文件内容: `logger = logging.getLogger(__name__)` 与中英双语模块 docstring | 命中 ≥ 1 次 (NFR-002 风格合规) |
