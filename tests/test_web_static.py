from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from ellectric.api.server import app
    return TestClient(app)


def test_static_index_returns_html(client):
    """GET / returns the built dashboard HTML page."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    assert "Ellectric" in body
    assert "id=\"root\"" in body


def test_static_serves_js_assets(client):
    """Built JS assets are served correctly."""
    resp = client.get("/")
    html = resp.text
    import re
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
    assert scripts, "no script src found in index.html"
    for src in scripts:
        path = src.lstrip("./")
        resp2 = client.get("/" + path)
        assert resp2.status_code == 200, f"Asset {src} not served"
        assert resp2.headers["content-type"].startswith(
            ("text/javascript", "application/javascript", "application/x-javascript")
        ), f"Unexpected content-type for {src}: {resp2.headers['content-type']}"


def test_legacy_api_routes_not_captured(client):
    """API routes are not captured by the static mount."""
    routes = {r.path for r in client.app.routes if hasattr(r, "path")}
    for path in ("/predict", "/simulate", "/backtest", "/explain", "/recommend",
                 "/chat/stream", "/capabilities", "/datasets", "/reports",
                 "/reports/{report_id:path}"):
        assert path in routes, f"missing route: {path}"
