"""
Ember Climate 数据加载器 — 中国小时级/日级电力数据探索
========================================================

设计意图 (Design Intent)
~~~~~~~~~~~~~~~~~~~~~~~~
Ember Climate 提供全球各国的小时级和日级电力数据（发电量、碳排放强度等），
这是 OWID 年度数据的补充——年度数据只能做趋势分析，
小时级数据才能做负荷预测、电价预测等后续阶段的核心工作。

当前状态: **探索性模块** — Ember API 可能需要 key，
若不可用则 logger.warning 降级，不阻断管道。

数据源 (Data Source)
~~~~~~~~~~~~~~~~~~~~
Ember 提供的数据维度:
- electricity_generation: 发电量 (MW)
- carbon_intensity: 碳排放强度 (gCO2/kWh)
- 时间粒度: 小时级/日级（比 OWID 年度精细得多）

模块职责 (Module Responsibilities)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- EmberLoader: 从 Ember API 拉取中国小时级/日级电力数据
"""

import logging
from typing import Optional
from pathlib import Path

import pandas as pd
import urllib.request
import json
import io

from ellectric.pipeline.data_loader import DataLoader

logger = logging.getLogger(__name__)

# Ember API 端点（v1 无认证的公开端点）
EMBER_API_BASE = "https://api.ember-energy.org/v1"
EMBER_COUNTRY_DATA_URL = f"{EMBER_API_BASE}/country/CHN"


class EmberLoader(DataLoader):
    """
    从 Ember Climate API 拉取中国小时级电力数据。

    容错机制 (Error Handling)
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    Ember API 可能变更或需要认证。若 API 不可用:
    1. load_data() 抛 ImportError 风格的 RuntimeError，提示用户手动下载数据
    2. 调用方应 try/except 处理降级逻辑
    """

    _metadata_source = "Ember Climate"
    _metadata_version = "v1 API (exploratory)"

    def load_data(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        从 Ember API 加载中国小时级电力数据。

        Args:
            start: 开始日期 'YYYY-MM-DD'
            end:   结束日期 'YYYY-MM-DD'

        Returns:
            DataFrame with data contract {timestamp, load_mw, ...}
        """
        logger.info("正在尝试从 Ember API 拉取中国数据...")

        try:
            df = self._fetch_ember_data(start, end)
            logger.info(f"Ember 数据加载完成: {len(df)} 行")
            return df
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.warning(f"Ember API 不可用 ({e})，此模块为探索性质，请手动下载数据。")
            raise RuntimeError(
                "Ember API 当前不可用。\n"
                "此模块为探索性质——请访问 https://ember-energy.org/data "
                "手动下载中国数据，放入 data/ 目录。\n"
                f"原始错误: {e}"
            ) from e

    def _fetch_ember_data(
        self, start: Optional[str], end: Optional[str]
    ) -> pd.DataFrame:
        """从 Ember API 拉取并解析数据。"""
        params = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = EMBER_COUNTRY_DATA_URL
        if query_string:
            url = f"{url}?{query_string}"

        logger.info(f"Ember API 请求: {url}")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Ellectric/1.0",
                "Accept": "application/json",
            },
        )
        response = urllib.request.urlopen(req, timeout=30)

        data = json.loads(response.read().decode("utf-8"))
        response.close()

        # 数据解析：Ember 返回的数据结构可能变化
        # 当前尝试标准格式
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "data" in data:
            df = pd.DataFrame(data["data"])
        else:
            raise ValueError(f"无法解析 Ember API 响应格式: {type(data)}")

        if df.empty:
            raise ValueError("Ember API 返回空数据")

        # 标准化为 Data Contract
        df = _standardize_ember_columns(df)
        return df


def _standardize_ember_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    将 Ember 数据列名标准化为内部 Data Contract。

    Ember 的可能命名 → 内部标准:
    - datetime / date / timestamp → timestamp
    - generation_mw / electricity_generation → load_mw
    """
    # timestamp
    for col in ["datetime", "date", "timestamp", "local_datetime"]:
        if col in df.columns:
            df["timestamp"] = pd.to_datetime(df[col], utc=True)
            break

    # load_mw
    for col in ["generation_mw", "electricity_generation", "load_mw",
                "total_generation_mw", "demand_mw"]:
        if col in df.columns:
            df["load_mw"] = pd.to_numeric(df[col], errors="coerce")
            break

    # region
    df["region"] = "中国"
    df["source"] = "Ember"

    # 确保核心列存在
    required = {"timestamp", "load_mw"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Ember 数据缺少核心列: {missing}。可用列: {list(df.columns)}")

    return df
