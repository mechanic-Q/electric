"""
数据抓取模块 — Electric Data Fetch Module
==========================================

为 Electric 项目提供可被 import 的程序化数据抓取接口。

模块:
- WeatherFetcher: Open-Meteo 气象数据抓取（免费，无 API key）
"""

from ellectric.fetch.weather import WeatherFetcher

__all__ = ["WeatherFetcher"]
