from __future__ import annotations

import asyncio
import json


async def _collect(generator):
    return [frame async for frame in generator]


def _parse(frame: str) -> dict:
    assert frame.startswith("data: ")
    return json.loads(frame.removeprefix("data: ").strip())


class _Chunk:
    def __init__(self, content: str):
        self.content = content


class _JsonToolAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": _Chunk("你好")}}
        yield {
            "event": "on_tool_start",
            "name": "query_reports",
            "data": {"input": {"report_type": "weather_tier4"}},
        }
        yield {
            "event": "on_tool_end",
            "name": "query_reports",
            "data": {
                "output": json.dumps(
                    {
                        "status": "fallback",
                        "source": "offline_report",
                        "fallback_reason": "model_missing",
                        "report_status": "degraded",
                        "metrics": {"mae_baseline_tier3": 3412.02},
                        "metrics_meta": {"mae_baseline_tier3": {"label": "Baseline Tier3 MAE", "unit": "MW"}},
                    }
                )
            },
        }


class _PlainTextToolAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_tool_start",
            "name": "read_report",
            "data": {"input": {"report_id": "weather_tier4/validation"}},
        }
        yield {
            "event": "on_tool_end",
            "name": "read_report",
            "data": {"output": "plain text report"},
        }


def test_stream_chat_emits_tool_result_payload(monkeypatch):
    from ellectric.chat import streaming

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(streaming, "create_agent_executor", lambda: _JsonToolAgent())

    events = [_parse(frame) for frame in asyncio.run(_collect(streaming.stream_chat("查报告")))]

    assert events[0] == {"type": "token", "content": "你好"}
    assert events[1] == {
        "type": "tool_call",
        "name": "query_reports",
        "args": {"report_type": "weather_tier4"},
    }
    assert events[2]["type"] == "tool_result"
    assert events[2]["name"] == "query_reports"
    payload = json.loads(events[2]["content"])
    assert payload["source"] == "offline_report"
    assert payload["fallback_reason"] == "model_missing"
    assert payload["report_status"] == "degraded"
    assert payload["metrics"] == {"mae_baseline_tier3": 3412.02}
    assert payload["metrics_meta"]["mae_baseline_tier3"]["unit"] == "MW"
    assert events[-1] == {"type": "done"}


def test_stream_chat_sets_payload_none_for_plain_text(monkeypatch):
    from ellectric.chat import streaming

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(streaming, "create_agent_executor", lambda: _PlainTextToolAgent())

    events = [_parse(frame) for frame in asyncio.run(_collect(streaming.stream_chat("读报告")))]

    result = next(event for event in events if event["type"] == "tool_result")
    assert result == {
        "type": "tool_result",
        "name": "read_report",
        "content": "plain text report",
    }


def test_stream_chat_uses_resolved_key_without_env(monkeypatch):
    from ellectric.chat import streaming

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(streaming, "_resolve_deepseek_key", lambda: "test")
    monkeypatch.setattr(streaming, "create_agent_executor", lambda: _PlainTextToolAgent())

    events = [_parse(frame) for frame in asyncio.run(_collect(streaming.stream_chat("读报告")))]

    assert not any(event["type"] == "error" for event in events)
    assert next(event for event in events if event["type"] == "tool_result")["content"] == "plain text report"


def test_stream_chat_empty_query_uses_message_field():
    from ellectric.chat.streaming import stream_chat

    events = [_parse(frame) for frame in asyncio.run(_collect(stream_chat("  ")))]

    assert events == [{"type": "error", "message": "查询不能为空"}]
