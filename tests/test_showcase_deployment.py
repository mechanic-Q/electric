"""Showcase WebUI deployment smoke tests.

Primary seam: FastAPI app behaves correctly as a public showcase site.
Supporting seam: Rolling Demo artifact contract.
Supporting seam: Showcase Explainer tool boundary.

Covers issue #31 acceptance criteria.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from ellectric.api.server import app

    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════
# Primary seam: Showcase app smoke test
# ═══════════════════════════════════════════════════════════════════


class TestStaticRollingDemo:
    """Static Rolling Demo JSON is served and has correct contract."""

    def test_rolling_demo_json_returns_200(self, client):
        resp = client.get("/rolling-demo.json")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")

    def test_rolling_demo_json_has_contract_keys(self, client):
        resp = client.get("/rolling-demo.json")
        data = resp.json()
        expected_keys = {"meta", "series", "panels", "strategy", "reports", "warnings"}
        assert expected_keys.issubset(data.keys()), (
            f"missing keys: {expected_keys - set(data.keys())}"
        )

    def test_rolling_demo_meta_has_required_fields(self, client):
        resp = client.get("/rolling-demo.json")
        meta = resp.json()["meta"]
        for field in ("source", "start", "end", "frequency", "points_per_day", "rows"):
            assert field in meta, f"missing meta field: {field}"
        assert meta["source"] == "shandong"
        assert meta["frequency"] == "15min"
        assert meta["points_per_day"] == 96
        assert meta["rows"] > 0


class TestOfflineReports:
    """Offline report listing and detail endpoints are readable."""

    def test_report_list_returns_200(self, client):
        resp = client.get("/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_report_detail_returns_200(self, client):
        list_resp = client.get("/reports")
        reports = list_resp.json()
        first_id = reports[0]["id"]
        resp = client.get(f"/reports/{first_id}")
        assert resp.status_code == 200
        detail = resp.json()
        assert "id" in detail
        assert "title" in detail or "content" in detail


class TestChatStreamMissingKey:
    """Copilot chat stream returns a clear error when no DeepSeek key is set."""

    def test_chat_stream_without_key_returns_error(self, client, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setattr(
            "ellectric.llm.agent._resolve_deepseek_key", lambda: None
        )
        resp = client.post(
            "/chat/stream",
            json={"query": "XGBoost 是什么？"},
        )
        assert resp.status_code == 200
        body = resp.text
        assert "DEEPSEEK_API_KEY" in body or "未设置" in body or "error" in body.lower()


# ═══════════════════════════════════════════════════════════════════
# Supporting seam: Rolling Demo artifact contract
# ═══════════════════════════════════════════════════════════════════


class TestRollingDemoArtifact:
    """Pre-baked Rolling Demo JSON artifact has stable contract."""

    @pytest.fixture(scope="class")
    def artifact(self):
        path = Path(__file__).parent.parent / "ellectric" / "web" / "public" / "rolling-demo.json"
        if not path.exists():
            pytest.skip("rolling-demo.json not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_artifact_has_all_six_keys(self, artifact):
        expected = {"meta", "series", "panels", "strategy", "reports", "warnings"}
        assert expected.issubset(artifact.keys())

    def test_artifact_meta_source_is_shandong(self, artifact):
        assert artifact["meta"]["source"] == "shandong"
        assert artifact["meta"]["frequency"] == "15min"

    def test_artifact_has_enough_data_for_autoplay(self, artifact):
        assert artifact["meta"]["rows"] > 0
        assert len(artifact["series"]) > 0


# ═══════════════════════════════════════════════════════════════════
# Supporting seam: Showcase Explainer tool boundary
# ═══════════════════════════════════════════════════════════════════


class TestAgentToolBoundary:
    """Showcase Explainer only has lightweight lookup tools."""

    HEAVY_TOOLS = {"query_forecast", "run_simulation", "run_backtest", "recommend_trade"}
    SAFE_TOOLS = {"query_capabilities", "query_datasets", "query_reports", "read_report"}

    def test_heavy_tools_not_in_agent_module(self):
        import inspect

        from ellectric.llm import agent as agent_module

        source = inspect.getsource(agent_module)
        for tool_name in self.HEAVY_TOOLS:
            assert tool_name not in source, (
                f"Heavy tool '{tool_name}' still referenced in agent module"
            )

    def test_safe_tools_importable(self):
        from ellectric.llm.tools import (
            query_capabilities,
            query_datasets,
            query_reports,
            read_report,
        )

        for tool in (query_capabilities, query_datasets, query_reports, read_report):
            assert hasattr(tool, "invoke"), f"{tool} missing invoke method"
            assert hasattr(tool, "name"), f"{tool} missing name attribute"

    def test_system_prompt_is_showcase_explainer(self):
        from ellectric.llm.agent import _SYSTEM_PROMPT

        assert "展示" in _SYSTEM_PROMPT or "解说" in _SYSTEM_PROMPT
        assert "通俗" in _SYSTEM_PROMPT
