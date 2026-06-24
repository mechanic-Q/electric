"""
山西电力交易数据抓取器 — ShanxiFetcher
========================================

通过 playwright 驱动 headless chromium，使用预先获取的 cookie/x-ticket 访问
山西零售商城 (pmos.sx.sgcc.com.cn/pxf-phbsx-shop) 的公开数据接口。

支持 18 个 marketInfo API 的批量抓取，结果双输出：
1. snapshots/<YYYY-MM-DD>/<source>_<month>.json — 历史快照（永不覆盖）
2. <source>_<month>.json — latest 视图（供 ShanxiSpotDaLoader 等加载）

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 模块化：核心类可被 LLM tool / FastAPI handler 直接 import
- 安全性：cookie 默认从环境变量 SHANXI_COOKIE 读，不写死
- 可追溯：双输出确保历史快照不被覆盖

用法 (Usage)
~~~~~~~~~~~~
    fetcher = ShanxiFetcher()  # 自动从 env 读 cookie
    result = fetcher.fetch_one("spot_da", "2026-06")
    # → {"status": 200, "rows": 96, "snapshot_path": str, "latest_path": str}

    # 批量抓取
    results = fetcher.fetch_range(
        sources=["spot_da", "spot_rt"],
        months=["2026-01", "2026-02"],
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════
# 常量配置
# ═══════════════════════════════════════════════════════


BASE_URL = "https://pmos.sx.sgcc.com.cn/px-shop/marketInfo"
SHOP_ROOT = "https://pmos.sx.sgcc.com.cn/pxf-phbsx-shop/"

# 山西零售商城 18 个 marketInfo API
ALL_APIS: dict[str, str] = {
    "spot_da":           "querySpotMarketClearing",
    "spot_rt":           "queryRealTimeSpotMarketClearing",
    "month_deal":        "queryMonthDeal",
    "user_transaction":  "queryUserTransaction",
    "month_settle":      "queryUserMonthSettlementPrice",
    "month_settle1":     "queryUserMonthSettlementPrice1",
    "year_trade_fit":    "queryYearTradeFittingPrice",
    "price_trend":       "queryPriceTrend",
    "time_div_trend":    "queryTimeDivisionPriceTrend",
    "no_time_trend":     "queryNoTimeDivisionPriceTrend",
    "month_market":      "queryMonthTradeMarketList",
    "market_list":       "queryMarketList",
    "market_users":      "queryMarketUserList",
    "public_info":       "queryPublicInfoClient",
    "dynamic":           "queryMarketDynamics",
    "policy":            "queryPolicyDocument",
    "retail_settle":     "queryRetailSettlement",
    "retail_prob":       "queryRetailProblemInfo",
}


# ═══════════════════════════════════════════════════════
# ShanxiFetcher 主类
# ═══════════════════════════════════════════════════════


class ShanxiFetcher:
    """山西电力交易数据抓取器。

    Args:
        cookie: 完整 cookie 字符串或 X-Ticket token。默认从环境变量 SHANXI_COOKIE 读。
        data_dir: 数据根目录（默认 ellectric/data/raw/shanxi）。
        rate_limit_ms: API 调用间隔毫秒数（默认 200，防触发反爬）。

    Raises:
        ValueError: cookie 缺失（既未传也未在 env 中找到）
    """

    def __init__(
        self,
        cookie: str | None = None,
        data_dir: str = "ellectric/data/raw/shanxi",
        rate_limit_ms: int = 200,
        chromium_path: str = "/usr/bin/chromium-browser",
    ) -> None:
        self.cookie = cookie or os.environ.get("SHANXI_COOKIE", "")
        if not self.cookie:
            raise ValueError(
                "cookie 缺失：请传入 cookie 参数，或设置环境变量 SHANXI_COOKIE。"
                "Cookie 获取方式：浏览器登录 https://pmos.sx.sgcc.com.cn → Cookie-Editor 导出 X-Ticket 值。"
            )
        self.data_dir = Path(data_dir)
        self.snapshots_dir = self.data_dir / "snapshots"
        self.rate_limit_ms = rate_limit_ms
        self.chromium_path = chromium_path

        # 自动创建目录
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    # ════════════════════════════════════════════════════════
    # 公开 API
    # ════════════════════════════════════════════════════════

    def fetch_one(
        self,
        source: str,
        month: str,
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        """抓取一个 API 一个月的数据。

        Args:
            source: API 名称（必须在 ALL_APIS 中，如 "spot_da"）
            month: YYYY-MM 格式月份
            snapshot_id: 快照标识（默认今天日期 YYYY-MM-DD）

        Returns:
            {
                "status": int,        # HTTP 状态码
                "rows": int,          # data 中记录数（list 长度，0 表示空）
                "snapshot_path": str, # 快照文件路径
                "latest_path": str,   # latest 视图文件路径
                "msg": str,           # API 返回的 msg 字段
            }

        Raises:
            ValueError: source 不在 ALL_APIS 中
        """
        if source not in ALL_APIS:
            raise ValueError(
                f"未知 source: {source}。可选: {list(ALL_APIS.keys())}"
            )
        snap_id = snapshot_id or datetime.now().strftime("%Y-%m-%d")
        return asyncio.run(self._fetch_one_async(source, month, snap_id))

    def fetch_range(
        self,
        sources: list[str] | None = None,
        months: list[str] | None = None,
        snapshot_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """批量抓取。

        Args:
            sources: API 名称列表（None 表示全 18 个）
            months: 月份列表（None 表示默认范围 2018-01 至当月）
            snapshot_id: 快照标识（默认今天日期）

        Returns:
            {<source>_<month>: <fetch_one result>}
        """
        if sources is None:
            sources = list(ALL_APIS.keys())
        if months is None:
            months = self._default_months()
        snap_id = snapshot_id or datetime.now().strftime("%Y-%m-%d")
        return asyncio.run(self._fetch_range_async(sources, months, snap_id))

    # ════════════════════════════════════════════════════════
    # 内部异步实现
    # ════════════════════════════════════════════════════════

    async def _fetch_one_async(
        self, source: str, month: str, snap_id: str
    ) -> dict[str, Any]:
        """异步抓取单个 API 单月数据。"""
        from playwright.async_api import async_playwright

        path = ALL_APIS[source]
        body = json.dumps({"startDate": month, "_t": int(datetime.now().timestamp() * 1000)})
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "x-ticket": self.cookie,
            "clienttag": "OUTNET_BROWSE",
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path=self.chromium_path,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context()
            page = await ctx.new_page()

            try:
                await page.goto(SHOP_ROOT, timeout=30000)
                await page.wait_for_timeout(1000)

                js = f"""async () => {{
                    const r = await fetch("{BASE_URL}/{path}", {{
                        method: "POST",
                        headers: {json.dumps(headers)},
                        body: {json.dumps(body)},
                    }});
                    return {{ status: r.status, text: await r.text() }};
                }}"""
                resp = await page.evaluate(js)
            finally:
                await browser.close()

        # 解析响应
        rows = 0
        msg = ""
        data_to_save = None
        try:
            payload = json.loads(resp["text"])
            msg = payload.get("msg", "")
            data = payload.get("data") or []
            if isinstance(data, list):
                rows = len(data)
            data_to_save = payload
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("解析失败 source=%s month=%s err=%s", source, month, e)
            data_to_save = {"raw_text": resp["text"][:5000]}

        # 双输出：snapshot + latest
        snapshot_path = self._save_snapshot(source, month, snap_id, data_to_save)
        latest_path = self._save_latest(source, month, data_to_save)

        return {
            "status": resp["status"],
            "rows": rows,
            "snapshot_path": str(snapshot_path),
            "latest_path": str(latest_path),
            "msg": msg,
        }

    async def _fetch_range_async(
        self,
        sources: list[str],
        months: list[str],
        snap_id: str,
    ) -> dict[str, dict[str, Any]]:
        """异步批量抓取。"""
        from playwright.async_api import async_playwright

        results: dict[str, dict[str, Any]] = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path=self.chromium_path,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context()
            page = await ctx.new_page()
            try:
                await page.goto(SHOP_ROOT, timeout=30000)
                await page.wait_for_timeout(1000)

                for source in sources:
                    if source not in ALL_APIS:
                        logger.warning("skip 未知 source: %s", source)
                        continue
                    api_path = ALL_APIS[source]
                    for month in months:
                        key = f"{source}_{month}"
                        try:
                            body = json.dumps({"startDate": month, "_t": int(datetime.now().timestamp() * 1000)})
                            headers = {
                                "Content-Type": "application/json;charset=UTF-8",
                                "x-ticket": self.cookie,
                                "clienttag": "OUTNET_BROWSE",
                            }
                            js = f"""async () => {{
                                const r = await fetch("{BASE_URL}/{api_path}", {{
                                    method: "POST",
                                    headers: {json.dumps(headers)},
                                    body: {json.dumps(body)},
                                }});
                                return {{ status: r.status, text: await r.text() }};
                            }}"""
                            resp = await page.evaluate(js)

                            rows, msg, data_to_save = 0, "", None
                            try:
                                payload = json.loads(resp["text"])
                                msg = payload.get("msg", "")
                                data = payload.get("data") or []
                                if isinstance(data, list):
                                    rows = len(data)
                                data_to_save = payload
                            except json.JSONDecodeError:
                                data_to_save = {"raw_text": resp["text"][:5000]}

                            snap = self._save_snapshot(source, month, snap_id, data_to_save)
                            latest = self._save_latest(source, month, data_to_save)

                            results[key] = {
                                "status": resp["status"],
                                "rows": rows,
                                "snapshot_path": str(snap),
                                "latest_path": str(latest),
                                "msg": msg,
                            }
                            logger.info("[%s] %s rows=%d", source, month, rows)
                        except Exception as e:
                            logger.warning("fetch 失败 %s/%s: %s", source, month, e)
                            results[key] = {"error": str(e)}

                        await asyncio.sleep(self.rate_limit_ms / 1000.0)
            finally:
                await browser.close()

        return results

    # ════════════════════════════════════════════════════════
    # 文件写入
    # ════════════════════════════════════════════════════════

    def _save_snapshot(
        self,
        source: str,
        month: str,
        snap_id: str,
        data: dict[str, Any],
    ) -> Path:
        """保存快照到 snapshots/<snap_id>/<source>_<month>.json。永不覆盖：
        若同名已存在，追加 .N 后缀。"""
        snap_dir = self.snapshots_dir / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)
        target = snap_dir / f"{source}_{month}.json"
        if target.exists():
            i = 1
            while (snap_dir / f"{source}_{month}.{i}.json").exists():
                i += 1
            target = snap_dir / f"{source}_{month}.{i}.json"
        target.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        return target

    def _save_latest(
        self,
        source: str,
        month: str,
        data: dict[str, Any],
    ) -> Path:
        """更新 latest 视图：data/raw/shanxi/<source>_<month>.json。"""
        target = self.data_dir / f"{source}_{month}.json"
        target.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        return target

    # ────────────────────────────────────────────────────────
    # 工具方法
    # ────────────────────────────────────────────────────────

    def _default_months(self) -> list[str]:
        """生成默认月份列表 2018-01 至当月。"""
        months: list[str] = []
        now = datetime.now()
        for year in range(2018, now.year + 1):
            for m in range(1, 13):
                if year == now.year and m > now.month:
                    break
                months.append(f"{year}-{m:02d}")
        return months
