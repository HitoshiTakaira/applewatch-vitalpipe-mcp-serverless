"""Wiring-level tests for the MCP Lambda handler.

These check that the FastMCP tool wrappers delegate correctly and that the
ASGI app is assembled as expected. Full protocol-level (Streamable HTTP over
Mangum) verification is left to manual E2E testing after deploy, per
docs/基本設計.md §8 — simulating a real MCP client handshake through Mangum
in a unit test isn't worth the complexity for this project's scale.
"""

from __future__ import annotations

from mangum import Mangum

from handlers.mcp_function import app as mcp_app


def test_tools_delegate_to_queries(monkeypatch):
    sentinel = {"ok": True}
    monkeypatch.setattr(mcp_app.queries, "get_metric_summary", lambda *a, **k: sentinel)
    monkeypatch.setattr(mcp_app.queries, "get_workouts", lambda *a, **k: sentinel)
    monkeypatch.setattr(mcp_app.queries, "get_sleep_summary", lambda *a, **k: sentinel)
    monkeypatch.setattr(mcp_app.queries, "get_trend", lambda *a, **k: sentinel)

    assert mcp_app.get_metric_summary("active_energy", "2026-07-01", "2026-07-02") is sentinel
    assert mcp_app.get_workouts("2026-07-01", "2026-07-02") is sentinel
    assert mcp_app.get_sleep_summary("2026-07-01", "2026-07-02") is sentinel
    assert mcp_app.get_trend("active_energy", 7) is sentinel


def test_asgi_app_mounts_mcp_route():
    paths = {route.path for route in mcp_app._asgi_app.routes}
    assert "/mcp" in paths


def test_handler_is_mangum_instance():
    assert isinstance(mcp_app.handler, Mangum)
