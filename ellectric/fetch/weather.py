"""
Open-Meteo 气象数据抓取器 — WeatherFetcher
============================================

通过 Open-Meteo Historical Weather API（免费、无 API key）抓取山东核心城市
历史气象数据，与山东 15min 电力数据对齐。

数据源: https://open-meteo.com/
城市: 济南 (36.65°N, 117.00°E) / 青岛 (36.07°N, 120.38°E)
变量: 气温、地表辐照度、风速、降水、湿度、云量

设计理念 (Design Philosophy)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- 纯标准库：urllib + json，不引入新依赖
- 小时级气象 × 山东 3 城 → 前向填充到 15min 对齐
- 结果 DataFrame → 下游可直接 merge 到 ShandongDataLoader 输出

用法 (Usage)
~~~~~~~~~~~~
    from ellectric.fetch.weather import WeatherFetcher
    fetcher = WeatherFetcher()
    df = fetcher.fetch_historical("2024-01", "2024-06")
    print(df.shape)  # (~175天 × 24h, 6列/城 × 2城 + 1 timestamp)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib import request, error

import pandas as pd

logger = logging.getLogger(__name__)

# ── 城市坐标 ──

SHANDONG_CITIES = {
    "jinan":   (36.65, 117.00),
    "qingdao": (36.07, 120.38),
}

# Open-Meteo API 端点
_API_BASE = "https://archive-api.open-meteo.com/v1/archive"

# 默认气象变量
_DEFAULT_VARIABLES = [
    "temperature_2m",
    "shortwave_radiation_instant",  # GHI (W/m²)
    "wind_speed_10m",
    "precipitation",
    "relative_humidity_2m",
    "cloud_cover",
]

# ── 变量名映射（API → 友好列名）──

_VARIABLE_MAP = {
    "temperature_2m": "temp_{city}",
    "shortwave_radiation_instant": "ghi_{city}",
    "wind_speed_10m": "wind_speed_{city}",
    "precipitation": "precip_{city}",
    "relative_humidity_2m": "humidity_{city}",
    "cloud_cover": "cloud_{city}",
}


class WeatherFetcher:
    """Open-Meteo 免费历史气象抓取器。

    无需 API key，单次请求覆盖一个时间范围。

    Attributes:
        cities: 城市 dict {english_name: (lat, lon)}
        variables: 抓取的气象变量列表
    """

    def __init__(
        self,
        cities: dict | None = None,
        variables: list[str] | None = None,
    ) -> None:
        self.cities = cities or SHANDONG_CITIES
        self.variables = variables or _DEFAULT_VARIABLES

    # ── 公共接口 ──

    def fetch_historical(
        self,
        start: str = "2024-01-01",
        end: str = "2026-01-14",
    ) -> pd.DataFrame:
        """抓取历史气象数据，返回 DataFrame。

        Args:
            start: 起始日期 (YYYY-MM-DD)
            end: 结束日期

        Returns:
            DataFrame 索引为 timestamp (UTC, 小时级)，列如:
            temp_jinan, ghi_jinan, wind_speed_jinan, ...
            temp_qingdao, ghi_qingdao, ...
        """
        dfs = {}
        for city_eng, (lat, lon) in self.cities.items():
            data = self._fetch_city(lat, lon, start, end, city_eng)
            dfs[city_eng] = data
        weather = self._merge_cities(dfs)
        logger.info(
            "气象数据加载完成: %s ~ %s, %d 行 x %d 列",
            str(weather.index.min()), str(weather.index.max()),
            len(weather), len(weather.columns),
        )
        return weather

    # ── 内部 ──

    def _fetch_city(
        self, lat: float, lon: float,
        start: str, end: str, city_eng: str,
    ) -> pd.DataFrame:
        """抓取单个城市气象数据。"""
        params = (
            f"latitude={lat}&longitude={lon}"
            f"&start_date={start}&end_date={end}"
            f"&hourly={','.join(self.variables)}"
            "&timezone=Asia/Shanghai"
        )
        url = f"{_API_BASE}?{params}"
        logger.debug("Open-Meteo request: %s", url[:120])

        try:
            with request.urlopen(url, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except (error.URLError, json.JSONDecodeError) as e:
            logger.error("Open-Meteo 请求失败 (%s): %s", city_eng, e)
            return pd.DataFrame()

        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            logger.warning("Open-Meteo 无数据: %s (%s ~ %s)", city_eng, start, end)
            return pd.DataFrame()

        df = pd.DataFrame({"timestamp": pd.to_datetime(times, utc=True)})
        for var in self.variables:
            col = _VARIABLE_MAP.get(var, var).format(city=city_eng)
            df[col] = pd.to_numeric(hourly.get(var, []), errors="coerce")

        df = df.set_index("timestamp")
        logger.debug("%s: %d rows fetched", city_eng, len(df))
        return df

    def _merge_cities(self, dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """横向合并多城市数据。"""
        merged = None
        for city, df in dfs.items():
            if df.empty:
                continue
            if merged is None:
                merged = df
            else:
                merged = merged.join(df, how="outer")
        if merged is None:
            logger.warning("所有城市气象数据为空")
            return pd.DataFrame()
        merged = merged.sort_index()
        # 前向填充少量缺失值
        merged = merged.ffill(limit=6)
        return merged

    # ── 便捷方法：与山东电力数据对齐 ──

    def align_to_15min(
        self,
        weather: pd.DataFrame,
        shandong_index: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """将小时级气象数据对齐到 15min 电力数据时间轴。

        通过 reindex + 无容差 ffill 将每小时值前向填充到全部 4 个 15min 子点
        (00:00, 00:15, 00:30, 00:45)，确保边界点不产生 NaN。

        Args:
            weather: fetch_historical() 返回的 DataFrame
            shandong_index: ShandongDataLoader.load_data() 返回的 timestamp 列

        Returns:
            与 shandong_index 对齐的 weather DataFrame
        """
        aligned = weather.reindex(shandong_index, method="ffill")
        null_pct = 100 * aligned.iloc[:, 0].isna().sum() / len(aligned)
        if null_pct > 5:
            logger.warning("气象数据对齐后 %.0f%% 为 null", null_pct)
        return aligned
