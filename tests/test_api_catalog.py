"""Catalog API smoke tests — Wave 2.

覆盖：
- /capabilities /datasets /reports /reports/{id:path} 状态与结构。
- 路由注册顺序：catalog 路由不被 StaticFiles 捕获。
- 缺失报告返回明确 missing/error 而非 500。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from ellectric.api.server import app

    return TestClient(app)


def test_capabilities_returns_list(client):
    resp = client.get("/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data
    ids = {item["id"] for item in data}
    assert "forecast_load" in ids
    assert "reports_offline" in ids
    assert "datasets_info" in ids


def test_datasets_returns_three_sources(client):
    resp = client.get("/datasets")
    assert resp.status_code == 200
    data = resp.json()
    ids = [d["id"] for d in data]
    assert ids == ["shandong", "owid", "chinese_hourly"]


def test_reports_returns_list_and_filters(client):
    resp = client.get("/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    types = {d["report_type"] for d in data}
    assert "weather_tier4" in types

    resp2 = client.get("/reports", params={"report_type": "weather_tier4"})
    assert resp2.status_code == 200
    filtered = resp2.json()
    assert filtered
    assert all(d["report_type"] == "weather_tier4" for d in filtered)


def test_report_detail_known_id(client):
    resp = client.get("/reports/weather_tier4/validation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "weather_tier4/validation"
    assert body["status"] in ("ok", "missing", "error")


def test_report_detail_unknown_id(client):
    resp = client.get("/reports/does_not_exist/xyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "missing"


def test_report_detail_rejects_traversal(client):
    resp = client.get("/reports/..%2Fetc%2Fpasswd")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("error", "missing")


def test_legacy_routes_still_registered(client):
    """回归检查：旧 POST 路由仍存在（不校验 body 是否成功）。"""
    from ellectric.api.server import app

    routes = {r.path for r in app.routes if hasattr(r, "path")}
    for path in ("/predict", "/simulate", "/backtest", "/explain", "/recommend",
                 "/chat/stream", "/capabilities", "/datasets", "/reports",
                 "/reports/{report_id:path}"):
        assert path in routes, f"missing route: {path}"


def test_catalog_routes_registered_before_static_mount():
    """新 catalog 路由必须在 app.mount('/') 之前注册。"""
    from ellectric.api.server import app

    catalog_paths = {"/capabilities", "/datasets", "/reports"}
    static_seen = False
    catalog_after_static: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if path == "/" and route.__class__.__name__ == "Mount":
            static_seen = True
            continue
        if static_seen and path in catalog_paths:
            catalog_after_static.append(path)
    assert not catalog_after_static, catalog_after_static
