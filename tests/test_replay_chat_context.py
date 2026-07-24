from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage


def _strategy(*, value: float, positive: int, negative: int) -> dict:
    return {
        "simulated_spread_value": value,
        "contribution": "positive" if value > 0 else "negative",
        "reconstructed_position_pct": None,
        "position_state": None,
        "long_periods": positive,
        "short_periods": negative,
        "approximately_flat_periods": 0,
        "indeterminate_periods": 0,
        "mean_absolute_position_pct": 51.2,
    }


def replay_context() -> dict:
    return {
        "scene": "shandong-2025-10-30d",
        "window_start": "2025-10-01T00:00:00+08:00",
        "window_end": "2025-10-30T23:45:00+08:00",
        "timezone": "Asia/Shanghai (UTC+8)",
        "granularity": "daily",
        "period_start": "2025-10-18T00:00:00+08:00",
        "period_end": "2025-10-18T23:45:00+08:00",
        "period_points": 96,
        "baseline_initialization": False,
        "market": {
            "realtime_settlement_price": 451.2,
            "realtime_price_measure": "mean",
            "realtime_price_min": 201.0,
            "realtime_price_max": 701.0,
            "daily_backtest_baseline_price": 386.0,
            "spread": 65.2,
            "day_ahead_hourly_price": None,
            "load_actual_mw": 98_000.0,
            "historical_published_load_forecast_mw": 97_500.0,
            "load_measure": "peak",
            "wind_mw": 8_000.0,
            "solar_mw": 4_000.0,
            "renewable_measure": "mean",
        },
        "strategies": {
            "td3": _strategy(value=556_299.63, positive=58, negative=38),
            "ppo": _strategy(value=312_000.0, positive=62, negative=34),
            "sac": _strategy(value=-18_000.0, positive=47, negative=49),
            "trend": _strategy(value=86_150.0, positive=54, negative=42),
        },
        "snapshot": {
            "generated_at": "2026-07-20T14:36:19Z",
            "content_hash": "a" * 64,
        },
    }


def test_chat_api_validates_and_forwards_exact_replay_context(monkeypatch):
    from ellectric.api.server import app
    from ellectric.chat import streaming

    received: list[dict | None] = []

    async def fake_stream(_query, _history, replay_context=None):
        received.append(replay_context)
        yield 'data: {"type":"done"}\n\n'

    monkeypatch.setattr(streaming, "stream_chat", fake_stream)
    response = TestClient(app).post(
        "/chat/stream",
        json={"query": "这一天怎么表现？", "history": [], "replay_context": replay_context()},
    )

    assert response.status_code == 200
    assert received == [replay_context()]


def test_chat_api_rejects_inconsistent_or_extra_replay_facts():
    from ellectric.api.server import app

    extra_context = replay_context()
    extra_context["long_term_pnl"] = 20_340_000
    extra_response = TestClient(app).post(
        "/chat/stream",
        json={"query": "解释", "history": [], "replay_context": extra_context},
    )
    inconsistent_context = replay_context()
    inconsistent_context["period_points"] = 4
    inconsistent_response = TestClient(app).post(
        "/chat/stream",
        json={"query": "解释", "history": [], "replay_context": inconsistent_context},
    )

    assert extra_response.status_code == 422
    assert {error["type"] for error in extra_response.json()["detail"]} == {"extra_forbidden"}
    assert inconsistent_response.status_code == 422
    assert {error["type"] for error in inconsistent_response.json()["detail"]} == {"value_error"}


class _CaptureAgent:
    def __init__(self):
        self.messages: list = []

    async def astream_events(self, payload, **_kwargs):
        self.messages = payload["messages"]
        yield {"event": "on_chat_model_stream", "data": {"chunk": type("Chunk", (), {"content": "已解释"})()}}


def test_replay_context_only_decorates_current_question(monkeypatch):
    from ellectric.chat import streaming

    agent = _CaptureAgent()
    monkeypatch.setattr(streaming, "_resolve_deepseek_key", lambda: "test")
    monkeypatch.setattr(streaming, "create_agent_executor", lambda: agent)

    async def collect():
        return [frame async for frame in streaming.stream_chat(
            "为什么TD3是正贡献？",
            history=[
                {"role": "user", "content": "旧问题"},
                {"role": "assistant", "content": "旧回答"},
            ],
            replay_context=replay_context(),
        )]

    frames = asyncio.run(collect())

    assert isinstance(agent.messages[0], HumanMessage)
    assert agent.messages[0].content == "旧问题"
    assert isinstance(agent.messages[1], AIMessage)
    assert agent.messages[1].content == "旧回答"
    current = agent.messages[2].content
    assert "<replay_context>" in current
    assert '"period_start":"2025-10-18T00:00:00+08:00"' in current
    assert '"simulated_spread_value":556299.63' in current
    assert "20340000" not in current
    assert "为什么TD3是正贡献？" in current
    assert json.loads(frames[-1].removeprefix("data: ")) == {"type": "done"}
