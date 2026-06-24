"""
山西/全省级电力数据抓取模块 — 三明治架构数据采集层
=====================================================

为 Electric 项目提供可被 import 的程序化数据抓取接口，配合 scripts/ 下
的 CLI 壳实现"模块 + 脚本"双模式使用。

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 模块化：核心类 `ShanxiFetcher` 可被 LLM tool / FastAPI handler 直接 import
- 脚本化：`scripts/fetch_shanxi.py` 作为薄 CLI 壳，仅做参数转发
- 版本管理：每次抓取双输出 — snapshots/<date>/ (永不覆盖) + latest 视图

用法 (Usage)
~~~~~~~~~~~~
    from ellectric.fetch.shanxi import ShanxiFetcher

    fetcher = ShanxiFetcher(cookie="...")
    result = fetcher.fetch_one(source="spot_da", month="2026-06")
    # → {"status": 200, "rows": 96, "snapshot_path": ..., "latest_path": ...}
"""

from ellectric.fetch.shanxi import ShanxiFetcher

__all__ = ["ShanxiFetcher"]
