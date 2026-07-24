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

import hashlib
import json
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
    def test_default_payload_has_validated_strategy_evidence_snapshot(self):
        from ellectric.service.dashboard import build_rolling_demo

        result = build_rolling_demo()
        strategy = result.strategy

        assert strategy.status == "ok"
        assert strategy.window == {
            "start": "2025-10-01T00:00:00+08:00",
            "end": "2025-10-30T23:45:00+08:00",
            "timezone": "Asia/Shanghai",
            "points": 2880,
            "points_per_day": 96,
            "standardized_day": "00:00-23:45",
        }
        assert result.meta.start == "2025-10-01T00:00:00+08:00"
        assert result.meta.end == "2025-10-30T23:45:00+08:00"
        # Source 00:00 is a Shandong local clock mislabeled UTC by the loader;
        # showcase correction must preserve 00:00 rather than shift it to 08:00.
        assert result.series.timestamps[0] == "2025-10-01T00:00:00+08:00"
        assert len(strategy.timeseries["timestamps"]) == 2880
        assert strategy.timeseries["timestamps"] == result.series.timestamps
        assert set(strategy.timeseries["strategies"]) == {
            "td3", "ppo", "sac", "trend"
        }
        assert strategy.methodology["capacity_scale_mw"] == pytest.approx(99673.38)
        assert strategy.methodology["settlement_price"] == "historical_rt_price"
        assert strategy.daily["dates"] == [
            f"2025-10-{day:02d}" for day in range(1, 31)
        ]
        assert strategy.daily["baseline_initialization"][:7] == [True] * 7
        assert strategy.daily["baseline_initialization"][7:] == [False] * 23

        summary = {row["strategy"]: row for row in strategy.summary}
        assert summary["td3"]["simulated_spread_value"] == pytest.approx(3178504.01, abs=0.01)
        assert summary["td3"]["profitable_days"] == 25
        assert summary["td3"]["active_positive_contribution_rate"] == pytest.approx(
            0.5344767238, abs=1e-10
        )
        assert summary["td3"]["max_drawdown"] == pytest.approx(257417.40, abs=0.01)
        assert summary["td3"]["profit_factor"] == pytest.approx(1.37, abs=0.005)
        assert summary["td3"]["trend_multiple"] == pytest.approx(5.59, abs=0.005)
        assert summary["td3"]["oracle_capture_rate"] == pytest.approx(0.149, abs=0.0005)
        assert summary["ppo"]["simulated_spread_value"] == pytest.approx(2344946.61, abs=0.01)
        assert summary["sac"]["simulated_spread_value"] == pytest.approx(1691325.43, abs=0.01)
        assert summary["trend"]["simulated_spread_value"] == pytest.approx(568534.36, abs=0.01)

        assert len(strategy.oracle["cumulative_simulated_spread_value"]) == 2880
        assert strategy.long_term_evidence["points"] == 10176
        assert strategy.provenance["source_git_sha"] == "a68513326c13d765db6748a68e5dfd48816c55a4"
        serialized = strategy.model_dump(mode="json")
        expected_hash = serialized["provenance"].pop("content_hash")
        actual_hash = hashlib.sha256(
            json.dumps(
                serialized,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        assert expected_hash == actual_hash
        assert all(panel.id != "strategy" for panel in result.panels)

    def test_missing_strategy_evidence_degrades_as_one_unit(self, monkeypatch, tmp_path):
        from ellectric.service import dashboard

        monkeypatch.setattr(dashboard, "_REPORTS_ROOT", tmp_path)
        result = dashboard.build_rolling_demo()

        assert result.meta.rows == 2880
        assert result.strategy.status == "degraded"
        assert "missing" in (result.strategy.degradation_reason or "")
        assert result.strategy.summary == []
        assert result.strategy.timeseries == {}
        assert result.strategy.daily == {}
        assert result.strategy.oracle == {}
        assert result.strategy.long_term_evidence == {}
        assert result.strategy.provenance == {}
        assert any("30 天策略证据不可用" in warning for warning in result.warnings)

    def test_prebake_cli_returns_nonzero_for_market_only_degradation(
        self, monkeypatch, tmp_path
    ):
        from ellectric.scripts import prebake_demo
        from ellectric.service import dashboard

        monkeypatch.setattr(dashboard, "_REPORTS_ROOT", tmp_path / "missing-reports")
        output = tmp_path / "rolling-demo.json"

        exit_code = prebake_demo.main(["--output", str(output)])
        artifact = json.loads(output.read_text(encoding="utf-8"))

        assert exit_code == 1
        assert artifact["meta"]["rows"] == 2880
        assert artifact["strategy"]["status"] == "degraded"
        assert artifact["strategy"]["summary"] == []
        assert artifact["strategy"]["timeseries"] == {}

    def test_prebake_cli_writes_validated_strategy_snapshot(self, tmp_path):
        from ellectric.scripts import prebake_demo

        output = tmp_path / "rolling-demo.json"
        exit_code = prebake_demo.main(["--output", str(output)])
        artifact = json.loads(output.read_text(encoding="utf-8"))

        assert exit_code == 0
        assert artifact["meta"]["rows"] == 2880
        assert artifact["strategy"]["status"] == "ok"
        assert len(artifact["strategy"]["timeseries"]["timestamps"]) == 2880
        expected_hash = artifact["strategy"]["provenance"].pop("content_hash")
        actual_hash = hashlib.sha256(
            json.dumps(
                artifact["strategy"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        assert expected_hash == actual_hash

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
