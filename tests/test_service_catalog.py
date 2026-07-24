"""Catalog registry + fallback helper — Wave 2 单元测试。

覆盖：
- list_capabilities/list_datasets/list_reports 返回内容与容错。
- get_report 缺失/非法 ID 处理。
- build_forecast_fallback 只对模型缺失触发，否则返回 None。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_list_capabilities_covers_core_dimensions():
    from ellectric.service import catalog

    items = catalog.list_capabilities()
    ids = {item.id for item in items}
    expected = {
        "forecast_load",
        "forecast_price",
        "forecast_wind",
        "forecast_solar",
        "simulate_market",
        "backtest_strategy",
        "explain_shap",
        "recommend_trade",
        "reports_offline",
        "datasets_info",
    }
    assert expected.issubset(ids)
    for item in items:
        assert item.title
        assert item.description
        if item.category == "forecast":
            assert item.supports_offline_fallback is True


def test_list_datasets_returns_three_sources_and_degrades_gracefully(monkeypatch):
    from ellectric.service import catalog

    class _BrokenLoader:
        data_path = Path("nonexistent.csv")

        def get_metadata(self):
            raise RuntimeError("boom")

        def load_data(self):
            raise RuntimeError("boom")

    import ellectric.pipeline.shandong_loader as shandong_mod

    monkeypatch.setattr(shandong_mod, "ShandongDataLoader", lambda: _BrokenLoader())

    datasets = catalog.list_datasets()
    ids = [d.id for d in datasets]
    assert ids == ["shandong", "owid", "chinese_hourly"]
    shandong = next(d for d in datasets if d.id == "shandong")
    assert shandong.available is False


def test_list_reports_scans_known_report_types():
    from ellectric.service import catalog

    reports = catalog.list_reports()
    types = {r.report_type for r in reports}
    assert "weather_tier4" in types
    assert "renewable" in types
    assert "rl_evaluation" in types


def test_rl_report_catalog_uses_long_term_simulated_value_language():
    from ellectric.service import catalog

    report = next(item for item in catalog.list_reports() if item.report_type == "rl_evaluation")
    assert report.title.startswith("106 天样本外稳定性评估")
    assert "P&L" not in report.title
    assert all(not key.startswith("pnl_") for key in report.metrics)
    assert all(key.startswith("simulated_spread_value_") for key in report.metrics)


def test_list_reports_filter_by_type():
    from ellectric.service import catalog

    weather = catalog.list_reports(report_type="weather_tier4")
    assert weather
    assert all(r.report_type == "weather_tier4" for r in weather)


def test_get_report_unknown_id_returns_missing():
    from ellectric.service import catalog

    detail = catalog.get_report("does_not_exist/xyz")
    assert detail.status == "missing"
    assert detail.content is None


def test_get_report_rejects_path_traversal():
    from ellectric.service import catalog

    detail = catalog.get_report("../etc/passwd")
    assert detail.status == "error"


def test_get_report_reads_content_when_available(tmp_path, monkeypatch):
    """构造临时报告根，验证 get_report 能读取 JSON 主体。"""
    from ellectric.service import catalog

    weather_dir = tmp_path / "weather_tier4"
    weather_dir.mkdir()
    payload = {
        "status": "ok",
        "metadata": {"generated_at": "2026-07-02T00:00:00Z"},
        "experiments": {
            "baseline_tier3": {"metrics": {"mae": 3412.02}},
            "weather_tier4": {"metrics": {"mae": 2755.47}},
            "delta": {"mae_delta_pct": -19.24},
        },
        "interpretation": {"summary": "test summary"},
    }
    (weather_dir / "weather_tier4_validation.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(catalog, "_REPORTS_ROOT", tmp_path)
    monkeypatch.setattr(catalog, "_PROJECT_ROOT", tmp_path)

    reports = catalog.list_reports()
    weather = [r for r in reports if r.id == "weather_tier4/validation"]
    assert weather
    assert weather[0].status == "ok"
    assert weather[0].metrics.get("mae_delta_pct") == -19.24
    assert "mae_baseline_tier3" in weather[0].metrics
    assert "mae_weather_tier4" in weather[0].metrics
    assert "mae_delta_pct" in weather[0].metrics
    assert weather[0].metrics_meta
    assert weather[0].metrics_meta["mae_baseline_tier3"]["label"] == "Baseline Tier3 MAE"
    assert weather[0].metrics_meta["mae_baseline_tier3"]["unit"] == "MW"
    
    detail = catalog.get_report("weather_tier4/validation")
    assert detail.status == "ok"
    assert isinstance(detail.content, dict)
    assert detail.content["interpretation"]["summary"] == "test summary"
    assert detail.metrics_meta
    assert detail.metrics_meta["mae_delta_pct"]["unit"] == "%"


def test_build_forecast_fallback_returns_dict_for_model_missing():
    from ellectric.service.handlers import build_forecast_fallback

    result = build_forecast_fallback("load", FileNotFoundError("xgboost_model.joblib missing"))
    assert result is not None
    assert result["status"] == "fallback"
    assert result["source"] == "offline_report"
    assert result["fallback_reason"] == "model_missing"
    assert result["model_type"] == "load"
    assert result["report_id"]
    assert "report_status" in result
    assert "metrics_meta" in result


def test_build_forecast_fallback_returns_none_for_generic_error():
    from ellectric.service.handlers import build_forecast_fallback

    result = build_forecast_fallback("load", ValueError("invalid horizon"))
    assert result is None


def test_build_forecast_fallback_price_uses_price_comparison():
    from ellectric.service.handlers import build_forecast_fallback

    result = build_forecast_fallback("price", FileNotFoundError("lear_model.joblib missing"))
    assert result is not None
    assert result["report_id"].startswith("price_comparison/")


def test_weather_tier4_degraded_status_passthrough(monkeypatch, tmp_path):
    import json
    from ellectric.service import catalog

    weather_dir = tmp_path / "weather_tier4"
    weather_dir.mkdir()
    payload = {
        "status": "degraded",
        "metadata": {"generated_at": "2026-07-02T00:00:00Z"},
        "experiments": {
            "baseline_tier3": {"metrics": {"mae": 3412.02}},
            "weather_tier4": {"metrics": {"mae": 2755.47}},
            "delta": {"mae_delta_pct": -19.24},
        },
        "interpretation": {"summary": "Weather features unavailable"},
    }
    (weather_dir / "weather_tier4_validation.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(catalog, "_REPORTS_ROOT", tmp_path)
    monkeypatch.setattr(catalog, "_PROJECT_ROOT", tmp_path)

    reports = catalog.list_reports(report_type="weather_tier4")
    weather = [r for r in reports if r.id == "weather_tier4/validation"]
    assert weather
    assert weather[0].status == "degraded"
    assert weather[0].metrics.get("mae_baseline_tier3") == 3412.02
    assert weather[0].metrics_meta
    assert weather[0].metrics_meta["mae_baseline_tier3"]["unit"] == "MW"
