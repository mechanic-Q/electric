---
author: lmr
created_at: 2026-06-24T15:00:00+08:00
---

# 数据抓取管道 — 设计文档

## 背景

上 3 个变更（shanxi-spot-data-access / time-resolution-param / data-schema-expand）已完成数据接入和参数化。一次性手动跑 `sx_pull_all.py` 把山西数据 dump 到 `data/raw/shanxi/`，但缺乏可重复抓取的能力：

- 每月数据更新需要手动跑脚本
- 没有快照管理，重抓覆盖旧数据
- 未集成到现有三明治架构（API/CLI/LLM）

## 设计目标

1. 新建 `ellectric/fetch/shanxi.py` — `ShanxiFetcher` 类（核心抓取模块）
2. 新建 `ellectric/scripts/fetch_shanxi.py` — CLI 薄壳
3. 抓取结果归档到 `data/raw/shanxi/snapshots/YYYY-MM-DD/` 保留历史快照
4. 同时更新 `data/raw/shanxi/<source>_<month>.json`（latest 视图，供 loader 加载）
5. 复用现有 cookie 配置和 API 列表

## 非目标

- ❌ 不做调度（cron/airflow）
- ❌ 不接入 FastAPI endpoint（留给后续变更）
- ❌ 不接入 LLM tool
- ❌ 不抓广东等其他省份
- ❌ 不引入新依赖
- ❌ 不做完整 ETL 管道（清洗/转 Parquet 等已在 loader 处理）
- ❌ 不修改 ShanxiSpotDaLoader 等已有 loader 行为

## 决策

### D-001@v1 — 模块 + 脚本双模式 (方案 C)

**决策**：核心逻辑在 `ellectric/fetch/shanxi.py` 模块，scripts 是薄 CLI 壳

**备选**：
- A：仅 Typer CLI 子命令（被拒：复杂度高且未来网站不能 import）
- B：仅独立脚本（被拒：LLM/API 无法直接 import）

**理由**：满足三明治架构 — 网站/LLM 可 `from ellectric.fetch.shanxi import ShanxiFetcher` 直接 import。

### D-002@v1 — Snapshots 归档策略

**决策**：每次抓取产出两份：
1. `data/raw/shanxi/snapshots/YYYY-MM-DD/<source>_<month>.json` — 历史快照
2. `data/raw/shanxi/<source>_<month>.json` — latest 视图（供 loader 加载）

**理由**：快照可追溯，latest 视图保持现有 loader 不变。

### D-003@v1 — Cookie 配置外部化

**决策**：cookie 从环境变量 `SHANXI_COOKIE` 读，或 `ShanxiFetcher(cookie=...)` 显式传入。

**理由**：cookie 是私密凭证，不能写死在代码里。

## 总体方案

### 文件清单

| 操作 | 路径 | 说明 |
|---|---|---|
| 新增 | `ellectric/fetch/__init__.py` | 模块入口 |
| 新增 | `ellectric/fetch/shanxi.py` | `ShanxiFetcher` 类 (~250 行) |
| 新增 | `ellectric/scripts/fetch_shanxi.py` | CLI 壳 (~60 行) |
| 新增 | `ellectric/scripts/verify_fetch_shanxi.py` | 验证脚本 |
| 修改 | 无 | 不动现有 loader/data_loader/config 等 |

### 接口设计

```python
class ShanxiFetcher:
    """山西现货数据抓取器。"""

    BASE_URL = "https://pmos.sx.sgcc.com.cn/px-shop/marketInfo"
    ALL_APIS = {
        "spot_da": "querySpotMarketClearing",
        "spot_rt": "queryRealTimeSpotMarketClearing",
        # ... 18 个 API
    }

    def __init__(
        self,
        cookie: str | None = None,
        data_dir: str = "ellectric/data/raw/shanxi",
    ): ...

    def fetch_one(
        self, source: str, month: str
    ) -> dict:
        """抓取一个 API 一个月数据。
        Returns:
            {"status": int, "rows": int, "snapshot_path": str, "latest_path": str}
        """
        ...

    def fetch_range(
        self,
        sources: list[str] | None = None,
        months: list[str] | None = None,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        """批量抓取。
        sources=None → 抓全部 18 个 API
        months=None → 抓默认范围（2018-01 ~ 当月）
        snapshot_id=None → 用当天日期 YYYY-MM-DD
        """
        ...
```

### Snapshot 目录结构

```text
ellectric/data/raw/shanxi/
├── spot_da_2026-05.json              ← latest（loader 读取）
├── spot_da_2026-06.json
├── ... 其他 latest 文件
└── snapshots/
    ├── 2026-06-24/                    ← 第一次抓取
    │   ├── spot_da_2026-05.json
    │   ├── spot_da_2026-06.json
    │   └── ...
    └── 2026-07-15/                    ← 后续抓取
        └── ...
```

### CLI 壳设计

```bash
# 抓全部
python ellectric/scripts/fetch_shanxi.py --all

# 抓指定 source
python ellectric/scripts/fetch_shanxi.py --source spot_da --month 2026-06

# 抓月份范围
python ellectric/scripts/fetch_shanxi.py --range 2026-01:2026-06
```

### 兼容策略

- ShanxiSpotDaLoader / SpotRtLoader / MonthSettleLoader 等 8 个 loader 读取 latest 视图（默认 data_dir），行为不变
- snapshots 目录只读，不会被现有 loader 加载
- 现有 `_full_summary.json` 不变，仍由抓取脚本更新

### 验收标准

1. `from ellectric.fetch.shanxi import ShanxiFetcher` 成功
2. `ShanxiFetcher(cookie=...).fetch_one("spot_da", "2026-06")` 返回 dict 含 rows
3. snapshot 目录 `snapshots/<today>/` 有新文件
4. latest 视图同步更新
5. 现有 `verify_shanxi_loader.py` 37/37 仍通过
6. 不引入新依赖（requests 已在 cookie 模块用）

## 风险登记

| ID | 风险 | 等级 | 应对 |
|---|---|---|---|
| R-01 | cookie 过期需手工更新 | P1 | 文档明示在 README，加 `--cookie-from-env` |
| R-02 | API 限速触发反爬 | P1 | 默认 200ms 间隔，可配置 |
| R-03 | 雪山旧数据被新抓取覆盖 | P0 | snapshots 永不覆盖，latest 可被覆盖（设计） |
| R-04 | Cookie 在错误处嵌入代码 | P0 | 默认从环境变量读 |

## 自审

- design 内部自洽：5 个验收标准都可量化
- 与现有 loader 兼容：latest 视图为默认 data_dir
- snapshots 设计满足"留下痕迹"原则
- 无运行时生命周期 — 本变更纯函数式 fetch + 文件写入
