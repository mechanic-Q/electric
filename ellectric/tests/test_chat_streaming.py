"""Test stream_chat SSE generator with mocked agent executor.

No live DeepSeek API key required — create_agent_executor is monkeypatched
to return a fake agent that yields controlled event sequences.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from ellectric.chat.streaming import stream_chat

# ── Helpers ──────────────────────────────────────────────────────────


class FakeChunk:
    """Mimics AIMessageChunk — just holds .content."""
    def __init__(self, content: str):
        self.content = content


class FakeMessages:
    """Mimics the dict-like messages sequence returned by ainvoke."""
    def __init__(self, content: str):
        self.content = content


def _collect(query: str, events, ainvoke_content="兜底回答", history=None):
    """Run stream_chat synchronously and return list of decoded SSE frames."""
    async def _run():
        frames = []

        async def fake_astream(*args, **kwargs):
            for ev in events:
                yield ev

        fake_agent = AsyncMock()
        fake_agent.astream_events = fake_astream
        fake_agent.ainvoke = AsyncMock(return_value={
            "messages": [FakeMessages(ainvoke_content)],
        })

        with patch("ellectric.chat.streaming.create_agent_executor",
                   return_value=fake_agent):
            with patch("ellectric.chat.streaming._resolve_deepseek_key",
                       return_value="sk-test"):
                async for frame in stream_chat(query, history=history):
                    frames.append(json.loads(frame.replace("data: ", "").strip()))
        return frames

    return asyncio.run(_run())


# ── Tests: normal token stream ──────────────────────────────────────


def test_normal_token_stream():
    """Content-bearing chunks are emitted as token frames."""
    events = [
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("Hello")}},
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk(" world")}},
    ]
    frames = _collect("hi", events)
    tokens = [f for f in frames if f["type"] == "token"]
    assert len(tokens) == 2
    assert tokens[0]["content"] == "Hello"
    assert tokens[1]["content"] == " world"
    assert frames[-1]["type"] == "done"


def test_empty_content_chunks_are_skipped():
    """Reasoning-phase chunks with empty content are not emitted."""
    events = [
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("")}},
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("Real")}},
    ]
    frames = _collect("test empty", events)
    tokens = [f for f in frames if f["type"] == "token"]
    assert len(tokens) == 1
    assert tokens[0]["content"] == "Real"


# ── Tests: zero-token fallback ──────────────────────────────────────


def test_zero_token_triggers_ainvoke_fallback():
    """When astream_events yields no content tokens, ainvoke is called."""
    events = [
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("")}},
    ]
    frames = _collect("trigger fallback", events, ainvoke_content="兜底回答好了")
    tokens = [f for f in frames if f["type"] == "token"]
    assert len(tokens) == 1
    assert tokens[0]["content"] == "兜底回答好了"
    assert frames[-1]["type"] == "done"


def test_ainvoke_fallback_only_fires_when_zero_tokens():
    """Normal token stream does NOT trigger ainvoke."""
    events = [
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("normal")}},
    ]
    frames = _collect("no fallback", events, ainvoke_content="should not appear")
    tokens = [f for f in frames if f["type"] == "token"]
    assert len(tokens) == 1
    assert tokens[0]["content"] == "normal"


# ── Tests: tool events ──────────────────────────────────────────────


def test_tool_call_and_result_forwarded():
    """on_tool_start → tool_call frame, on_tool_end → tool_result frame."""
    events = [
        {"event": "on_tool_start",
         "name": "query_reports",
         "data": {"input": {}}},
        {"event": "on_tool_end",
         "name": "query_reports",
         "data": {"output": '[{"id":"r1"}]'}},
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("合成回答")}},
    ]
    frames = _collect("tools test", events)
    types = [f["type"] for f in frames]
    assert "tool_call" in types
    assert "tool_result" in types
    tc = [f for f in frames if f["type"] == "tool_call"][0]
    assert tc["name"] == "query_reports"
    tr = [f for f in frames if f["type"] == "tool_result"][0]
    assert tr["name"] == "query_reports"
    assert frames[-1]["type"] == "done"


# ── Tests: done always last ─────────────────────────────────────────


def test_done_is_always_last_frame():
    """done frame is the final event emitted."""
    events = [
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("A")}},
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("B")}},
    ]
    frames = _collect("done last", events)
    assert frames[-1]["type"] == "done"


# ── Tests: edge cases ───────────────────────────────────────────────


def test_empty_query_returns_error():
    """Empty or whitespace-only query yields error frame."""
    frames = _collect("  ", [])
    assert frames[0]["type"] == "error"


def test_missing_api_key_returns_error():
    """When no API key is configured, yield error frame."""

    async def _run():
        frames = []
        with patch("ellectric.chat.streaming._resolve_deepseek_key",
                   return_value=None):
            async for frame in stream_chat("hi"):
                frames.append(json.loads(frame.replace("data: ", "").strip()))
        return frames

    frames = asyncio.run(_run())
    assert frames[0]["type"] == "error"


def test_unknown_events_are_skipped():
    """Unrecognized event types are silently ignored."""
    events = [
        {"event": "on_chat_model_start", "data": {}},
        {"event": "on_chain_start", "data": {}},
        {"event": "on_chat_model_stream",
         "data": {"chunk": FakeChunk("only this")}},
    ]
    frames = _collect("skip unknown", events)
    tokens = [f for f in frames if f["type"] == "token"]
    assert len(tokens) == 1
    assert tokens[0]["content"] == "only this"
