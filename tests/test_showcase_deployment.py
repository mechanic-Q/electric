"""Showcase WebUI deployment smoke tests.

Primary seam: FastAPI app behaves correctly as a public showcase site.
Supporting seam: Rolling Demo artifact contract.
Supporting seam: Showcase Explainer tool boundary.

Covers issue #31 acceptance criteria.
"""
from __future__ import annotations

import json
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

    def test_artifact_exposes_validated_strategy_snapshot(self, artifact):
        strategy = artifact["strategy"]

        assert strategy["status"] == "ok"
        assert [row["strategy"] for row in strategy["summary"]] == [
            "td3", "ppo", "sac", "trend"
        ]
        assert strategy["window"]["points"] == 2880
        assert "ranking" not in strategy
        assert "pnl_curves" not in strategy
        assert all(panel["id"] != "strategy" for panel in artifact["panels"])


class TestStrategyComparisonSource:
    """Public strategy semantics remain separate from legacy report fields."""

    @pytest.fixture(scope="class")
    def sources(self):
        root = Path(__file__).parent.parent / "ellectric" / "web" / "src"
        return {
            path.name: path.read_text(encoding="utf-8")
            for path in (
                root / "App.tsx",
                root / "ReplayStage.tsx",
                root / "StrategyComparison.tsx",
                root / "StrategyPathEvidence.tsx",
            )
        }

    def test_comparison_uses_all_approved_metrics(self, sources):
        comparison = sources["StrategyComparison.tsx"]
        for label in (
            "30 天模拟价差值",
            "盈利日",
            "持仓时段正贡献率",
            "最大回撤",
            "盈利因子",
            "趋势倍数",
            "Oracle 捕获率",
            "事实标签",
        ):
            assert label in comparison

    def test_legacy_ranking_and_currency_semantics_are_absent(self, sources):
        public_source = "\n".join(sources.values())

        assert "strategy.ranking" not in public_source
        assert "formatPnL" not in public_source
        assert "收益 / P&L" not in public_source
        assert "RL 全量评估 / Full Dataset RL Evaluation" not in public_source

    def test_replay_uses_one_multi_granularity_playhead(self, sources):
        replay = sources["ReplayStage.tsx"]

        assert 'type ReplayMode = "day" | "hour" | "point"' in replay
        assert "setTick" in replay
        assert "setCurrentTick" not in replay
        assert "setSpeed" not in replay
        assert "setInterval" not in replay
        assert "visibilitychange" in replay
        assert "prefers-reduced-motion: reduce" in replay

    def test_replay_preserves_market_source_semantics(self, sources):
        replay = sources["ReplayStage.tsx"]

        assert "山东市场时间（北京时间，UTC+8）" in replay
        assert "30 天 × 24 小时实时价格均价" in replay
        assert "历史发布负荷预测" in replay
        assert "日前价仅作对照" in replay
        assert "30×96" not in replay

    def test_strategy_path_uses_native_accessible_visuals(self, sources):
        path = sources["StrategyPathEvidence.tsx"]

        assert "const HEAT_LIMIT = 300_000" in path
        assert "<svg" in path
        assert 'type="button"' in path
        assert 'role="gridcell"' in path
        assert "onSelectDay(day)" in path
        assert "Oracle 理论价差上界" in path
        assert "plotly" not in path.lower()
        assert "recharts" not in path.lower()

    def test_copilot_sends_compact_current_replay_context(self, sources):
        app = sources["App.tsx"]
        replay = sources["ReplayStage.tsx"]

        assert "onContextChange={setReplayContext}" in app
        assert "replayContext, ac.signal" in app
        assert 'scene: "shandong-2025-10-30d"' in replay
        assert "strategy.provenance.content_hash" in replay
        assert "long_term_evidence" not in replay

    def test_degraded_strategy_does_not_render_comparison_or_long_term_values(
        self, sources
    ):
        comparison = sources["StrategyComparison.tsx"]

        degraded_branch = comparison.split('if (strategy.status !== "ok")', 1)[1]
        degraded_branch = degraded_branch.split("const { window", 1)[0]
        assert "StrategyTable" not in degraded_branch
        assert "strategy-long-term" not in degraded_branch


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
