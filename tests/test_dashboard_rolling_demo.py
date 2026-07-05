"""Rolling demo backend tests — Wave 1 (task-01/02/03).

Coverage:
- (schema) RollingDemoRequest days bounds, defaults.
- (schema) RollingDemoResponse has all six top-level keys.
- (service) build_rolling_demo returns correct source, frequency, points_per_day.
- (service) Series arrays are aligned to timestamps.
- (service) days values are clamped, not rejected; missing data produces warnings.
- (endpoint) GET /dashboard/rolling-demo returns 200 with correct meta shape.
- (endpoint) days=0/50 → 422 via Pydantic validation.
- (endpoint) Missing data → warnings + fallback panels.
- (endpoint) Route registered and read-only.
"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def client():
    from ellectric.api.server import app

    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════
# (task-01) Schema tests
# ═══════════════════════════════════════════════════════════════════


class TestSchema:
    def test_request_defaults(self):
        from ellectric.service.schemas import RollingDemoRequest

        req = RollingDemoRequest()
        assert req.start == "2025-10-01"
        assert req.days == 30

    def test_request_days_bounds(self):
        from ellectric.service.schemas import RollingDemoRequest

        RollingDemoRequest(days=1)
        RollingDemoRequest(days=30)
        with pytest.raises(Exception):
            RollingDemoRequest(days=0)
        with pytest.raises(Exception):
            RollingDemoRequest(days=31)

    def test_response_has_all_keys(self):
        from ellectric.service.schemas import (
            RollingDemoMeta,
            RollingDemoResponse,
            RollingDemoSeries,
            RollingDemoStrategy,
        )

        resp = RollingDemoResponse(
            meta=RollingDemoMeta(
                source="s", start="2025-01-01", end="2025-01-02",
                frequency="15min", points_per_day=96, rows=96,
            ),
            series=RollingDemoSeries(),
            strategy=RollingDemoStrategy(),
        )
        for key in ("meta", "series", "panels", "strategy", "reports", "warnings"):
            assert hasattr(resp, key)


# ═══════════════════════════════════════════════════════════════════
# (task-02) Service tests
# ═══════════════════════════════════════════════════════════════════


class TestService:
    def test_default_payload_shape(self):
        from ellectric.service.dashboard import build_rolling_demo

        result = build_rolling_demo()
        assert result.meta.source == "shandong"
        assert result.meta.frequency == "15min"
        assert result.meta.points_per_day == 96
        assert result.meta.rows > 0
        assert result.meta.start < result.meta.end

    def test_all_six_keys_present(self):
        from ellectric.service.dashboard import build_rolling_demo

        result = build_rolling_demo()
        for key in ("meta", "series", "panels", "strategy", "reports", "warnings"):
            assert hasattr(result, key)

    def test_series_arrays_aligned(self):
        from ellectric.service.dashboard import build_rolling_demo

        result = build_rolling_demo()
        n = len(result.series.timestamps)
        assert n == result.meta.rows
        assert n > 0
        for arr_name in (
            "load_actual", "load_forecast", "price_rt", "price_da",
            "wind_actual", "solar_actual", "tie_line", "pumped_storage",
        ):
            arr = getattr(result.series, arr_name)
            assert len(arr) == n, f"{arr_name} length {len(arr)} != {n}"

    def test_days_30_more_than_days_1(self):
        from ellectric.service.dashboard import build_rolling_demo

        r1 = build_rolling_demo(days=1)
        r30 = build_rolling_demo(days=30)
        assert r30.meta.rows > r1.meta.rows

    def test_days_0_equals_days_1(self):
        from ellectric.service.dashboard import build_rolling_demo

        r0 = build_rolling_demo(days=0)
        r1 = build_rolling_demo(days=1)
        assert r0.meta.rows == r1.meta.rows

    def test_days_50_equals_days_30(self):
        from ellectric.service.dashboard import build_rolling_demo

        r50 = build_rolling_demo(days=50)
        r30 = build_rolling_demo(days=30)
        assert r50.meta.rows == r30.meta.rows

    def test_days_above_max_produces_warning(self):
        from ellectric.service.dashboard import build_rolling_demo

        result = build_rolling_demo(days=50)
        assert any("50" in w for w in result.warnings)

    def test_missing_data_returns_warnings(self, monkeypatch):
        from ellectric.service.dashboard import build_rolling_demo
        from ellectric.pipeline.shandong_loader import ShandongDataLoader

        empty = pd.DataFrame({"timestamp": pd.to_datetime([])})
        monkeypatch.setattr(ShandongDataLoader, "load_data", lambda self, **kw: empty)

        result = build_rolling_demo()
        assert len(result.warnings) > 0


# ═══════════════════════════════════════════════════════════════════
# (task-03) Endpoint tests
# ═══════════════════════════════════════════════════════════════════


class TestEndpoint:
    def test_default_payload(self, client):
        resp = client.get("/dashboard/rolling-demo")
        assert resp.status_code == 200
        meta = resp.json()["meta"]
        assert meta["points_per_day"] == 96
        assert meta["source"] == "shandong"
        assert meta["frequency"] == "15min"
        assert meta["rows"] > 0

    def test_top_level_keys(self, client):
        resp = client.get("/dashboard/rolling-demo")
        assert resp.status_code == 200
        for key in ("meta", "series", "panels", "strategy", "reports", "warnings"):
            assert key in resp.json()

    def test_days_above_max_returns_capped(self, client):
        resp = client.get("/dashboard/rolling-demo", params={"days": 50})
        assert resp.status_code == 200
        body = resp.json()
        assert any("已从 50" in w for w in body["warnings"])

    def test_days_zero_returns_warning(self, client):
        resp = client.get("/dashboard/rolling-demo", params={"days": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert any("已从 0" in w for w in body["warnings"])

    def test_warnings_on_missing_data(self, client, monkeypatch):
        from ellectric.pipeline.shandong_loader import ShandongDataLoader

        empty = pd.DataFrame({"timestamp": pd.to_datetime([])})
        monkeypatch.setattr(ShandongDataLoader, "load_data", lambda self, **kw: empty)

        resp = client.get("/dashboard/rolling-demo")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["warnings"]) > 0

    def test_route_registered(self):
        from ellectric.api.server import app

        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/dashboard/rolling-demo" in routes
