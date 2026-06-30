import statistics
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ellectric.service.schemas import (
    RecommendRequest,
    RecommendResponse,
    TradeAction,
)


# ═══════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════

class TestRecommendRequestSchema:
    def test_recommend_request_defaults(self):
        req = RecommendRequest(date="2026-06-15")
        assert req.date == "2026-06-15"
        assert req.horizon_hours == 24
        assert req.market == "shandong"
        assert req.risk_preference == "balanced"
        assert req.max_actions == 5

    def test_recommend_request_required(self):
        with pytest.raises(ValidationError):
            RecommendRequest()

    def test_recommend_request_custom_values(self):
        req = RecommendRequest(
            date="2026-06-15",
            horizon_hours=48,
            market="shandong",
            risk_preference="aggressive",
            max_actions=3,
        )
        assert req.horizon_hours == 48
        assert req.risk_preference == "aggressive"
        assert req.max_actions == 3

    def test_recommend_request_horizon_bounds(self):
        RecommendRequest(date="2026-06-15", horizon_hours=1)
        RecommendRequest(date="2026-06-15", horizon_hours=72)
        with pytest.raises(ValidationError):
            RecommendRequest(date="2026-06-15", horizon_hours=0)
        with pytest.raises(ValidationError):
            RecommendRequest(date="2026-06-15", horizon_hours=73)


class TestTradeActionSchema:
    def test_trade_action_buy(self):
        action = TradeAction(
            timestamp="2026-06-15T10:00:00",
            action="buy",
            price_limit=350.0,
            quantity_mwh=50.0,
            reason="expected price rise",
            confidence="high",
        )
        assert action.action == "buy"
        assert action.price_limit == 350.0
        assert action.quantity_mwh == 50.0
        assert action.confidence == "high"

    def test_trade_action_sell(self):
        action = TradeAction(
            timestamp="2026-06-15T12:00:00",
            action="sell",
            reason="expected price drop",
            confidence="medium",
        )
        assert action.action == "sell"
        assert action.price_limit is None
        assert action.quantity_mwh is None

    def test_trade_action_hold(self):
        action = TradeAction(
            timestamp="2026-06-15T14:00:00",
            action="hold",
            reason="market uncertainty",
            confidence="low",
        )
        assert action.action == "hold"

    def test_trade_action_invalid_action(self):
        with pytest.raises(ValidationError):
            TradeAction(
                timestamp="2026-06-15T10:00:00",
                action="destroy",
                reason="n/a",
                confidence="high",
            )

    def test_trade_action_invalid_confidence(self):
        with pytest.raises(ValidationError):
            TradeAction(
                timestamp="2026-06-15T10:00:00",
                action="hold",
                reason="n/a",
                confidence="certain",
            )


class TestRecommendResponseSchema:
    def test_recommend_response_schema(self):
        actions = [
            TradeAction(
                timestamp="2026-06-15T10:00:00",
                action="buy",
                price_limit=350.0,
                quantity_mwh=50.0,
                reason="forecasted price spike at 10:00",
                confidence="high",
            ),
        ]
        resp = RecommendResponse(
            summary="buy 50 MWh at 10:00",
            actions=actions,
            confidence="high",
            evidence={"forecast": "available"},
            disclaimer="learning only",
        )
        assert resp.summary == "buy 50 MWh at 10:00"
        assert len(resp.actions) == 1
        assert resp.confidence == "high"
        assert resp.evidence["forecast"] == "available"

    def test_recommend_response_actions_default(self):
        resp = RecommendResponse(
            summary="no action",
            confidence="low",
            evidence={},
            disclaimer="learning only",
        )
        assert resp.actions == []

    def test_recommend_response_exclude_none(self):
        resp = RecommendResponse(
            summary="test",
            confidence="medium",
            evidence={},
            disclaimer="test",
        )
        data = resp.model_dump(exclude_none=True)
        assert "actions" in data


# ═══════════════════════════════════════════════════════════
# Handler Tests
# ═══════════════════════════════════════════════════════════

def _make_forecast_response(predictions=None):
    if predictions is None:
        predictions = [100.0, 102.0, 101.0, 103.0]
    from ellectric.service.schemas import ForecastMetrics
    ts = [datetime(2026, 1, 15, 0, 0)]
    return type("ForecastResponse", (), {
        "timestamps": ts * len(predictions),
        "predictions": predictions,
        "metrics": ForecastMetrics(mae=10.0, rmse=15.0, mape=5.0),
    })()


def _make_backtest_response():
    from ellectric.service.schemas import BacktestResponse
    return BacktestResponse(
        status="success",
        cumulative_pnl=[1000.0, 2000.0],
        sharpe_ratio=1.5,
        comparison={"oracle": 2000.0, "baseline_persistence": 800.0},
    )


def _make_explain_response():
    from ellectric.service.schemas import FeatureImportance
    return type("ExplainResponse", (), {
        "status": "success",
        "feature_importance": [
            FeatureImportance(name="hour", importance=0.5, rank=1),
        ],
    })()


def test_recommend_all_evidence_available():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response()
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain") as mock_e:
                mock_e.return_value = _make_explain_response()
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.confidence == "high"
    assert len(resp.actions) > 0


def test_recommend_forecast_only():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response()
        with patch("ellectric.service.handlers.run_backtest", side_effect=RuntimeError("no data")):
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("no explain")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.confidence == "low"
    assert len(resp.actions) > 0


def test_recommend_all_fail():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast", side_effect=RuntimeError("no model")):
        with patch("ellectric.service.handlers.run_backtest", side_effect=RuntimeError("no data")):
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("no explain")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.confidence == "low"
    assert all(a.action == "hold" for a in resp.actions)


def test_recommend_forecast_and_backtest_only():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response()
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("no explain")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.confidence == "medium"


def test_recommend_disclaimer_always_present():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response()
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain") as mock_e:
                mock_e.return_value = _make_explain_response()
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.disclaimer is not None
    assert len(resp.disclaimer) > 0


def test_recommend_disclaimer_present_low_confidence():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast", side_effect=RuntimeError("fail")):
        with patch("ellectric.service.handlers.run_backtest", side_effect=RuntimeError("fail")):
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("fail")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.disclaimer is not None
    assert len(resp.disclaimer) > 0


def test_recommend_max_actions():
    req = RecommendRequest(date="2026-06-15", max_actions=1)
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response(predictions=[100, 105, 110, 115])
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain") as mock_e:
                mock_e.return_value = _make_explain_response()
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert len(resp.actions) <= 1


def test_recommend_evidence_dict_present():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response()
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain") as mock_e:
                mock_e.return_value = _make_explain_response()
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert isinstance(resp.evidence, dict)
    assert resp.evidence.get("forecast") == "available"
    assert resp.evidence.get("backtest") == "available"
    assert resp.evidence.get("explain") == "available"


def test_recommend_evidence_partial():
    req = RecommendRequest(date="2026-06-15")
    with patch("ellectric.service.handlers.run_forecast", side_effect=RuntimeError("fail")):
        with patch("ellectric.service.handlers.run_backtest") as mock_b:
            mock_b.return_value = _make_backtest_response()
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("fail")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.evidence.get("forecast") != "available"
    assert resp.evidence.get("backtest") == "available"
    assert resp.confidence == "low"


def test_recommend_flat_trend_produces_hold():
    req = RecommendRequest(date="2026-06-15")
    flat_predictions = [100.0, 100.5, 100.3, 100.7]
    with patch("ellectric.service.handlers.run_forecast") as mock_f:
        mock_f.return_value = _make_forecast_response(predictions=flat_predictions)
        with patch("ellectric.service.handlers.run_backtest", side_effect=RuntimeError("no data")):
            with patch("ellectric.service.handlers.run_explain", side_effect=RuntimeError("no explain")):
                from ellectric.service.handlers import run_recommend_trade
                resp = run_recommend_trade(req)

    assert resp.confidence == "low"
    assert len(resp.actions) >= 1
